from PyQt5.QtWidgets import QProgressDialog
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFont
import qt.resources_rcc
import time
import log_config
from PyQt5.QtWidgets import QApplication


class ProgressBarHelper:

    @staticmethod
    def complete_progress_bar(progress: QProgressDialog, total_files: int) -> None:
        """Complete the progress bar"""
        if progress is None:
            return

        progress.setValue(total_files)
        x = 5
        while x > 0:
            progress.setLabelText(f"Processing complete.\n\n This dialog will close in {x} seconds. \n\n Or press click cancel to exit")
            QApplication.processEvents()
            time.sleep(1)
            x -= 1
            if progress.wasCanceled():
                break
        progress.close()
        QApplication.processEvents()

    @staticmethod
    def get_progress_bar(total_files: int, type: str, min_files: int = 3) -> QProgressDialog:
        """Get a progress bar"""

        if total_files < min_files:
            return None

        progress = QProgressDialog(f"{type} files...", "Cancel", 0, total_files)
        progress.setMaximum(total_files)
        progress.setWindowIcon(QIcon(":/icons/icons/headphones.svg"))
        progress.setWindowTitle(f"{type} Files")
        progress.setLabelText(f"{type} Files...")
        progress.setCancelButtonText("Cancel")
        progress.setWindowModality(Qt.ApplicationModal)
        progress.setWindowFlags(progress.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        progress.setAutoClose(False)
        progress.setAutoReset(False)

        font = QFont()
        font.setPointSize(10)
        progress.setFont(font)

        progress.show()
        QApplication.processEvents()
        return progress

    @staticmethod
    def update_progress_bar_value(progress: QProgressDialog, value: int) -> None:
        """Update the progress bar value"""

        if progress:
            progress.setValue(value)
            QApplication.processEvents()

    @staticmethod
    def update_progress_bar_text(progress: QProgressDialog, message: str) -> None:
        """Update the progress bar text"""

        if progress:
            progress.setLabelText(f"\n\n{message}\n")
            QApplication.processEvents()



    @staticmethod
    def update_progress_bar(progress: QProgressDialog, message: str, value: int) -> None:
        """Update the progress bar text"""

        if progress:
            progress.setLabelText(f"\n\n{message}\n")
            progress.setValue(value)
            QApplication.processEvents()

    @staticmethod
    def user_has_cancelled(progress: QProgressDialog) -> bool:
        """Check if the user has cancelled the progress bar"""

        return False if progress is None else progress.wasCanceled()
