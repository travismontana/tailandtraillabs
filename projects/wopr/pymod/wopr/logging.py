import logging
import sys
from pathlib import Path
from typing import Optional

from wopr.config import get_config, WOPRConfig


def setup_logging(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    config: Optional[WOPRConfig] = None
) -> logging.Logger:
    """
    Setup standardized logging for WOPR components.
    All settings come from config.yaml.
    
    Args:
        name: Logger name
        level: Log level override (uses config default if None)
        log_file: Optional file path for file logging
        config: Optional config override (uses global config if None)
    
    Returns:
        Configured logger instance
    
    Examples:
        >>> logger = setup_logging("wopr-camera")
        >>> logger.info("Camera initialized")
        
        >>> logger = setup_logging("wopr-api", log_file="/var/log/wopr-api.log")
    """
    # Get config
    if config is None:
        config = get_config()
    
    logger = logging.getLogger(name)
    
    # Use level from config if not provided
    if level is None:
        level = config.logging.default_level
    
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatter using config format
    formatter = logging.Formatter(
        fmt=config.logging.format,
        datefmt=config.logging.date_format
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
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