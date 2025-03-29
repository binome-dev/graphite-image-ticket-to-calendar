import os
from pydantic import Field
from grafi.assistants.assistant import Assistant
from grafi.common.topics.output_topic import agent_output_topic
from grafi.common.topics.topic import Topic, agent_input_topic
from grafi.common.topics.subscription_builder import SubscriptionBuilder
from grafi.nodes.impl.llm_node import LLMNode
from grafi.nodes.impl.llm_function_call_node import LLMFunctionCallNode
from grafi.tools.llms.impl.openai_tool import OpenAITool
from grafi.tools.llms.llm_response_command import LLMResponseCommand
from grafi.tools.functions.function_tool import FunctionTool
from grafi.tools.functions.function_calling_command import FunctionCallingCommand
from grafi.workflows.impl.event_driven_workflow import EventDrivenWorkflow




class ImageToCalendar(Assistant):

    name: str = Field(default="Assistant")
    type: str = Field(default="Assistant")
    api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    event_extraction_system_message: str = Field(default=None)
    observation_llm_system_message: str = Field(default=None)
    action_llm_system_message: str = Field(default=None)
    summary_llm_system_message: str = Field(default=None)
    model: str = Field(default="gpt-4o-mini")


    class Builder(Assistant.Builder):

        def __init__(self):
            self._assistant = self.init_assistant()
        
        def _init_assistant(self) -> "ImageToCalendar.Builder":
            return ImageToCalendar()

        def api_key(self, api_key: str) -> "ImageToCalendar.Builder":
            self._assistant.api_key = api_key
            return self
        
        def event_extraction_system_message(self, event_extraction_prompt: str) -> "ImageToCalendar.Builder":
            self._assistant.event_extraction_system_message = event_extraction_system_message
            return self

        def action_llm_system_message(self, action_llm_system_message: str) -> "ImageToCalendar.Builder":
            self._assistant.action_llm_system_message = action_llm_system_message
            return self

        def observation_llm_system_message(self, observation_llm_system_message: str) -> "ImageToCalendar.Builder":
            self._assistant.observation_llm_system_message = observation_llm_system_message
            return self

        def summary_llm_system_message(self, summary_llm_system_message: str) -> "ImageToCalendar.Builder":
            self._assistant.summary_llm_system_message = summary_llm_system_message
            return self

        def model(self) -> "ImageToCalendar.Builder":
            self._assistant.model = model
            return self
        
        def build(self) -> "ImageToCalendar.Builder":
            self._assistant._construct_workflow()
            return self._assistant

    def _construct_workflow(self):

        workflow_agent = EventDrivenWorkflow.Builder().name("ImageToCalendarWorkflow")

        # All the required Topics:
        event_extracted_topic = Topic(name="event_extracted_topic")
        incomplete_info_topic = Topic(name="incomplete_info_topic",
            condition=lambda msgs: msgs[-1].tool_calls and msgs[-1].tool_calls[0].function.name == "ask_user"  # These functions still need to be defined
        )
        complete_info_topic = Topic(name="complete_info_topic",
            condition=lambda msgs: msgs[-1].tool_calls and msgs[-1].tool_calls[0].function.name == "add_event_to_calendar"
        )
        calendar_response_topic = Topic(name="calendar_response_topic")


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
 
        #This node will be requiring an additional function called ask_user to request more info
        additional_info_node = (
            LLMFunctionCallNode.Builder()
            .name("AskUserNode")
            .subscribe(incomplete_info_topic)
            .command(
                FunctionCallingCommand.Builder()
                .function_tool(self.ask_user)
                .build()
            )
            .publish_to(human_request_topic)
            .build()
        )

        workflow_agent.node(additional_info_node)

        #This node will be requiring an additional function called add_event_to_calendar to post the event
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
                    .system_message(summary_llm_system_message)
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




