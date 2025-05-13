# agent.py

import os
from typing import Any
from grafi.assistants.assistant import Assistant
from grafi.common.topics.topic import Topic, agent_input_topic
from grafi.common.topics.output_topic import agent_output_topic
from grafi.common.topics.human_request_topic import human_request_topic
from grafi.common.topics.subscription_builder import SubscriptionBuilder
from grafi.nodes.impl.llm_node import LLMNode
from grafi.nodes.impl.llm_function_call_node import LLMFunctionCallNode
from grafi.tools.functions.function_calling_command import FunctionCallingCommand
from grafi.tools.llms.impl.openai_tool import OpenAITool
from grafi.tools.llms.llm_response_command import LLMResponseCommand
from grafi.workflows.impl.event_driven_workflow import EventDrivenWorkflow
from openinference.semconv.trace import OpenInferenceSpanKindValues
from pydantic import Field

from assistant.additional_functions import AskUserTool, CalendarTool


class ImageToCalendarHITL(Assistant):
    ask_user: Any = Field(default=None)
    add_event_to_calendar: Any = Field(default=None)
    oi_span_type: OpenInferenceSpanKindValues = Field(default=OpenInferenceSpanKindValues.AGENT)
    name: str = Field(default="ImageToCalendarHITL")
    type: str = Field(default="Assistant")
    api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    event_extraction_system_message: str = Field(default="")
    action_llm_system_message: str = Field(default="")
    summary_llm_system_message: str = Field(default="")
    merge_llm_system_message: str = Field(default="")
    model: str = Field(default="gpt-4o")

    class Builder(Assistant.Builder):
        def __init__(self):
            self._assistant = self._init_assistant()

        def _init_assistant(self) -> "ImageToCalendarHITL":
            return ImageToCalendarHITL()

        def api_key(self, api_key: str) -> "ImageToCalendarHITL.Builder":
            self._assistant.api_key = api_key
            return self

        def event_extraction_system_message(self, msg: str) -> "ImageToCalendarHITL.Builder":
            self._assistant.event_extraction_system_message = msg
            return self

        def action_llm_system_message(self, msg: str) -> "ImageToCalendarHITL.Builder":
            self._assistant.action_llm_system_message = msg
            return self

        def summary_llm_system_message(self, msg: str) -> "ImageToCalendarHITL.Builder":
            self._assistant.summary_llm_system_message = msg
            return self

        def model(self, model: str) -> "ImageToCalendarHITL.Builder":
            self._assistant.model = model
            return self

        def hitl_request(self, tool: Any) -> "ImageToCalendarHITL.Builder":
            self._assistant.ask_user = tool
            return self

        def build(self) -> "ImageToCalendarHITL":
            self._assistant._construct_workflow()
            return self._assistant

    def _construct_workflow(self):
        if not self.ask_user:
            self.ask_user = AskUserTool.Builder().name("ask_user").function(AskUserTool.ask_user).build()

        self.add_event_to_calendar = (
            CalendarTool.Builder()
            .name("add_event_to_calendar")
            .function(CalendarTool.add_event_to_calendar)
            .build()
        )

        workflow = EventDrivenWorkflow.Builder().name("ImageToCalendarWorkflow")

        # Topics
        event_extracted_topic = Topic(name="event_extracted_topic")
        hitl_call_topic = Topic(
            name="hitl_call_topic",
            condition=lambda msgs: msgs
            and msgs[-1].tool_calls
            and msgs[-1].tool_calls[0].function.name == "ask_user",
        )
        complete_info_topic = Topic(
            name="complete_info_topic",
            condition=lambda msgs: msgs
            and msgs[-1].tool_calls
            and msgs[-1].tool_calls[0].function.name == "add_event_to_calendar",
        )
        calendar_response_topic = Topic(name="calendar_response_topic")

        # VisionNode
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
                    .model(self.model)
                    .system_message(self.event_extraction_system_message)
                    .build()
                )
                .build()
            )
            .publish_to(event_extracted_topic)
            .build()
        )
        workflow.node(vision_node)

        # ActionNode
        action_node = (
            LLMNode.Builder()
            .name("ActionNode")
            .subscribe(
                SubscriptionBuilder()
                .subscribed_to(event_extracted_topic)
                .or_()
                .subscribed_to(human_request_topic)
                .build()
            )
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
            .publish_to(hitl_call_topic)
            .publish_to(complete_info_topic)
            .build()
        )

        workflow.node(action_node)

        # HumanRequestNode (for HITL clarification)
        human_request_node = (
            LLMFunctionCallNode.Builder()
            .name("HumanRequestNode")
            .subscribe(hitl_call_topic)
            .command(
                FunctionCallingCommand.Builder()
                .function_tool(self.ask_user)
                .build()
            )
            .publish_to(human_request_topic)
            .build()
        )
        workflow.node(human_request_node)

        # CalendarNode
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
        workflow.node(calendar_node)

        # ConfirmationNode
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
        workflow.node(confirmation_node)

        self.workflow = workflow.build()
