from tinytag import TinyTag
from scanner import scanner_dir


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
        if child.type == scanner_dir.FileType.FILE:
            # we have a file, so lets see if we have a publisher
            if publisher := get_publisher(child.name):
                new_tree.add_child_node(publisher, scanner_dir.FileType.DIRECTORY)
            else:
                # we don't have a publisher, so let's create a new child node in the target tree called "Unknown Publisher"
                new_tree.add_child_node("Unknown Publisher", scanner_dir.FileType.DIRECTORY)

    update_statusbar("Repackaging... Done")
    return new_tree


def get_publisher(file_path):
    tag = TinyTag.get(file_path)
    return tag.publisher
