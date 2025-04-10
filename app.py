import os
import uuid
import base64
import json

from google_auth_oauthlib.flow import Flow
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from fastapi.responses import RedirectResponse
from fastapi import Request
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File


from assistant.image_to_calendar_agent import ImageToCalendar
from grafi.common.models.execution_context import ExecutionContext
from grafi.common.models.message import Message 


GOOGLE_CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]
REDIRECT_URI = "http://localhost:8000/oauth2callback"


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
Your task is to analyze the image and return all relevant event details, including:

- title
- date (in YYYY-MM-DD format)
- start_time (in HH:MM, 24-hour format)
- end_time (in HH:MM, 24-hour format, optional if not present)
- location

Return the result in this exact JSON structure:

{
  "title": "Event Title",
  "date": "YYYY-MM-DD",
  "start_time": "HH:MM",
  "end_time": "HH:MM",
  "location": "Event Location"
}

If the end time isn't specified, you can omit it or leave it as null.
"""

action_llm_system_message = """
You are an AI assistant responsible for analyzing extracted event information and determining whether it is complete. 
If any required fields (title, date, time, location) are missing or unclear, call the function `ask_user` to request clarification.

- When calling `ask_user`, always include:
  - `missing_fields`: a list of the missing field names
  - `extracted_data`: a dictionary containing the event fields that were successfully extracted

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

# @app.get("/test-local/{filename}")
def test_local(filename: str):
    image_path = f"test_images/{filename}"

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")


    input_data = [
        Message(
            content=[
                {"type": "text", "text": "Extract important info as per your instructions"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}",
                    },
                },
            ],
            role="user",
        )
    ]

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

test_local("test_image_2.jpg")

@app.post("/test-upload/")
async def test_upload(file: UploadFile = File(...)):
    
    image_bytes = await file.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    

    mime_type = file.content_type  # It would make more sense not to hardcode the type as different users will have different image types
    
    input_data = [
        Message(
            content=[
                {"type": "text", "text": "Extract important info as per your instructions"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{image_base64}",
                    },
                },
            ],
            role="user",
        )
    ]
    
    execution_context = ExecutionContext(
        conversation_id=uuid.uuid4().hex,
        assistant_request_id=uuid.uuid4().hex,
        execution_id=uuid.uuid4().hex,
    )
    
    output = assistant.execute(execution_context, input_data)
    
    # output = await assistant.execute(execution_context, input_data)
    
    return {
        "execution_context": execution_context.model_dump(),
        "response": output[0].content
    }


