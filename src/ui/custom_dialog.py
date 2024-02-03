from PyQt5.QtCore import Qt
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5.QtGui import QPixmap


class CustomDialog(QDialog):
    """Custom Dialog"""

    def __init__(self, message, hide_remember=False, parent=None):
        """
        Initializes a custom dialog with the given message, optional hide_remember flag, and parent widget.

        Args:
            message (str): The message to display in the dialog.
            hide_remember (bool, optional): Flag to hide the remember choice checkbox. Defaults to False.
            parent (QWidget, optional): The parent widget of the dialog. Defaults to None.
        """

        super(CustomDialog, self).__init__(parent)

        uic.loadUi("src\\qt\\custom_dialog.ui", self)

        self.label_message.setText(message)

        self.button_yes.clicked.connect(lambda: self.done(QMessageBox.Yes))
        self.button_no.clicked.connect(lambda: self.done(QMessageBox.No))
        self.button_cancel.clicked.connect(self.reject)
        if hide_remember:
            self.checkbox_remember.hide()

        self.adjustSize()
        pixmap = QPixmap(":/icons/icons/alert-triangle.svg")
        pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label_icon.setPixmap(pixmap)

    def remember_choice(self):
        """
        Returns the state of the remember choice checkbox.

        Returns:
            bool: True if the remember choice checkbox is checked, False otherwise.
        """
        return self.checkbox_remember.isChecked()

    def show_dialog(self) -> tuple[int, bool]:
        """
        Executes the custom dialog and returns the result and the state of the remember choice checkbox.

        Returns:
            tuple[int, bool]: A tuple containing the result of the dialog and the state of the remember choice checkbox.
            dialog result: 0-cancel, 1-no, 2-yes
            remember choice: True or False
        """
        return super(CustomDialog, self).exec_(), self.remember_choice()
