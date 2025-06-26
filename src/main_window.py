import configparser
import os
import traceback
from typing import Dict, Union, cast

import winshell
from PyQt5 import uic, QtGui
from PyQt5.QtCore import QSize, QPropertyAnimation, QEasingCurve, Qt, QDir, QModelIndex, QPoint
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtWidgets import (
    QStackedWidget,
    QApplication,
    QMainWindow,
    QAction,
    QStyle,
    QTreeView,
    QFileDialog,
    QPushButton,
    QMessageBox,
    QCompleter,
    QFileSystemModel, QSlider,
)
from mutagen.id3 import PictureType

from file_operations.audio_tags import AudioTagHelper, PictureTypeDescription
from file_operations.file_utils import ask_and_move_files, ask_and_copy_files
from file_operations.repackage_dir import repackage_dir_by_label
# Set logger instance
from log_config import get_logger
from path_helper import get_absolute_path_config
from ui.custom_image_label import ImageLabel
from ui.custom_line_edit import MyLineEdit
from ui.custom_tree_view import MyTreeView
from ui.custom_tree_view_context_menu_handler import TreeViewContextMenuHandler
from ui.custom_waveform_widget import WaveformWidget
from ui.db_window import DatabaseWindow
from ui.recycle import RestoreDialog
from ui.settings_dialogue import SettingsDialog

logger = get_logger("mc.main_window")

# Create an instance of QApplication
app = QApplication([])

# define constants
ICON_INDEX = 0
CONFIG_SECTION_DIRECTORIES = "Directories"
CONFIG_SECTION_WINDOW = "Window"
CONFIG_WINDOW_HEIGHT = "height"
CONFIG_WINDOW_WIDTH = "Width"
CONFIG_LAST_TARGET_DIRECTORY = "last_target_directory"
CONFIG_LAST_SOURCE_DIRECTORY = "last_source_directory"
INVALID_MEDIA_ERROR_MSG = 'Failed to play the media file. You might need to install the K-Lite Codec Pack. You can download it from the official website:<br><a href="https://www.codecguide.com/download_kl.htm">https://www.codecguide.com/download_kl.htm</a>'
# Create a dictionary that maps picture type numbers to descriptions
PICTURE_TYPES = {value: key for key, value in vars(PictureType).items() if not key.startswith("_")}


# TODO: database integration - in progress
# TODO: fix the artwork display
# TODO: add a settings dialog
# TODO: complete settings management - create a config manager

class MainWindow(QMainWindow):
    """Main window class for the application."""

    def __init__(self, application):
        """Initialize the main window."""
        super().__init__()
        self.animation = None
        self.application = application

        # Set up instance variables
        self.config = configparser.ConfigParser()
        self.id3_tags = []
        self.audio_tags = AudioTagHelper()
        self.player = QMediaPlayer()

        # set up config
        self.__setup_config()

        # Set up the user interface from Designer.
        # Load the .ui file and set up the UI
        uic.loadUi(
            "src\\qt\\music_manager.ui",
            self,
        )
        self.__setup_ui()

    def __setup_ui(self):
        """Set up the user interface. Returns: None"""
        # Sets up the user interface of the main window.
        self.update_status("Welcome - select a directory to scan either from the menu or the scan button")
        self.__setup_icons()
        self.__setup_media_player()
        self.__setup_context_menus()
        self.__setup_window_size()
        self.__setup_exit()
        self.__setup_open_dir_browsers()
        self.__setup_copy_dir_view()
        self.__setup_path_info_bar()
        self.__setup_wave_form_widget()
        self.__setup_tree_widgets()
        self.__setup_id3_tags()
        self.__setup_label_cache()
        self.__setup_label_style_sheet()
        self.__clear_labels()
        self.__setup_action_buttons()
        self.__setup_menu_buttons()
        self.__setup_dir_up_buttons()
        self.__setup_slider()

    #  self.__setup_mp3tag_path()

    def __setup_context_menus(self):
        """Set up the context menus for the tree views. Returns: None"""
        self.tree_view_cm_handler = TreeViewContextMenuHandler(self.player, self.update_status)

    def __setup_media_player(self) -> None:
        """Sets up the media player. Returns: None"""
        self.player.mediaStatusChanged.connect(self.handle_media_status_changed)  # type: ignore[attr-defined]

    def __setup_config(self) -> None:
        """Sets up the configuration by reading the config.ini file and adding missing sections if necessary. Returns: None"""

        self.config.read(get_absolute_path_config())
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

    def __setup_path_info_bar(self) -> None:
        """Set up the path labels. Returns: None"""
        # Create a file system model
        model = QFileSystemModel()
        model.setRootPath(QDir.rootPath())

        # Create a completer with the model
        completer = QCompleter()
        completer.setModel(model)

        # Set the completer for the MyLineEdit
        self.path_info_bar_source = self.findChild(MyLineEdit, "path_source")
        self.path_info_bar_source.setCompleter(completer)

        self.path_info_bar_target = self.findChild(MyLineEdit, "path_target")
        self.path_info_bar_target.setCompleter(completer)

        self.path_info_bar_source.returnPressed.connect(lambda: self.on_path_info_bar_return_pressed(self.tree_source, self.path_info_bar_source))
        self.path_info_bar_target.returnPressed.connect(lambda: self.on_path_info_bar_return_pressed(self.tree_target, self.path_info_bar_target))
        self.path_info_bar_source.setText(self.config[CONFIG_SECTION_DIRECTORIES][CONFIG_LAST_SOURCE_DIRECTORY])
        self.path_info_bar_target.setText(self.config[CONFIG_SECTION_DIRECTORIES][CONFIG_LAST_TARGET_DIRECTORY])

    def __setup_icons(self) -> None:
        """Set up the icons. Returns: None"""

        self.icon_left = QtGui.QIcon(":/icons/icons/chevrons-left.svg")
        self.icon_right = QtGui.QIcon(":/icons/icons/chevrons-right.svg")
        self.icon_menu = QtGui.QIcon(":/icons/icons/menu.svg")
        self.icon_repackage = QtGui.QIcon(":/icons/icons/package.svg")
        self.icon_move = QtGui.QIcon(":/icons/icons/move.svg")
        self.icon_exit = QtGui.QIcon(":/icons/icons/log-out.svg")

    def __setup_menu_buttons(self) -> None:
        """Set up the menu buttons. Returns: None"""
        # toggle menu
        self.frame_left_menu.setMinimumWidth(0)
        self.but_toggle = self.findChild(QPushButton, "but_toggle")
        self.but_toggle.clicked.connect(lambda: self.toggle_menu())
        self.but_toggle.setToolTip("Open Menu")
        self.but_toggle.setToolTipDuration(1000)
        self.but_toggle.setIcon(self.icon_menu)
        self.but_toggle.setShortcut("Ctrl+M")
        self.but_exit.setIcon(QtGui.QIcon(self.icon_exit.pixmap(40, 40)))

    def __setup_action_buttons(self) -> None:
        """Set up the action buttons. Returns: None"""
        # repackage button
        self.but_repackage_src = self.findChild(QPushButton, "butt_repackage_source")
        self.but_repackage_src.clicked.connect(lambda: self.on_repackage_button_clicked(self.tree_source, self.tree_target))
        self.but_repackage_src.setToolTip("[Ctrl+R] Repackage the source directory -> target directory")
        self.but_repackage_src.setToolTipDuration(1000)
        self.but_repackage_src.setShortcut("Ctrl+R")

        self.but_repackage_tar = self.findChild(QPushButton, "butt_repackage_target")
        self.but_repackage_tar.clicked.connect(lambda: self.on_repackage_button_clicked(self.tree_target, self.tree_source))
        self.but_repackage_tar.setToolTip("[Ctrl+Shift+R] Repackage the target directory -> source directory")
        self.but_repackage_tar.setToolTipDuration(1000)
        self.but_repackage_tar.setShortcut("Ctrl+R")

        self.but_restore = self.findChild(QPushButton, "but_restore")
        self.but_restore.clicked.connect(lambda: self.on_restore_button_clicked())
        self.but_restore.setToolTip("[Ctrl+T] Restore from the recycle bin")
        self.but_restore.setToolTipDuration(1000)
        self.but_restore.setShortcut("Ctrl+T")

        self.but_move_to_target = self.findChild(QPushButton, "but_move_to_target")
        self.but_move_to_target.clicked.connect(lambda: self.on_move_button_clicked(self.tree_source, self.tree_target))
        self.but_move_to_target.setToolTip("[Ctrl+M] Move the select items in the source directory -> target directory")
        self.but_move_to_target.setToolTipDuration(1000)
        self.but_move_to_target.setShortcut("Ctrl+M")

        self.but_move_to_source = self.findChild(QPushButton, "but_move_to_source")
        self.but_move_to_source.clicked.connect(lambda: self.on_move_button_clicked(self.tree_target, self.tree_source))
        self.but_move_to_source.setToolTip("[Ctrl+shift+M] Move the select items in the target directory -> source directory")
        self.but_move_to_source.setToolTipDuration(1000)
        self.but_move_to_source.setShortcut("Ctrl+shift+M")

        self.but_copy_to_target = self.findChild(QPushButton, "but_copy_to_target")
        self.but_copy_to_target.clicked.connect(lambda: self.on_copy_button_clicked(self.tree_source, self.tree_target))
        self.but_copy_to_target.setToolTip("[Ctrl+P] Copy the select items in the source directory -> target directory")
        self.but_copy_to_target.setToolTipDuration(1000)
        self.but_copy_to_target.setShortcut("Ctrl+P")

        self.but_copy_to_source = self.findChild(QPushButton, "but_copy_to_source")
        self.but_copy_to_source.clicked.connect(lambda: self.on_copy_button_clicked(self.tree_target, self.tree_source))
        self.but_copy_to_source.setToolTip("[Ctrl+shift+C] Copy the select items in the target directory -> target directory")
        self.but_copy_to_source.setToolTipDuration(1000)
        self.but_copy_to_source.setShortcut("Ctrl+shift+C")

        self.but_settings = self.findChild(QPushButton, "but_settings")
        self.but_settings.clicked.connect(lambda: self.on_settings_button_clicked())
        self.but_settings.setToolTip("[Ctrl+S] Open the settings dialog")
        self.but_settings.setToolTipDuration(1000)
        self.but_settings.setShortcut("Ctrl+S")

        self.but_db = self.findChild(QPushButton, "but_db")
        self.but_db.clicked.connect(lambda: self.on_db_button_clicked())
        self.but_db.setToolTip("[Ctrl+D] Open the database dialog")
        self.but_db.setToolTipDuration(1000)
        self.but_db.setShortcut("Ctrl+D")

    def __setup_window_size(self) -> None:
        """Sets up the size of the main window based on the configuration settings. Returns: None"""
        self.resize(
            self.config.getint(CONFIG_SECTION_WINDOW, CONFIG_WINDOW_WIDTH, fallback=800),
            self.config.getint(CONFIG_SECTION_WINDOW, CONFIG_WINDOW_HEIGHT, fallback=600),
        )

        self.setMinimumSize(QSize(800, 600))

    def __setup_id3_tags(self) -> None:
        """Populates the id3_tags list with the names of the supported ID3 tags. Returns: None"""

        self.id3_tags = [
            AudioTagHelper.TITLE,
            AudioTagHelper.ARTIST,
            AudioTagHelper.ALBUM,
            AudioTagHelper.LABEL,
            AudioTagHelper.DISC_NUMBER,
            AudioTagHelper.TRACK_NUMBER,
            AudioTagHelper.CATALOGNUMBER,
            AudioTagHelper.DISCOGS_RELEASE_ID,
            # AudioTagHelper.URL,
            AudioTagHelper.ALBUM_ARTIST,
            AudioTagHelper.YEAR,
            AudioTagHelper.GENRE,
            AudioTagHelper.MEDIA,
            AudioTagHelper.STYLE,
            AudioTagHelper.COUNTRY,
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

            self.lbl_src_album_artist,
            self.lbl_src_date,
            self.lbl_src_genre,
            self.lbl_src_media,
            self.lbl_src_style,
            self.lbl_src_country,
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

            self.lbl_tar_album_artist,
            self.lbl_tar_date,
            self.lbl_tar_genre,
            self.lbl_tar_media,
            self.lbl_tar_style,
            self.lbl_tar_country,
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
        """Populates the id3_tags list with the names of the supported ID3 tags. Returns: None"""

        self.tree_source = self.findChild(MyTreeView, "tree_source")
        last_dir = self.config[CONFIG_SECTION_DIRECTORIES][CONFIG_LAST_SOURCE_DIRECTORY]
        self.__set_tree_actions(self.tree_source, last_dir, self.path_info_bar_source)
        self.tree_target = self.findChild(MyTreeView, "tree_target")
        last_dir = self.config[CONFIG_SECTION_DIRECTORIES][CONFIG_LAST_TARGET_DIRECTORY]
        self.__set_tree_actions(self.tree_target, last_dir, self.path_info_bar_target)
        if self.waveform_widget:
            self.tree_source.set_waveform_callback(self.waveform_widget.load_waveform_from_file)
            self.tree_target.set_waveform_callback(self.waveform_widget.load_waveform_from_file)

    def __set_tree_actions(self, tree_view: MyTreeView, last_dir: str, path_bar: MyLineEdit) -> None:
        tree_view.setup_tree_view(last_dir)
        tree_view.set_single_click_handler(self.on_tree_clicked)
        tree_view.set_double_click_handler(lambda index, clicked_tree, _: self.on_tree_double_clicked(index, clicked_tree, path_bar))
        tree_view.set_custom_context_menu(self.on_context_menu_requested)

    def __setup_exit(self) -> None:
        """Sets up the exit button. Returns: None"""
        mf_exit = self.findChild(QAction, "mf_exit")
        self.but_exit = self.findChild(QPushButton, "but_exit")
        self.but_exit_2 = self.findChild(QPushButton, "but_exit_2")

        mf_exit.triggered.connect(self.confirm_exit)
        self.but_exit.clicked.connect(self.confirm_exit)
        self.but_exit_2.clicked.connect(self.confirm_exit)

        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton)
        mf_exit.setIcon(icon)
        self.but_exit.setIcon(icon)
        mf_exit.setShortcut("Ctrl+Q")

    def __setup_copy_dir_view(self) -> None:
        """Sets up the functionality of the copy dir buttons. Returns: None"""
        but_copy_source = self.findChild(QPushButton, "but_copy_source")
        but_copy_source.clicked.connect(lambda: self.copy_dir_tree_view(self.tree_target, self.path_info_bar_target, self.tree_source.get_root_dir()))
        but_copy_target = self.findChild(QPushButton, "but_copy_target")
        but_copy_target.clicked.connect(lambda: self.copy_dir_tree_view(self.tree_source, self.path_info_bar_source, self.tree_target.get_root_dir()))

    def __setup_dir_up_buttons(self) -> None:
        """Sets up the functionality of the path up buttons. Returns: None"""
        self.findChild(QPushButton, "but_source_up").clicked.connect(lambda: self.go_up_dir_level(self.tree_source, self.path_info_bar_source))
        self.findChild(QPushButton, "but_target_up").clicked.connect(lambda: self.go_up_dir_level(self.tree_target, self.path_info_bar_target))

    def __setup_wave_form_widget(self) -> None:
        """Sets up the waveform widget. Returns: None"""
        self.waveform_widget = self.findChild(WaveformWidget, "waveform_widget")
        if not self.waveform_widget:
            logger.fatal("WaveformWidget not found in the UI")
            sys.exit(1)

    def __setup_slider(self) -> None:
        """Sets up the slider for the waveform widget. Returns: None"""
        self.slider = self.findChild(QSlider, "slider_waveform")
        if self.slider is None:
            logger.error("Slider 'slider_waveform' not found in the UI")
            sys.exit(1)
        if not hasattr(self, "waveform_widget") or self.waveform_widget is None:
            logger.error("WaveformWidget is not initialized before setting slider")
            sys.exit(1)

        self.slider.setMinimum(0)
        self.slider.setMaximum(1000)  # Increase for finer granularity
        self.slider.setSingleStep(1)  # Smallest possible step
        self.waveform_widget.set_slider(self.slider)
        self.slider.valueChanged.connect(self.on_slider_moved)

    def on_slider_moved(self, value):
        # Map slider value to waveform position
        min_val, max_val = self.slider.minimum(), self.slider.maximum()
        if max_val == min_val:
            rel_pos = 0.0
        else:
            rel_pos = (value - min_val) / (max_val - min_val)
        self.waveform_widget.set_needle_position(rel_pos)

    def on_context_menu_requested(self, tree_view: MyTreeView, position: QPoint):

        index = tree_view.indexAt(position)

        if tree_view == self.tree_source:
            other_tree = self.tree_target
        else:
            other_tree = self.tree_source

        self.tree_view_cm_handler.show_menu(tree_view, index, position, other_tree)

    @staticmethod
    def on_move_button_clicked(from_tree: MyTreeView, to_tree: MyTreeView) -> None:
        """Move files from the source directory to the target directory. Returns: None"""
        logger.info(f"Moving files from '{from_tree.get_root_dir()}' to '{to_tree.get_root_dir()}'")
        selected_files = from_tree.get_selected_files(True)
        ask_and_move_files(selected_files, from_tree.get_root_dir(), to_tree.get_root_dir())

    @staticmethod
    def on_copy_button_clicked(from_tree: MyTreeView, to_tree: MyTreeView) -> None:
        """Copy files from the source directory to the target directory. Returns: None"""
        logger.info(f"Copying files from '{from_tree.get_root_dir()}' to '{to_tree.get_root_dir()}'")
        selected_files = from_tree.get_selected_files(True)
        ask_and_copy_files(selected_files, to_tree.get_root_dir())

    @staticmethod
    def on_restore_button_clicked() -> None:
        """Restore files from the recycle bin. Returns: None"""

        r = list(winshell.recycle_bin())  # this lists the original path of all the all items in the recycling bin
        logger.info(f"Recycle bin: '{r}'")

        RestoreDialog().exec_()

    def on_tree_clicked(self, item: QModelIndex, tree_view: MyTreeView) -> None:
        """Handles the tree view click event. Returns: None"""
        self.display_id3_tags_when_an_item_is_selected(item, tree_view)

    @staticmethod
    def on_tree_double_clicked(index: QModelIndex, tree_view: MyTreeView, info_bar: MyLineEdit) -> None:
        """Handles the tree view double click event. Returns: None"""
        tree_view.on_tree_double_clicked(index)
        info_bar.setText(tree_view.get_root_dir())

    def on_path_info_bar_return_pressed(self, tree_view: MyTreeView, path_info_bar: MyLineEdit) -> None:
        """Handles the directory when the return key is pressed. Returns: None"""

        if not os.path.isdir(path_info_bar.text()):
            QMessageBox.critical(self, "Error", "Directory doesn't exist")
            path_info_bar.setText(tree_view.get_root_dir())
        else:
            tree_view.change_dir(os.path.normpath(path_info_bar.text()))

    @staticmethod
    def on_settings_button_clicked() -> None:
        """Handles the settings button click event. Returns: None"""
        logger.info("Opening the settings dialog")
        SettingsDialog().exec_()

    def on_db_button_clicked(self) -> None:
        """Handles the database button click event. Returns: None"""
        logger.info("Opening the database dialog")
        source_path = self.tree_source.get_root_dir()  # get the path from the source treeview
        DatabaseWindow(source_path).show()

    @staticmethod
    def go_up_dir_level(tree_view: MyTreeView, path_bar: MyLineEdit) -> None:

        tree_view.go_up_one_dir_level()
        path_bar.setText(tree_view.get_root_dir())

    def copy_dir_tree_view(self, tree_view: MyTreeView, path_info_bar: MyLineEdit, directory: str) -> None:
        """Copies the source directory to the target directory. Returns: None"""
        tree_view.change_dir(directory)
        path_info_bar.setText(self.tree_target.get_root_dir())

    def confirm_exit(self) -> None:
        """Confirms the exit of the application. Returns: None"""

        if self.prompt_yes_no("Exit", "Are you sure you want to exit?") == QMessageBox.No:
            return

        self.hide()
        self.__update_config_file()
        self.application.quit()

    def __update_config_file(self) -> None:
        """Updates the config file with the current window size and position. Returns: None"""

        # Write the window size to the config file
        self.config.set(CONFIG_SECTION_WINDOW, CONFIG_WINDOW_HEIGHT, f"{self.size().height()}")
        self.config.set(CONFIG_SECTION_WINDOW, CONFIG_WINDOW_WIDTH, f"{self.size().width()}")
        self.config.set(CONFIG_SECTION_DIRECTORIES, CONFIG_LAST_SOURCE_DIRECTORY, self.path_info_bar_source.text())
        self.config.set(CONFIG_SECTION_DIRECTORIES, CONFIG_LAST_TARGET_DIRECTORY, self.path_info_bar_target.text())

        # Save the config file
        with open(get_absolute_path_config(), "w") as config_file:
            self.config.write(config_file)

    def __setup_open_dir_browsers(self) -> None:
        """Set up the open dir browsers. Returns: None"""
        but_select_source = self.findChild(QPushButton, "but_select_source")
        but_select_source.clicked.connect(lambda: self.open_directory_browser(self.tree_source, self.path_info_bar_source))

        but_select_target = self.findChild(QPushButton, "but_select_target")
        but_select_target.clicked.connect(lambda: self.open_directory_browser(self.tree_target, self.path_info_bar_target))

    def open_directory_browser(self, tree_view: MyTreeView, path: MyLineEdit) -> None:
        """Open directory browser. Returns: None"""

        if directory := QFileDialog.getExistingDirectory(self, "Select Directory", tree_view.get_root_dir(), QFileDialog.ShowDirsOnly):
            tree_view.change_dir(directory)
            path.setText(directory)

    def on_repackage_button_clicked(self, tree_source: MyTreeView, tree_target: MyTreeView) -> None:
        """Set up the repackage button. Returns: None"""
        self.repackage(tree_source, tree_target)

    def _display_and_log_error(self, err: Exception) -> None:
        """Displays the error message and logs the error to the log file. Returns: None"""
        logger.error(traceback.format_exc())
        QMessageBox.critical(self, "Error", str(err))

    def update_status(self, text: str) -> None:
        """Update the text in lbl_stat."""
        self.lbl_stat.setText(text)

    def update_statusbar(self, text: str) -> None:
        """Update the text in the status bar."""
        self.statusbar.showMessage(text)

    def prompt_yes_no(self, title: str, message: str) -> int:
        """Displays a yes/no prompt to the user. Returns: QMessageBox.Yes or QMessageBox.No"""
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

    @staticmethod
    def clear_labels(labels) -> None:
        """Clears label tags . Returns: None"""
        for label in labels:
            label.setText("")

    def display_id3_tags_when_an_item_is_selected(self, item: QModelIndex, tree_view: QTreeView) -> None:
        """Displays the ID3 tags for the selected audio file in the source tree. Returns: None"""

        model = cast(QFileSystemModel, tree_view.model())
        absolute_filename = model.filePath(item)

        if not self.audio_tags.isSupportedAudioFile(absolute_filename):
            return

        self._display_id3_tags(absolute_filename, tree_view)
        self._display_cover_artwork(absolute_filename, tree_view)

    def _display_cover_artwork(self, absolute_file_path: str, tree_view: QTreeView) -> None:
        """Displays the cover artwork for the selected audio file in the source tree. Returns: None"""
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
            pixmap.loadFromData(image.data)  # type: ignore[attr-defined]
            label = ImageLabel(pixmap, image)
            stacked_widget.addWidget(label)

        # Store the sizes of the images in bytes in a list
        self.image_sizes = [len(image.data) for image in cover_art_images]  # type: ignore[attr-defined]

        label_map = self.get_labels(tree_view, "artwork")
        page_number_label = label_map.get("page")

        page_number_label.setText(f"{stacked_widget.currentIndex() + 1} / {stacked_widget.count()}")
        stacked_widget.setCurrentIndex(0)
        label_map.get("next").clicked.connect(lambda: stacked_widget.setCurrentIndex((stacked_widget.currentIndex() + 1) % stacked_widget.count()))
        label_map.get("prev").clicked.connect(lambda: stacked_widget.setCurrentIndex((stacked_widget.currentIndex() - 1) % stacked_widget.count()))

        stacked_widget.currentChanged.connect(lambda: page_number_label.setText(f"{stacked_widget.currentIndex() + 1} / {stacked_widget.count()}"))
        stacked_widget.currentChanged.connect(lambda: self.update_image_labels(stacked_widget, label_map))

    def update_image_labels(self, stacked_widget: QStackedWidget, label_map: Dict[str, int]) -> None:
        """Update the image labels when the current index of the stacked widget changes."""
        # Get the current pixmap
        widget = stacked_widget.currentWidget()

        if widget is None:
            return

        pixmap = widget.pixmap

        # Update the resolution label
        resolution = f"{pixmap.width()}x{pixmap.height()}"
        label_map.get("res").setText(resolution)  # type: ignore[attr-defined]

        # Update the size label
        current_index = stacked_widget.currentIndex()
        if current_index > 0:
            size = self.image_sizes[current_index] / 1024  # size in KB
            label_map.get("size").setText(f"{size:.2f} KB")  # type: ignore[attr-defined]

        label_map.get("art").setText(PictureTypeDescription.get_description(widget.image.type))
        label_map.get("mime").setText(widget.image.mime)  # type: ignore[attr-defined]
        label_map.get("desc").setText(widget.image.desc)  # type: ignore[attr-defined]

    def _display_id3_tags(self, absolute_file_path: str, tree_view: QTreeView) -> None:
        """Displays the ID3 tags for the selected audio file in the source tree. Returns: None"""

        labels = self.get_labels(tree_view, "id3")

        # Get the ID3 tags for the selected file from AudioTags
        audio_tags = self.audio_tags.get_tags(absolute_file_path)
        url = audio_tags.get(AudioTagHelper.URL, [""])[0]  # Get the URL if present

        for label, tag in zip(labels, self.id3_tags):
            value = self.get_tag_value(tag, audio_tags)
            if tag == AudioTagHelper.DISCOGS_RELEASE_ID and url:
                label.setText(f'<a href="{url}">{value}</a>')
                label.setOpenExternalLinks(True)
            else:
                label.setText(value)

    @staticmethod
    def get_tag_value(tag, audio_tags):
        """Helper function to get the tag value, including alternative tag names for catalog number."""
        if tag in audio_tags:
            return audio_tags[tag][0]
        if tag == AudioTagHelper.CATALOGNUMBER:
            if AudioTagHelper.CATALOG_NUMBER in audio_tags:
                return audio_tags[AudioTagHelper.CATALOG_NUMBER][0]
            if AudioTagHelper.CATALOGID in audio_tags:
                return audio_tags[AudioTagHelper.CATALOGID][0]
        return ""

    def get_labels(self, tree_view: QTreeView, label_type: str) -> Union[list, dict]:
        """Returns a list or dictionary of source or target labels based on label_type."""
        source, target = self.label_cache.get(label_type, (None, None))
        return source if tree_view == self.tree_source else target

    def repackage(self, tree_source: MyTreeView, tree_target: MyTreeView) -> None:
        """moves the files from the source directory to the target directory based on the LABEL tag. Returns: None"""

        source_dir = tree_source.get_root_dir()
        target_dir = tree_target.get_root_dir()

        self.update_status("Repackaging started...")
        logger.info("Repackaging started...")
        repackage_dir_by_label(source_dir, target_dir)
        logger.info("Repackaging finished...")

    def toggle_menu(self) -> None:
        """Toggles the left menu. Returns: None"""
        width = self.frame_left_menu.width()
        max_extend = 100

        width_extended = max_extend if width == 0 else 0
        self.animation = QPropertyAnimation(self.frame_left_menu, b"minimumWidth")
        self.animation.setDuration(400)
        self.animation.setStartValue(width)
        self.animation.setEndValue(width_extended)
        self.animation.setEasingCurve(QEasingCurve.InOutQuart)
        self.animation.start()

        icon = self.icon_left if width == 0 else self.icon_menu
        self.but_toggle.setIcon(icon)

        tooltip = "Close Menu" if width <= 0 else "Open Menu"
        self.but_toggle.setToolTip(tooltip)
        self.but_toggle.setToolTipDuration(1000 if width <= 0 else 0)

    @staticmethod
    def handle_media_status_changed(status):
        """Handles the media status changed event."""
        if status == QMediaPlayer.InvalidMedia:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("Error")
            msg_box.setText(INVALID_MEDIA_ERROR_MSG)
            msg_box.setTextFormat(Qt.RichText)
            msg_box.exec()


if __name__ == "__main__":

    import sys

    exit_code = 0
    try:
        # Create an instance of MainWindow
        main_window = MainWindow(app)

        # Display the main window
        main_window.show()

        # Start the application event loop
        app.exec_()

    except Exception as e:
        logger.exception("Unhandled exception: %s", e)
        logger.error(traceback.format_exc())
        exit_code = 1

    finally:
        logger.info("Application exited")
        app.quit()
    sys.exit(exit_code)
