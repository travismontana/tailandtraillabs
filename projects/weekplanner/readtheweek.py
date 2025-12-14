#!/usr/bin/env python3
"""
Weekly Task and Meal Planner

This script reads a YAML file containing weekly tasks, meals, and activities, then:
- Creates tasks in Google Tasks (for non-time-specific to-dos)
- Creates time-specific tasks as Calendar events with 15min reminders (deadline-based)
- Creates meal events in Google Calendar (Food calendar)
- Creates activity events in Google Calendar (Primary calendar) with scheduled times

Required OAuth scopes:
- https://www.googleapis.com/auth/tasks (for Google Tasks)
- https://www.googleapis.com/auth/calendar (for Google Calendar)

Usage:
    python readtheweek.py [-v] [-q] [-c CREDSFILE] <yaml_file>

Example:
    python readtheweek.py week.yaml                    # Normal mode
    python readtheweek.py -v week.yaml                 # Verbose mode
    python readtheweek.py -q week.yaml                 # Quiet mode
"""

import argparse
import logging
import yaml
import os
import os.path
import re
import stat
import warnings
from pathlib import Path

# Suppress ALL warnings (do this as early as possible)
warnings.filterwarnings('ignore')

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import time, datetime, timedelta

# Suppress noisy warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', message='.*urllib3.*')
warnings.filterwarnings('ignore', message='.*chardet.*')

# Suppress googleapiclient INFO logs about file_cache
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Global configuration
VERBOSE = False
QUIET = False

# OAuth scopes for Google APIs
SCOPES = [
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/calendar"
]

# Default meal times (24-hour format)
times = {
    'breakfast': time(7, 30),
    'lunch': time(11, 30),
    'dinner': time(18, 30),
    'snack': time(15, 0)
}

def log(msg):
    """
    Log a message if verbose mode is enabled.
    
    Args:
        msg (str): The message to log
    """
    if VERBOSE:
        logger.info(msg)

def info(msg):
    """
    Print an info message unless quiet mode is enabled.
    
    Args:
        msg (str): The message to print
    """
    if not QUIET:
        print(msg)

def secure_file_path(filename, base_dir=None):
    """
    Get a secure file path in the user's home directory.
    
    Args:
        filename (str): Name of the file
        base_dir (str): Optional subdirectory under ~/.config/
        
    Returns:
        Path: Secure file path
    """
    if base_dir:
        config_dir = Path.home() / '.config' / base_dir
    else:
        config_dir = Path.home() / '.config' / 'readtheweek'
    
    # Create directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    
    return config_dir / filename

def check_file_permissions(filepath):
    """
    Check if a file has secure permissions (readable only by owner).
    
    Args:
        filepath (str or Path): Path to the file to check
        
    Returns:
        bool: True if permissions are secure, False otherwise
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        return True
    
    file_stat = filepath.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    
    # Check if file is readable/writable by group or others
    if file_mode & (stat.S_IRWXG | stat.S_IRWXO):
        if not QUIET:
            logger.warning(f"File {filepath} has insecure permissions ({oct(file_mode)})")
            logger.warning(f"Fix with: chmod 600 {filepath}")
        return False
    
    return True

def secure_write_file(filepath, content):
    """
    Write content to a file with secure permissions.
    
    Args:
        filepath (str or Path): Path to write to
        content (str): Content to write
    """
    filepath = Path(filepath)
    
    # Write the file
    with open(filepath, 'w') as f:
        f.write(content)
    
    # Set secure permissions (owner read/write only)
    filepath.chmod(0o600)
    log(f"Wrote file with secure permissions: {filepath}")

def optsfunc():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(description="Read The Week Options")
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('-q', '--quiet', action='store_true', help='Minimal output (errors only)')
    parser.add_argument('-c', '--credsfile', type=str, 
                       default=str(secure_file_path('credentials.json')),
                       help='Path to the OAuth credentials file')
    parser.add_argument('-t', '--tokenfile', type=str,
                       default=str(secure_file_path('token.json')),
                       help='Path to store the OAuth token')
    parser.add_argument('--food-calendar', type=str,
                       default=None,
                       help='Food calendar ID (will prompt if not provided)')
    parser.add_argument('file', type=str, help='Path to the input YAML file')
    return parser.parse_args()

def readtheweek(file_path):
    """
    Read and parse the weekly planning YAML file.
    
    Args:
        file_path (str): Path to the YAML file to read
        
    Returns:
        dict: Parsed YAML data
        
    Raises:
        ValueError: If YAML is invalid or missing required fields
    """
    file_path = Path(file_path)
    
    # Check if file exists
    if not file_path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")
    
    # Check file permissions
    if not check_file_permissions(file_path):
        logger.warning(f"YAML file has insecure permissions: {file_path}")
    
    with open(file_path, 'r') as file:
        # Use safe_load instead of full_load for security
        data = yaml.safe_load(file)
    
    log(f"File content read successfully from {file_path}")
    
    # Basic validation
    if not isinstance(data, dict):
        raise ValueError("YAML file must contain a dictionary")
    
    return data

def parsetheweek(data):
    """
    Parse the weekly data structure.
    
    Args:
        data (dict): Raw data from YAML file
        
    Returns:
        dict: Processed data
    """
    log("Parsing data...")
    
    # Validate data structure
    if 'allweek' not in data:
        log("No 'allweek' section found in YAML")
    
    return data

def parse_item_with_time(item_data):
    """
    Parse an item that could be:
    - A simple string: "Do laundry"
    - A time-prefixed string: "14:30 - Finish report"
    
    Args:
        item_data: String containing task information
        
    Returns:
        tuple: (title, due_time, is_timed)
    """
    if isinstance(item_data, str):
        # Check for time prefix: "HH:MM - text"
        match = re.match(r'^(\d{1,2}):(\d{2})\s*-\s*(.+)$', item_data)
        if match:
            hour, minute, title = match.groups()
            hour, minute = int(hour), int(minute)
            
            # Validate time
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                logger.warning(f"Invalid time in '{item_data}', treating as regular task")
                return item_data, None, False
            
            return title, time(hour, minute), True
        
        return item_data, None, False
    
    return str(item_data), None, False

def parse_activity_with_time(item_data, default_time=None, default_duration=120):
    """
    Parse an activity with time and duration support.
    
    Args:
        item_data: String or dict containing activity information
        default_time (time): Default time if none specified
        default_duration (int): Default duration in minutes
        
    Returns:
        tuple: (title, activity_time, duration_minutes)
    """
    # Handle dictionary format
    if isinstance(item_data, dict):
        title = item_data.get('item', item_data.get('title', 'Untitled'))
        
        time_str = item_data.get('time')
        if time_str:
            try:
                hour, minute = map(int, time_str.split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("Invalid time")
                activity_time = time(hour, minute)
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid time format '{time_str}', using default")
                activity_time = default_time
        else:
            activity_time = default_time
        
        try:
            duration = int(item_data.get('duration', default_duration))
            if duration <= 0 or duration > 1440:  # Max 24 hours
                raise ValueError("Duration out of range")
        except (ValueError, TypeError):
            logger.warning(f"Invalid duration, using default {default_duration} minutes")
            duration = default_duration
        
        return title, activity_time, duration
    
    # Handle string format
    item_str = str(item_data)
    
    # Check for time prefix: "HH:MM - text"
    match = re.match(r'^(\d{1,2}):(\d{2})\s*-\s*(.+)$', item_str)
    if match:
        hour, minute, title = match.groups()
        hour, minute = int(hour), int(minute)
        
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            logger.warning(f"Invalid time in '{item_str}', using default")
            return item_str, default_time, default_duration
        
        return title, time(hour, minute), default_duration
    
    return item_str, default_time, default_duration

def get_food_calendar_id(calendar_service, provided_id=None):
    """
    Get the Food calendar ID, either from argument or by prompting user.
    
    Args:
        calendar_service: Google Calendar API service
        provided_id (str): Calendar ID provided via command line
        
    Returns:
        str: Food calendar ID
    """
    if provided_id:
        return provided_id
    
    # Check for saved calendar ID
    config_file = secure_file_path('calendar_config.txt')
    if config_file.exists():
        with open(config_file, 'r') as f:
            saved_id = f.read().strip()
            if saved_id:
                log(f"Using saved Food calendar ID")
                return saved_id
    
    # List calendars and prompt (only if not quiet)
    if QUIET:
        raise ValueError("Food calendar ID required. Use --food-calendar or remove --quiet flag.")
    
    print("\nAvailable calendars:")
    calendars = calendar_service.calendarList().list().execute()
    calendar_list = calendars.get('items', [])
    
    for idx, cal in enumerate(calendar_list):
        print(f"{idx + 1}. {cal['summary']}")
    
    while True:
        try:
            choice = input("\nSelect Food calendar number (or enter calendar ID): ").strip()
            
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(calendar_list):
                    selected_id = calendar_list[idx]['id']
                    break
            else:
                selected_id = choice
                break
        except (ValueError, KeyboardInterrupt):
            print("Invalid selection. Please try again.")
    
    # Save for future use
    secure_write_file(config_file, selected_id)
    info("Saved Food calendar ID for future use")
    
    return selected_id

def createtask(credsfile, tokenfile, taskdict, food_calendar_id=None):
    """
    Create tasks and calendar events from the weekly planning dictionary.
    
    Args:
        credsfile (str): Path to OAuth credentials JSON file
        tokenfile (str): Path to store OAuth token
        taskdict (dict): Dictionary containing weekly tasks, meals, and activities
        food_calendar_id (str): Optional Food calendar ID
        
    Returns:
        dict: Statistics about what was created
    """
    credsfile = Path(credsfile)
    tokenfile = Path(tokenfile)
    
    # Statistics
    stats = {
        'tasks': 0,
        'timed_tasks': 0,
        'meals': 0,
        'activities': 0,
        'skipped': 0
    }
    
    # Validate credentials file exists
    if not credsfile.exists():
        raise FileNotFoundError(f"Credentials file not found: {credsfile}")
    
    # Check credentials file permissions
    if not check_file_permissions(credsfile):
        raise PermissionError(f"Credentials file has insecure permissions: {credsfile}")
    
    creds = None
    
    # ===== AUTHENTICATION =====
    if tokenfile.exists():
        check_file_permissions(tokenfile)
        creds = Credentials.from_authorized_user_file(str(tokenfile), SCOPES)
        log("Loaded credentials from token file.")
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            log("Refreshed expired credentials.")
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credsfile), SCOPES)
            creds = flow.run_local_server(port=0)
            log("Obtained new credentials via OAuth flow.")
        
        secure_write_file(tokenfile, creds.to_json())
    
    # ===== BUILD API SERVICES =====
    try:
        service = build("tasks", "v1", credentials=creds)
        calendar_service = build("calendar", "v3", credentials=creds)
        
        log("Built Google Tasks and Calendar services.")
        
        # Get Food calendar ID
        food_calendar_id = get_food_calendar_id(calendar_service, food_calendar_id)
        
        # Get task lists
        results = service.tasklists().list(maxResults=10).execute()
        items = results.get("items", [])
        
        if not items:
            logger.error("No task lists found.")
            return stats
        
        log("Task lists:")
        for item in items:
            log(f"  {item['title']} ({item['id']})")
    
    except HttpError as err:
        logger.error(f"API error: {err}")
        return stats
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return stats
    
    # Find the "My Stuff" task list
    my_tasks = next((item for item in items if item['title'] == 'My Stuff'), None)
    if not my_tasks:
        logger.error("Could not find 'My Stuff' task list")
        return stats
    
    my_tasks_id = my_tasks['id']
    my_tasks_tasks = service.tasks().list(tasklist=my_tasks_id).execute()
    
    # ===== PROCESS EACH DAY =====
    log("Creating tasks and events...")
    for day_name, day_data in taskdict.items():
        log(f"Processing day: {day_name}")
        
        # Calculate due date
        due_datetime = None
        day_name_lower = day_name.lower()
        
        if day_name_lower != 'allweek':
            day_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            
            if day_name_lower in day_map:
                today = datetime.now()
                current_weekday = today.weekday()
                target_weekday = day_map[day_name_lower]
                
                days_ahead = target_weekday - current_weekday
                if days_ahead < 0:
                    days_ahead += 7
                
                target_date = today + timedelta(days=days_ahead)
                due_datetime = target_date.replace(hour=20, minute=0, second=0, microsecond=0)
                whendue = due_datetime.isoformat() + 'Z'
                log(f"Due date for {day_name_lower}: {whendue}")
        else:
            whendue = None
        
        # Process Things
        things_key = next((k for k in day_data.keys() if k.lower() == 'things'), None)
        if things_key and day_data[things_key]:
            for item_data in day_data[things_key]:
                try:
                    title, item_time, is_timed = parse_item_with_time(item_data)
                    
                    if is_timed and whendue:
                        # Time-specific task → Calendar event
                        task_datetime = due_datetime.replace(hour=item_time.hour, minute=item_time.minute)
                        
                        if task_datetime < datetime.now():
                            task_datetime += timedelta(days=7)
                        
                        start_time = (task_datetime - timedelta(minutes=30)).isoformat()
                        end_time = task_datetime.isoformat()
                        timezone = 'America/Chicago'
                        
                        # Duplicate check
                        time_min = task_datetime.replace(hour=0, minute=0, second=0).isoformat() + 'Z'
                        time_max = (task_datetime + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat() + 'Z'
                        
                        existing_events = calendar_service.events().list(
                            calendarId='primary',
                            timeMin=time_min,
                            timeMax=time_max,
                            singleEvents=True
                        ).execute()
                        
                        events = existing_events.get('items', [])
                        event_exists = any(e.get('summary') == f"⏰ {title}" for e in events)
                        
                        if not event_exists:
                            event = {
                                'summary': f"⏰ {title}",
                                'description': 'Task - Complete by this time',
                                'start': {'dateTime': start_time, 'timeZone': timezone},
                                'end': {'dateTime': end_time, 'timeZone': timezone},
                                'reminders': {
                                    'useDefault': False,
                                    'overrides': [{'method': 'popup', 'minutes': 15}],
                                },
                            }
                            
                            calendar_service.events().insert(calendarId='primary', body=event).execute()
                            log(f"Timed task created: {title}")
                            stats['timed_tasks'] += 1
                        else:
                            log(f"Timed task already exists: {title}")
                            stats['skipped'] += 1
                    
                    else:
                        # Regular task
                        tasks = {'title': title}
                        if whendue:
                            tasks['due'] = whendue
                        
                        # Duplicate check
                        if 'items' in my_tasks_tasks:
                            existing_titles = [t['title'] for t in my_tasks_tasks['items']]
                            if title in existing_titles:
                                log(f"Task already exists: {title}")
                                stats['skipped'] += 1
                                continue
                        
                        service.tasks().insert(tasklist=my_tasks_id, body=tasks).execute()
                        log(f"Task created: {title}")
                        stats['tasks'] += 1
                
                except Exception as e:
                    logger.error(f"Error processing task '{item_data}': {e}")
                    continue
        
        # Process Meals
        for meal_name, meal_time in times.items():
            meal_key = meal_name.lower() if meal_name.lower() in day_data else meal_name.capitalize()
            
            if meal_key in day_data and day_data[meal_key]:
                try:
                    item = day_data[meal_key]
                    
                    if whendue:
                        mealduedatetime = due_datetime.replace(hour=meal_time.hour, minute=meal_time.minute)
                        
                        if mealduedatetime < datetime.now():
                            mealduedatetime += timedelta(days=7)
                        
                        start_time = mealduedatetime.isoformat()
                        end_time = (mealduedatetime + timedelta(hours=1)).isoformat()
                        timezone = 'America/Chicago'
                        
                        # Duplicate check
                        time_min = mealduedatetime.replace(hour=0, minute=0, second=0).isoformat() + 'Z'
                        time_max = (mealduedatetime + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat() + 'Z'
                        
                        existing_events = calendar_service.events().list(
                            calendarId=food_calendar_id,
                            timeMin=time_min,
                            timeMax=time_max,
                            singleEvents=True
                        ).execute()
                        
                        events = existing_events.get('items', [])
                        event_exists = any(e.get('summary') == item for e in events)
                        
                        if not event_exists:
                            event = {
                                'summary': item,
                                'description': meal_name.capitalize(),
                                'start': {'dateTime': start_time, 'timeZone': timezone},
                                'end': {'dateTime': end_time, 'timeZone': timezone},
                            }
                            
                            calendar_service.events().insert(calendarId=food_calendar_id, body=event).execute()
                            log(f"Meal event created: {meal_name} - {item}")
                            stats['meals'] += 1
                        else:
                            log(f"Meal already exists: {meal_name} - {item}")
                            stats['skipped'] += 1
                
                except Exception as e:
                    logger.error(f"Error processing meal '{meal_name}': {e}")
                    continue
        
        # Process Activities
        activity_key = next((k for k in day_data.keys() if k.lower() == 'activity'), None)
        if activity_key and day_data[activity_key]:
            for activity_data in day_data[activity_key]:
                try:
                    title, activity_time, duration = parse_activity_with_time(
                        activity_data,
                        default_time=time(19, 0),
                        default_duration=120
                    )
                    
                    if whendue and activity_time:
                        activity_datetime = due_datetime.replace(
                            hour=activity_time.hour,
                            minute=activity_time.minute,
                            second=0,
                            microsecond=0
                        )
                        
                        if activity_datetime < datetime.now():
                            activity_datetime += timedelta(days=7)
                        
                        start_time = activity_datetime.isoformat()
                        end_time = (activity_datetime + timedelta(minutes=duration)).isoformat()
                        timezone = 'America/Chicago'
                        
                        # Duplicate check
                        target_date = activity_datetime.date()
                        time_min = datetime.combine(target_date, time(0, 0)).isoformat() + 'Z'
                        time_max = datetime.combine(target_date + timedelta(days=1), time(23, 59)).isoformat() + 'Z'
                        
                        existing_events = calendar_service.events().list(
                            calendarId='primary',
                            timeMin=time_min,
                            timeMax=time_max,
                            singleEvents=True
                        ).execute()
                        
                        events = existing_events.get('items', [])
                        event_exists = any(e.get('summary') == title for e in events)
                        
                        if not event_exists:
                            event = {
                                'summary': title,
                                'description': 'Activity',
                                'start': {'dateTime': start_time, 'timeZone': timezone},
                                'end': {'dateTime': end_time, 'timeZone': timezone},
                            }
                            
                            calendar_service.events().insert(calendarId='primary', body=event).execute()
                            log(f"Activity event created: {title}")
                            stats['activities'] += 1
                        else:
                            log(f"Activity already exists: {title}")
                            stats['skipped'] += 1
                
                except Exception as e:
                    logger.error(f"Error processing activity '{activity_data}': {e}")
                    continue
    
    return stats

def main():
    """
    Main entry point for the script.
    """
    try:
        getopts = optsfunc()
        
        global VERBOSE, QUIET
        
        if getopts.verbose:
            VERBOSE = True
        
        if getopts.quiet:
            QUIET = True
            # Set logging to only show errors
            logging.getLogger().setLevel(logging.ERROR)
        
        if VERBOSE and QUIET:
            print("Error: Cannot use --verbose and --quiet together")
            return 1
        
        log(f"Reading file: {getopts.file}")
        data = readtheweek(getopts.file)
        taskdict = parsetheweek(data)
        stats = createtask(getopts.credsfile, getopts.tokenfile, taskdict, getopts.food_calendar)
        
        # Show summary
        if not QUIET:
            total = stats['tasks'] + stats['timed_tasks'] + stats['meals'] + stats['activities']
            if total > 0 or stats['skipped'] > 0:
                print(f"\n✓ Complete: {stats['tasks']} tasks, {stats['timed_tasks']} timed tasks, "
                      f"{stats['meals']} meals, {stats['activities']} activities created")
                if stats['skipped'] > 0:
                    print(f"  ({stats['skipped']} items already existed)")
            else:
                print("✓ No new items to create")
    
    except KeyboardInterrupt:
        if not QUIET:
            print("\nInterrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())