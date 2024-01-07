from PyQt5 import uic
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QAction,
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
    QFileDialog,
    QStatusBar,
    QLabel,
    QPushButton,
    QMessageBox,
)
from scanner.scanner_dir import get_dir_structure
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize
import configparser

# Create an instance of QApplication
app = QApplication([])

ICON_INDEX = 0


class MainWindow(QMainWindow):
    """Main window class for the application."""

    def __init__(self, app):
        """Initialize the main window."""
        super().__init__()
        self.app = app
        self.config = configparser.ConfigParser()
        self.config.read("config.ini")
        if "Directories" not in self.config:
            self.config.add_section("Directories")

        # Load the .ui file and setup the UI
        uic.loadUi(
            "C:\\dev\\projects\\python\\music-catalogue\\src\\qt\\music_manager.ui",
            self,
        )

        # Call the setup_ui method to setup the UI
        self.setup_ui()

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

    def setup_tree_widgets(self):
        self.tree_source = self.findChild(QTreeWidget, "tree_source")
        self.tree_target = self.findChild(QTreeWidget, "tree_target")
        self.tree_source.setHeaderLabel("No directory selected")
        self.tree_target.setHeaderLabel("No directory selected")
        self.tree_source.setIconSize(QSize(32, 32))
        self.tree_target.setIconSize(QSize(32, 32))
        self.tree_structure_source = None
        self.tree_structure_target = None

    def setup_exit(self):
        """Setup the exit button and menu item."""
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

    def copy_source_to_target(self):
        if self.tree_structure_source is None:
            QMessageBox.critical(self, "Error", "Source directory not scanned")
            return

        reply = self.prompt_yes_no(
            "Confirmation",
            "Are you sure you want to copy the source to the target?",
        )
        if reply == QMessageBox.No:
            return
        self.tree_structure_target = self.tree_structure_source
        self.tree_target.clear()
        self.tree_target.setHeaderLabel(self.tree_structure_target.name)
        self.add_tree_items(self.tree_target.invisibleRootItem(), self.tree_structure_target)

        QMessageBox.information(self, "Success", "Copy complete")

    def confirm_exit(self):
        """Confirm exit from the application."""
        if (
            self.prompt_yes_no("Exit", "Are you sure you want to exit?")
            == QMessageBox.No
        ):
            return

        self.app.quit()

    def setup_scan_source(self):
        """Setup the source scan button and menu item."""
        action_scan = self.findChild(QAction, "mf_scan")
        action_scan.triggered.connect(self.scan_source_directory)

        but_select_source = self.findChild(QPushButton, "but_select_source")
        but_select_source.clicked.connect(self.scan_source_directory)

    def setup_scan_target(self):
        """Setup the target scan button."""
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
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def scan_directory(self, directory, tree_widget, type):
        """Scan a directory and update the UI."""
        self.update_status(f"Scanning {type} directory: {directory}")
        self.update_statusbar(f"Scanning {type} directory: {directory}")

        tree_structure = get_dir_structure(directory, self.update_statusbar)
        if type == "source":
            self.tree_structure_source = tree_structure
        else:
            self.tree_structure_target = tree_structure

        tree_widget.clear()
        tree_widget.setHeaderLabel(directory)

        self.add_tree_items(tree_widget.invisibleRootItem(), tree_structure)
        self.update_status(f"{type.capitalize()} directory scanned: {directory}")
        self.update_statusbar(f"{type.capitalize()} directory scanned: {directory}")

    def add_tree_items(self, parent_item, tree_structure):
        """Add items to the tree widget."""
        item = QTreeWidgetItem(parent_item, [tree_structure.name])
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


if __name__ == "__main__":
    # Create an instance of MainWindow
    main_window = MainWindow(app)

    # Display the main window
    main_window.show()

    # Start the application event loop
    app.exec_()
