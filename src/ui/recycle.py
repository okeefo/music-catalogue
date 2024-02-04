import sys, os, winshell
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QAbstractItemView
import PyQt5.QtGui as QtGui
from PyQt5.uic import loadUi
import logging 

# create logger and set the logging level to info
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class RestoreDialog(QDialog):
    def __init__(self):
        super().__init__()
        loadUi("src//qt//recycle.ui", self)
        self.restoreButton.clicked.connect(self.restore)
        self.exitButton.clicked.connect(self.close)

        # get the list of files in the recycle bin and display them in the tableView
        r = list(winshell.recycle_bin())  # this lists the original path of all the all items in the recycling bin
        view = self.tableView
        for item in r:
            # create a new table model
            model = QtGui.QStandardItemModel(view)
            model.setHorizontalHeaderLabels(["Name","Original Path"])
            view.setModel(model)
            view.setEditTriggers(QAbstractItemView.NoEditTriggers)
            
            # add the original path of the item to the table
            item_name = QtGui.QStandardItem(os.path.basename(item.name()))
            item_original_filename = QtGui.QStandardItem(item.original_filename())
            model.appendRow([item_name, item_original_filename])
            
            view.resizeColumnsToContents()
            
        

    def restore(self):
        # Add your restore logic here
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Restore")
        if file_path:
            # Perform restore operation using the selected file
            logger.info(f"Restoring file: {file_path}")

    def closeEvent(self, event):
        logger.info("Window is being closed")
        # Call the parent class's closeEvent method to actually close the window
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = RestoreDialog()
    dialog.show()
    sys.exit(app.exec_())
