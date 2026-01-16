"""
Logging configuration for TaleTiles Audiobook Player.

Provides consistent logging across all modules with:
- Console output for development
- File logging for production
- Log rotation to prevent disk filling
"""

import logging
import logging.handlers
import sys
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: str | Path | None = None,
    console: bool = True
):
    """
    Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional path to log file
        console: Whether to output to console
    """
    # Get numeric level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)-8s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Suppress noisy libraries
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('mpv').setLevel(logging.WARNING)

    logging.info(f"Logging configured: level={level}, file={log_file}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)
