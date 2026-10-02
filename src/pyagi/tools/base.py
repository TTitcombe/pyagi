from typing import Callable, Any
from pyagi.types import Tool
from abc import abstractmethod, ABC

class Toolset(ABC):
    @property
    @abstractmethod
    def tools(self) -> list[Tool]:
        ...

    @property
    @abstractmethod
    def tool_mapping(self) -> dict[str, Callable]:
        ...

    def invoke(self, tool_name: str, params: dict) -> tuple[bool, Any]:
        internal_fn = self.tool_mapping[tool_name]

        if internal_fn is None:
            return False, None
        else:
            return True, internal_fn(*params)
