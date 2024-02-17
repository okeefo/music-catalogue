import math
import os
from pathlib import Path
from PyQt5.QtWidgets import QMessageBox
from ui.custom_messagebox import ButtonType, show_message_box
from typing import List, Tuple


def __count_files(paths: List[str]) -> Tuple[int, int, int, int, int]:
    """Counts the number of files, directories, audio files and the total size of all files and audio files"""
    total_files = 0
    total_dirs = 0
    total_audio_files = 0
    total_size_audio_files = 0
    total_size_all_files = 0
    audio_extensions = {".mp3", ".wav", ".flac", ".aac"}
    processed_files = set()

    for path in paths:
        if os.path.isfile(path):
            if path not in processed_files:
                processed_files.add(path)
                total_files += 1
                total_size_all_files += os.path.getsize(path)
                if Path(path).suffix in audio_extensions:
                    total_audio_files += 1
                    total_size_audio_files += os.path.getsize(path)
        elif os.path.isdir(path):
            total_dirs += 1
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if fp not in processed_files:
                        processed_files.add(fp)
                        total_files += 1
                        total_size_all_files += os.path.getsize(fp)
                        if Path(fp).suffix in audio_extensions:
                            total_audio_files += 1
                            total_size_audio_files += os.path.getsize(fp)
                for _ in dirnames:
                    total_dirs += 1

    return total_files, total_dirs, total_audio_files, total_size_audio_files, total_size_all_files


def __convert_size(size_bytes: int) -> str:
    """Converts a file size in bytes to human readable format"""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def display_results(paths: List[str], include_root_dir: bool = False) -> None:
    total_files, total_dirs, total_audio_files, total_size_audio_files, total_size_all_files = __count_files(paths)
    if include_root_dir:
        total_dirs -= 1
    total_size_audio_files = __convert_size(total_size_audio_files)
    total_size_all_files = __convert_size(total_size_all_files)
    result = f"Total files: {total_files}\nTotal directories: {total_dirs}\nTotal audio files: {total_audio_files}\nTotal size of audio files: {total_size_audio_files}\nTotal size of all files: {total_size_all_files}"

    show_message_box(result, ButtonType.Ok, "File Count Results", "information")
