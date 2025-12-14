"""WOPR Core Library - Tactical Wargaming Adjudication Tracker"""

from wopr.config import (
    init_config,
    get_setting,
    get_str,
    get_int,
    get_float,
    get_bool,
    get_list,
    get_dict,
    get_section,
    reload_config,
    ConfigError
)
from wopr.storage import (
    imagefilename,
    thumbnailfilename,
    ensure_path,
    get_game_directory,
    list_game_images,
    StorageError
)
from wopr.logging import setup_logging, get_logger

__version__ = "0.1.0"
__all__ = [
    # Config
    'init_config',
    'get_setting',
    'get_str',
    'get_int',
    'get_float',
    'get_bool',
    'get_list',
    'get_dict',
    'get_section',
    'reload_config',
    'ConfigError',
    # Storage
    'imagefilename',
    'thumbnailfilename',
    'ensure_path',
    'get_game_directory',
    'list_game_images',
    'StorageError',
    # Logging
    'setup_logging',
    'get_logger',
]
