from typing import Callable
from pyagi.types import Tool
import os
import statistics
from pathlib import Path
from pyagi.tools.base import Toolset

class FileToolset(Toolset):
    def __init__(self, root: str | None = None):
        super().__init__()

        self.root = Path(root) if isinstance(root, str) else Path.cwd()

    def edit_file(self, filepath: str, content: str):
        """
        Edit part of a file by appending text to the end (creates file if does not exist).

        Params
        ------
        filepath: str
            Complete filepath to the file to edit or create
        content: str
            Content to insert.

        """

        p = self.root / filepath

        with p.open('a') as fp:
            fp.write(content)

        return f"{filepath} edited."

    def read_file(self, filepath: str):
        """
        Read the content of the given filepath.
        """
        p = self.root / filepath
        with p.open('r') as fp:
            out = fp.read()

        return out

    def list_files(self):
        """
        List files in the current working directory, and the cwd.
        """
        cwd = self.root.cwd()
        files = [f for f in os.listdir(cwd) if os.path.isfile(os.path.join(cwd, f))]

        return f"CWD: {cwd}; contains {files}"

    @property
    def tools(self) -> list[Tool]:
        return [
            {
                "tool_name": "edit_file",
                "description": "Edit part of a file by appending text to the end. Creates the file if it does not exist.",
                "parameters": {"filepath": f"str, relative to root at {self.root}", "content": "str"}
            },
            {
                "tool_name": "read_file",
                "description": "Read the content of the given filepath.",
                "parameters": {"filepath": f"str, relative to root at {self.root}"}
            },
            {
                "tool_name": "list_files",
                "description": f"List files in root at {self.root}, and the cwd itself.",
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
