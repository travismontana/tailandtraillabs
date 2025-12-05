#!/bin/bash
# Weekly Plan Sync Helper Script
# 
# SETUP:
# 1. Replace YOUR_EMAIL with your Gmail address
# 2. Replace YOUR_APP_PASSWORD with your Google App Password
# 3. Make sure credentials.json is in the same directory
# 4. Make this script executable: chmod +x run-sync.sh

python sync-week.py thisweek.md \
  --google-creds credentials.json \
  --keep-user YOUR_EMAIL@gmail.com \
  --keep-pass "YOUR_APP_PASSWORD"
