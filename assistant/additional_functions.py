import os
import json
import datetime

from grafi.tools.functions.function_tool import FunctionTool
from grafi.common.decorators.llm_function import llm_function

from googleapiclient.discovery import build
from google.oauth2 import service_account

from dotenv import load_dotenv

load_dotenv()

calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

print("📅 Using calendar ID:", calendar_id)


class AskUserTool(FunctionTool):

    @staticmethod
    @llm_function
    def ask_user(
    *args,
    missing_fields: list[str],
    extracted_data: dict,
    **kwargs 
) -> str:
        """
        This function handles missing data (e.g. date, time, location, or title)
        and returns a natural language question asking the user for more info.
        """

        question_parts = [
            f"Please provide the event's {field.replace('_', ' ')}."
            for field in missing_fields
        ]

        question = " ".join(question_parts)

        return json.dumps({"question_description": question})

class CalendarTool(FunctionTool):

    @staticmethod
    @llm_function
    def add_event_to_calendar(
        *args,
        event_title: str,
        event_date: str,
        start_time: str = None,
        end_time: str = None,
        location: str = None,
        **kwargs
    ) -> str:
        """
        Adds an event to Google Calendar using a service account.
        """

        SERVICE_ACCOUNT_FILE = "secrets/service-account.json"
        SCOPES = ["https://www.googleapis.com/auth/calendar"]

        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build("calendar", "v3", credentials=credentials)

        if start_time:
            start_dt = f"{event_date}T{start_time}:00"
            if end_time:
                end_dt = f"{event_date}T{end_time}:00"
            else:
                start_obj = datetime.datetime.strptime(start_dt, "%Y-%m-%dT%H:%M:%S")
                end_obj = start_obj + datetime.timedelta(hours=1)
                end_dt = end_obj.strftime("%Y-%m-%dT%H:%M:%S")

            start = {"dateTime": start_dt, "timeZone": "UTC"}
            end = {"dateTime": end_dt, "timeZone": "UTC"}
        else:
            start = {"date": event_date}
            end = {"date": event_date}

        event = {
            "summary": event_title,
            "start": start,
            "end": end,
        }

        if location:
            event["location"] = location

        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()

        return json.dumps({
            "status": "success",
            "event": {
                "id": created_event.get("id"),
                "summary": created_event.get("summary"),
                "start": created_event.get("start"),
                "end": created_event.get("end"),
                "location": created_event.get("location", "")
            }
        })