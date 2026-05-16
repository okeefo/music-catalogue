import os

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QFileDialog

from config_manager import ConfigurationManager
from log_config import get_logger

logger = get_logger(__name__)

_UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "qt")


class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi(os.path.join(_UI_DIR, "settings.ui"), self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._connect_browse_buttons()
        self._load_settings()

    def _connect_browse_buttons(self) -> None:
        """Wire browse buttons to file pickers."""
        if btn := self.findChild(type(self.ui.pushButton), "pushButton"):
            btn.clicked.connect(lambda: self._browse_dir(self.ui.start_dir_source))
        if btn2 := self.findChild(type(self.ui.pushButton_2), "pushButton_2"):
            btn2.clicked.connect(lambda: self._browse_dir(self.ui.start_dir_target))
        if btn5 := self.findChild(type(self.ui.pushButton_5), "pushButton_5"):
            btn5.clicked.connect(lambda: self._browse_dir(self.ui.db_location))

    def _browse_dir(self, line_edit) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Directory", line_edit.text())
        if path:
            line_edit.setText(path)

    def _load_settings(self) -> None:
        """Populate all form fields from ConfigurationManager."""
        cfg = ConfigurationManager()
        self.ui.start_dir_source.setText(cfg.last_source_directory)
        self.ui.start_dir_target.setText(cfg.last_target_directory)
        self.ui.log_dir.setText(cfg.log_dir)
        self.ui.clear_each_run.setChecked(cfg.clear_log_each_run)
        self.ui.max_log_size.setValue(self._parse_mb(cfg.max_log_size))
        self.ui.backup_count.setValue(cfg.backup_count)
        self.ui.db_location.setText(cfg.db_location)
        self.ui.db_name.setText(cfg.db_name)
        self.ui.discogs_token.setText(cfg.discogs_token)
        self.ui.file_mask.setText(cfg.filename_mask)

    def _save_settings(self) -> None:
        """Read all form fields and persist to config.ini via ConfigurationManager."""
        cfg = ConfigurationManager()
        cfg.set("Directories", "last_source_directory", self.ui.start_dir_source.text())
        cfg.set("Directories", "last_target_directory", self.ui.start_dir_target.text())
        cfg.set("main_logger", "log_dir", self.ui.log_dir.text())
        cfg.set("main_logger", "clear_log_each_run", str(self.ui.clear_each_run.isChecked()))
        cfg.set("main_logger", "max_log_size", f"{self.ui.max_log_size.value()}MB")
        cfg.set("main_logger", "backup_count", str(self.ui.backup_count.value()))
        cfg.set("db", "location", self.ui.db_location.text())
        cfg.set("db", "name", self.ui.db_name.text())
        cfg.set("discogs", "token", self.ui.discogs_token.text())
        cfg.set("autotag", "filename_mask", self.ui.file_mask.text())
        cfg.save()
        logger.info("Settings saved.")

    def accept(self) -> None:
        self._save_settings()
        super().accept()

    def reject(self) -> None:
        logger.info("Settings dialog cancelled.")
        super().reject()

    @staticmethod
    def _parse_mb(value: str) -> int:
        unit = value[-2:].upper()
        num = value[:-2]
        try:
            if unit == "KB":
                return int(num) // 1024
            if unit == "GB":
                return int(num) * 1024
            if unit == "MB":
                return int(num)
        except (ValueError, IndexError):
            pass
        return 10
