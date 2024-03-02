import winreg
import os
import subprocess

from PyQt5 import QtGui
from PyQt5.QtWidgets import QAction, QMenu, QTreeView, QWidget, QMessageBox
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtCore import QUrl, QPoint, QModelIndex

from typing import List

from ui.custom_tree_view import MyTreeView
from file_operations.file_utils import ask_and_move_files, delete_files, ask_and_copy_files
from file_operations.repackage_dir import repackage_dir_by_label, repackage_files_by_label
from file_operations.files_system_info import display_results
from file_operations.auto_tag import auto_tag_files, tag_filename
from file_operations.audio_tags import AudioTagHelper

import qt.resources_rcc

# create logger
from log_config import get_logger

logger = get_logger(__name__)


class TreeViewContextMenuHandler(QWidget):

    def __init__(self, player: QMediaPlayer, update_status: callable):
        """Initialise the TreeViewContextMenuHandler."""
        super().__init__()
        self.player = player
        self.update_status = update_status
        self.__setup_mp3tag_path()
        self.__setup_menus()
        self.__setup_vlc_path()
        self.__setup_action_map()
        self.__setup_display_menu_map()
        self.audio_tag_helper = AudioTagHelper()
        self.clipboard = []

    def __setup_display_menu_map(self):
        self.display_menu_map = {
            "info": {0: [self.info_dir_action], "default": [self.info_dir_action, self.info_selected_action]},
            "new_folder": {0: [self.new_folder_action], "default": [self.new_folder_action]},
            "rename": {1: [self.rename_file_action]},
            "open_in": {"default": [self.open_in_mp3tag_action, self.open_in_vlc_action]},
            "tag": {0: [self.auto_tag_dir_action], "override": [self.auto_tag_dir_action], "default": [self.auto_tag_dir_action, self.auto_tag_selected_action]},
            "tag_filename": {0: [self.tag_filename_dir_action], "override": [self.tag_filename_dir_action], "default": [self.tag_filename_dir_action, self.tag_filename_selected_action]},
            "media_player": {"override": [self.play_action, self.stop_action, self.pause_action]},
            "repackage": {0: [self.repackage_dir_action], "override": [self.repackage_dir_action], "default": [self.repackage_dir_action, self.repackage_select_action]},
            "move": {0: [self.move_all_action], "default": [self.move_all_action, self.move_selected_action]},
            "copy": {0: [self.copy_selected_across_action], "default": [self.copy_selected_across_action, self.copy_selected_to_clipboard_action]},
            "paste": {"override": [self.paste_items_to_root_action, self.paste_items_to_selected_action]},
            "delete": {0: [], "default": [self.delete_action]},
        }

    def __setup_action_map(self):
        self.action_map = {
            self.delete_action: lambda tree_view, dest_path: self.__do_delete(tree_view),
            self.open_in_mp3tag_action: lambda tree_view, dest_path: self.__do_open_in_mp3tag(tree_view),
            self.open_in_vlc_action: lambda tree_view, dest_path: self.__do_open_in_vlc(tree_view),
            self.repackage_dir_action: lambda tree_view, dest_path: self.__do_repackage_dir_by_label(tree_view),
            self.repackage_select_action: lambda tree_view, dest_path: self.__do_repackage_selected_items_by_label(tree_view),
            self.move_selected_action: lambda tree_view, dest_path: self.__do_move_selected_items(tree_view, dest_path),
            self.move_all_action: lambda tree_view, dest_path: self.__do_move_all(tree_view, dest_path),
            self.play_action: lambda tree_view, dest_path: self.__do_play_media(tree_view),
            self.stop_action: lambda tree_view, dest_path: self.__do_stop_media(),
            self.pause_action: lambda tree_view, dest_path: self.__do_pause_media(),
            self.info_dir_action: lambda tree_view, dest_path: self.__do_show_info_dir(tree_view),
            self.info_selected_action: lambda tree_view, dest_path: self.__do_show_info_selected_items(tree_view),
            self.copy_selected_across_action: lambda tree_view, dest_path: self.__do_copy_selected_items_to_destination(tree_view, dest_path),
            self.copy_selected_to_clipboard_action: lambda tree_view, dest_path: self.__do_copy_selected_items_to_clipboard(tree_view),
            self.paste_items_to_root_action: lambda tree_view, dest_path: self.__do_paste_items_from_clipboard(tree_view),
            self.paste_items_to_selected_action: lambda tree_view, dest_path: self.__do_paste_items_from_clipboard(tree_view, True),
            self.rename_file_action: lambda tree_view, dest_path: self.__do_rename_file(tree_view),
            self.auto_tag_dir_action: lambda tree_view, dest_path: self.__do_auto_tag_dir(tree_view),
            self.auto_tag_selected_action: lambda tree_view, dest_path: self.__do_auto_tag_selected_items(tree_view),
            self.tag_filename_dir_action: lambda tree_view, dest_path: self.__do_tag_filename_dir(tree_view),
            self.tag_filename_selected_action: lambda tree_view, dest_path: self.__do_tag_filename_selection(tree_view),
            self.new_folder_action: lambda tree_view, dest_path: self.__do_new_folder(tree_view),
        }

    def __setup_menus(self):
        """Set up the menus."""

        # define actions
        self.open_in_mp3tag_action = QAction(QtGui.QIcon(os.path.abspath("src/qt/icons/mp3tag_icon.png")), "Open in MP3Tag", self)
        self.open_in_vlc_action = QAction(QtGui.QIcon(os.path.abspath("src/qt/icons/vlc.ico")), "Open in VLC", self)
        self.play_action = QAction(QtGui.QIcon(":/icons/icons/play.svg"), "Play", self)
        self.stop_action = QAction(QtGui.QIcon(":/icons/icons/stop-circle.svg"), "Stop", self)
        self.pause_action = QAction(QtGui.QIcon(":/icons/icons/pause.svg"), "Pause", self)
        self.delete_action = QAction(QtGui.QIcon(":/icons/icons/delete.svg"), "Delete", self)
        self.move_selected_action = QAction(QtGui.QIcon(":/icons/icons/send.svg"), "Move", self)
        self.move_all_action = QAction(QtGui.QIcon(":/icons/icons/send.svg"), "Move All", self)
        self.repackage_dir_action = QAction(QtGui.QIcon(":/icons/icons/briefcase.svg"), "Repackage All", self)
        self.repackage_select_action = QAction(QtGui.QIcon(":/icons/icons/briefcase.svg"), "Repackage", self)
        self.info_dir_action = QAction(QtGui.QIcon(":/icons/icons/info.svg"), "Info all items", self)
        self.info_selected_action = QAction(QtGui.QIcon(":/icons/icons/info.svg"), "Info selected items", self)
        self.copy_selected_across_action = QAction(QtGui.QIcon(":/icons/icons/clipboard.svg"), "Copy across.", self)
        self.copy_selected_to_clipboard_action = QAction(QtGui.QIcon(":/icons/icons/clipboard.svg"), "Copy items to clipboard", self)
        self.paste_items_to_root_action = QAction(QtGui.QIcon(":/icons/icons/copy.svg"), "Paste here", self)
        self.paste_items_to_selected_action = QAction(QtGui.QIcon(":/icons/icons/copy.svg"), "Paste in selected dir", self)
        self.rename_file_action = QAction(QtGui.QIcon(":/icons/icons/type.svg"), "Rename (F2 or Ctrl+7)", self)
        self.auto_tag_dir_action = QAction(QtGui.QIcon(":/icons/icons/globe.svg"), "ID Tag - All ", self)
        self.auto_tag_selected_action = QAction(QtGui.QIcon(":/icons/icons/globe.svg"), "ID Tag", self)
        self.tag_filename_selected_action = QAction(QtGui.QIcon(":/icons/icons/hash.svg"), "Tags -> Filename", self)
        self.tag_filename_dir_action = QAction(QtGui.QIcon(":/icons/icons/hash.svg"), "Tags -> Filename - All", self)
        self.new_folder_action = QAction(QtGui.QIcon(":/icons/icons/folder-plus.svg"), "New Folder", self)

        # menu 1 - MP3 tag only

    def __clear_clipboard(self) -> None:
        """Clear the clipboard. Returns: None"""
        self.clipboard = []

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
        """get vlc path from registry"""

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\vlc.exe") as key:
                self.vlc_path = winreg.QueryValueEx(key, "")[0]

        except Exception as e:
            logger.error(f"Failed to get VLC path from registry: '{e}'")

        if self.vlc_path is None:
            self.vlc_path = "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"
            logger.warning(f"VLC path not found in registry. Using default path: '{self.vlc_path}'")

    def __add_actions_to_menu(self, menu: QMenu, action_type: str, number_of_selected_items: int, override: bool = False) -> None:
        """Adds actions to the menu based on the number of selected items and the type of action. Returns: None"""

        if override:
            actions = self.display_menu_map[action_type].get("override")
        else:

            actions = self.display_menu_map[action_type].get(number_of_selected_items if number_of_selected_items <= 1 else "multiple")
            if actions is None:
                actions = self.display_menu_map[action_type].get("default", [])

        if actions:
            menu.addActions(actions)
            menu.addSeparator()

    def get_menu_to_display(self, file_path: str, tree_view: QTreeView) -> QMenu:
        """Selects menu based on file type"""
        menu = QMenu()

        number_of_selected_items = len(tree_view.selectionModel().selectedRows())
        is_dir = number_of_selected_items == 1 and os.path.isdir(file_path)
        is_audio_file = number_of_selected_items == 1 and self.audio_tag_helper.isSupportedAudioFile(file_path)

        self.__add_actions_to_menu(menu, "info", number_of_selected_items)
        self.__add_actions_to_menu(menu, "new_folder", number_of_selected_items)
        self.__add_actions_to_menu(menu, "rename", number_of_selected_items)
        self.__add_actions_to_menu(menu, "open_in", number_of_selected_items)
        self.__add_actions_to_menu(menu, "tag", number_of_selected_items, is_dir)
        self.__add_actions_to_menu(menu, "tag_filename", number_of_selected_items, is_dir)
        self.__add_actions_to_menu(menu, "media_player", number_of_selected_items, is_audio_file)
        self.__add_actions_to_menu(menu, "repackage", number_of_selected_items, is_dir)
        self.__add_actions_to_menu(menu, "move", number_of_selected_items)
        self.__add_actions_to_menu(menu, "copy", number_of_selected_items)
        self.__add_actions_to_menu(menu, "paste", number_of_selected_items)
        self.__add_actions_to_menu(menu, "delete", number_of_selected_items)

        return menu

    def show_menu(self, tree_view: QTreeView, index: QModelIndex, position: QPoint, other_tree_view: MyTreeView) -> None:
        """Displays a context menu when right clicking on a tree view. Returns: None"""

        logger.info("Showing context menu...")
        file_path = tree_view.model().filePath(index)

        menu = self.get_menu_to_display(file_path, tree_view)
        if menu is None:
            return

        action = menu.exec_(tree_view.mapToGlobal(position))
        self.handle_action(action, tree_view, other_tree_view.get_root_dir())

    def handle_action(self, action: QAction, tree_view: MyTreeView, dest_path: str) -> None:
        """Handles the action selected in the context menu"""

        if action in self.action_map:
            self.action_map[action](tree_view, dest_path)
        elif action is not None:
            logger.error(f"Action {action} not recognized.")

    def __do_delete(self, tree_view: MyTreeView) -> None:
        """Deletes selected files. Returns: None"""

        logger.info("Menu action - delete")
        result = delete_files(tree_view.get_selected_files())
        self.update_status(result)
        logger.info("Menu action - delete : done")

    def __do_open_in_mp3tag(self, tree_vew: MyTreeView) -> None:
        """Opens a file/directory in MP3Tag. Returns: None"""

        file_path = tree_vew.get_selected_files(True)
        logger.info(f"Menu Action -> Opening file/s in MP3Tag: '{file_path}'")
        try:
            command = f'"{self.mp3tag_path}"'

            for i in range(len(file_path)):
                option = "/fp:" if os.path.isdir(file_path[i]) else "/fn:"
                if i > 0:
                    option = f"/add {option}"

                command = f'{command} {option}"{file_path[i]}"'

            logger.info(f"Opening file/s in MP3Tag: '{command}'")
            subprocess.Popen(command, shell=False)
            logger.info("Menu Action -> opening file/s in MP3Tag: done")

        except Exception as e:
            logger.error(f"Failed to open file/dir in MP3Tag: '{e}'")

    def __do_open_in_vlc(self, tree_view: MyTreeView) -> None:
        """Opens a file/directory in VLC. Returns: None"""

        file_paths = tree_view.get_selected_files(True)
        logger.info(f"Menu Action -> Opening file/s in VLC: '{self.vlc_path,file_paths}'")
        command = [self.vlc_path] + file_paths
        subprocess.Popen(command, shell=False)
        logger.info(f"Menu Action -> opening file/s in VLC: done")

    def __do_repackage_dir_by_label(self, tree_view: MyTreeView) -> None:
        """Repackages a directory. Returns: None"""

        directory = tree_view.get_root_dir()
        logger.info(f"Menu Action -> repackage dir by label : '{directory}'")
        repackage_dir_by_label(directory, directory)
        logger.info("Menu Action -> repackage dir by label : done")
        self.update_status(f"Repackaged directory by label : '{directory}'")

    def __do_repackage_selected_items_by_label(self, tree_view: MyTreeView) -> None:
        """Repackages selected items by label. Returns: None"""

        logger.info("Menu Action -> repackage selected items by label")
        repackage_files_by_label(tree_view.get_selected_file_names_relative_to_the_root(), tree_view.get_root_dir(), tree_view.get_root_dir())
        logger.info("Menu Action -> repackage selected items by label : done")
        self.update_status("Repackaged selected items by label")

    def __do_move_selected_items(self, tree_view: MyTreeView, dest_path: str) -> None:
        """Moves selected items to a destination path. Returns: None"""

        logger.info(f"Menu Action -> move selected items : '{dest_path}'")
        ask_and_move_files(tree_view.get_selected_file_names_relative_to_the_root(), tree_view.get_root_dir(), dest_path)
        logger.info("Menu Action -> move selected items : done")
        self.update_status(f"Moved selected items to '{dest_path}'")

    def __do_move_all(self, tree_view: MyTreeView, dest_path: str) -> None:
        """Moves all items to a destination path. Returns: None"""

        from_dir = tree_view.get_root_dir()
        logger.info(f"Menu Action -> move all items : from '{from_dir}' to '{dest_path}'")
        ask_and_move_files(os.listdir(from_dir), from_dir, dest_path)
        logger.info("Menu Action -> move all items : done")
        self.update_status(f"Moved all items to '{dest_path}'")

    def __do_play_media(self, tree_view: MyTreeView) -> None:
        """Plays a file. Returns: None"""

        selected_file = tree_view.get_selected_files()[0]
        logger.info(f"Menu action -> play file :Playing: '{selected_file}'")
        self.play_file(selected_file)
        self.update_status(f"Playing: '{selected_file}'")
        logger.info(f"media status: '{self.player.mediaStatus()}'")
        logger.info("Menu action -> play file : done")

    def __do_stop_media(self) -> None:
        """Stops the media player. Returns: None"""

        logger.info(f"Menu action -> stop: Stopping media player: {self.player.mediaStatus()}")
        self.player.stop()
        self.__log_media_update("Stopped", "stop")

    def __do_pause_media(self) -> None:
        """Pauses the media player. Returns: None"""

        logger.info(f"Menu action -> pause: Pausing media player: {self.player.mediaStatus()}")
        self.player.pause()
        self.__log_media_update("Paused", " done")

    def __log_media_update(self, status_action, menu_action):
        """Logs the media status and updates the status bar. Returns: None"""

        self.update_status(f"{status_action} media player")
        logger.info(f"Media status: '{self.player.mediaStatus()}'")
        logger.info(f"Menu action -> {menu_action}: done")

    def play_file(self, file_path: str) -> None:
        """Plays an audio file. Returns: None"""

        if self.player.currentMedia().canonicalUrl() == QUrl.fromLocalFile(file_path):
            if self.player.mediaStatus() == QMediaPlayer.PlayingState:
                logger.info(f"Already playing: '{file_path}' - no action")
                return
        else:
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))

        self.player.play()

    def __do_show_info_dir(self, tree_view: MyTreeView) -> None:
        """Shows info for all items in a directory. Returns: None"""

        logger.info("Menu action -> info dir")
        root_dir = tree_view.get_root_dir()
        self.update_status(f"Showing info for all items in directory {root_dir}")
        display_results([root_dir], True)
        logger.info("Menu action -> info dir : done")

    def __do_show_info_selected_items(self, tree_view: MyTreeView) -> None:
        """Shows info for selected items. Returns: None"""

        logger.info("Menu action -> info selected items")
        self.update_status("Showing info for selected items")
        display_results(tree_view.get_selected_files())
        logger.info("Menu action -> info selected items : done")

    def __do_copy_selected_items_to_clipboard(self, tree_view: MyTreeView) -> None:
        """Copies selected items to clipboard. Returns: None"""

        logger.info("Menu action -> copy selected items to clipboard")
        self.clipboard = tree_view.get_selected_files()
        logger.info("Menu action -> copy selected items to clipboard : done")

    def __do_paste_items_from_clipboard(self, tree_view: MyTreeView, toSelectedDir: bool = False) -> None:
        """Pastes items from clipboard. Returns: None"""

        logger.info("Menu action -> paste items from clipboard")
        if toSelectedDir:
            ask_and_copy_files(self.clipboard, tree_view.get_selected_files()[0])
        else:
            ask_and_copy_files(self.clipboard, tree_view.get_root_dir())
        self.__clear_clipboard()
        logger.info("Menu action -> paste items from clipboard : done")

    def __do_copy_selected_items_to_destination(self, tree_view: MyTreeView, dest_path: str) -> None:
        """Copies selected items to a destination path. Returns: None"""

        logger.info(f"Menu action -> copy selected items to destination: '{dest_path}'")
        ask_and_copy_files(tree_view.get_selected_files(), dest_path)
        logger.info("Menu action -> copy selected items to destination : done")
        self.update_status(f"Copied selected items to '{dest_path}'")

    def __do_rename_file(self, tree_view: MyTreeView) -> None:
        """Renames a file. Returns: None"""

        logger.info("Menu action -> rename file")
        ## rename the file/dir at the current index
        logger.info(f"Old filename {tree_view.currentIndex().data()}")

        tree_view.edit(tree_view.currentIndex())
        logger.info(f"New filename {tree_view.currentIndex().data()}")
        logger.info("Menu action -> rename file : done")

    def __do_auto_tag_dir(self, tree_view: MyTreeView) -> None:
        """Auto tags all files in a directory. Returns: None"""

        logger.info("Menu action -> auto tag dir")
        self.update_status("Auto tagging directory")
        auto_tag_files(os.listdir(tree_view.get_root_dir()), tree_view.get_root_dir())
        logger.info("Menu action -> auto tag dir : done")

    def __do_auto_tag_selected_items(self, tree_view: MyTreeView) -> None:
        """Auto tags selected items. Returns: None"""

        logger.info("Menu action -> auto tag selected items")
        self.update_status("Auto tagging selected items")
        auto_tag_files(tree_view.get_selected_files(), tree_view.get_root_dir())
        logger.info("Menu action -> auto tag selected items : done")

    def __do_tag_filename_selection(self, tree_view: MyTreeView) -> None:
        """Tags the filename of selected items. Returns: None"""

        logger.info("Menu action -> tag filename selected items")
        self.update_status("Tagging filename of selected items")
        tag_filename(tree_view.get_selected_files(), tree_view.get_root_dir())
        logger.info("Menu action -> tag filename selected items : done")

    def __do_tag_filename_dir(self, tree_view: MyTreeView) -> None:
        """Tags the filename of all items in a directory. Returns: None"""

        logger.info("Menu action -> tag filename dir")
        self.update_status("Tagging filename of all items in directory")
        tag_filename(os.listdir(tree_view.get_root_dir()), tree_view.get_root_dir())
        logger.info("Menu action -> tag filename dir : done")

    def __do_new_folder(self, tree_view: MyTreeView) -> None:
        """Creates a new folder. Returns: None"""

        logger.info("Menu action -> new folder")
        root = tree_view.get_root_dir()
        os.mkdir(os.path.join(root, "New Folder"))
        # highlight the new folder and set it to edit mode
        tree_view.edit(tree_view.model().index(os.path.join(root, "New Folder")))
        logger.info("Menu action -> new folder : done")
