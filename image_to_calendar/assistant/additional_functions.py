import json
from grafi.tools.functions.function_tool import FunctionTool
from grafi.common.decorators.llm_function import llm_function


class AskUserTool(FunctionTool):

    @llm_function
    def ask_user(self, missing_fields: list[str], extracted_data: dict) -> str:
        
        "This function was designed to handle missing data, say one of: date/time/location/title is missing, it will request more info on the missing one"

        question_parts = []

        for field in missing_fields:
            question_parts.append(f"Please provide the event's {field.replace('_', ' ')}.")

        question = " ".join(question_parts)

        return json.dumps({"question_description": question})

class CalendarTool(FunctionTool):

    @llm_function
    def add_event_to_calendar(self, event_title: str, event_date: str, 
        start_time: str = None,
        end_time: str = None,
        location: str = None
    ) -> str:

        result = {"status": "success",
        "event": 
            {
                "title": event_title,
                "date": event_date,
                "start_time": start_time,
                "end_time": end_time,
                "location": location
            }
        }

        return json.dumps(result)