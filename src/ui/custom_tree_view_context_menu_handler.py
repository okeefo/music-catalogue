import logging
import winreg
import os
import subprocess
import send2trash

from PyQt5.QtWidgets import QAction, QMenu, QTreeView, QWidget, QMessageBox
from PyQt5 import QtGui

# from main_window import MyTreeView
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtCore import QUrl, QPoint, QModelIndex
from ui.custom_dialog import CustomDialog
from log_config import get_logger
from ui.custom_tree_view import MyTreeView
from file_system_utils.copy_and_move import move_files

# create logger
logger = get_logger(__name__)


class TreeViewContextMenuHandler(QWidget):

    def __init__(self, player: QMediaPlayer, update_status: callable):
        logging.info("TreeViewContextMenuHandler initialising...")
        super().__init__()
        self.player = player
        self.update_status = update_status
        self.__setup_mp3tag_path()
        self.__setup_menus()
        self.__setup_vlc_path()
        logging.info("TreeViewContextMenuHandler initialised...")

    def __setup_menus(self):

        self.icon_play = QtGui.QIcon(":/icons/icons/play.svg")
        self.icon_pause = QtGui.QIcon(":/icons/icons/pause.svg")
        self.icon_stop = QtGui.QIcon(":/icons/icons/stop-circle.svg")
        self.icon_delete = QtGui.QIcon(":/icons/icons/delete.svg")
        self.icon_mp3tag = QtGui.QIcon(os.path.abspath("src/qt/icons/mp3tag_icon.png"))
        self.icon_vlc = QtGui.QIcon(os.path.abspath("src/qt/icons/vlc.ico"))

        # define actions
        self.open_in_mp3tag_action = QAction(self.icon_mp3tag, "Open in MP3Tag", self)
        self.open_in_vlc_action = QAction(self.icon_vlc, "Open in VLC", self)
        self.play_action = QAction(self.icon_play, "Play", self)
        self.stop_action = QAction(self.icon_stop, "Stop", self)
        self.pause_action = QAction(self.icon_pause, "Pause", self)
        self.delete_action = QAction(self.icon_delete, "Delete", self)
        self.move_action = QAction("Move", self)

        # menu 1 - MP3 tag only
        menu = QMenu()
        menu.addAction(self.open_in_mp3tag_action)
        menu.addAction(self.open_in_vlc_action)
        menu.addSeparator()
        menu.addAction(self.delete_action)
        menu.addSeparator()
        menu.addAction(self.move_action)
        self.cm_no_media_controls = menu

        # menu 2 - MP3 tag and media
        menu = QMenu(self)
        menu.addAction(self.open_in_mp3tag_action)
        menu.addAction(self.open_in_vlc_action)
        menu.addSeparator()
        menu.addAction(self.play_action)
        menu.addAction(self.stop_action)
        menu.addAction(self.pause_action)
        menu.addSeparator()
        menu.addAction(self.delete_action)
        menu.addSeparator()
        menu.addAction(self.move_action)

        self.cm_with_media_controls = menu

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

    def __setup_vlc_path(self) -> None:

        # get VLC path from registry
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\vlc.exe") as key:
                self.vlc_path = winreg.QueryValueEx(key, "")[0]

        except Exception as e:
            logger.error(f"Failed to get VLC path from registry: {e}")

        if self.vlc_path is None:
            self.vlc_path = "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"
            logger.warning(f"VLC path not found in registry. Using default path: {self.vlc_path}")

    def handler(self, tree_view: QTreeView, index: QModelIndex, position: QPoint, other_tree_view: MyTreeView) -> None:
        """Displays a context menu when right clicking on a tree view. Returns: None"""

        file_path = tree_view.model().filePath(index)

        menu = self.get_menu_to_display(file_path, tree_view)
        if menu is None:
            return

        action = menu.exec_(tree_view.mapToGlobal(position))

        selected_indexes = tree_view.selectionModel().selectedRows()
        selected_file_paths = [tree_view.model().filePath(i) for i in selected_indexes]
        selected_file_paths = [os.path.normpath(i) for i in selected_file_paths]

        # logger.info(f"Selected indexes: {selected_file_paths}")

        self.handle_action(action, selected_file_paths, tree_view.model().rootPath(), other_tree_view.model().rootPath())

    def get_menu_to_display(self, file_path: str, tree_view: QTreeView) -> QMenu:
        """Selects menu based on file type"""
        if os.path.isdir(file_path) or len(tree_view.selectionModel().selectedRows()) > 1:
            return self.cm_no_media_controls

        elif not file_path.lower().endswith((".wav", ".mp3", ".ogg", ".flac")):
            return

        else:
            return self.cm_with_media_controls

    def handle_action(self, action: QAction, selected_file_paths: list, this_path: str, that_path: str) -> None:
        """Handles the action selected in the context menu"""

        if action == self.delete_action:
            self.delete_files(selected_file_paths)

        elif action == self.open_in_mp3tag_action:
            self.open_in_mp3tag(selected_file_paths)

        elif action == self.open_in_vlc_action:
            self.open_in_vlc(selected_file_paths)

        elif action == self.move_action:
            logger.info(f"action - move: {selected_file_paths} - from:{this_path} - to:{that_path}")
            move_files(selected_file_paths, this_path, that_path)

        elif action == self.play_action:
            logger.info(f"action - playing: {selected_file_paths[0]}")
            self.play_file(selected_file_paths[0])
            logger.info(f"media status: {self.player.mediaStatus()}")

        elif action == self.stop_action:
            logger.info(f"action - stop:Stopping: {selected_file_paths[0]}")
            self.player.stop()
            self.update_status(f"Stopped: {selected_file_paths[0]}")
            logger.info(f"media status: {self.player.mediaStatus()}")

        elif action == self.pause_action:
            logger.info(f"Pausing: {selected_file_paths[0]}")
            self.player.pause()
            self.update_status(f"Paused: {selected_file_paths[0]}")
            logger.info(f"media status: {self.player.mediaStatus()}")

    def play_file(self, file_path: str) -> None:
        """Plays a file. Returns: None"""
        if self.player.currentMedia().canonicalUrl() == QUrl.fromLocalFile(file_path):
            if self.player.mediaStatus() == QMediaPlayer.PlayingState:
                logger.info(f"Already playing: {file_path} - no action")
                return
        else:
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))

        self.player.play()

    def open_in_vlc(self, file_paths: dict) -> None:
        """Opens a file/directory in VLC. Returns: None"""
        logger.info(f"Opening file/s in VLC: {self.vlc_path,file_paths}")
        command = [self.vlc_path] + file_paths
        subprocess.Popen(command, shell=False)
        logger.info(f"opening file/s in VLC: done")

    def open_in_mp3tag(self, file_path: dict) -> None:
        """Opens a file/directory in MP3Tag. Returns: None"""

        try:
            command = f'"{self.mp3tag_path}"'

            for i in range(len(file_path)):
                option = "/fp:" if os.path.isdir(file_path[i]) else "/fn:"
                if i > 0:
                    option = f"/add {option}"

                command = f'{command} {option}"{file_path[i]}"'

            logger.info(f"Opening file/s in MP3Tag: {command}")
            subprocess.Popen(command, shell=False)
            logger.info("opening file/s in MP3Tag: done")

        except Exception as e:
            logger.error(f"Failed to open file/dir in MP3Tag: {e}")

    def delete_files(self, file_path: dict) -> None:
        """Deletes a file/directory. Returns: None"""
        selected_files = 0
        selected_dirs = 0
        for i in range(len(file_path)):
            if os.path.isdir(file_path[i]):
                selected_dirs += 1
            else:
                selected_files += 1

        logger.info("prompting user to delete files")

        message = f"Are you sure you want to delete {selected_files} files"
        message += f" and {selected_dirs} directories?" if selected_dirs > 0 else "?"
        message += f"\n\nNote: files will be moved to the recycle bin."

        response, choice = CustomDialog(message, hide_remember=True).show_dialog()

        logger.info(f"User chose: {choice}")

        if response == QMessageBox.Yes:
            for item in file_path:
                send2trash.send2trash(item)
                logger.info(f"Deleted: {item}")
            self.update_status(f"Deleted: {selected_files} files and {selected_dirs} directories")
        else:
            logger.info("Delete files cancelled")
