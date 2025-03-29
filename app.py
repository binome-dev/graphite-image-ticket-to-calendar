import os
import uuid
import base64

from fastapi import FastAPI
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
    .model("gpt-4o-mini")
    .build()
)


@app.get("/")
def root():
    return {"message": "Image-to-calendar AI agent is running!"}


#This is just for testing purposes, in reality the image will be receiced as a POST request which will be done after the intial testing

@app.get("/test-local")
def test_local():
    image_path = "test_image.png"  # replace with your test image path

  
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    image_data_url = f"data:image/png;base64,{image_base64}"

  
    image_block = {
        "type": "image_url",
        "image_url": {
            "url": image_data_url
        }
    }


    execution_context = ExecutionContext(
        conversation_id=uuid.uuid4().hex,
        assistant_request_id=uuid.uuid4().hex,
        execution_id=uuid.uuid4().hex,
    )


    input_data = [
        Message(
            role="user",
            content=[
                {"type": "text", "text": "Please extract event details from this image."},
                image_block
            ]
        )
    ]

    output = assistant.execute(execution_context, input_data)

    return {
        "execution_context": execution_context.model_dump(),
        "response": output[0].content,
    }