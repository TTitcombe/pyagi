from typing import TypedDict, Literal, Union

class Message(TypedDict):
    role: Union[Literal["user"], Literal["system"], Literal["assistant"], Literal["tool"]]
    content: str

class ToolUse(TypedDict):
    tool_name: str
    input: str
    output: str
