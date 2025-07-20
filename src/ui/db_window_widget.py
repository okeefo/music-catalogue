import os

from PyQt5.QtCore import Qt, QDir, QModelIndex
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QIcon, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QFileSystemModel, QPushButton, QFrame, QGroupBox, QLabel, QHeaderView, QCompleter, QMessageBox, QWidget, QTableView

from db.music_db import MusicCatalogDB
from log_config import get_logger
from ui.custom_line_edit import MyLineEdit
from ui.custom_tree_view import MyTreeView

logger = get_logger(__name__)


class DatabaseWidget(QWidget):
    label_map = {}
    label_a_map = {}

    _instance = None

    def __init__(self, parent=None):
        super().__init__(parent)

        # self.but_db_goUp = None
        # self.model = None
        # self.tree = None
        # self.ui = None
        # self.animation = None
        self.icon_left = QIcon("src/qt/icons/chevrons-left.svg")
        self.icon_right = QIcon("src/qt/icons/chevrons-right.svg")
        self.folder_icon = QIcon(":/icons/icons/folder.svg")
        self.media_icon = QIcon(":/media/icons/media/Oxygen-Icons.org-Oxygen-Actions-media-record.256.png")

        self.music_db = MusicCatalogDB("H:/_-__Tagged__-_/Vinyl Collection/keefy.db")
        self.music_db.load()

    def setup_ui(self, path: str):
        """Set up the UI components for the database widget."""
        # get self

        self.setWindowFlags(Qt.WindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint))
        self.__setup_model()
        self.__setup_line_edit(path)
        self.__setup_tree_view(path)
        self.__setup_buttons()
        self.__populate_label_maps()
        self.clear_track_labels()

        self.__set_chevron_icon()
        self.__setup_data_views()
        self.__populate_view_db_labels()
        self.__populate_view_db_tracks()

    def __setup_line_edit(self, path: str) -> None:
        # Set the completer for the MyLineEdit
        self.path_info_bar = self.findChild(MyLineEdit, "db_path_root")
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

    def __setup_model(self):
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())

    def __setup_tree_view(self, path: str = QDir.rootPath()):
        self.tree = self.findChild(MyTreeView, "treeView_db")
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(path))
        header = self.tree.header()  # get the header of the tree view
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        treeview = self.tree
        treeview.set_double_click_handler(lambda index, tree, info_bar: self.on_tree_double_clicked(index, self.tree, self.path_info_bar))
        self.tree.show()

    def __setup_buttons(self):
        self.but_db_goUp = self.findChild(QPushButton, "but_db_goUp")
        self.but_db_goUp.clicked.connect(lambda: self.go_up_one_level(self.path_info_bar))

        self.db_side_frame = self.findChild(QFrame, "db_side_frame")
        self.but_db_frame_hide = self.findChild(QPushButton, "but_db_frame_hide")
        self.but_db_frame_hide.clicked.connect(self.show_hide_db_side_frame)

    def __setup_data_views(self):
        """Set up the tree views for releases."""
        self.view_db_labels = self.findChild(QTableView, "view_db_labels")
        self.view_db_labels.setModel(QStandardItemModel())
        monospace = QFont("Source Code Pro", 8)  # change the size as desired
        self.view_db_labels.setFont(monospace)
        self.view_db_labels.setAlternatingRowColors(True)
        self.view_db_labels.verticalHeader().setVisible(False)

        self.view_db_tracks = self.findChild(QTableView, "view_db_tracks")
        self.view_db_tracks.setModel(QStandardItemModel())
        self.view_db_tracks.setFont(monospace)

    @staticmethod
    def on_tree_double_clicked(index: QModelIndex, tree_view: MyTreeView, path_bar: MyLineEdit) -> None:
        """Change the root index of the tree view to the index of the double-clicked item."""
        tree_view.on_tree_double_clicked(index)
        path_bar.setText(tree_view.get_root_dir())

    def show_hide_db_side_frame(self):
        """Animate the frame and change the icon."""
        logger.info("Animating frame")
        self.db_side_frame.setVisible(self.db_side_frame.isHidden())
        self.__set_chevron_icon()

    def __set_chevron_icon(self):
        icon = self.icon_right if self.db_side_frame.isHidden() else self.icon_left
        self.but_db_frame_hide.setIcon(icon)

    def __populate_label_maps(self):
        logger.info("Populating label maps")
        gbox = self.findChild(QGroupBox, 'gbox_db_track_labels')
        if not gbox:
            logger.error("GroupBox 'gbox_track_labels' not found.")
            return None

        for child in gbox.children():
            if isinstance(child, QLabel):
                if child.objectName().endswith('_a_2'):
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

    def __populate_view_db_labels(self):
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["ID", "Label Name"])

        for record in self.music_db.get_labels().values():
            id_item = QStandardItem(str(record.id))
            id_item.setEditable(False)
            label_item = QStandardItem(self.folder_icon, record.name)
            label_item.setEditable(False)
            model.appendRow([id_item, label_item])

        self.view_db_labels.setModel(model)
        self.view_db_labels.setColumnHidden(0, True)
        self.view_db_labels.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    def __populate_view_db_tracks(self):

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Tracks"])
        media_icon = QIcon(":/media/icons/media/Oxygen-Icons.org-Oxygen-Actions-media-record.256.png")

        tracks = self.music_db.get_tracks().values()

        # Iterate over the retrieved tracks and add them to the treeview
        for track in tracks:
            # Assuming each track is a dict with a 'title' key,
            # create a new QStandardItem using the track's title.
            item = QStandardItem(media_icon, str(track))
            item.setEditable(False)
            # Add the item to the model.
            model.appendRow(item)

        self.view_db_tracks.setModel(model)
