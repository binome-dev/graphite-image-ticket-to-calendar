import os
from fastapi import FastAPI
from image_to_calendar.assistant.image_to_calendar_agent import ImageToCalendar




openai_key = os.getenv("OPENAI_KEY")

#Still need to work on this

event_extraction_system_message = """
You are an AI assistant responsible for extracting calendar event information from uploaded images. 
Your task is to analyze the image and return all relevant event details, including the title, date, time, and location.
Format the information clearly in a structured JSON format.
"""

action_llm_system_message = """
You are an AI assistant responsible for analyzing extracted event information and determining whether it is complete. 
If any required fields (title, date, time, location) are missing or unclear, call the function `ask_user` to request clarification.
If the information is sufficient, call the function `add_event_to_calendar` to proceed with saving the event.
"""

observation_llm_system_message = """
You are an AI assistant that interprets user responses to previously requested missing event details. 
Your task is to integrate the new information with the existing data to form a complete event entry.
Ensure accuracy and completeness before calling the final calendar function.
"""

summary_llm_system_message = """
You are an AI assistant that confirms the successful creation of a calendar event. 
Your task is to provide the user with a clear and concise summary of the event that was added, including the title, date, time, and location.
"""




assistant = (
    ImageToCalendar.Builder()
    .api_key(openai_key) # need key
    .event_extraction_system_message(event_extraction_system_message)
    .action_llm_system_message(action_llm_system_message)
    .observation_llm_system_message(observation_llm_system_message)
    .summary_llm_system_message(summary_llm_system_message)
    .model("gpt-4o-mini")
    .build()
)
