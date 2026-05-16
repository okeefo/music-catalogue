import configparser
import os

from log_config import get_logger
from path_helper import get_absolute_path_config

logger = get_logger(__name__)


class ConfigurationManager:
    _instance = None

    def __new__(cls):
        if not isinstance(cls._instance, cls):
            cls._instance = super().__new__(cls)
            cls._instance._config = configparser.ConfigParser(interpolation=None)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        config_path = get_absolute_path_config()
        if not self._config.read(config_path):
            logger.warning(f"config.ini not found at {config_path}. Using defaults.")

    def reload(self) -> None:
        """Re-read config.ini from disk — call after external changes."""
        self._config = configparser.ConfigParser(interpolation=None)
        self._load()

    def save(self) -> None:
        """Write the current in-memory config back to config.ini."""
        config_path = get_absolute_path_config()
        with open(config_path, "w") as f:
            self._config.write(f)
        logger.info(f"Configuration saved to {config_path}")

    def get(self, section: str, key: str, fallback: str = "") -> str:
        return self._config.get(section, key, fallback=fallback)

    def set(self, section: str, key: str, value: str) -> None:
        if not self._config.has_section(section):
            self._config.add_section(section)
        self._config.set(section, key, value)

    # ── Directories ──────────────────────────────────────────────────────

    @property
    def last_source_directory(self) -> str:
        return self._config.get("Directories", "last_source_directory", fallback="")

    @property
    def last_target_directory(self) -> str:
        return self._config.get("Directories", "last_target_directory", fallback="")

    @property
    def last_left_directory(self) -> str:
        return self._config.get("Directories", "last_left_directory", fallback="")

    @property
    def last_right_directory(self) -> str:
        return self._config.get("Directories", "last_right_directory", fallback="")

    # ── Window ────────────────────────────────────────────────────────────

    @property
    def window_width(self) -> int:
        return self._config.getint("Window", "width", fallback=1200)

    @property
    def window_height(self) -> int:
        return self._config.getint("Window", "height", fallback=800)

    # ── Logging ───────────────────────────────────────────────────────────

    @property
    def log_dir(self) -> str:
        return self._config.get("main_logger", "log_dir", fallback="logs")

    @property
    def clear_log_each_run(self) -> bool:
        return self._config.getboolean("main_logger", "clear_log_each_run", fallback=False)

    @property
    def max_log_size(self) -> str:
        return self._config.get("main_logger", "max_log_size", fallback="10MB")

    @property
    def backup_count(self) -> int:
        return self._config.getint("main_logger", "backup_count", fallback=5)

    # ── Discogs ───────────────────────────────────────────────────────────

    @property
    def discogs_token(self) -> str:
        return self._config.get("discogs", "token", fallback="")

    # ── Autotag ───────────────────────────────────────────────────────────

    @property
    def filename_mask(self) -> str:
        return self._config.get("autotag", "filename_mask", fallback="")

    # ── Database ──────────────────────────────────────────────────────────

    @property
    def db_location(self) -> str:
        return self._config.get("db", "location", fallback="")

    @property
    def db_name(self) -> str:
        return self._config.get("db", "name", fallback="music_catalogue.db")

    @property
    def db_path(self) -> str:
        loc = self.db_location
        name = self.db_name
        if loc and name:
            return os.path.join(loc, name)
        return ""

    # ── System PATH ───────────────────────────────────────────────────────

    def add_to_system_path(self, new_path: str) -> None:
        fq_path = os.path.join(os.getcwd(), new_path)
        logger.info(f"Adding {fq_path} to system PATH")
        if fq_path not in os.environ["PATH"]:
            os.environ["PATH"] += os.pathsep + fq_path
            logger.info(f"{fq_path} added to system PATH successfully.")
        else:
            logger.info(f"{fq_path} is already in the system PATH")
