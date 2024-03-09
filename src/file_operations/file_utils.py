import shutil
import time
import send2trash
import os
from typing import List, Union
from ui.custom_messagebox import ButtonType, show_message_box, convert_response_to_string
from ui.progress_bar_helper import ProgressBarHelper
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
import qt.resources_rcc

import log_config

logger = log_config.get_logger(__name__)


def __move_files(file_list: List[str], source_dir: str, target_dir: str, progress_bar: ProgressBarHelper = None) -> None:
    """Move files between dirs"""

    userResponse = None
    files_to_delete = []
    root = False
    if not progress_bar:
        progress_bar = ProgressBarHelper(len(file_list), "Moving", 10)
        root = True

    for i, source_file in enumerate(file_list):

        source_file, fq_source_file, fq_target_file = __get_fully_qualified_file_name(source_file, source_dir, target_dir)

        progress_bar.update_progress_bar_text(f"Moving {source_file}...")
        if root:
            progress_bar.increment()

        logger.info(f'Moving "{fq_source_file}" to "{target_dir}"')

        if os.path.exists(fq_target_file):
            action, userResponse = _handle_move_of_existing_target_file(source_file, fq_source_file, target_dir, fq_target_file, userResponse, files_to_delete)
            if action == "cancel":
                return
            if action == "skip":
                continue

        shutil.move(fq_source_file, target_dir)

    if root:
        logger.info("Move files done, cleaning up any empty directories and source files")
        __clean_up(files_to_delete)
        logger.info("Clean up done")
        progress_bar.complete_progress_bar()


def _handle_move_of_existing_target_file(source_file: str, fq_source_file: str, target_dir: str, fq_target_file: str, userResponse, files_to_delete: List[str]) -> Union[str, int]:

    userResponse = __get_user_response_for_moving_an_existing_item(fq_source_file, source_file, target_dir, userResponse)

    action = ""
    if userResponse == QMessageBox.Cancel:
        logger.info("Move files cancelled by user")
        action = "cancel"

    elif userResponse in [QMessageBox.Yes, QMessageBox.YesToAll]:

        if os.path.isdir(fq_source_file):
            logger.info(f'Merging directory "{fq_source_file}" into "{fq_target_file}"')
            __move_files(os.listdir(fq_source_file), fq_source_file, fq_target_file)
            files_to_delete.append(fq_source_file)
            action = "skip"

        else:
            send2trash.send2trash(fq_target_file)

    elif userResponse in [QMessageBox.No, QMessageBox.NoToAll]:
        # skip the file
        logger.info(f"Skipping file: {source_file}")
        if userResponse == QMessageBox.No:
            userResponse = None
        action = "skip"

    return action, userResponse


def __get_fully_qualified_file_name(source_file, source_dir, target_dir) -> tuple[str, str, str]:
    """Get the fully qualified file names for the source and target files"""

    fq_source_file = os.path.normpath(os.path.join(source_dir, source_file))
    source_file = os.path.basename(fq_source_file)
    fq_target_file = os.path.normpath(os.path.join(target_dir, source_file))

    return source_file, fq_source_file, fq_target_file


def __get_user_response_for_moving_an_existing_item(fq_source_file, source_file, target_dir, userResponse) -> int:
    logger.info(f"File/Dir '{source_file}' already exists in target directory: {target_dir}")
    # ask user if they want to overwrite the file
    if userResponse is None or userResponse in [QMessageBox.Yes, QMessageBox.No]:
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
    progress = ProgressBarHelper(total_files, "Copying", 5)

    for copied_files, source_file in enumerate(file_list):

        progress.update_progress_bar_text(f"Copying {source_file}...")

        if __target_file_exists(source_file, target_dir):

            if userResponse is None:
                userResponse = show_message_box(f"The file:\n'{source_file}'\nalready exists in the target directory.\n\nDo you want to overwrite it?", ButtonType.YesNoToAllCancel, "Overwrite File?")
                logger.info(f"User chose: {convert_response_to_string(userResponse)}")

            if userResponse == QMessageBox.Cancel:
                logger.info("Copy files cancelled by user")
                return

            elif userResponse in [QMessageBox.No, QMessageBox.NoToAll]:
                logger.info(f"Skipping file: {source_file} ")
                if userResponse == QMessageBox.No:
                    userResponse = None
                continue

            elif userResponse == QMessageBox.Yes:
                userResponse = None

        __do_copy_file(source_file, target_dir, userResponse)

        progress.increment()

        if progress.user_has_cancelled():
            break

    progress.complete_progress_bar()


def __target_file_exists(source_file, target_dir) -> bool:
    """Check if the target file exists"""

    fq_source_file = os.path.normpath(source_file)
    source_file = os.path.basename(fq_source_file)
    fq_target_file = os.path.normpath(os.path.join(target_dir, source_file))

    return os.path.exists(fq_target_file)


def __do_copy_file(source_file, target_dir, userResponse):

    if os.path.isfile(source_file):
        logger.info(f'Copying file "{source_file}" to "{target_dir}"')
        shutil.copy2(source_file, target_dir)

    elif os.path.isdir(source_file):
        logger.info(f'Copying directory "{source_file}" to "{target_dir}"')
        shutil.copytree(source_file, os.path.join(target_dir, os.path.basename(source_file)))

    else:
        logger.error(f"Source path does not exist: {source_file}")


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
        for i, item in enumerate(file_path):
            send2trash.send2trash(item)
            logger.info(f"Deleted: {item} : {i} of {selected_files} files and {selected_dirs} directories")
        return f"Deleted: '{selected_files}' files and '{selected_dirs}' directories"
    else:
        msg = "Delete files cancelled by user"
        logger.info(msg)
        return msg
