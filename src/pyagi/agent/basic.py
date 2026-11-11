from pyagi.context.manager import ContextManager
from pyagi.tools.manager import ToolManager
import json
from typing import Callable
from pyagi.types import Message, Tool
from pyagi.models.base import BaseModel
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, model: BaseModel, tool_manager: ToolManager):
        self.model = model
        self.tools = tool_manager

    @abstractmethod
    def run(self):
        ...

class BasicLoopAgent(BaseAgent):
    """
    Get user input and iterate up to five times before going back to the user.

    Tool errors are not handled. No memory management.
    """
    def __init__(self, model: BaseModel, tool_manager: ToolManager, system: str | None = None):
        super().__init__(model, tool_manager)
        system = system or "You are an agent helping with personal tasks"
        self.context_manager = ContextManager(system)

        self.should_stop: bool = False

    def handle_command(self, user_msg: str) -> None:
        if not user_msg.startswith("/"):
            return

        if user_msg == "/exit":
            self.should_stop = True
        elif user_msg == "/compact":
            self.context_manager.compact(self.model)
        elif user_msg == "/clear":
            self.context_manager.reset()

    def run(self):
        while True:
            # _ is meant to be final output (rather than printing)
            _ = self.run_iteration()
            if self.should_stop:
                break

    def run_iteration(self) -> str | None:
        user_msg = input("> ")

        self.handle_command(user_msg)
        if self.should_stop:
            return None

        self.context_manager.add({ "role": "user", "content": user_msg })

        call_model = True
        tool_iteration = 0
        while call_model:
            output, new_messages, call_model = self.iteration()
            print(output + "\n\n")
            self.context_manager.add(new_messages)
            tool_iteration += 1

            # backstop to stop an infinite loop. To be removed when this is less buggy.
            if tool_iteration > 5:
                self.should_stop = True
                return None

        return None

    def iteration(self):
        all_new_messages: list[Message] = []
        new_message, thinking, tool_attempts = self.model.query(self.context_manager.messages, self.tools.tools)
        all_new_messages.append({
            "role": "assistant",
            "content": new_message,
            "thinking": thinking,
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
                else:
                    # This is a terrible error message: the agent has no information to improve on.
                    # TODO: tools handle their own errors and return structured errors.
                    all_new_messages.append({
                        "role": "tool",
                        "content": f"{tool['tool_name']} failed to invoke",
                    })
            except Exception as e:
                all_new_messages.append({
                    "role": "tool",
                    "content": f"{tool['tool_name']} failed to run: {str(e)}"
                })

        return new_message, all_new_messages, len(tool_attempts) > 0
