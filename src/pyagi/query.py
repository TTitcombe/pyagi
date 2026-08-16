from pyagi.types import Message
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"


def generate(messages: list[Message], model: str) -> str:
    payload = {
        "model": model,
        "messages": messages,
        # Ollama streams NDJSON by default, which r.json() can't parse.
        "stream": False,
    }
    # A cold model has to be loaded into memory first, which can take a while.
    r = requests.post(OLLAMA_URL, json=payload, timeout=300)
    r.raise_for_status()

    output = r.json()
    print(output.keys())
    return output["message"]["content"]
