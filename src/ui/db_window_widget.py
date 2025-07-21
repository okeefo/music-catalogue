import os

from PyQt5.QtCore import Qt, QDir, QModelIndex, QItemSelectionModel
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QIcon, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QFileSystemModel, QPushButton, QFrame, QGroupBox, QLabel, QHeaderView, QCompleter, QMessageBox, QWidget, QTableView, QStyledItemDelegate
import PyQt5.QtWidgets as QtWidgets
from db.music_db import MusicCatalogDB
from log_config import get_logger
from ui.custom_line_edit import MyLineEdit
from ui.custom_tree_view import MyTreeView
from PyQt5.QtCore import QItemSelection

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

        flags = self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        self.setWindowFlags(Qt.WindowFlags(flags))
        self.__setup_model()
        self.__setup_line_edit(path)
        self.__setup_tree_view(path)
        self.__setup_buttons()
        self.__populate_label_maps()
        self.clear_track_labels()

        self.__set_chevron_icon()
        self.__setup_data_views()
        self.__populate_view_db_labels()
        self.__populate_view_db_releases()
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
        self.__setup_data_view(self.view_db_labels)

        self.view_db_releases = self.findChild(QTableView, "view_db_releases")
        self.__setup_data_view(self.view_db_releases)

        self.view_db_tracks = self.findChild(QTableView, "view_db_tracks")
        self.__setup_data_view(self.view_db_tracks)

    @staticmethod
    def __setup_data_view(table_view: QTableView) -> None:
        """Set up a table view with a standard item model."""
        table_view.setModel(QStandardItemModel())
        monospace = QFont("Source Code Pro", 8)  # change the size as desired
        table_view.setFont(monospace)
        table_view.setAlternatingRowColors(True)
        table_view.verticalHeader().setVisible(False)

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
        gbox = self.findChild(QGroupBox, "gbox_db_track_labels")
        if not gbox:
            logger.error("GroupBox 'gbox_track_labels' not found.")
            return None

        for child in gbox.children():
            if isinstance(child, QLabel):
                if child.objectName().endswith("_a_2"):
                    self.label_a_map[child.objectName()] = child.minimumWidth()
                else:
                    self.label_map[child.objectName()] = child.minimumWidth()

        logger.info(f"Label map: {self.label_map}")
        logger.info(f"Label_a map: {self.label_a_map}")
        return None

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
        self.view_db_labels.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.view_db_labels.clicked.connect(self.on_label_row_clicked)
        self.view_db_labels.selectionModel().selectionChanged.connect(self.on_label_selected)

    def __populate_view_db_releases(self):
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Release ID", "label_id", "Catalog Number", "Discogs Id", "Title", "Artist", "Year"])
        model.setColumnCount(7)

        for release in self.music_db.get_releases().values():
            release_id_item = QStandardItem(str(release.id))
            release_id_item.setEditable(False)
            label_id_item = QStandardItem(str(release.label_id))
            label_id_item.setEditable(False)
            catalog_number_item = QStandardItem(release.catalog_number)
            catalog_number_item.setEditable(False)
            discogs_id_item = QStandardItem(str(release.discogs_id))
            discogs_id_item.setEditable(False)
            title_item = QStandardItem(release.title)
            title_item.setEditable(False)
            artist_item = QStandardItem(release.album_artist_name)
            artist_item.setEditable(False)
            year_item = QStandardItem(str(release.date))
            year_item.setEditable(False)

            model.appendRow([release_id_item, label_id_item, catalog_number_item, discogs_id_item, title_item, artist_item, year_item])

        self.view_db_releases.setModel(model)
        self.view_db_releases.setColumnHidden(0, True)  # Hide the release_id column
        self.view_db_releases.setColumnHidden(1, True)  # Hide the label_id column
        self.view_db_releases.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.view_db_releases.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.view_db_releases.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.view_db_releases.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)

        # Assuming discogs_id column index is <discogs_column_index>
        discogs_column_index = 3  # adjust this to your actual column index
        delegate = CenterAlignDelegate(self.view_db_releases)
        self.view_db_releases.setItemDelegateForColumn(discogs_column_index, delegate)

    def on_label_row_clicked(self, index: QModelIndex):
        selection_model = self.view_db_labels.selectionModel()
        selection = QItemSelection(index, index)
        if selection_model.isSelected(index):
            selection_model.select(selection, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)
        else:
            selection_model.clearSelection()
            selection_model.select(selection, QItemSelectionModel.Select | QItemSelectionModel.Rows)

    def on_label_selected(self, selected, deselected):

        logger.info("Label selected")

        # Get the selected index
        indexes = selected.indexes()
        if not indexes:
            self.__populate_view_db_releases()
            return

        # The first column (0) is the label ID (hidden)
        label_id_index = indexes[0].siblingAtColumn(0)
        label_id = label_id_index.data()
        if not label_id:
            return

        # Filter releases by label_id
        filtered_releases = [release for release in self.music_db.get_releases().values() if str(release.label_id) == str(label_id)]

        # Rebuild the releases model with only matching releases
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Release ID", "label_id", "Catalog Number", "Discogs Id", "Title", "Artist", "Year"])
        model.setColumnCount(7)

        for release in filtered_releases:
            release_id_item = QStandardItem(str(release.id))
            release_id_item.setEditable(False)
            label_id_item = QStandardItem(str(release.label_id))
            label_id_item.setEditable(False)
            catalog_number_item = QStandardItem(release.catalog_number)
            catalog_number_item.setEditable(False)
            discogs_id_item = QStandardItem(str(release.discogs_id))
            discogs_id_item.setEditable(False)
            title_item = QStandardItem(release.title)
            title_item.setEditable(False)
            artist_item = QStandardItem(release.album_artist_name)
            artist_item.setEditable(False)
            year_item = QStandardItem(str(release.date))
            year_item.setEditable(False)

            model.appendRow([release_id_item, label_id_item, catalog_number_item, discogs_id_item, title_item, artist_item, year_item])

        self.view_db_releases.setModel(model)
        self.view_db_releases.setColumnHidden(0, True)
        self.view_db_releases.setColumnHidden(1, True)
        self.view_db_releases.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.view_db_releases.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.view_db_releases.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.view_db_releases.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)

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


class CenterAlignDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignmentFlag.AlignCenter
