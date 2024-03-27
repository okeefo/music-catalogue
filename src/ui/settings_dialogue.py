from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog
from src.log_config import get_logger
import configparser

logger = get_logger(__name__)


class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi("src\\qt\\settings.ui", self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.__display_settings()
        # self.ui.show())

    def closeEvent(self, event):
        logger.info("Settings dialog closed.")
        event.accept()

    def accept(self):
        logger.info("Settings dialog accepted.")
        self.close()

    def reject(self):
        logger.info("Settings dialog rejected.")
        self.close()

    def show(self):
        logger.info("Settings dialog shown.")
        self.ui.show()

    def hide(self):
        logger.info("Settings dialog hidden.")
        self.ui.hide()

    def __display_settings(self):
        # read the config file and display the settings
        config = configparser.RawConfigParser()
        if config.read('config.ini')[0] == '':
            logger.error("Config file not found.")
            return
        self._display_startup_settings(config)
        self._display_logging_settings(config)
        self._display_db_settings(config)
        self._display_discogs_settings(config)
        self._display_filetag_settings(config)

    def _display_startup_settings(self, config: configparser.RawConfigParser) -> None:
        # display the startup settings
        logger.info("Displaying startup settings.")
        self.ui.start_dir_source.setText(config.get('Directories', 'last_source_directory'))
        self.ui.start_dir_target.setText(config.get('Directories', 'last_target_directory'))

    def _display_logging_settings(self, config: configparser.RawConfigParser) -> None:
        logger.info("Displaying logging settings.")

        logdir = config.get('main_logger', 'log_dir')
        logger.info(f"setting: logdir: {logdir}")
        self.ui.log_dir.setText(logdir)

        clear_each_run = config.getboolean('main_logger', 'clear_log_each_run')
        logger.info(f"setting: clear_each_run: {clear_each_run}")
        self.ui.clear_each_run.setChecked(clear_each_run)

        max_log_size = self.__get_log_size_in_mb(config)
        logger.info(f"setting: max_log_size: {max_log_size}")
        self.ui.max_log_size.setValue(max_log_size)

        backup_count = int(config.get('main_logger', 'backup_count'))
        if not backup_count:
            logger.info(f"setting: backup_count, its not numeric: '{backup_count}'")
            backup_count = 5
        logger.info(f"setting: backup_count: {backup_count}")
        self.ui.backup_count.setValue(backup_count)

    def _display_db_settings(self, config: configparser.RawConfigParser) -> None:
        logger.info("Displaying database settings.")
        if 'db' in config.sections():

            if 'location' in config['db']:
                self.ui.db_location.setText(config.get('db', 'location'))

            if 'name' in config['db']:
                self.ui.db_name.setText(config.get('db', 'name'))

    def _display_discogs_settings(self, config: configparser.RawConfigParser) -> None:
        logger.info("Displaying Discogs settings.")
        self.ui.discogs_token.setText(config.get('discogs', 'token'))

    def _display_filetag_settings(self, config: configparser.RawConfigParser) -> None:
        logger.info("Displaying FileTag settings.")
        filename_mask = self._config_get(config, 'autotag', 'filename_mask')
        self.ui.file_mask.setText(config.get('autotag', 'filename_mask'))
    
    def __get_log_size_in_mb(self, config: configparser.RawConfigParser) -> int:
        max_log_size = config.get('main_logger', 'max_log_size')
        unit = max_log_size[-2:]
        value = max_log_size[:-2]

        if str(unit).upper() == 'KB':
            return int(value) // 1024
        elif str(unit).upper() == 'GB':
            return int(value) * 1024
        elif str(unit).upper() == 'MB':
            return int(value)
        else:
            return 10

    def _config_get(self, config: configparser.RawConfigParser, section: str, key: str) -> str:

        return (
            config[section][key]
            if section in config.sections() and key in config[section]
            else ""
        )
     
     

