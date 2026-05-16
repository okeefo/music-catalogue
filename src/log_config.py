import configparser
import logging
import os
import sys
from logging import Logger
from logging.handlers import RotatingFileHandler

from path_helper import get_absolute_path_config, get_absolute_path_log_dir

log_file_cleared = False
file_handler = None
console_handler = None

# Defaults mirror ConfigurationManager's [main_logger] fallbacks.
_DEFAULT_LOG_DIR = get_absolute_path_log_dir()
_DEFAULT_CLEAR_EACH_RUN = False
_DEFAULT_MAX_LOG_SIZE = "10MB"
_DEFAULT_BACKUP_COUNT = 5


def _parse_size_to_bytes(size_str: str) -> int:
    s = size_str.upper().strip()
    if s.endswith("GB"):
        return int(s[:-2]) * 1024 * 1024 * 1024
    if s.endswith("MB"):
        return int(s[:-2]) * 1024 * 1024
    if s.endswith("K") or s.endswith("KB"):
        return int(s.rstrip("B").rstrip("K")) * 1024
    return int(s)


def _read_config():
    # Use interpolation=None to match ConfigurationManager — prevents
    # configparser choking on values that contain '%' (e.g. filename masks).
    config = configparser.ConfigParser(interpolation=None)
    config.read(get_absolute_path_config())
    return config


def get_logger(name) -> Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        add_file_handlers(logger)
    return logger


def add_file_handlers(logger: Logger) -> None:
    global file_handler, console_handler

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    if file_handler is None:
        file_handler = _initialise_file_handler()

    if console_handler is None:
        console_handler = _initialise_console_handler()

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def _get_formatter() -> logging.Formatter:
    return logging.Formatter("%(asctime)s - [%(levelname)s] - [%(name)s:%(funcName)s] - %(message)s")


def _initialise_file_handler() -> logging.FileHandler:
    global log_file_cleared

    config = _read_config()

    log_dir = config.get("main_logger", "log_dir", fallback=_DEFAULT_LOG_DIR)
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    clear_log_each_run = config.getboolean("main_logger", "clear_log_each_run", fallback=_DEFAULT_CLEAR_EACH_RUN)
    max_log_size = _parse_size_to_bytes(config.get("main_logger", "max_log_size", fallback=_DEFAULT_MAX_LOG_SIZE))
    backup_count = config.getint("main_logger", "backup_count", fallback=_DEFAULT_BACKUP_COUNT)

    log_file = os.path.join(log_dir, "music-catalog.log")
    if clear_log_each_run and not log_file_cleared:
        handler = logging.FileHandler(log_file, "w", "utf-8")
        log_file_cleared = True
    else:
        handler = RotatingFileHandler(log_file, maxBytes=max_log_size, backupCount=backup_count, encoding="utf-8")

    handler.setFormatter(_get_formatter())
    handler.setLevel(logging.INFO)
    return handler


def _initialise_console_handler() -> logging.StreamHandler:
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(_get_formatter())
    handler.setLevel(logging.INFO)
    return handler
