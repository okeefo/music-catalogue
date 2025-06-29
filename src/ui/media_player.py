from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import (
    QWidget, QSlider, QPushButton, QLabel, QMessageBox,
)

# Set logger instance
from log_config import get_logger
from ui.custom_waveform_widget import WaveformWidget

logger = get_logger(__name__)

INVALID_MEDIA_ERROR_MSG = 'Failed to play the media file. You might need to install the K-Lite Codec Pack. You can download it from the official website:<br><a href="https://www.codecguide.com/download_kl.htm">https://www.codecguide.com/download_kl.htm</a>'
class MediaPlayerController(QWidget):
    # create a placeholder for the Parent - which is the main window
    parent = None

    def __init__(
            self,
            parent,
            slider: QSlider,
            waveform_widget: WaveformWidget,
            butt_play: QPushButton,
            butt_stop: QPushButton,
            lbl_current: QLabel,
            lbl_duration: QLabel,
            lbl_info: QLabel,
            wdgt_cover_art: QWidget
    ) -> None:
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("MediaPlayerController")

        self.lbl_current = lbl_current
        self.lbl_duration = lbl_duration
        self.wdgt_cover_art = wdgt_cover_art
        self.info_bar = lbl_info
        self.info_bar.setText("No audio file loaded")

        self._user_is_sliding = None

        self.__setup_icons()
        self.__setup_media_player()
        self.__setup_waveform_widget(waveform_widget)
        self.__setup_slider(slider)
        self.__setup_action_buttons(butt_play, butt_stop)

    def __setup_icons(self) -> None:
        """Set up the icons. Returns: None"""

        self.icon_play_off = QIcon("src/qt/icons/media/Farm-Fresh_control_play.png")
        self.icon_play_on = QIcon("src/qt/icons/media/Fatcow-Farm-Fresh-Control-play-blue.32.png")
        self.icon_stop_off = QIcon("src/qt/icons/media/Fatcow-Farm-Fresh-Control-stop.32.png")
        self.icon_stop_on = QIcon("src/qt/icons/media/Fatcow-Farm-Fresh-Control-stop-blue.32.png")
        self.icon_pause = QIcon("src/qt/icons/media/Fatcow-Farm-Fresh-Control-pause-blue.32.png")

    def __setup_action_buttons(self, butt_play: QPushButton, butt_stop: QPushButton) -> None:
        """Set up the action buttons. Returns: None"""

        self.butt_play = butt_play
        self.butt_play.setIcon(self.icon_play_off)
        self.butt_play.clicked.connect(lambda: self.on_play_button_clicked())
        self.butt_play.setToolTip("Play the loaded audio file")
        self.butt_play.setToolTipDuration(1000)
        # self.but_db.setShortcut("Ctrl+D")

        self.butt_stop = butt_stop
        self.butt_stop.setIcon(self.icon_stop_off)
        self.butt_stop.clicked.connect(lambda: self.on_stop_button_clicked())
        self.butt_stop.setToolTip("Stop playing the loaded audio file")
        self.butt_stop.setToolTipDuration(1000)
        # self.but_db.setShortcut("Ctrl+D")

    def __setup_media_player(self) -> None:
        """Sets up the media player. Returns: None"""
        self.player = QMediaPlayer(self)
        self.player.setNotifyInterval(50)
        self.player.mediaStatusChanged.connect(self.handle_media_status_changed)  # type: ignore[attr-defined]
        self.player.positionChanged.connect(self.on_player_position_changed)  # type: ignore[attr-defined]

    def __setup_slider(self, slider: QSlider) -> None:
        """Sets up the slider for the waveform widget. Returns: None"""
        self.slider = slider
        self.slider.setMinimum(0)
        self.slider.setMaximum(1000)  # Increase for finer granularity
        # self.slider.setSingleStep(1)  # Smallest possible step
        self.waveform_widget.set_slider(self.slider)
        self.slider.valueChanged.connect(self.on_slider_moved)
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)

    def __setup_waveform_widget(self, wave_widget: WaveformWidget) -> None:
        """Sets up the waveform widget. Returns: None"""
        self.waveform_widget = wave_widget
        self.waveform_widget.durationChanged.connect(self.update_duration_label)
        self.waveform_widget.set_player(self.player)

    def on_slider_pressed(self) -> None:
        self._user_is_sliding = True

    def on_slider_released(self) -> None:
        self._user_is_sliding = False
        # Compute relative position from slider value and seek media player
        max_val = self.slider.maximum()
        rel_pos = self.slider.value() / max_val if max_val else 0.0
        total_ms = self.waveform_widget.duration * 1000
        new_position = int(rel_pos * total_ms)
        self.player.setPosition(new_position)

    def update_duration_label(self, formatted_duration: str) -> None:
        self.lbl_duration.setText(formatted_duration)

    def on_slider_moved(self, value):
        # Map slider value to waveform position
        max_val = self.slider.maximum()
        rel_pos = value / max_val if max_val else 0.0
        self.waveform_widget.set_needle_position(rel_pos)

        # Calculate current time based on the waveform widget duration
        duration = self.waveform_widget.duration  # duration in seconds
        current_time = rel_pos * duration
        self.lbl_current.setText(self.format_time(current_time))

    def load_media(self, path: str, artist: str, title: str) -> None:
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
        self.waveform_widget.load_waveform_from_file(path, artist, title)
        self.on_stop_button_clicked()

    def on_player_position_changed(self, position: int) -> None:
        if self._user_is_sliding:
            return
        # Convert duration (seconds) to ms before calculating progress
        total_ms = self.waveform_widget.duration * 1000
        if total_ms == 0:
            return
        rel_pos = min(max(position / total_ms, 0.0), 1.0)
        self.waveform_widget.set_needle_position(rel_pos)
        self.slider.blockSignals(True)
        self.slider.setValue(int(rel_pos * self.slider.maximum()))
        self.slider.blockSignals(False)
        # Update current time label
        current_seconds = position / 1000.0
        self.lbl_current.setText(self.format_time(current_seconds))

    def on_play_button_clicked(self) -> None:
        if not self.waveform_widget.waveform_loaded:
            return

        # if the stop icon is off turn it on
        self.butt_stop.setIcon(self.icon_stop_on)

        # Assuming the waveform widget has a loaded audio file and self.player is set up with the media
        logger.info("Play button clicked")
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.butt_play.setIcon(self.icon_play_on)
            self.info_bar.setText(f"Paused: {self.waveform_widget.artist} - {self.waveform_widget.title}")
            return

        logger.info(f"Loading media from waveform widget file: {self.waveform_widget.track_path}")

        self.player.play()
        # When audio starts playing, show blue pause icon.
        self.butt_play.setIcon(self.icon_pause)
        self.info_bar.setText(f"Playing {self.waveform_widget.artist} - {self.waveform_widget.title}")


    def on_stop_button_clicked(self) -> None:
        # Assuming the waveform widget has a loaded audio file and self.player is set up with the media
        logger.info("Play button clicked")

        # Load the media from the waveform widget file if needed, e.g.
        self.player.stop()
        self.butt_play.setIcon(self.icon_play_off)
        self.butt_stop.setIcon(self.icon_stop_off)
        self.info_bar.setText(f"{self.waveform_widget.artist} - {self.waveform_widget.title}")

    @staticmethod
    def handle_media_status_changed(status):
        """Handles the media status changed event."""
        if status == QMediaPlayer.InvalidMedia:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("Error")
            msg_box.setText(INVALID_MEDIA_ERROR_MSG)
            msg_box.setTextFormat(Qt.RichText)
            msg_box.exec()

    @staticmethod
    def format_time(seconds: float) -> str:
        total_sec = int(seconds)
        ms = int((seconds - total_sec) * 100)
        h = total_sec // 3600
        m = (total_sec % 3600) // 60
        s = total_sec % 60
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:02d}"
