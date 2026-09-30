from typing import Callable
from pyagi.types import Tool
import os
import statistics
from pathlib import Path
from pyagi.tools.base import Toolset

class FileToolset(Toolset):
    @staticmethod
    def edit_file(filepath: str, content: str):
        """
        Edit part of a file by appending text to the end (creates file if does not exist).

        Params
        ------
        filepath: str
            Complete filepath to the file to edit or create
        content: str
            Content to insert.

        """

        p = Path(filepath)
        if not p.exists():
            user_decision = input(f"Agent is trying to create file {filepath}. Proceed? (y/n)")
        else:
            user_decision = input(f"Agent is trying to edit {filepath}. Proceed? (y/n)")

        if user_decision != "y":
            return "Edit did not proceed: user permission gate."

        with p.open('a') as fp:
            fp.write(content)

        return f"{filepath} edited."

    @staticmethod
    def read_file(filepath: str):
        """
        Read the content of the given filepath.
        """
        p = Path(filepath)
        with p.open('r') as fp:
            out = fp.read()

        return out

    @staticmethod
    def list_files():
        """
        List files in the current working directory, and the cwd.
        """
        cwd = os.getcwd()
        files = [f for f in os.listdir(cwd) if os.path.isfile(os.path.join(cwd, f))]

        return f"CWD: {cwd}; contains {files}"

    @property
    def tools(self) -> list[Tool]:
        return [
            {
                "tool_name": "edit_file",
                "description": "Edit part of a file by appending text to the end. Creates the file if it does not exist.",
                "parameters": {"filepath": "str", "content": "str"}
            },
            {
                "tool_name": "read_file",
                "description": "Read the content of the given filepath.",
                "parameters": {"filepath": "str"}
            },
            {
                "tool_name": "list_files",
                "description": "List files in the current working directory, and the cwd itself.",
                "parameters": {}
            },
        ]

    @property
    def tool_mapping(self) -> dict[str, Callable]:
        return {
            "list_files": self.list_files,
            "edit_file": self.edit_file,
            "read_file": self.read_file,
        }
