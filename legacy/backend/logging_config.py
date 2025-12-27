"""
Centralized Logging Configuration for LIZZY

Provides structured logging with rotation, levels, and consistent formatting.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


class LizzyLogger:
    """Centralized logger for LIZZY components."""

    _loggers = {}

    @classmethod
    def get_logger(cls, name: str, log_dir: Optional[Path] = None) -> logging.Logger:
        """
        Get or create a logger with consistent configuration.

        Args:
            name: Logger name (usually __name__ of the module)
            log_dir: Optional directory for log files (defaults to logs/)

        Returns:
            Configured logger instance
        """
        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(name)

        # Only configure if not already configured
        if not logger.handlers:
            logger.setLevel(logging.DEBUG)

            # Console handler - INFO and above
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

            # File handler with rotation - DEBUG and above
            if log_dir is None:
                from .config import config
                log_dir = config.root_dir / "logs"

            log_dir.mkdir(exist_ok=True)

            # Main log file
            log_file = log_dir / f"{name.replace('.', '_')}.log"
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

            # Prevent propagation to root logger
            logger.propagate = False

        cls._loggers[name] = logger
        return logger

    @classmethod
    def configure_root_logger(cls, level: int = logging.INFO) -> None:
        """
        Configure the root logger for the application.

        Args:
            level: Logging level for root logger
        """
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


# Convenience function for getting loggers
def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (use __name__ from calling module)

    Returns:
        Configured logger

    Example:
        from backend.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Started processing")
    """
    return LizzyLogger.get_logger(name)


# Log level helpers
def set_debug_mode(enable: bool = True) -> None:
    """Enable or disable debug mode for all loggers."""
    level = logging.DEBUG if enable else logging.INFO
    for logger in LizzyLogger._loggers.values():
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(level)
