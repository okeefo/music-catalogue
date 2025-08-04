import os

from PyQt5 import uic
from PyQt5.QtCore import Qt, QDir, QModelIndex
from PyQt5.QtGui import QFont, QIcon, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QWidget, QSlider, QPushButton, QFrame, QGroupBox, QLabel, QHeaderView, QCompleter, QMessageBox
from qtpy import QtGui
from db.db_reader import MusicCatalogDB_2
from ui.custom_waveform_widget import WaveformWidget
from ui.media_player import MediaPlayerController
from ui.custom_line_edit import MyLineEdit
from ui.custom_tree_view import MyTreeView
from log_config import get_logger

logger = get_logger(__name__)


class DatabaseMediaWindow(QWidget):
    label_map = {}
    label_a_map = {}

    def __init__(self, parent=None):
        super().__init__(parent)

        self.icon_left = QIcon("src/qt/icons/chevrons-left.svg")
        self.icon_right = QIcon("src/qt/icons/chevrons-right.svg")
        self.folder_icon = QIcon(":/icons/icons/folder.svg")
        self.media_icon = QIcon(":/media/icons/media/Oxygen-Icons.org-Oxygen-Actions-media-record.256.png")

        self.music_db2 = MusicCatalogDB_2("H:/_-__Tagged__-_/Vinyl Collection/keefy.db")
        self.music_db2.load()

    #        self.setup_ui()

    def setup_ui(self):
        self.__setupLabelViewer()
        self.__setup_media_player()

    def __setupLabelViewer(self):
        cache = self.music_db2.get_labels_and_releases()
        # Find the QTreeView widget
        self.tree_view = self.findChild(MyTreeView, "view_db_labels_releases")

        # Set up the model
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Label & Release"])

        # For each label, add as a parent item with folder icon

        for label_name, release_ids in cache.items():
            label_item = QStandardItem(self.folder_icon, label_name)
            label_item.setEditable(False)
            # For each release under this label, add as child
            for release_id in release_ids:
                release = self.music_db2._releases_cache.get(release_id)
                if release:
                    # Show media_icon, catalog_number, and title
                    release_text = f"{release.catalog_number} - {release.title}"
                    release_item = QStandardItem(self.media_icon, release_text)
                    release_item.setEditable(False)
                    label_item.appendRow(release_item)
            model.appendRow(label_item)

        self.tree_view.setModel(model)
        self.tree_view.setHeaderHidden(False)

    def __setup_media_player(self) -> None:
        """Sets up the media player. Returns: None"""
        self.slider_db = self.findChild(QSlider, "slider_db")
        self.wdgt_wave_db = self.findChild(WaveformWidget, "wdgt_wave_db")
        self.butt_play_db = self.findChild(QPushButton, "butt_play_db")
        self.butt_stop_db = self.findChild(QPushButton, "butt_stop_db")
        self.lbl_current_db = self.findChild(QLabel, "lbl_current_db")
        self.lbl_duration_db = self.findChild(QLabel, "lbl_duration_db")
        self.lbl_info_db = self.findChild(QLabel, "lbl_info_db")
        self.lbl_cover_db = self.findChild(QLabel, "lbl_cover_db")
        self.player = MediaPlayerController(self, self.slider_db, self.wdgt_wave_db, self.butt_play_db, self.butt_stop_db, self.lbl_current_db, self.lbl_duration_db,
                                              self.lbl_info_db, self.lbl_cover_db)