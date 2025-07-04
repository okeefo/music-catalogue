from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtCore import pyqtSignal
import os
from log_config import get_logger

# create logger
logger = get_logger(__name__)

class MyLineEdit(QLineEdit):
    
    searchRequested = pyqtSignal(str)
     
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Connect the returnPressed signal to the normalize_path slot
        self.returnPressed.connect(self.on_return_pressed)
        self.textChanged.connect(self.on_text_changed)


    def normalize_path(self):
        # Get the text from the QLineEdit
        path = self.text()

        # Normalize the path
        normalized_path = os.path.normpath(path)

        # Set the text of the QLineEdit to the normalized path
        self.setText(normalized_path)
    
    def on_return_pressed(self):

        if self.text().startswith(":"):
            # Emit search signal with the query (without the colon)
            self.searchRequested.emit(self.text()[1:])
        else:
            self.normalize_path()

    def on_text_changed(self, text):
        return
        if text.startswith(":"):
            # Optionally, emit search as-you-type
            self.searchRequested.emit(text[1:])