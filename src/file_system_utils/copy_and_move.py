import shutil
import send2trash
import os
from ui.custom_messagebox import ButtonType, show_message_box, convert_response_to_string
from PyQt5.QtWidgets import QMessageBox


import log_config
logger = log_config.get_logger(__name__)

def move_files(file_list:dict[str], target_dir:str) -> None:
    """ Move files between dirs """
    # loop over the file list and move the files
    for source_file in file_list:
        logger.info( f'Moving "{source_file}" to "{target_dir}"')
        shutil.move(source_file, target_dir)

def ask_and_move_files(file_list:str, target_dir:str) -> None:
    """ prompt user adn ask before moving files between dirs """
    logger.info( f"Prompt user to move files from '{file_list}' to '{target_dir}'")
    message = f"Moving the contents of:\n\n {target_dir}\n\n to:\n\n{file_list}\n\nDo you want to continue?"
    response = show_message_box(message, ButtonType.YesNoCancel, "Move Files", "warning")
    logger.info(f"User chose: {convert_response_to_string(response)}")
    
    
def delete_files(self, file_path: dict) -> str:
    """Deletes a file/directory. Returns: None"""
    selected_files = 0
    selected_dirs = 0
    for i in range(len(file_path)):
        if os.path.isdir(file_path[i]):
            selected_dirs += 1
        else:
            selected_files += 1
    
    if selected_files == 0 and selected_dirs == 0:
        logger.info("no files to delete - doing nothing...")
        self.update_status("No files selected to delete")
        return

    logger.info("prompting user to delete files")

    message = f"Are you sure you want to delete {selected_files} files"
    message += f" and {selected_dirs} directories?" if selected_dirs > 0 else "?"
    message += f"\n\nNote: files will be moved to the recycle bin."

    response = show_message_box(message, ButtonType.YesNoCancel,"Are You Sure ?", "warning")

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


