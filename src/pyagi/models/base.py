from abc import abstractmethod, ABC
from pyagi.types import ToolUse, Message, ToolAttempt, Tool
from typing import List

class BaseModel(ABC):
    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def query(self, messages: List[Message], tools: List[Tool]) -> tuple[str, str, List[ToolAttempt]]:
        ...
