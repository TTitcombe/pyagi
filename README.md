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

## Evals

Evals run on [Harbor](https://docs.harborframework.com); see [evals/README.md](evals/README.md).

```bash
uv run harbor run -p evals/tasks -a pyagi_evals.harbor_agent:PyagiAgent -m qwen3:14b -n 1
```

## Roadmap

- [x] Basic file tool use
- [x] Mock calendar and email tools
- [x] Evals benchmark on personal assistant tasks
- [x] Container environment with mock data
- [ ] Episodic memory
- [ ] Context management
- [x] Web search
- [ ] long-term planning capabilities / reasoning
- [ ] Logging / observability
- [ ] permissions + safety layers

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
