# pyagi-bench

A minimal harness for evaluating the agent as a personal assistant. It has
three parts: a mock world (the email and calendar the agent can use), tasks
graded on what the agent changed in that world, and a runner that records
everything.

```bash
uv run bench list
uv run bench validate                       # the oracle solves every task; doing nothing fails every task
uv run bench run -c configs/baseline.yaml --trials 4 --label "first baseline"
uv run bench run -c configs/baseline.yaml --task 'email/*' --split dev
```

Docker (the world ships in the image; Ollama runs on the host):

```bash
docker compose build --build-arg GIT_SHA=$(git rev-parse HEAD)
docker compose run --rm bench run -c configs/baseline.yaml --trials 4
```

The first version (18 tasks, a richer world, LLM judge, simulated users,
human review, comparisons with confidence intervals) is in commit `eb098c2`.

## How it fits together

```
task YAML ──► world = world/*.yaml + task setup      (fresh copy per trial)
                │
runner ── prompt ──► AgentAdapter.respond() ──► ctx.call_tool() ──► Environment ──► tools mutate world
   ▲                      │                                            │
   └── scripted reply ◄── reply                       every call logged to the trial timeline
                │
grading: diff(world before, world after) + timeline ──► checks ──► pass / fail / pending
```

| Path | What it is |
|---|---|
| `benchmark/world/` | `world.yaml` (frozen clock, user) + one YAML list per collection (`emails`, `events`) |
| `benchmark/tasks/<category>/<name>.yaml` | one task per file; id = path without extension |
| `src/pyagi_bench/env/` | world state + diff, tool registry, email and calendar tools |
| `src/pyagi_bench/grading/` | checks and matchers |
| `src/pyagi_bench/agents/` | `AgentAdapter` interface; `basic_loop` (your agent), `oracle`, `noop` |
| `src/pyagi_bench/runner.py` | trials, the timeline, the run directory |
| `src/pyagi_bench/metrics.py` | pass@1, pass^k |

Each run directory in `runs/` holds:
- `run.json`: config, git sha, benchmark content hash
- `results.jsonl`: one line per trial
- `trajectories/*.json`: timeline plus the world before and after
- `logs/*.log`: the agent's stdout
- `summary.md`

## Ideas worth keeping in mind

- **Grade the end state, not the path.** Was the email sent to the right person?
  Does the event exist at the right time? Many paths are valid; few end states
  are. (τ-bench, AppWorld, WorkBench.)
- **Collateral damage is failure.** Each task declares the changes it allows
  (`side_effects`). Any other change fails the task.
- **Prove each task is solvable and non-vacuous.** The oracle replays a
  reference solution and must pass; an agent that does nothing must fail. If
  doing nothing passes (common for "don't do X" tasks), add a check on the
  useful part. (ABC checklist, Zhu et al. 2025.)
- **Reliability, not just capability.** pass^k is the chance that *all* k trials
  succeed. Run several trials. (τ-bench.)
- **Reproducibility.** A frozen clock, a fresh world per trial, deterministic
  ids, and a content hash of `benchmark/` recorded with every run.
- **Humans where state can't decide.** `human` checks stay `pending`, and
  pending trials are left out of the metrics.
- **Hold out a split.** Iterate on `dev`; keep `test` for numbers you report.
  (Kapoor et al., "AI Agents That Matter".)

## Task schema

See [`tasks/email/reply-landlord.yaml`](tasks/email/reply-landlord.yaml), which
documents every field: `description`, `split`, `prompt`, `replies`, `setup`,
`side_effects`, `checks`, `oracle`.

### Checks

Field values in checks use matchers:
- a scalar is a case-insensitive equality match; datetimes are compared as datetimes
- `{contains: x | [x, y]}`
- `{contains_any: [x, y]}`
- `{regex: ...}`

Any check also accepts `group:` (for example `utility` or `security`) for slicing later.

| check | passes when |
|---|---|
| `email_sent` | a new sent email matches `to/cc/subject/body/in_reply_to` (`count:` = exactly n) |
| `event_exists` | the final calendar has a matching event |
| `record_exists` / `record_absent` | generic: `{collection, where, scope: final\|added, count}` |
| `response` | the agent's final reply matches text matchers |
| `asked_before` | the agent handed back to the user before its first successful call to `tool` |
| `human` | always `pending`; for you to grade |
| `side_effects` | added automatically from the task's `side_effects` |

### Adding things

- **A tool:** add a function with `@tool(...)` in `env/<service>.py`, and import
  the module in `env/tools.py:all_tools`. Raise `ToolError` for mistakes the
  agent made; they are returned to the agent and counted.
- **A collection of world data:** add `benchmark/world/<name>.yaml`, a list of
  records that each have an `id`.
- **A check:** add a function with `@check("name")` in `grading/checks.py`.
- **An agent design:** subclass `AgentAdapter` in `agents/`, register it in
  `AGENTS`, and point a config's `agent.type` at it.

## Removed, and where each comes from

Each of these was in `eb098c2`.

| Idea | Why it matters | Source |
|---|---|---|
| LLM-simulated user | multi-turn tasks where the right reply depends on what the agent asked | τ-bench; Seshadri et al. 2026 *(preprint)* on simulator bias |
| LLM judge, calibrated against your human grades | subjective checks at scale | Zheng et al. 2023; AgentRewardBench 2025 |
| Confidence intervals over tasks; paired comparisons | telling real improvements from noise | Miller 2024, "Adding Error Bars to Evals" |
| Utility vs security scoring of injection tasks | an agent that refuses everything is "secure" | AgentDojo 2024; InjecAgent 2024 |
| Confirmation before irreversible actions | risk and helpfulness scored separately | ToolEmu 2023 |
| Multi-session tasks | testing memory | LongMemEval 2024; LoCoMo 2024 |
| Cost alongside accuracy (tokens, time) | a slower but better agent isn't automatically better | Kapoor et al. 2024 |
| Native vs prompted tool calling | the format often matters as much as the model | BFCL (Patil et al., ICML 2025) |
