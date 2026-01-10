# This will be a page that receives input from a user, then runs a function with the input and puts in the users google call.
# When the page loads, the users is asked to choose between:
# Food
# Activity
#
# Food:
# User will have  the options to input:
# breakfast
# lunch
# snack
# dinner
# dessert
# 
# none are required, they are just deleverd to the “putitonthecalfunc()”
# the user has the option to choose what day the meals are for. 
# they are stack vertically
# all meals are shown
# 
# 
# for the Activity page
# they are asked for:
# what it is
# what day it is
# what time it is
# how long
# or is it all-day
# the user has the option to choose what day the activity is for.

import gradio as gr
from datetime import datetime

def putitonthecalfunc(event_type, data):
    """
    Placeholder for Google Calendar integration
    
    event_type: "food" or "activity"
    data: dict with event details
    """
    print(f"Event Type: {event_type}")
    print(f"Data: {data}")
    return f"Calendar event created: {event_type}\n{data}"

def submit_food(day, breakfast, lunch, snack, dinner, dessert):
    """Process food entry"""
    meals = {}
    if breakfast: meals["breakfast"] = breakfast
    if lunch: meals["lunch"] = lunch
    if snack: meals["snack"] = snack
    if dinner: meals["dinner"] = dinner
    if dessert: meals["dessert"] = dessert
    
    if not meals:
        return "No meals specified. Calendar remains hunger-free."
    
    event_data = {
        "date": day,
        "meals": meals
    }
    
    result = putitonthecalfunc("food", event_data)
    return result

def submit_activity(day, name, time, duration, is_allday):
    """Process activity entry"""
    if not name:
        return "Activity name required. Even 'Existential Pondering' counts."
    
    event_data = {
        "date": day,
        "name": name,
        "all_day": is_allday
    }
    
    if not is_allday:
        event_data["time"] = time if time else "00:00"
        event_data["duration"] = duration if duration else "1h"
    
    result = putitonthecalfunc("activity", event_data)
    return result

# Build the interface
with gr.Blocks(title="Calendar Entry System") as app:
    gr.Markdown("# Calendar Event Creator")
    
    with gr.Tabs():
        # FOOD TAB
        with gr.TabItem("Food"):
            day_food = gr.DateTime(
                include_time=False,
                label="Select Day",
                value=datetime.now().strftime('%Y-%m-%d'),
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
            day_activity = gr.Textbox(
                label="Day (YYYY-MM-DD)",
                value=datetime.now().strftime("%Y-%m-%d")
            )
            
            activity_name = gr.Textbox(label="Activity")
            activity_time = gr.Textbox(label="Time (HH:MM)", placeholder="14:30")
            activity_duration = gr.Textbox(label="Duration", placeholder="2h")
            activity_allday = gr.Checkbox(label="All-Day Event")
            
            activity_submit = gr.Button("Add to Calendar", variant="primary")
            activity_output = gr.Textbox(label="Result", interactive=False)
            
            activity_submit.click(
                fn=submit_activity,
                inputs=[day_activity, activity_name, activity_time, activity_duration, activity_allday],
                outputs=activity_output
            )

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860)