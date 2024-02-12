import winreg
import os
import subprocess
import send2trash

from PyQt5.QtWidgets import QAction, QMenu, QTreeView, QWidget, QMessageBox
from PyQt5 import QtGui

# from main_window import MyTreeView
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtCore import QUrl, QPoint, QModelIndex
from ui.custom_messagebox import ButtonType, show_message_box, convert_response_to_string
from ui.custom_tree_view import MyTreeView
from file_system_utils.copy_and_move import move_files, ask_and_move_files
from file_system_utils.repackage_dir import repackage_dir_by_label
import qt.resources_rcc

# create logger
from log_config import get_logger

logger = get_logger(__name__)


class TreeViewContextMenuHandler(QWidget):

    def __init__(self, player: QMediaPlayer, update_status: callable):
        logger.info("TreeViewContextMenuHandler initialising...")
        super().__init__()
        self.player = player
        self.update_status = update_status
        self.__setup_mp3tag_path()
        self.__setup_menus()
        self.__setup_vlc_path()
        logger.info("TreeViewContextMenuHandler initialised...")

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
        self.move_selected_action = QAction("Move", self)
        self.move_all_action = QAction("Move All", self)
        self.repackage_dir_action = QAction("Repackage this Dir", self)
        self.repackage_select_action = QAction("Repackage Selection", self)

        # menu 1 - MP3 tag only

    def __setup_mp3tag_path(self) -> None:
        """get mp3tag path from registry"""

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Mp3tag.exe") as key:
                self.mp3tag_path = winreg.QueryValueEx(key, "")[0]

        except Exception as e:
            logger.error(f"Failed to get Mp3tag path from registry: '{e}'")

        if self.mp3tag_path is None:
            self.mp3tag_path = "C:\\Program Files\\Mp3tag\\Mp3tag.exe"
            logger.warning(f"Mp3tag path not found in registry. Using default path: '{self.mp3tag_path}'")

    def __setup_vlc_path(self) -> None:

        # get VLC path from registry
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\vlc.exe") as key:
                self.vlc_path = winreg.QueryValueEx(key, "")[0]

        except Exception as e:
            logger.error(f"Failed to get VLC path from registry: '{e}'")

        if self.vlc_path is None:
            self.vlc_path = "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"
            logger.warning(f"VLC path not found in registry. Using default path: '{self.vlc_path}'")

    def get_menu_to_display(self, file_path: str, tree_view: QTreeView) -> QMenu:
        """Selects menu based on file type"""
        # create a menu
        menu = QMenu()

        # if no items are selected
        if len(tree_view.selectionModel().selectedRows()) == 0 or file_path is None:
            menu.addAction(self.move_all_action)
            menu.addAction(self.repackage_dir_action)
            return menu

        # multiple items selected
        elif os.path.isdir(file_path) or len(tree_view.selectionModel().selectedRows()) > 1:
            menu.addAction(self.open_in_mp3tag_action)
            menu.addAction(self.open_in_vlc_action)
            menu.addSeparator()
            menu.addAction(self.delete_action)
            menu.addSeparator()
            menu.addAction(self.move_selected_action)
            return menu

        # single item selected
        else:

            menu.addAction(self.open_in_mp3tag_action)
            menu.addAction(self.open_in_vlc_action)

            # add media player actions if supported audio file
            if file_path.lower().endswith((".wav", ".mp3", ".ogg", ".flac")):

                menu.addSeparator()
                menu.addAction(self.play_action)
                menu.addAction(self.stop_action)
                menu.addAction(self.pause_action)
                menu.addSeparator()
                menu.addAction(self.repackage_select_action)

            menu.addSeparator()
            menu.addAction(self.move_selected_action)
            menu.addAction(self.move_all_action)
            menu.addAction(self.delete_action)

        return menu

    def show_menu(self, tree_view: QTreeView, index: QModelIndex, position: QPoint, other_tree_view: MyTreeView) -> None:
        """Displays a context menu when right clicking on a tree view. Returns: None"""

        file_path = tree_view.model().filePath(index)

        menu = self.get_menu_to_display(file_path, tree_view)
        if menu is None:
            return

        action = menu.exec_(tree_view.mapToGlobal(position))
        self.handle_action(action, tree_view, other_tree_view.model().rootPath())

    def handle_action(self, action: QAction, tree_view: MyTreeView, dest_path: str) -> None:
        """Handles the action selected in the context menu"""

        if action == self.delete_action:
            self.delete_files(self.get_selected_file_paths(tree_view))

        elif action == self.open_in_mp3tag_action:
            self.open_in_mp3tag(self.get_selected_file_paths(tree_view))

        elif action == self.open_in_vlc_action:
            self.open_in_vlc(self.get_selected_file_paths(tree_view))

        elif action == self.repackage_dir_action:
            logger.info(f"action - repackage dir: '{tree_view.model().rootPath()}'")
            self.repackage_dir(tree_view.model().rootPath())
             
        elif action == self.move_selected_action:
            move_files(self.get_selected_file_paths(tree_view), dest_path)

        elif action == self.move_all_action:
            from_path = tree_view.model().rootPath()
            logger.info(f"action - move all from : '{from_path}' - to: '{dest_path}'")
            ask_and_move_files(from_path, dest_path)

        elif action == self.play_action:
            selected_file = self.get_selected_file_paths(tree_view)[0]
            logger.info(f"action - playing: '{selected_file}'")
            self.play_file(selected_file)
            logger.info(f"media status: '{self.player.mediaStatus()}'")

        elif action == self.stop_action:
            selected_file = self.get_selected_file_paths(tree_view)[0]
            logger.info(f"action - stop:Stopping: '{selected_file}'")
            self.player.stop()
            self.update_status(f"Stopped: '{selected_file}'")
            logger.info(f"media status: '{self.player.mediaStatus()}'")

        elif action == self.pause_action:
            selected_file = self.get_selected_file_paths(tree_view)[0]
            logger.info(f"Pausing: '{selected_file}'")
            self.player.pause()
            self.update_status(f"Paused: '{selected_file}'")
            logger.info(f"media status: '{self.player.mediaStatus()}'")

    def get_selected_file_paths(self, tree_view: QTreeView) -> list:
        """Returns a list of selected file paths from the tree view"""
        selected_indexes = tree_view.selectionModel().selectedRows()
        selected_file_paths = [tree_view.model().filePath(i) for i in selected_indexes]
        selected_file_paths = [os.path.normpath(i) for i in selected_file_paths]
        return selected_file_paths

    def play_file(self, file_path: str) -> None:
        """Plays an audio file. Returns: None"""
        if self.player.currentMedia().canonicalUrl() == QUrl.fromLocalFile(file_path):
            if self.player.mediaStatus() == QMediaPlayer.PlayingState:
                logger.info(f"Already playing: '{file_path}' - no action")
                return
        else:
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))

        self.player.play()

    def open_in_vlc(self, file_paths: dict) -> None:
        """Opens a file/directory in VLC. Returns: None"""
        logger.info(f"Opening file/s in VLC: '{self.vlc_path,file_paths}'")
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

            logger.info(f"Opening file/s in MP3Tag: '{command}'")
            subprocess.Popen(command, shell=False)
            logger.info("opening file/s in MP3Tag: done")

        except Exception as e:
            logger.error(f"Failed to open file/dir in MP3Tag: '{e}'")

    def delete_files(self, file_path: dict) -> None:
        """Deletes a file/directory. Returns: None"""
        selected_files = 0
        selected_dirs = 0
        for i in range(len(file_path)):
            if os.path.isdir(file_path[i]):
                selected_dirs += 1
            else:
                selected_files += 1
        if selected_files == 0 and selected_dirs == 0:
            logger.info("no files to delete - doing nothing...")
            self.update_status("No files selected to delete")
            return

        logger.info("prompting user to delete files")

        message = f"Are you sure you want to delete {selected_files} files"
        message += f" and {selected_dirs} directories?" if selected_dirs > 0 else "?"
        message += f"\n\nNote: files will be moved to the recycle bin."

        response = show_message_box(message, ButtonType.YesNoCancel,"Are You Sure ?", "warning")

        logger.info(f"User chose: '{convert_response_to_string(response)}'")

        if response == QMessageBox.Yes:
            for item in file_path:
                send2trash.send2trash(item)
                logger.info(f"Deleted: {item}")
            self.update_status(f"Deleted: '{selected_files}' files and '{selected_dirs}' directories")
        else:
            logger.info("Delete files cancelled")

    def repackage_dir(self, dir_path: str) -> None:
        """Repackages a directory. Returns: None"""
        logger.info(f"Repackaging dir: '{dir_path}'")
        repackage_dir_by_label(dir_path, dir_path)
