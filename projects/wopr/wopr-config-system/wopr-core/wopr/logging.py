import logging
import sys
from pathlib import Path
from typing import Optional

from wopr.config import get_str


def setup_logging(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup logging using central config.
    
    Args:
        name: Logger name
        level: Log level override (uses config if None)
        log_file: Optional log file path
    
    Returns:
        Configured logger
    
    Examples:
        >>> logger = setup_logging("wopr-camera")
        >>> logger.info("Camera initialized")
        
        >>> logger = setup_logging("wopr-api", log_file="/var/log/wopr-api.log")
    """
    logger = logging.getLogger(name)
    
    # Get level from config if not provided
    if level is None:
        level = get_str('logging.default_level')
    
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers.clear()
    
    # Get format from config
    log_format = get_str('logging.format')
    date_format = get_str('logging.date_format')
    
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance (assumes setup_logging was called).
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
