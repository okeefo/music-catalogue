from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction

# Create an instance of QApplication
app = QApplication([])

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Load the .ui file and setup the UI
        uic.loadUi('C:\\dev\\projects\\python\\music-catalogue\\src\\qt\\music_manager.ui', self)

        # Get the actionExit from the menu bar
        action_exit = self.findChild(QAction, 'actionExit')

        # Connect the triggered signal of actionExit to the quit slot of the application
        action_exit.triggered.connect(app.quit)

# Create an instance of MainWindow
main_window = MainWindow()

# Display the main window
main_window.show()

# Start the application event loop
app.exec_()


