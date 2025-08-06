import os
from typing import Dict

from PyQt5 import uic
from PyQt5.QtCore import Qt, QDir, QModelIndex, QItemSelectionModel, QItemSelection
from PyQt5.QtGui import QFont, QIcon, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QWidget, QSlider, QPushButton, QTreeView, QTableView, QLabel, QLineEdit, QCompleter, QMessageBox
from qtpy import QtGui
from db.db_reader import MusicCatalogDB_2, Track, Release, RecordLabel
from ui.custom_waveform_widget import WaveformWidget
from ui.media_player import MediaPlayerController
from ui.db_window_widget import CenterAlignDelegate, DatabaseWidget
from log_config import get_logger

logger = get_logger(__name__)


class DatabaseMediaWindow(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.icon_left = QIcon("src/qt/icons/chevrons-left.svg")
        self.icon_right = QIcon("src/qt/icons/chevrons-right.svg")
        self.folder_icon = QIcon(":/icons/icons/folder.svg")
        self.media_icon = QIcon(":/media/icons/media/Oxygen-Icons.org-Oxygen-Actions-media-record.256.png")
        self.icon_expand = QIcon(":/icons/icons/folder-plus.svg")
        self.icon_collapse = QIcon(":/icons/icons/folder-minus.svg")

        self._tree_expanded = False  # Track expand/collapse state

        self.music_db2 = MusicCatalogDB_2("H:/_-__Tagged__-_/Vinyl Collection/keefy.db")
        self.music_db2.load()

    def setup_ui(self):
        self.__setupLabelViewer()
        self.__setupTrackViewer()
        self.__setup_media_player()
        self.__setup_search_bars()
        self.__setup_buttons()

    def __setupLabelViewer(self):
        self.tree_view = self.findChild(QTreeView, "view_db_labels_releases")
        self.populate_label_viewer()
        self._current_label_release_tracks = None  # Tracks filtered by label/release

    def __setup_search_bars(self):
        self.search_bar_labels = self.findChild(QLineEdit, "search_bar_labels")
        self.search_bar_tracks = self.findChild(QLineEdit, "search_bar_tracks")
        self.search_bar_labels.textChanged.connect(self.filter_label_viewer)
        self.search_bar_tracks.textChanged.connect(self.filter_track_viewer)

    def __setup_buttons(self):
        self.butt_exp_releases = self.findChild(QPushButton, "butt_exp_releases")
        self.butt_exp_releases.setIcon(self.icon_expand)
        self.butt_exp_releases.clicked.connect(self.butt_exp_releases_clicked)

        self.butt_clear_releases = self.findChild(QPushButton, "butt_clear_releases")
        self.butt_clear_releases.clicked.connect(lambda: self.butt_clear_search_bar_clicked(self.search_bar_labels))

        self.butt_clear_tracks = self.findChild(QPushButton, "butt_clear_tracks")
        self.butt_clear_tracks.clicked.connect(lambda: self.butt_clear_search_bar_clicked(self.search_bar_tracks))

    def butt_exp_releases_clicked(self):
        """
        Expands or collapses all releases in the label viewer tree.
        and updates the button icon accordingly.
        """
        if self._tree_expanded:
            self.tree_view.collapseAll()
            self.butt_exp_releases.setIcon(self.icon_expand)
            self._tree_expanded = False
        else:
            self.tree_view.expandAll()
            self.butt_exp_releases.setIcon(self.icon_collapse)
            self._tree_expanded = True

    def butt_clear_search_bar_clicked(self, search_bar: QLineEdit):
        """
        Clears the search bar
        """
        search_bar.clear()

    def filter_track_viewer(self, text):
        """
        Filters the track viewer table based on the search text.
        Respects the current label/release filter if present.
        Shows only tracks that match the search term in any column (case-insensitive, substring match).
        """
        text = text.strip().lower()
        # Use the current label/release filtered tracks if present, else all tracks
        base_tracks = self._current_label_release_tracks if self._current_label_release_tracks is not None else self.music_db2.get_all_tracks()
        if not text:
            self.__populate_view_db_tracks(base_tracks)
            return
        filtered_tracks = []
        for track in base_tracks:
            for attr in [
                "track_id",
                "label",
                "catalog_number",
                "discogs_id",
                "album_title",
                "track_artist",
                "track_title",
                "format",
                "disc_number",
                "track_number",
                "year",
                "country",
                "file_location",
            ]:
                value = str(getattr(track, attr, "")).lower()
                if text in value:
                    filtered_tracks.append(track)
                    break
        self.__populate_view_db_tracks(filtered_tracks)

    def filter_label_viewer(self, text):
        """
        Filters the label viewer tree based on the search text.
        Shows only labels/releases that match the search term (case-insensitive, substring match).
        """
        label_cache = self.music_db2.get_labels_and_releases()
        text = text.strip().lower()

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Labels & Releases"])

        for label_name, release_ids in label_cache.items():
            label_match = text in label_name.lower()
            # Build list of matching releases
            matching_releases = []
            for release_id in release_ids:
                release = self.music_db2.get_release_by_id(release_id)
                if release:
                    release_text = f"{release.catalog_number} - {release.title}"
                    if text in release_text.lower():
                        matching_releases.append((release, release_text))
            # If label matches or any release matches, show
            if label_match or matching_releases:
                label_item = QStandardItem(self.folder_icon, label_name)
                label_item.setEditable(False)
                for release, release_text in matching_releases:
                    release_item = QStandardItem(self.media_icon, release_text)
                    release_item.setEditable(False)
                    label_item.appendRow(release_item)
                # If label matches but no releases match, show all releases
                if label_match and not matching_releases:
                    for release_id in release_ids:
                        release = self.music_db2.get_release_by_id(release_id)
                        if release:
                            release_text = f"{release.catalog_number} - {release.title}"
                            release_item = QStandardItem(self.media_icon, release_text)
                            release_item.setEditable(False)
                            label_item.appendRow(release_item)
                model.appendRow(label_item)

        self.tree_view.setModel(model)
        self.tree_view.setHeaderHidden(False)
        # Disconnect previous signal connections to avoid duplicates
        try:
            self.tree_view.pressed.disconnect()
        except Exception:
            pass
        try:
            self.tree_view.selectionModel().selectionChanged.disconnect()
        except Exception:
            pass
        self.tree_view.pressed.connect(lambda index: self.on_row_pressed(self.tree_view, index))
        self.tree_view.selectionModel().selectionChanged.connect(self.on_label_selected)

    def populate_label_viewer(self):
        """Populates the label viewer with labels and their associated releases."""

        label_cache = self.music_db2.get_labels_and_releases()

        # Set up the model
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Labels & Releases"])

        # For each label, add as a parent item with folder icon

        for label_name, release_ids in label_cache.items():
            label_item = QStandardItem(self.folder_icon, label_name)
            label_item.setEditable(False)
            # For each release under this label, add as child
            for release_id in release_ids:
                release = self.music_db2.get_release_by_id(release_id)
                if release:
                    # Show media_icon, catalog_number, and title
                    release_text = f"{release.catalog_number} - {release.title}"
                    release_item = QStandardItem(self.media_icon, release_text)
                    release_item.setEditable(False)
                    label_item.appendRow(release_item)
            model.appendRow(label_item)

        self.tree_view.setModel(model)
        self.tree_view.setHeaderHidden(False)
        # Disconnect previous signal connections to avoid duplicates
        try:
            self.tree_view.pressed.disconnect()
        except Exception:
            pass
        try:
            self.tree_view.selectionModel().selectionChanged.disconnect()
        except Exception:
            pass
        self.tree_view.pressed.connect(lambda index: self.on_row_pressed(self.tree_view, index))
        self.tree_view.selectionModel().selectionChanged.connect(self.on_label_selected)

    def __setupTrackViewer(self):
        """Sets up the track viewer with a table view."""
        self.track_viewer = self.findChild(QTableView, "track_viewer")
        self.track_viewer.doubleClicked.connect(self.on_track_viewer_double_clicked)
        DatabaseWidget._setup_data_view(self.track_viewer, DatabaseWidget.on_row_clicked)
        self.__populate_view_db_tracks(None)

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
        self.player = MediaPlayerController(
            self, self.slider_db, self.wdgt_wave_db, self.butt_play_db, self.butt_stop_db, self.lbl_current_db, self.lbl_duration_db, self.lbl_info_db, self.lbl_cover_db
        )

    def __populate_view_db_tracks(self, filtered_tracks=None):
        logger.info("Populating view_db_tracks with filtered tracks" if filtered_tracks else "Populating view_db_tracks with all tracks")
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(
            ["Track ID", "Label", "Catalog No", "Discogs ID", "Album Title", "Track Artist", "Track Title", "Format", "Disc No", "Track No", "Year", "Country", "File Path"]
        )

        tracks = filtered_tracks if filtered_tracks is not None else self.music_db2.get_all_tracks()

        for track in tracks:
            items = [
                QStandardItem(str(getattr(track, attr)))
                for attr in [
                    "track_id",
                    "label",
                    "catalog_number",
                    "discogs_id",
                    "album_title",
                    "track_artist",
                    "track_title",
                    "format",
                    "disc_number",
                    "track_number",
                    "year",
                    "country",
                    "file_location",
                ]
            ]
            for item in items:
                item.setEditable(False)
            model.appendRow(items)

        self.track_viewer.setModel(model)
        self.track_viewer.setColumnHidden(0, True)

        self.__center_align_delegate(2)  # Center align the catalog number column
        self.__center_align_delegate(3)  # Center align the Discogs ID column
        self.__center_align_delegate(7)  # Center align the format column
        self.__center_align_delegate(8)  # Center align the disc number column
        self.__center_align_delegate(9)  # Center align the track number column

        self.track_viewer.resizeColumnToContents(4)  # 4  is the index of "Album title"
        self.track_viewer.resizeColumnToContents(5)  # 5  is the index of "Track Artist"
        self.track_viewer.resizeColumnToContents(6)  # 6  is the index of "Track Title"
        self.track_viewer.resizeColumnToContents(7)  # 7  is the index of "Format"
        self.track_viewer.resizeColumnToContents(8)  # 8  is the index of "Disc No"
        self.track_viewer.resizeColumnToContents(9)  # 9  is the index of "Track No"
        self.track_viewer.resizeColumnToContents(10)  # 10 is the index of "Year"
        self.track_viewer.resizeColumnToContents(11)  # 12 is the index of "Country"
        self.track_viewer.resizeColumnToContents(12)  # 13 is the index of "File Path"

    def __center_align_delegate(self, index: int) -> None:
        """
        Centers the text in the specified column index.

        Args:
            index (int): The column index to center align.
        """
        delegate = CenterAlignDelegate(self.track_viewer)
        self.track_viewer.setItemDelegateForColumn(index, delegate)

    def on_row_pressed(self, tree_view: QTreeView, index: QModelIndex):
        selection_model = tree_view.selectionModel()
        selection = QItemSelection(index, index)
        if selection_model.isSelected(index):
            selection_model.select(selection, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)
            logger.info(f"Deselected index: {index.data()}")
        else:
            selection_model.clearSelection()
            selection_model.select(selection, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            logger.info(f"Selected index: {index.data()}")
        # Force the view to update selection highlighting immediately
        tree_view.viewport().update()

    def on_label_selected(self, selected: QItemSelection, deselected: QItemSelection):
        # Get the selected index
        indexes = selected.indexes()
        if not indexes:
            self._current_label_release_tracks = None
            self.__populate_view_db_tracks(filtered_tracks=None)
            return

        index = indexes[0]
        parent = index.parent()

        if not parent.isValid():
            # Top-level: label
            label_name = index.data()
            logger.info(f"Label selected: {label_name}")
            filtered_tracks = [track for track in self.music_db2.get_all_tracks() if str(track.label) == str(label_name)]
            self._current_label_release_tracks = filtered_tracks
            self.__populate_view_db_tracks(filtered_tracks)
        else:
            # Child: release
            release_text = index.data()
            # Extract catalog number from release_text (format: "CATNO - Title")
            catalog_number = release_text.split(" - ")[0]
            logger.info(f"Release selected: {release_text} (Catalog: {catalog_number})")
            filtered_tracks = [track for track in self.music_db2.get_all_tracks() if str(track.catalog_number) == str(catalog_number)]
            self._current_label_release_tracks = filtered_tracks
            self.__populate_view_db_tracks(filtered_tracks)

    def on_track_viewer_double_clicked(self, index: QModelIndex) -> None:
        """Handles the tree view double click event. Returns: None"""

        model = self.track_viewer.model()
        row = index.row()

        file_path_index = model.index(row, 12)
        file_path = file_path_index.data()

        if not file_path or not os.path.isfile(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return

        if self.player:
            logger.info(f"Loading file in media player: {file_path}")
            self.player.load_media(file_path)

    def closeEvent(self, event):
        """
        Ensure all timers, media players, and widgets are properly cleaned up on close to avoid QBasicTimer warnings.
        """
        # Stop and close the media player if it exists
        if hasattr(self, "player") and self.player:
            try:
                self.player.stop()
            except Exception:
                pass
            try:
                self.player.close()  # If MediaPlayerController is a QWidget or has a close method
            except Exception:
                pass
            self.player.deleteLater()
        # Stop and close the waveform widget if it exists
        if hasattr(self, "wdgt_wave_db") and self.wdgt_wave_db:
            try:
                self.wdgt_wave_db.close()
            except Exception:
                pass
            self.wdgt_wave_db.deleteLater()
        # Call the base class closeEvent
        super().closeEvent(event)
