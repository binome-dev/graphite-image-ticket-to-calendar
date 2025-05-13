import os
import base64
import uuid
import json

from assistant.image_to_calendr_hitl import ImageToCalendarHITL
from assistant.additional_functions import AskUserTool
from grafi.common.models.execution_context import ExecutionContext
from grafi.common.models.message import Message
from pydantic import BaseModel

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File
from fastapi import Body


openai_key = os.getenv("OPENAI_KEY", "")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_execution_context(conversation_id: str = None):
    return ExecutionContext(
        conversation_id=conversation_id or uuid.uuid4().hex,
        execution_id=uuid.uuid4().hex,
        assistant_request_id=uuid.uuid4().hex,
    )

event_extraction_system_message = """
You are an AI assistant tasked with extracting event information from an image.

Return **only a valid JSON object** containing:

- title (e.g., "Music Night")
- date (format: YYYY-MM-DD, assume 2025 if year missing)
- start_time (format: HH:MM, 24-hour)
- end_time (optional, format: HH:MM)
- location (venue or address)

If any field is missing or unclear, use an empty string (""). DO NOT make up values.

Output must be JSON only — no markdown, no bullet points, no text, no formatting, no explanation.

Example:
{
  "title": "Music Night",
  "date": "2025-01-06",
  "start_time": "18:00",
  "end_time": "",
  "location": "Goodsound Club, 132 Main St, Newcity"
}
"""


action_llm_system_message = """

You are an intelligent event-processing assistant.

You are given partial or complete structured event information. Your job is to decide what to do next.

- If ALL required fields are present and valid (`title`, `date`, `start_time`, and `location`), call the `add_event_to_calendar` function using the event data as arguments.
- If ANY required field is missing, empty, or clearly incomplete, call the `ask_user` function.

Call `ask_user` with two arguments:
1. `missing_fields`: a list of missing or invalid field names such as `["start_time", "location"]`.
2. `extracted_data`: the partial event dictionary you received.

DO NOT assume or make up any values. Only call `add_event_to_calendar` if everything is complete.

You must always use a tool call — either `add_event_to_calendar` or `ask_user`. Do not respond with plain text.

Required fields:
- `title`: name of the event (e.g., "Team Meeting")
- `date`: a valid date in ISO format (e.g., "2025-02-20")
- `start_time`: in HH:MM format
- `location`: a known venue or place

Note: `end_time` is optional. If missing, do not ask for it — the calendar will use a default duration.

"""

summary_llm_system_message = """
You are an AI assistant that confirms the successful creation of a calendar event. 
Your task is to provide the user with a clear and concise summary of the event that was added.

Include all key details in the summary: title, date, time, and location.
Make sure the summary is friendly, easy to understand, and reaffirms the event was added successfully.
"""


def encode_image_as_base64(image_path: str):
    mime_type = "image/png" if image_path.endswith(".png") else "image/jpeg"
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"

def test_image_calendar_agent():
    assistant = (
        ImageToCalendarHITL.Builder()
        .api_key(openai_key)
        .event_extraction_system_message(event_extraction_system_message)
        .action_llm_system_message(action_llm_system_message)
        .summary_llm_system_message(summary_llm_system_message)
        .hitl_request(
            AskUserTool.Builder().name("ask_user").function(AskUserTool.ask_user).build()
        )
        .model("gpt-4o")
        .build()
    )

    image_path = input("Path to event image (JPG/PNG): ").strip()
    if not os.path.isfile(image_path):
        print("File not found.")
        return

    conversation_id = uuid.uuid4().hex
    execution_context = get_execution_context(conversation_id)
    image_b64 = encode_image_as_base64(image_path)

    input_data = [
        Message(
            role="user",
            content=[
                {"type": "text", "text": "Extract event details as per your instructions"},
                {"type": "image_url", "image_url": {"url": image_b64}},
            ],
        )
    ]

    while True:
        output = assistant.execute(execution_context, input_data)
        if not output:
            print("No response.")
            return

        msg = output[0]

        # Case: HITL triggered → ask_user tool call
        if msg.tool_calls and msg.tool_calls[0].function.name == "ask_user":
            args = msg.tool_calls[0].function.arguments
            missing_fields = args.get("missing_fields", [])
            extracted_data = args.get("extracted_data", {})

            print(f"Assistant: Please provide: {', '.join(missing_fields)}")
            user_reply = input("You: ")

            input_data = [
                Message(
                    role="user",
                    content=user_reply,
                    annotations=[{
                        "type": "extracted_event",
                        "value": extracted_data
                    }]
                )
            ]
            continue

        # Case: Success message
        if isinstance(msg.content, str) and "event" in msg.content.lower() and "added" in msg.content.lower():
            print("Assistant:", msg.content)
            print("✅ Event successfully created.")
            return

        # Fallback (e.g., clarification question not via tool_call)
        print("Assistant:", msg.content)
        user_reply = input("You: ")
        input_data = [Message(role="user", content=user_reply)]

assistant = (
    ImageToCalendarHITL.Builder()
    .api_key(openai_key)
    .event_extraction_system_message(event_extraction_system_message)
    .action_llm_system_message(action_llm_system_message)
    .summary_llm_system_message(summary_llm_system_message)
    .hitl_request(
        AskUserTool.Builder().name("ask_user").function(AskUserTool.ask_user).build()
    )
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
    extracted_data: dict | None = None 


@app.post("/message/")
async def message(req: MessageRequest):
    annotations = []
    if req.extracted_data:
        annotations = [{
            "type": "extracted_event",
            "value": req.extracted_data
        }]

    user_message = Message(
        role="user",
        content=req.message,
        annotations=annotations
    )

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
