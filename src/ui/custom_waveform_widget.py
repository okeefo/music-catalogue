from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen
import file_operations.audio_waveform_analyzer as analyzer

# create logger
from log_config import get_logger
logger = get_logger(__name__)

class WaveformWidget(QWidget):
    """
    Widget to display an audio waveform and playback progress.
    Emits seekRequested(float) when user clicks to seek.
    """
    seekRequested = pyqtSignal(float)  # Emits a float between 0.0 and 1.0
    durationChanged = pyqtSignal(str)  # Signal to send formatted duration

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_path = None
        self.artist = None
        self.title = None
        self._slider = None
        self.waveform = []  # List of floats (normalized 0-1)
        self.progress = 0.0  # 0.0=start, 1.0=end

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

        logger.info("Painting waveform.")
        painter = QPainter(self)
        w, h = self.width(), self.height()
        mid = h // 2
        n = len(self.waveform)
        played_color = QColor("blue")
        unplayed_color = QColor("orange")
        pen = QPen()
        pen.setWidth(1)

        for i, value in enumerate(self.waveform):
            x = int(i * w / n)
            y = int(value * (h // 2))
            pen.setColor(played_color if i / len(self.waveform) < self.progress else unplayed_color)
            painter.setPen(pen)
            painter.drawLine(x, mid - y, x, mid + y)

        # Draw needle
        needle_x = int(self.progress * w)
        needle_x = max(0, min(w - 1, needle_x))
        painter.setPen(QPen(Qt.red, 2))
        painter.drawLine(needle_x, 0, needle_x, h)

    def mousePressEvent(self, event):
        if self.waveform and self.width() > 0:
            pos = event.x() / self.width()
            pos = max(0.0, min(1.0, pos))
            self.seekRequested.emit(pos)

    def set_needle_position(self, pos):
        """
        Set the current needle position (e.g., playback head) in the waveform.
        Args:
            pos (float): Position as a float between 0.0 and 1.0 (relative position).
        """
        self.progress = max(0.0, min(1.0, pos))
        self.update()  # Triggers a repaint to show the new needle position

    def load_waveform_from_file(self, path, artist: str = None, track_name: str = None) -> None:
        # For now, generate random data

        logger.info(f"Loading waveform from file: {path}")
        track_data = analyzer.analyze_audio_file(path, num_samples=5000)


        self.set_waveform(track_data.waveform)
        self.set_duration(track_data.duration)
        self.set_progress(0.0)
        # Optionally, store the path if needed
        self._file_path = path
        self.artist = artist
        self.title = track_name
        logger.info(f"Waveform loaded with {len(self.waveform)} samples from {path}")

    def set_duration(self, duration: float) -> None:
        """ Set the duration of the audio track."""
        self._duration = duration
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