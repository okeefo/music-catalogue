import os

from PyQt5.QtWidgets import QStyle,QApplication
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
        if 'dir' not in icons:
            icons['dir'] = style.standardIcon(QStyle.SP_DirIcon)
        return icons['dir']
    
    if extension in ['mp3', 'wav', 'jpg', 'png']:
        if extension not in icons:
            icons[extension] = QIcon(os.path.abspath(f'icons/mc-1-{extension}.ico'))
        return icons[extension]
    
    else:
        if 'file' not in icons:
            icons['file'] = style.standardIcon(QStyle.SP_FileIcon)
        return icons['file']
