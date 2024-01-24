import traceback
from PyQt5 import uic, QtWidgets, QtGui
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QAction,
    QStyle,
    QTreeWidget,
    QTreeView,
    QTreeWidgetItem,
    QFileDialog,
    QPushButton,
    QMessageBox,
    QTextBrowser,
    QCompleter,
    QFileSystemModel,
    QLineEdit,
)
from PyQt5.QtCore import QSize, QPropertyAnimation, QEasingCurve, Qt, QDir, QModelIndex
from scanner.repackage_dir import repackage
import configparser
import logging
from PyQt5 import QtGui
import qt.resources_rcc
import os
from enum import Enum
from scanner.audio_tags import AudioTags
import scanner.audio_tags

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


# create a enum that can be used to denote changes are being made either in the source or target views
# create two methods isSource and isTarget if the changeType is SOURCE or TARGET respectively


class ChangeType(Enum):
    SOURCE = 0
    TARGET = 1

    def isSource(self):
        return self == ChangeType.SOURCE

    def isTarget(self):
        return self == ChangeType.TARGET


# Set logging instance
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window class for the application."""

    def __init__(self, application):
        """Initialize the main window."""
        super().__init__()
        self.application = application

        # Set up instance variables
        self.config = configparser.ConfigParser()
        self.id3_tags = []
        self.id3_labels_source = []
        self.id3_labels_target = []
        self.directory_source = "c:\\"
        self.directory_target = "c:\\"
        self.audio_tags = AudioTags()

        # set up config
        self.__setup_config()

        # Set up the user interface from Designer.
        # Load the .ui file and set up the UI
        uic.loadUi(
            "src\\qt\\music_manager.ui",
            self,
        )

        # QResource.registerResource("c:\\dev\\projects\\python\\music-catalog\\src\\qt\\resources.qrc")

        # Call the setup_ui method to set up the UI
        self.__setup_ui()

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

    def __setup_ui(self) -> None:
        """
        Sets up the user interface of the main window.
        Returns: None
        """
        self.update_status("Welcome - select a directory to scan either from the menu or the scan button")
        # set window size from config
        self.__setup_icons()
        self.__setup_window_size()
        self.__setup_exit()
        self.__setup_scan_source()
        self.__setup_scan_target()
        self.__setup_copy_source_button()
        self.__setup_tree_widgets()
        self.__setup_refresh_button()
        self.__setup_id3_label_caches()
        self.__setup_id3_tags()
        self.__clear_label_text(self.id3_labels_source)
        self.__clear_label_text(self.id3_labels_target)
        self.__setup_commit_button()
        self.__setup_menu_buttons()
        self.__setup_path_labels()
        self.__setup_dir_up_buttons()

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

    def __setup_commit_button(self) -> None:
        pass

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

    def __setup_id3_label_caches(self) -> None:
        """
        Populates the source_id3_labels and target_id3_labels lists with the corresponding label widgets.
        Returns: None
        """

        self.id3_labels_source = [
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

        self.id3_labels_target = [
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
        model.setRootPath(last_dir)

        tree_view.setModel(model)
        tree_view.sortByColumn(0, Qt.AscendingOrder)
        tree_view.setRootIndex(model.index(last_dir))
        tree_view.clicked.connect(lambda: self.on_tree_clicked(tree_view.selectedIndexes()[0], tree_view))
        tree_view.doubleClicked.connect(lambda: self.on_tree_double_clicked(tree_view.selectedIndexes()[0], tree_view))
        tree_view.expanded.connect(lambda: self.resize_first_column(tree_view))
        tree_view.setSortingEnabled(True)

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
        """
        Sets up the functionality of the copy source button.
        Returns: None
        """

        but_copy_source = self.findChild(QPushButton, "but_copy_source")
        but_copy_source.clicked.connect(self.copy_source_to_target)

    def __setup_refresh_button(self) -> None:
        """
        Sets up the functionality of the refresh button.
        Returns: None
        """

        but_refresh = self.findChild(QPushButton, "but_refresh_target_2")
        but_refresh.clicked.connect(self.reset_target)

    def __setup_commit_button(self) -> None:
        """
        Sets up the functionality of the commit button.
        Returns: None
        """

        but_commit = self.findChild(QPushButton, "but_commit_2")
        but_commit.clicked.connect(self.repackage)

    def __setup_dir_up_buttons(self) -> None:
        """
        Sets up the functionality of the path up buttons.
        Returns: None
        """

        self.findChild(QPushButton, "but_source_up").clicked.connect(lambda: self.go_up_dir_level(self.tree_source, self.path_source))
        self.findChild(QPushButton, "but_target_up").clicked.connect(lambda: self.go_up_dir_level(self.tree_target, self.path_target))

    def resize_first_column(self, tree_view: QTreeView) -> None:
        tree_view.resizeColumnToContents(0)

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
        if model.isDir(index):
            path = model.filePath(index)
            # if model.rowCount(index) > 0:
            self.set_root_index(path, tree_view)

            # else:
            model.directoryLoaded.connect(lambda: self.set_root_index(path, tree_view))
            #  tree_view.expand(index)

            if tree_view == self.tree_source:
                self.path_source.setText(path)
                self.directory_updated(path, ChangeType.SOURCE)
            else:
                self.path_target.setText(path)
                self.directory_updated(path, ChangeType.TARGET)

    def set_root_index(self, directory, tree_view: QTreeView = None) -> None:
        model = tree_view.model()
        tree_view.setRootIndex(model.index(directory))
        for column in range(model.columnCount()):
            tree_view.resizeColumnToContents(column)

        try:
            model.directoryLoaded.disconnect()
        except TypeError:
            pass

    def go_up_dir_level(self, tree_view: QTreeView, path: QLineEdit) -> None:
        model = tree_view.model()
        current_root_path = model.filePath(tree_view.rootIndex())
        dir = QDir(current_root_path)
        if dir.cdUp():
            parent_path = dir.absolutePath()

            model = QFileSystemModel()

            model.setRootPath(parent_path)

            tree_view.setModel(model)
            tree_view.sortByColumn(0, Qt.AscendingOrder)
            self.set_root_index(parent_path, tree_view)
            model.directoryLoaded.connect(lambda: self.resize_first_column(tree_view))

            path.setText(parent_path)
            changeType = ChangeType.SOURCE if tree_view == self.tree_source else ChangeType.TARGET
            self.directory_updated(parent_path, changeType)

    def reset_target(self) -> None:
        """
        Resets the target directory tree structure to before any changes were made.
        Returns: None
        """

        tree_structure_target = self.tree_structure_target_original
        self._populate_target_tree(tree_structure_target)

    def copy_source_to_target(self) -> None:
        """
        Copies the source directory to the target directory.
        Returns: None
        """
        self.open_directory(self.tree_target,  self.path_target, self.path_source.text())

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
            path.setText(directory)
            changeType = ChangeType.SOURCE if tree_view == self.tree_source else ChangeType.TARGET
            self.directory_updated(directory, changeType)

        except Exception as e:
            self._display_and_log_error(e)

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

    def __clear_label_text(self, labels) -> None:
        """Clears label tags . Returns: None"""
        for label in labels:
            label.setText("")

    def display_id3_tags_when_an_item_is_selected(self, item: QModelIndex, tree_view: QTreeView) -> None:
        """
        Displays source or Target audio tag labels when a user selects an audio
        file in a tree widget.
        Returns: None
        """
        if item is None:
            return

        source = tree_view == self.tree_source

        labels = self.get_label_list(source)

        # Get the absolute file path from the QModelIndex
        model = tree_view.model()
        file_path = model.filePath(item)

        # Get the ID3 tags for the selected file from AudioTags
        audio_tags = self.audio_tags.get_tags(file_path)

        for label, tag in zip(labels, self.id3_tags):
               
            value = audio_tags[tag][0] if tag in audio_tags else "" 
    
            if tag == "URL":
                label.setText(f'<a href="{value}">{value}</a>')
            else:
                label.setText(value)

    def get_label_list(self, source=True) -> list:
        """Returns: list of source or target ID3 labels"""
        return self.id3_labels_source if source else self.id3_labels_target

    def resizeColumns(self) -> None:
        """Resize the columns of the tree widget. Returns: None"""
        if self.sender() == self.tree_source:
            tree_widget = self.tree_source
        else:
            tree_widget = self.tree_target

        for i in range(tree_widget.columnCount()):
            tree_widget.resizeColumnToContents(i)

    def repackage(self) -> None:
        """
        Commit the changes to the target directory.
        Returns: None
        """

        if self.tree_structure_source is None or self.tree_structure_source.get_absolute_path() is None:
            QMessageBox.critical(self, "Error", "Source directory not scanned")
            return

        if self.tree_structure_target is None or self.tree_structure_target.get_absolute_path() is None:
            QMessageBox.critical(self, "Error", "Target directory not scanned")
            return

        self.disable_main_window()

        repackage(
            self.tree_structure_source,
            self.tree_structure_target.get_absolute_path(),
            self.update_statusbar,
            self.update_status,
            True,
        )
        self.scan_target_directory(self.tree_structure_target.get_absolute_path())
        self.update_statusbar("Repackaging... Done")
        self.enable_main_window()

    def toggleMenu(self) -> None:
        # get width
        width = self.frame_left_menu.width()
        #print(f"width:{width}")
        maxExtend = 100
        standard = 0

        # SET MAX WIDTH
        widthExtended = maxExtend if width == 0 else standard
        #print(f"widthExtended:{widthExtended}")
        
        # ANIMATION
        self.animation = QPropertyAnimation(self.frame_left_menu, b"minimumWidth")
        self.animation.setDuration(400)
        self.animation.setStartValue(width)
        self.animation.setEndValue(widthExtended)
        self.animation.setEasingCurve(QEasingCurve.InOutQuart)
        self.animation.start()

        # Set the ico from resources.
        # when the menu is open, the icon is chevrons-left.svg, when closed the chevrons-right.svg
        icon = self.icon_left if width == 0 else self.icon_menu
        self.but_toggle.setIcon(icon)
        if width <= 0:
            self.but_toggle.setToolTip("Close Menu")
            self.but_toggle.setToolTipDuration(1000)
        else:
            self.but_toggle.setToolTip("Open Menu")


if __name__ == "__main__":
    # Create an instance of MainWindow
    main_window = MainWindow(app)

    # Display the main window
    main_window.show()

    # Start the application event loop
    app.exec_()
