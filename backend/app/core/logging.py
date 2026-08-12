import logging
import sys

from ..config import settings


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("chatbot")
    if logger.handlers:
        return logger

    level = logging.DEBUG if settings.debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


logger = setup_logging()
