import statistics
from abc import abstractmethod
from hashlib import new
import json
import re
from typing import List, Callable
import requests

from pyagi.models.base import BaseModel
from pyagi.types import ToolUse, Message, ToolAttempt, Tool

OLLAMA_URL = "http://localhost:11434/api/chat"


class OllamaChatModel(BaseModel):
    """
    Use ollama chat api to invoke a model.

    Inserts tools into chat template and extracts tool use on our behalf.
    """
    def query(self, messages: List[Message], tools: List[Tool]) -> tuple[str, str, List[ToolAttempt]]:
        return (
            "",
            "",
            []
            # TODO: get the tools
        )

class OllamaDirect(BaseModel):
    def __init__(self, model: str, ollama_url: str = OLLAMA_URL):
        super().__init__(model)
        self.ollama_url = ollama_url
        self.tool_use_regex = rf'<tool>(.+?)</tool>'

    def process_message(self, message: str) -> str:
        return re.sub(self.tool_use_regex, "", message).strip()

    def process_tools(self, message: str) -> list[ToolAttempt]:
        tool_regex = re.findall(self.tool_use_regex, message, re.DOTALL)
        tools: list[ToolAttempt] = []

        for maybe_tool in tool_regex:
            try:
                print(f"Got json regex: {maybe_tool}")
                tool_json = json.loads(maybe_tool)
                tool_name = tool_json["tool"]
                tool_params = tool_json["parameters"] if "parameters" in tool_json else {}
                print(f"Got tool: {tool_name} | {tool_params}")
                tools.append({ "tool_name": tool_name, "inputs": tool_params })
            except Exception as e:
                print(f"Error parsing tool: {e}")

        return tools

    def add_tool_to_system(self, messages: List[Message], tools: List[Tool]) -> List[Message]:
        new_messages: list[Message] = []
        for message in messages:
            if message["role"] == "system":
                new_message: Message = {
                    "role": "system",
                    "content": message["content"] + f"\n\n{self.tool_prompt(tools)}"
                }
                new_messages.append(new_message)
            else:
                new_messages.append(message)

        return new_messages

    @staticmethod
    def tool_prompt(tools: List[Tool]):
        prompt = "You have access to the following tools:\n<tools>"

        for tool in tools:
            prompt += f"<tool_definition>{tool['tool_name']}:\n{tool['parameters']}\n{tool['description']}</tool_definition>\n"

        prompt += '\n</tools>\n\nInvoke a tool by outputting\n<tool>\n{"tool": tool_name, "parameters": <dict of parameters>}\n</tool>'
        return prompt.strip()

    def query(self, messages: List[Message], tools: List[Tool]) -> tuple[str, str, List[ToolAttempt]]:
        processed_messages = self.add_tool_to_system(messages, tools)
        # print("Sending...")
        for _m in processed_messages:
            print(_m["content"])

        payload = {
            "model": self.model,
            "messages": processed_messages,
            # Ollama streams NDJSON by default, which r.json() can't parse.
            "stream": False,
            "think": True
        }

        # A cold model has to be loaded into memory first, which can take a while.
        r = requests.post(self.ollama_url, json=payload, timeout=300)
        r.raise_for_status()

        output = r.json()
        new_message: str = output["message"]["content"]

        message = self.process_message(new_message)
        tool_usage = self.process_tools(new_message)

        return (
            message,
            output["message"].get("thinking"),
            tool_usage,
        )
