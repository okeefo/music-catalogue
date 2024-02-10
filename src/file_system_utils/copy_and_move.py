import os
import shutil
import log_config

logger = log_config.get_logger(__name__)

def move_files(file_list:dict[str], source_dir:str, target_dir:str) -> None:
    # loop over the file list and move the files
    for source_file in file_list:
        logger.info( f"Moving {source_file} to {target_dir}")
        shutil.move(source_file, target_dir)

    
