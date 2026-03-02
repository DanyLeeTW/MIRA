import asyncio
import json
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Literal, Optional

import pandas as pd
import requests
from config import EVALUATION_MODE
from openai import OpenAI
from pydantic import BaseModel, Field, model_validator
from tenacity import retry, wait_exponential

# from termcolor import colored


if not EVALUATION_MODE:
    raise ValueError("Interactive mode not supported. Set EVALUATION_MODE=True.")

from visualisations import EvaluationOutputCollector as OutputCollector

print("Loaded evaluation mode.")


class Response(BaseModel):
    assistant: str
    type: Literal[
        "assistant_response", "function_call", "terminated"
    ]  # text response, tool use, break signal
    messages: None | str


@dataclass(frozen=False)
class PatientContext:
    """Encapsulates all necessary context for processing patient-specific tool calls."""

    patient_id: str
    patient_hadm_id: str
    organization_id: str
    practitioner_id: str
    session: requests.Session
    headersList: Dict[str, str]
    patient_data: Any
    tools: List[Dict[str, Any]]
    patient_info: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converts the PatientContext to a dictionary for easy passing."""
        return self.__dict__


class PatientAssistant(BaseModel):
    """
    A class representing an AI assistant without tool use.

    Attributes:
        client (openai.OpenAI): The OpenAI client used for making API calls.
        name (str): The name of the assistant.
        model (str): The model used for generating responses.
        instructions (str): Instructions for the assistant.
        temperature (float): The temperature setting for response generation.
        current_step (int): Current step count in the conversation.
        message_history (List[Dict[str, Any]]): A list to store the message history.
    """

    client: OpenAI
    name: str
    model: str
    instructions: str
    temperature: float = 0.01
    # current_step: int = Field(default=0)
    global_step: int = Field(default=0)
    message_history: List[Dict[str, Any]] = Field(default_factory=list)
    message_collector: Any = Field(default_factory=OutputCollector)

    @model_validator(mode="after")
    def initialize_message_history(cls, values):
        values.message_history.append(
            {"role": "system", "content": values.instructions}
        )
        return values

    class Config:
        arbitrary_types_allowed = True

    @retry(wait=wait_exponential(multiplier=1, min=2, max=6))
    def chat_completion(self, new_input: Optional[str]) -> Response:
        """
        Generates a chat completion response based on the provided user input.

        Args:
            new_input (Optional[str]): The new input message from the user.

        Returns:
            Response: The response from the assistant.
        """
        if new_input:
            self.message_history.append({"role": "user", "content": new_input})

        messages = self.message_history

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }

        response = self.client.chat.completions.create(**payload)

        self.message_history.append(
            {"role": "assistant", "content": response.choices[0].message.content}
        )

        response_model = Response(
            assistant=self.name,
            type="assistant_response",
            messages=response.choices[0].message.content,
        )

        self.message_collector.display_message(self.name, response_model.messages)

        return response_model

    def chat(self, new_input: str):
        """
        Process a new input message and generate a response.

        Args:
            new_input (str): The new message from the user to process.

        Returns:
            str: The assistant's response message, or "Conversation ended."
        """
        # self.current_step += 1
        self.global_step += 1
        response = self.chat_completion(new_input)
        return response


class MedAssistant(BaseModel):
    """
    A class representing an AI assistant with various attributes and methods for interaction.

    Attributes:
        client (OpenAI): The OpenAI client used for making API calls.
        name (str): The name of the assistant. Default is "Agent".
        model (str): The model used for generating responses. Default is "gpt-4o-mini".
        instructions (str): Instructions for the assistant. Default is "You are a helpful assistant."
        tools (List[Dict[str, Any]]): A list of tools (dictionaries) the assistant can use. Default is an empty list.
        temperature (float): The temperature setting for response generation. Default is 0.01.
        tool_choice (str): The tool choice mode. Default is "auto".
        func_name_to_func (Dict[str, Callable]): A dictionary mapping function names to functions.
        message_history (List[Dict[str, Any]]): A list to store the message history.
    """

    client: OpenAI
    name: str
    model: str
    instructions: str
    completion_prompt: str
    temperature: float = 0.01
    max_steps: int = Field(default=20)
    current_step: int = Field(default=0)
    global_step: int = Field(default=0)
    completed_called: bool = Field(default=False)
    tool_choice: str = "auto"
    message_history: List[Dict[str, Any]] = Field(default_factory=list)
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    func_name_to_func: Dict[str, Callable] = Field(default_factory=dict)
    tool_call_idx: int = Field(default=0)
    check_enabled: bool = Field(
        default=True
    )  # check stopping conditions, temporarily disable if the agent will be forced to finish the case
    is_last_round: bool = Field(
        default=False
    )  # used to temporarily handle check_enabled
    patient_context: PatientContext = Field(..., description="Patient context")
    message_collector: Any = Field(default_factory=OutputCollector)

    if not EVALUATION_MODE:
        print("Setting `MedAssistant` to interactive mode for Gradio display.")
        tool_call_event: threading.Event = Field(
            default_factory=threading.Event, exclude=True
        )
        selected_arguments: Dict[str, Any] = Field(default_factory=dict, exclude=True)

    @model_validator(mode="after")
    def initialize_message_history(cls, values):
        values.message_history.append(
            {"role": "system", "content": values.instructions}
        )
        return values

    class Config:
        arbitrary_types_allowed = True

    def update_patient_info(self):
        """Update the patient info in the patient context."""
        self.patient_context.patient_info = format_conversation(self.message_history)

    @retry(wait=wait_exponential(multiplier=1, min=2, max=6))
    async def chat_completion(
        self,
        new_input: Optional[str],
        *,
        model: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        tool_choice: Optional[Literal["auto", "required", "none"]] = "auto",
    ):
        """
        Generates a chat completion response based on the provided user input.

        Args:
            new_input (Optional[str]): The new input message from the user.

        Returns:
            Response: The response from the assistant, including any tool calls if applicable.
        """
        # set variables if provided
        model = model or self.model
        tools = tools or self.tools
        tool_choice = tool_choice or self.tool_choice  # type: ignore

        if new_input:
            self.message_history.append({"role": "user", "content": new_input})

        messages = self.message_history

        payload = {
            "model": model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if self.tool_choice in ["auto", "required"]:
            payload.update(
                {
                    "tools": tools,
                    "tool_choice": tool_choice,
                    "parallel_tool_calls": False,
                }
            )

        response = self.client.chat.completions.create(**payload)
        tool_calls = response.choices[0].message.tool_calls

        if not tool_calls:
            self.message_history.append(
                {"role": "assistant", "content": response.choices[0].message.content}
            )

            # update the patient info with the newest messages
            self.update_patient_info()

            response_model = Response(
                assistant=self.name,
                type="assistant_response",
                messages=response.choices[0].message.content,
            )

            self.message_collector.display_message(self.name, response_model.messages)

            return response_model

        if tool_calls:
            for tool_call in tool_calls:
                self.tool_call_idx += 1
                self.message_history.append(
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": f"tool_call_{self.tool_call_idx}",
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments,
                                },
                            }
                        ],
                    }
                )

                print("tool Call", tool_call)
                result = await self.execute_tool_calls(tool_call)

                self.message_history.append(
                    {
                        "tool_call_id": f"tool_call_{self.tool_call_idx}",
                        "role": "tool",
                        "name": tool_call.function.name,
                        "content": str(result),
                    }
                )
                # update the patient info with the newest messages
                self.update_patient_info()

        return Response(assistant=self.name, type="function_call", messages=None)

    async def chat(self, new_input: str):
        """
        Process a new input message and generate a response.

        This method adds the new input to the message history, initiates a chat completion,
        and handles the response. It continues the conversation until a stopping condition
        is met (e.g., max steps reached or completion called).

        Args:
            new_input (str): The new message from the user to process.

        Returns:
            str: The final response message from the assistant, or "Conversation ended."
                 if the conversation is terminated.
        """
        self.current_step = 0  # reset at every round
        while self.should_continue(self.check_enabled):
            self.current_step += 1
            # we have a 1-turn chat_completion by default, except if the assistant calls tools
            # if the assistant calls tools, there is no new input in the next round and we repeat (thus update current_step and reset at every .chat invokation)
            # until returning message with role "assistant"
            response = await self.chat_completion(
                new_input if self.current_step == 1 else None
            )
            if response.type == "function_call":
                continue

            else:
                # global step only applies to "full turns", so tool calling does not increase it
                self.global_step += 1
                # if we are in the last round, we allow the assistant (once exceeding the max_steps) by re-enabling completion checking to break the loop
                # this allows calling tools and requests as needed but wrapping up
                if self.is_last_round:
                    # if the "Finish" action has not been called by the model until now, enforce it
                    if not self.completed_called:
                        self.check_enabled = True
                        self.completed_called = True
                        # force the model to stop
                        tool = [
                            next(
                                filter(
                                    lambda tool: tool["function"]["name"] == "Finish",
                                    self.tools,
                                )
                            )
                        ]
                        _ = await self.chat_completion(
                            None, tools=tool, tool_choice="required"
                        )  # the agent calls the "Finish" tool that gets appended to its history, but we return the last text message
                        return response
                    return response  # "Finish" action has been called by the model, as .completed_called has been set
                return response  # default

        # if the assistant has completed the patient case or we have automatically flagged it as completed due to exceeding max_steps return
        if self.completed_called:
            return Response(assistant=self.name, type="terminated", messages=None)

        # if we reach the maximum global steps, without the agent finishing the patient case, enforce completion
        self.check_enabled = False
        self.is_last_round = True
        # also we want to inform the assistant that it needs to wrap up
        self.message_history.append(
            {"role": "system", "content": self.completion_prompt}
        )
        return await self.chat(new_input)

    def should_continue(self, check_enabled: bool) -> bool:
        """Determine if the conversation should continue based on step count and completion status."""
        # there are two ways conversations can be ended: either by the Agent calling "Finish" action, or by exceeding maximum number of conversation turns,
        # ... upon which the agent has one last final turn of tool use for wrap up.
        if check_enabled:
            return self.global_step < self.max_steps and not self.completed_called
        return True

    async def execute_tool_calls(self, tool_call):
        """
        Executes the tool calls specified in the tool_call parameter.

        This method takes a tool_call object, extracts the function name and arguments,
        and attempts to execute the corresponding function from the func_name_to_func dictionary.
        If the function is not found or the arguments are invalid, appropriate error messages are returned.

        Args:
            tool_call (ToolCall): An object containing the function name and arguments to be executed.

        Returns:
            Any: The result of the function execution, or an error message if the function is not found or arguments are invalid.
        """
        function_name = tool_call.function.name

        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
            return f"Invalid arguments for function {function_name}: {e}"

        if not EVALUATION_MODE:
            # Send the arguments to the Gradio interface and wait for user input
            if self.message_collector.message_queue:
                # Send a special message indicating that user input is required
                self.message_collector.message_queue.put(
                    {
                        "speaker": "System",
                        "type": "tool_call",
                        "function_name": function_name,
                        "arguments": arguments,
                    }
                )

                # Wait for the user's input
                self.tool_call_event.clear()
                self.tool_call_event.wait()  # block until the event thread is finished by the user

                # Update arguments with the user's selection
                arguments = self.selected_arguments  # this is send by the frontend

        # print(colored(arguments, "yellow"))
        all_args = self.patient_context.to_dict()
        all_args.update(arguments)

        # print(colored(arguments, "blue"))

        function = self.func_name_to_func.get(
            function_name,
            lambda **kwargs: (
                f"Function {function_name} not found. Please choose one of {list(self.func_name_to_func.keys())}"
            ),
        )

        # print(colored(function, "yellow"))

        try:
            if asyncio.iscoroutinefunction(function):
                function_result = await function(**all_args)
            else:
                function_result = function(**all_args)
        except Exception as e:
            return f"Runtime error during execution of {function_name}: {e}"

        # print(colored(function_result, "yellow"))

        if function.__name__ == "finish" or function.__name__ == "close_case":
            # slightly handled differently by the frontend if not EVALUATION_MODE
            self.completed_called = True
            self.message_collector.display_action(
                f"Completed the patient case ✅✅✅ with diagnosis: {function_result}",
                function.__name__,
            )

        else:
            self.message_collector.display_action(function_result, function.__name__)

        return function_result


async def call_chat(speaker, message):
    """Run the chat method of the speaker, whether it is async or not"""
    if asyncio.iscoroutinefunction(speaker.chat):
        return await speaker.chat(message)
    else:
        return speaker.chat(message)


def format_conversation(messages):
    """
    Formats a conversation represented as a list of messages into a nicely formatted string.

    Args:
        messages (List[Dict]): The conversation messages.

    Returns:
        str: The formatted conversation string.
    """
    formatted_messages = []
    tool_call_function_info = {}  # Maps tool_call_id to function details

    for msg in messages:
        role = msg.get("role")
        if role == "system":
            continue  # Skip system messages
        elif role == "user":
            content = msg.get("content", "")
            formatted_messages.append(f"**Patient:** {content}")
        elif role == "assistant":
            content = msg.get("content")
            if content:
                formatted_messages.append(f"**Assistant:** {content}")
        elif role == "tool":
            tool_call_id = msg.get("tool_call_id")
            content = msg.get("content", "")
            # Retrieve function name from stored info
            function_info = tool_call_function_info.get(tool_call_id, {})
            function_name = function_info.get(
                "function_name", msg.get("name", "UnknownFunction")
            )
            formatted_messages.append(
                f"**Tool Call:** {function_name} result (content):\n{content}"
            )
        else:
            # Handle any other roles if necessary
            pass

    formatted_conversation = "\n\n===\n".join(formatted_messages)
    # print(colored(" * " * 100, "red"))
    # print(colored(formatted_conversation, "yellow"))
    # print(colored(" * " * 100, "red"))
    return formatted_conversation
