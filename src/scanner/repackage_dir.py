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
           
            # step 1 - check if audio file has a Label id3 tag else set it to "Unknown Publisher"
            # step 2 - check if there is already a node with the same name as the Label tag if not create one
            # step 3 - add the file to the node
            # step 4 - remove the file from the root of the target tree

            # step 1
            label = child.get_id3_tag("LABEL") or "Unknown Publisher"
            
            # step 2
            publisher_node = new_tree.get_child_node_by_name(label)
            if publisher_node is None:
                publisher_node = FsoNode(label,FsoType.DIRECTORY) 
                new_tree.add_child_node(publisher_node)

            # step 3
            publisher_node.add_child_node(child)   

            # step 4
            new_tree.remove_child_node(child)

    # update the status bar           
    update_statusbar("Repackaging... Done")
    return new_tree
