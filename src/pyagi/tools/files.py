import os
from typing import Union
from pathlib import Path

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

def read_file(filepath: str):
    """
    Read the content of the given filepath.
    """
    p = Path(filepath)
    with p.open('r') as fp:
        out = fp.read()

    return out

def list_files():
    """
    List files in the current working directory, and the cwd.
    """
    cwd = os.getcwd()
    files = os.listdir()

    return f"CWD: {cwd}; contains {files}"
