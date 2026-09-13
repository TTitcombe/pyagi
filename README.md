# Agent-from-scratch

Building an agent from scratch, no frameworks,
one feature at a time.

VERY WIP.

## Setup

- ollama
- uv

This uses `ollama` to serve models,
it does NOT use the ollama framework to abstract e.g. tool calls away.

## How to use

_n.b. the default model is `deepseek-r1:14b`, so make sure your machine can handle at least that._

`uv run main.py` will start an interactive agent terminal session.

`exit` to end the session.

## Roadmap

- [ ] Basic file tool use. IN PROGRESS
- [ ] Terminal utilities like usage and compaction
- [ ] Web search
- [ ] long-term planning capabilities
- [ ] Episodic memory
- [ ] Logging / observability

Anything more complex,
like computer use, skills, MCP support,
is a stretch goal.

## AI notice

This is a personal excercise to develop an agent from scratch.
As such, I am not using agents to code this.
I am, however, using Claude to evaluate my approach,
suggest improvements,
and surface relevant literature.

If I end up implementing a rich TUI,
that will most likely be authored by AI,
because building that is not the purpose of this work.
