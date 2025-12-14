import os
import requests
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when configuration is invalid or missing"""
    pass


class ConfigClient:
    """
    Client for WOPR Config Service.
    Fetches configuration from centralized HTTP service.
    """
    
    def __init__(self, service_url: Optional[str] = None, timeout: int = 5):
        """
        Initialize config client.
        
        Args:
            service_url: Config service URL (default from WOPR_CONFIG_SERVICE_URL env)
            timeout: Request timeout in seconds
        """
        if service_url is None:
            service_url = os.getenv(
                'WOPR_CONFIG_SERVICE_URL',
                'http://config-service:8080'
            )
        
        self.service_url = service_url.rstrip('/')
        self.timeout = timeout
        self._cache = {}
        self._cache_enabled = os.getenv('WOPR_CONFIG_CACHE', 'true').lower() == 'true'
    
    def get(self, key: str, default: Any = None, use_cache: bool = True) -> Any:
        """
        Get configuration value by dot-notation key.
        
        Args:
            key: Dot-notation key (e.g. 'storage.base_path')
            default: Default value if key not found
            use_cache: Use cached value if available
        
        Returns:
            Configuration value
        """
        # Check cache first
        if use_cache and self._cache_enabled and key in self._cache:
            return self._cache[key]
        
        try:
            response = requests.get(
                f"{self.service_url}/get/{key}",
                timeout=self.timeout
            )
            
            if response.status_code == 404:
                logger.warning(f"Config key not found: {key}, using default: {default}")
                return default
            
            response.raise_for_status()
            data = response.json()
            value = data['value']
            
            # Cache the value
            if self._cache_enabled:
                self._cache[key] = value
            
            return value
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch config key '{key}': {e}")
            if default is not None:
                logger.warning(f"Using default value for '{key}': {default}")
                return default
            raise ConfigError(f"Failed to fetch config key '{key}': {e}")
    
    def get_multiple(self, keys: list) -> dict:
        """
        Get multiple configuration values in one request.
        More efficient than multiple get() calls.
        
        Args:
            keys: List of dot-notation keys
        
        Returns:
            Dict mapping keys to values
        """
        try:
            response = requests.post(
                f"{self.service_url}/get",
                json={'keys': keys},
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            # Cache the values
            if self._cache_enabled:
                self._cache.update(data)
            
            return data
            
        except requests.RequestException as e:
            raise ConfigError(f"Failed to fetch multiple config keys: {e}")
    
    def get_section(self, section: str) -> dict:
        """
        Get entire configuration section.
        
        Args:
            section: Section name (e.g. 'storage', 'camera')
        
        Returns:
            Dict with section configuration
        """
        try:
            response = requests.get(
                f"{self.service_url}/section/{section}",
                timeout=self.timeout
            )
            
            if response.status_code == 404:
                raise ConfigError(f"Config section not found: {section}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            raise ConfigError(f"Failed to fetch config section '{section}': {e}")
    
    def get_str(self, key: str, default: Optional[str] = None) -> str:
        """Get string value"""
        value = self.get(key, default)
        if value is None:
            raise ConfigError(f"Required config key not found: {key}")
        return str(value)
    
    def get_int(self, key: str, default: Optional[int] = None) -> int:
        """Get integer value"""
        value = self.get(key, default)
        if value is None:
            raise ConfigError(f"Required config key not found: {key}")
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ConfigError(f"Config key '{key}' must be an integer, got: {value}")
    
    def get_float(self, key: str, default: Optional[float] = None) -> float:
        """Get float value"""
        value = self.get(key, default)
        if value is None:
            raise ConfigError(f"Required config key not found: {key}")
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ConfigError(f"Config key '{key}' must be a float, got: {value}")
    
    def get_bool(self, key: str, default: Optional[bool] = None) -> bool:
        """Get boolean value"""
        value = self.get(key, default)
        if value is None:
            raise ConfigError(f"Required config key not found: {key}")
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on')
        return bool(value)
    
    def get_list(self, key: str, default: Optional[list] = None) -> list:
        """Get list value"""
        value = self.get(key, default)
        if value is None:
            raise ConfigError(f"Required config key not found: {key}")
        if not isinstance(value, list):
            raise ConfigError(f"Config key '{key}' must be a list")
        return value
    
    def get_dict(self, key: str, default: Optional[dict] = None) -> dict:
        """Get dict value"""
        value = self.get(key, default)
        if value is None:
            raise ConfigError(f"Required config key not found: {key}")
        if not isinstance(value, dict):
            raise ConfigError(f"Config key '{key}' must be a dict")
        return value
    
    def clear_cache(self) -> None:
        """Clear local cache"""
        self._cache.clear()
    
    def reload(self) -> None:
        """Trigger config service to reload from file"""
        try:
            response = requests.post(
                f"{self.service_url}/reload",
                timeout=self.timeout
            )
            response.raise_for_status()
            self.clear_cache()
            logger.info("Config service reloaded successfully")
        except requests.RequestException as e:
            raise ConfigError(f"Failed to reload config service: {e}")


# Global client instance
_client: Optional[ConfigClient] = None


def init_config(service_url: Optional[str] = None, timeout: int = 5) -> None:
    """
    Initialize global config client.
    Call once at application startup.
    
    Args:
        service_url: Config service URL (default from env)
        timeout: Request timeout in seconds
    """
    global _client
    _client = ConfigClient(service_url, timeout)


def get_client() -> ConfigClient:
    """Get global config client instance"""
    global _client
    if _client is None:
        _client = ConfigClient()
    return _client


# Convenience functions (auto-initialize if needed)
def get_setting(key: str, default: Any = None) -> Any:
    """Get configuration value"""
    return get_client().get(key, default)


def get_str(key: str, default: Optional[str] = None) -> str:
    """Get string value"""
    return get_client().get_str(key, default)


def get_int(key: str, default: Optional[int] = None) -> int:
    """Get integer value"""
    return get_client().get_int(key, default)


def get_float(key: str, default: Optional[float] = None) -> float:
    """Get float value"""
    return get_client().get_float(key, default)


def get_bool(key: str, default: Optional[bool] = None) -> bool:
    """Get boolean value"""
    return get_client().get_bool(key, default)


def get_list(key: str, default: Optional[list] = None) -> list:
    """Get list value"""
    return get_client().get_list(key, default)


def get_dict(key: str, default: Optional[dict] = None) -> dict:
    """Get dict value"""
    return get_client().get_dict(key, default)


def get_section(section: str) -> dict:
    """Get entire config section"""
    return get_client().get_section(section)


def reload_config() -> None:
    """Reload config service"""
    get_client().reload()
