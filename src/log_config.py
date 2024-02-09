import logging

logging.basicConfig(format="%(asctime)s - %(name)s - %(funcName)s - %(levelname)s -  %(message)s", level=logging.INFO)

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger