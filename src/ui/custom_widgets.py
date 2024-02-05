from PyQt5.QtWidgets import QTreeView, QLabel, QVBoxLayout, QDialog
from PyQt5.QtCore import QItemSelectionModel, Qt
from PyQt5.QtGui import QPixmap, QIcon
from mutagen.id3 import APIC
from scanner.audio_tags import PictureTypeDescription


class MyTreeView(QTreeView):
    """A TreeView that allows to select multiple items at once."""

    def mousePressEvent(self, event):
        """Select multiple items on mouse click."""
        index = self.indexAt(event.pos())
        if event.button() == Qt.LeftButton:
            if index.isValid():
                self.clearSelection()
                self.setCurrentIndex(index)
                self.selectionModel().select(index, QItemSelectionModel.Select)
        elif event.button() == Qt.RightButton:
            if index.isValid() and not self.selectionModel().isSelected(index):
                #   self.clearSelection()
                self.setCurrentIndex(index)
                self.selectionModel().select(index, QItemSelectionModel.Select)
        super().mousePressEvent(event)


class ImageLabel(QLabel):

    def __init__(self, pixmap: QPixmap, image: APIC):
        super().__init__()
        self.pixmap = pixmap
        self.image = image

    def resizeEvent(self, event):
        scaled_pixmap = self.pixmap.scaled(self.size(), Qt.KeepAspectRatio)
        self.setPixmap(scaled_pixmap)

    def mouseDoubleClickEvent(self, event):
        # Create a QDialog to show the image
        pop_up_image_dialogue(PictureTypeDescription.get_description(self.image.type), self.pixmap)


def pop_up_image_dialogue(title: str, pixmap: QPixmap) -> None:
    """Set up image dialogue pop up - shown when a user double clicks on an image in the UI."""
    dialog = QDialog()
    dialog.setWindowTitle(title)
    dialog.setLayout(QVBoxLayout())
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # Remove the '?' from the title bar

    # Create a QLabel, set its pixmap to the pixmap of the ImageLabel, and add it to the QDialog
    label = QLabel(dialog)
    label.setPixmap(pixmap)
    label.setScaledContents(True)
    dialog.setWindowIcon(QIcon(":/icons/icons/headphones.svg"))
    dialog.layout().addWidget(label)

    # Show the QDialog
    dialog.exec_()
