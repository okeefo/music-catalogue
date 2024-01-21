from datetime import datetime
from enum import Enum
import os
from PyQt5.QtWidgets import QApplication, QStyle
from PyQt5.QtGui import QIcon
import taglib


# The class below is FileType. It is an enum that represents the type of a file. It has two values: DIRECTORY and FILE.
class FsoType(Enum):
    """
    Represents the type of a file system object.

    Attributes:
        DIRECTORY (str): The type of a directory.
        FILE (str): The type of a file.
    """

    DIRECTORY = "directory"
    FILE = "file"


app = QApplication([])


fosIcons = {
    FsoType.DIRECTORY: QApplication.style().standardIcon(QStyle.SP_DirIcon),
    FsoType.FILE: QApplication.style().standardIcon(QStyle.SP_FileIcon),
    "mp3": QIcon(os.path.abspath("src/qt/icons/mc-1-mp3.ico")),
    "wav": QIcon(os.path.abspath("icons/mc-1-wav.ico")),
    "jpg": QIcon(os.path.abspath("icons/mc-1-jpg.ico")),
    "png": QIcon(os.path.abspath("icons/mc-1-png.ico")),
}

supported_audio_extensions = ["mp3", "wav"]


def is_supported_audio_file(extension):
    """
    Checks if the given file extension is supported as an audio file.

    Args:
        extension (str): The file extension to check.

    Returns:
        bool: True if the file extension is supported as an audio file, False otherwise.
    """

    return extension in supported_audio_extensions


def get_icon(file_type, extension=None):
    """
    Get the icon for a given file type or extension.

    Parameters:
    - file_type (str): The type of the file (e.g., "DIRECTORY", "FILE").
    - extension (str, optional): The file extension (e.g., ".txt", ".mp3").

    Returns:
    - str: The icon corresponding to the file type or extension.
    """
    if file_type == FsoType.DIRECTORY:
        return fosIcons[FsoType.DIRECTORY]
    if extension in supported_audio_extensions:
        return fosIcons[extension]
    else:
        return fosIcons[file_type]


#  Files can't have children only directories.


class FsoNode:
    def __init__(self, absolute_path, type_override=None, tags_override=None):
        self.__absolute_path = absolute_path
        self.__name = os.path.basename(absolute_path)
        self.__type = self._init_type(type_override)
        self.__extension = self._init_extension()
        self.__icon = self._init_icon()
        self.__children = []
        self.__parent = None
        self.__tags = self._init_tags(tags_override)
        self.__modified_date = self._init_modified_date()
        self.__file_size = self._init_file_size()

    def _init_modified_date(self):
        return (
            datetime.fromtimestamp(os.path.getmtime(self.__absolute_path)).strftime(
                "%D-%m-%Y %H:%M"
            )
            if (os.path.exists(self.__absolute_path))
            else "??"
        )

    def _init_file_size(self):
        return (
            os.path.getsize(self.__absolute_path)
            if (os.path.exists(self.__absolute_path) and self.__type == FsoType.FILE)
            else 0
        )

    def _init_tags(self, tags_override=None):
        if (
            self.__type == FsoType.DIRECTORY
            or self.__extension not in supported_audio_extensions
        ):
            return []
        elif tags_override is not None:
            return tags_override
        else:
            return taglib.File(self.__absolute_path).tags

    def _init_type(self, typeOverride=None):
        if typeOverride is not None:
            return typeOverride
        else:
            return (
                FsoType.DIRECTORY
                if os.path.isdir(self.__absolute_path)
                else FsoType.FILE
            )

    def _init_extension(self):
        if self.__type == FsoType.FILE:
            return os.path.splitext(self.__absolute_path)[1][1:]
        else:
            return None

    def _init_icon(self):
        if self.__type == FsoType.DIRECTORY:
            return get_icon(self.__type)
        else:
            return get_icon(self.__type, self.__extension)

    def copy(self):
        copied_node = FsoNode(self.__absolute_path, self.get_type(), self.__tags.copy())
        copied_node.__children = [child.copy() for child in self.__children]
        return copied_node

    def add_child_node(self, node):
        if self.__type == FsoType.FILE:
            raise ValueError("Files can't have children, only directories")

        node.parent = self
        self.__children.append(node)

    def add_child_nodes(self, nodes):
        # only valid if the current node is a directory
        if self.__type == FsoType.FILE:
            raise ValueError("Files can't have children, only directories")

        # add reference to the parent
        for node in nodes:
            self.add_child_node(node)

    def get_child_node(self, name):
        return next((child for child in self.__children if child.__name == name), None)

    def get_child_node_by_name(self, name):
        return self.get_child_node(name)

    def get_child_nodes(self, name):
        return [child for child in self.__children if child.__name == name] or None

    def get_child_nodes_by_type(self, file_type):
        return [child for child in self.__children if child.__type == file_type] or None

    def get_child_node_by_type(self, file_type):
        return next(
            (child for child in self.__children if child.__type == file_type), None
        )

    def get_child_node_by_extension(self, extension):
        return next(
            (child for child in self.__children if child.__extension == extension), None
        )

    def get_child_nodes_by_extension(self, extension):
        return [
            child for child in self.__children if child.__extension == extension
        ] or None

    def get_child_nodes_by_extension_and_type(self, extension, file_type):
        return [
            child
            for child in self.__children
            if child.__extension == extension and child.__type == file_type
        ] or None

    def get_child_node_by_extension_and_type(self, extension, file_type):
        return next(
            (
                child
                for child in self.__children
                if child.__extension == extension and child.__type == file_type
            ),
            None,
        )

    def __repr__(self):
        return f"FsoNode( {self.__name}, {self.__absolute_path} {self.__type}, {self.__extension}, {self.__icon}, {self.__tags}, {self.__parent}, {len(self.__children)} children)"

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self.__absolute_path == other.__absolute_path
                and self.__name == other.__name
                and self.__type == other.__type
                and self.__icon == other.__icon
                and self.__extension == other.__extension
                and self.__children == other.__children
                and self.__tags == other.__tags
                and self.__parent == other.__parent
            )
        return False

    def get_absolute_path(self) -> str:
        return self.__absolute_path

    def get_name(self) -> str:
        return self.__name

    def get_type(self) -> FsoType:
        return self.__type

    def get_icon(self) -> QIcon:
        return self.__icon

    def get_extension(self) -> str:
        return self.__extension

    def get_children(self) -> list:
        return self.__children

    def get_id3_tag(self, tag_name_requested):
        """
        Gets the value of the specified ID3 tag for the file.

        Args:
            tag_name_requested (str): The name of the ID3 tag to retrieve.

        Returns:
            str or None: The value of the requested ID3 tag, or None if the file is not a supported audio file or the tag does not exist.
        """
        if (
            self.__type != FsoType.FILE
            or self.__extension not in supported_audio_extensions
        ):
            return None

        return (
            self.__tags.get(tag_name_requested)[0]
            if (self.__tags.get(tag_name_requested))
            else None
        )

    def get_parent(self):
        return self.__parent

    def set_parent(self, parent):
        self.__parent = parent

    def get_modified_date(self):
        return self.__modified_date

    def get_file_size(self):
        return self.__file_size

    ##this function returns the file size as mega bytes.  Its formatted as a string for display purposes
    def get_file_size_mb(self):
        return (
            f"{round(self.__file_size / 1000000, 2)} MB"
            if (self.__type == FsoType.FILE)
            else None
        )

    def remove_child_node(self, child_node):
        if child_node in self.__children:
            self.__children.remove(child_node)
