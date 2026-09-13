from pyagi.types import ToolUse
from typing import Any
import json
import re
from pyagi.tools.files import edit_file, list_files, read_file

TOOLS = [
    edit_file,
    list_files,
    read_file,
]

TOOL_DICT = {tool.__name__: tool for tool in TOOLS }

def tool_prompt() -> str:
    if len(TOOLS) == 0:
        return ""

    prompt = "You have access to the following tools:\n"

    for tool in TOOLS:
        prompt += f"{tool.__name__}:\n{tool.__doc__}\n\n"

    prompt += "\n\nInvoke a tool by outputting\n<tool>\n{'tool': <tool_name>, 'parameters': <dict of parameters>}\n</tool>"
    return prompt.strip()

def process_tools(prompt: str) -> list[ToolUse]:
    tool_regex = re.findall(r'<tool>(.+?)</tool>', prompt, re.DOTALL)
    tool_outputs: list[ToolUse] = []

    for maybe_tool in tool_regex:
        try:
            print(f"Got json regex: {maybe_tool}")
            tool_json = json.loads(maybe_tool)
            tool_name = tool_json["tool"]
            tool_params = tool_json["parameters"] if "parameters" in tool_json else {}
            print(f"Got tool: {tool_name} | {tool_params}")

            if tool_name not in TOOL_DICT:
                continue

            print(f"Invoking {tool_name} with {tool_params}")
            tool_output = TOOL_DICT[tool_name](**tool_params)
            print(f"Got {tool_output}")
            tool_outputs.append({ "tool_name": tool_name, "input": json.dumps(tool_params), "output": json.dumps(tool_output) })
        except Exception as e:
            print(f"Error parsing tool: {e}")

    return tool_outputs
