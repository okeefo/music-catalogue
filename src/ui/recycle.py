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
        self.treeView.resizeColumnToContents(0)

    def restore(self):
        # get selected row from treeview
        shell = win32com.client.Dispatch("Shell.Application")
        namespace = shell.Namespace(10)  # 10 is the code for the Recycle Bin
        for item in namespace.Items():
            original_path = namespace.GetDetailsOf(item, 1)  # 1 is the code for the original path
            original_filename = namespace.GetDetailsOf(item, 0)  # 0 is the code for the original filename
            print("Original Path: ", original_path)
            print("Original Filename: ", original_filename)

    def closeEvent(self, event):
        logger.info("Window is being closed")
        # Call the parent class's closeEvent method to actually close the window
        super().closeEvent(event)


class RecycleBinModel(QAbstractItemModel):
    def __init__(self):
        super().__init__()
        shell = win32com.client.Dispatch("Shell.Application")
        self.namespace = shell.Namespace(10)  # 10 is the code for the Recycle Bin
        self.items = list(self.namespace.Items())

    def rowCount(self, parent=QModelIndex()):
        return len(self.items)

    def columnCount(self, parent=QModelIndex()):
        return 2  # We'll have two columns: one for the filename and one for the path

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return ["Original Filename", "Original Path"][section]
        return None

    def index(self, row, column, parent=QModelIndex()):
        return self.createIndex(row, column)

    def parent(self, index):
        return QModelIndex()

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            item = self.items[index.row()]
            if role == Qt.DisplayRole:
                if index.column() == 0:
                    return self.namespace.GetDetailsOf(item, 0)  # 0 is the code for the original filename
                elif index.column() == 1:
                    return self.namespace.GetDetailsOf(item, 1)  # 1 is the code for the original path
            elif role == Qt.DecorationRole and index.column() == 0:
                icon_provider = QFileIconProvider()
                return icon_provider.icon(QFileInfo(item.Path))
        return None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = RestoreDialog()
    dialog.show()
    sys.exit(app.exec_())
