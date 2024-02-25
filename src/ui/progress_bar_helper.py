from PyQt5.QtWidgets import QProgressDialog
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFont
import qt.resources_rcc
import time
import log_config
from PyQt5.QtWidgets import QApplication


class ProgressBarHelper:

    progress_bar: QProgressDialog = None

    def __init__(self, total_files: int, type: str, min_files: int = 3) -> QProgressDialog:
        """Get a progress bar"""

        if total_files < min_files:
            return None

        self.progress_bar = QProgressDialog(f"{type} files...", "Cancel", 0, total_files)
        self.progress_bar.setMaximum(total_files)
        self.progress_bar.setWindowIcon(QIcon(":/icons/icons/headphones.svg"))
        self.progress_bar.setWindowTitle(f"{type} Files")
        self.progress_bar.setLabelText(f"{type} Files...")
        self.progress_bar.setCancelButtonText("Cancel")
        self.progress_bar.setWindowModality(Qt.ApplicationModal)
        self.progress_bar.setWindowFlags(self.progress_bar.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.progress_bar.setAutoClose(False)
        self.progress_bar.setAutoReset(False)

        font = QFont()
        font.setPointSize(10)
        self.progress_bar.setFont(font)

        self.progress_bar.show()
        QApplication.processEvents()

    def complete_progress_bar(self, total_files: int) -> None:
        """Complete the progress bar"""
        if self.progress_bar is None:
            return

        self.progress_bar.setValue(total_files)
        x = 5
        while x > 0:
            self.progress_bar.setLabelText(f"Processing complete.\n\n This dialog will close in {x} seconds. \n\n Or press click cancel to exit")
            QApplication.processEvents()
            time.sleep(1)
            x -= 1
            if self.progress_bar.wasCanceled():
                break
        self.progress_bar.close()
        QApplication.processEvents()

    def update_progress_bar_value(self, value: int) -> None:
        """Update the progress bar value"""

        if self.progress_bar:
            self.progress_bar.setValue(value)
            QApplication.processEvents()

    def update_progress_bar_text(self, message: str) -> None:
        """Update the progress bar text"""

        if self.progress_bar:
            self.progress_bar.setLabelText(f"\n\n{message}\n")
            QApplication.processEvents()

    def update_progress_bar(self, message: str, value: int) -> None:
        """Update the progress bar text and value"""

        if self.progress_bar:
            self.progress_bar.setLabelText(f"\n\n{message}\n")
            self.progress_bar.setValue(value)
            QApplication.processEvents()

    def user_has_cancelled(self) -> bool:
        """Check if the user has cancelled the progress bar"""

        return False if self.progress_bar is None else self.progress_bar.wasCanceled()
