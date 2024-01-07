import os

from PyQt5.QtWidgets import QStyle, QApplication
from PyQt5.QtGui import QIcon

DIRECTORY = "directory"
FILE = "file"


class FileNode:
    def __init__(self, name, type, icon, extension=None):
        self.name = name
        self.type = type
        self.icon = icon
        self.extension = extension
        self.children = []

    def copy(self):
        copied_node = FileNode(self.name, self.type, self.icon, self.extension)
        copied_node.children = [child.copy() for child in self.children]
        return copied_node

    def add_child_node(self, node):
        self.children.append(node)
    
    def add_child_node(self, name, type, extension=None):
        self.children.append(FileNode(name, type, get_icon(type, extension), extension))

    def add_child_nodes(self, nodes):
        self.children.extend(nodes)

    def get_child_node(self, name):
        return next((child for child in self.children if child.name == name), None)

    def get_child_nodes(self, name):
        return [child for child in self.children if child.name == name] or None
    
    def get_child_nodes_by_type(self, type):
        return [child for child in self.children if child.type == type] or None
    
    def get_child_node_by_type(self, type):
        return next((child for child in self.children if child.type == type), None)
    
    def get_child_node_by_extension(self, extension):
        return next((child for child in self.children if child.extension == extension), None)
    
    def get_child_nodes_by_extension(self, extension):
        return [child for child in self.children if child.extension == extension] or None
    
    def get_child_nodes_by_extension_and_type(self, extension, type):
        return [child for child in self.children if child.extension == extension and child.type == type] or None
    
    def get_child_node_by_extension_and_type(self, extension, type):
        return next((child for child in self.children if child.extension == extension and child.type == type), None)
    
    
    def __repr__(self):
        return f"FileNode(name={self.name}, type={self.type}, extension={self.extension}, children={self.children})"


def create_tree(path, type):
    if type == FILE:
        extension = os.path.splitext(path)[1][1:].lower()
        icon = get_icon(type, extension)
        return FileNode(os.path.basename(path), type, icon, extension)
    else:
        icon = get_icon(type, None)
        return FileNode(os.path.basename(path), type, icon)


def get_dir_structure(path, update_statusbar):
    tree = create_tree(path, DIRECTORY)

    if os.path.isdir(path):
        for filename in os.listdir(path):
            child_path = os.path.join(path, filename)

            if os.path.isdir(child_path):
                update_statusbar(f"scanning dir: {child_path}")
                tree.children.append(get_dir_structure(child_path, update_statusbar))
            else:
                # Update the status bar with the file name
                update_statusbar(f"adding file: {child_path}")
                tree.children.append(create_tree(child_path, FILE))

    return tree


# Dictionary to store QIcons
icons = {}


def get_icon(type, extension):
    style = QApplication.style()

    if type == DIRECTORY:
        if "dir" not in icons:
            icons["dir"] = style.standardIcon(QStyle.SP_DirIcon)
        return icons["dir"]

    if extension in ["mp3", "wav", "jpg", "png"]:
        if extension not in icons:
            icons[extension] = QIcon(os.path.abspath(f"icons/mc-1-{extension}.ico"))
        return icons[extension]

    else:
        if "file" not in icons:
            icons["file"] = style.standardIcon(QStyle.SP_FileIcon)
        return icons["file"]
