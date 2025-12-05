#!/usr/bin/env python3
"""
Weekly Plan Sync - Syncs markdown weekly plans to Google Calendar, Keep, and Tasks
"""
import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path
import pickle

# Google Calendar and Tasks
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Google Keep
import gkeepapi

# Scopes for Google APIs
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/tasks'
]

def parse_markdown(file_path):
    """Parse the weekly planning markdown file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Structure to hold parsed data
    week_data = {}
    current_day = None
    current_section = None
    
    lines = content.split('\n')
    
    for line in lines:
        # Match day headers like "Monday:" or "Tuesday:"
        day_match = re.match(r'^(Monday|Tuesday|Wed(?:nesday)?|Thursday|Friday|Saturday|Sunday):\s*$', line.strip())
        if day_match:
            day_name = day_match.group(1)
            # Normalize "Wed" to "Wednesday"
            if day_name == "Wed":
                day_name = "Wednesday"
            current_day = day_name
            week_data[current_day] = {
                'Breakfast': None,
                'Lunch': None,
                'Dinner': None,
                'Snacks': None,
                'GroceryShopping': [],
                'Things': []
            }
            current_section = None
            continue
        
        if current_day is None:
            continue
        
        # Match section headers with times like "Breakfast (7:30am):" or just "Breakfast:"
        if re.match(r'\s*Breakfast', line, re.IGNORECASE):
            current_section = 'Breakfast'
            # Extract meal if on same line (after the colon)
            meal_match = re.search(r':\s*(.+)', line)
            if meal_match and meal_match.group(1).strip():
                week_data[current_day]['Breakfast'] = meal_match.group(1).strip()
        elif re.match(r'\s*Lunch', line, re.IGNORECASE):
            current_section = 'Lunch'
            meal_match = re.search(r':\s*(.+)', line)
            if meal_match and meal_match.group(1).strip():
                week_data[current_day]['Lunch'] = meal_match.group(1).strip()
        elif re.match(r'\s*Dinner', line, re.IGNORECASE):
            current_section = 'Dinner'
            meal_match = re.search(r':\s*(.+)', line)
            if meal_match and meal_match.group(1).strip():
                week_data[current_day]['Dinner'] = meal_match.group(1).strip()
        elif re.match(r'\s*Snacks', line, re.IGNORECASE):
            current_section = 'Snacks'
            meal_match = re.search(r':\s*(.+)', line)
            if meal_match and meal_match.group(1).strip():
                week_data[current_day]['Snacks'] = meal_match.group(1).strip()
        elif re.match(r'\s*GroceryShopping:', line, re.IGNORECASE):
            current_section = 'GroceryShopping'
        elif re.match(r'\s*Things:', line, re.IGNORECASE):
            current_section = 'Things'
        # Match list items (lines starting with -)
        elif line.strip().startswith('-'):
            item = line.strip()[1:].strip()
            if current_section == 'GroceryShopping':
                week_data[current_day]['GroceryShopping'].append(item)
            elif current_section == 'Things':
                week_data[current_day]['Things'].append(item)
        # Handle content on lines following meal headers (indented or not)
        elif line.strip() and current_section in ['Breakfast', 'Lunch', 'Dinner', 'Snacks']:
            # Skip if it looks like a sub-section header
            if not any(line.strip().startswith(x) for x in ['GroceryShopping:', 'Things:']):
                if week_data[current_day][current_section] is None:
                    week_data[current_day][current_section] = line.strip()
                else:
                    week_data[current_day][current_section] += ' ' + line.strip()
    
    return week_data

def get_google_creds(creds_file):
    """Get Google OAuth credentials."""
    creds = None
    token_file = 'token.pickle'
    
    # Load saved credentials
    if Path(token_file).exists():
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    
    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def get_calendar_id(service, calendar_name):
    """Get the calendar ID for a given calendar name."""
    calendar_list = service.calendarList().list().execute()
    
    for calendar in calendar_list.get('items', []):
        if calendar['summary'] == calendar_name:
            return calendar['id']
    
    return None

def get_task_list_id(service, list_name):
    """Get the task list ID for a given list name, create if doesn't exist."""
    task_lists = service.tasklists().list().execute()
    
    for task_list in task_lists.get('items', []):
        if task_list['title'] == list_name:
            return task_list['id']
    
    # Create if doesn't exist
    new_list = service.tasklists().insert(body={'title': list_name}).execute()
    print(f"Created new task list: {list_name}")
    return new_list['id']

def get_monday_of_week(file_path):
    """Determine the Monday of the week - uses next Monday from today."""
    today = datetime.now().date()
    
    # Calculate days until next Monday (0 = Monday, 6 = Sunday)
    days_until_monday = (7 - today.weekday()) % 7
    
    # If today is Monday, use today; otherwise use next Monday
    if today.weekday() == 0:
        return today
    elif days_until_monday == 0:
        return today + timedelta(days=7)
    else:
        return today + timedelta(days=days_until_monday)

def add_meals_to_calendar(service, calendar_id, week_data, start_date):
    """Add meals to Google Calendar."""
    day_offset = {
        'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
        'Friday': 4, 'Saturday': 5, 'Sunday': 6
    }
    
    meal_times = {
        'Breakfast': '07:30',
        'Lunch': '11:30',
        'Dinner': '18:30',
        'Snacks': '15:00'
    }
    
    for day, data in week_data.items():
        if day not in day_offset:
            continue
            
        day_date = start_date + timedelta(days=day_offset[day])
        
        for meal_type, meal_time in meal_times.items():
            meal_content = data.get(meal_type)
            if meal_content:
                hour, minute = map(int, meal_time.split(':'))
                start_datetime = datetime.combine(day_date, datetime.min.time().replace(hour=hour, minute=minute))
                end_datetime = start_datetime + timedelta(hours=1)
                
                event = {
                    'summary': f'{meal_type}: {meal_content}',
                    'start': {
                        'dateTime': start_datetime.isoformat(),
                        'timeZone': 'America/Chicago',
                    },
                    'end': {
                        'dateTime': end_datetime.isoformat(),
                        'timeZone': 'America/Chicago',
                    },
                }
                
                service.events().insert(calendarId=calendar_id, body=event).execute()
                print(f"  ✓ {day} {meal_type}: {meal_content}")

def add_to_shopping_list(keep, week_data):
    """Add grocery items to Google Keep shopping list."""
    # Find or create shopping list
    shopping_list = None
    for note in keep.all():
        if note.title == 'Shopping List':
            shopping_list = note
            break
    
    if shopping_list is None:
        shopping_list = keep.createList('Shopping List')
        print("  Created new 'Shopping List' in Google Keep")
    
    # Collect all grocery items from all days
    all_items = []
    for day, data in week_data.items():
        all_items.extend(data['GroceryShopping'])
    
    # Add items to list
    for item in all_items:
        shopping_list.add(item, False)  # False = not checked
        print(f"  ✓ {item}")
    
    keep.sync()

def add_tasks(service, task_list_id, week_data):
    """Add things to Google Tasks."""
    all_tasks = set()  # Use set to avoid duplicates
    
    for day, data in week_data.items():
        for thing in data['Things']:
            all_tasks.add(thing)
    
    # Add each unique task
    for task_title in all_tasks:
        task = {'title': task_title}
        service.tasks().insert(tasklist=task_list_id, body=task).execute()
        print(f"  ✓ {task_title}")

def main():
    parser = argparse.ArgumentParser(
        description='Sync weekly plan markdown to Google Calendar, Keep, and Tasks'
    )
    parser.add_argument('markdown_file', help='Path to the weekly plan markdown file')
    parser.add_argument('--google-creds', required=True, 
                       help='Path to Google OAuth credentials JSON file')
    parser.add_argument('--keep-user', required=True, 
                       help='Google Keep username/email')
    parser.add_argument('--keep-pass', required=True, 
                       help='Google Keep password or app password')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Weekly Plan Sync")
    print("=" * 60)
    
    # Parse the markdown file
    print("\n📄 Parsing markdown file...")
    week_data = parse_markdown(args.markdown_file)
    print(f"   Found {len(week_data)} days")
    
    # Get Google credentials
    print("\n🔐 Authenticating with Google...")
    google_creds = get_google_creds(args.google_creds)
    
    # Build services
    calendar_service = build('calendar', 'v3', credentials=google_creds)
    tasks_service = build('tasks', 'v1', credentials=google_creds)
    
    # Get calendar and task list IDs
    print("\n🔍 Finding 'Food' calendar...")
    food_calendar_id = get_calendar_id(calendar_service, 'Food')
    if not food_calendar_id:
        print("   ❌ ERROR: 'Food' calendar not found! Please create it first.")
        return
    print("   ✓ Found Food calendar")
    
    print("\n🔍 Finding/creating 'Stuff to do' task list...")
    task_list_id = get_task_list_id(tasks_service, 'Stuff to do')
    print("   ✓ Ready")
    
    # Determine the start date (Monday of the week)
    start_date = get_monday_of_week(args.markdown_file)
    print(f"\n📅 Using week starting: {start_date.strftime('%A, %B %d, %Y')}")
    
    # Add meals to calendar
    print("\n🍽️  Adding meals to calendar...")
    add_meals_to_calendar(calendar_service, food_calendar_id, week_data, start_date)
    
    # Connect to Google Keep
    print("\n📝 Connecting to Google Keep...")
    keep = gkeepapi.Keep()
    try:
        keep.login(args.keep_user, args.keep_pass)
        print("   ✓ Connected")
    except Exception as e:
        print(f"   ❌ ERROR: Failed to login to Google Keep: {e}")
        print("   💡 TIP: You may need to use an App Password instead of your regular password")
        print("      Visit: https://myaccount.google.com/apppasswords")
        return
    
    # Add to shopping list
    print("\n🛒 Adding items to shopping list...")
    add_to_shopping_list(keep, week_data)
    
    # Add tasks
    print("\n✅ Adding tasks to 'Stuff to do'...")
    add_tasks(tasks_service, task_list_id, week_data)
    
    print("\n" + "=" * 60)
    print("✨ All done! Your week is planned.")
    print("=" * 60)

if __name__ == '__main__':
    main()
