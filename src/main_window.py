from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction
from PyQt5.QtWidgets import QFileDialog

# Create an instance of QApplication
app = QApplication([])


class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()

            # Load the .ui file and setup the UI
            uic.loadUi(
                "C:\\dev\\projects\\python\\music-catalogue\\src\\qt\\music_manager.ui",
                self,
            )

            # Call the setup_ui method to setup the UI
            self.setup_ui()

        def setup_ui(self):
            # Perform additional setup for the UI here
            self.update_status("Welcome - select a directory to scan either from thr menu or the scan button")
            self.setup_exit()
            self.setup_scan()

        def setup_exit(self):
            # Get the actionExit from the menu bar
            action_exit = self.findChild(QAction, "mf_exit")
            # Connect the triggered signal of actionExit to the quit slot of the application
            action_exit.triggered.connect(app.quit)

        def setup_scan(self):
            # Get the actionScan from the menu bar
            action_scan = self.findChild(QAction, "mf_scan")
            # Connect the triggered signal of actionScan to the scan_directory slot
            action_scan.triggered.connect(self.scan_directory)

        def scan_directory(self):
            # Open a directory dialog to select a directory
            directory = QFileDialog.getExistingDirectory(self, "Select Directory")
            # Update the label with the selected directory path
            if directory:
                self.update_status("Scanning directory: " + directory)
                self.update_statusbar("Scanning directory: " + directory)

        def update_status(self, text):
            # Update the text in lbl_stat
            self.lbl_stat.setText(text)
            
        def update_statusbar(self,text):
            # Update the text in the status bar
            self.statusbar.showMessage(text)
        


# Create an instance of MainWindow
main_window = MainWindow()

# Display the main window
main_window.show()

# Start the application event loop
app.exec_()
