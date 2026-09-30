from typing import TypedDict, Literal, Union, Any

class Message(TypedDict):
    role: Union[Literal["user"], Literal["system"], Literal["assistant"], Literal["tool"]]
    content: str

class Tool(TypedDict):
    tool_name: str
    description: str
    parameters: dict[str, str]

class ToolAttempt(TypedDict):
    tool_name: str
    inputs: dict

class ToolUse(ToolAttempt):
    output: str
