from datetime import datetime
from pathlib import Path
from typing import Optional
import os

from wopr.config import get_config, WOPRConfig


class StorageError(Exception):
    """Raised when storage operations fail"""
    pass


def imagefilename(
    game_id: str,
    subject: str,
    sequence: Optional[int] = None,
    extension: Optional[str] = None,
    config: Optional[WOPRConfig] = None
) -> str:
    """
    Generate image filename with proper path structure.
    All settings come from config.yaml.
    
    Args:
        game_id: Unique game identifier
        subject: Subject type (must be in config.yaml image_subjects)
        sequence: Optional sequence number for ordering
        extension: File extension (default from config)
        config: Optional config override (uses global config if None)
    
    Returns:
        Full path to image file
    
    Raises:
        StorageError: If path is not accessible
        ValueError: If inputs are invalid
    
    Examples:
        >>> imagefilename("abc123", "capture")
        '/mnt/nas/twat/games/abc123/20251213-143022-capture.jpg'
        
        >>> imagefilename("abc123", "move", sequence=5)
        '/mnt/nas/twat/games/abc123/20251213-143022-move-005.jpg'
    """
    # Get config
    if config is None:
        config = get_config()
    
    # Validate inputs
    if not game_id or not game_id.strip():
        raise ValueError("game_id cannot be empty")
    if not subject or not subject.strip():
        raise ValueError("subject cannot be empty")
    
    # Validate subject is in allowed list
    if subject not in config.image_subjects:
        raise ValueError(
            f"Invalid subject '{subject}'. Must be one of: {config.image_subjects}"
        )
    
    # Get extension from config if not provided
    if extension is None:
        extension = config.storage.default_extension
    
    # Validate extension
    if extension not in config.storage.image_extensions:
        raise ValueError(
            f"Invalid extension '{extension}'. Must be one of: {config.storage.image_extensions}"
        )
    
    # Generate timestamp using format from config
    timestamp = datetime.now().strftime(config.filenames.timestamp_format)
    
    # Build filename using template from config
    if sequence is not None:
        filename = config.filenames.image_with_sequence_template.format(
            timestamp=timestamp,
            subject=subject,
            sequence=sequence,
            extension=extension,
            game_id=game_id
        )
    else:
        filename = config.filenames.image_template.format(
            timestamp=timestamp,
            subject=subject,
            extension=extension,
            game_id=game_id
        )
    
    # Build full path using config paths
    game_dir = config.storage.games_path / game_id
    filepath = game_dir / filename
    
    # Ensure directory exists if configured to do so
    if config.storage.ensure_directories:
        try:
            game_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create directory {game_dir}: {e}")
    else:
        if not game_dir.exists():
            raise StorageError(f"Directory does not exist: {game_dir}")
    
    # Verify path is writable
    if config.storage.ensure_directories and not os.access(game_dir, os.W_OK):
        raise StorageError(f"Directory not writable: {game_dir}")
    
    return str(filepath)


def thumbnailfilename(
    game_id: str,
    subject: str,
    config: Optional[WOPRConfig] = None
) -> str:
    """
    Generate thumbnail filename.
    
    Args:
        game_id: Unique game identifier
        subject: Subject type
        config: Optional config override
    
    Returns:
        Full path to thumbnail file
    """
    if config is None:
        config = get_config()
    
    timestamp = datetime.now().strftime(config.filenames.timestamp_format)
    
    filename = config.filenames.thumbnail_template.format(
        timestamp=timestamp,
        subject=subject,
        extension=config.storage.default_extension
    )
    
    game_dir = config.storage.games_path / game_id
    
    if config.storage.ensure_directories:
        game_dir.mkdir(parents=True, exist_ok=True)
    
    return str(game_dir / filename)


def ensure_path(path: str, config: Optional[WOPRConfig] = None) -> Path:
    """
    Ensure a path exists and is writable.
    
    Args:
        path: Path to validate/create
        config: Optional config override
    
    Returns:
        Path object
    
    Raises:
        StorageError: If path cannot be created or is not writable
    """
    if config is None:
        config = get_config()
    
    p = Path(path)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise StorageError(f"Failed to create path {path}: {e}")
    
    if not os.access(p, os.W_OK):
        raise StorageError(f"Path not writable: {path}")
    
    return p


def get_game_directory(game_id: str, config: Optional[WOPRConfig] = None) -> Path:
    """
    Get the directory path for a game.
    
    Args:
        game_id: Unique game identifier
        config: Optional config override
    
    Returns:
        Path to game directory
    """
    if config is None:
        config = get_config()
    
    return config.storage.games_path / game_id


def list_game_images(
    game_id: str,
    extension: Optional[str] = None,
    config: Optional[WOPRConfig] = None
) -> list[Path]:
    """
    List all images for a game, sorted by timestamp.
    
    Args:
        game_id: Unique game identifier
        extension: Filter by extension (default: all allowed extensions)
        config: Optional config override
    
    Returns:
        List of Path objects, sorted chronologically
    """
    if config is None:
        config = get_config()
    
    game_dir = get_game_directory(game_id, config)
    
    if not game_dir.exists():
        return []
    
    # Get files with allowed extensions
    if extension:
        extensions = [extension]
    else:
        extensions = config.storage.image_extensions
    
    images = []
    for ext in extensions:
        images.extend(game_dir.glob(f"*.{ext}"))
    
    # Sort by name (includes timestamp)
    return sorted(images)