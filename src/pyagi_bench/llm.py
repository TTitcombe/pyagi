"""
Minimal Ollama client for the harness's own model calls (judge, user simulator).
Independent of pyagi's model classes so changing the agent never changes the grader.
"""
import json
import os

import requests

DEFAULT_URL = "http://localhost:11434"


def base_url(configured: str | None = None) -> str:
    return (configured or os.environ.get("OLLAMA_URL") or DEFAULT_URL).rstrip("/")


def chat(model: str, messages: list[dict], *, url: str | None = None, json_mode: bool = False, options: dict | None = None) -> str:
    payload = {"model": model, "messages": messages, "stream": False, "options": options or {}}
    if json_mode:
        payload["format"] = "json"
    r = requests.post(f"{base_url(url)}/api/chat", json=payload, timeout=600)
    r.raise_for_status()
    return r.json()["message"]["content"]


def model_digest(model: str, url: str | None = None) -> str | None:
    """Exact weights identifier, so 'qwen3:8b' today and 'qwen3:8b' next month aren't silently conflated."""
    try:
        r = requests.get(f"{base_url(url)}/api/tags", timeout=3)
        r.raise_for_status()
        for m in r.json().get("models", []):
            if m["name"] == model or m["model"] == model:
                return m.get("digest")
    except (requests.RequestException, KeyError, json.JSONDecodeError):
        pass
    return None
