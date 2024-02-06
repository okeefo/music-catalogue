import sys, winshell
import logging
import os
import win32com.client

import io

from PyQt5.QtWidgets import QApplication, QDialog, QTreeView, QFileIconProvider
from PyQt5.QtCore import QDir, QModelIndex, QAbstractItemModel, Qt, QFileInfo
from PyQt5.uic import loadUi
from PyQt5.QtGui import QIcon
from PIL import Image


# create logger and set the logging level to info
logging.basicConfig(format="%(asctime)s - %(name)s - %(funcName)s - %(levelname)s -  %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RestoreDialog(QDialog):
    def __init__(self):
        super().__init__()
        loadUi("src//qt//recycle.ui", self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.restoreButton.clicked.connect(self.restore)
        self.exitButton.clicked.connect(self.close)

        # get the list of files in the recycle bin and display them in the tableView
        self.treeView = self.findChild(QTreeView, "treeView")
        model = RecycleBinModel()
        self.treeView.setModel(model)
        self.treeView.setRootIsDecorated(False)  # Disable the expandable arrow indicator
        self.treeView.setColumnHidden(2, True)
        self.treeView.resizeColumnToContents(0)
        
    def restore(self):
        """ Restore the selected files from the recycle bin. """
        selected_indexes = self.treeView.selectionModel().selectedRows()
        # Collect all items to restore in a separate list
        for index in selected_indexes:
            model: RecycleBinModel = self.treeView.model()
            
            og_file = index.sibling(index.row(),0).data()
            og_path =index.sibling(index.row(),1).data()
            origin_file_loc = os.path.join(og_path, og_file)
            recyc_file = index.sibling(index.row(),2).data()
            
            logger.info("Restoring file: %s to %s", recyc_file, origin_file_loc)
            winshell.undelete(origin_file_loc)
            logger.info("Restored file: %s to %s", recyc_file, origin_file_loc)

        model.update_model_data()
        self.treeView.reset()

                    
            
    def closeEvent(self, event):
        logger.info("Window is being closed")
        # Call the parent class's closeEvent method to actually close the window
        super().closeEvent(event)


class RecycleBinModel(QAbstractItemModel):
    def __init__(self):
        super().__init__()
        self.shell = win32com.client.Dispatch("Shell.Application")
        self.namespace = self.shell.Namespace(10)  # 10 is the code for the Recycle Bin
        self.items = list(self.namespace.Items())

    def rowCount(self, parent=QModelIndex()):
        return len(self.items)

    def columnCount(self, parent=QModelIndex()):
        return 3  # We'll have two columns: one for the filename and one for the path

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return ["Original Filename", "Original Path", "FSO file"][section]
        return None

    def index(self, row, column, parent=QModelIndex()):
        return self.createIndex(row, column)

    def parent(self, index):
        return QModelIndex()

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if index.isValid():
            item = self.items[index.row()]
            if role == Qt.DisplayRole:
                if index.column() == 0:
                    return  self.namespace.GetDetailsOf(item, 0) # 0 is the code for the original filename
                elif index.column() == 1:
                    return self.namespace.GetDetailsOf(item, 1) # 0 is the code for the original filename
                elif index.column() == 2:
                    return item.Path
            elif role == Qt.DecorationRole and index.column() == 0:
                icon_provider = QFileIconProvider()
                return icon_provider.icon(QFileInfo(item.Path))
        return None
  
    
    def update_model_data(self):
        """ Update the model data by re-fetching the items from the recycle bin. """
        self.namespace = self.shell.Namespace(10)  # 10 is the code for the Recycle Bin
        self.items = list(self.namespace.Items())
        #self.items = list(winshell.recycle_bin().items())
        self.layoutChanged.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = RestoreDialog()
    dialog.show()
    sys.exit(app.exec_())
