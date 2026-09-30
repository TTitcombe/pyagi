from pyagi.tools.file_io import FileToolset
from pyagi.tools.base import Toolset
from typing import Callable, Any
from pyagi.types import Tool

class ToolManager:
    def __init__(self):
        self.toolsets: list[Toolset] = []

    def register(self, toolset: Toolset) -> None:
        self.toolsets.append(toolset)

    @property
    def tools(self):
        all_tools = []
        for toolset in self.toolsets:
            all_tools.extend(toolset.tools)

        return all_tools

    def invoke(self, tool_name: str, params: dict) -> tuple[bool, Any]:
        for toolset in self.toolsets:
            did_match, result = toolset.invoke(tool_name, params)
            if did_match:
                return True, result

        return False, None


def create_tools(*, file_io: bool = False) -> ToolManager:
    manager = ToolManager()
    if file_io:
        manager.register(FileToolset())

    return manager
