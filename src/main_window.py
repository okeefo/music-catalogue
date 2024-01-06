from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QStyle, QTreeWidget, QTreeWidgetItem, QFileDialog, QStatusBar, QLabel,QPushButton, QMessageBox
from scanner.scanner_dir import get_dir_structure
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize

# Create an instance of QApplication
app = QApplication([])

class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app

        # Load the .ui file and setup the UI
        uic.loadUi(
            "C:\\dev\\projects\\python\\music-catalogue\\src\\qt\\music_manager.ui",
            self,
        )

        # Call the setup_ui method to setup the UI
        self.setup_ui()

    def setup_ui(self):
        # Perform additional setup for the UI here
        self.update_status(
            "Welcome - select a directory to scan either from thr menu or the scan button"
        )
        self.setup_exit()
        self.setup_scan()

        self.tree_source.setHeaderLabel("No directory selected")
        self.tree_source.setIconSize(QSize(32, 32))
        self.tree_target.setHeaderLabel("No directory selected")
        self.tree_target.setIconSize(QSize(32, 32))
        
        self.tree_structure = None

    def setup_exit(self):
        mf_exit = self.findChild(QAction, "mf_exit")
        but_exit = self.findChild(QPushButton, "but_exit")

        mf_exit.triggered.connect(self.confirm_exit)
        but_exit.clicked.connect(self.confirm_exit)

        icon = self.style().standardIcon(QStyle.SP_DialogCloseButton)
        mf_exit.setIcon(icon)
        but_exit.setIcon(icon)

        mf_exit.setShortcut("Ctrl+Q")

    def confirm_exit(self):
        reply = QMessageBox.question(
            self,
            "Exit",
            "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.app.quit()
        
        

    def setup_scan(self):
        # Get the actionScan from the menu bar
        action_scan = self.findChild(QAction, "mf_scan")
        # Connect the triggered signal of actionScan to the scan_directory slot
        action_scan.triggered.connect(self.scan_directory)

        # Get the but_select_source push button
        but_select_source = self.findChild(QPushButton, "but_select_source")
        # Connect the clicked signal of but_select_source to the scan_directory slot
        but_select_source.clicked.connect(self.scan_directory)

    def scan_directory(self):
        if directory := QFileDialog.getExistingDirectory(self, "Select Directory"):
            self.update_status(f"Scanning directory: {directory}")
            self.update_statusbar(f"Scanning directory: {directory}")
            # Call the scanDirectory function and pass in the directory path

            tree_structure = get_dir_structure(directory, self.update_statusbar)
            # Store the reference to the tree structure object
            self.tree_structure = tree_structure
            # Clear the tree_source and set the header label to the selected directory
            self.tree_source.clear()
            self.tree_source.setHeaderLabel(directory)

            self.add_tree_items(self.tree_source.invisibleRootItem(), tree_structure)
            # Update the status label
            self.update_status(f"Directory scanned: {directory}")
            self.update_statusbar(f"Directory scanned: {directory}")

    def add_tree_items(self, parent_item, tree_structure):
        item = QTreeWidgetItem(parent_item, [tree_structure.name])
        item.setIcon(0, tree_structure.icon)

        for child in tree_structure.children:
            self.add_tree_items(item, child)

    def update_status(self, text):
        # Update the text in lbl_stat
        self.lbl_stat.setText(text)

    def update_statusbar(self, text):
        # Update the text in the status bar
        self.statusbar.showMessage(text)


if __name__ == "__main__":
    # Create an instance of MainWindow
    main_window = MainWindow(app)

    # Display the main window
    main_window.show()

    # Start the application event loop
    app.exec_()
