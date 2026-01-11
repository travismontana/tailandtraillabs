# Brain to calendar - web service.

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
# start day/time
# end time within 4 hours of the start time
# the time select is in 15 min increments
#
# Using: gradio
# Needs from env: 
# CALENDER_ID="bomar.us_t22bmj6saugbq00etnmorqr3ug@group.calendar.google.com"
#
# Date time picker, can not pick more than 4 hours.  selects in 15 min intervals.