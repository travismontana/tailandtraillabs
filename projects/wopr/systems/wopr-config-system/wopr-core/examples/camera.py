from wopr.config import init_config, get_str, get_int
from wopr.storage import imagefilename
from wopr.logging import setup_logging

# Initialize config client at startup
init_config()  # Uses WOPR_CONFIG_SERVICE_URL env var

logger = setup_logging("wopr-camera")

def capture(game_id: str, subject: str):
    # Fetch config from service
    resolution_name = get_str('camera.default_resolution')
    width = get_int(f'camera.resolutions.{resolution_name}.width')
    height = get_int(f'camera.resolutions.{resolution_name}.height')
    
    logger.info(f"Config fetched: {resolution_name} = {width}x{height}")
    
    # Generate filepath (also calls config service internally)
    filepath = imagefilename(game_id, subject)
    
    # ... capture code ...
    
    return filepath