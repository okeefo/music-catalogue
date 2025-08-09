import os
from typing import Dict

from PyQt5 import uic
from PyQt5.QtCore import Qt, QDir, QModelIndex, QItemSelectionModel, QItemSelection
from PyQt5.QtGui import QFont, QIcon, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QWidget, QSlider, QPushButton, QTreeView, QTableView, QLabel, QLineEdit, QCompleter, QMessageBox
from qtpy import QtGui
from PyQt5.QtWidgets import QMenu
from db.db_reader import MusicCatalogDB_2, Track, Release, RecordLabel
from ui.custom_waveform_widget import WaveformWidget
from ui.media_player import MediaPlayerController
from ui.db_window_widget import CenterAlignDelegate, DatabaseWidget
from log_config import get_logger

logger = get_logger(__name__)


class DatabaseMediaWindow(QWidget):

    # Table column headers and attribute mapping
    TRACK_TABLE_HEADERS = [
        "Track ID",
        "No",
        "Label",
        "Catalog No",
        "Discogs ID",
        "Album Title",
        "Track Artist",
        "Track Title",
        "Format",
        "Disc No",
        "Track No",
        "Year",
        "Country",
        "File Path",
    ]

    TRACK_ATTRS = [
        "track_id",
        "file_id",
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
    COL_IDX = {name: i for i, name in enumerate(TRACK_TABLE_HEADERS)}

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
        # Enable custom context menu
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.on_labels_tree_context_menu)

    def __setupTrackViewer(self):
        """Sets up the track viewer with a table view."""
        self.track_viewer = self.findChild(QTableView, "track_viewer")
        self.track_viewer.doubleClicked.connect(self.on_track_viewer_double_clicked)
        DatabaseWidget._setup_data_view(self.track_viewer, DatabaseWidget.on_row_clicked)
        self.__populate_view_db_tracks(None)
        self.track_viewer.setContextMenuPolicy(Qt.CustomContextMenu)
        self.track_viewer.customContextMenuRequested.connect(self.on_track_viewer_context_menu)

    def on_track_viewer_context_menu(self, pos):
        logger.debug(f"Context menu requested at pos: {pos}")
        index = self.track_viewer.indexAt(pos)
        logger.debug(f"Index at pos: {index} (isValid: {index.isValid()})")
        row = index.row() if index.isValid() else None
        # If not on a valid index, try to use the current selection
        if row is None or row < 0:
            selection = self.track_viewer.selectionModel().selectedRows()
            logger.debug(f"No valid index at pos. Selection: {selection}")
            if selection:
                row = selection[0].row()
                logger.debug(f"Using selected row: {row}")
            else:
                logger.debug("No valid row to act on for context menu.")
                return  # No valid row to act on
        model = self.track_viewer.model()
        file_path_index = model.index(row, self.COL_IDX["File Path"])
        file_path = file_path_index.data()
        file_id_index = model.index(row, self.COL_IDX["No"])
        file_id = file_id_index.data()
        logger.debug(f"Context menu for row: {row}, file_id: {file_id}, file_path: {file_path}")
        try:
            file_id = int(file_id)
        except Exception:
            file_id = None
        menu = QMenu(self.track_viewer)
        analyse_action = menu.addAction("Analyse")
        play_action = menu.addAction("Play")
        action = menu.exec_(self.track_viewer.viewport().mapToGlobal(pos))
        logger.debug(f"Context menu action selected: {action.text() if action else None}")
        if action == analyse_action:
            logger.info(f"Analyse action triggered from context menu for file_id={file_id}, file_path={file_path}")
            self.analyse_single_track(file_id, file_path)
        elif action == play_action:
            logger.info(f"Play action triggered from context menu for file_id={file_id}, file_path={file_path}")
            self.play_single_track(file_path, file_id)

    def analyse_single_track(self, file_id, file_path):
        """Analyse a single track and store waveform data in DB."""
        from file_operations.audio_waveform_analyzer import analyze_audio_file
        from db.db_writer import MusicCatalogDBWriter
        import json
        import time

        if not file_path or not os.path.isfile(file_path):
            logger.warning(f"File does not exist: {file_path}")
            QMessageBox.warning(self, "File Not Found", f"File does not exist: {file_path}")
            return
        db_writer = MusicCatalogDBWriter(self.music_db2.db_path)
        db_writer.ensure_track_meta_data_table()
        start_time = time.time()
        result = analyze_audio_file(file_path, num_samples=10000)
        if result is None:
            logger.warning(f"Unsupported or failed to analyze: {file_path}")
            QMessageBox.warning(self, "Analysis Failed", f"Unsupported or failed to analyze: {file_path}")
            db_writer.close()
            return
        waveform_json = json.dumps(result.waveform)
        db_writer.write_waveform_data(file_id, waveform_json.encode("utf-8"))
        db_writer.close()
        elapsed = time.time() - start_time
        logger.info(f"Waveform analysis complete. Processed 1 track in {elapsed:.2f} seconds.")
        QMessageBox.information(self, "Analysis Complete", f"Waveform analysis complete. Processed 1 track in {elapsed:.2f} seconds.")

    def play_single_track(self, file_path, file_id):
        """Load and play a single track from the table view."""
        if not file_path or not os.path.isfile(file_path):
            logger.warning(f"File does not exist: {file_path}")
            QMessageBox.warning(self, "File Not Found", f"File does not exist: {file_path}")
            return
        if self.player:
            logger.info(f"Loading and playing file in media player: {file_path}")
            self.player.load_media(file_path, file_id=file_id)
            self.player.on_play_button_clicked()

    def on_labels_tree_context_menu(self, pos):
        menu = QMenu(self.tree_view)
        analyse_action = menu.addAction("Analyse")
        action = menu.exec_(self.tree_view.viewport().mapToGlobal(pos))
        if action == analyse_action:
            self.handle_analyse_selected()

    def handle_analyse_selected(self):
        """
        Handler for the 'Analyse' context menu action. Gathers selected tracks, analyzes audio, and stores waveform data in DB.
        Shows a progress dialog with cancel support.
        """
        from file_operations.audio_waveform_analyzer import analyze_audio_file
        from db.db_writer import MusicCatalogDBWriter
        import json
        import time
        from PyQt5.QtWidgets import QProgressDialog, QApplication
        from PyQt5.QtCore import Qt

        # Determine which tracks to analyze
        selected_indexes = self.tree_view.selectionModel().selectedIndexes()
        if not selected_indexes:
            tracks = self.music_db2.get_all_tracks()
            logger.info("No label/release selected: analyzing all tracks.")
        else:
            # Use the same logic as on_label_selected
            index = selected_indexes[0]
            parent = index.parent()
            if not parent.isValid():
                label_name = index.data()
                tracks = [track for track in self.music_db2.get_all_tracks() if str(track.label) == str(label_name)]
                logger.info(f"Analyzing tracks for label: {label_name}")
            else:
                release_text = index.data()
                catalog_number = release_text.split(" - ")[0]
                tracks = [track for track in self.music_db2.get_all_tracks() if str(track.catalog_number) == str(catalog_number)]
                logger.info(f"Analyzing tracks for release: {release_text}")

        total_tracks = len(tracks)
        if total_tracks == 0:
            QMessageBox.information(self, "No Tracks", "No tracks found to analyze.")
            return

        # Progress dialog setup
        progress = QProgressDialog("Analyzing audio files...", "Cancel", 0, total_tracks, self)
        progress.setWindowTitle("Waveform Analysis Progress")
        progress.setWindowModality(Qt.ApplicationModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)

        db_writer = MusicCatalogDBWriter(self.music_db2.db_path)
        db_writer.ensure_track_meta_data_table()

        processed = 0
        start_time = time.time()
        cancelled = False
        for i, track in enumerate(tracks, 1):
            file_id = track.file_id
            file_path = track.file_location
            # Update progress dialog
            progress.setLabelText(f"Processing file {i}/{total_tracks}:\n{file_path}")
            progress.setValue(i - 1)
            QApplication.processEvents()
            if progress.wasCanceled():
                cancelled = True
                logger.info("Waveform analysis cancelled by user.")
                break
            if not file_path or not os.path.isfile(file_path):
                logger.warning(f"File does not exist: {file_path}")
                continue
            result = analyze_audio_file(file_path, num_samples=10000)
            if result is None:
                logger.warning(f"Unsupported or failed to analyze: {file_path}")
                continue
            waveform_json = json.dumps(result.waveform)
            db_writer.write_waveform_data(file_id, waveform_json.encode("utf-8"))
            processed += 1
        db_writer.close()
        elapsed = time.time() - start_time
        progress.setValue(total_tracks)
        progress.close()
        if cancelled:
            QMessageBox.information(self, "Analysis Cancelled", f"Waveform analysis cancelled. Processed {processed} tracks in {elapsed:.2f} seconds.")
        else:
            logger.info(f"Waveform analysis complete. Processed {processed} tracks in {elapsed:.2f} seconds.")

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
        base_tracks = self._current_label_release_tracks if self._current_label_release_tracks is not None else self.music_db2.get_all_tracks()
        if not text:
            self.__populate_view_db_tracks(base_tracks)
            return
        filtered_tracks = []
        for track in base_tracks:
            for attr in self.TRACK_ATTRS:
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
        db_path = self.music_db2.db_path if hasattr(self, "music_db2") else None
        self.player = MediaPlayerController(
            self, self.slider_db, self.wdgt_wave_db, self.butt_play_db, self.butt_stop_db, self.lbl_current_db, self.lbl_duration_db, self.lbl_info_db, self.lbl_cover_db, db_path
        )

    def __populate_view_db_tracks(self, filtered_tracks=None):
        logger.info("Populating view_db_tracks with filtered tracks" if filtered_tracks else "Populating view_db_tracks with all tracks")
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(self.TRACK_TABLE_HEADERS)

        tracks = filtered_tracks if filtered_tracks is not None else self.music_db2.get_all_tracks()

        for track in tracks:
            items = []
            for attr in self.TRACK_ATTRS:
                if attr == "discogs_id":
                    # Display as plain text but styled as a hyperlink
                    discogs_id = str(getattr(track, attr, ""))
                    item = QStandardItem(discogs_id)
                    item.setData(track.discogs_url, Qt.UserRole)
                    # Style as hyperlink: blue and underlined
                    font = item.font()
                    font.setUnderline(True)
                    item.setFont(font)
                    item.setForeground(QtGui.QBrush(QtGui.QColor(0, 102, 204)))
                    item.setEditable(False)
                    items.append(item)
                else:
                    item = QStandardItem(str(getattr(track, attr, "")))
                    item.setEditable(False)
                    items.append(item)
            model.appendRow(items)

        self.track_viewer.setModel(model)
        # Hide the first and last columns (Track ID and No)
        self.track_viewer.setColumnHidden(self.COL_IDX["Track ID"], True)
        # self.track_viewer.setColumnHidden(self.COL_IDX["No"], True)

        # Use constants for column indexes
        for col in ["Catalog No", "Discogs ID", "Format", "Disc No", "Track No"]:
            self.__center_align_delegate(self.COL_IDX[col])

        for col in ["Album Title", "Track Artist", "Track Title", "Format", "Disc No", "Track No", "Year", "Country", "File Path"]:
            self.track_viewer.resizeColumnToContents(self.COL_IDX[col])

        # No need for rich text rendering; hyperlink is styled with font/brush

    def __center_align_delegate(self, index: int) -> None:
        """
        Centers the text in the specified column index.

        Args:
            index (int): The column index to center align.
        """
        delegate = CenterAlignDelegate(self.track_viewer)
        self.track_viewer.setItemDelegateForColumn(index, delegate)

    def on_row_pressed(self, tree_view: QTreeView, index: QModelIndex):
        # Only change selection if the left mouse button is pressed
        mouse_buttons = QtGui.QGuiApplication.mouseButtons()
        if mouse_buttons & Qt.LeftButton:
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
        else:
            # Ignore right/middle mouse button for selection
            pass

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
        """Handles the table view double click event. Returns: None"""
        logger.debug(f"Double clicked on index: row={index.row()}, col={index.column()}, button state unknown (Qt does not provide)")
        model = self.track_viewer.model()
        row = index.row()
        col = index.column()

        # If double-clicked on Discogs ID column, open the URL
        if col == self.COL_IDX["Discogs ID"]:
            item = model.item(row, col)
            url = item.data(Qt.UserRole)
            logger.debug(f"Double click on Discogs ID: url={url}")
            if url and isinstance(url, str) and url.strip():
                import webbrowser

                # Remove any embedded null characters
                url = url.replace("\x00", "").replace("\0", "").strip()
                try:
                    webbrowser.open(url)
                except Exception as e:
                    logger.error(f"Failed to open Discogs URL: {url} ({e})")
            return

        file_path_index = model.index(row, self.COL_IDX["File Path"])
        file_path = file_path_index.data()

        file_id_index = model.index(row, self.COL_IDX["No"])
        file_id = file_id_index.data()
        logger.debug(f"Double click: row={row}, file_id={file_id}, file_path={file_path}")
        try:
            file_id = int(file_id)
        except Exception:
            file_id = None

        # Get track title for info bar
        track_title_index = model.index(row, self.COL_IDX["Track Title"])
        track_title = track_title_index.data() if track_title_index.isValid() else ""

        if not file_path or not os.path.isfile(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return

        if self.player:
            logger.info(f"Loading file in media player: {file_path}")
            # Set info bar to 'Loading <track title>'
            if hasattr(self, "lbl_info_db") and self.lbl_info_db:
                self.lbl_info_db.setText(f"Loading {track_title}")
                self.lbl_info_db.repaint()  # Force immediate update
            self.player.load_media(file_path, file_id=file_id)
            # Set info bar to '<track title>' after loading
            if hasattr(self, "lbl_info_db") and self.lbl_info_db:
                self.lbl_info_db.setText(track_title)

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
