from typing import TypedDict, Literal, Union

class Message(TypedDict):
    role: Union[Literal["user"], Literal["system"], Literal["assistant"]]
    content: str
