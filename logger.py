import logging
import sys
from pathlib import Path

# LOGGER
class Logger:
    @staticmethod
    def setup(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
        _format = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        _datefmt = "%Y-%m-%d %H:%M:%S"
        logger = logging.getLogger(name)
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        file_handler = logging.FileHandler(Path("derridai7.log"), mode="w")
        file_handler.setFormatter(logging.Formatter(_format, _datefmt))
        formatter = logging.Formatter(_format, _datefmt)
        handler.setFormatter(formatter)
        if not logger.hasHandlers():
            logger.addHandler(handler)
            logger.addHandler(file_handler)
        return logger