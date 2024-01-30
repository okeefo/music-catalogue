import traceback
import configparser
import contextlib
import logging
import qt.resources_rcc
import os

from PyQt5 import uic, QtGui
from PyQt5.QtWidgets import (
    QStackedWidget,
    QDialog,
    QLabel,
    QApplication,
    QMainWindow,
    QAction,
    QStyle,
    QTreeView,
    QFileDialog,
    QPushButton,
    QMessageBox,
    QCompleter,
    QFileSystemModel,
    QLineEdit,
    QMenu,
    QVBoxLayout,
)
from PyQt5.QtCore import QSize, QPropertyAnimation, QEasingCurve, Qt, QDir, QModelIndex, QUrl
from scanner.repackage_dir import repackageByLabel
from PyQt5.QtGui import QFont, QPixmap
from enum import Enum
from scanner.audio_tags import AudioTags
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from mutagen.id3 import PictureType, APIC
from mutagen.id3 import error as ID3Error
from scanner.audio_tags import PictureTypeDescription
from typing import Dict
from typing import Union
from PIL import Image


# Create an instance of QApplication
app = QApplication([])

# define constants
ICON_INDEX = 0
CONFIG_SECTION_DIRECTORIES = "Directories"
CONFIG_SECTION_WINDOW = "Window"
CONFIG_WINDOW_HIGHT = "hight"
CONFIG_WINDOW_WIDTH = "Width"
CONFIG_LAST_TARGET_DIRECTORY = "last_target_directory"
CONFIG_LAST_SOURCE_DIRECTORY = "last_source_directory"
INVALID_MEDIA_ERROR_MSG = 'Failed to play the media file. You might need to install the K-Lite Codec Pack. You can download it from the official website:<br><a href="https://www.codecguide.com/download_kl.htm">https://www.codecguide.com/download_kl.htm</a>'
# Create a dictionary that maps picture type numbers to descriptions
PICTURE_TYPES = {value: key for key, value in vars(PictureType).items() if not key.startswith("_")}


class ChangeType(Enum):
    SOURCE = 0
    TARGET = 1

    def isSource(self):
        return self == ChangeType.SOURCE

    def isTarget(self):
        return self == ChangeType.TARGET


# Set logging instance
logger = logging.getLogger(__name__)


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
        dialog = QDialog()
        dialog.setWindowTitle(title)
        dialog.setLayout(QVBoxLayout())
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # Remove the '?' from the title bar


        # Create a QLabel, set its pixmap to the pixmap of the ImageLabel, and add it to the QDialog
        label = QLabel(dialog)
        label.setPixmap(pixmap)
        label.setScaledContents(True)
        dialog.setWindowIcon(QtGui.QIcon(":/icons/icons/headphones.svg"))
        dialog.layout().addWidget(label)
      
        # Show the QDialog
        dialog.exec_()

class MainWindow(QMainWindow):
    """Main window class for the application."""

    def __init__(self, application):
        """Initialize the main window."""
        super().__init__()
        self.application = application

        # Set up instance variables
        self.config = configparser.ConfigParser()
        self.id3_tags = []
        self.directory_source = "c:\\"
        self.directory_target = "c:\\"
        self.audio_tags = AudioTags()
        self.player = QMediaPlayer()

        # set up config
        self.__setup_config()

        # Set up the user interface from Designer.
        # Load the .ui file and set up the UI
        uic.loadUi(
            "src\\qt\\music_manager.ui",
            self,
        )

        # Sets up the user interface of the main window.
        self.update_status("Welcome - select a directory to scan either from the menu or the scan button")
        self.__setup_icons()
        self.__setup_window_size()
        self.__setup_exit()
        self.__setup_scan_source()
        self.__setup_scan_target()
        self.__setup_copy_source_button()
        self.__setup_tree_widgets()
        self.__setup_refresh_button()
        self.__setup_id3_tags()
        self.__setup_label_cache()
        self.__setup_label_style_sheet()
        self.__clear_labels()
        self.__setup_action_buttons()
        self.__setup_menu_buttons()
        self.__setup_path_labels()
        self.__setup_dir_up_buttons()
        self.__setup_media_player()

    def __setup_media_player(self) -> None:
        """
        Sets up the media player.
        Returns: None
        """
        self.player.mediaStatusChanged.connect(self.handle_media_status_changed)

    def __setup_config(self) -> None:
        """
        Sets up the configuration by reading the config.ini file and adding missing sections if necessary.
        Returns: None
        """

        self.config.read("config.ini")
        if CONFIG_SECTION_DIRECTORIES not in self.config:
            self.config.add_section(CONFIG_SECTION_DIRECTORIES)
            self.config.set(
                CONFIG_SECTION_DIRECTORIES,
                CONFIG_LAST_TARGET_DIRECTORY,
                QDir.rootPath(),
            )
            self.config.set(
                CONFIG_SECTION_DIRECTORIES,
                CONFIG_LAST_SOURCE_DIRECTORY,
                QDir.rootPath(),
            )
        if CONFIG_SECTION_WINDOW not in self.config:
            self.config.add_section(CONFIG_SECTION_WINDOW)

    def __setup_path_labels(self) -> None:
        # Create a file system model
        model = QFileSystemModel()
        model.setRootPath(QDir.rootPath())

        # Create a completer with the model
        completer = QCompleter()
        completer.setModel(model)

        # Set the completer for the QLineEdit
        self.path_source = self.findChild(QLineEdit, "path_source")
        self.path_source.setCompleter(completer)
        self.path_target = self.findChild(QLineEdit, "path_target")
        self.path_target.setCompleter(completer)

        #       self.path_source = self.findChild(QtWidgets.QLabel, "path_label_source")
        # self.path_target = self.findChild(QtWidgets.QLabel, "path_label_target")
        self.path_source.returnPressed.connect(lambda: self.on_path_return_pressed(self.tree_source))
        self.path_target.returnPressed.connect(lambda: self.on_path_return_pressed(self.tree_target))
        self.path_source.setText(self.config[CONFIG_SECTION_DIRECTORIES][CONFIG_LAST_SOURCE_DIRECTORY])
        self.path_target.setText(self.config[CONFIG_SECTION_DIRECTORIES][CONFIG_LAST_TARGET_DIRECTORY])

    def __setup_icons(self) -> None:
        self.icon_left = QtGui.QIcon(":/icons/icons/chevrons-left.svg")
        self.icon_right = QtGui.QIcon(":/icons/icons/chevrons-right.svg")
        self.icon_menu = QtGui.QIcon(":/icons/icons/menu.svg")
        self.icon_repackage = QtGui.QIcon(":/icons/icons/package.svg")
        self.icon_move = QtGui.QIcon(":/icons/icons/move.svg")
        self.icon_exit = QtGui.QIcon(":/icons/icons/log-out.svg")
        self.icon_play = QtGui.QIcon(":/icons/icons/play.svg")
        self.icon_pause = QtGui.QIcon(":/icons/icons/pause.svg")
        self.icon_stop = QtGui.QIcon(":/icons/icons/stop-circle.svg")

    def __setup_menu_buttons(self) -> None:
        """Set up the menu buttons. Returns: None"""
        # toggle menu
        self.frame_left_menu.setMinimumWidth(0)
        self.but_toggle = self.findChild(QPushButton, "but_toggle")
        self.but_toggle.clicked.connect(lambda: self.toggleMenu())
        self.but_toggle.setToolTip("Open Menu")
        self.but_toggle.setToolTipDuration(1000)
        self.but_toggle.setIcon(self.icon_menu)
        self.but_toggle.setShortcut("Ctrl+M")
        self.but_exit.setIcon(QtGui.QIcon(self.icon_exit.pixmap(40, 40)))

    def __setup_action_buttons(self) -> None:
        """Set up the action buttons. Returns: None"""
        # repackage button
        self.but_repackage = self.findChild(QPushButton, "butt_repackage")
        self.but_repackage.clicked.connect(lambda: self.on_repackage_button_clicked())
        self.but_repackage.setToolTip("[Ctrl+R] Repackage the source directory -> target directory")
        self.but_repackage.setToolTipDuration(1000)
        self.but_repackage.setShortcut("Ctrl+R")

    def __setup_window_size(self) -> None:
        """
        Sets up the size of the main window based on the configuration settings.
        Returns: None
        """
        self.resize(
            self.config.getint(CONFIG_SECTION_WINDOW, CONFIG_WINDOW_WIDTH, fallback=800),
            self.config.getint(CONFIG_SECTION_WINDOW, CONFIG_WINDOW_HIGHT, fallback=600),
        )

        self.setMinimumSize(QSize(800, 600))

    def __setup_id3_tags(self) -> None:
        """
        Populates the id3_tags list with the names of the supported ID3 tags.
        Returns: None
        """

        self.id3_tags = [
            "TITLE",
            "ARTIST",
            "ALBUM",
            "LABEL",
            "DISCNUMBER",
            "TRACKNUMBER",
            "CATALOGNUMBER",
            "DISCOGS_RELEASE_ID",
            "URL",
        ]

    def __setup_label_cache(self) -> None:
        id3_labels_source = [
            self.lbl_src_title,
            self.lbl_src_artist,
            self.lbl_src_album,
            self.lbl_src_label,
            self.lbl_src_side,
            self.lbl_src_track,
            self.lbl_src_catalog,
            self.lbl_src_discogs_id,
            self.lbl_src_website,
        ]

        id3_labels_target = [
            self.lbl_tar_title,
            self.lbl_tar_artist,
            self.lbl_tar_album,
            self.lbl_tar_label,
            self.lbl_tar_side,
            self.lbl_tar_track,
            self.lbl_tar_catalog,
            self.lbl_tar_discogs_id,
            self.lbl_tar_website,
        ]
        source_artwork_labels = {
            "art": self.label_source_art_type,
            "res": self.label_source_resolution,
            "size": self.label_source_size,
            "mime": self.label_source_mime,
            "desc": self.label_source_desc,
            "page": self.label_source_page_num,
            "next": self.src_image_next,
            "prev": self.src_image_prev,
        }
        target_artwork_labels = {
            "art": self.label_target_art_type,
            "res": self.label_target_resolution,
            "size": self.label_target_size,
            "mime": self.label_target_mime,
            "desc": self.label_target_desc,
            "page": self.label_target_page_num,
            "next": self.tar_image_next,
            "prev": self.tar_image_prev,
        }

        self.label_cache = {"id3": (id3_labels_source, id3_labels_target), "artwork": (source_artwork_labels, target_artwork_labels)}

    def __setup_label_style_sheet(self) -> None:
        """Set style sheet for the labels. Returns: None"""
        # Create a QFont object for the bold and italic font
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)

        source_labels, target_labels = self.label_cache.get("id3")
        # Loop over the source labels
        for label in source_labels:
            label.setFont(font)
            label.setStyleSheet("color: rgb(33, 143, 122 );")

        # Loop over the target labels
        for label in target_labels:
            label.setFont(font)
            label.setStyleSheet("color: rgb(177, 162, 86);")

    def __setup_tree_widgets(self) -> None:
        """
        Populates the id3_tags list with the names of the supported ID3 tags.
        Returns: None
        """

        self.tree_source = self.findChild(QTreeView, "tree_source")
        last_dir = self.config[CONFIG_SECTION_DIRECTORIES][CONFIG_LAST_SOURCE_DIRECTORY]
        self.__setup_tree_view(self.tree_source, last_dir)

        self.tree_target = self.findChild(QTreeView, "tree_target")
        last_dir = self.config[CONFIG_SECTION_DIRECTORIES][CONFIG_LAST_TARGET_DIRECTORY]
        self.__setup_tree_view(self.tree_target, last_dir)

    def __setup_tree_view(self, tree_view: QTreeView, last_dir) -> None:
        model = QFileSystemModel()
        model.directoryLoaded.connect(lambda: self.resize_first_column(tree_view))
        self.set_root_path_for_tree_view(model, last_dir, tree_view)
        tree_view.setRootIndex(model.index(last_dir))
        tree_view.clicked.connect(lambda: self.on_tree_clicked(tree_view.selectedIndexes()[0], tree_view))
        tree_view.doubleClicked.connect(lambda: self.on_tree_double_clicked(tree_view.selectedIndexes()[0], tree_view))
        tree_view.expanded.connect(lambda: self.resize_first_column(tree_view))
        tree_view.setSortingEnabled(True)

        # Enable custom context menu
        tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        tree_view.customContextMenuRequested.connect(self.tree_view_context_menu)

    def __setup_exit(self) -> None:
        """
        Sets up the exit functionality of the main window.
        Returns: None
        """

        mf_exit = self.findChild(QAction, "mf_exit")
        self.but_exit = self.findChild(QPushButton, "but_exit")
        self.but_exit_2 = self.findChild(QPushButton, "but_exit_2")

        mf_exit.triggered.connect(self.confirm_exit)
        self.but_exit.clicked.connect(self.confirm_exit)
        self.but_exit_2.clicked.connect(self.confirm_exit)

        icon = self.style().standardIcon(QStyle.SP_DialogCloseButton)
        mf_exit.setIcon(icon)
        self.but_exit.setIcon(icon)
        mf_exit.setShortcut("Ctrl+Q")

    def __setup_copy_source_button(self) -> None:
        """Sets up the functionality of the copy source button. Returns: None"""
        but_copy_source = self.findChild(QPushButton, "but_copy_source")
        but_copy_source.clicked.connect(self.copy_source_to_target)

    def __setup_refresh_button(self) -> None:
        """Sets up the functionality of the refresh button. Returns: None"""
        but_refresh = self.findChild(QPushButton, "but_refresh_target_2")
        but_refresh.clicked.connect(self.reset_target)

    def __setup_dir_up_buttons(self) -> None:
        """Sets up the functionality of the path up buttons. Returns: None"""
        self.findChild(QPushButton, "but_source_up").clicked.connect(lambda: self.go_up_dir_level(self.tree_source, self.path_source))
        self.findChild(QPushButton, "but_target_up").clicked.connect(lambda: self.go_up_dir_level(self.tree_target, self.path_target))

    def resize_first_column(self, tree_view: QTreeView) -> None:
        """Resize the first column of the tree view to fit the longest filename. Returns: None"""
        tree_view.resizeColumnToContents(0)

    def tree_view_context_menu(self, position):
        """Displays a context menu when right clicking on a tree view. Returns: None"""
        tree_view = self.sender()
        index = tree_view.indexAt(position)
        if not index.isValid():
            return

        file_path = tree_view.model().filePath(index)
        if not file_path.lower().endswith((".wav", ".mp3", ".ogg", ".flac")):
            return

        menu = QMenu(self)
        play_action = QAction(self.icon_play, "Play", self)
        menu.addAction(play_action)
        stop_action = QAction(self.icon_stop, "Stop", self)
        menu.addAction(stop_action)
        pause_action = QAction(self.icon_pause, "Pause", self)  # Changed "Stop" to "Pause"
        menu.addAction(pause_action)
        action = menu.exec_(tree_view.mapToGlobal(position))

        if action == play_action:
            # if the media player is already loaded with the same file and is playing, do nothing
            if self.player.currentMedia().canonicalUrl() == QUrl.fromLocalFile(file_path):
                if self.player.mediaStatus() == QMediaPlayer.PlayingState:
                    return
            else:
                self.player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))

            self.update_status(f"Playing: {file_path}")
            self.player.play()

        elif action == stop_action:
            self.player.stop()
            self.update_status(f"Stopped: {file_path}")

        elif action == pause_action:
            self.player.pause()
            self.update_status(f"Paused: {file_path}")

    def on_path_return_pressed(self, tree_view: QTreeView) -> None:
        if tree_view == self.tree_source:
            self.handle_directory(
                "Source directory not found",
                self.path_source,
                self.directory_source,
                tree_view,
            )
        else:
            self.handle_directory(
                "Target directory not found",
                self.path_target,
                self.directory_target,
                tree_view,
            )

    def handle_directory(self, error_message, path_line: QLineEdit, original_path, tree_view: QTreeView) -> None:
        """
        Handles the directory selection.
        Args:
        error_message: The error message to display if the directory is not found.
        path_line: The line edit where the path is stored.
        original_path: The original path.
        tree_view: The tree view where the directory is selected.

        Returns: None
        """

        if not os.path.isdir(path_line.text()):
            QMessageBox.critical(self, "Error", error_message)
            path_line.setText(original_path)
        else:
            self.open_directory(tree_view, path_line, path_line.text())

    def on_tree_clicked(self, item: QModelIndex, tree_view) -> None:
        """
        Displays the ID3 tags for the selected audio file in the source tree.
        Returns: None
        """
        self.display_id3_tags_when_an_item_is_selected(item, tree_view)

    def on_tree_double_clicked(self, index: QModelIndex, tree_view: QTreeView) -> None:
        model = tree_view.model()
        path = model.filePath(index)
       
        if model.isDir(index):
            self.handle_tree_double_click_dir(path, tree_view)
       
        # check if paths is a file and an image like jpg, png etc
        elif os.path.isfile(path) and path.lower().endswith((".jpg", ".png", ".jpeg")):
            # load image to a pixmap
            pixmap = QPixmap(path)
            #pop image in a new dialog
            pop_up_image_dialogue(path, pixmap)


    def handle_tree_double_click_dir(self, path: str, tree_view: QTreeView) -> None:
        model = tree_view.model()
        self.set_root_index_of_tree_view(path, tree_view)

        model.directoryLoaded.connect(lambda: self.set_root_index_of_tree_view(path, tree_view))
        model.directoryLoaded.connect(lambda: self.set_root_index_of_tree_view(path, tree_view))
        #  tree_view.expand(index)
        model.directoryLoaded.connect(lambda: self.set_root_index_of_tree_view(path, tree_view))
        #  tree_view.expand(index)

        if tree_view == self.tree_source:
            self.path_source.setText(path)
            self.directory_updated(path, ChangeType.SOURCE)
        else:
            self.path_target.setText(path)
            self.directory_updated(path, ChangeType.TARGET)

    def set_root_index_of_tree_view(self, directory, tree_view: QTreeView = None) -> None:
        """ Sets the root index of the tree view. """
        model = tree_view.model()
        tree_view.setRootIndex(model.index(directory))
        for column in range(model.columnCount()):
            tree_view.resizeColumnToContents(column)

        with contextlib.suppress(TypeError):
            model.directoryLoaded.disconnect()

    def go_up_dir_level(self, tree_view: QTreeView, path: QLineEdit) -> None:
        model = tree_view.model()
        current_root_path = model.filePath(tree_view.rootIndex())
        directory = QDir(current_root_path)
        if directory.cdUp():
            self._change_dir_up(directory, tree_view, path)

    # TODO Rename this here and in `go_up_dir_level`
    def _change_dir_up(self, directory: QDir, tree_view: QTreeView, path: QLineEdit) -> None:
        """ Changes the directory up one level. """
        parent_path = directory.absolutePath()

        model = QFileSystemModel()

        self.set_root_path_for_tree_view(model, parent_path, tree_view)
        self.set_root_index_of_tree_view(parent_path, tree_view)
        model.directoryLoaded.connect(lambda: self.resize_first_column(tree_view))

        self._set_absolute_path(path, parent_path, tree_view)

    def set_root_path_for_tree_view(self, model: QFileSystemModel, absolute_path: str, tree_view: QTreeView):
        """Sets the root path for the given tree view."""
        model.setRootPath(absolute_path)
        tree_view.setModel(model)
        tree_view.sortByColumn(0, Qt.AscendingOrder)

    def reset_target(self) -> None:
        """Resets the target directory tree structure to before any changes were made. Returns: None"""

        tree_structure_target = self.tree_structure_target_original
        self._populate_target_tree(tree_structure_target)

    def copy_source_to_target(self) -> None:
        """
        Copies the source directory to the target directory.
        Returns: None
        """
        self.open_directory(self.tree_target, self.path_target, self.path_source.text())

    def confirm_exit(self) -> None:
        """
        Confirms the exit action with the user.
        Returns: None
        """

        if self.prompt_yes_no("Exit", "Are you sure you want to exit?") == QMessageBox.No:
            return

        self.__update_config_file()

        self.application.quit()

    def __update_config_file(self) -> None:
        """
        Updates the configuration file with the current window size.
        Returns: None
        """

        # Write the window size to the config file
        self.config.set(CONFIG_SECTION_WINDOW, CONFIG_WINDOW_HIGHT, f"{self.size().height()}")
        self.config.set(CONFIG_SECTION_WINDOW, CONFIG_WINDOW_WIDTH, f"{self.size().width()}")

        # Save the config file
        with open("config.ini", "w") as config_file:
            self.config.write(config_file)

    def __setup_scan_source(self) -> None:
        """Set up the source scan button and menu item. Returns: None"""
        action_scan = self.findChild(QAction, "mf_scan")
        action_scan.triggered.connect(lambda: self.open_directory(self.tree_source, self.path_source))

        but_select_source = self.findChild(QPushButton, "but_select_source")
        but_select_source.clicked.connect(lambda: self.open_directory(self.tree_source, self.path_source))

    def __setup_scan_target(self) -> None:
        """Set up the target scan button. Returns: None"""
        but_select_target = self.findChild(QPushButton, "but_select_target")
        but_select_target.clicked.connect(lambda: self.open_directory(self.tree_target, self.path_target))

    def on_repackage_button_clicked(self) -> None:
        """Set up the repackage button. Returns: None"""
        self.repackage()

    def open_directory(self, tree_view: QTreeView, path: QLineEdit, directory=None) -> None:
        """Scan the source directory. Returns: None"""

        if not directory:
            if tree_view == self.tree_source:
                last_directory = self.config.get(
                    CONFIG_SECTION_DIRECTORIES,
                    CONFIG_LAST_SOURCE_DIRECTORY,
                    fallback="",
                )
            else:
                last_directory = self.config.get(
                    CONFIG_SECTION_DIRECTORIES,
                    CONFIG_LAST_TARGET_DIRECTORY,
                    fallback="",
                )

            directory = QFileDialog.getExistingDirectory(self, "Select Directory", last_directory)

        if not directory:
            return

        try:
            # self.tree_source.setRootIndex(self.source_model.index(QDir.rootPath()))
            # set a directory to the root path of the source tree

            tree_view.setRootIndex(tree_view.model().index(directory))
            self._set_absolute_path(path, directory, tree_view)
        except Exception as e:
            self._display_and_log_error(e)

    # TODO Rename this here and in `go_up_dir_level` and `open_directory`
    def _set_absolute_path(self, path: QLineEdit, absolute_path: str, tree_view: QTreeView):
        path.setText(absolute_path)
        changeType = ChangeType.SOURCE if tree_view == self.tree_source else ChangeType.TARGET
        self.directory_updated(absolute_path, changeType)

    def directory_updated(self, directory, changeType: ChangeType) -> None:
        """Update the source or target directory config settings, and the base reference based on the given directory."""

        if changeType.isSource():
            self.config.set(CONFIG_SECTION_DIRECTORIES, CONFIG_LAST_SOURCE_DIRECTORY, directory)
            self.directory_source = directory
        else:
            self.config.set(CONFIG_SECTION_DIRECTORIES, CONFIG_LAST_TARGET_DIRECTORY, directory)
            self.directory_target = directory

    def _display_and_log_error(self, e) -> None:
        logging.error(traceback.format_exc())
        QMessageBox.critical(self, "Error", str(e))

    def update_status(self, text) -> None:
        """Update the text in lbl_stat."""
        self.lbl_stat.setText(text)

    def update_statusbar(self, text) -> None:
        """Update the text in the status bar."""
        self.statusbar.showMessage(text)

    def prompt_yes_no(self, title, message) -> int:
        """Prompt the user for a yes or no response.
        Returns:
            QMessageBox.Yes or QMessageBox.No
        """
        return QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

    def __clear_labels(self) -> None:
        """Clears label tags . Returns: None"""
        src, tar = self.label_cache.get("id3")
        self.clear_labels(src)
        self.clear_labels(tar)
        src, tar = self.label_cache.get("artwork")
        self.clear_labels(src.values())
        self.clear_labels(tar.values())

    def clear_labels(self, labels) -> None:
        """Clears label tags . Returns: None"""
        for label in labels:
            label.setText("")

    def display_id3_tags_when_an_item_is_selected(self, item: QModelIndex, tree_view: QTreeView) -> None:
        """
        Displays source or Target audio tag labels when a user selects an audio
        file in a tree widget.
        Returns: None
        """

        absolute_filename = tree_view.model().filePath(item)

        if not self.audio_tags.isSupported(absolute_filename):
            return

        self._display_id3_tags(absolute_filename, tree_view)
        self._display_cover_artwork(absolute_filename, tree_view)

    def _display_cover_artwork(self, absolute_file_path: str, tree_view: QTreeView) -> None:
        # Get artwork from the audio tags
        cover_art_images = self.audio_tags.get_cover_art(absolute_file_path)

        stacked_widget = self.stacked_widget_target if tree_view == self.tree_target else self.stacked_widget_source

        # Clear the QStackedWidget
        while stacked_widget.count() > 0:
            widget = stacked_widget.widget(0)
            stacked_widget.removeWidget(widget)
            widget.deleteLater()

            # Add the cover art images to the QStackedWidget
        for image in cover_art_images:
            pixmap = QPixmap()
            pixmap.loadFromData(image.data)
            label = ImageLabel(pixmap, image)
            stacked_widget.addWidget(label)

        # Store the sizes of the images in bytes in a list
        self.image_sizes = [len(image.data) for image in cover_art_images]

        label_map = self.get_labels(tree_view, "artwork")
        page_number_label = label_map.get("page")

        page_number_label.setText(f"{stacked_widget.currentIndex() + 1} / {stacked_widget.count()}")
        stacked_widget.setCurrentIndex(0)
        label_map.get("next").clicked.connect(lambda: stacked_widget.setCurrentIndex((stacked_widget.currentIndex() + 1) % stacked_widget.count()))
        label_map.get("prev").clicked.connect(lambda: stacked_widget.setCurrentIndex((stacked_widget.currentIndex() - 1) % stacked_widget.count()))

        stacked_widget.currentChanged.connect(lambda: page_number_label.setText(f"{stacked_widget.currentIndex() + 1} / {stacked_widget.count()}"))
        stacked_widget.currentChanged.connect(lambda: self.update_image_labels(stacked_widget, label_map))

    def update_image_labels(self, stacked_widget: QStackedWidget, label_map: Dict[str, int]) -> None:
        # Get the current pixmap
        widget = stacked_widget.currentWidget()

        if widget is None:
            return

        pixmap = widget.pixmap

        # Update the resolution label
        resolution = f"{pixmap.width()}x{pixmap.height()}"
        label_map.get("res").setText(resolution)

        # Update the size label
        current_index = stacked_widget.currentIndex()
        if current_index > 0:
            size = self.image_sizes[current_index] / 1024  # size in KB
            label_map.get("size").setText(f"{size:.2f} KB")

        label_map.get("art").setText(PictureTypeDescription.get_description(widget.image.type))
        label_map.get("mime").setText(widget.image.mime)
        label_map.get("desc").setText(widget.image.desc)

    def _display_id3_tags(self, absolute_file_path: str, tree_view: QTreeView) -> None:
        labels = self.get_labels(tree_view, "id3")

        # Get the ID3 tags for the selected file from AudioTags
        audio_tags = self.audio_tags.get_tags(absolute_file_path)

        for label, tag in zip(labels, self.id3_tags):
            value = audio_tags[tag][0] if tag in audio_tags else ""

            if tag == "URL":
                label.setText(f'<a href="{value}">{value}</a>')
            else:
                label.setText(value)

    def get_labels(self, tree_view: QTreeView, label_type: str) -> Union[list, dict]:
        """Returns a list or dictionary of source or target labels based on label_type."""
        source, target = self.label_cache.get(label_type, (None, None))
        return source if tree_view == self.tree_source else target

    def resizeColumns(self) -> None:
        """Resize the columns of the tree widget. Returns: None"""
        for i in range(self.sender().columnCount()):
            self.sender().resizeColumnToContents(i)

    def check_directory_scanned(self, directory, error_message):
        if directory is None:
            QMessageBox.critical(self, "Error", error_message)
            return False
        return True

    def repackage(self) -> None:
        """moves the files from the source directory to the target directory based on the LABEL tag. Returns: None"""

        source_dir = self.tree_source.model().rootPath()
        target_dir = self.tree_target.model().rootPath()

        if not self.check_directory_scanned(source_dir, "Source directory not scanned"):
            return

        if not self.check_directory_scanned(target_dir, "Target directory not scanned"):
            return

        self.update_status("Repackaging started...")
        repackageByLabel(source_dir, target_dir)

    def toggleMenu(self) -> None:
        width = self.frame_left_menu.width()
        maxExtend = 100

        widthExtended = maxExtend if width == 0 else 0
        self.animation = QPropertyAnimation(self.frame_left_menu, b"minimumWidth")
        self.animation.setDuration(400)
        self.animation.setStartValue(width)
        self.animation.setEndValue(widthExtended)
        self.animation.setEasingCurve(QEasingCurve.InOutQuart)
        self.animation.start()

        icon = self.icon_left if width == 0 else self.icon_menu
        self.but_toggle.setIcon(icon)

        tooltip = "Close Menu" if width <= 0 else "Open Menu"
        self.but_toggle.setToolTip(tooltip)
        self.but_toggle.setToolTipDuration(1000 if width <= 0 else 0)

    def handle_media_status_changed(self, status):
        """
        Handle changes in media player status.

        Show error message if media is invalid.
        """

        if status == QMediaPlayer.InvalidMedia:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setWindowTitle("Error")
            msgBox.setText(INVALID_MEDIA_ERROR_MSG)
            msgBox.setTextFormat(Qt.RichText)
            msgBox.exec()


if __name__ == "__main__":
    # Create an instance of MainWindow
    main_window = MainWindow(app)

    # Display the main window
    main_window.show()

    # Start the application event loop
    app.exec_()
