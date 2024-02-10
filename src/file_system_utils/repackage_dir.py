import os
import shutil

from PyQt5.QtWidgets import QDialog, QMessageBox
from ui.custom_dialog import CustomDialog
from log_config import get_logger

logger = get_logger(__name__)

def handle_user_choice(file, label):
    message = f"The file:\n'{file}'\nalready exists in the target directory\n'{label}'. \n\nDo you want to overwrite it?"
    dialog = CustomDialog(message)
    return dialog.show_dialog()

def repackage_by_label(source_dir, target_dir, audio_tags):
    logger.info(f"Repackaging {source_dir} to {target_dir}")
    remember_choice = None
    user_choice = None
    for file in os.listdir(source_dir):
        source_file = os.path.join(source_dir, file)
        if not audio_tags.isSupported(source_file):
            logger.warn(f"Skipping - file not supported: {source_file}")
            continue

        tags = audio_tags.get_tags(source_file)
        if not tags:
            logger.warn(f"Skipping - no tags{source_file}")
            continue

        label = tags.get("LABEL", ["Unknown Publisher"])[0]
        target_subdir = os.path.join(target_dir, label)
        os.makedirs(target_subdir, exist_ok=True)

        target_file = os.path.join(target_subdir, file)
        if os.path.exists(target_file) and not (remember_choice and user_choice == QMessageBox.Yes):
            if not remember_choice:
                user_choice, remember_choice = handle_user_choice(file, label)
            if user_choice == QDialog.Rejected:
                break
            if user_choice != QMessageBox.Yes:
                continue

        shutil.move(source_file, target_file)

    logger.info("Repacking Done")
