import json
from grafi.tools.functions.function_tool import FunctionTool
from grafi.common.decorators.llm_function import llm_function


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



        result = {
            "status": "success",
            "event": {
                "title": event_title,
                "date": event_date,
                "start_time": start_time,
                "end_time": end_time,
                "location": location
            }
        }

        return json.dumps(result)
