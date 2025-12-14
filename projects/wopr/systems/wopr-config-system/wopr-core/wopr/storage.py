from datetime import datetime
from pathlib import Path
from typing import Optional
import os

from wopr.config import get_str, get_list, get_bool


class StorageError(Exception):
    """Raised when storage operations fail"""
    pass


def imagefilename(
    game_id: str,
    subject: str,
    sequence: Optional[int] = None,
    extension: Optional[str] = None
) -> str:
    """
    Generate image filename with proper path structure.
    All settings come from central config.
    
    Args:
        game_id: Unique game identifier
        subject: Subject type
        sequence: Optional sequence number
        extension: File extension (uses config default if None)
    
    Returns:
        Full path to image file
    
    Examples:
        >>> imagefilename("abc123", "capture")
        '/mnt/nas/twat/games/abc123/20251214-143022-capture.jpg'
        
        >>> imagefilename("abc123", "move", sequence=5)
        '/mnt/nas/twat/games/abc123/20251214-143022-move-005.jpg'
    """
    # Validate inputs
    if not game_id or not game_id.strip():
        raise ValueError("game_id cannot be empty")
    if not subject or not subject.strip():
        raise ValueError("subject cannot be empty")
    
    # Validate sequence type
    if sequence is not None and not isinstance(sequence, int):
        raise TypeError(f"sequence must be an integer, got {type(sequence).__name__}")
    
    # Get config values
    allowed_subjects = get_list('image_subjects')
    if subject not in allowed_subjects:
        raise ValueError(f"Invalid subject '{subject}'. Must be one of: {allowed_subjects}")
    
    # Get extension
    if extension is None:
        extension = get_str('storage.default_extension')
    
    allowed_extensions = get_list('storage.image_extensions')
    if extension not in allowed_extensions:
        raise ValueError(f"Invalid extension '{extension}'. Must be one of: {allowed_extensions}")
    
    # Generate timestamp
    timestamp_format = get_str('filenames.timestamp_format')
    timestamp = datetime.now().strftime(timestamp_format)
    
    # Build filename from template
    template_vars = {
        'timestamp': timestamp,
        'subject': subject,
        'game_id': game_id,
        'extension': extension
    }
    
    if sequence is not None:
        template_vars['sequence'] = sequence
        template = get_str('filenames.image_with_sequence_template')
    else:
        template = get_str('filenames.image_template')
    
    filename = template.format(**template_vars)
    
    # Build full path
    base_path = get_str('storage.base_path')
    games_subdir = get_str('storage.games_subdir')
    game_dir = Path(base_path) / games_subdir / game_id
    filepath = game_dir / filename
    
    # Ensure directory exists
    if get_bool('storage.ensure_directories'):
        try:
            game_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create directory {game_dir}: {e}")
    else:
        if not game_dir.exists():
            raise StorageError(f"Directory does not exist: {game_dir}")
    
    # Verify writable
    if get_bool('storage.ensure_directories') and not os.access(game_dir, os.W_OK):
        raise StorageError(f"Directory not writable: {game_dir}")
    
    return str(filepath)


def thumbnailfilename(game_id: str, subject: str) -> str:
    """
    Generate thumbnail filename.
    
    Args:
        game_id: Unique game identifier
        subject: Subject type
    
    Returns:
        Full path to thumbnail file
    """
    timestamp_format = get_str('filenames.timestamp_format')
    timestamp = datetime.now().strftime(timestamp_format)
    
    template = get_str('filenames.thumbnail_template')
    extension = get_str('storage.default_extension')
    
    filename = template.format(
        timestamp=timestamp,
        subject=subject,
        game_id=game_id,
        extension=extension
    )
    
    base_path = get_str('storage.base_path')
    games_subdir = get_str('storage.games_subdir')
    game_dir = Path(base_path) / games_subdir / game_id
    
    if get_bool('storage.ensure_directories'):
        game_dir.mkdir(parents=True, exist_ok=True)
    
    return str(game_dir / filename)


def ensure_path(path: str) -> Path:
    """
    Ensure a path exists and is writable.
    
    Args:
        path: Path to validate/create
    
    Returns:
        Path object
    
    Raises:
        StorageError: If path cannot be created or is not writable
    """
    p = Path(path)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise StorageError(f"Failed to create path {path}: {e}")
    
    if not os.access(p, os.W_OK):
        raise StorageError(f"Path not writable: {path}")
    
    return p


def get_game_directory(game_id: str) -> Path:
    """
    Get the directory path for a game.
    
    Args:
        game_id: Unique game identifier
    
    Returns:
        Path to game directory
    """
    base_path = get_str('storage.base_path')
    games_subdir = get_str('storage.games_subdir')
    return Path(base_path) / games_subdir / game_id


def list_game_images(game_id: str, extension: Optional[str] = None) -> list:
    """
    List all images for a game, sorted by timestamp.
    
    Args:
        game_id: Unique game identifier
        extension: Filter by extension (default: all allowed extensions)
    
    Returns:
        List of Path objects, sorted chronologically
    """
    game_dir = get_game_directory(game_id)
    
    if not game_dir.exists():
        return []
    
    # Get files with allowed extensions
    if extension:
        extensions = [extension]
    else:
        extensions = get_list('storage.image_extensions')
    
    images = []
    for ext in extensions:
        images.extend(game_dir.glob(f"*.{ext}"))
    
    # Sort by name (includes timestamp)
    return sorted(images)
