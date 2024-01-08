import os

from PyQt5.QtWidgets import QStyle, QApplication
from PyQt5.QtGui import QIcon
from enum import Enum

from scanner.file_system_tree import FsoNode



def get_dir_structure(path, update_statusbar):
    """
    This function takes the path of a directory and a reference to the status bar.
    It scans the directory and returns a tree structure of the directory as a FsoNode object.
    The status bar is updated during the scanning process.
    """
    update_statusbar(f"Scanning directory: {path}")
    tree_structure = FsoNode(path)
    _scan_dir(path, tree_structure, update_statusbar)
    update_statusbar(f"Directory scanned: {path}")
    return tree_structure


def _scan_dir(path, parent_node, update_statusbar):
    """
    This function takes a path, a parent node, and a reference to the status bar.
    It scans the directory and adds the files and subdirectories to the parent node.
    The status bar is updated during the scanning process.
    """
    for fso in os.scandir(path):
        if fso.is_dir():
            # We have a directory, so let's add it to the parent node
            child_node = FsoNode(fso.path, parent_node)
            parent_node.add_child_node(child_node)
            _scan_dir(fso.path, child_node, update_statusbar)
            update_statusbar(f"Scanning directory: {fso.path}")
        else:
            # We have a file, so let's add it to the parent node
            parent_node.add_child_node(FsoNode(fso.path, parent_node))
            update_statusbar(f"Scanning file: {fso.path}")
