import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

logger = logging.getLogger("event_ticketing")
logger.setLevel(_LEVEL)

if not logger.handlers:
    formatter = logging.Formatter(_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        _LOG_DIR / "app.log", maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
