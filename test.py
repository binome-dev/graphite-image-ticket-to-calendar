import os
from dotenv import load_dotenv
load_dotenv()

print("🧪 CALENDAR ID from .env:", os.getenv("GOOGLE_CALENDAR_ID"))