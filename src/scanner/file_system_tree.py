from enum import Enum
import os
from PyQt5.QtWidgets import QApplication, QStyle
from PyQt5.QtGui import QIcon
from tinytag import TinyTag

# The class below is FileType. It is an enum that represents the type of a file. It has two values: DIRECTORY and FILE.
class FsoType(Enum):
    DIRECTORY = "directory"
    FILE = "file"

app = QApplication([])


fosIcons = {
    FsoType.DIRECTORY: QApplication.style().standardIcon(QStyle.SP_DirIcon),
    FsoType.FILE: QApplication.style().standardIcon(QStyle.SP_FileIcon),
    "mp3": QIcon(os.path.abspath("icons/mc-1-mp3.ico")),
    "wav": QIcon(os.path.abspath("icons/mc-1-wav.ico")),
    "jpg": QIcon(os.path.abspath("icons/mc-1-jpg.ico")),
    "png": QIcon(os.path.abspath("icons/mc-1-png.ico"))
}

supported_audio_extensions = ["mp3", "wav"]

def get_icon(file_type, extension=None):
    if file_type == FsoType.DIRECTORY:
        return fosIcons[file_type]
    else:
        return fosIcons[extension]


class FsoNode:
    
    def __init__(self, absolute_path, parent=None):
        self.absolute_path = absolute_path
        self.name = os.path.basename(absolute_path)
        self.type = self._init_type()
        self.extension = self._init_extension()
        self.icon = self._init_icon()
        self.children = []
        self.parent = parent
    
    def _init_type(self):
        return FsoType.DIRECTORY if os.path.isdir(self.absolute_path) else FsoType.FILE
    
    def _init_extension(self):
        if self.type == FsoType.FILE:
            return os.path.splitext(self.absolute_path)[1][1:]
        else:
            return None
    
    def _init_icon(self):
        if self.type == FsoType.DIRECTORY:
            return get_icon(self.type)
        else:
            return get_icon(self.type, self.extension)
    
    def copy(self):
        copied_node = FsoNode(self.absolute_path)
        copied_node.children = [child.copy() for child in self.children]
        return copied_node

    def add_child_node(self, name, file_type=None, extension=None):
        if file_type is None:
            self.children.append(name)  # Assuming 'name' is a FsoNode object
        else:
            self.children.append(FsoNode(name, file_type, get_icon(file_type, extension), extension))

    def add_child_nodes(self, nodes):
        self.children.extend(nodes)

    def get_child_node(self, name):
        return next((child for child in self.children if child.name == name), None)

    def get_child_nodes(self, name):
        return [child for child in self.children if child.name == name] or None

    def get_child_nodes_by_type(self, file_type):
        return [child for child in self.children if child.type == file_type] or None

    def get_child_node_by_type(self, file_type):
        return next((child for child in self.children if child.type == file_type), None)

    def get_child_node_by_extension(self, extension):
        return next((child for child in self.children if child.extension == extension), None)

    def get_child_nodes_by_extension(self, extension):
        return [child for child in self.children if child.extension == extension] or None

    def get_child_nodes_by_extension_and_type(self, extension, file_type):
        return [child for child in self.children if child.extension == extension and child.type == file_type] or None

    def get_child_node_by_extension_and_type(self, extension, file_type):
        return next((child for child in self.children if child.extension == extension and child.type == file_type),
                    None)

    def __repr__(self):
        return f"FsoNode({self.name}, {self.type}, {self.icon}, {self.absolute_path}, {self.extension}, {self.children})"

    def __eq__(self, other):
            if isinstance(other, self.__class__):
                return (
                    self.absolute_path == other.absolute_path and
                    self.name == other.name and
                    self.type == other.type and
                    self.icon == other.icon and
                    self.extension == other.extension and
                    self.children == other.children
                )
            return False
    

    def get_children(self): 
        if self.type == FsoType.DIRECTORY:
            return os.listdir(self.absolute_path)
        else:
            return None
        
    def get_parent(self):
        if self.type == FsoType.DIRECTORY:
            return os.path.dirname(self.absolute_path)
        else:
            return None
    
    def get_absolute_path(self):
        return self.absolute_path  
    
    def get_name(self):
        return self.name
    
    def get_type(self):
        return self.type
    
    def get_icon(self):
        return self.icon
    
    def get_extension(self):
        return self.extension
       
    def get_children(self):
        return self.children 
    
    def get_parent(self):
        return self.parent

    def get_id3_tag(self, tag):
        """
        This function returns the requested ID3 tag if the file is a supported audio file.
        It checks if the file extension is in the list of supported audio extensions.
        If the file is not a supported audio file, it returns None.
        """
        if self.type != FsoType.FILE:
            return None
        if self.extension in supported_audio_extensions:
            tags = TinyTag.get(self.absolute_path)
            return getattr(tags, tag) 

