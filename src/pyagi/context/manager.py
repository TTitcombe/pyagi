from pyagi.models.base import BaseModel
from pyagi.types import Message

class ContextManager:
    def __init__(self, system: str | None):
        self.system_prompt = system
        self.messages: list[Message] = []

        if system:
            self.messages.append({
                "role": "system",
                "content": system,
            })

    def reset(self):
        self.messages = []
        if self.system_prompt:
            self.messages.append({
                "role": "system",
                "content": self.system_prompt,
            })

    def add(self, messages: Message | list[Message]) -> None:
        messages = [messages] if not isinstance(messages, list) else messages
        self.messages.extend(messages)

    def compact(self, model: BaseModel, guidance: str | None = None) -> None:
        guidance = guidance or "Summarise the key parts of this conversation so that another AI can pick it up. Include provenance of what the user and you have done."
        output_message, _ = model.query([*self.messages, { "role": "user", "content": guidance }], [])

        self.reset()
        self.add({ "role": "assistant", "content": output_message })
