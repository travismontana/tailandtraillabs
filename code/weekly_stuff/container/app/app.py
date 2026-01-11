# This will be a page that receives input from a user, then runs a function with the input and puts in the users google call.
# When the page loads, the users is asked to choose between:
# Food
# Activity
#
# Food:
# User will have the options to input:
# breakfast
# lunch
# snack
# dinner
# dessert
# 
# none are required, they are just delivered to the "putitonthecalfunc()"
# the user has the option to choose what day the meals are for. 
# they are stack vertically
# all meals are shown
# 
# 
# for the Activity page
# they are asked for:
# start day/time
# end time within 4 hours of the start time
# the time select is in 15 min increments
# then the activity itself

import logging
import warnings
import gradio as gr
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
with gr.Blocks(analytics_enabled=False) as demo:
    pass  # Placeholder to avoid Gradio initialization issues
warnings.filterwarnings('ignore')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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

STEP_MINUTES = 15
MAX_HOURS = 4
TZ = ZoneInfo('America/Chicago')

def get_next_15min_increment():
    """Get the next 15-minute increment from current time."""
    now = datetime.now(TZ)
    minutes = now.minute
    next_quarter = ((minutes // STEP_MINUTES) + 1) * STEP_MINUTES
    
    if next_quarter >= 60:
        next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        next_time = now.replace(minute=next_quarter, second=0, microsecond=0)
    
    logger.info(f"Page load time: {now.strftime('%H:%M')}, next 15-min increment: {next_time.strftime('%H:%M')}")
    return next_time

def get_time_options():
    """Generate hour and minute dropdown options."""
    hours = [f"{h:02d}" for h in range(24)]
    minutes = ["00", "15", "30", "45"]
    return hours, minutes

def get_end_time_choices(day, start_hour, start_min):
    """
    Generate valid end time choices (hour/minute) based on start time.
    Returns: (end_hour_choices, end_minute_choices)
    """
    if not all([day, start_hour, start_min]):
        logger.debug("Missing start time components, returning all choices")
        return get_time_options()
    
    try:
        day_dt = datetime.fromtimestamp(float(day), tz=TZ)
        start_dt = day_dt.replace(
            hour=int(start_hour),
            minute=int(start_min),
            second=0,
            microsecond=0
        )
        
        # Generate all valid end times (start + 15min to start + 4h)
        min_end = start_dt + timedelta(minutes=15)
        max_end = start_dt + timedelta(hours=MAX_HOURS)
        
        valid_times = []
        current = min_end
        while current <= max_end:
            valid_times.append(current)
            current += timedelta(minutes=15)
        
        # Extract unique hours and minutes
        valid_hours_set = set()
        valid_minutes_by_hour = {}
        
        for dt in valid_times:
            hour_str = f"{dt.hour:02d}"
            min_str = f"{dt.minute:02d}"
            valid_hours_set.add(hour_str)
            
            if hour_str not in valid_minutes_by_hour:
                valid_minutes_by_hour[hour_str] = set()
            valid_minutes_by_hour[hour_str].add(min_str)
        
        valid_hours = sorted(list(valid_hours_set))
        
        logger.debug(f"Valid end hours: {valid_hours}")
        
        # For minutes, return all since they depend on selected hour
        # Validation will catch invalid combinations
        return valid_hours, ["00", "15", "30", "45"]
        
    except Exception as e:
        logger.error(f"Error generating end time choices: {e}")
        return get_time_options()

def calculate_default_end_time(day, start_hour, start_min):
    """
    Calculate default end time (start + 30 minutes).
    Returns: (end_hour, end_minute, status_message)
    """
    if not all([day, start_hour, start_min]):
        logger.debug("Missing start time, no default end calculated")
        return None, None, "Select start time first"
    
    try:
        day_dt = datetime.fromtimestamp(float(day), tz=TZ)
        start_dt = day_dt.replace(
            hour=int(start_hour),
            minute=int(start_min),
            second=0,
            microsecond=0
        )
        
        end_dt = start_dt + timedelta(minutes=30)
        
        end_hour = f"{end_dt.hour:02d}"
        end_min = f"{end_dt.minute:02d}"
        
        msg = f"Start: {start_dt.strftime('%H:%M')} → End: {end_dt.strftime('%H:%M')} (30 min)"
        logger.info(f"Auto-calculated end time: {msg}")
        
        return end_hour, end_min, msg
        
    except Exception as e:
        logger.error(f"Error calculating default end time: {e}")
        return None, None, f"Error: {e}"

def validate_activity_time(day, start_hour, start_min, end_hour, end_min):
    """
    Validate activity time selection.
    Returns: (is_valid, message, calculated_start, calculated_end)
    """
    logger.debug(f"Validating: day={day}, start={start_hour}:{start_min}, end={end_hour}:{end_min}")
    
    if not all([day, start_hour, start_min, end_hour, end_min]):
        logger.warning("Incomplete time selection")
        return False, "All time fields required", None, None
    
    try:
        # Parse the day (comes as timestamp from gr.DateTime)
        day_dt = datetime.fromtimestamp(float(day), tz=TZ)
        
        # Build start datetime
        start_dt = day_dt.replace(
            hour=int(start_hour),
            minute=int(start_min),
            second=0,
            microsecond=0
        )
        
        # Build end datetime
        end_dt = day_dt.replace(
            hour=int(end_hour),
            minute=int(end_min),
            second=0,
            microsecond=0
        )
        
        # If end is before or equal to start, assume next day
        if end_dt <= start_dt:
            logger.info("End time <= start, assuming next day")
            end_dt += timedelta(days=1)
        
        # Check minimum duration (15 minutes)
        duration = end_dt - start_dt
        if duration < timedelta(minutes=15):
            logger.warning(f"Duration {duration} less than minimum 15 minutes")
            return False, "Duration must be at least 15 minutes", start_dt, end_dt
        
        # Check max duration
        max_duration = timedelta(hours=MAX_HOURS)
        
        if duration > max_duration:
            logger.warning(f"Duration {duration} exceeds max {max_duration}")
            return False, f"Duration {duration} exceeds maximum of {MAX_HOURS} hours", start_dt, end_dt
        
        msg = f"Valid: {start_dt.strftime('%Y-%m-%d %H:%M')} → {end_dt.strftime('%Y-%m-%d %H:%M')} ({duration})"
        logger.info(msg)
        return True, msg, start_dt, end_dt
        
    except Exception as e:
        logger.error(f"Time validation error: {e}")
        return False, f"Error validating time: {e}", None, None


def putitonthecalfunc(event_type, data):
    """
    Placeholder for Google Calendar integration

    event_type: "food" or "activity"
    data: dict with event details

    entry = {
        'summary': name,
        'description': name,
        'start': {'dateTime':  start_datetime, 'timeZone': 'America/Chicago'},
        'end': {'dateTime': start_datetime + timedelta(minutes=45), 'timeZone': 'America/Chicago'},
        }
    """
    logger.info(f"Calendar function called - Type: {event_type}")
    logger.debug(f"Event data: {data}")
    
    day_epoch = float(data['date'])
    base_date = datetime.fromtimestamp(day_epoch, tz=TZ)
    day = data['date']
    
    logger.info(f"Base date: {base_date.strftime('%Y-%m-%d')}")
    
    if event_type == "food":
        meal_count = len(data['meals'])
        logger.info(f"Processing {meal_count} meal(s) for {base_date.strftime('%Y-%m-%d')}")
        
        for k, v in data['meals'].items():
            logger.info(f"Adding {k}: '{v}' on {base_date.strftime('%Y-%m-%d')}")
            event_time = times[k]
            meal_name = v
            start_datetime = base_date.replace(
                hour=event_time.hour,
                minute=event_time.minute,
                second=event_time.second
            )
            end_datetime = start_datetime + timedelta(minutes=45)
            allin = {
                'summary': meal_name,
                'description': meal_name,
                'start': {'dateTime': start_datetime.isoformat(), 'timeZone': 'America/Chicago'},
                'end': {'dateTime': end_datetime.isoformat(), 'timeZone': 'America/Chicago'},
            }
            logger.info(f"Event details - Summary: '{meal_name}', Start: {start_datetime.isoformat()}, End: {end_datetime.isoformat()}")
            logger.debug(f"Full event payload: {allin}")
            # TODO: Actually call Google Calendar API here with allin
            
    elif event_type == "activity":
        name = data['name']
        start_dt = data['start_dt']
        end_dt = data['end_dt']
        
        duration = end_dt - start_dt
        logger.info(f"Creating activity '{name}' - {start_dt.isoformat()} → {end_dt.isoformat()} ({duration})")
        
        allin = {
            'summary': name,
            'description': name,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'America/Chicago'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'America/Chicago'},
        }
        logger.debug(f"Full event payload: {allin}")
        # TODO: Actually call Google Calendar API here with allin
        
    else:
        logger.error(f"Unknown event type: '{event_type}'")
        return "Error: Unknown event type"
    logger.info(f"Allin: {allin}")
    logger.info("Event processing complete")
    return "Success"

def submit_food(day, breakfast, lunch, snack, dinner, dessert):
    """Process food entry"""
    logger.info("Food submission initiated")
    logger.debug(f"Raw inputs - day: {day}, breakfast: {breakfast}, lunch: {lunch}, snack: {snack}, dinner: {dinner}, dessert: {dessert}")
    
    meals = {}
    if breakfast: meals["breakfast"] = breakfast
    if lunch: meals["lunch"] = lunch
    if snack: meals["snack"] = snack
    if dinner: meals["dinner"] = dinner
    if dessert: meals["dessert"] = dessert
    
    if not meals:
        logger.warning("No meals specified in food submission")
        return "No meals specified. Calendar remains hunger-free."
    
    logger.info(f"Processing {len(meals)} meal(s): {', '.join(meals.keys())}")
    
    event_data = {
        "date": day,
        "meals": meals
    }
    
    result = putitonthecalfunc("food", event_data)
    logger.info(f"Food submission result: {result}")
    return result

def submit_activity(name, day, start_hour, start_min, end_hour, end_min):
    """Process activity entry"""
    logger.info("Activity submission initiated")
    logger.debug(f"Raw inputs - name: '{name}', day: {day}, start: {start_hour}:{start_min}, end: {end_hour}:{end_min}")
    
    if not name:
        logger.warning("Activity submission missing name")
        return "Activity name required. Even 'Existential Pondering' counts."
    
    # Validate time
    is_valid, msg, start_dt, end_dt = validate_activity_time(day, start_hour, start_min, end_hour, end_min)
    
    if not is_valid:
        logger.warning(f"Activity validation failed: {msg}")
        return f"Validation failed: {msg}"
    
    event_data = {
        'name': name,
        'start_dt': start_dt,
        'end_dt': end_dt,
        'date': day
    }
    
    result = putitonthecalfunc("activity", event_data)
    
    result_msg = f"Success: '{name}' scheduled for {start_dt.strftime('%Y-%m-%d %H:%M')} - {end_dt.strftime('%H:%M')}"
    logger.info(f"Activity submission complete: {result_msg}")
    return result_msg

# Build the interface
logger.info("Building Gradio interface")

# Calculate initial time values
next_time = get_next_15min_increment()
default_start_hour = f"{next_time.hour:02d}"
default_start_min = f"{next_time.minute:02d}"
default_end_time = next_time + timedelta(minutes=30)
default_end_hour = f"{default_end_time.hour:02d}"
default_end_min = f"{default_end_time.minute:02d}"

hours, minutes = get_time_options()

with gr.Blocks(title="Calendar Entry System",analytics_enabled=False) as app:
    gr.Markdown("# Calendar Event Creator")
    
    with gr.Tabs():
        # FOOD TAB
        with gr.TabItem("Food"):
            day_food = gr.DateTime(
                include_time=False,
                label="Select Day",
                value=datetime.now(TZ).strftime('%Y-%m-%d'),
                interactive=True
            )
            
            breakfast = gr.Textbox(label="Breakfast")
            lunch = gr.Textbox(label="Lunch")
            snack = gr.Textbox(label="Snack")
            dinner = gr.Textbox(label="Dinner")
            dessert = gr.Textbox(label="Dessert")
            
            food_submit = gr.Button("Add to Calendar", variant="primary")
            food_output = gr.Textbox(label="Result", interactive=False)
            
            food_submit.click(
                fn=submit_food,
                inputs=[day_food, breakfast, lunch, snack, dinner, dessert],
                outputs=food_output
            )
        
        # ACTIVITY TAB
        with gr.TabItem("Activity"):
            
            activity_name = gr.Textbox(label="Activity")
            
            day_activity = gr.DateTime(
                include_time=False,
                label="Select Day",
                value=datetime.now(TZ).strftime('%Y-%m-%d'),
                interactive=True
            )
            
            gr.Markdown("### Start Time")
            with gr.Row():
                start_hour = gr.Dropdown(
                    choices=hours,
                    value=default_start_hour,
                    label="Hour",
                    interactive=True
                )
                start_min = gr.Dropdown(
                    choices=minutes,
                    value=default_start_min,
                    label="Minute",
                    interactive=True
                )
            
            gr.Markdown("### End Time (max 4 hours from start)")
            with gr.Row():
                end_hour = gr.Dropdown(
                    choices=hours,
                    value=default_end_hour,
                    label="Hour",
                    interactive=True
                )
                end_min = gr.Dropdown(
                    choices=minutes,
                    value=default_end_min,
                    label="Minute",
                    interactive=True
                )
            
            status = gr.Textbox(label="Status", interactive=False)
            
            # Auto-update end time when start time changes
            def update_end_time(day, sh, sm):
                eh, em, msg = calculate_default_end_time(day, sh, sm)
                # Also get validation message
                if eh and em:
                    _, val_msg, _, _ = validate_activity_time(day, sh, sm, eh, em)
                    return eh, em, val_msg
                return eh, em, msg
            
            # When start time changes, auto-set end time to start + 30min
            for component in [day_activity, start_hour, start_min]:
                component.change(
                    fn=update_end_time,
                    inputs=[day_activity, start_hour, start_min],
                    outputs=[end_hour, end_min, status]
                )
            
            # Validate whenever end time changes manually
            for component in [end_hour, end_min]:
                component.change(
                    fn=lambda d, sh, sm, eh, em: validate_activity_time(d, sh, sm, eh, em)[1],
                    inputs=[day_activity, start_hour, start_min, end_hour, end_min],
                    outputs=status
                )
            
            activity_submit = gr.Button("Add to Calendar", variant="primary")
            activity_output = gr.Textbox(label="Result", interactive=False)
            
            activity_submit.click(
                fn=submit_activity,
                inputs=[activity_name, day_activity, start_hour, start_min, end_hour, end_min],
                outputs=activity_output
            )

if __name__ == "__main__":
    logger.info("Launching Gradio application on 0.0.0.0:7860")
    app.launch(server_name="0.0.0.0", server_port=7860)