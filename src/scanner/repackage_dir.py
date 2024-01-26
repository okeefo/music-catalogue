import os
import shutil
import filecmp

from tkinter import messagebox
import scanner.audio_tags as AudioTags
from PyQt5.QtCore import Qt
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QApplication
from PyQt5.QtGui import QPixmap


class CustomDialog(QDialog):
    def __init__(self, message, parent=None):
        super(CustomDialog, self).__init__(parent)
        uic.loadUi("src\\qt\\custom_dialog.ui", self)

        self.label_message.setText(message)

        self.button_yes.clicked.connect(lambda: self.done(2))
        self.button_no.clicked.connect(lambda: self.done(1))
        self.button_cancel.clicked.connect(self.reject)
        self.adjustSize()
        pixmap = QPixmap(":/icons/icons/alert-triangle.svg")
        pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label_icon.setPixmap(pixmap)

    def remember_choice(self):
        return self.checkbox_remember.isChecked()

    def exec_(self):
        result = super(CustomDialog, self).exec_()
        return result, self.remember_choice()


def repackageByLabel(source_dir, target_dir):
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    remember_choice = None
    user_choice = None
    audio_tags = AudioTags.AudioTags()
    for file in os.listdir(source_dir):
        source_file = os.path.join(source_dir, file)

        if audio_tags.isSupported(source_file):
            tags = audio_tags.get_tags(source_file)
            if tags:
                label = tags.get("LABEL", ["Unknown Publisher"])[0]
                target_subdir = os.path.join(target_dir, label)

                if not os.path.exists(target_subdir):
                    os.mkdir(target_subdir)

                target_file = os.path.join(target_subdir, file)
                if not os.path.exists(target_file) or (remember_choice and user_choice == 2):
                    shutil.move(source_file, target_file)
                else:
                    if not remember_choice:
                        message = f"The file:\n'{file}'\nalready exists in the target directory\n'{label}'. \n\nDo you want to overwrite it?"
                        dialog = CustomDialog(message)
                        user_choice, remember_choice = dialog.exec_()

                    if user_choice == QDialog.Rejected:
                        break

                    if user_choice == 2:
                        shutil.move(source_file, target_file)
            else:
                print("Skipping - no tags" + source_file)
        else:
            print("Skipping - file not supported" + source_file)

    print("Repacking Done")
