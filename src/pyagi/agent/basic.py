from pyagi.tools.manager import ToolManager
import json
from typing import Callable
from pyagi.types import Message, Tool
from pyagi.models.base import BaseModel
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, model: BaseModel, tool_manager: ToolManager, system: str | None = None):
        self.model = model
        self.messages: list[Message] = []
        self.tools = tool_manager

        self.system = system or "You are an agent helping with personal tasks."
        self.messages.append({"role": "system", "content": self.system})


    @abstractmethod
    def run(self):
        ...

class BasicLoopAgent(BaseAgent):
    """
    Get user input and iterate up to five times before going back to the user.

    Tool errors are not handled. No memory management.
    """
    def run(self):
        while True:
            user_msg = input("> ")

            if user_msg == "exit":
                break

            self.messages.append({ "role": "user", "content": user_msg })

            call_model = True
            tool_iteration = 0
            while call_model:
                output, new_messages, call_model = self.iteration()
                print(output + "\n\n")
                self.messages.extend(new_messages)
                tool_iteration += 1

                # backstop to stop an infinite loop. To be removed when this is less buggy.
                if tool_iteration > 5:
                    break

    def iteration(self):
        all_new_messages: list[Message] = []
        new_message, tool_attempts = self.model.query(self.messages, self.tools.tools)
        all_new_messages.append({
            "role": "assistant",
            "content": new_message
        })

        for tool in tool_attempts:
            try:
                did_invoke, tool_output = self.tools.invoke(tool["tool_name"], tool["inputs"])
                if did_invoke:
                    tool_output_str = json.dumps(tool_output)
                    all_new_messages.append({
                        "role": "tool",
                        "content": tool_output_str
                    })
            except:
                ...

        return new_message, all_new_messages, len(tool_attempts) > 0
