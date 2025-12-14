#!/usr/bin/env python3

import cv2
import time
import random
import string
from datetime import datetime

now = datetime.now()
timestamp = now.strftime("%Y%m%d-%H%M%S")

# Initialize camera (0 = default camera)
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
woprdir = "/remote/wopr"
woprimagedir = f"{woprdir}/images"
woprimagedirimport = f"{woprimagedir}/import"
project = "testproj1"
subject = "round1"

for i in range(3):
  sixrand = ''.join(random.sample(string.ascii_lowercase, 8))

imagefile = f"{timestamp}-{sixrand}-{project}-{subject}.jpg"
imagefullpath = f"{woprimagedirimport}/{imagefile}"

cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

# Set resolution (may or may not work depending on camera)
#cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
#cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
cap.set(3, 3840)
cap.set(4, 2160)

# Capture
ret, frame = cap.read()
if ret:
    print(f"File: {imagefullpath}")
    cv2.imwrite(imagefullpath, frame)

cap.release()
