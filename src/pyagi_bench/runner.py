"""
Runs an agent config over tasks × trials and writes a self-describing run dir:

    runs/<timestamp>_<config>_<model>_<selection>[_<label>]/
        run.json            config, git state, benchmark version, model digests, selection
        results.jsonl       one line per trial, appended as they finish (safe to resume)
        trajectories/       full timeline + initial/final world per trial (enables re-grading)
        logs/               captured stdout/stderr of the agent per trial
        reviews.jsonl       human verdicts from `bench review`
        summary.md          human-readable report

Trials run trial-major (every task once, then every task again) so an
interrupted run still has an unbiased pass@1 over the whole selection.
"""
import contextlib
import io
import json
import os
import platform
import re
import subprocess
import sys
import time
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Callable

from pyagi_bench import llm
from pyagi_bench.agents import TaskContext, make_agent
from pyagi_bench.config import ConfigError, RunConfig
from pyagi_bench.env import Environment
from pyagi_bench.grading import grade, outcome
from pyagi_bench.grading.context import GradeContext
from pyagi_bench.grading.judge import Judge
from pyagi_bench.tasks import Task, benchmark_version
from pyagi_bench.user_sim import make_user


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def run_name(config: RunConfig, selection: str, label: str | None, now: datetime) -> str:
    model = config.model.get("name") or config.agent["type"]
    parts = [now.strftime("%Y%m%d-%H%M%S"), slug(config.name), slug(model), slug(selection)]
    if label:
        parts.append(slug(label))
    return "_".join(parts)


def make_judge(config: RunConfig) -> Judge | None:
    j = config.judge
    return Judge(j["model"], j.get("url"), j.get("options")) if j else None


def git_info() -> dict:
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip())
        return {"sha": sha, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        # Inside a container without .git the image records the commit at build time.
        return {"sha": os.environ.get("PYAGI_GIT_SHA", "unknown"), "dirty": None}


def _models(config: RunConfig) -> dict:
    sections = [("agent", config.model, "name"), ("judge", config.judge, "model"), ("user_simulator", config.user_simulator, "model")]
    return {
        role: {"name": s[key], "digest": llm.model_digest(s[key], s.get("url"))}
        for role, s, key in sections
        if s and s.get(key)
    }


def trajectory_path(task_id: str, trial: int) -> str:
    return f"trajectories/{task_id.replace('/', '__')}__t{trial}.json"


def run_trial(task: Task, trial: int, config: RunConfig, benchmark_dir: Path, run_dir: Path, judge: Judge | None) -> dict:
    events: list[dict] = []
    env = Environment(task.build_world(benchmark_dir / "worlds"), events)
    agent = make_agent(config)
    ctx = TaskContext(env.preamble(), list(env.tools.values()), env.call, task.oracle if agent.needs_reference else None)

    log_path = run_dir / "logs" / Path(trajectory_path(task.id, trial)).with_suffix(".log").name
    error = None
    started = time.perf_counter()
    # Agent output goes to the log; an empty stdin makes any stray input() fail fast instead of hanging the run.
    with log_path.open("w") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        real_stdin, sys.stdin = sys.stdin, io.StringIO()
        try:
            agent.start(ctx)
            for index, session in enumerate(task.sessions):
                if index:
                    agent.new_session()
                events.append({"type": "session", "session": index})
                user = make_user(session, config)
                message: str | None = session.prompt
                for turn in range(session.max_turns):
                    events.append({"type": "user", "session": index, "turn": turn, "content": message})
                    reply = agent.respond(message)
                    events.append({"type": "agent", "session": index, "turn": turn, "content": reply})
                    message = user.reply(reply)
                    if message is None:
                        break
        except ConfigError:
            raise
        except Exception:
            error = traceback.format_exc()
            print(error)
        finally:
            sys.stdin = real_stdin
    wall = time.perf_counter() - started

    final = env.world.snapshot()
    checks = [r.to_dict() for r in grade(GradeContext(task, env.initial, final, events, judge))]
    status, score = outcome(checks)
    if error:
        status = "error"

    calls = [e for e in events if e["type"] == "tool_call"]
    trajectory = {
        "task_id": task.id,
        "trial": trial,
        "events": events,
        "transcript": _safe(agent.transcript, []),
        "initial": env.initial,
        "final": final,
        "error": error,
    }
    path = trajectory_path(task.id, trial)
    (run_dir / path).write_text(json.dumps(trajectory, indent=1, default=str))

    return {
        "task_id": task.id,
        "trial": trial,
        "category": task.category,
        "difficulty": task.difficulty,
        "split": task.split,
        "tags": task.tags,
        "status": status,
        "score": round(score, 3),
        "error": error.strip().splitlines()[-1] if error else None,
        "checks": checks,
        "metrics": {
            "wall_seconds": round(wall, 2),
            "turns": sum(e["type"] == "agent" for e in events),
            "tool_calls": len(calls),
            "tool_errors": dict(Counter(e["error"] for e in calls if "error" in e)),
            **_safe(agent.usage, {}),
        },
        "trajectory": path,
    }


def _safe(fn: Callable, default):
    """Adapter introspection must never cost us a trial's results."""
    try:
        return fn()
    except Exception:
        return default


def completed(run_dir: Path) -> set[tuple[str, int]]:
    results = run_dir / "results.jsonl"
    if not results.exists():
        return set()
    return {(r["task_id"], r["trial"]) for r in map(json.loads, results.read_text().splitlines())}


def execute(
    config: RunConfig,
    tasks: list[Task],
    trials: int,
    benchmark_dir: Path,
    run_dir: Path,
    selection: str,
    progress: Callable[[str], None] = print,
) -> Path:
    """Run (or resume) a run dir. Resuming reuses the stored config and selection."""
    (run_dir / "trajectories").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(exist_ok=True)
    meta_path = run_dir / "run.json"

    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta["benchmark_version"] != benchmark_version(benchmark_dir):
            progress("WARNING: benchmark files changed since this run started; results may mix versions")
    else:
        meta = {
            "name": run_dir.name,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "status": "running",
            "config_name": config.name,
            "config_hash": config.hash,
            "config": config.raw,
            "selection": selection,
            "tasks": [t.id for t in tasks],
            "trials": trials,
            "benchmark_version": benchmark_version(benchmark_dir),
            "git": git_info(),
            "models": _models(config),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "command": sys.argv,
        }
        meta_path.write_text(json.dumps(meta, indent=2))

    judge = make_judge(config)
    done = completed(run_dir)
    total = len(tasks) * trials
    with (run_dir / "results.jsonl").open("a") as out:
        for trial in range(trials):
            for i, task in enumerate(tasks):
                n = trial * len(tasks) + i + 1
                if (task.id, trial) in done:
                    continue
                record = run_trial(task, trial, config, benchmark_dir, run_dir, judge)
                out.write(json.dumps(record) + "\n")
                out.flush()
                m = record["metrics"]
                failed = [c["check"] for c in record["checks"] if c["status"] in ("fail", "error")]
                progress(
                    f"[{n:>3}/{total}] {task.id:<40} t{trial}  {record['status'].upper():<7}"
                    f" {m['wall_seconds']:>6.1f}s  {m['tool_calls']:>2} calls"
                    + (f"  failed: {', '.join(failed)}" if failed else "")
                    + (f"  ({record['error']})" if record["error"] else "")
                )

    meta.update(status="complete", finished_at=datetime.now().astimezone().isoformat(timespec="seconds"))
    meta_path.write_text(json.dumps(meta, indent=2))
    return run_dir
