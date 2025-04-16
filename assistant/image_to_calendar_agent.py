import os
from typing import Any

from grafi.assistants.assistant import Assistant
from grafi.common.topics.output_topic import agent_output_topic
from grafi.common.topics.topic import Topic, agent_input_topic
from grafi.nodes.impl.llm_function_call_node import LLMFunctionCallNode
from grafi.nodes.impl.llm_node import LLMNode
from grafi.tools.functions.function_calling_command import FunctionCallingCommand
from grafi.tools.llms.impl.openai_tool import OpenAITool
from grafi.tools.llms.llm_response_command import LLMResponseCommand
from grafi.workflows.impl.event_driven_workflow import EventDrivenWorkflow
from openinference.semconv.trace import OpenInferenceSpanKindValues
from pydantic import Field

from assistant.additional_functions import AskUserTool, CalendarTool


class ImageToCalendar(Assistant):

    ask_user: Any = Field(default=None)
    add_event_to_calendar: Any = Field(default=None)
    oi_span_type: OpenInferenceSpanKindValues = Field(
        default=OpenInferenceSpanKindValues.AGENT
    )
    name: str = Field(default="Assistant")
    type: str = Field(default="Assistant")
    api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    event_extraction_system_message: str = Field(default="")
    observation_llm_system_message: str = Field(default="")
    action_llm_system_message: str = Field(default="")
    summary_llm_system_message: str = Field(default="")
    model: str = Field(default="gpt-4o")

    class Builder(Assistant.Builder):

        def __init__(self):
            self._assistant = self._init_assistant()

        def _init_assistant(self) -> "ImageToCalendar":
            return ImageToCalendar()

        def api_key(self, api_key: str) -> "ImageToCalendar.Builder":
            self._assistant.api_key = api_key
            return self

        def event_extraction_system_message(
            self, event_extraction_prompt: str
        ) -> "ImageToCalendar.Builder":
            self._assistant.event_extraction_system_message = event_extraction_prompt
            return self

        def action_llm_system_message(
            self, action_llm_system_message: str
        ) -> "ImageToCalendar.Builder":
            self._assistant.action_llm_system_message = action_llm_system_message
            return self

        def observation_llm_system_message(
            self, observation_llm_system_message: str
        ) -> "ImageToCalendar.Builder":
            self._assistant.observation_llm_system_message = (
                observation_llm_system_message
            )
            return self

        def summary_llm_system_message(
            self, summary_llm_system_message: str
        ) -> "ImageToCalendar.Builder":
            self._assistant.summary_llm_system_message = summary_llm_system_message
            return self

        def model(self, model: str) -> "ImageToCalendar.Builder":
            self._assistant.model = model
            return self

        def build(self) -> "ImageToCalendar":
            self._assistant._construct_workflow()
            return self._assistant

    def _construct_workflow(self):

      
        self.ask_user = AskUserTool.Builder().name("ask_user").function(AskUserTool.ask_user).build()

        self.add_event_to_calendar = CalendarTool.Builder().name("add_event_to_calendar").function(CalendarTool.add_event_to_calendar).build()


        workflow_agent = EventDrivenWorkflow.Builder().name("ImageToCalendarWorkflow")

     
        event_extracted_topic = Topic(name="event_extracted_topic")


        incomplete_info_topic = Topic(
            name="incomplete_info_topic",
            condition=lambda msgs: msgs[-1].tool_calls and msgs[-1].tool_calls[0].function.name == "ask_user"

            # This condition will check if the last message published from the agent to the topic was a call to trigger the `ask_user`. This is done by using 
            # msgs[-1] which will check the last message posted, then the msgs[-1].tool_calls checks if there was any function call in the latest message,
            # and then finally the tool_calls[0].function.name == "ask_user" will check whether the function that is being called is specifically ask_user

            # Note: The `ask_user` is an additional function needed in case the provided image does not contain enough information to post an event on the calendar
            # The code for it can be found in additional_functions.py

            #Note: The agent decides whether the information is complete or not based on the conditions defined in the prompt provided to the system 


        )

        complete_info_topic = Topic(
            name="complete_info_topic",
            condition=lambda msgs: msgs[-1].tool_calls and msgs[-1].tool_calls[0].function.name == "add_event_to_calendar"

            # Same logic as with incomplete_info_topic,
            # 1) msgs[-1]: This accesses the most recent message published to the topic.
            # 2) msgs[-1].tool_calls: This checks if the last message contains any "tool calls".
            # 3) msgs[-1].tool_calls[0].function.name == "add_event_to_calendar"`: This checks if the function called in the last message is `add_event_to_calendar` which will actually trigger the even posting to Google Calendar
        )
        calendar_response_topic = Topic(name="calendar_response_topic")
        human_request_topic = Topic(name="human_request_topic")

        vision_node = (
         LLMNode.Builder()
         .name("VisionNode")
         .subscribe(agent_input_topic)
         .command(
             LLMResponseCommand.Builder()
             .llm(
                 OpenAITool.Builder()
                 .name("VisionLLM")
                 .api_key(self.api_key)
                 .model("gpt-4-vision-preview") 
                 .system_message(self.event_extraction_system_message)  
                 .build()
             )
             .build()
         )
         .publish_to(event_extracted_topic)
         .build()
         )
        
        workflow_agent.node(vision_node)

        action_node = (
            LLMNode.Builder()
            .name("ActionNode")
            .subscribe(event_extracted_topic)
            .command(
                LLMResponseCommand.Builder()
                .llm(
                    OpenAITool.Builder()
                    .name("ActionLLM")
                    .api_key(self.api_key)
                    .model(self.model)
                    .system_message(self.action_llm_system_message)
                    .build()
                )
                .build()
            )
            .publish_to(complete_info_topic)
            .publish_to(incomplete_info_topic)
            .build()
        )

        workflow_agent.node(action_node)

        additional_info_node = (
            LLMFunctionCallNode.Builder()
            .name("AskUserNode")
            .subscribe(incomplete_info_topic)
            .command(
                FunctionCallingCommand.Builder().function_tool(self.ask_user).build()
            )
            .publish_to(human_request_topic)
            .build()
        )

        workflow_agent.node(additional_info_node)

        calendar_node = (
            LLMFunctionCallNode.Builder()
            .name("CalendarNode")
            .subscribe(complete_info_topic)
            .command(
                FunctionCallingCommand.Builder()
                .function_tool(self.add_event_to_calendar)
                .build()
            )
            .publish_to(calendar_response_topic)
            .build()
        )

        workflow_agent.node(calendar_node)

        confirmation_node = (
            LLMNode.Builder()
            .name("ConfirmationNode")
            .subscribe(calendar_response_topic)
            .command(
                LLMResponseCommand.Builder()
                .llm(
                    OpenAITool.Builder()
                    .name("SummaryLLM")
                    .api_key(self.api_key)
                    .model(self.model)
                    .system_message(self.summary_llm_system_message)
                    .build()
                )
                .build()
            )
            .publish_to(agent_output_topic)
            .build()
        )

        workflow_agent.node(confirmation_node)

        self.workflow = workflow_agent.build()

        return self
