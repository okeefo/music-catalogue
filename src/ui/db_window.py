import os

from PyQt5 import uic
from PyQt5.QtCore import Qt, QDir, QModelIndex
from PyQt5.QtWidgets import QMainWindow, QFileSystemModel, QPushButton, QFrame, QGroupBox, QLabel, QHeaderView, QCompleter, QMessageBox
from qtpy import QtGui
from ui.custom_line_edit import MyLineEdit
from ui.custom_tree_view import MyTreeView

from log_config import get_logger

logger = get_logger(__name__)


class DatabaseWindow(QMainWindow):
    label_map = {}
    label_a_map = {}

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = super(DatabaseWindow, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def show(self):
        super(DatabaseWindow, self).show()

    def __init__(self, path: str, parent=None):
        super(DatabaseWindow, self).__init__()
        self.icon_right = None
        self.icon_left = None
        self.frame_3 = None
        self.but_frame3_hide = None
        self.go_up_button = None
        self.model = None
        self.tree = None
        self.ui = None
        self.animation = None

        self.__setup_ui()
        self.__setup_model()
        self.__setup_line_edit(path)
        self.__setup_tree_view(path)
        self.__setup_buttons()
        self.__populate_label_maps()
        self.clear_track_labels()
        self.__setup_icons()
        self.__set_chevron_icon()

    def __setup_line_edit(self, path : str) -> None:
        # Set the completer for the MyLineEdit
        self.path_info_bar = self.findChild(MyLineEdit, "path_source")
        completer = QCompleter()
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setModel(self.model)
        self.path_info_bar.setCompleter(completer)
        self.path_info_bar.returnPressed.connect(lambda: self.on_path_info_bar_return_pressed(self.tree, self.path_info_bar))
        self.path_info_bar.setText(path)

    def on_path_info_bar_return_pressed(self, tree_view: MyTreeView, path_info_bar: MyLineEdit) -> None:
        """Handles the directory when the return key is pressed. Returns: None"""

        if not os.path.isdir(path_info_bar.text()):
            QMessageBox.critical(self, "Error", "Directory doesn't exist")
            path_info_bar.setText(tree_view.get_root_dir())
        else:
            tree_view.change_dir(os.path.normpath(path_info_bar.text()))

    def __setup_ui(self):
        self.ui = uic.loadUi(os.path.join("src", "qt", "database.ui"), self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def __setup_model(self):
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())

    def __setup_tree_view(self, path: str = QDir.rootPath()):
        self.tree = self.findChild(MyTreeView, "treeView")
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(path))
        header = self.tree.header()  # get the header of the tree view
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        treeview = self.tree
        treeview.set_double_click_handler(lambda index, tree, info_bar: self.on_tree_double_clicked(index, self.tree, self.path_info_bar))
        self.tree.show()

    def __setup_buttons(self):
        self.go_up_button = self.findChild(QPushButton, "but_goUp")
        self.go_up_button.clicked.connect(lambda: self.go_up_one_level(self.path_info_bar))

        self.frame_3 = self.findChild(QFrame, "frame_3")
        self.but_frame3_hide = self.findChild(QPushButton, "but_frame3_hide")
        self.but_frame3_hide.clicked.connect(self.show_hide_frame_3)

    def __setup_icons(self):
        self.icon_left = QtGui.QIcon("/src/qt/icons/chevrons-left.svg")
        self.icon_right = QtGui.QIcon("/src/qt/icons/chevrons-right.svg")

    @staticmethod
    def on_tree_double_clicked(index: QModelIndex, tree_view: MyTreeView, path_bar: MyLineEdit) -> None:
        """Change the root index of the tree view to the index of the double-clicked item."""
        tree_view.on_tree_double_clicked(index)
        path_bar.setText(tree_view.get_root_dir())

    def show_hide_frame_3(self):
        """Animate the frame and change the icon."""
        logger.info("Animating frame")
        self.frame_3.setVisible(self.frame_3.isHidden())
        self.__set_chevron_icon()

    def __set_chevron_icon(self):
        icon = self.icon_right if self.frame_3.isHidden() else self.icon_left
        self.but_frame3_hide.setIcon(icon)

    def __populate_label_maps(self):
        logger.info("Populating label maps")
        gbox = self.findChild(QGroupBox, 'gbox_track_labels')
        if not gbox:
            return None

        for child in gbox.children():
            if isinstance(child, QLabel):
                if child.objectName().endswith('_a'):
                    self.label_a_map[child.objectName()] = child.minimumWidth()
                else:
                    self.label_map[child.objectName()] = child.minimumWidth()

        logger.info(f"Label map: {self.label_map}")
        logger.info(f"Label_a map: {self.label_a_map}")

    def go_up_one_level(self, path_bar: MyLineEdit) -> None:
        """Slot that is called when the "Go Up" button is clicked."""
        self.tree.go_up_one_dir_level()
        path_bar.setText(self.tree.get_root_dir())

    def clear_track_labels(self) -> None:
        """Clear the track labels."""
        logger.info("Clearing track labels")
        for key in self.label_a_map.keys():
            label = self.findChild(QLabel, key)
            label.setText("")

    # lbl_media
    # lbl_album
    # lbl_media_a
    # lbl_track_a
    # lbl_style
    # lbl_date_a
    # lbl_artist_a
    # lbl_cat
    # lbl_disc_a
    # lbl_country
    # lbl_title_a
    # lbl_cat_a
    # lbl_website
    # lbl_title
    # lbl_date
    # lbl_style_a
    # lbl_aartist
    # lbl_label
    # lbl_track
    # lbl_side
    # lbl_side_a
    # lbl_artist
    # lbl_country_a
    # lbl_website_a
    # lbl_genre_a
    # lbl_album_a
    # lbl_label_a
    # lbl_disc
    # lbl_aartist_a
    # lbl_genre_a
