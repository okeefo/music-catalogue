import shutil
import time
import send2trash
import os
from typing import List
from ui.custom_messagebox import ButtonType, show_message_box, convert_response_to_string
from ui.custom_progress_dialog import ProgressDialog
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import qt.resources_rcc

import log_config
from PyQt5.QtWidgets import QApplication


logger = log_config.get_logger(__name__)


def __move_files(file_list: List[str], source_dir: str, target_dir: str) -> None:
    """Move files between dirs"""

    userResponse = None
    files_to_delete = []

    # loop over the file list and move the files
    for source_file in file_list:

        fq_source_file = os.path.normpath(os.path.join(source_dir, source_file))
        source_file = os.path.basename(fq_source_file)
        fq_target_file = os.path.normpath(os.path.join(target_dir, source_file))

        logger.info(f'Moving "{fq_source_file}" to "{target_dir}"')
        # Check if the file already exists in the target directory
        if os.path.exists(fq_target_file):

            userResponse = __get_user_response_for_moving_an_existing_item(fq_source_file, source_file, fq_target_file, target_dir, userResponse)

            if userResponse == QMessageBox.Cancel:
                logger.info("Move files cancelled by user")
                return

            elif userResponse in [QMessageBox.Yes, QMessageBox.YesToAll]:

                # if the source is a directory we need to merge the contents of the source directory into the target directory
                if os.path.isdir(fq_source_file):
                    logger.info(f'Merging directory "{fq_source_file}" into "{fq_target_file}"')
                    # create fully qualified file names for the contents of the fq_source_dir
                    __move_files(os.listdir(fq_source_file), fq_source_file, fq_target_file)

                    # add fq_source_file to teh list files to delete later
                    files_to_delete.append(fq_source_file)

                    if userResponse == QMessageBox.Yes:
                        userResponse = None

                    continue

                else:
                    if userResponse == QMessageBox.Yes:
                        userResponse = None

                    send2trash.send2trash(fq_target_file)

            elif userResponse in [QMessageBox.No, QMessageBox.NoToAll]:
                # skip the file
                logger.info(f"Skipping file: {source_file}")
                if userResponse == QMessageBox.No:
                    userResponse = None
                continue

        shutil.move(fq_source_file, target_dir)

    logger.info("Move files done, cleaning up any empty directories and source files")
    __clean_up(files_to_delete)


def __get_user_response_for_moving_an_existing_item(fq_source_file, source_file, fq_target_file, target_dir, userResponse) -> int:
    logger.info(f"File/Dir '{source_file}' already exists in target directory: {target_dir}")
    # ask user if they want to overwrite the file
    if userResponse is None:
        if os.path.isdir(fq_source_file):
            userResponse = show_message_box(
                f"The directory:\n'{source_file}'\nalready exists in the target directory.\n{target_dir}\nDo you want to merge the contents?", ButtonType.YesNoToAllCancel, "Merge Directory?"
            )
        else:
            userResponse = show_message_box(
                f"The file:\n'{source_file}'\nalready exists in the target directory.\n{target_dir}\nDo you want to overwrite it?", ButtonType.YesNoToAllCancel, "Overwrite File?"
            )

    logger.info(f"User chose: {convert_response_to_string(userResponse)}")

    return userResponse


def __clean_up(files_to_delete: List[str]) -> None:
    if not files_to_delete:
        logger.info("Nothing to delete")
        return

    for file in files_to_delete:
        if os.path.isdir(file):
            if os.listdir(file):
                logger.info(f"Skipping - directory is not empty: {file}")
                continue
            else:
                logger.info(f"Deleting directory: {file}")
        else:
            logger.info(f"Deleting file: {file}")

        send2trash.send2trash(file)
        logger.info(f"Deleted: {file}")


def ask_and_move_files(file_list: List[str], source_dir, target_dir: str) -> None:
    """prompt user adn ask before moving files between dirs"""

    file_list, source_dir, target_dir = __normalise_paths(file_list, source_dir, target_dir)

    if not file_list:
        logger.info("No files selected to move")
        return

    logger.info(f"Prompt user to move files from '{file_list}' in '{source_dir}' to '{target_dir}'")
    if len(file_list) > 1:
        message = f"Moving the selected files to:\n\n{target_dir}\n\nDo you want to continue?"
    else:
        message = f"Moving: \n\n {file_list[0]}\n to:\n{target_dir}\n\nDo you want to continue?"
    response = show_message_box(message, ButtonType.YesNoCancel, "Move Files", "warning")
    logger.info(f"User chose: {convert_response_to_string(response)}")
    __move_files(file_list, source_dir, target_dir) if response == QMessageBox.Yes else logger.info("Move files cancelled by user")


def __normalise_paths(file_list: List[str], source_dir: str, target_dir: str) -> tuple[List[str], str, str]:
    """Normalise the paths for the source and target dirs"""

    if source_dir:
        source_dir = os.path.normpath(source_dir)

    if target_dir:
        target_dir = os.path.normpath(target_dir)

    if file_list:
        file_list = [os.path.normpath(os.path.join(source_dir, file)) for file in file_list]

    return file_list, source_dir, target_dir


def __copy_files(file_list: dict[str], target_dir: str, userResponse: int = None) -> None:
    """Copy files/dirs form source to target"""

    total_files = len(file_list)
    copied_files = 0
    progress = __get_progress_bar(total_files)

    # loop over the file list and move the files
    for i, source_file in enumerate(file_list):

        # update progress
        progress.setLabelText(f"Copying {source_file}...")

        already_exists = False
        if os.path.isfile(source_file):
            already_exists = os.path.exists(os.path.join(target_dir, os.path.basename(source_file)))
        elif os.path.isdir(source_file):
            already_exists = os.path.exists(os.path.join(target_dir, os.path.basename(source_file)))

        if already_exists:

            if userResponse is None:
                userResponse = show_message_box(f"The file:\n'{source_file}'\nalready exists in the target directory.\n\nDo you want to overwrite it?", ButtonType.YesNoToAllCancel, "Overwrite File?")
                logger.info(f"User chose: {convert_response_to_string(userResponse)}")

            if userResponse == QMessageBox.Cancel:
                logger.info("Copy files cancelled by user")
                return

            elif userResponse in [QMessageBox.No, QMessageBox.NoToAll]:
                # skip the file
                logger.info(f"Skipping file: {source_file} ")
                if userResponse == QMessageBox.No:
                    userResponse = None
                continue

            elif userResponse == QMessageBox.Yes:
                userResponse = None

        if os.path.isfile(source_file):
            logger.info(f'Copying file "{source_file}" to "{target_dir}"')
            shutil.copy(source_file, target_dir)


        elif os.path.isdir(source_file):
            logger.info(f'Copying directory "{source_file}" to "{target_dir}"')
            shutil.copytree(source_file, os.path.join(target_dir, os.path.basename(source_file)))

        else:
            logger.error(f"Source path does not exist: {source_file}")

        copied_files += 1
        progress.setValue(copied_files)
        if progress.wasCanceled():
            break

    progress.setValue(total_files)
    progress.setLabelText("Copy complete. Click 'Cancel' to close this dialog.")
    while not progress.wasCanceled():
        QApplication.processEvents()
        time.sleep(0.1)  # sleep for a short time to reduce CPU usage



def __get_progress_bar(total_files: int) -> QProgressDialog:
    """Get a progress bar"""
    
    progress = QProgressDialog("Copying files...", "Cancel", 0, total_files)
    progress.setWindowIcon(QIcon(":/icons/icons/headphones.svg"))
    progress.setWindowTitle("Copying Files")
    progress.setLabelText("Copying Files...")
    progress.setCancelButtonText("Cancel")
    progress.setWindowModality(Qt.ApplicationModal)
    progress.setWindowFlags(progress.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    progress.setAutoClose(False)
    progress.setAutoReset(False)
    progress.show()
    return progress


def ask_and_copy_files(file_list: List[str], target_dir: str) -> None:
    """prompt user adn ask before copying files between dirs"""

    if not file_list:
        logger.info("No files selected to copy")
        return

    logger.info(f"Prompt user to copy files from '{file_list}' to '{target_dir}'")
    if len(file_list) > 2:
        message = f"Copying the selected files to:\n\n{target_dir}\n\nDo you want to continue?"
    else:
        message = f"Copying: \n\n {file_list} to:\n\n{target_dir}\n\nDo you want to continue?"
    response = show_message_box(message, ButtonType.YesNoCancel, "Copy Files", "warning")
    logger.info(f"User chose: {convert_response_to_string(response)}")
    __copy_files(file_list, target_dir) if response == QMessageBox.Yes else logger.info("Copy files cancelled by user")


def delete_files(file_path: List[str]) -> str:
    """Deletes a file/directory. Returns: None"""

    selected_files = 0
    selected_dirs = 0
    for item_ in file_path:
        if os.path.isdir(item_):
            selected_dirs += 1
        else:
            selected_files += 1

    if selected_files == 0 and selected_dirs == 0:
        logger.info("no files to delete - doing nothing...")
        return "No files selected to delete"

    logger.info("prompting user to delete files")

    message = f"Are you sure you want to delete {selected_files} files"
    message += f" and {selected_dirs} directories?" if selected_dirs > 0 else "?"
    message += f"\n\nNote: files will be moved to the recycle bin."

    response = show_message_box(message, ButtonType.YesNoCancel, "Are You Sure ?", "warning")

    logger.info(f"User chose: '{convert_response_to_string(response)}'")

    if response == QMessageBox.Yes:
        for item in file_path:
            send2trash.send2trash(item)
            logger.info(f"Deleted: {item} = '{selected_files}' files and '{selected_dirs}' directories")
        return f"Deleted: '{selected_files}' files and '{selected_dirs}' directories"
    else:
        msg = "Delete files cancelled by user"
        logger.info(msg)
        return msg
