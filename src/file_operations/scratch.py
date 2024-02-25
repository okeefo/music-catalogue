import re, os, sys, configparser, discogs_client, requests

from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from file_operations.audio_tags import AudioTagHelper
from audio_tags import AudioTagHelper
from log_config import get_logger

logger = get_logger("f_o.scratch")


def display(file_list, destination_dir):

    audio_tags = AudioTagHelper()

    for file_name in file_list:
        full_path = os.path.join(destination_dir, file_name)
        # audio_tags.get_tags(full_path)

        audio_tags.log_tag_key_values(full_path)
        logger.info("")
        logger.info("-------------------------------------------")
        logger.info("")
    # audio_tags.log_tags(full_path)

    # logger.info(f"tags: {tags}")


if __name__ == "__main__":
    # Add the root directory of your project to the Python path

    file_list = ["a8_jam and spoon-r21478021-01.wav", "a8_jam and spoon-r21478021-02.wav"]
    # file_list = ["a8_jam and spoon-r21478021-02.wav"]
    # file_list = ["MiTM - NASTY'ER EP - A1-r15174933-01.wav", "MiTM - NASTY'ER EP - A2-r15174933-02.wav"]

    #   file_list = ["TheRave--A1--r28675504-01.wav"]

    display(file_list, os.path.normpath("E:\\tmp_cop_A"))
