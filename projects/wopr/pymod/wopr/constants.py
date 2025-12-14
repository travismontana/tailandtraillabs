"""Shared constants across WOPR components"""

# Game types
GAME_TYPE_DUNE = "dune_imperium"
GAME_TYPE_LEGION = "star_wars_legion"

# Game statuses
STATUS_SETUP = "setup"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_ABANDONED = "abandoned"

# Analysis statuses
ANALYSIS_PENDING = "pending"
ANALYSIS_PROCESSING = "processing"
ANALYSIS_COMPLETED = "completed"
ANALYSIS_FAILED = "failed"

# Image subjects
SUBJECT_SETUP = "setup"
SUBJECT_CAPTURE = "capture"
SUBJECT_MOVE = "move"
SUBJECT_THUMBNAIL = "thumb"

# Vision models
MODEL_QWEN2VL = "qwen2-vl:7b"
MODEL_OPENCV = "opencv"