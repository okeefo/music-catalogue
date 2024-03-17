import os
import sys


def get_base_dir() -> str:
    # Get the directory of the script or executable
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, 'frozen', False) else __file__))

    # If running in development mode, go up one level to the project directory
    if not getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(base_dir)

    return base_dir


def get_absolute_path_config() -> str:
    # Define the path to the config.ini file
    return os.path.join(get_base_dir(), 'config.ini')


def get_absolute_path_log_dir() -> str:
    # Define the path to the log directory
    return os.path.join(get_base_dir(), 'logs')
