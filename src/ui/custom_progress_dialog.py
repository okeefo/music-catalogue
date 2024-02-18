from PyQt5.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QLabel, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
class ProgressDialog(QDialog):
    def __init__(self, total_files):
        super().__init__()

        self.setWindowTitle("Copying Files")
        self.setWindowIcon(QIcon(":/icons/icons/headphones.svg"))
        self.setWindowModality(Qt.ApplicationModal)

        self.layout = QVBoxLayout()

        self.label = QLabel("Copying Files...")
        self.layout.addWidget(self.label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, total_files)
        self.layout.addWidget(self.progress_bar)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.close)
        self.layout.addWidget(self.cancel_button)

        self.setLayout(self.layout)

        self.canceled = False

    def update_progress(self, value, text):
        self.progress_bar.setValue(value)
        self.label.setText(text)

    def complete(self):
        self.label.setText("Copy complete. Click 'Cancel' to close this dialog.")
        self.progress_bar.setValue(self.progress_bar.maximum())

    def cancel(self):
        self.canceled = True