import os
import shutil
from scanner.file_system_tree import FsoNode, FsoType
import filecmp


def preview_repackage(
    tree_structure_source, tree_structure_target, update_statusbar
) -> FsoNode:
    # set up the status bar
    update_statusbar("Repackaging...")

    # This is a simple implementation that only looks for files at the root of source dir and creates child node on the
    # target but creates a dir node for the child. The name of the dir is the id3 tag publisher. If the publisher  tag
    # is empty, it will create a dir node with the name "Unknown Publisher".

    # create a new tree structure - don't amend the original
    new_tree = tree_structure_target.copy()

    # now lets loop through the source tree and look for files to move
    for child in tree_structure_source.get_children():
        if child.get_type() == FsoType.FILE:
            # we have a file, so lets see if we have a Label tag

            # step 1 - check if audio file has a Label id3 tag else set it to "Unknown Publisher"
            # step 2 - check if there is already a node with the same name as the Label tag if not create one
            # step 3 - add the file to the node
            # step 4 - remove the file from the root of the target tree is it exists

            # step 1
            label = child.get_id3_tag("LABEL") or "Unknown Publisher"

            # step 2
            publisher_node = new_tree.get_child_node_by_name(label)
            if publisher_node is None:
                publisher_node = FsoNode(label, FsoType.DIRECTORY)
                new_tree.add_child_node(publisher_node)

            # step 3 - add the file to the node only if it doesn't already exist
            if not publisher_node.get_child_node_by_name(child.get_name()):
                publisher_node.add_child_node(child)

            # step 4
            new_tree.remove_child_node(child)

    # update the status bar
    update_statusbar("Repackaging... Done")
    return new_tree


def repackage(
    tree_structure_source,
    target_directory,
    update_statusbar,
    update_status,
    copy_files=False,
):
    """
    Repackages the files from the source directory into the target directory based on the provided tree structure.

    Moves or copies the files from the source directory to the target directory based on the label ID3 tag.
    If the target file already exists and is different from the source file, it is removed before moving the file.
    If copy_files is True, the files are copied instead of moved.

    Args:
        tree_structure_source (FileSystemObject): The tree structure of the source directory.
        target_directory (str): The target directory to repackage the files into.
        update_statusbar (function): A function to update the status bar.
        copy_files (bool, optional): If True, the files are copied instead of moved. Defaults to False.

    Returns:
        None
    """

    # set up the status bar
    update_statusbar("Repackaging...")

    # loop through the source tree and look for files to move
    for child in tree_structure_source.get_children():
        update_statusbar(f"scanning...{child.get_name()}")
        update_status(f"scanning...{child.get_name()}")

        if child.get_type() == FsoType.FILE:
            # check if audio file has a Label id3 tag else set it to "Unknown Publisher"
            label = child.get_id3_tag("LABEL") or "Unknown Publisher"

            # create a directory with the same name as the Label tag if it doesn't exist
            publisher_directory = os.path.join(target_directory, label)
            os.makedirs(publisher_directory, exist_ok=True)

            # move or copy the file to the directory
            target_file = os.path.join(publisher_directory, child.get_name())
            if (
                copy_files
                and os.path.exists(target_file)
                or not copy_files
                and os.path.exists(target_file)
            ):
                update_status(f"File already exists: {child.get_name()}")
                update_statusbar(f"File already exists: {child.get_name()}")
            elif copy_files and not os.path.exists(target_file):
                update_status(f"Copying file: {child.get_name()}")
                update_statusbar(f"Copying file: {child.get_name()}")
                shutil.copy2(child.get_absolute_path(), target_file)
            else:
                update_status(f"Moving file: {child.get_name()}")
                update_statusbar(f"Moving file: {child.get_name()}")
                shutil.move(child.get_absolute_path(), target_file)
    # update the status bar
    update_status("Repackaging... Done")
    update_statusbar("Repackaging... Done")
