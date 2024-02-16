import logging
from logging.handlers import RotatingFileHandler
from path_helper import get_absolute_path_log_dir, get_absolute_path_config
import os
import sys
import codecs
import configparser
from logging import Logger

log_file_cleared = False


def __get_config():

    # Read the configuration options from config.ini
    config = configparser.ConfigParser()
    config.read(get_absolute_path_config())
    # Check if the config.ini file was successfully read
    if len(config.read("config.ini")) == 0:
        raise FileNotFoundError("The config.ini file could not be found or read.")

    # Check if the main_logger section exists, if not, create it with default settings
    if not config.has_section("main_logger"):
        __create_config_entry(config)

    # Convert max_log_size to bytes
    max_log_size = config.get("main_logger", "max_log_size").upper()
    if "K" in max_log_size:
        max_log_size = int(max_log_size.replace("K", "")) * 1024
    elif "MB" in max_log_size:
        max_log_size = int(max_log_size.replace("MB", "")) * 1024 * 1024
    elif "GB" in max_log_size:
        max_log_size = int(max_log_size.replace("GB", "")) * 1024 * 1024 * 1024
    else:
        max_log_size = int(max_log_size)  # Assume bytes if no unit is specified

    config.set("main_logger", "max_log_size", str(max_log_size))

    return config

def __create_config_entry(config):
    config.add_section("main_logger")
    config.set("main_logger", "log_dir", get_absolute_path_log_dir())
    config.set("main_logger", "clear_log_each_run", "False")
    config.set("main_logger", "max_log_size", "2MB")
    config.set("main_logger", "backup_count", "5")

    # Write the configuration to the config.ini file
    with open("config.ini", "w") as config_file:
        config.write(config_file)


def get_logger(name):

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        add_file_handlers(logger)

    return logger


file_handler = None
console_handler = None


def add_file_handlers(logger: Logger) -> RotatingFileHandler:
    global file_handler
    global console_handler

    # Remove all handlers from the logger
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    if file_handler is None:
        file_handler = __initialise_file_handler()

    if console_handler is None:
        console_handler = __initialise_console_handler()

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    

def __get_formatter() -> logging.Formatter:
    """Returns a formatter for the log file. Returns: logging.Formatter"""
    return logging.Formatter("%(asctime)s - [%(levelname)s] - [%(name)s:%(funcName)s] - %(message)s")


def __initialise_file_handler() -> logging.FileHandler:
    global file_handler
    global log_file_cleared

    config = __get_config()

    log_dir = config.get("main_logger", "log_dir")
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    clear_log_each_run = config.getboolean("main_logger", "clear_log_each_run")
    max_log_size = config.getint("main_logger", "max_log_size")
    backup_count = config.getint("main_logger", "backup_count")

    formatter = __get_formatter()

    # Create a file handler that logs to a file
    log_file = os.path.join(log_dir, "music-catalog.log")
    if clear_log_each_run and not log_file_cleared:
        file_handler = logging.FileHandler(log_file, "w", "utf-8")  # Overwrite the log file each run
        log_file_cleared = True
    else:
        file_handler = RotatingFileHandler(log_file, maxBytes=max_log_size, backupCount=backup_count, encoding="utf-8")

    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    return file_handler


def __initialise_console_handler() -> logging.StreamHandler:
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(__get_formatter())
    console_handler.setLevel(logging.INFO)
    console_handler.stream = codecs.open(sys.stdout.fileno(), "w", "utf-8")
    return console_handler