#!/usr/bin/env python3

import cv2
import time
import random
import string
from datetime import datetime

from wopr.config import get_config
from wopr.logging import setup_logging
from wopr.storage import imagefilename

config = get_config()
logger = setup_logging("wopr-camera", config=config)

game_id = "dune_imperium"
subject = "capture"
sequence = 1

# Generate filepath from config
filepath = imagefilename(
  game_id=game_id,
  subject=subject,
  sequence=sequence,
  config=config
)
  
resolution = config.camera.get_resolution(config.camera.default_resolution)
logger.info(f"Capturing {resolution.width}x{resolution.height} to {filepath}")
    
# Initialize camera (0 = default camera)
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

# Set resolution (may or may not work depending on camera)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution.width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution.height)

# Capture
ret, frame = cap.read()
if ret:
    print(f"File: {filepath}")
    cv2.imwrite(filepath, frame)

cap.release()
