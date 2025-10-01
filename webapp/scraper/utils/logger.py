from loguru import logger
import sys
from pathlib import Path
from config import settings


def setup_scraper_logger():
    """
    Configure loguru logger for scraper module.

    Sets up console and file logging with appropriate formats and levels.
    """
    # Remove default logger
    logger.remove()

    # Console logging
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO" if settings.is_production else "DEBUG",
        colorize=True,
    )

    # File logging (if in production)
    if settings.is_production:
        log_dir = Path(__file__).parent.parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)

        logger.add(
            log_dir / "scraper_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="INFO",
            rotation="1 day",
            retention="30 days",
            compression="zip",
        )

    return logger


# Initialize logger on import
scraper_logger = setup_scraper_logger()
