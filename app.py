import base64
import os
import uuid


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File
from fastapi import Body


from assistant.image_to_calendar_agent import ImageToCalendar
from assistant.additional_functions import *
from grafi.common.models.execution_context import ExecutionContext
from grafi.common.models.message import Message

from assistant.image_to_calendar_agent import ImageToCalendar
from pydantic import BaseModel



openai_key = os.getenv("OPENAI_KEY", "")

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

If the year is not explicitly mentioned in the date, assume the current year.

Return the result in this exact JSON structure:

{
  "title": "Event Title",
  "date": "YYYY-MM-DD",
  "start_time": "HH:MM",
  "end_time": "HH:MM",
  "location": "Event Location"
}

If the year is not specified, assume the year is 2025.
"""

action_llm_system_message = """
You are an AI assistant responsible for analyzing extracted event information and determining whether it is complete.

Required event fields are:
- title
- date (in YYYY-MM-DD format)
- start_time (in HH:MM, 24-hour format)
- location

Optional: end_time (can be omitted if not provided)

---

If any required field is missing or unclear, call the function `ask_user`.

When calling `ask_user`, you MUST include:

1. `missing_fields`: a list of the missing or unclear fields (e.g. ["start_time", "location"])
2. `extracted_data`: a dictionary containing ALL the successfully extracted fields, even if the event is incomplete.

Example function call:
```json
{
  "function": {
    "name": "ask_user",
    "arguments": {
      "missing_fields": ["location", "start_time"],
      "extracted_data": {
        "title": "Team Meeting",
        "date": "2025-05-07"
      }
    }
  }
}

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


@app.post("/upload/")
async def upload(file: UploadFile = File(...)):

    conversation_id = uuid.uuid4().hex  

    image_bytes = await file.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    mime_type = file.content_type

    input_data = [
        Message(
            role="user",
            content=[
                {"type": "text", "text": "Extract important info as per your instructions"},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
            ],
        )
    ]

    execution_context = ExecutionContext(
        conversation_id=conversation_id,
        execution_id=uuid.uuid4().hex,
        assistant_request_id=uuid.uuid4().hex,
    )

    output = assistant.execute(execution_context, input_data)

    return {
        "conversation_id": conversation_id,  
        "execution_context": execution_context.model_dump(),
        "response": output[0].content
    }


class MessageRequest(BaseModel):
    message: str
    conversation_id: str 


@app.post("/message/")
async def message(req: MessageRequest):
    user_message = Message(role="user", content=req.message)

    execution_context = ExecutionContext(
        conversation_id=req.conversation_id,  
        execution_id=uuid.uuid4().hex,
        assistant_request_id=uuid.uuid4().hex,
    )

    output = assistant.execute(execution_context, [user_message])

    return {
        "execution_context": execution_context.model_dump(),
        "response": output[0].content
    }