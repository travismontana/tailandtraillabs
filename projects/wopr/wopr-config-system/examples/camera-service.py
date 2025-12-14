#!/usr/bin/env python3
"""
Example Camera Service using WOPR Config System
"""
import cv2
from wopr.config import init_config, get_str, get_int
from wopr.storage import imagefilename
from wopr.logging import setup_logging

# Initialize config client at startup
init_config()  # Uses WOPR_CONFIG_SERVICE_URL env var

# Setup logging from config
logger = setup_logging("wopr-camera")

def capture_image(game_id: str, subject: str, sequence: int = None):
    """
    Capture image using configuration from config service.
    
    Args:
        game_id: Game identifier
        subject: Subject type (capture, move, etc.)
        sequence: Optional sequence number
    
    Returns:
        Path to captured image
    """
    logger.info(f"Starting capture for game {game_id}, subject {subject}")
    
    # Get camera settings from config service
    resolution_name = get_str('camera.default_resolution')
    width = get_int(f'camera.resolutions.{resolution_name}.width')
    height = get_int(f'camera.resolutions.{resolution_name}.height')
    
    logger.info(f"Using resolution: {resolution_name} ({width}x{height})")
    
    # Generate filepath - automatically creates directories
    filepath = imagefilename(
        game_id=game_id,
        subject=subject,
        sequence=sequence
    )
    
    logger.info(f"Will save to: {filepath}")
    
    # Initialize camera
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    
    # Set MJPG format for higher resolutions
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
    
    # Set resolution from config
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    # Verify actual resolution
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    logger.info(f"Actual camera resolution: {actual_width}x{actual_height}")
    
    # Capture
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(filepath, frame)
        logger.info(f"Image captured successfully: {filepath}")
    else:
        logger.error("Failed to capture frame")
        raise Exception("Camera capture failed")
    
    cap.release()
    
    return filepath


if __name__ == '__main__':
    # Example usage
    try:
        filepath = capture_image(
            game_id="test_game_001",
            subject="capture",
            sequence=1
        )
        print(f"Captured: {filepath}")
    except Exception as e:
        logger.error(f"Capture failed: {e}")
        raise
