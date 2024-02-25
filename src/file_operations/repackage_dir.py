import os
import shutil

from PyQt5.QtWidgets import QMessageBox
from ui.custom_messagebox import ButtonType, show_message_box, convert_response_to_string
from file_operations.audio_tags import AudioTagHelper
from log_config import get_logger
from typing import Tuple

logger = get_logger(__name__)
audio_tags = AudioTagHelper()


def ___ask_user_to_overwrite(file, label):
    """Ask user to overwrite file"""
    message = f"The file:\n'{file}'\nalready exists in the target directory\n'{label}'. \n\nDo you want to overwrite it?"
    return show_message_box(message, ButtonType.YesNoToAllCancel, "Overwrite File?")


def repackage_dir_by_label(source_dir: str, target_dir: str) -> None:
    """Repackages a directory by label"""
    logger.info(f"Repackaging '{source_dir}' to '{target_dir}'")
    repackage_files_by_label(os.listdir(source_dir), source_dir, target_dir)


def repackage_files_by_label(files: dict[str], source_dir: str, target_dir: str) -> None:

    user_choice = None
    for file in files:
        ##if file is a dir then skip
        if os.path.isdir(os.path.join(source_dir, file)):
            logger.info(f"Skipping - file is a directory: '{file}'")
            continue
        user_choice = repackage_file_by_label(file, source_dir, target_dir, user_choice)
        if user_choice == QMessageBox.Cancel:
            break

    logger.info("Repacking Done")


def repackage_file_by_label(file: str, source_dir: str, target_dir: str, user_choice: int = 0) -> int:
    """repackages a file by label
    Returns:
           int: The result of the dialog if the file exists. Can be one of the following QMessageBox constants:
                QMessageBox.Yes, QMessageBox.No, QMessageBox.YesToAll, QMessageBox.NoToAll, QMessageBox.Cancel
                else returns whatever user_choice was passed in
    """

    source_file = os.path.join(source_dir, file)
    source_file = os.path.normpath(source_file)

    # if file is a dir then skip

    if os.path.isdir(source_file):
        logger.info(f"Skipping - file is a directory: '{source_file}'")
        return user_choice

    # check is file is supported else skip
    if not audio_tags.isSupportedAudioFile(source_file):
        logger.warn(f"Skipping - file not supported: '{source_file}'")
        return user_choice

    # get tags if no tags skip
    tags = audio_tags.get_tags(source_file)
    if not tags:
        logger.warn(f"Skipping - no tags '{source_file}'")
        return user_choice

    # get label if no label return "unknown Publisher"
    label = tags.get("LABEL", ["Unknown Publisher"])[0]
    target_subdir = os.path.join(target_dir, label)

    # make dir if it doesn't exist.
    os.makedirs(target_subdir, exist_ok=True)

    # check if file exists in target dir and ask user to overwrite if needed
    target_file = os.path.join(target_subdir, file)

    if not os.path.exists(target_file):
        __repack(source_file, target_file)

    elif user_choice == QMessageBox.NoToAll:
        __log_skip(target_file, user_choice)

    elif user_choice == QMessageBox.YesToAll:
        __log_overwrite(target_file, user_choice)
        __repack(source_file, target_file)

    else:
        user_choice = ___ask_user_to_overwrite(file, label)

        if user_choice in [QMessageBox.Yes, QMessageBox.YesToAll]:
            __log_overwrite(target_file, user_choice)
            __repack(source_file, target_file)

        else:
            __log_skip(target_file, user_choice)

    return user_choice


def __log_skip(target_file: str, user_choice: int) -> None:
    logger.info(f"Skipping - target file already exists '{target_file}' - User choice: {convert_response_to_string(user_choice)}")


def __log_overwrite(target_file: str, user_choice: int) -> None:
    logger.info(f"Overwriting - target file already exists '{target_file}' - User choice: {convert_response_to_string(user_choice)}")


def __repack(source_file: str, target_file: str):
    """Moves the source file to the target file"""
    logger.info(f"Repackaging {source_file} to {target_file}")
    shutil.move(source_file, target_file)
    logger.info("Repackaging Done")
