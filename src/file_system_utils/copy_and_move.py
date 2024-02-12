import shutil
from ui.custom_messagebox import ButtonType, show_message_box, convert_response_to_string

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
    
    
    
    

