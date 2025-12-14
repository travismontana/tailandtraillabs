import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


class ConfigError(Exception):
    """Raised when configuration is invalid or missing"""
    pass


@dataclass
class StorageConfig:
    """Storage configuration"""
    base_path: str
    games_subdir: str
    image_extensions: list[str]
    default_extension: str
    thumbnail_size: tuple[int, int]
    ensure_directories: bool
    
    @property
    def games_path(self) -> Path:
        return Path(self.base_path) / self.games_subdir


@dataclass
class LoggingConfig:
    """Logging configuration"""
    default_level: str
    format: str
    date_format: str
    default_log_dir: str


@dataclass
class FilenameConfig:
    """Filename template configuration"""
    timestamp_format: str
    image_template: str
    image_with_sequence_template: str
    thumbnail_template: str


@dataclass
class CameraResolution:
    """Camera resolution settings"""
    width: int
    height: int
    
    def as_tuple(self) -> tuple[int, int]:
        return (self.width, self.height)


@dataclass
class CameraConfig:
    """Camera configuration"""
    default_resolution: str
    resolutions: Dict[str, CameraResolution]
    capture_delay_seconds: float
    default_format: str
    buffer_count: int
    
    def get_resolution(self, name: str) -> CameraResolution:
        if name not in self.resolutions:
            raise ConfigError(f"Unknown resolution: {name}")
        return self.resolutions[name]


@dataclass
class APIConfig:
    """API configuration"""
    host: str
    port: int
    camera_service_url: str
    camera_timeout_seconds: int
    ollama_url: str
    ollama_timeout_seconds: int


@dataclass
class VisionConfig:
    """Vision processing configuration"""
    default_model: str
    opencv_change_threshold: int
    min_change_area_pixels: int
    gaussian_blur_kernel: tuple[int, int]
    morphology_kernel: tuple[int, int]
    morphology_iterations: Dict[str, int]


@dataclass
class DatabaseConfig:
    """Database configuration"""
    connection_pool_size: int
    connection_timeout_seconds: int
    max_overflow: int


@dataclass
class GameType:
    """Game type definition"""
    id: str
    display_name: str


@dataclass
class WOPRConfig:
    """
    Complete WOPR configuration.
    Loaded from config.yaml with optional environment variable overrides.
    """
    storage: StorageConfig
    logging: LoggingConfig
    filenames: FilenameConfig
    camera: CameraConfig
    api: APIConfig
    vision: VisionConfig
    database: DatabaseConfig
    game_types: list[GameType]
    game_statuses: list[str]
    analysis_statuses: list[str]
    image_subjects: list[str]
    
    _config_path: str = field(default=None, repr=False)
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "WOPRConfig":
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to config.yaml. If None, searches:
                1. WOPR_CONFIG environment variable
                2. ./config.yaml
                3. /etc/wopr/config.yaml
                4. ~/.config/wopr/config.yaml
        
        Returns:
            WOPRConfig instance
        
        Raises:
            ConfigError: If config file not found or invalid
        """
        # Find config file
        if config_path is None:
            config_path = cls._find_config_file()
        
        if not Path(config_path).exists():
            raise ConfigError(f"Config file not found: {config_path}")
        
        # Load YAML
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in config file: {e}")
        
        # Apply environment variable overrides
        data = cls._apply_env_overrides(data)
        
        # Parse and validate
        try:
            return cls._from_dict(data, config_path)
        except (KeyError, TypeError, ValueError) as e:
            raise ConfigError(f"Invalid configuration: {e}")
    
    @classmethod
    def _find_config_file(cls) -> str:
        """Search for config file in standard locations"""
        search_paths = [
            os.getenv('WOPR_CONFIG'),
            './config.yaml',
            '/etc/wopr/config.yaml',
            str(Path.home() / '.config' / 'wopr' / 'config.yaml'),
        ]
        
        for path in search_paths:
            if path and Path(path).exists():
                return path
        
        raise ConfigError(
            "Config file not found. Searched:\n" + 
            "\n".join(f"  - {p}" for p in search_paths if p)
        )
    
    @classmethod
    def _apply_env_overrides(cls, data: dict) -> dict:
        """
        Apply environment variable overrides.
        
        Environment variables use format: WOPR_SECTION_KEY
        Example: WOPR_STORAGE_BASE_PATH=/custom/path
        """
        # Storage overrides
        if 'WOPR_STORAGE_BASE_PATH' in os.environ:
            data['storage']['base_path'] = os.environ['WOPR_STORAGE_BASE_PATH']
        
        # Logging overrides
        if 'WOPR_LOG_LEVEL' in os.environ:
            data['logging']['default_level'] = os.environ['WOPR_LOG_LEVEL']
        
        if 'WOPR_LOG_DIR' in os.environ:
            data['logging']['default_log_dir'] = os.environ['WOPR_LOG_DIR']
        
        # API overrides
        if 'WOPR_API_HOST' in os.environ:
            data['api']['host'] = os.environ['WOPR_API_HOST']
        
        if 'WOPR_API_PORT' in os.environ:
            data['api']['port'] = int(os.environ['WOPR_API_PORT'])
        
        if 'WOPR_CAMERA_URL' in os.environ:
            data['api']['camera_service_url'] = os.environ['WOPR_CAMERA_URL']
        
        if 'WOPR_OLLAMA_URL' in os.environ:
            data['api']['ollama_url'] = os.environ['WOPR_OLLAMA_URL']
        
        return data
    
    @classmethod
    def _from_dict(cls, data: dict, config_path: str) -> "WOPRConfig":
        """Parse configuration dictionary into typed objects"""
        
        # Parse storage config
        storage = StorageConfig(
            base_path=data['storage']['base_path'],
            games_subdir=data['storage']['games_subdir'],
            image_extensions=data['storage']['image_extensions'],
            default_extension=data['storage']['default_extension'],
            thumbnail_size=tuple(data['storage']['thumbnail_size']),
            ensure_directories=data['storage']['ensure_directories']
        )
        
        # Parse logging config
        logging_cfg = LoggingConfig(
            default_level=data['logging']['default_level'],
            format=data['logging']['format'],
            date_format=data['logging']['date_format'],
            default_log_dir=data['logging']['default_log_dir']
        )
        
        # Parse filename config
        filenames = FilenameConfig(
            timestamp_format=data['filenames']['timestamp_format'],
            image_template=data['filenames']['image_template'],
            image_with_sequence_template=data['filenames']['image_with_sequence_template'],
            thumbnail_template=data['filenames']['thumbnail_template']
        )
        
        # Parse camera config
        resolutions = {
            name: CameraResolution(**res_data)
            for name, res_data in data['camera']['resolutions'].items()
        }
        
        camera = CameraConfig(
            default_resolution=data['camera']['default_resolution'],
            resolutions=resolutions,
            capture_delay_seconds=data['camera']['capture_delay_seconds'],
            default_format=data['camera']['default_format'],
            buffer_count=data['camera']['buffer_count']
        )
        
        # Parse API config
        api = APIConfig(
            host=data['api']['host'],
            port=data['api']['port'],
            camera_service_url=data['api']['camera_service_url'],
            camera_timeout_seconds=data['api']['camera_timeout_seconds'],
            ollama_url=data['api']['ollama_url'],
            ollama_timeout_seconds=data['api']['ollama_timeout_seconds']
        )
        
        # Parse vision config
        vision = VisionConfig(
            default_model=data['vision']['default_model'],
            opencv_change_threshold=data['vision']['opencv_change_threshold'],
            min_change_area_pixels=data['vision']['min_change_area_pixels'],
            gaussian_blur_kernel=tuple(data['vision']['gaussian_blur_kernel']),
            morphology_kernel=tuple(data['vision']['morphology_kernel']),
            morphology_iterations=data['vision']['morphology_iterations']
        )
        
        # Parse database config
        database = DatabaseConfig(
            connection_pool_size=data['database']['connection_pool_size'],
            connection_timeout_seconds=data['database']['connection_timeout_seconds'],
            max_overflow=data['database']['max_overflow']
        )
        
        # Parse game types
        game_types = [
            GameType(**gt) for gt in data['game_types']
        ]
        
        return cls(
            storage=storage,
            logging=logging_cfg,
            filenames=filenames,
            camera=camera,
            api=api,
            vision=vision,
            database=database,
            game_types=game_types,
            game_statuses=data['game_statuses'],
            analysis_statuses=data['analysis_statuses'],
            image_subjects=data['image_subjects'],
            _config_path=config_path
        )
    
    def validate(self) -> list[str]:
        """
        Validate configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate storage paths
        base_path = Path(self.storage.base_path)
        if not base_path.exists() and not self.storage.ensure_directories:
            errors.append(f"Storage base path does not exist: {base_path}")
        
        # Validate camera resolution
        if self.camera.default_resolution not in self.camera.resolutions:
            errors.append(f"Invalid default resolution: {self.camera.default_resolution}")
        
        # Validate extensions
        if self.storage.default_extension not in self.storage.image_extensions:
            errors.append(f"Default extension not in allowed extensions")
        
        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.logging.default_level.upper() not in valid_levels:
            errors.append(f"Invalid log level: {self.logging.default_level}")
        
        return errors
    
    def get_game_type(self, game_type_id: str) -> Optional[GameType]:
        """Get game type by ID"""
        for gt in self.game_types:
            if gt.id == game_type_id:
                return gt
        return None


# Global config instance (loaded once)
_config: Optional[WOPRConfig] = None


def get_config() -> WOPRConfig:
    """
    Get global configuration instance.
    Loads config on first call, then returns cached instance.
    """
    global _config
    if _config is None:
        _config = WOPRConfig.load()
        errors = _config.validate()
        if errors:
            raise ConfigError("Configuration validation failed:\n" + "\n".join(errors))
    return _config


def reload_config(config_path: Optional[str] = None) -> WOPRConfig:
    """Reload configuration from file"""
    global _config
    _config = WOPRConfig.load(config_path)
    errors = _config.validate()
    if errors:
        raise ConfigError("Configuration validation failed:\n" + "\n".join(errors))
    return _config