from PyQt5.QtWidgets import QLineEdit
import os


class MyLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Connect the returnPressed signal to the normalize_path slot
        self.returnPressed.connect(self.normalize_path)

    def normalize_path(self):
        # Get the text from the QLineEdit
        path = self.text()

        # Normalize the path
        normalized_path = os.path.normpath(path)

        # Set the text of the QLineEdit to the normalized path
        self.setText(normalized_path)
