# Evals

Evals run on [Harbor](https://docs.harborframework.com).

Currently a small eval set of file management tasks, to be expanded over time.

## Running

Docker must be running. Ollama must be running locally with the model pulled.

```bash
evals/build.sh                                 # builds the base world and its overlays; rerun after any change to them
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

## The mock world

`evals/base` builds the image every task starts from:

| Path in the container | From | What it is |
|---|---|---|
| `/app` | `files/` | the user's files; the agent's file tools work here |
| `/var/lib/world` | `seed/` | live state of the mock services (`calendar.json`, `mail.json`, `contacts.json`, `web.json`; `world.json` holds the frozen clock and user) |
| `/opt/world/seed` | `seed/` | untouched copy of the starting state, for checkers to diff against |
| `/opt/world/bin/` | `world/bin/` | mock service CLIs, on `PATH`: `cal` (`now`, `list`, `search`, `get`, `create`, `update`, `delete`), `mail` (`search`, `read`, `send`, `draft`, `move`), `contacts` (`search`), `web` (`search`, `fetch`) |
| `/opt/world/lib/check.py` | `world/lib/` | checker library for verifiers; on `PYTHONPATH` |

The agent's calendar, email and contact tools should call these CLIs through the adapter's `exec`. Each returns JSON,
or an `Error: ...` message with a non-zero exit code. `mail send` only files the email in `sent`: nothing is delivered
and nobody replies. Reading email never changes state. `web` is a small seeded corpus (venue pages with opening hours
and booking addresses, a restaurant guide), not the internet. The venues are fictional, so the model can't answer from
what it already knows. The calendar and archived email include past date nights, as history the agent can look up.

**Overlays** (`evals/overlays/<name>/`) layer extra state on the base world for a group of tasks, without changing
it for everyone else. `seed/*.json` records are added (or replace base records with the same id), and `files/` lands in
`/app`. The seed copy gets the same records, so checkers diff against the overlay's starting point. `build.sh` builds
each overlay as `pyagi-evals-<name>:local`; tasks point at it with `docker_image`. The `food-shop` overlay serves the
four `food-shop-*` tasks.

## Writing a task

Copy `tasks/move-lunch`. `solve.sh` is the `cal` commands that solve it. `test.sh` uses `check.py`:

```bash
python3 - <<'PY' || echo 0 > /logs/verifier/reward.txt
from check import *

event_exists(title_contains="Priya", start="2026-10-06T13:00", end="2026-10-06T14:00", count=1)
only_changed({"calendar.update": 1})   # anything else changed in the world fails the task
finish()                               # writes reward.txt (1 only if every check passed) and checks.json
PY
```

Checks:
- calendar: `event_exists`, `event_absent`
- email: `email_sent`, `email_not_sent`, `draft_saved`, `email_in_folder`
- side effects: `only_changed`, `nothing_changed` (for ask/refuse tasks)
- the agent's final reply: `reply_contains`
- building blocks for task-specific checks: `new_events`, `sent_emails`, `clashes`, `mentions_date`, `mentions_time`,
  `file_text`; record the result with `expect(name, passed, detail)`

The example tasks are `move-lunch` (calendar), `reply-landlord` (email) and `date-night` (long-horizon planning across
calendar, email, contacts, web and files). `date-night` grades on rules (Sam is free, no clash, the venue is new,
vegetarian-friendly and open, the booking email gives date, time and party size, the todo is ticked off) rather than one
fixed answer, so any valid booking passes. Tag each task in `task.toml` `[metadata]` with
`family`, `outcome`, `steps` and `split`.
