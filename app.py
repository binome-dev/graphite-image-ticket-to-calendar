import os
import uuid
import base64
import json

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from assistant.image_to_calendar_agent import ImageToCalendar
from grafi.common.models.execution_context import ExecutionContext
from grafi.common.models.message import Message 




openai_key = os.getenv("OPENAI_KEY")

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)


event_extraction_system_message = """
You are an AI assistant responsible for extracting calendar event information from uploaded images. 
Your task is to analyze the image and return all relevant event details, including the title, date, time, and location.

This is the JSON format I expect:

{
  "title": "Event Title",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "location": "Event Location"
}

Ensure the data is structured clearly and consistently in this format.
"""


action_llm_system_message = """
You are an AI assistant responsible for analyzing extracted event information and determining whether it is complete. 
If any required fields (title, date, time, location) are missing or unclear, call the function `ask_user` to request clarification. 
If the information is sufficient, call the function `add_event_to_calendar` to proceed with saving the event.
"""

observation_llm_system_message = """
You are an AI assistant that interprets user responses to previously requested missing event details. 
Your task is to integrate the new information with the existing data to form a complete event entry.

Ensure all required fields (title, date, time, location) are now present and clearly understood. 
If the data is sufficient, call the function `add_event_to_calendar` to proceed with saving the event.
If information is still missing or unclear, call the function `ask_user` again to request clarification.
"""


summary_llm_system_message = """
You are an AI assistant that confirms the successful creation of a calendar event. 
Your task is to provide the user with a clear and concise summary of the event that was added.

Include all key details in the summary: title, date, time, and location.
Make sure the summary is friendly, easy to understand, and reaffirms the event was added successfully.
"""


assistant = (
    ImageToCalendar.Builder()
    .api_key(openai_key) 
    .event_extraction_system_message(event_extraction_system_message)
    .action_llm_system_message(action_llm_system_message)
    .observation_llm_system_message(observation_llm_system_message)
    .summary_llm_system_message(summary_llm_system_message)
    .model("gpt-4o")
    .build()
)


@app.get("/")
def root():
    return {"message": "Image-to-calendar AI agent is running!"}


@app.get("/test-local/{filename}")
def test_local(filename: str):
    image_path = f"test_images/{filename}"


    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")


    message1 = Message(
    role="user",
    content=f"data:image/jpeg;base64,{image_base64}")

    #message2 = Message(
     #   role="user",
     #   content="Extract the information from the image as per instructions"
   # )


    input_data = [message1]

    execution_context = ExecutionContext(
        conversation_id=uuid.uuid4().hex,
        assistant_request_id=uuid.uuid4().hex,
        execution_id=uuid.uuid4().hex,
    )


    output = assistant.execute(execution_context, input_data)


    return {
        "execution_context": execution_context.model_dump(),
        "response": output[0].content
    }