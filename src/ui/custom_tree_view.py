import os

from PyQt5.QtWidgets import QTreeView, QFileSystemModel, QAbstractItemView
from PyQt5.QtCore import QItemSelectionModel, Qt, QDir, QFileInfo, QFile, QModelIndex
from PyQt5.QtGui import QPixmap
from typing import List, cast
from ui.custom_image_label import pop_up_image_dialogue
from log_config import get_logger

import contextlib
from PyQt5.QtWidgets import QApplication


# create logger
logger = get_logger(__name__)


class FileSystemModel(QFileSystemModel):
    def flags(self, index):
        default_flags = super().flags(index)
        if index.isValid():
            return default_flags | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsEditable
        else:
            return default_flags | Qt.ItemFlag.ItemIsDropEnabled

    def supportedDropActions(self):
        return Qt.DropAction.CopyAction | Qt.DropAction.MoveAction

    def dropMimeData(self, data, action, row, column, parent):
        logger.info(f"dropMimeData: data={data}, action={action}, row={row}, column={column}, parent={parent}")

        # Implement logic to move/copy files or directories based on the data, action, and parent parameters
        if action == Qt.IgnoreAction:
            return True

        if not data.hasUrls():
            return False

        if column > 0:
            return False

        success = all(self.copy_or_move_file(url, parent) for url in data.urls())

        if success:
            self.directoryLoaded.emit(self.filePath(parent))

        return success

    def copy_or_move_file(self, url, parent):
        file_path = url.toLocalFile()
        file_name = QFileInfo(file_path).fileName()
        destination_path = self.filePath(parent) + QDir.separator() + file_name

        logger.info(f"Moving file from '{file_path}' to '{destination_path}'")

        if QFile.exists(destination_path):
            logger.info(f"File already exists at '{destination_path}'")
            return False

        if QFile.rename(file_path, destination_path):  # Move the file
            logger.info(f"Successfully moved file to '{destination_path}'")
            return True
        else:
            logger.info(f"Failed to move file to '{destination_path}'")
            return False

    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid() and role == Qt.EditRole:
            # Get the file path at the index
            file_path = self.filePath(index)

            # Get the directory of the file
            dir_path = os.path.dirname(file_path)

            # Create the new file path
            new_file_path = os.path.join(dir_path, value)

            # Rename the file or directory
            os.rename(file_path, new_file_path)

            # Emit the dataChanged signal
            self.dataChanged.emit(index, index)

            return True

        return False

    def data(self, index, role=Qt.DisplayRole):
        if index.column() == 1 and role == Qt.DisplayRole:
            if size_str := super().data(index, role):
                # Remove unit from the string and convert to float
                size_str = size_str.replace(',', '')  # Remove comma
                size = float(size_str.split()[0])
                # Convert size from MiB to KB
                size *= 1024
                if size < 1024:
                    return f'{size:.2f} KB'
                elif size < 1024**2:
                    return f'{size / 1024:.2f} MB'
                else:
                    return f'{size / 1024**2:.2f} GB'
        return super().data(index, role)


class MyTreeView(QTreeView):
    """A TreeView that allows to select multiple items at once."""

    def __init__(self, *args, **kwargs):
        super(MyTreeView, self).__init__(*args, **kwargs)
        self.setFocusPolicy( Qt.FocusPolicy(Qt.StrongFocus))
        self.setSelectionMode(QAbstractItemView.SelectionMode(QTreeView.ExtendedSelection))

    def mousePressEvent(self, event):
        """Select multiple items on mouse click."""
        index = self.indexAt(event.pos())
        if event.button() == Qt.LeftButton:
            if index.isValid():
                self.setCurrentIndex(index)
                if QApplication.keyboardModifiers() == Qt.ControlModifier:
                    self.selectionModel().select(index, QItemSelectionModel.SelectionFlag(QItemSelectionModel.Toggle))
                else:
                    self.selectionModel().select(index, QItemSelectionModel.SelectionFlag(QItemSelectionModel.Select))
        elif event.button() == Qt.RightButton:
            if index.isValid() and not self.selectionModel().isSelected(index):
                self.setCurrentIndex(index)
                self.selectionModel().select(index, QItemSelectionModel.SelectionFlag(QItemSelectionModel.Select))
        super().mousePressEvent(event)

    def setup_tree_view(self, last_dir) -> None:
        """Sets up the tree view. Returns: None"""

        self.set_dir_as(last_dir)
        self.expanded.connect(self.resize_columns)
        self.setSortingEnabled(True)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode(QAbstractItemView.InternalMove))
        self.setDefaultDropAction(Qt.DropAction(Qt.MoveAction))

    def set_dir_as(self, last_dir) -> None:
        model = FileSystemModel()
        model.directoryLoaded.connect(self.resize_columns)
        self.__set_root_path_for_tree_view(model, last_dir)
        self.setRootIndex(model.index(last_dir))

    def set_single_click_handler(self, single_click_fn) -> None:
        self.clicked.connect(lambda index: single_click_fn(index, self))

    def set_double_click_handler(self, double_click_fn, item=None) -> None:
        self.doubleClicked.connect(lambda index: double_click_fn(index, self, item))

    def set_custom_context_menu(self, context_menu_fn) -> None:
        # Enable custom context menu
        self.setContextMenuPolicy( Qt.ContextMenuPolicy(Qt.CustomContextMenu))
        self.customContextMenuRequested.connect(lambda position: context_menu_fn(self, position))

    def resize_columns(self) -> None:
        """Resize the first column of the tree view to fit the longest filename. Returns: None"""
        for column in range(self.model().columnCount()):
            self.resizeColumnToContents(column)

    def __handle_tree_double_click_dir(self, path: str) -> None:
        """Handles the tree view double click event for directories. Returns: None"""

        model = cast(QFileSystemModel, self.model())
        self.__set_root_index_of_tree_view(path)
        self.__set_root_path_for_tree_view(model, path)

        model.directoryLoaded.connect(lambda: self.__set_root_index_of_tree_view(path))

    def on_tree_double_clicked(self, index: QModelIndex) -> None:
        """Handles the tree view double click event. Returns: None"""

        model = cast(QFileSystemModel, self.model())
        path = model.filePath(index)

        if model.isDir(index):
            self.__handle_tree_double_click_dir(path)

        elif os.path.isfile(path) and path.lower().endswith((".jpg", ".png", ".jpeg")):
            pixmap = QPixmap(path)
            pop_up_image_dialogue(path, pixmap)

    def __set_root_path_for_tree_view(self, model: QFileSystemModel, absolute_path: str):
        """Sets the root path for the given tree view."""

        model.setRootPath(absolute_path)
        self.setModel(model)
        self.sortByColumn(0, Qt.SortOrder(Qt.AscendingOrder))

    def __set_root_index_of_tree_view(self, directory) -> None:
        """Sets the root index of the tree view."""

        model = cast(QFileSystemModel, self.model())
        self.setRootIndex(model.index(self, directory))
        self.resize_columns()
        with contextlib.suppress(TypeError):
            model.directoryLoaded.disconnect()

    def go_up_one_dir_level(self) -> None:
        """Goes up one directory level."""

        model = cast(QFileSystemModel, self.model())
        current_root_path = model.filePath(self.rootIndex())
        directory = QDir(current_root_path)
        if directory.cdUp():
            self.set_dir_as(directory.absolutePath())

    def change_dir(self, directory) -> None:
        """Changes the directory of the tree view."""

        logger.info(f"Tree View {self.objectName()} Changing directory to {directory}")

        self.set_dir_as(directory)
        self.resize_columns()
        self.clearSelection()
        self.setCurrentIndex(self.model().index(self, directory))
        self.selectionModel().select(self.model().index(self, directory), QItemSelectionModel.SelectionFlag(QItemSelectionModel.Select))
        self.selectionModel().setCurrentIndex(self.model().index(self, directory), QItemSelectionModel.SelectionFlag(QItemSelectionModel.Select))

    def get_selected_file_names_relative_to_the_root(self) -> List[str]:
        """Returns a list of the selected files (inc) in the tree view."""

        selected_indexes = self.selectionModel().selectedRows()
        model = cast(QFileSystemModel, self.model())
        root_path = model.rootPath()
        return [os.path.relpath(model.filePath(i), root_path) for i in selected_indexes]

    def get_selected_files(self, default_all=False) -> List[str]:
        """Returns a list of selected file paths from the tree view, if there are no selected files and defaultAll=true, returns all files."""

        if len(self.selectionModel().selectedRows()) == 0 and default_all == True:
            self.selectAll()

        model = cast(QFileSystemModel, self.model())
        selected_indexes = self.selectionModel().selectedRows()
        selected_file_paths = [model.filePath(i) for i in selected_indexes]
        return [os.path.normpath(i) for i in selected_file_paths]

    def get_root_dir(self) -> str:
        """Returns the root directory of the tree view."""

        model = cast(QFileSystemModel, self.model())
        return os.path.normpath(model.rootPath())

    def keyPressEvent(self, event):
        super().keyPressEvent(event)

        if event.key() == Qt.Key_7 and event.modifiers() & Qt.ControlModifier:
            index = self.currentIndex()
            if index.isValid():
                # Create a new index that points to the first column of the current row
                first_column_index = self.model().index(index.row(), 0, index.parent())
                self.edit(first_column_index)