
import re

from typing import List


from log_config import get_logger
logger = get_logger("f_o.auto_tag")



def auto_tag_files(file_name_list: List[str], root_dir: str) -> None:
    """Auto tag files"""
    logger.info(f"Auto tagging {len(file_name_list)} files")
    release_ids = group_files_by_release_id(file_name_list)
    for release_id, files in release_ids.items():
        logger.info(f"Auto tagging {len(files)} files for release id '{release_id}'")
        # tag_files(files, release_id, root_dir)
    
    
def group_files_by_release_id(files: List[str]) -> dict:
    """ Group files by release id """
    
    logger.info(f"Grouping {len(files)} files by release id")
    
    release_id_pattern = re.compile(r'r(\d+)-\d+\.wav$')
    release_id_to_files = {}

    for file in files:
        if match := release_id_pattern.search(file):
            release_id = f'r{match[1]}'
            logger.info(f"Found release id '{release_id}' in file '{file}'")
            
            if release_id not in release_id_to_files:
                release_id_to_files[release_id] = []
            release_id_to_files[release_id].append(file)

    logger.info(f"Grouped {len(release_id_to_files)} release ids")
    #log the release ids
    logger.info(f"Release ids: {release_id_to_files.keys()}")
    return release_id_to_files