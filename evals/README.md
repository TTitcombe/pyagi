# Evals

Evals run on [Harbor](https://docs.harborframework.com).

Currently a small eval set of file management tasks, to be expanded over time.

## Running

Docker must be running. Ollama must be running locally with the model pulled.

```bash
docker build -t pyagi-evals-base:local evals/base   # once, and after every change to evals/base
uv run harbor run -p evals/tasks -a oracle     # reference solutions: every task should score 1
uv run harbor run -p evals/tasks -a nop        # does nothing: every task should score 0
uv run harbor run -p evals/tasks -a pyagi_evals.harbor_agent:PyagiAgent -m qwen3:14b -n 1 -k 4
uv run harbor view jobs                        # browse results in the web viewer
```

- `-k 4`: 4 attempts per task; the results include pass@k.
- `-n 1`: run one trial at a time, because Ollama serves one request at a time.
- `--job-name`: name the run; results go to `jobs/<name>/`.
- `-i 'pattern'`: only run tasks matching the pattern.

`jobs/<job>/result.json` holds the metrics. Each trial directory holds:
- `agent/`: `messages.json` (full context), `agent.log` (everything the agent printed), `response.txt` (final reply)
- `verifier/`: the reward and the test output
