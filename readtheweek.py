#!/usr/bin/env python3

import argparse
import logging
import yaml
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import time, datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VERBOSE = False
#SCOPES = ["https://www.googleapis.com/auth/tasks.readonly"]
SCOPES = [
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/calendar"
]

times = {
    'breakfast': time(7, 30),
    'lunch': time(11, 30),
    'dinner': time(18, 30),
    'snack': time(15, 0)
}

def log(msg):
    if VERBOSE:
        logger.info(msg)

def optsfunc():
    parser = argparse.ArgumentParser(description="Read The Week Options")
    parser.add_argument('-v', action='store_true', help='Enable verbose output')
    parser.add_argument('-c', '--credsfile', type=str, default='token.json', help='Path to the token file')
    parser.add_argument('file', type=str, help='Path to the input file')
    return parser.parse_args()

def readtheweek(file_path):
    with open(file_path, 'r') as file:
        data = yaml.full_load(file)
    log(f"File content read successfully from {file_path}")
    log(f"Data: {data}")
    return data

def parsetheweek(data):
    # Placeholder for parsing logic
    log("Parsing data...")
    log(f"Data to parse: {data['allweek']}")
    """
    * data['allweek'] is expected to be a list of entries.
    * These entries will be added to google task "My Tasks"
    * For the daily entries, they get applied to the respective day and times.
    * If today is monday, and theres a task for monday in the sheet, 
    * it gets added to today, but sunday is next sunday.
    * If theres a time associated with the task, it gets added at that time.
    * If the time is before current time, it gets added to next week.
    * Implement parsing logic as needed.
    """
    allday = data.get('allday', [])
    log(f"All day tasks: {allday}")
    return data  # Modify as needed

def createtask(credsfile, taskdict):
    food_calendar_id = 'bomar.us_t22bmj6saugbq00etnmorqr3ug@group.calendar.google.com'
    tokenfile = "/tmp/token.json"
    # Placeholder for task creation logic
    for task, due in taskdict.items():
        log(f"Creating task: {task} with due date: {due}")
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(tokenfile):
        creds = Credentials.from_authorized_user_file(tokenfile, SCOPES)
        log("Loaded credentials from token file.")
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            log("Refreshed expired credentials.")
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credsfile, SCOPES
            )
            creds = flow.run_local_server(port=0)
            log("Obtained new credentials via OAuth flow.")
        # Save the credentials for the next run
        with open(tokenfile, "w") as token:
            token.write(creds.to_json())
            log(f"Saved credentials to {tokenfile}.")   
    try:
        service = build("tasks", "v1", credentials=creds)
        calendar_service = build("calendar", "v3", credentials=creds)
        calendars = calendar_service.calendarList().list().execute()
        log(f"Available calendars: {calendars.get('items', [])}")
        for cal in calendars.get('items', []):
            log(f"Calendar: {cal['summary']} - ID: {cal['id']}")
        log("Built Google Tasks service.")
        # Call the Tasks API
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

    # allweek stuff
    my_tasks = next((item for item in items if item['title'] == 'My Stuff'), None)
    if my_tasks:
        my_tasks_id = my_tasks['id']
        my_tasks_tasks = service.tasks().list(tasklist=my_tasks_id).execute()
    log("Creating the tasks")
    for day_name, day_data in taskdict.items():
        log(f"Processing day: {day_name} with data: {day_data}")
        # Calculate due date for daily tasks
        due_datetime = None
        if day_name != 'allweek':
            # Map day names to weekday numbers (Monday=0, Sunday=6)
            day_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            
            if day_name in day_map:
                today = datetime.now()
                current_weekday = today.weekday()
                target_weekday = day_map[day_name]
                
                # Calculate days until target day
                days_ahead = target_weekday - current_weekday
                
                # If the day already passed this week, schedule for next week
                if days_ahead < 0:
                    days_ahead += 7
                
                # Calculate the target date at 8pm
                target_date = today + timedelta(days=days_ahead)
                due_datetime = target_date.replace(hour=20, minute=0, second=0, microsecond=0)
                
                # Format for Google Tasks (RFC 3339)
                whendue = due_datetime.isoformat() + 'Z'
                log(f"Due date for {day_name}: {whendue}")
        else:
            whendue = None
        things_key = 'things' if 'things' in day_data else 'Things'
        if things_key in day_data and day_data[things_key]:
            for item in day_data[things_key]:
                log(f"Creating task: {item}")
                tasks = {
                    'title': item,
                }
                if whendue:
                    tasks['due'] = whendue
                log(f"Creating task: {tasks}")
                # check if the task already exists
                if 'items' in my_tasks_tasks:
                    existing_titles = [t['title'] for t in my_tasks_tasks['items']]
                    if item in existing_titles:
                        log(f"Task {item} already exists, skipping.")
                        continue
                tasksexec = service.tasks().insert(tasklist=my_tasks_id, body=tasks).execute()
                log(f"Task created: {tasksexec['title']} with ID: {tasksexec}")
        breakfast_key = 'breakfast' if 'breakfast' in day_data else 'Breakfast'
        if breakfast_key in day_data and day_data[breakfast_key]:
            item = day_data[breakfast_key]
            log(f"Creating breakfast task: {item}")
            tasks = {
                'title': item,
            }
            if whendue:
                btime = times['breakfast']
                bduedatetime = due_datetime.replace(hour=btime.hour, minute=btime.minute)
                if bduedatetime < datetime.now():
                    bduedatetime += timedelta(days=7)
                # Calendar event needs start and end times
                start_time = bduedatetime.isoformat()
                end_time = (bduedatetime + timedelta(hours=1)).isoformat()  # 1 hour duration
                timezone = 'America/Chicago'
                time_min = bduedatetime.replace(hour=0, minute=0, second=0).isoformat() + 'Z'
                time_max = (bduedatetime + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat() + 'Z'
                existing_events = calendar_service.events().list(
                    calendarId=food_calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    q=item,  # Search query for the event title
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()

                events = existing_events.get('items', [])
                # Check if event with matching title already exists
                event_exists = any(e.get('summary') == item for e in events)

                if event_exists:
                    log(f"Calendar event '{item}' already exists, skipping.")
                else:
                    event = {
                        'summary': item,  # Event title
                        'description': 'Breakfast',
                        'start': {
                            'dateTime': start_time,
                            'timeZone': timezone,  # Adjust to your timezone
                        },
                        'end': {
                            'dateTime': end_time,
                            'timeZone': timezone,
                        },
                    }
                    
                    # Insert into food calendar
                    event_result = calendar_service.events().insert(
                        calendarId=food_calendar_id,
                        body=event
                    ).execute()
                    
                    log(f"Calendar event created: {event_result.get('htmlLink')}")
                    tasks['due'] = bduedatetime.isoformat() + 'Z'
                    log(f"Breakfast due date: {tasks['due']}")
            # Add breakfast to google calendar
            # tasks['title'] is the breakfast item
            # tasks['due'] is in this format: 2025-12-06T20:00:00Z
    # other daily stuff
    


def main():
    getopts = optsfunc()
    if getopts.v:
        global VERBOSE
        VERBOSE = True
    log(f"Reading file: {getopts.file}")
    data = readtheweek(getopts.file)
    taskdict = parsetheweek(data)
    createtask(getopts.credsfile, taskdict)


if __name__ == '__main__':
    main()
