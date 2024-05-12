from PyQt5 import uic
from PyQt5.QtCore import Qt, QDir, QModelIndex, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QMainWindow, QFileSystemModel, QTreeView, QPushButton, QFrame
from src.log_config import get_logger

logger = get_logger(__name__)


class DatabaseDialog(QMainWindow):

    def __init__(self):
        super().__init__()
        self.animation = None
        self.ui = uic.loadUi("src\\qt\\database2.ui", self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Create a file system model
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())

        # find the tree view and set the model
        self.tree = self.findChild(QTreeView, "treeView")
        self.tree.setModel(self.model)

        # Set the root index
        # self.tree.setRootIndex(self.model.index(QDir.rootPath()))
        self.tree.setRootIndex(self.model.index(''))  # Set root index to an empty string

        # Connect the doubleClicked signal to the custom slot
        self.tree.doubleClicked.connect(self.on_tree_double_clicked)

        self.go_up_button = self.findChild(QPushButton, "but_goUp")
        self.go_up_button.clicked.connect(self.go_up_one_level)
        
        # find the frame_3 and but_menu
        self.frame_3 = self.findChild(QFrame, "frame_3")
        self.but_menu = self.findChild(QPushButton, "but_menu")
        self.but_menu.clicked.connect(self.animate_frame)

        # Hide the columns for size, type, and last modified
        # self.tree.hideColumn(1)
        # self.tree.hideColumn(2)
        # self.tree.hideColumn(3)

        # Show the tree view
        self.tree.show()

        # self.__display_settings()
        # self.ui.show())

    def closeEvent(self, event):
        logger.info("Database dialog closed.")
        event.accept()

    def accept(self):
        logger.info("Database dialog accepted.")
        self.close()

    def reject(self):
        logger.info("Database dialog rejected.")
        self.close()

    def show(self):
        logger.info("Database dialog shown.")
        super().show()

    def hide(self):
        logger.info("Database dialog hidden.")
        self.ui.hide()

    def on_tree_double_clicked(self, index: QModelIndex):
        """Slot that is called when an item in the tree view is double-clicked."""
        # Set the root index of the tree view to the index of the double-clicked item
        self.tree.setRootIndex(index)

    def go_up_one_level(self):
        """Slot that is called when the "Go Up" button is clicked."""
        # Get the current root index
        current_root_index = self.tree.rootIndex()

        # Get the parent of the current root index
        parent_index = self.model.parent(current_root_index)

        # Set the root index of the tree view to the parent index
        self.tree.setRootIndex(parent_index)

    def animate_frame(self):
        logger.info("Animating frame")
        # Create a QPropertyAnimation object
        self.animation = QPropertyAnimation(self.frame_3, b"minimumWidth")

        # Set the duration of the animation to 300 milliseconds
        self.animation.setDuration(300)

        # Set the start value of the animation to the current width of the frame
        self.animation.setStartValue(self.frame_3.width())

        # Set the end value of the animation to 0
        self.animation.setEndValue(0)

        # Set the easing curve of the animation to OutCubic for a smooth effect
        self.animation.setEasingCurve(QEasingCurve.InOutQuart)

        # Start the animation
        self.animation.start()