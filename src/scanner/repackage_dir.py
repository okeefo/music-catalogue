import os
from tinytag import TinyTag
from scanner import scanner_dir
from scanner.file_system_tree import FsoNode, FsoType


def preview_repackage(tree_structure_source, tree_structure_target, update_statusbar):
    # set up the status bar
    update_statusbar("Repackaging...")

    # This is a simple implementation that only looks for files at the root of source dir and creates child node on the 
    # target but creates a dir node for the child. The name of the dir is the id3 tag publisher. If the publisher  tag
    # is empty, it will create a dir node with the name "Unknown Publisher".

    # create a new tree structure - don't amend the original
    new_tree = tree_structure_target.copy()

    # now lets loop through the source tree and look for files to move
    for child in tree_structure_source.children:
        if child.type == FsoType.FILE:
            # we have a file, so lets see if we have a Label tag
            if label := child.get_id3_tag("LABEL"):
                
                path = child.absolute_path
                file_name = os.path.basename(path)  
                new_dir = path.replace(file_name, label)
                new_path = os.path.join(new_dir, file_name)
                node = FsoNode(new_dir, FsoType.DIRECTORY)
                node.add_child_node(FsoNode(new_path, FsoType.FILE))
                new_tree.add_child_node(node)
            else:
                # we don't have a publisher, so let's create a new child node in the target tree called "Unknown Publisher"
                new_tree.add_child_node("Unknown Publisher", FsoType.DIRECTORY)

    update_statusbar("Repackaging... Done")
    return new_tree
