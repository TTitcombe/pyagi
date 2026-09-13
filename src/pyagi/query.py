from ollama import chat, ChatResponse
from pyagi.tools.files import list_files, edit_file, read_file
from pyagi.types import Message

OLLAMA_URL = "http://localhost:11434/api/chat"

def generate(messages: list[Message], model: str) -> ChatResponse:
    response: ChatResponse = chat(
            model=model,
            messages=messages,
            tools=[list_files, edit_file, read_file],
    )

    return response
