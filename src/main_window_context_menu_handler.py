import logging
import winreg
import os
import subprocess
import send2trash

from PyQt5.QtWidgets import QAction, QMenu, QTreeView, QWidget, QMessageBox
from PyQt5 import QtGui
#from main_window import MyTreeView
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtCore import QUrl, QPoint, QModelIndex
from ui.custom_dialog import CustomDialog


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class TreeViewContextMenuHandler(QWidget):
    
    def __init__(self, player: QMediaPlayer, update_status: callable):
        logging.info("TreeViewContextMenuHandler initialising...")
        super().__init__()
        self.player = player
        self.update_status = update_status
        self.__setup_mp3tag_path()
        self.__setup_menus()
        logging.info("TreeViewContextMenuHandler initialised...")
    
    def __setup_menus(self):
        
        self.icon_play = QtGui.QIcon(":/icons/icons/play.svg")
        self.icon_pause = QtGui.QIcon(":/icons/icons/pause.svg")
        self.icon_stop = QtGui.QIcon(":/icons/icons/stop-circle.svg")
        self.icon_delete = QtGui.QIcon(":/icons/icons/delete.svg")
        self.icon_mp3tag = QtGui.QIcon(os.path.abspath("src/qt/icons/mp3tag_icon.png"))

        # define actions
        self.open_in_mp3tag_action = QAction(self.icon_mp3tag, "Open in MP3Tag", self)
        self.play_action = QAction(self.icon_play, "Play", self)
        self.stop_action = QAction(self.icon_stop, "Stop", self)
        self.pause_action = QAction(self.icon_pause, "Pause", self)
        self.delete_action = QAction(self.icon_delete, "Delete", self)

        # menu 1 - MP3 tag only
        menu = QMenu()
        menu.addAction(self.open_in_mp3tag_action)
        menu.addSeparator()
        menu.addAction(self.delete_action)
        self.cm_mp3tag_only = menu

        # menu 2 - MP3 tag and media
        menu = QMenu(self)
        menu.addAction(self.open_in_mp3tag_action)
        menu.addSeparator()
        menu.addAction(self.play_action)
        menu.addAction(self.stop_action)
        menu.addAction(self.pause_action)
        menu.addSeparator()
        menu.addAction(self.delete_action)

        self.cm_mp3tag_and_media = menu

    
    def __setup_mp3tag_path(self) -> None:
        """get mp3tag path from registry"""

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Mp3tag.exe") as key:
                self.mp3tag_path = winreg.QueryValueEx(key, "")[0]

        except Exception as e:
            logger.error(f"Failed to get Mp3tag path from registry: {e}")

        if self.mp3tag_path is None:
            self.mp3tag_path = "C:\\Program Files\\Mp3tag\\Mp3tag.exe"
            logger.warning(f"Mp3tag path not found in registry. Using default path: {self.mp3tag_path}")
            
    def handler(self, tree_view: QTreeView, index: QModelIndex, position: QPoint ) -> None:
        """Displays a context menu when right clicking on a tree view. Returns: None"""

        file_path = tree_view.model().filePath(index)

        if os.path.isdir(file_path) or len(tree_view.selectionModel().selectedRows()) > 1:
            menu = self.cm_mp3tag_only

        elif not file_path.lower().endswith((".wav", ".mp3", ".ogg", ".flac")):
            return

        else:
            menu = self.cm_mp3tag_and_media

        action = menu.exec_(tree_view.mapToGlobal(position))

        if action in [self.open_in_mp3tag_action, self.delete_action]:

            selected_indexes = tree_view.selectionModel().selectedRows()
            selected_file_paths = [tree_view.model().filePath(i) for i in selected_indexes]
            if action == self.delete_action:
                self.delete_files(selected_file_paths)
            else:
                self.open_in_mp3tag(selected_file_paths)

        elif action == self.play_action:
            if self.player.currentMedia().canonicalUrl() == QUrl.fromLocalFile(file_path):
                if self.player.mediaStatus() == QMediaPlayer.PlayingState:
                    return
            else:
                self.player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))

            self.update_status(f"Playing: {file_path}")
            self.player.play()

        elif action == self.stop_action:
            self.player.stop()
            self.update_status(f"Stopped: {file_path}")

        elif action == self.pause_action:
            self.player.pause()
            self.update_status(f"Paused: {file_path}")
    
    
    def open_in_mp3tag(self, file_path: dict) -> None:
        """Opens a file/directory in MP3Tag. Returns: None"""

        try:
            command = f'"{self.mp3tag_path}"'

            for i in range(len(file_path)):
                option = "/fp:" if os.path.isdir(file_path[i]) else "/fn:"
                if i > 0:
                    option = f"/add {option}"

                command = f'{command} {option}"{file_path[i]}"'

            subprocess.Popen(command, shell=False)

        except Exception as e:
            logger.error(f"Failed to open file/dir in MP3Tag: {e}")
    
    def delete_files(self, file_path: dict) -> None:

        selected_files = 0
        selected_dirs = 0
        for i in range(len(file_path)):
            if os.path.isdir(file_path[i]):
                selected_dirs += 1
            else:
                selected_files += 1

        message = f"Are you sure you want to delete {selected_files} files"
        message += f" and {selected_dirs} directories?" if selected_dirs > 0 else "?"
        message += f"\n\nNote: files will be moved to the recycle bin."

        response, choice = CustomDialog(message, hide_remember=True).show_dialog()

        if response == QMessageBox.Yes:
            for item in file_path:
                correct_file_path = os.path.normpath(item)
                send2trash.send2trash(correct_file_path)
