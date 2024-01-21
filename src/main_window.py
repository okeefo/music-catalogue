import traceback
from PyQt5 import uic, QtWidgets, QtGui
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QAction,
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
    QFileDialog,
    QPushButton,
    QMessageBox,
    QTextBrowser
)
from PyQt5.QtCore import QSize, QPropertyAnimation, QEasingCurve, Qt, QResource
from scanner.scanner_dir import get_dir_structure
from scanner.repackage_dir import preview_repackage, repackage
import configparser
from scanner.file_system_tree import is_supported_audio_file
import logging
from PyQt5 import QtGui
import qt.resources_rcc
# TODO: commit button


class PaddedTreeWidgetItem(QTreeWidgetItem):
    """
    A custom QTreeWidgetItem class that adds padding to the displayed content.
    This help visually separate the columns in the tree view.

    Overrides the data() method to append spaces to the end of the content when the role is Qt.DisplayRole.

    Args:
        column (int): The column index of the item.
        role (int): The role of the item data.

    Returns:
        Any: The data for the specified column and role."""

    def data(self, column, role):
        data = super().data(column, role)
        if role == Qt.DisplayRole:
            data += " " * 2  # Add spaces to the end of the content
        return data


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

# Set logging instance
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window class for the application."""

    def __init__(self, application):
        """Initialize the main window."""
        super().__init__()
        self.application = application

        # Set up instance variables
        self.tree_source = None
        self.tree_target = None
        self.tree_structure_source = None
        self.tree_structure_target = None
        self.tree_structure_target_original = None
        self.config = configparser.ConfigParser()
        self.id3_tags = []
        self.id3_labels_source = []
        self.id3_labels_target = []
        

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
        if CONFIG_SECTION_WINDOW not in self.config:
            self.config.add_section(CONFIG_SECTION_WINDOW)

    def __setup_ui(self) -> None:
        """
        Sets up the user interface of the main window.
        Returns: None
        """
        self.update_status(
            "Welcome - select a directory to scan either from thr menu or the scan button"
        )
        # set window size from config
        self.__setup_icons()
        self.__setup_window_size()
        self.__setup_exit()
        self.__setup_scan_source()
        self.__setup_scan_target()
        self.__setup_copy_source_button()
        self.__setup_tree_widgets()
        self.__setup_refresh_button()
        self.__setup_preview_button()
        self.__setup_id3_label_caches()
        self.__setup_id3_tags()
        self.__clear_label_text(self.id3_labels_source)
        self.__clear_label_text(self.id3_labels_target)
        self.__setup_commit_button()
        self.__setup_menu_buttons()
        self.__setup_checkboxes()
       
        
    
    def __setup_icons(self) -> None:
       
        self.icon_left = QtGui.QIcon(":/icons/icons/chevrons-left.svg") 
        self.icon_right =  QtGui.QIcon(":/icons/icons/chevrons-right.svg")
        self.icon_repackage = QtGui.QIcon(":/icons/icons/package.svg")
        self.icon_move = QtGui.QIcon(":/icons/icons/move.svg")
        self.icon_exit = QtGui.QIcon(":/icons/icons/log-out.svg")
        
    def __setup_checkboxes(self) -> None:
        self.checkbox_overwrite = self.findChild(QtWidgets.QCheckBox, "checkBox_overwrite")
        self.checkbox_overwrite.setToolTip("Overwrite existing files in the target directory with the same name as the source files")
        self.checkbox_copy = self.findChild(QtWidgets.QCheckBox, "checkBox_copy")
        self.checkbox_copy.setToolTip("Copy files from the source directory to the target directory instead of moving them")
        
        
    def __setup_menu_buttons(self) -> None:
        """Set up the menu buttons. Returns: None"""
        # toggle menu
        self.frame_left_menu.setMinimumWidth(0)
        self.but_toggle = self.findChild(QPushButton, "but_toggle")
        self.but_toggle.clicked.connect(lambda: self.toggleMenu())
        self.but_toggle.setToolTip("Open Menu")
        self.but_toggle.setToolTipDuration(1000)
        self.but_toggle.setIcon(QtGui.QIcon(":/icons/icons/chevrons-right.svg"))
        self.but_toggle.setShortcut("Ctrl+M")
        
        # Repackage buttons
        self.but_repackage = self.findChild(QPushButton, "but_repackage")
        self.but_repackage.setIcon(QtGui.QIcon(self.icon_repackage.pixmap(40, 40)))
#        self.but_repackage.clicked.connect(self.repackage_files)
        self.but_repackage.setToolTip("Repackage files by Label")
        
        # Move buttons
        self.but_move = self.findChild(QPushButton, "but_move_2")
        self.but_move.setIcon(QtGui.QIcon(self.icon_move.pixmap(40, 40)))
 #       self.but_move.clicked.connect(self.move_files)
        self.but_move.setToolTip("Move files from the source directory to the target directory")
        
        
        
        self.but_exit.setIcon(QtGui.QIcon(self.icon_exit.pixmap(40, 40)))
        
    def __setup_commit_button(self) -> None:
        pass
    
    def __setup_window_size(self) -> None:
        """
        Sets up the size of the main window based on the configuration settings.
        Returns: None
        """
        self.resize(
            self.config.getint(
                CONFIG_SECTION_WINDOW, CONFIG_WINDOW_WIDTH, fallback=800
            ),
            self.config.getint(
                CONFIG_SECTION_WINDOW, CONFIG_WINDOW_HIGHT, fallback=600
            ),
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

        self.tree_source = self.findChild(QTreeWidget, "tree_source")
        self.tree_target = self.findChild(QTreeWidget, "tree_target")
        self.tree_source.setHeaderLabels(["Name", "Type", "Date", "Size"])
        self.tree_target.setHeaderLabels(["Name", "Type", "Date", "Size"])
        self.tree_source.setIconSize(QSize(32, 32))
        self.tree_target.setIconSize(QSize(32, 32))
        self.tree_source.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_source.setSortingEnabled(True)
        # when user clicks on a node in the source tree, display the id3 tags for the selected audio file
        self.tree_source.itemClicked.connect(
            self.display_id3_tags_when_an_item_is_selected
        )
        self.tree_target.itemClicked.connect(
            self.display_id3_tags_when_an_item_is_selected
        )
        # When user clicks expand - resize the columns
        self.tree_source.itemExpanded.connect(self.resizeColumns)
        self.tree_target.itemExpanded.connect(self.resizeColumns)

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

    def __setup_preview_button(self) -> None:
        """
        Sets up the functionality of the preview button.
        Returns: None
        """

        but_preview = self.findChild(QPushButton, "but_preview_to_target_2")
        but_preview.clicked.connect(self.preview)

    def __setup_commit_button(self) -> None:
        """
        Sets up the functionality of the commit button.
        Returns: None
        """

        but_commit = self.findChild(QPushButton, "but_commit_2")
        but_commit.clicked.connect(self.repackage)

    def reset_target(self) -> None:
        """
        Resets the target directory tree structure to before any changes were made.
        Returns: None
        """

        tree_structure_target = self.tree_structure_target_original
        self._populate_target_tree(tree_structure_target)

    def preview(self) -> None:
        """
        Previews the repackaging of the source directory into the target directory.
        Returns: None
        """

        self.disable_main_window()
        # check if target tree is empty, if it is, copy source to target silently
        if self.tree_structure_target is None:
            self.copy_source_to_target(True)

        new_tree = preview_repackage(
            self.tree_structure_source,
            self.tree_structure_target,
            self.update_statusbar,
        )
        self._populate_target_tree(new_tree)

        # Expand the first top-level item
        self.tree_target.expandItem(self.tree_target.topLevelItem(0))
        self.enable_main_window()

    def _populate_target_tree(self, new_tree) -> None:
        """
        Populates the target directory tree with the provided new_tree.
        Returns: None
        """

        self.tree_target.clear()
        self.findChild(QTextBrowser, "path_target").setText(new_tree.get_absolute_path())
        self.add_tree_items(self.tree_target.invisibleRootItem(), new_tree)
        self.tree_target.expandItem(self.tree_target.topLevelItem(0))
        self.tree_structure_target = new_tree
        # Expand the first top-level item
        self.tree_target.expandItem(self.tree_target.topLevelItem(0))

    def copy_source_to_target(self, silent=False) -> None:
        """
        Copies the source directory to the target directory.
        Returns: None
        """

        if self.tree_structure_source is None:
            QMessageBox.critical(self, "Error", "Source directory not scanned")
            return

        if not silent:
            reply = self.prompt_yes_no(
                "Confirmation",
                "Are you sure you want to copy the source to the target?",
            )
            if reply == QMessageBox.No:
                return
        self._populate_target_tree(self.tree_structure_source.copy())
        self.tree_structure_target_original = self.tree_structure_target

    def confirm_exit(self) -> None:
        """
        Confirms the exit action with the user.
        Returns: None
        """

        if (
            self.prompt_yes_no("Exit", "Are you sure you want to exit?")
            == QMessageBox.No
        ):
            return

        self.__update_config_file()

        self.application.quit()

    def __update_config_file(self) -> None:
        """
        Updates the configuration file with the current window size.
        Returns: None
        """

        # Write the window size to the config file
        self.config.set(
            CONFIG_SECTION_WINDOW, CONFIG_WINDOW_HIGHT, f"{self.size().height()}"
        )
        self.config.set(
            CONFIG_SECTION_WINDOW, CONFIG_WINDOW_WIDTH, f"{self.size().width()}"
        )

        # Save the config file
        with open("config.ini", "w") as config_file:
            self.config.write(config_file)

    def __setup_scan_source(self) -> None:
        """Set up the source scan button and menu item. Returns: None"""
        action_scan = self.findChild(QAction, "mf_scan")
        action_scan.triggered.connect(self.scan_source_directory)

        but_select_source = self.findChild(QPushButton, "but_select_source")
        but_select_source.clicked.connect(self.scan_source_directory)

    def __setup_scan_target(self) -> None:
        """Set up the target scan button. Returns: None"""
        but_select_target = self.findChild(QPushButton, "but_select_target")
        but_select_target.clicked.connect(self.scan_target_directory)

    def scan_source_directory(self) -> None:
        """Scan the source directory. Returns: None"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            self.config.get(
                CONFIG_SECTION_DIRECTORIES, CONFIG_LAST_SOURCE_DIRECTORY, fallback=""
            ),
        )
        if not directory:
            return

        self.config.set(
            CONFIG_SECTION_DIRECTORIES, CONFIG_LAST_SOURCE_DIRECTORY, directory
        )

        try:
            self.do_file_system_scan_and_display(directory, self.tree_source, "source")
        except Exception as e:
            self._display_and_log_error(e)

    def scan_target_directory(self, directory=None) -> None:
        """Ask User to select target DIR and scan it. Returns: None"""
        if not directory:
            directory = QFileDialog.getExistingDirectory(
                self,
                "Select Directory",
                self.config.get(
                    CONFIG_SECTION_DIRECTORIES,
                    CONFIG_LAST_TARGET_DIRECTORY,
                    fallback="",
                ),
            )

        if not directory:
            return

        self.config.set(
            CONFIG_SECTION_DIRECTORIES, CONFIG_LAST_TARGET_DIRECTORY, directory
        )

        try:
            self.do_file_system_scan_and_display(directory, self.tree_target, "target")
            self.tree_structure_target_original = self.tree_structure_target.copy()
        except Exception as e:
            self._display_and_log_error(e)

    # TODO Rename this here and in `scan_source_directory` and `scan_target_directory`
    def _display_and_log_error(self, e) -> None:
        logging.error(traceback.format_exc())
        QMessageBox.critical(self, "Error", str(e))

    def do_file_system_scan_and_display(
        self, directory, tree_widget, file_type
    ) -> None:
        """
        Scan a directory and update the UI.
        Returns: None
        """
        self.update_status(f"Scanning {file_type} directory: {directory}")
        self.update_statusbar(f"Scanning {file_type} directory: {directory}")

        tree_structure = get_dir_structure(directory, self.update_statusbar)
        if file_type == "source":
            self.tree_structure_source = tree_structure
            self.findChild(QTextBrowser, "path_source").setText(directory)
        else:
            self.tree_structure_target = tree_structure
            self.findChild(QTextBrowser, "path_target").setText(directory)

        tree_widget.clear()
        
      

        self.add_tree_items(tree_widget.invisibleRootItem(), tree_structure)

        self.update_status(f"{file_type.capitalize()} directory scanned: {directory}")
        self.update_statusbar(
            f"{file_type.capitalize()} directory scanned: {directory}"
        )

        # Expand the first top-level item
        tree_widget.expandItem(tree_widget.topLevelItem(0))

    def add_tree_items(self, parent_item, tree_structure) -> None:
        """Add items to the tree widget (display)."""

        # add name, file type, date time and file size to the tree widget
        item = PaddedTreeWidgetItem(
            parent_item,
            [
                tree_structure.get_name(),
                tree_structure.get_extension(),
                tree_structure.get_modified_date(),
                tree_structure.get_file_size_mb(),
            ],
        )
        item.setIcon(ICON_INDEX, tree_structure.get_icon())

        for child in tree_structure.get_children():
            self.add_tree_items(item, child)

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

    def enable_main_window(self) -> None:
        """Re-enable the main window after a long operation.Returns: None"""
        self.__setEnabled(True)

    def disable_main_window(self) -> None:
        """Disable the main window during long operations. Returns: None"""
        self.__setEnabled(False)

    def __setEnabled(self, enabled) -> None:
        """Enables or Disables main Window, Return: None"""
        super().setEnabled(enabled)
        if enabled:
            self.update_statusbar("Ready")
        else:
            self.update_statusbar("Busy")

        # Disable or enable all child widgets recursively
        for child_widget in self.findChildren(QtWidgets.QWidget):
            child_widget.setEnabled(enabled)

    def __clear_label_text(self, labels) -> None:
        """Clears label tags . Returns: None"""
        for label in labels:
            label.setText("")

    def display_id3_tags_when_an_item_is_selected(self, item) -> None:
        """
        Displays source or Target audio tag labels when a user selects an audio
        file in a tree widget.
        Returns: None
        """
        if item is None:
            return

        source = self.sender() == self.tree_source

        labels = self.get_label_list(source)

        if not is_supported_audio_file(item.text(1).rstrip()):
            self.__clear_label_text(labels)
            return

        tree_structure = (
            self.tree_structure_source if source else self.tree_structure_target
        )

        item = tree_structure.get_child_node_by_name(item.text(0).rstrip())

        for label, tag in zip(labels, self.id3_tags):
            if tag == "URL":
                url = item.get_id3_tag(tag)
                label.setText(f'<a href="{url}">{url}</a>')
            else:
                label.setText(item.get_id3_tag(tag))

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

        if (
            self.tree_structure_source is None
            or self.tree_structure_source.get_absolute_path() is None
        ):
            QMessageBox.critical(self, "Error", "Source directory not scanned")
            return

        if (
            self.tree_structure_target is None
            or self.tree_structure_target.get_absolute_path() is None
        ):
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
        print(f"width:{width}")
        maxExtend = 180
        standard = 0

        # SET MAX WIDTH
        widthExtended = maxExtend if width <= 100 else standard
        print(f"widthExtended:{widthExtended}")
        # ANIMATION
        self.animation = QPropertyAnimation(self.frame_left_menu, b"minimumWidth")
        self.animation.setDuration(400)
        self.animation.setStartValue(width)
        self.animation.setEndValue(widthExtended)
        self.animation.setEasingCurve(QEasingCurve.InOutQuart)
        self.animation.start()

        # Set the ico from resources.  
        # when the menu is open, the icon is chevrons-left.svg, when closed the chevrons-right.svg
        icon = QtGui.QIcon(":/icons/icons/chevrons-left.svg") if width <= 100 else QtGui.QIcon(":/icons/icons/chevrons-right.svg")
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
