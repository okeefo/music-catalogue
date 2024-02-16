import math
import os
from pathlib import Path
from PyQt5.QtWidgets import QMessageBox
from ui.custom_messagebox import ButtonType, show_message_box   


def count_files(start_dir):
    total_files = 0
    total_dirs = 0
    total_audio_files = 0
    total_size_audio_files = 0
    total_size_all_files = 0
    audio_extensions = {".mp3", ".wav", ".flac", ".aac"}

    for dirpath, dirnames, filenames in os.walk(start_dir):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_files += 1
            total_size_all_files += os.path.getsize(fp)
            if Path(fp).suffix in audio_extensions:
                total_audio_files += 1
                total_size_audio_files += os.path.getsize(fp)
        for _ in dirnames:
            total_dirs += 1

    return total_files, total_dirs, total_audio_files, total_size_audio_files, total_size_all_files


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"



def display_results(start_dir):
    total_files, total_dirs, total_audio_files, total_size_audio_files, total_size_all_files = count_files(start_dir)
    total_size_audio_files = convert_size(total_size_audio_files)
    total_size_all_files = convert_size(total_size_all_files)
    result = f"Total files: {total_files}\nTotal directories: {total_dirs}\nTotal audio files: {total_audio_files}\nTotal size of audio files: {total_size_audio_files}\nTotal size of all files: {total_size_all_files}"
    
    show_message_box(result, ButtonType.Ok, "File Count Results", "information")
    
