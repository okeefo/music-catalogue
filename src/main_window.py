from PyQt5 import uic, QtWidgets
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
)
from scanner.scanner_dir import get_dir_structure
from PyQt5.QtCore import QSize
from scanner.repackage_dir import preview_repackage
import configparser
from PyQt5.QtCore import Qt
from scanner.file_system_tree import is_supported_audio_file

# Create an instance of QApplication
app = QApplication([])

ICON_INDEX = 0


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
        self.source_id3_labels = []
        self.target_id3_labels = []

        # set up config
        self.setup_config()

        # Set up the user interface from Designer.
        # Load the .ui file and set up the UI
        uic.loadUi(
            "C:\\dev\\projects\\python\\music-catalogue\\src\\qt\\music_manager.ui",
            self,
        )

        # Call the setup_ui method to set up the UI
        self.setup_ui()

    def setup_config(self):
        self.config.read("config.ini")
        if "Directories" not in self.config:
            self.config.add_section("Directories")

    def setup_ui(self):
        """Perform additional setup for the UI."""
        self.update_status(
            "Welcome - select a directory to scan either from thr menu or the scan button"
        )
        self.setup_exit()
        self.setup_scan_source()
        self.setup_scan_target()
        self.setup_copy_source_button()
        self.setup_tree_widgets()
        self.setup_refresh_button()
        self.setup_preview_button()
        self.setup_id3_label_caches()
        self.setup_id3_tags()
        self.clear_audio_tags(True)
        self.clear_audio_tags(False)

    def setup_id3_label_caches(self):
        self.source_id3_labels = [
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

        self.target_id3_labels = [
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

    def setup_id3_tags(self):
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

    def setup_tree_widgets(self):
        """Set up the tree widgets."""
        self.tree_source = self.findChild(QTreeWidget, "tree_source")
        self.tree_target = self.findChild(QTreeWidget, "tree_target")
        self.tree_source.setHeaderLabels(["No directory selected", ""])
        self.tree_target.setHeaderLabels(["No directory selected", ""])
        self.tree_source.setIconSize(QSize(32, 32))
        self.tree_target.setIconSize(QSize(32, 32))
        self.tree_source.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_source.setSortingEnabled(True)
        # when user clicks on a node in the source tree, display the id3 tags for the selected audio file
        self.tree_source.itemClicked.connect(self.display_audio_tags)
        self.tree_target.itemClicked.connect(self.display_audio_tags)

    def setup_exit(self):
        """Set up the exit button and menu item."""
        mf_exit = self.findChild(QAction, "mf_exit")
        but_exit = self.findChild(QPushButton, "but_exit")

        mf_exit.triggered.connect(self.confirm_exit)
        but_exit.clicked.connect(self.confirm_exit)

        icon = self.style().standardIcon(QStyle.SP_DialogCloseButton)
        mf_exit.setIcon(icon)
        but_exit.setIcon(icon)
        mf_exit.setShortcut("Ctrl+Q")

    def setup_copy_source_button(self):
        but_copy_source = self.findChild(QPushButton, "but_copy_source")
        but_copy_source.clicked.connect(self.copy_source_to_target)

    def setup_refresh_button(self):
        but_refresh = self.findChild(QPushButton, "but_refresh_target")
        but_refresh.clicked.connect(self.refresh)

    def setup_preview_button(self):
        but_preview = self.findChild(QPushButton, "but_preview_to_target")
        but_preview.clicked.connect(self.preview)

    def refresh(self):
        tree_structure_target = self.tree_structure_target_original
        self._populate_target_tree(tree_structure_target)

    def preview(self):
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
        self.enable_main_window()

    def _populate_target_tree(self, new_tree):
        self.tree_target.clear()
        self.add_tree_items(self.tree_target.invisibleRootItem(), new_tree)
        self.tree_structure_target = new_tree

    def copy_source_to_target(self, silent=False):
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
        
        self.tree_structure_target = self.tree_structure_source.copy()
        self.tree_target.clear()
        self.tree_target.setHeaderLabel(self.tree_source.headerItem().text(0))
        self.add_tree_items(
            self.tree_target.invisibleRootItem(), self.tree_structure_target
        )
        self.tree_structure_target_original = self.tree_structure_target

    def confirm_exit(self):
        """Confirm exit from the application."""
        if (
            self.prompt_yes_no("Exit", "Are you sure you want to exit?")
            == QMessageBox.No
        ):
            return

        self.application.quit()

    def setup_scan_source(self):
        """Set up the source scan button and menu item."""
        action_scan = self.findChild(QAction, "mf_scan")
        action_scan.triggered.connect(self.scan_source_directory)

        but_select_source = self.findChild(QPushButton, "but_select_source")
        but_select_source.clicked.connect(self.scan_source_directory)

    def setup_scan_target(self):
        """Set up the target scan button."""
        but_select_target = self.findChild(QPushButton, "but_select_target")
        but_select_target.clicked.connect(self.scan_target_directory)

    def scan_source_directory(self):
        """Scan the source directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            self.config.get("Directories", "last_source_directory", fallback=""),
        )
        if not directory:
            return

        self.config.set("Directories", "last_source_directory", directory)
        with open("config.ini", "w") as config_file:
            self.config.write(config_file)

        try:
            self.scan_directory(directory, self.tree_source, "source")
        except Exception as e:
            print(f"Error: {e}")  # Print the error message to the terminal
            QMessageBox.critical(self, "Error", str(e))

    def scan_target_directory(self):
        """Scan the target directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            self.config.get("Directories", "last_target_directory", fallback=""),
        )
        if not directory:
            return

        self.config.set("Directories", "last_target_directory", directory)
        with open("config.ini", "w") as config_file:
            self.config.write(config_file)

        try:
            self.scan_directory(directory, self.tree_target, "target")
            self.tree_structure_target_original = self.tree_structure_target
        except Exception as e:
            print(f"Error: {e}")  # Print the error message to the terminal
            QMessageBox.critical(self, "Error", str(e))

    def scan_directory(self, directory, tree_widget, file_type):
        """Scan a directory and update the UI."""
        self.update_status(f"Scanning {file_type} directory: {directory}")
        self.update_statusbar(f"Scanning {file_type} directory: {directory}")

        tree_structure = get_dir_structure(directory, self.update_statusbar)
        if file_type == "source":
            self.tree_structure_source = tree_structure
        else:
            self.tree_structure_target = tree_structure

        tree_widget.clear()
        tree_widget.setHeaderLabels([directory, "Type"])

        self.add_tree_items(tree_widget.invisibleRootItem(), tree_structure)
        self.update_status(f"{file_type.capitalize()} directory scanned: {directory}")
        self.update_statusbar(
            f"{file_type.capitalize()} directory scanned: {directory}"
        )

    def add_tree_items(self, parent_item, tree_structure):
        """Add items to the tree widget."""
        # add name and type to the tree widget
        # add name and type to the tree widget
        item = QTreeWidgetItem(
            parent_item, [tree_structure.name, tree_structure.extension]
        )
        item.setIcon(ICON_INDEX, tree_structure.icon)

        for child in tree_structure.children:
            self.add_tree_items(item, child)

    def update_status(self, text):
        """Update the text in lbl_stat."""
        self.lbl_stat.setText(text)

    def update_statusbar(self, text):
        """Update the text in the status bar."""
        self.statusbar.showMessage(text)

    def prompt_yes_no(self, title, message):
        """Prompt the user for a yes or no response."""
        return QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

    def enable_main_window(self):
        self.setEnabled(True)

    def disable_main_window(self):
        self.setEnabled(False)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        if enabled:
            self.update_statusbar("Ready")
        else:
            self.update_statusbar("Busy")

        # Disable or enable all child widgets recursively
        for child_widget in self.findChildren(QtWidgets.QWidget):
            child_widget.setEnabled(enabled)

    def clear_audio_tags(self, source=True):
        labels = self.get_label_list(source)

        for label in labels:
            label.setText("")

    def display_audio_tags(self, item):
        if item is None:
            return

        source = self.sender() == self.tree_source

        if not is_supported_audio_file(item.text(1)):
            self.clear_audio_tags(source)
            return

        labels = self.get_label_list(source)

        tree_structure = (
            self.tree_structure_source if source else self.tree_structure_target
        )

        item = tree_structure.get_child_node_by_name(item.text(0))

        for label, tag in zip(labels, self.id3_tags):
            label.setText(item.get_id3_tag(tag))

    def get_label_list(self, source=True):
        return self.source_id3_labels if source else self.target_id3_labels


if __name__ == "__main__":
    # Create an instance of MainWindow
    main_window = MainWindow(app)

    # Display the main window
    main_window.show()

    # Start the application event loop
    app.exec_()
