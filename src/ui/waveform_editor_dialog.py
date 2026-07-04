import os
import tempfile

import numpy as np
from pydub import AudioSegment
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollBar,
    QVBoxLayout,
    QWidget,
)

from file_operations.audio_tags import AudioTagHelper
from log_config import get_logger

logger = get_logger(__name__)

# 5 ms per envelope bin: enough detail to spot and cut silences when fully zoomed in
_ENVELOPE_BINS_PER_SECOND = 200
_MIN_VIEW_WINDOW_S = 0.05
_ZOOM_STEP = 1.5
# How close (px) the mouse must be to a selection edge to grab and drag it
_EDGE_GRAB_PX = 6


def _max_pool(values: np.ndarray, bins: int) -> np.ndarray:
    """Max-pool values into the requested number of bins, spanning the whole array."""
    if len(values) <= bins:
        return values
    edges = np.linspace(0, len(values), bins + 1).astype(int)
    return np.maximum.reduceat(values, edges[:-1])


class WaveformEditView(QWidget):
    """Renders a zoomable/scrollable window of the waveform envelope with a
    click-drag selection and a playback needle. All positions are in seconds."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.envelope = np.array([])
        self.duration = 0.0
        self.view_start = 0.0
        self.view_end = 0.0
        self.selection = None  # (start_s, end_s) or None
        self.playhead = None  # seconds or None
        self._drag_anchor = None
        self.on_view_changed = None  # callback, no args
        self.on_selection_changed = None  # callback, no args
        self.setMinimumHeight(180)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)  # for the resize cursor over selection edges

    def set_envelope(self, envelope: np.ndarray, duration: float) -> None:
        self.envelope = envelope
        self.duration = duration
        self.view_start = 0.0
        self.view_end = duration
        self.selection = None
        self.playhead = None
        self._notify()
        self.update()

    def _notify(self) -> None:
        if self.on_view_changed:
            self.on_view_changed()
        if self.on_selection_changed:
            self.on_selection_changed()

    def x_to_time(self, x: int) -> float:
        w = max(1, self.width())
        t = self.view_start + (x / w) * (self.view_end - self.view_start)
        return max(0.0, min(self.duration, t))

    def time_to_x(self, t: float) -> int:
        window = self.view_end - self.view_start
        if window <= 0:
            return 0
        return int((t - self.view_start) / window * self.width())

    def set_view(self, start: float, end: float) -> None:
        window = max(_MIN_VIEW_WINDOW_S, end - start)
        start = max(0.0, min(start, self.duration - window))
        self.view_start = start
        self.view_end = min(self.duration, start + window)
        if self.on_view_changed:
            self.on_view_changed()
        self.update()

    def zoom(self, factor: float, centre_t: float = None) -> None:
        window = self.view_end - self.view_start
        new_window = max(_MIN_VIEW_WINDOW_S, min(self.duration, window / factor))
        if centre_t is None:
            centre_t = (self.view_start + self.view_end) / 2
        rel = (centre_t - self.view_start) / window if window else 0.5
        start = centre_t - rel * new_window

        if self.selection:
            sel_start, sel_end = self.selection
            if (sel_end - sel_start) <= new_window:
                # Shift just enough to keep the whole selection in view
                start = max(min(start, sel_start), sel_end - new_window)
            else:
                # Selection can't fit: keep its right-hand edge in the centre of the window
                start = sel_end - new_window / 2

        self.set_view(start, start + new_window)

    def zoom_fit(self) -> None:
        self.set_view(0.0, self.duration)

    def set_playhead(self, t) -> None:
        self.playhead = t
        self.update()

    def wheelEvent(self, event):
        factor = _ZOOM_STEP if event.angleDelta().y() > 0 else 1 / _ZOOM_STEP
        self.zoom(factor, self.x_to_time(event.pos().x()))

    def _selection_edge_at(self, x: int):
        """Return 'left'/'right' if x is within grab range of a selection edge, else None."""
        if not self.selection:
            return None
        if abs(x - self.time_to_x(self.selection[0])) <= _EDGE_GRAB_PX:
            return "left"
        if abs(x - self.time_to_x(self.selection[1])) <= _EDGE_GRAB_PX:
            return "right"
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edge = self._selection_edge_at(event.pos().x())
            if edge:
                # Grab the edge: anchor on the opposite edge so dragging resizes the selection
                self._drag_anchor = self.selection[1] if edge == "left" else self.selection[0]
            else:
                self._drag_anchor = self.x_to_time(event.pos().x())
                self.selection = None
            if self.on_selection_changed:
                self.on_selection_changed()
            self.update()

    def mouseMoveEvent(self, event):
        if self._drag_anchor is not None:
            t = self.x_to_time(event.pos().x())
            self.selection = (min(self._drag_anchor, t), max(self._drag_anchor, t))
            if self.on_selection_changed:
                self.on_selection_changed()
            self.update()
        else:
            self.setCursor(Qt.SizeHorCursor if self._selection_edge_at(event.pos().x()) else Qt.CrossCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_anchor is not None:
            t = self.x_to_time(event.pos().x())
            selection = (min(self._drag_anchor, t), max(self._drag_anchor, t))
            # Treat a tiny drag as a click: clear the selection
            self.selection = selection if (selection[1] - selection[0]) > 0.005 else None
            self._drag_anchor = None
            if self.on_selection_changed:
                self.on_selection_changed()
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(30, 30, 30))
        if len(self.envelope) == 0 or self.duration <= 0:
            return

        mid = h // 2
        n_env = len(self.envelope)
        i0 = int(self.view_start / self.duration * n_env)
        i1 = max(i0 + 1, int(self.view_end / self.duration * n_env))
        visible = self.envelope[i0:i1]
        display = _max_pool(visible, w)
        n = len(display)

        pen = QPen(QColor("orange"))
        pen.setWidth(1)
        painter.setPen(pen)
        for i, value in enumerate(display):
            x = int(i * w / n)
            y = int(value * (h // 2 - 2))
            painter.drawLine(x, mid - y, x, mid + y)

        if self.selection:
            x0 = self.time_to_x(self.selection[0])
            x1 = self.time_to_x(self.selection[1])
            painter.fillRect(x0, 0, max(1, x1 - x0), h, QColor(70, 130, 220, 90))
            painter.setPen(QPen(QColor(120, 170, 255), 1))
            painter.drawLine(x0, 0, x0, h)
            painter.drawLine(x1, 0, x1, h)

        if self.playhead is not None and self.view_start <= self.playhead <= self.view_end:
            painter.setPen(QPen(Qt.red, 2))
            x = self.time_to_x(self.playhead)
            painter.drawLine(x, 0, x, h)


class WaveformEditorDialog(QDialog):
    """Pop-up editor for a wav file: zoom/scroll the waveform, select regions,
    cut them out (or trim to a selection), preview edits, undo, then save over
    the original or as a copy. Tags and cover art are preserved on save."""

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowTitle(f"Waveform Editor - {os.path.basename(file_path)}")
        self.resize(1200, 420)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        self.original = AudioSegment.from_wav(file_path)
        self.audio = self.original
        self.ops = []  # list of ("cut"|"keep", start_ms, end_ms) applied in order
        self._temp_files = []
        self._preview_offset_s = 0.0
        self._looping = False

        self.player = QMediaPlayer(self)
        self.player.setNotifyInterval(50)
        self.player.positionChanged.connect(self._on_player_position)
        self.player.stateChanged.connect(self._on_player_state)
        self.player.mediaStatusChanged.connect(self._on_media_status)

        self._build_ui()
        self._refresh_envelope()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.view = WaveformEditView(self)
        self.view.on_view_changed = self._sync_scrollbar
        self.view.on_selection_changed = self._update_labels
        layout.addWidget(self.view, stretch=1)

        self.scrollbar = QScrollBar(Qt.Horizontal, self)
        self.scrollbar.valueChanged.connect(self._on_scrollbar)
        layout.addWidget(self.scrollbar)

        self.lbl_info = QLabel(self)
        layout.addWidget(self.lbl_info)

        buttons = QHBoxLayout()
        self.butt_zoom_in = self._button(buttons, "Zoom In", lambda: self.view.zoom(_ZOOM_STEP))
        self.butt_zoom_out = self._button(buttons, "Zoom Out", lambda: self.view.zoom(1 / _ZOOM_STEP))
        self.butt_zoom_fit = self._button(buttons, "Fit", self.view.zoom_fit)
        buttons.addSpacing(20)
        self.butt_play_sel = self._button(buttons, "Play Selection", self._play_selection)
        self.butt_play_all = self._button(buttons, "Play All", self._play_all)
        self.butt_stop = self._button(buttons, "Stop", self._stop_playback)
        buttons.addSpacing(20)
        self.butt_cut = self._button(buttons, "Cut Selection", self._cut_selection)
        self.butt_trim = self._button(buttons, "Trim to Selection", self._trim_to_selection)
        self.butt_undo = self._button(buttons, "Undo", self._undo)
        buttons.addStretch()
        self.butt_save = self._button(buttons, "Save...", self._save)
        self._button(buttons, "Close", self.close)
        layout.addLayout(buttons)

    def _button(self, layout: QHBoxLayout, text: str, slot) -> QPushButton:
        button = QPushButton(text, self)
        button.clicked.connect(slot)
        # Keep keyboard focus on the dialog so the spacebar drives playback, not a button
        button.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(button)
        return button

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self._cut_selection()
        elif event.key() == Qt.Key_Space:
            self._toggle_playback()
        else:
            super().keyPressEvent(event)

    def _toggle_playback(self) -> None:
        """Spacebar transport: pause while playing; when paused, a loop restarts
        from the top of the selection while normal playback resumes in place."""
        state = self.player.state()
        if state == QMediaPlayer.PlayingState:
            self.player.pause()
        elif state == QMediaPlayer.PausedState and not self._looping:
            self.player.play()
        elif self.view.selection:
            self._play_selection()
        else:
            self._play_all()

    # ------------------------------------------------------- waveform state --

    def _refresh_envelope(self) -> None:
        duration = len(self.audio) / 1000.0
        samples = np.array(self.audio.get_array_of_samples(), dtype=np.int32)
        if self.audio.channels > 1:
            samples = samples.reshape((-1, self.audio.channels)).max(axis=1)
        bins = max(1000, int(duration * _ENVELOPE_BINS_PER_SECOND))
        envelope = _max_pool(np.abs(samples), bins)
        peak = envelope.max()
        envelope = envelope / peak if peak > 0 else envelope.astype(float)
        self.view.set_envelope(envelope, duration)
        self._sync_scrollbar()
        self._update_labels()

    def _sync_scrollbar(self) -> None:
        window_ms = int((self.view.view_end - self.view.view_start) * 1000)
        total_ms = int(self.view.duration * 1000)
        self.scrollbar.blockSignals(True)
        self.scrollbar.setRange(0, max(0, total_ms - window_ms))
        self.scrollbar.setPageStep(window_ms)
        self.scrollbar.setValue(int(self.view.view_start * 1000))
        self.scrollbar.blockSignals(False)

    def _on_scrollbar(self, value: int) -> None:
        window = self.view.view_end - self.view.view_start
        self.view.view_start = value / 1000.0
        self.view.view_end = self.view.view_start + window
        self.view.update()

    def _update_labels(self) -> None:
        text = f"Duration: {self._fmt(self.view.duration)}"
        if self.view.selection:
            s, e = self.view.selection
            text += f"    Selection: {self._fmt(s)} - {self._fmt(e)}  ({self._fmt(e - s)})"
        if self.ops:
            text += f"    Edits: {len(self.ops)}"
        self.lbl_info.setText(text)

    @staticmethod
    def _fmt(seconds: float) -> str:
        m, s = divmod(seconds, 60)
        return f"{int(m):02d}:{s:06.3f}"

    # --------------------------------------------------------------- edits --

    def _rebuild_audio(self) -> None:
        audio = self.original
        for op, start_ms, end_ms in self.ops:
            if op == "cut":
                audio = audio[:start_ms] + audio[end_ms:]
            else:  # keep
                audio = audio[start_ms:end_ms]
        self.audio = audio

    def _apply_op(self, op) -> None:
        self._stop_playback()
        self.ops.append(op)
        self._rebuild_audio()
        if len(self.audio) == 0:
            logger.warning("Edit would remove all audio; ignoring")
            self.ops.pop()
            self._rebuild_audio()
            return
        self._refresh_envelope()

    def _cut_selection(self) -> None:
        if not self.view.selection:
            return
        s, e = self.view.selection
        self._apply_op(("cut", int(s * 1000), int(e * 1000)))

    def _trim_to_selection(self) -> None:
        if not self.view.selection:
            return
        s, e = self.view.selection
        self._apply_op(("keep", int(s * 1000), int(e * 1000)))

    def _undo(self) -> None:
        if not self.ops:
            return
        self._stop_playback()
        self.ops.pop()
        self._rebuild_audio()
        self._refresh_envelope()

    # ------------------------------------------------------------- preview --

    def _export_temp(self, segment: AudioSegment) -> str:
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        segment.export(path, format="wav")
        self._temp_files.append(path)
        return path

    def _play_segment(self, segment: AudioSegment, offset_s: float, loop: bool = False) -> None:
        self._stop_playback()
        path = self._export_temp(segment)
        self._preview_offset_s = offset_s
        self._looping = loop
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
        self.player.play()

    def _play_selection(self) -> None:
        if not self.view.selection:
            return
        s, e = self.view.selection
        self._play_segment(self.audio[int(s * 1000):int(e * 1000)], s, loop=True)

    def _play_all(self) -> None:
        self._play_segment(self.audio, 0.0)

    def _stop_playback(self) -> None:
        self._looping = False
        self.player.stop()
        self.player.setMedia(QMediaContent())
        self.view.set_playhead(None)
        self._cleanup_temp_files()

    def _on_media_status(self, status) -> None:
        if status == QMediaPlayer.EndOfMedia and self._looping:
            self.player.setPosition(0)
            self.player.play()

    def _on_player_position(self, position_ms: int) -> None:
        self.view.set_playhead(self._preview_offset_s + position_ms / 1000.0)

    def _on_player_state(self, state) -> None:
        if state == QMediaPlayer.StoppedState:
            self.view.set_playhead(None)

    def _cleanup_temp_files(self) -> None:
        remaining = []
        for path in self._temp_files:
            try:
                os.remove(path)
            except OSError:
                remaining.append(path)  # still held by the player; retried on next cleanup
        self._temp_files = remaining

    # ---------------------------------------------------------------- save --

    def _save(self) -> None:
        if not self.ops:
            QMessageBox.information(self, "Waveform Editor", "No edits to save.")
            return

        box = QMessageBox(self)
        box.setWindowTitle("Save Edited Audio")
        box.setText(f"Save {len(self.ops)} edit(s) to:\n{os.path.basename(self.file_path)}")
        overwrite = box.addButton("Overwrite Original", QMessageBox.AcceptRole)
        copy = box.addButton("Save As Copy", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Cancel)
        box.exec_()

        if box.clickedButton() is overwrite:
            self._write(self.file_path)
        elif box.clickedButton() is copy:
            root, ext = os.path.splitext(self.file_path)
            self._write(f"{root} (edited){ext}")

    def _write(self, target_path: str) -> None:
        self._stop_playback()
        tag_helper = AudioTagHelper()
        tags, cover_art = tag_helper.get_tags_and_cover_art(self.file_path)

        try:
            fd, temp_path = tempfile.mkstemp(suffix=".wav", dir=os.path.dirname(target_path))
            os.close(fd)
            self.audio.export(temp_path, format="wav")
            os.replace(temp_path, target_path)
        except Exception:
            logger.exception(f"Failed to save edited audio to '{target_path}'")
            QMessageBox.warning(self, "Waveform Editor", f"Failed to save:\n{target_path}")
            return

        if tags:
            tag_helper.write_tags(target_path, tags)
        if cover_art:
            tag_helper.write_cover_art(target_path, cover_art)

        logger.info(f"Saved edited audio ({len(self.ops)} edits) to '{target_path}'")
        QMessageBox.information(self, "Waveform Editor", f"Saved:\n{target_path}")
        # Saved edits become the new baseline
        if target_path == self.file_path:
            self.original = self.audio
            self.ops = []
            self._update_labels()

    def closeEvent(self, event):
        self._stop_playback()
        self._cleanup_temp_files()
        super().closeEvent(event)
