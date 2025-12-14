from wopr.config import get_config
from wopr.logging import setup_logging
from wopr.storage import imagefilename

# Load config once at startup
config = get_config()

# Setup logging from config
logger = setup_logging("wopr-camera", config=config)

def capture(game_id: str, subject: str, sequence: int = None):
    """Capture image - everything comes from config"""
    
    # Get resolution from config
    resolution = config.camera.get_resolution(config.camera.default_resolution)
    
    # Generate filepath from config
    filepath = imagefilename(
        game_id=game_id,
        subject=subject,
        sequence=sequence,
        config=config
    )
    
    logger.info(f"Capturing {resolution.width}x{resolution.height} to {filepath}")
    
    # All camera settings from config
    # ... picamera2 code using config.camera.* ...
    
    return filepath