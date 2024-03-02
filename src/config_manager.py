import os
import configparser
from log_config import get_logger

logger = get_logger(__name__)

class ConfigurationManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConfigurationManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def add_to_system_path(self, new_path:str):
        """ Add a new path to the system PATH. It assumes that the PATH is relative to the current working directory. """

        # Get the current PATH
        fq_path = os.path.join(os.getcwd(), new_path)
        logger.info(f"Adding {fq_path} to system PATH")      
        
        if fq_path not in os.environ["PATH"]:
            os.environ["PATH"] += os.pathsep + fq_path
            logger.info(f"{fq_path} added to system PATH successfully. New PATH is: {os.environ['PATH']}")
            
        else:
            logger.info(f"{fq_path} is already in the system PATH")