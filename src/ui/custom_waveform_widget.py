from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtWidgets import QWidget

import file_operations.audio_waveform_analyzer as analyzer

# create logger
from log_config import get_logger

logger = get_logger(__name__)


class WaveformWidget(QWidget):
    def load_waveform_from_db_or_file(self, file_id, file_path, db_path, num_samples=2500):
        """
        Try to load waveform data from the DB. If not found, load from file and optionally cache to DB.
        """
        import json
        from db.db_writer import MusicCatalogDBWriter

        logger.info(f"Trying to load waveform from DB for file_id={file_id}")
        db_writer = MusicCatalogDBWriter(db_path)
        db_writer.ensure_track_meta_data_table()
        cursor = db_writer.connection.cursor()
        cursor.execute("SELECT waveform_data FROM track_meta_data WHERE id=?", (file_id,))
        row = cursor.fetchone()
        if row and row[0]:
            try:
                waveform = json.loads(row[0].decode("utf-8") if isinstance(row[0], bytes) else row[0])
                logger.info(f"Loaded waveform from DB for file_id={file_id}")
                # You may want to also fetch duration if you store it
                self.set_waveform(waveform)
                # Duration fallback: analyze file for duration only if needed
                from file_operations.audio_waveform_analyzer import analyze_audio_file

                result = analyze_audio_file(file_path, num_samples=10)  # Fast, low-res for duration
                duration = result.duration if result else 0.0
                self.set_duration(duration)
                self.set_progress(0.0)
                self.track_path = file_path
                self.waveform_loaded = True
                if self.callback_on_loaded:
                    self.callback_on_loaded(duration)
                cursor.close()
                db_writer.close()
                return
            except Exception as e:
                logger.warning(f"Failed to load waveform from DB: {e}")
        cursor.close()
        db_writer.close()
        # Fallback: load from file as before
        self.load_waveform_from_file(file_path)

    def load_waveform_from_db_or_file(self, file_id, file_path, db_path, num_samples=2500):
        """
        Try to load waveform data from the DB. If not found, load from file and optionally cache to DB.
        """
        import json
        from db.db_reader import MusicCatalogDB_2

        logger.info(f"Trying to load waveform from DB for file_id={file_id}")
        db_reader = MusicCatalogDB_2(db_path)
        raw_waveform = db_reader.get_waveform_data(file_id)
        if raw_waveform:
            try:
                waveform = json.loads(raw_waveform.decode("utf-8") if isinstance(raw_waveform, bytes) else raw_waveform)
                logger.info(f"Loaded waveform from DB for file_id={file_id}")
                self.set_waveform(waveform)
                # Duration fallback: analyze file for duration only if needed
                from file_operations.audio_waveform_analyzer import analyze_audio_file

                result = analyze_audio_file(file_path, num_samples=10)  # Fast, low-res for duration
                duration = result.duration if result else 0.0
                self.set_duration(duration)
                self.set_progress(0.0)
                self.track_path = file_path
                self.waveform_loaded = True
                if self.callback_on_loaded:
                    self.callback_on_loaded(duration)
                db_reader.close()
                return
            except Exception as e:
                logger.warning(f"Failed to load waveform from DB: {e}")
        db_reader.close()
        # Fallback: load from file as before
        self.load_waveform_from_file(file_path)

    """
    Widget to display an audio waveform and playback progress.
    Emits seekRequested(float) when user clicks to seek.
    """
    seekRequested = pyqtSignal(float)  # Emits a float between 0.0 and 1.0
    durationChanged = pyqtSignal(str)  # Signal to send formatted duration

    def __init__(self, parent=None):
        super().__init__(parent)
        self.track_path = None
        self._slider = None
        self.waveform = []  # List of floats (normalized 0-1)
        self.progress = 0.0  # 0.0=start, 1.0=end
        self.waveform_loaded = False
        self.duration = 0.0  # Duration in seconds
        self.player = None  # Placeholder for media player instance
        self.callback_on_seeked = None  # Callback when user seeks
        self.callback_on_loaded = None  # Callback when waveform is loaded

    def set_callback_on_seeked(self, callback):
        """
        Set a callback function to be called when the user seeks in the waveform.
        Args:
            callback (callable): Function to call with the new position (float between 0.0 and 1.0).
        """
        self.callback_on_seeked = callback

    def set_callback_on_loaded(self, callback):
        """
        Set a callback function to be called when the waveform is loaded.
        Args:
            callback (callable): Function to call with the waveform data and duration.
        """
        self.callback_on_loaded = callback

    def set_slider(self, slider):
        self._slider = slider

    def set_waveform(self, data):
        logger.info("Setting waveform data.")
        self.waveform = data
        self.update()

    def set_progress(self, progress):
        self.progress = progress
        self.update()

    def get_length(self):
        """Return the number of samples in the waveform."""
        return len(self.waveform)

    def paintEvent(self, event):
        if not self.waveform:
            return
        painter = QPainter(self)
        w, h = self.width(), self.height()
        mid = h // 2
        played_color = QColor("blue")
        unplayed_color = QColor("orange")
        pen = QPen()
        pen.setWidth(1)

        # Use fast downsampling for display
        import numpy as np

        display_waveform = analyzer.get_display_waveform(np.array(self.waveform), w)
        n = len(display_waveform)

        for i, value in enumerate(display_waveform):
            x = i
            y = int(value * (h // 2))
            pen.setColor(played_color if (i / n) < self.progress else unplayed_color)
            painter.setPen(pen)
            painter.drawLine(x, mid - y, x, mid + y)

        # Draw needle
        needle_x = int(self.progress * w)
        needle_x = max(0, min(w - 1, needle_x))
        painter.setPen(QPen(Qt.red, 2))
        painter.drawLine(needle_x, 0, needle_x, h)

    def set_needle_position(self, pos):
        """
        Set the current needle position (e.g., playback head) in the waveform.
        Args:
            pos (float): Position as a float between 0.0 and 1.0 (relative position).
        """
        self.progress = max(0.0, min(1.0, pos))
        self.update()  # Triggers a repaint to show the new needle position

    def load_waveform_from_file(self, path) -> None:
        logger.info(f"Loading waveform from file asynchronously: {path}")
        self.worker = WaveformWorker(path)
        self.worker.waveformLoaded.connect(lambda waveform, duration: self.on_waveform_loaded(waveform, duration, path))
        self.worker.start()

    def on_waveform_loaded(self, waveform, duration, path):

        self.set_waveform(waveform)
        self.set_duration(duration)
        self.set_progress(0.0)
        self.track_path = path
        self.waveform_loaded = True
        self.callback_on_loaded(duration)

        logger.info(f"Waveform loaded with {len(self.waveform)} samples from {path}")

    def set_duration(self, duration: float) -> None:
        """Set the duration of the audio track."""
        self.duration = duration
        formatted = self._format_duration(duration)
        self.durationChanged.emit(formatted)
        logger.info(f"Duration set to {formatted}")

    def _format_duration(self, duration: float) -> str:
        # Assuming duration is in seconds.
        total_sec = int(duration)
        ms = int((duration - total_sec) * 100)
        h = total_sec // 3600
        m = (total_sec % 3600) // 60
        s = total_sec % 60
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:02d}"

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Get x position relative to the widget width
            x = event.pos().x()
            width = self.width()
            rel_pos = x / width if width else 0.0

            # Update the needle position on the waveform
            self.set_needle_position(rel_pos)

            # Calculate new media position in milliseconds
            total_ms = self.duration * 1000
            new_position = int(rel_pos * total_ms)
            # Call a callback or directly update the media player if available
            self.callback_on_seeked(new_position)


class WaveformWorker(QThread):
    waveformLoaded = pyqtSignal(object, float)  # waveform data and duration

    def __init__(self, path, num_samples=2500):
        super().__init__()
        self.path = path
        self.num_samples = num_samples

    def run(self):
        track_data = analyzer.analyze_audio_file(self.path, num_samples=self.num_samples)
        self.waveformLoaded.emit(track_data.waveform, track_data.duration)
