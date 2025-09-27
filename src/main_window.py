import configparser
import os
import traceback
from typing import Dict, Union, cast

import winshell
from PyQt5 import uic, QtGui
from PyQt5.QtCore import QSize, QPropertyAnimation, QEasingCurve, QDir, QModelIndex, QPoint
from PyQt5.QtGui import QFont, QPixmap, QIcon
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
    QWidget,
    QFileSystemModel, QMenu,
)
from mutagen.id3 import PictureType

from file_operations.audio_tags import AudioTagHelper, PictureTypeDescription
from file_operations.file_utils import ask_and_move_files, ask_and_copy_files
from file_operations.repackage_dir import repackage_dir_by_label
from log_config import get_logger
from path_helper import get_absolute_path_config
from ui.custom_image_label import ImageLabel
from ui.custom_line_edit import MyLineEdit
from ui.custom_tree_view import MyTreeView
from ui.custom_tree_view_context_menu_handler import TreeViewContextMenuHandler
from ui.db_window import DatabaseWindow
from ui.db_media_window import DatabaseMediaWindow
from ui.media_player import MediaPlayerController
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
CONFIG_LAST_RIGHT_DIRECTORY = "last_right_directory"
CONFIG_LAST_LEFT_DIRECTORY = "last_left_directory"

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
        self.default_path = "C:/"
        super().__init__()
        self.animation = None
        self.application = application

        # Set up instance variables
        self.config = configparser.ConfigParser()
        self.id3_tags = []
        self.audio_tags = AudioTagHelper()
        self.player = QMediaPlayer(self)
        # self.player.setNotifyInterval(50)
        self._user_is_sliding = False

        # set up config
        self.__setup_config()

        # Set up the user interface from Designer.
        # Load the .ui file and set up the UI
        uic.loadUi(
            "src\\qt\\music_manager.ui",
            self,
        )
        self.__setup_ui()
        self.db_window.setup_ui("C:/")
        self.db_media_window.setup_ui()

    def __setup_ui(self):
        """Set up the user interface. Returns: None"""
        self.stack_page_view.setCurrentIndex(0)  # default to file view with media player
        self.__setup_icons()
        self.__setup_decks()
        self.__setup_context_menus()
        self.__setup_window_size()
        self.__setup_exit()
        self.__setup_open_dir_browsers()
        self.__setup_copy_dir_view()
        self.__setup_path_info_bar()
        self.__setup_tree_widgets()
        self.__setup_id3_tags()
        self.__setup_label_cache()
        self.__setup_label_style_sheet()
        self.__clear_labels()
        self.__setup_action_buttons()
        self.__setup_menu_buttons()
        self.__setup_dir_up_buttons()

    #  self.__setup_mp3tag_path()

    def __setup_context_menus(self):
        """Set up the context menus for the tree views. Returns: None"""
        self.tree_view_cm_handler = TreeViewContextMenuHandler(self.player)

    def __setup_decks(self) -> None:
        """Sets up the media players. Returns: None"""
        self.player_a = MediaPlayerController(self, self.slider_a, self.wdgt_wave_a, self.butt_play_a, self.butt_stop_a, self.lbl_current_a, self.lbl_duration_a,
                                              self.lbl_info_a, self.lbl_cover_a)
        self.player_b = MediaPlayerController(self, self.slider_b, self.wdgt_wave_b, self.butt_play_b, self.butt_stop_b, self.lbl_current_b, self.lbl_duration_b,
                                              self.lbl_info_b, self.lbl_cover_b)

    def __setup_config(self) -> None:
        """Sets up the configuration by reading the config.ini file and adding missing sections if necessary. Returns: None"""

        self.config.read(get_absolute_path_config())
        if CONFIG_SECTION_DIRECTORIES not in self.config:
            self.config.add_section(CONFIG_SECTION_DIRECTORIES)
            self.config.set(
                CONFIG_SECTION_DIRECTORIES,
                CONFIG_LAST_RIGHT_DIRECTORY,
                QDir.rootPath(),
            )
            self.config.set(
                CONFIG_SECTION_DIRECTORIES,
                CONFIG_LAST_LEFT_DIRECTORY,
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
        self.path_info_bar_left = self.findChild(MyLineEdit, "path_left")
        self.path_info_bar_left.setCompleter(completer)

        self.path_info_bar_right = self.findChild(MyLineEdit, "path_right")
        self.path_info_bar_right.setCompleter(completer)

        self.path_info_bar_left.returnPressed.connect(lambda: self.on_path_info_bar_return_pressed(self.tree_left, self.path_info_bar_left))
        self.path_info_bar_right.returnPressed.connect(lambda: self.on_path_info_bar_return_pressed(self.tree_right, self.path_info_bar_right))

        last_left_dir = self.config.get(CONFIG_SECTION_DIRECTORIES, CONFIG_LAST_LEFT_DIRECTORY, fallback=self.default_path)
        self.path_info_bar_left.setText(last_left_dir)
        last_right_dir = self.config.get(CONFIG_SECTION_DIRECTORIES, CONFIG_LAST_RIGHT_DIRECTORY, fallback=self.default_path)
        self.path_info_bar_right.setText(last_right_dir)

    def __setup_icons(self) -> None:
        """Set up the icons. Returns: None"""

        self.icon_left = QIcon("src/qt/icons/chevrons-left.svg")
        self.icon_right = QIcon("src/qt/icons/chevrons-right.svg")
        self.icon_menu = QIcon("src/qt/icons/menu.svg")
        self.icon_repackage = QIcon("src/qt/icons/package.svg")
        self.icon_move = QIcon("src/qt/icons/move.svg")
        self.icon_exit = QIcon("src/qt/icons/log-out.svg")

    def __setup_menu_buttons(self) -> None:
        """Set up the menu buttons. Returns: None"""
        self.menubar.setDisabled(False)
        self.menu_options = self.findChild(QMenu, "menu_options")
        self.menu_options.setDisabled(False)
        self.menuBar().raise_()

        self.menu_view_filem = self.findChild(QAction, "menu_view_filem")
        self.menu_view_filem.triggered.connect(lambda: self.stack_page_view.setCurrentIndex(0))
        self.menu_view_filem.setToolTip("File Manager")

        self.menu_view_dbm = self.findChild(QAction, "menu_view_dbm")
        self.menu_view_dbm.triggered.connect(lambda: self.stack_page_view.setCurrentIndex(1))
        self.menu_view_dbm.setToolTip("Database View")

        self.menu_view_dbm2 = self.findChild(QAction, "menu_view_dbm2")
        self.menu_view_dbm2.triggered.connect(lambda: self.stack_page_view.setCurrentIndex(2))
        self.menu_view_dbm2.setToolTip("Database with Media Player View")
        
        # toggle menu
        self.frame_left_menu.setMinimumWidth(0)
        self.but_toggle = self.findChild(QPushButton, "but_toggle")
        self.but_toggle.clicked.connect(lambda: self.toggle_menu())
        self.but_toggle.setToolTip("Open Menu")
        self.but_toggle.setToolTipDuration(5000)
        self.but_toggle.setIcon(self.icon_menu)
        self.but_toggle.setShortcut("Ctrl+M")
        self.but_exit.setIcon(QtGui.QIcon(self.icon_exit.pixmap(40, 40)))

    def __setup_action_buttons(self) -> None:
        """Set up the action buttons. Returns: None"""
        toolTipDuration = 10000
        self.but_restore = self.findChild(QPushButton, "but_restore")
        self.but_restore.clicked.connect(lambda: self.on_restore_button_clicked())
        self.but_restore.setToolTip("[Ctrl+T] Restore from the recycle bin")
        self.but_restore.setToolTipDuration(toolTipDuration)
        self.but_restore.setShortcut("Ctrl+T")

        to_right_text = "the selected items from the left -> right directory"
        to_left_text = "the selected items from the right -> left directory"

        self.but_move_to_right = self.findChild(QPushButton, "but_move_to_right")
        self.but_move_to_right.clicked.connect(lambda: self.on_move_button_clicked(self.tree_left, self.tree_right))
        self.but_move_to_right.setToolTip("[Ctrl+M] Move %s" % to_right_text)
        self.but_move_to_right.setToolTipDuration(toolTipDuration)
        self.but_move_to_right.setShortcut("Ctrl+M")

        self.but_move_to_left = self.findChild(QPushButton, "but_move_to_left")
        self.but_move_to_left.clicked.connect(lambda: self.on_move_button_clicked(self.tree_right, self.tree_left))
        self.but_move_to_left.setToolTip("[Ctrl+shift+M] Move %s" % to_left_text)
        self.but_move_to_left.setToolTipDuration(toolTipDuration)
        self.but_move_to_left.setShortcut("Ctrl+shift+M")

        self.but_copy_to_right = self.findChild(QPushButton, "but_copy_to_right")
        self.but_copy_to_right.clicked.connect(lambda: self.on_copy_button_clicked(self.tree_left, self.tree_right))
        self.but_copy_to_right.setToolTip("[Ctrl+P] Copy %s" % to_right_text)
        self.but_copy_to_right.setToolTipDuration(toolTipDuration)
        self.but_copy_to_right.setShortcut("Ctrl+P")

        self.but_copy_to_left = self.findChild(QPushButton, "but_copy_to_left")
        self.but_copy_to_left.clicked.connect(lambda: self.on_copy_button_clicked(self.tree_right, self.tree_left))
        self.but_copy_to_left.setToolTip("[Ctrl+shift+C] Copy %s" % to_left_text)
        self.but_copy_to_left.setToolTipDuration(toolTipDuration)
        self.but_copy_to_left.setShortcut("Ctrl+shift+C")

        self.but_settings = self.findChild(QPushButton, "but_settings")
        self.but_settings.clicked.connect(lambda: self.on_settings_button_clicked())
        self.but_settings.setToolTip("[Ctrl+S] Open the settings dialog")
        self.but_settings.setToolTipDuration(toolTipDuration)
        self.but_settings.setShortcut("Ctrl+S")

        self.but_db = self.findChild(QPushButton, "but_db")
        self.but_db.clicked.connect(lambda: self.on_db_button_clicked())
        self.but_db.setToolTip("[Ctrl+D] Open the database dialog")
        self.but_db.setToolTipDuration(toolTipDuration)
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
        id3_labels_left = [
            self.lbl_left_title,
            self.lbl_left_artist,
            self.lbl_left_album,
            self.lbl_left_label,
            self.lbl_left_side,
            self.lbl_left_track,
            self.lbl_left_catalog,
            self.lbl_left_discogs_id,

            self.lbl_left_album_artist,
            self.lbl_left_date,
            self.lbl_left_genre,
            self.lbl_left_media,
            self.lbl_left_style,
            self.lbl_left_country,
        ]

        id3_labels_right = [
            self.lbl_right_title,
            self.lbl_right_artist,
            self.lbl_right_album,
            self.lbl_right_label,
            self.lbl_right_side,
            self.lbl_right_track,
            self.lbl_right_catalog,
            self.lbl_right_discogs_id,

            self.lbl_right_album_artist,
            self.lbl_right_date,
            self.lbl_right_genre,
            self.lbl_right_media,
            self.lbl_right_style,
            self.lbl_right_country,
        ]
        left_artwork_labels = {
            "art": self.label_left_art_type,
            "res": self.label_left_resolution,
            "size": self.label_left_size,
            "mime": self.label_left_mime,
            "desc": self.label_left_desc,
            "page": self.label_left_page_num,
            "next": self.left_image_next,
            "prev": self.left_image_prev,
        }
        right_artwork_labels = {
            "art": self.label_right_art_type,
            "res": self.label_right_resolution,
            "size": self.label_right_size,
            "mime": self.label_right_mime,
            "desc": self.label_right_desc,
            "page": self.label_right_page_num,
            "next": self.right_image_next,
            "prev": self.right_image_prev,
        }

        self.label_cache = {"id3": (id3_labels_left, id3_labels_right), "artwork": (left_artwork_labels, right_artwork_labels)}

    def __setup_label_style_sheet(self) -> None:
        """Set style sheet for the labels. Returns: None"""
        # Create a QFont object for the bold and italic font
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)

        left_labels, right_labels = self.label_cache.get("id3")
        # Loop over the left labels
        for label in left_labels:
            label.setFont(font)
            label.setStyleSheet("color: rgb(33, 143, 122 );")

        # Loop over the right labels
        for label in right_labels:
            label.setFont(font)
            label.setStyleSheet("color: rgb(177, 162, 86);")

    def __setup_tree_widgets(self) -> None:
        """Populates the id3_tags list with the names of the supported ID3 tags. Returns: None"""

        last_dir = self.config.get(CONFIG_SECTION_DIRECTORIES, CONFIG_LAST_LEFT_DIRECTORY, fallback=self.default_path)
        self.tree_left = self.findChild(MyTreeView, "tree_left")
        self.tree_left.set_media_player(self.player_a)
        self.__set_tree_actions(self.tree_left, last_dir, self.path_info_bar_left)

        last_dir = self.config.get(CONFIG_SECTION_DIRECTORIES, CONFIG_LAST_RIGHT_DIRECTORY, fallback=self.default_path)
        self.tree_right = self.findChild(MyTreeView, "tree_right")
        self.tree_right.set_media_player(self.player_b)
        self.__set_tree_actions(self.tree_right, last_dir, self.path_info_bar_right)

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
        but_copy_left = self.findChild(QPushButton, "but_copy_left")
        but_copy_left.clicked.connect(lambda: self.copy_dir_tree_view(self.tree_right, self.path_info_bar_right, self.tree_left.get_root_dir()))
        but_copy_right = self.findChild(QPushButton, "but_copy_right")
        but_copy_right.clicked.connect(lambda: self.copy_dir_tree_view(self.tree_left, self.path_info_bar_left, self.tree_right.get_root_dir()))

    def __setup_dir_up_buttons(self) -> None:
        """Sets up the functionality of the path up buttons. Returns: None"""
        self.findChild(QPushButton, "but_left_up").clicked.connect(lambda: self.go_up_dir_level(self.tree_left, self.path_info_bar_left))
        self.findChild(QPushButton, "but_right_up").clicked.connect(lambda: self.go_up_dir_level(self.tree_right, self.path_info_bar_right))

    def on_context_menu_requested(self, tree_view: MyTreeView, position: QPoint):

        index = tree_view.indexAt(position)

        if tree_view == self.tree_left:
            other_tree = self.tree_right
        else:
            other_tree = self.tree_left

        self.tree_view_cm_handler.show_menu(tree_view, index, position, other_tree)

    @staticmethod
    def on_move_button_clicked(from_tree: MyTreeView, to_tree: MyTreeView) -> None:
        """Move files from the left directory to the right directory. Returns: None"""
        logger.info(f"Moving files from '{from_tree.get_root_dir()}' to '{to_tree.get_root_dir()}'")
        selected_files = from_tree.get_selected_files(True)
        ask_and_move_files(selected_files, from_tree.get_root_dir(), to_tree.get_root_dir())

    @staticmethod
    def on_copy_button_clicked(from_tree: MyTreeView, to_tree: MyTreeView) -> None:
        """Copy files from the left directory to the right directory. Returns: None"""
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
        left_path = self.tree_left.get_root_dir()  # get the path from the left treeview
        DatabaseWindow(left_path).show()

    @staticmethod
    def go_up_dir_level(tree_view: MyTreeView, path_bar: MyLineEdit) -> None:

        tree_view.go_up_one_dir_level()
        path_bar.setText(tree_view.get_root_dir())

    def copy_dir_tree_view(self, tree_view: MyTreeView, path_info_bar: MyLineEdit, directory: str) -> None:
        """Copies the left directory to the right directory. Returns: None"""
        tree_view.change_dir(directory)
        path_info_bar.setText(self.tree_right.get_root_dir())

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
        self.config.set(CONFIG_SECTION_DIRECTORIES, CONFIG_LAST_LEFT_DIRECTORY, self.path_info_bar_left.text())
        self.config.set(CONFIG_SECTION_DIRECTORIES, CONFIG_LAST_RIGHT_DIRECTORY, self.path_info_bar_right.text())

        # Save the config file
        with open(get_absolute_path_config(), "w") as config_file:
            self.config.write(config_file)

    def __setup_open_dir_browsers(self) -> None:
        """Set up the open dir browsers. Returns: None"""
        but_select_left = self.findChild(QPushButton, "but_select_left")
        but_select_left.clicked.connect(lambda: self.open_directory_browser(self.tree_left, self.path_info_bar_left))

        but_select_right = self.findChild(QPushButton, "but_select_right")
        but_select_right.clicked.connect(lambda: self.open_directory_browser(self.tree_right, self.path_info_bar_right))

    def open_directory_browser(self, tree_view: MyTreeView, path: MyLineEdit) -> None:
        """Open directory browser. Returns: None"""

        if directory := QFileDialog.getExistingDirectory(self, "Select Directory", tree_view.get_root_dir(), QFileDialog.ShowDirsOnly):
            tree_view.change_dir(directory)
            path.setText(directory)

    def on_repackage_button_clicked(self, tree_left: MyTreeView, tree_right: MyTreeView) -> None:
        """Set up the repackage button. Returns: None"""
        self.repackage(tree_left, tree_right)

    def _display_and_log_error(self, err: Exception) -> None:
        """Displays the error message and logs the error to the log file. Returns: None"""
        logger.error(traceback.format_exc())
        QMessageBox.critical(self, "Error", str(err))

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
        left, right = self.label_cache.get("id3")
        self.clear_labels(left)
        self.clear_labels(right)
        left, right = self.label_cache.get("artwork")
        self.clear_labels(left.values())
        self.clear_labels(right.values())

    @staticmethod
    def clear_labels(labels) -> None:
        """Clears label tags . Returns: None"""
        for label in labels:
            label.setText("")

    def display_id3_tags_when_an_item_is_selected(self, item: QModelIndex, tree_view: QTreeView) -> None:
        """Displays the ID3 tags for the selected audio file in the left tree. Returns: None"""

        model = cast(QFileSystemModel, tree_view.model())
        absolute_filename = model.filePath(item)

        if not self.audio_tags.isSupportedAudioFile(absolute_filename):
            return

        self._display_id3_tags(absolute_filename, tree_view)
        self._display_cover_artwork(absolute_filename, tree_view)

    def _display_cover_artwork(self, absolute_file_path: str, tree_view: QTreeView) -> None:
        """Displays the cover artwork for the selected audio file in the left tree. Returns: None"""
        # Get artwork from the audio tags
        cover_art_images = self.audio_tags.get_cover_art(absolute_file_path)

        stacked_widget = self.stacked_widget_right if tree_view == self.tree_right else self.stacked_widget_left

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
        """Displays the ID3 tags for the selected audio file in the left tree. Returns: None"""

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
        if tag == AudioTagHelper.MEDIA:
            if AudioTagHelper.MEDIA in audio_tags:
                return audio_tags[AudioTagHelper.MEDIA][0]
            if AudioTagHelper.MEDIATYPE in audio_tags:
                return audio_tags[AudioTagHelper.MEDIATYPE][0]
        if tag == AudioTagHelper.LABEL:
            if AudioTagHelper.LABEL in audio_tags:
                return audio_tags[AudioTagHelper.LABEL][0]
            if AudioTagHelper.ORGANIZATION in audio_tags:
                return audio_tags[AudioTagHelper.ORGANIZATION][0]
            
        return ""

    def get_labels(self, tree_view: QTreeView, label_type: str) -> Union[list, dict]:
        """Returns a list or dictionary of left or right labels based on label_type."""
        left, right = self.label_cache.get(label_type, (None, None))
        return left if tree_view == self.tree_left else right

    def repackage(self, tree_left: MyTreeView, tree_right: MyTreeView) -> None:
        """moves the files from the left directory to the right directory based on the LABEL tag. Returns: None"""

        left_dir = tree_left.get_root_dir()
        right_dir = tree_right.get_root_dir()

        self.update_status("Repackaging started...")
        logger.info("Repackaging started...")
        repackage_dir_by_label(left_dir, right_dir)
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


if __name__ == "__main__":

    import sys

    exit_code = 0
    try:
        main_window = MainWindow(app)  # All QWidget creation after QApplication
        main_window.show()
        app.exec_()

    except Exception as e:
        logger.exception("Unhandled exception: %s", e)
        logger.error(traceback.format_exc())
        exit_code = 1

    finally:
        logger.info("Application exited")
        app.quit()
    sys.exit(exit_code)
