"""
Merkezi Loglama Modülü — AI Model Stüdyosu
Konsola ve data_storage/app.log dosyasına seviyeli (INFO, WARNING, ERROR, DEBUG) log yazar.
"""
import os
import logging
from logging.handlers import RotatingFileHandler

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_DIR = os.path.join(_BASE_DIR, "data_storage")
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_FILE = os.path.join(_LOG_DIR, "app.log")

def setup_logger(name="AIStudio"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Dosya Handler (maks 5MB, 3 yedek dosya)
        file_handler = RotatingFileHandler(
            _LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_format = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

        # Konsol Handler
        console_handler = logging.StreamHandler()
        console_format = logging.Formatter(
            "[%(levelname)s] %(name)s: %(message)s"
        )
        console_handler.setFormatter(console_format)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    return logger

logger = setup_logger()
