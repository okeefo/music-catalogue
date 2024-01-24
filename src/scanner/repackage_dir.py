import os
import shutil
import filecmp


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

        if child.get_type() == "FILE": # FsoType.FILE
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
