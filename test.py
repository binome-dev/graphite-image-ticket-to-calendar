import os
import json
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from assistant.additional_functions import CalendarTool


CLIENT_SECRETS_FILE = "credentials.json" 
SCOPES = ["https://www.googleapis.com/auth/calendar"]


flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
credentials = flow.run_local_server(port=0)


result = CalendarTool.add_event_to_calendar_v2(
    credentials=credentials,
    event_title="Test Event",
    event_date="2025-04-09",
    start_time="13:00",
    end_time="14:00",
    location="London"
)


print(json.dumps(json.loads(result), indent=2))
