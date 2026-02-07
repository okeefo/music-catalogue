import configparser
import os

from PyQt5.QtCore import Qt, QDir, QModelIndex, QItemSelectionModel, QItemSelection
from PyQt5.QtGui import QFont, QIcon, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QFileSystemModel,
    QPushButton,
    QFrame,
    QGroupBox,
    QLabel,
    QHeaderView,
    QCompleter,
    QMessageBox,
    QWidget,
    QTableView,
    QStyledItemDelegate,
    QAbstractItemView,
)
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

        self.icon_left = QIcon("src/qt/icons/chevrons-left.svg")
        self.icon_right = QIcon("src/qt/icons/chevrons-right.svg")
        self.folder_icon = QIcon(":/icons/icons/folder.svg")
        self.media_icon = QIcon(":/media/icons/media/Oxygen-Icons.org-Oxygen-Actions-media-record.256.png")

        db_path = self.__resolve_db_path()
        self.music_db = MusicCatalogDB(db_path)
        if not self.music_db.load():
            logger.warning(f"DB Window: Failed to load database at: {db_path}. Views may be empty.")
        try:
            track_count = self.music_db.count_tracks()
            release_count = self.music_db.count_releases()
        except Exception:
            track_count = 0
            release_count = 0
        logger.info(f"DB Window: Tracks loaded: {track_count}, Releases loaded: {release_count} (db: {db_path})")

    def setup_ui(self, path: str):
        """Set up the UI components for the database widget."""
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
        if self.music_db and self.music_db.count_tracks() == 0:
            QMessageBox.information(self, "No Tracks", "DB Window: No tracks found in the database.\nPlease check your config.ini [db] path.")

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

        path = path_info_bar.text()
        if not os.path.isdir(path):
            QMessageBox.critical(self, "Error", "Directory doesn't exist")
            path_info_bar.setText(tree_view.get_root_dir())
        else:
            tree_view.change_dir(os.path.normpath(path))

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

    def __resolve_db_path(self) -> str:
        """Resolve the database path using config.ini [db] section, with sensible fallbacks."""
        candidates: list[str] = []
        try:
            cfg = configparser.ConfigParser()
            cfg.read("config.ini")
            if cfg.has_section("db"):
                loc = cfg["db"].get("location")
                name = cfg["db"].get("name")
                if loc and name:
                    candidates.append(os.path.join(loc, name))
                    candidates.append(os.path.join(loc, f"{name}.db"))
        except Exception:
            pass

        candidates.append("H:/_-__Tagged__-_/Vinyl Collection/keefy.db")
        for p in candidates:
            try:
                if p and os.path.isfile(p):
                    return p
            except Exception:
                continue
        return candidates[-1]

    def __setup_buttons(self):
        self.but_db_goUp = self.findChild(QPushButton, "but_db_goUp")
        self.but_db_goUp.clicked.connect(lambda: self.go_up_one_level(self.path_info_bar))

        self.db_side_frame = self.findChild(QFrame, "db_side_frame")
        self.but_db_frame_hide = self.findChild(QPushButton, "but_db_frame_hide")
        self.but_db_frame_hide.clicked.connect(self.show_hide_db_side_frame)

    def __setup_data_views(self):
        """Set up the tree views for releases."""
        self.view_db_labels = self.findChild(QTableView, "view_db_labels")
        self._setup_data_view(self.view_db_labels, self.on_row_clicked)

        self.view_db_releases = self.findChild(QTableView, "view_db_releases")
        self._setup_data_view(self.view_db_releases, self.on_row_clicked)

        self.view_db_tracks = self.findChild(QTableView, "view_db_tracks")
        self._setup_data_view(self.view_db_tracks, self.on_row_clicked)

    @staticmethod
    def _setup_data_view(table_view: QTableView, clicked_connect) -> None:
        """Set up a table view with a standard item model."""
        table_view.setModel(QStandardItemModel())
        table_view.setFont(QFont("Source Code Pro", 8))  # change the size as desired
        table_view.setAlternatingRowColors(True)
        table_view.verticalHeader().setVisible(False)
        table_view.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table_view.clicked.connect(lambda index: clicked_connect(table_view, index))

        table_view.setStyleSheet(
            """
        QTableView::item:selected {
            background: #3399ff;
            color: white;
        }
        QTableView::item:selected:!active {
            background: #3399ff;
            color: white;
        }
        """
        )

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
        self.view_db_labels.selectionModel().selectionChanged.connect(self.on_label_selected)

    def __populate_view_db_releases(self, filtered_releases=None):
        logger.info("Populating view_db_releases with filtered releases" if filtered_releases else "Populating view_db_releases with all releases")
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Release ID", "label_id", "Catalog Number", "Discogs Id", "Title", "Artist", "Year"])
        model.setColumnCount(7)

        releases = filtered_releases if filtered_releases is not None else self.music_db.get_releases().values()

        for release in releases:
            items = [QStandardItem(str(getattr(release, attr))) for attr in ["id", "label_id", "catalog_number", "discogs_id", "title", "album_artist_name", "date"]]
            for item in items:
                item.setEditable(False)
            model.appendRow(items)

        self.view_db_releases.setModel(model)
        self.view_db_releases.setColumnHidden(0, True)  # Hide the release_id column
        self.view_db_releases.setColumnHidden(1, True)  # Hide the label_id column
        self.view_db_releases.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view_db_releases.selectionModel().selectionChanged.connect(self.on_release_selected)
        header = self.view_db_releases.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

        # Assuming discogs_id column index is <discogs_column_index>
        discogs_column_index = 3  # adjust this to your actual column index
        delegate = CenterAlignDelegate(self.view_db_releases)
        self.view_db_releases.setItemDelegateForColumn(discogs_column_index, delegate)

    @staticmethod
    def on_row_clicked(table_view: QTableView, index: QModelIndex):
        selection_model = table_view.selectionModel()
        selection = QItemSelection(index, index)
        if selection_model.isSelected(index):
            selection_model.select(selection, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)
        else:
            selection_model.clearSelection()
            selection_model.select(selection, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            # set the background color of the label row

    def on_label_selected(self, selected, deselected):

        # Get the selected index
        indexes = selected.indexes()
        if not indexes:
            self.__populate_view_db_releases(filtered_releases=None)
            self.__populate_view_db_tracks(filtered_tracks=None)
            return

        # The first column (0) is the label ID (hidden)
        label_id_index = indexes[0].siblingAtColumn(0)
        label_id = label_id_index.data()
        if not label_id:
            return

        label_name_index = indexes[0].siblingAtColumn(1)
        label_name = label_name_index.data()
        if not label_name:
            return
        logger.info(f"Label selected: {label_name} (ID: {label_id})")
        filtered_releases = [release for release in self.music_db.get_releases().values() if str(release.label_id) == str(label_id)]
        filtered_tracks = [track for track in self.music_db.get_tracks().values() if str(track.label) == str(label_name)]
        self.__populate_view_db_releases(filtered_releases)
        self.__populate_view_db_tracks(filtered_tracks)

    def on_release_selected(self, selected, deselected):

        indexes = selected.indexes()
        if not indexes:
            self.__populate_view_db_tracks()
            return

        discogs_index = indexes[0].siblingAtColumn(3)
        discogs_id = discogs_index.data()
        if not discogs_id:
            return

        logger.info(f"Release selected - discogsId: {discogs_id})")
        filtered_tracks = [track for track in self.music_db.get_tracks().values() if str(track.discogs_id) == str(discogs_id)]
        self.__populate_view_db_tracks(filtered_tracks)

    def __populate_view_db_tracks(self, filtered_tracks=None):
        logger.info("Populating view_db_tracks with filtered tracks" if filtered_tracks else "Populating view_db_tracks with all tracks")
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(
            [
                "Track ID",
                "Label",
                "Catalog Number",
                "Discogs ID",
                "Album Title",
                "Track Artist",
                "Track Title",
                "Format",
                "Disc Number",
                "Track Number",
            ]
        )

        tracks = filtered_tracks if filtered_tracks is not None else self.music_db.get_tracks().values()

        for track in tracks:
            items = [
                QStandardItem(str(getattr(track, attr)))
                for attr in ["track_id", "label", "catalog_number", "discogs_id", "album_title", "track_artist", "track_title", "format", "disc_number", "track_number"]
            ]
            for item in items:
                item.setEditable(False)
            model.appendRow(items)

        self.view_db_tracks.setModel(model)
        self.view_db_tracks.setColumnHidden(0, True)


class CenterAlignDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignmentFlag.AlignCenter
