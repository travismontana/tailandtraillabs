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
    python readtheweek.py [-v] [-c CREDSFILE] <yaml_file>

Example:
    python readtheweek.py -v -c ~/.config/creds.json week.yaml
"""

import argparse
import logging
import yaml
import os.path
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import time, datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global configuration
VERBOSE = False

# OAuth scopes for Google APIs
SCOPES = [
    "https://www.googleapis.com/auth/tasks",      # Google Tasks read/write
    "https://www.googleapis.com/auth/calendar"    # Google Calendar read/write
]

# Default meal times (24-hour format)
times = {
    'breakfast': time(7, 30),   # 7:30 AM
    'lunch': time(11, 30),      # 11:30 AM
    'dinner': time(18, 30),     # 6:30 PM
    'snack': time(15, 0)        # 3:00 PM
}

def log(msg):
    """
    Log a message if verbose mode is enabled.
    
    Args:
        msg (str): The message to log
    """
    if VERBOSE:
        logger.info(msg)

def optsfunc():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed command-line arguments containing:
            - v (bool): Verbose mode flag
            - credsfile (str): Path to OAuth credentials file
            - file (str): Path to input YAML file
    """
    parser = argparse.ArgumentParser(description="Read The Week Options")
    parser.add_argument('-v', action='store_true', help='Enable verbose output')
    parser.add_argument('-c', '--credsfile', type=str, default='token.json', 
                       help='Path to the OAuth credentials file')
    parser.add_argument('file', type=str, help='Path to the input YAML file')
    return parser.parse_args()

def readtheweek(file_path):
    """
    Read and parse the weekly planning YAML file.
    
    Args:
        file_path (str): Path to the YAML file to read
        
    Returns:
        dict: Parsed YAML data containing weekly tasks, meals, and activities
        
    Expected YAML structure:
        allweek:
            things: [list of tasks]
        monday/tuesday/etc:
            Breakfast: meal name
            Lunch: meal name
            Dinner: meal name
            Snack: snack name
            Things: 
                - "Task without time"
                - "14:30 - Task due by 2:30pm"
            Activity: 
                - "19:00 - Game Night"
                - item: "Doctor Appointment"
                  time: "14:00"
                  duration: 60
    """
    with open(file_path, 'r') as file:
        data = yaml.full_load(file)
    log(f"File content read successfully from {file_path}")
    log(f"Data: {data}")
    return data

def parsetheweek(data):
    """
    Parse the weekly data structure.
    
    Currently a placeholder that returns the data as-is. Future enhancements could include:
    - Data validation
    - Transformation of data formats
    - Merging multiple weeks
    
    Args:
        data (dict): Raw data from YAML file
        
    Returns:
        dict: Processed data (currently unchanged from input)
        
    Notes:
        Scheduling logic:
        - If today is Monday and there's a task for Monday, it gets added to today
        - If today is Monday and there's a task for Sunday, it gets added to next Sunday
        - If a time-specific task's time has already passed today, it gets scheduled for next week
    """
    log("Parsing data...")
    log(f"Data to parse: {data['allweek']}")
    
    allday = data.get('allday', [])
    log(f"All day tasks: {allday}")
    return data

def parse_item_with_time(item_data):
    """
    Parse an item that could be:
    - A simple string: "Do laundry" → No time
    - A time-prefixed string: "14:30 - Finish report" → Time extracted
    
    Args:
        item_data: String containing task information
        
    Returns:
        tuple: (title, due_time, is_timed)
            - title (str): The task title
            - due_time (time): The time object if specified, else None
            - is_timed (bool): True if a time was specified
    """
    if isinstance(item_data, str):
        # Check for time prefix: "HH:MM - text"
        match = re.match(r'^(\d{1,2}):(\d{2})\s*-\s*(.+)$', item_data)
        if match:
            hour, minute, title = match.groups()
            return title, time(int(hour), int(minute)), True
        
        return item_data, None, False
    
    return str(item_data), None, False

def parse_activity_with_time(item_data, default_time=None, default_duration=120):
    """
    Parse an activity that could be:
    - A simple string: "Game Night"
    - A time-prefixed string: "19:00 - Game Night"
    - A dict: {"item": "Meeting", "time": "14:30", "duration": 90}
    
    Args:
        item_data: String or dict containing activity information
        default_time (time): Default time if none specified (default: None)
        default_duration (int): Default duration in minutes (default: 120)
        
    Returns:
        tuple: (title, activity_time, duration_minutes)
    """
    # Handle dictionary format
    if isinstance(item_data, dict):
        title = item_data.get('item', item_data.get('title', 'Untitled'))
        
        time_str = item_data.get('time')
        if time_str:
            hour, minute = map(int, time_str.split(':'))
            activity_time = time(hour, minute)
        else:
            activity_time = default_time
        
        duration = item_data.get('duration', default_duration)
        return title, activity_time, duration
    
    # Handle string format
    item_str = str(item_data)
    
    # Check for time prefix: "HH:MM - text"
    match = re.match(r'^(\d{1,2}):(\d{2})\s*-\s*(.+)$', item_str)
    if match:
        hour, minute, title = match.groups()
        return title, time(int(hour), int(minute)), default_duration
    
    # Plain string with no time
    return item_str, default_time, default_duration

def createtask(credsfile, taskdict):
    """
    Create tasks and calendar events from the weekly planning dictionary.
    
    This function:
    1. Authenticates with Google APIs using OAuth
    2. Creates tasks in Google Tasks for non-time-specific to-dos
    3. Creates calendar events for time-specific tasks with 15min reminders
    4. Creates meal events in the Food calendar
    5. Creates activity events in the primary calendar
    6. Checks for duplicates before creating new entries
    
    Args:
        credsfile (str): Path to OAuth credentials JSON file
        taskdict (dict): Dictionary containing weekly tasks, meals, and activities
        
    Returns:
        None
        
    Side effects:
        - Creates/updates token file at /tmp/token.json
        - Creates tasks in Google Tasks
        - Creates events in Google Calendar
        
    Raises:
        HttpError: If Google API calls fail
    """
    # Calendar ID for the Food calendar
    food_calendar_id = 'bomar.us_t22bmj6saugbq00etnmorqr3ug@group.calendar.google.com'
    tokenfile = "/tmp/token.json"
    
    # Log tasks being processed
    for task, due in taskdict.items():
        log(f"Creating task: {task} with due date: {due}")
    
    creds = None
    
    # ===== AUTHENTICATION =====
    # Load existing credentials if available
    if os.path.exists(tokenfile):
        creds = Credentials.from_authorized_user_file(tokenfile, SCOPES)
        log("Loaded credentials from token file.")
    
    # Refresh or obtain new credentials if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh expired credentials
            creds.refresh(Request())
            log("Refreshed expired credentials.")
        else:
            # Run OAuth flow to get new credentials
            flow = InstalledAppFlow.from_client_secrets_file(credsfile, SCOPES)
            creds = flow.run_local_server(port=0)
            log("Obtained new credentials via OAuth flow.")
        
        # Save credentials for future runs
        with open(tokenfile, "w") as token:
            token.write(creds.to_json())
            log(f"Saved credentials to {tokenfile}.")
    
    # ===== BUILD API SERVICES =====
    try:
        # Build Google Tasks and Calendar services
        service = build("tasks", "v1", credentials=creds)
        calendar_service = build("calendar", "v3", credentials=creds)
        
        # List available calendars for debugging
        calendars = calendar_service.calendarList().list().execute()
        log(f"Available calendars: {calendars.get('items', [])}")
        for cal in calendars.get('items', []):
            log(f"Calendar: {cal['summary']} - ID: {cal['id']}")
        
        log("Built Google Tasks service.")
        
        # Get list of task lists
        results = service.tasklists().list(maxResults=10).execute()
        items = results.get("items", [])
        log(f"Fetched task lists from Google Tasks.: {items}")
        
        if not items:
            print("No task lists found.")
            log("No task lists found.")
            return
        
        print("Task lists:")
        for item in items:
            log(f"{item['title']} ({item['id']})")
            
    except HttpError as err:
        print(err)
        return
    
    # ===== FIND TARGET TASK LIST =====
    # Find the "My Stuff" task list
    my_tasks = next((item for item in items if item['title'] == 'My Stuff'), None)
    if my_tasks:
        my_tasks_id = my_tasks['id']
        # Get existing tasks for duplicate detection
        my_tasks_tasks = service.tasks().list(tasklist=my_tasks_id).execute()
    
    # ===== PROCESS EACH DAY =====
    log("Creating the tasks")
    for day_name, day_data in taskdict.items():
        log(f"Processing day: {day_name} with data: {day_data}")
        
        # ===== CALCULATE DUE DATE FOR THIS DAY =====
        due_datetime = None
        day_name = day_name.lower()
        
        if day_name != 'allweek':
            # Map day names to Python weekday numbers (Monday=0, Sunday=6)
            day_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            
            if day_name in day_map:
                today = datetime.now()
                current_weekday = today.weekday()
                target_weekday = day_map[day_name]
                
                # Calculate how many days ahead the target day is
                days_ahead = target_weekday - current_weekday
                
                # If the day has already passed this week, schedule for next week
                if days_ahead < 0:
                    days_ahead += 7
                
                # Calculate the target date at 8pm (default end-of-day time)
                target_date = today + timedelta(days=days_ahead)
                due_datetime = target_date.replace(hour=20, minute=0, second=0, microsecond=0)
                
                # Format as RFC 3339 for Google Tasks API
                whendue = due_datetime.isoformat() + 'Z'
                log(f"Due date for {day_name}: {whendue}")
        else:
            # 'allweek' tasks don't have a specific due date
            whendue = None
        
        # ===== PROCESS GENERAL TASKS (Things) =====
        # Find the 'Things' key (case-insensitive)
        things_key = next((k for k in day_data.keys() if k.lower() == 'things'), None)
        if things_key and day_data[things_key]:
            for item_data in day_data[things_key]:
                title, item_time, is_timed = parse_item_with_time(item_data)
                
                if is_timed and whendue:
                    # TIME-SPECIFIC TASK → Create as calendar event with reminder
                    log(f"Creating timed task: {title} due at {item_time}")
                    
                    task_datetime = due_datetime.replace(hour=item_time.hour, minute=item_time.minute)
                    
                    if task_datetime < datetime.now():
                        task_datetime += timedelta(days=7)
                    
                    # Create a 30-minute slot ending at the deadline
                    start_time = (task_datetime - timedelta(minutes=30)).isoformat()
                    end_time = task_datetime.isoformat()
                    timezone = 'America/Chicago'
                    
                    # Check for duplicates
                    time_min = task_datetime.replace(hour=0, minute=0, second=0).isoformat() + 'Z'
                    time_max = (task_datetime + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat() + 'Z'
                    
                    existing_events = calendar_service.events().list(
                        calendarId='primary',
                        timeMin=time_min,
                        timeMax=time_max,
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    events = existing_events.get('items', [])
                    event_exists = any(e.get('summary') == f"⏰ {title}" for e in events)
                    
                    if event_exists:
                        log(f"Calendar event '⏰ {title}' already exists, skipping.")
                    else:
                        event = {
                            'summary': f"⏰ {title}",  # Emoji to distinguish tasks from appointments
                            'description': 'Task - Complete by this time',
                            'start': {
                                'dateTime': start_time,
                                'timeZone': timezone,
                            },
                            'end': {
                                'dateTime': end_time,
                                'timeZone': timezone,
                            },
                            'reminders': {
                                'useDefault': False,
                                'overrides': [
                                    {'method': 'popup', 'minutes': 15},  # 15 min reminder
                                ],
                            },
                        }
                        
                        event_result = calendar_service.events().insert(
                            calendarId='primary',
                            body=event
                        ).execute()
                        
                        log(f"Timed task calendar event created: {event_result.get('htmlLink')}")
                
                else:
                    # REGULAR TASK → Create as Google Task (date only, no specific time)
                    log(f"Creating task: {title}")
                    
                    tasks = {
                        'title': title,
                    }
                    if whendue:
                        tasks['due'] = whendue
                    
                    log(f"Creating task: {tasks}")
                    
                    # Check for duplicates
                    if 'items' in my_tasks_tasks:
                        existing_titles = [t['title'] for t in my_tasks_tasks['items']]
                        if title in existing_titles:
                            log(f"Task {title} already exists, skipping.")
                            continue
                    
                    # Create the task
                    tasksexec = service.tasks().insert(tasklist=my_tasks_id, body=tasks).execute()
                    log(f"Task created: {tasksexec['title']} with ID: {tasksexec}")
        
        # ===== PROCESS MEALS (Breakfast, Lunch, Dinner, Snack) =====
        # Loop through each meal type and create calendar events
        for meal_name, meal_time in times.items():
            # Find the meal key (case-insensitive)
            meal_key = meal_name.lower() if meal_name.lower() in day_data else meal_name.capitalize()
            
            if meal_key in day_data and day_data[meal_key]:
                item = day_data[meal_key]
                log(f"Creating {meal_name} task: {item}")
                
                if whendue:
                    # Calculate meal datetime using the predefined meal time
                    mealduedatetime = due_datetime.replace(hour=meal_time.hour, minute=meal_time.minute)
                    
                    # If the meal time has already passed today, schedule for next week
                    if mealduedatetime < datetime.now():
                        mealduedatetime += timedelta(days=7)
                    
                    # Calendar events need both start and end times
                    start_time = mealduedatetime.isoformat()
                    end_time = (mealduedatetime + timedelta(hours=1)).isoformat()  # 1 hour duration
                    timezone = 'America/Chicago'
                    
                    # Define search window for duplicate detection (entire day)
                    time_min = mealduedatetime.replace(hour=0, minute=0, second=0).isoformat() + 'Z'
                    time_max = (mealduedatetime + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat() + 'Z'
                    
                    # Search for existing meal events
                    existing_events = calendar_service.events().list(
                        calendarId=food_calendar_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    events = existing_events.get('items', [])
                    
                    # Check for exact title match
                    event_exists = False
                    for e in events:
                        if e.get('summary') == item:
                            log(f"Found existing event: {e.get('summary')} at {e.get('start')}")
                            event_exists = True
                            break
                    
                    if event_exists:
                        log(f"Calendar event '{item}' for {meal_name} already exists, skipping.")
                    else:
                        # Create the meal event
                        event = {
                            'summary': item,
                            'description': meal_name.capitalize(),
                            'start': {
                                'dateTime': start_time,
                                'timeZone': timezone,
                            },
                            'end': {
                                'dateTime': end_time,
                                'timeZone': timezone,
                            },
                        }
                        
                        # Insert into Food calendar
                        event_result = calendar_service.events().insert(
                            calendarId=food_calendar_id,
                            body=event
                        ).execute()
                        
                        log(f"{meal_name.capitalize()} calendar event created: {event_result.get('htmlLink')}")
                else:
                    log(f"No due date for {day_name}, skipping {meal_name} task creation.")
        
        # ===== PROCESS ACTIVITIES =====
        # Activities are appointments with scheduled start times and durations
        activity_key = next((k for k in day_data.keys() if k.lower() == 'activity'), None)
        if activity_key and day_data[activity_key]:
            for activity_data in day_data[activity_key]:
                # Parse activity with custom time/duration support
                title, activity_time, duration = parse_activity_with_time(
                    activity_data, 
                    default_time=time(19, 0),  # Default to 7pm
                    default_duration=120       # Default to 2 hours
                )
                
                log(f"Creating activity: {title}")
                
                if whendue and activity_time:
                    # Schedule activity at specific time with specific duration
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
                    
                    # Define search window for duplicate detection (entire day)
                    target_date = activity_datetime.date()
                    time_min = datetime.combine(target_date, time(0, 0)).isoformat() + 'Z'
                    time_max = datetime.combine(target_date + timedelta(days=1), time(23, 59)).isoformat() + 'Z'
                    
                    # Search for existing activity events
                    existing_events = calendar_service.events().list(
                        calendarId='primary',
                        timeMin=time_min,
                        timeMax=time_max,
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    events = existing_events.get('items', [])
                    
                    # Check for exact title match
                    event_exists = False
                    for e in events:
                        if e.get('summary') == title:
                            log(f"Found existing event: {e.get('summary')} at {e.get('start')}")
                            event_exists = True
                            break
                    
                    if event_exists:
                        log(f"Calendar event '{title}' already exists, skipping.")
                    else:
                        # Create the activity event
                        event = {
                            'summary': title,
                            'description': 'Activity',
                            'start': {
                                'dateTime': start_time,
                                'timeZone': timezone,
                            },
                            'end': {
                                'dateTime': end_time,
                                'timeZone': timezone,
                            },
                        }
                        
                        # Insert into primary calendar
                        event_result = calendar_service.events().insert(
                            calendarId='primary',
                            body=event
                        ).execute()
                        
                        log(f"Activity calendar event created: {event_result.get('htmlLink')}")
                else:
                    log(f"No due date for {day_name}, skipping {title} activity creation.")

def main():
    """
    Main entry point for the script.
    
    Parses command-line arguments, reads the YAML file, parses the data,
    and creates tasks and calendar events.
    """
    # Parse command-line arguments
    getopts = optsfunc()
    
    # Enable verbose logging if requested
    if getopts.v:
        global VERBOSE
        VERBOSE = True
    
    # Read and process the weekly planning file
    log(f"Reading file: {getopts.file}")
    data = readtheweek(getopts.file)
    taskdict = parsetheweek(data)
    createtask(getopts.credsfile, taskdict)

# Entry point
if __name__ == '__main__':
    main()