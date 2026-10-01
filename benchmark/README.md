# pyagi-bench: a personal-assistant benchmark

A mock world (mailbox, calendar, contacts, documents, shop), a suite of tasks
graded on **what the agent actually changed in that world**, and tooling to run,
review and compare agent configurations.

```bash
uv run bench list                                   # what's in the suite
uv run bench tools                                  # the tool API agents get
uv run bench validate                               # prove tasks are solvable and not vacuous
uv run bench run -c configs/baseline.yaml --split dev --trials 4
uv run bench run -c configs/baseline.yaml -c configs/variants/qwen3-8b.yaml --category email
uv run bench run -c configs/baseline.yaml --set model.name=qwen3:14b --label "qwen 14b"
uv run bench review runs/<run>                      # grade checks that need a human
uv run bench compare runs/<baseline> runs/<variant> # paired comparison
uv run bench rescore runs/<run>                     # re-grade after fixing a check, without re-running the model
uv run bench run --resume runs/<run>                # continue an interrupted run
```

In Docker (the mock world ships in the image; Ollama runs on the host):

```bash
docker compose build --build-arg GIT_SHA=$(git rev-parse HEAD)
docker compose run --rm bench run -c configs/baseline.yaml --trials 4
```

## Layout

```
benchmark/
  worlds/base/            the persona's world: world.yaml (clock, user) + one YAML per collection
    documents/            files, loaded as the `documents` collection keyed by path
  tasks/<category>/*.yaml one task per file; id = path without extension
configs/                  agent configurations (what's being evaluated)
src/pyagi_bench/
  env/                    world state + tool implementations (email, calendar, contacts, documents, shop)
  agents/                 AgentAdapter interface + adapters (basic_loop, oracle, noop)
  grading/                checks, matchers, LLM judge
  runner.py               runs trials, writes run dirs
  metrics.py, report.py   pass@1, pass^k, CIs, summaries, comparisons
runs/                     outputs (git-ignored)
```

## Design principles

These follow from the literature (see [References](#references)):

1. **Grade the end state, not the path.** Most checks inspect the world after
   the trial: was an email sent to the right person, does the event exist at
   the right time? Many paths are valid; few end states are. (τ-bench, AppWorld,
   WorkBench.)
2. **Collateral damage is failure.** Every task declares a `side_effects` budget,
   and *any* change outside it fails the task. An agent that books the meeting
   and also emails three people hasn't succeeded. (AppWorld, WorkBench.)
3. **Every task is proven solvable and non-vacuous.** `bench validate` runs an
   oracle (the task's reference solution) that must pass, and a do-nothing agent
   that must fail. A do-nothing agent scores 38% on τ-bench airline because of
   "no change" tasks. The ABC checklist calls this out. Tasks where restraint is
   correct (injection, out-of-stock) also carry a *utility* check.
4. **Reliability over capability.** Run k ≥ 4 trials and read **pass^k**, the
   chance that all k attempts succeed. An assistant that buys the right thing 70%
   of the time is not one you let near your card. (τ-bench.)
5. **Honest uncertainty.** CIs bootstrap over tasks, not trials, because trials of
   a task are correlated. Comparisons are paired on shared tasks. With 18
   tasks the CIs are wide, so treat small differences as noise. (Miller 2024,
   "Adding Error Bars to Evals".)
6. **Reproducible by construction.** A frozen clock, a fresh world per trial,
   deterministic ids, and a content hash of the benchmark (`benchmark_version`)
   recorded with every run. Runs also record the git sha and dirty flag, the
   fully resolved config, and the Ollama model digests.
7. **Safety is part of the suite, scored separately.** Injection tasks put
   attacker instructions in emails and documents. Checks are tagged
   `group: utility | security | safety`, so the report shows utility under
   attack separately from attack resistance. (AgentDojo, InjecAgent.) Spending
   and irreversible actions need confirmation. (ToolEmu.)
8. **Humans and judges only where state can't decide.** `human` checks queue for
   `bench review`. `llm_judge` checks fall back to human review when no judge is
   configured, and every judge verdict is labelled with its model. Use
   `bench review --judged` to spot-check verdicts; the report then shows
   judge–human agreement. Don't trust a judge you haven't calibrated.
   (Zheng et al. 2023, AgentRewardBench.)
9. **Hold out a test split.** Tune on `dev`. Touch `test` rarely, for numbers you
   publish. (Kapoor et al., "AI Agents That Matter".)
10. **Report cost next to accuracy.** For local models the cost that matters is
    wall-clock time and model calls. Every trial records them.

## Writing tasks

```yaml
# benchmark/tasks/calendar/move-lunch.yaml  ->  id: calendar/move-lunch
description: What this tests and why (for you, not the agent).
difficulty: easy | medium | hard
split: dev | test
tags: [single-app, update]          # free-form; reports slice by tag
world: base                         # default
now: 2026-10-05T09:00               # optional clock override
setup:                              # optional: add/replace records for this task only
  emails: [{id: em-x, folder: inbox, ...}]
prompt: Priya wants to push our lunch tomorrow to 1pm ...
user:
  replies: ["Yes please."]          # scripted replies, used each time the agent hands back
  # simulator: {persona: ..., goal: ..., knowledge: ...}   # LLM-played user instead
  # max_turns: 3
# sessions: [{prompt: ..., user: ...}, {prompt: ...}]      # multi-session (memory) tasks
side_effects: {events.update: 1}    # allowed changes: <collection>.<add|update|delete>: n | any
                                    # omitted = nothing may change; `side_effects: any` disables the check
checks:
  - event_exists: {title: {contains: Priya}, start: 2026-10-06T13:00, count: 1}
oracle:                             # reference solution, replayed by `bench validate`
  - {call: calendar_update_event, args: {event_id: ev-lunch-priya, start: ..., end: ...}}
  - {say: "Moved it."}              # `say` ends the agent's turn
```

Scripted replies are consumed whenever the agent hands back, whatever it said.
That is deterministic but blunt. If the right reply depends on what the agent
asked, use the LLM simulator. Its model is set in the config (`user_simulator`)
and recorded, because the choice of simulator measurably moves scores.

### Checks

Every check accepts `group:` (for example `utility` or `security`) for sliced
reporting. Field values use [matchers](../src/pyagi_bench/grading/matchers.py):

- a scalar is a case-insensitive equality match; datetimes are compared as datetimes
- a list is a set match
- `{contains, contains_any, not_contains, regex, includes, excludes, gte, lte, any_of, equals}`

| check | passes when |
|---|---|
| `email_sent` | a new sent email matches `to/cc/subject/body/in_reply_to` (`count:` = exactly n) |
| `email_not_sent` | no new sent email matches (no fields = nothing sent at all) |
| `draft_saved` | a new draft matches |
| `event_exists` / `event_absent` | the final calendar has / lacks a matching event |
| `event_scheduled` | a new event satisfies constraints: `duration_minutes`, `within`, `daily_window`, `weekdays_only`, `no_overlap` |
| `order_placed` / `no_order` | a new order matches / no new order (matching) |
| `record_exists` / `record_absent` | generic: `{collection, where, scope: final\|added\|updated\|deleted, count}` |
| `response` | the agent's last reply (or `messages: all`) matches text matchers |
| `tool_called` / `tool_not_called` | trajectory: successful calls matching `{name, args, min, max}` |
| `asked_before` | the agent handed back to the user before its first successful call to `tool` |
| `llm_judge` | judge model passes it against `rubric` (otherwise it waits for human review) |
| `human` | a person passes it in `bench review` |
| `python` | `{function: "module:fn"}` returns true; the escape hatch |
| `side_effects` | added automatically from the task's `side_effects` budget |

Checklist for a new task:
- [ ] `bench validate` passes: the oracle solves it, and the noop agent fails it.
- [ ] A wrong-but-plausible answer fails it. Try one by hand, or write a test.
- [ ] Every proper noun, date and number the agent needs exists in the world.
- [ ] Restraint tasks also carry a utility check.
- [ ] It isn't checking a phrasing the user never asked for.

## Evaluating a new agent design

Write an adapter in `src/pyagi_bench/agents/` and register it in `AGENTS`:

```python
class MyAdapter(AgentAdapter):
    def start(self, ctx: TaskContext): ...      # ctx.preamble, ctx.tools (JSON schemas), ctx.call_tool(name, args)
    def respond(self, message: str) -> str: ... # run until you hand back to the user
    def new_session(self): ...                  # multi-session tasks: keep memory, drop context
    def usage(self) -> dict: ...                # model_calls, model_seconds, tokens...
```

The benchmark owns the tool *API*. How it's presented to the model (prompted
`<tool>` tags, native tool calling, rewritten descriptions) is part of the agent
design, and a legitimate thing to vary. Then add a config:

```yaml
extends: ../baseline.yaml
name: with-memory
agent: {type: my_agent, memory: {kind: notes-file, max_items: 50}}   # free-form, your adapter reads it
```

## Reading the report

`summary.md` in each run dir contains:

- **Headline:** pass@1 with CI; pass^k and pass@k for every k up to the trial count.
- **Collateral damage:** the fraction of trials that changed something they shouldn't.
- **Check groups:** utility / security / safety pass rates.
- **By category, difficulty and tag.**
- **Cost & tool use:** time, turns, model calls, and tool-call error rate by kind:
  - `unknown_tool`, `invalid_args`, `tool_error`: the agent's mistakes, and a
    good signal for prompt/format work with small models
  - `env_bug`: our mistake; fix the environment
- **Per-task table** listing the most common failing checks.

For debugging, every trial's `trajectories/*.json` contains:

- the interleaved timeline of user and agent messages and tool calls with results
- the agent's raw transcript
- the world before and after the trial

`logs/*.log` captures everything the agent printed.

## Not built yet

Roughly in order of how much each would improve the findings:

- **More tasks.** 18 tasks give CIs of roughly ±20 points. To detect a
  10-point difference you want about 100+ tasks × 4+ trials. Generate
  *variants* from templates (different people, dates, items, phrasings) rather
  than writing every task by hand. Variants also measure robustness to rephrasing.
- **Native vs prompted tool calling** as separate configs. BFCL reports these
  separately for a reason, and with local models the format often matters more
  than the model.
- **Token counts.** Ollama returns `prompt_eval_count`/`eval_count`, but
  `BaseModel.query` doesn't surface them yet. Add them to `usage()`.
- **Sampling control.** `OllamaDirect` can't set temperature or seed yet. The
  adapter refuses `model.options` rather than silently ignoring them.
- **A "spam" baseline** that calls every mutating tool, to make sure collateral
  checks bite.
- **A scale knob for the world.** Hundreds of emails and months of calendar
  stress retrieval and context management, which is where memory and compaction
  work will show up.
- **Time that moves** (Gaia2/ARE): new email arriving mid-task, or deadlines
  passing.
- **Harmful *user* requests,** not just injected ones (OpenAgentSafety).
- **LLM-user validation:** compare simulator behaviour with a handful of sessions
  you play yourself, and add difficult personas (vague, impatient), since
  simulated users are too cooperative.
- **A failure taxonomy.** Label why trials fail (hallucinated id, wrong
  date arithmetic, gave up, loop limit). That turns scores into findings.
- **Per-trial timeouts and network isolation** once the agent gets web or shell tools.

## References

All verified 2026-10-01. Entries marked *preprint* are 2026 work not yet confirmed as peer reviewed.

- Yao et al., **τ-bench**, 2024. [arXiv:2406.12045](https://arxiv.org/abs/2406.12045): state-based grading, pass^k, LLM user simulation, policy documents.
- Barres et al., **τ²-bench**, 2025. [arXiv:2506.07982](https://arxiv.org/abs/2506.07982): dual-control environments; compositional task generation.
- Trivedi et al., **AppWorld**, ACL 2024. [arXiv:2407.18901](https://arxiv.org/abs/2407.18901): multi-app world, state-based checks including collateral damage.
- Lu et al., **ToolSandbox**, 2024. [arXiv:2408.04682](https://arxiv.org/abs/2408.04682): stateful tools, milestones, insufficient-information tasks.
- Styles et al., **WorkBench**, 2024. [arXiv:2405.00823](https://arxiv.org/abs/2405.00823): email/calendar tasks with a unique correct end state; wrong actions tracked.
- Xu et al., **TheAgentCompany**, 2024. [arXiv:2412.14161](https://arxiv.org/abs/2412.14161): checkpoints for partial credit.
- Froger et al., **ARE / Gaia2**, 2025. [arXiv:2509.17158](https://arxiv.org/abs/2509.17158): asynchronous environments where time moves.
- Kapoor et al., **AI Agents That Matter**, 2024. [arXiv:2407.01502](https://arxiv.org/abs/2407.01502): cost-aware evaluation, holdouts, reproducibility.
- Zhu et al., **Establishing Best Practices for Building Rigorous Agentic Benchmarks** (ABC), 2025. [arXiv:2507.02825](https://arxiv.org/abs/2507.02825): no-op baselines, task and outcome validity.
- Miller, **Adding Error Bars to Evals**, 2024. [arXiv:2411.00640](https://arxiv.org/abs/2411.00640): clustered standard errors, paired comparisons, power analysis.
- Madaan et al., **Quantifying Variance in Evaluation Benchmarks**, 2024. [arXiv:2406.10229](https://arxiv.org/abs/2406.10229).
- Debenedetti et al., **AgentDojo**, 2024. [arXiv:2406.13352](https://arxiv.org/abs/2406.13352): utility vs utility-under-attack vs attack success.
- Zhan et al., **InjecAgent**, 2024. [arXiv:2403.02691](https://arxiv.org/abs/2403.02691).
- Ruan et al., **ToolEmu**, ICLR 2024. [arXiv:2309.15817](https://arxiv.org/abs/2309.15817): risk and helpfulness scored separately.
- Vijayvargiya et al., **OpenAgentSafety**, 2025. [arXiv:2507.06134](https://arxiv.org/abs/2507.06134).
- Seshadri et al., **Lost in Simulation**, 2026 *preprint*. [arXiv:2601.17087](https://arxiv.org/abs/2601.17087): the choice of simulator model shifts agent scores.
- Zhou et al., **Mind the Sim2Real Gap in User Simulation for Agentic Tasks**, 2026 *preprint*. [arXiv:2603.11245](https://arxiv.org/abs/2603.11245).
- Zheng et al., **Judging LLM-as-a-Judge**, NeurIPS 2023. [arXiv:2306.05685](https://arxiv.org/abs/2306.05685).
- Lù et al., **AgentRewardBench**, 2025. [arXiv:2504.08942](https://arxiv.org/abs/2504.08942): judges vs expert labels on agent trajectories.
- Patil et al., **Berkeley Function Calling Leaderboard**, ICML 2025. [PMLR v267](https://proceedings.mlr.press/v267/patil25a.html): native vs prompted function calling.
- Wu et al., **LongMemEval**, ICLR 2025. [arXiv:2410.10813](https://arxiv.org/abs/2410.10813); Maharana et al., **LoCoMo**, 2024. [arXiv:2402.17753](https://arxiv.org/abs/2402.17753): multi-session memory.
- Anthropic, **Demystifying evals for AI agents**, Jan 2026. [anthropic.com](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).
- UK AISI, **Inspect**. [inspect.aisi.org.uk](https://inspect.aisi.org.uk): a mature framework to compare against or migrate to.
