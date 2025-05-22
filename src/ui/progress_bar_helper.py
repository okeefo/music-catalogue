from PyQt5.QtWidgets import QProgressDialog
from PyQt5.QtWidgets import QMessageBox, QProgressDialog,QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFont
import qt.resources_rcc
import time
import log_config
from PyQt5.QtWidgets import QApplication


class ProgressBarHelper:

    progress_bar: QProgressDialog = None
    counter: int = 0
    max: int = 0

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
        self.progress_bar.setFixedWidth(600)
        self.progress_bar.setFixedHeight(200)
        self.max = total_files

        self.progress_bar.setValue(0)# Find the QLabel in the children of the QProgressDialog
        label = next((child for child in self.progress_bar.children() if isinstance(child, QLabel)), None)

        # Set word wrap on the QLabel
        if label is not None:
            label.setWordWrap(True)
    
        font = QFont()
        font.setPointSize(10)
        self.progress_bar.setFont(font)

        self.progress_bar.show()
        QApplication.processEvents()

    def complete_progress_bar(self) -> None:
        """Complete the progress bar"""
        if self.progress_bar is None:
            return

        self.progress_bar.setValue(self.max)
        x = 2
        while x > 0:
            self.progress_bar.setLabelText(f"Processing complete.\n This dialog will close in {x} seconds. \n\n Or press click cancel to exit")
            QApplication.processEvents()
            time.sleep(1)
            x -= 1
            if self.progress_bar.wasCanceled():
                break
        self.progress_bar.close()
        QApplication.processEvents()

    def increment(self) -> None:
        """Update the progress bar value"""

        if self.progress_bar:
            self.counter += 1
            self.progress_bar.setValue(self.counter)
            QApplication.processEvents()

    def update_progress_bar_text(self, message: str) -> None:
        """Update the progress bar text"""

        if self.progress_bar:
            self.progress_bar.setLabelText(f"\n{message}")
            QApplication.processEvents()

    def increment_with_message(self, message: str) -> None:
        """Update the progress bar text and value"""

        if self.progress_bar:
            self.update_progress_bar_text(f"\n\{message}")
            self.increment()

    def user_has_cancelled(self) -> bool:
        """Check if the user has cancelled the progress bar"""

        return False if self.progress_bar is None else self.progress_bar.wasCanceled()
