"""
Runs an agent config over tasks × trials and writes a self-describing run dir:

    runs/<timestamp>_<config>_<model>_<selection>[_<label>]/
        run.json         config, git state, benchmark version, selection
        results.jsonl    one line per trial
        trajectories/    full timeline + world before/after per trial
        logs/            whatever the agent printed, per trial
        summary.md       human-readable report
"""
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable

from pyagi_bench.agents import TaskContext, make_agent
from pyagi_bench.config import RunConfig
from pyagi_bench.env import Environment
from pyagi_bench.grading import grade, outcome
from pyagi_bench.grading.context import GradeContext
from pyagi_bench.tasks import Task, benchmark_version


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def run_name(config: RunConfig, selection: str, label: str | None) -> str:
    model = config.model.get("name") or config.agent["type"]
    parts = [datetime.now().strftime("%Y%m%d-%H%M%S"), slug(config.name), slug(model), slug(selection)]
    return "_".join(parts + ([slug(label)] if label else []))


def git_info() -> dict:
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip())
        return {"sha": sha, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        # Inside a container without .git the image records the commit at build time.
        return {"sha": os.environ.get("PYAGI_GIT_SHA", "unknown"), "dirty": None}


def run_trial(task: Task, trial: int, config: RunConfig, benchmark_dir: Path, run_dir: Path) -> dict:
    events: list[dict] = []  # the trial's timeline: user/agent messages here, tool calls via the env
    env = Environment(task.build_world(benchmark_dir / "world"), events)
    agent = make_agent(config)
    ctx = TaskContext(env.preamble(), list(env.tools.values()), env.call, task.oracle if agent.needs_reference else None)
    replies = list(task.replies)

    name = f"{task.id.replace('/', '__')}__t{trial}"
    error = None
    started = time.perf_counter()
    # Agent prints go to the log; an empty stdin makes any stray input() fail fast instead of hanging.
    with (run_dir / "logs" / f"{name}.log").open("w") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        real_stdin, sys.stdin = sys.stdin, io.StringIO()
        try:
            agent.start(ctx)
            message = task.prompt
            for turn in range(task.max_turns):
                events.append({"type": "user", "turn": turn, "content": message})
                reply = agent.respond(message)
                events.append({"type": "agent", "turn": turn, "content": reply})
                if not replies:
                    break
                message = replies.pop(0)
        except Exception:
            error = traceback.format_exc()
            print(error)
        finally:
            sys.stdin = real_stdin
    wall = time.perf_counter() - started

    final = env.world.snapshot()
    checks = [r.to_dict() for r in grade(GradeContext(task, env.initial, final, events))]
    status, score = outcome(checks)
    if error:
        status = "error"

    trajectory = {
        "task_id": task.id,
        "trial": trial,
        "events": events,
        "transcript": agent.transcript() if not error else [],
        "initial": env.initial,
        "final": final,
        "error": error,
    }
    (run_dir / "trajectories" / f"{name}.json").write_text(json.dumps(trajectory, indent=1, default=str))

    calls = [e for e in events if e["type"] == "tool_call"]
    return {
        "task_id": task.id,
        "trial": trial,
        "category": task.category,
        "split": task.split,
        "status": status,
        "score": round(score, 3),
        "error": error.strip().splitlines()[-1] if error else None,
        "checks": checks,
        "wall_seconds": round(wall, 2),
        "tool_calls": len(calls),
        "tool_errors": sum("error" in e for e in calls),
    }


def execute(
    config: RunConfig,
    tasks: list[Task],
    trials: int,
    benchmark_dir: Path,
    run_dir: Path,
    selection: str,
    progress: Callable[[str], None] = print,
) -> Path:
    """Trials run trial-major (every task once, then again) so a partial run still covers every task."""
    (run_dir / "trajectories").mkdir(parents=True)
    (run_dir / "logs").mkdir()
    meta = {
        "name": run_dir.name,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "config": config.raw,
        "config_hash": config.hash,
        "selection": selection,
        "tasks": [t.id for t in tasks],
        "trials": trials,
        "benchmark_version": benchmark_version(benchmark_dir),
        "git": git_info(),
    }
    (run_dir / "run.json").write_text(json.dumps(meta, indent=2))

    total = len(tasks) * trials
    with (run_dir / "results.jsonl").open("w") as out:
        for trial in range(trials):
            for i, task in enumerate(tasks):
                record = run_trial(task, trial, config, benchmark_dir, run_dir)
                out.write(json.dumps(record) + "\n")
                out.flush()
                failed = [c["check"] for c in record["checks"] if c["status"] in ("fail", "error")]
                progress(
                    f"[{trial * len(tasks) + i + 1:>3}/{total}] {task.id:<40} t{trial}  {record['status'].upper():<7}"
                    f" {record['wall_seconds']:>6.1f}s  {record['tool_calls']:>2} calls"
                    + (f"  failed: {', '.join(failed)}" if failed else "")
                    + (f"  ({record['error']})" if record["error"] else "")
                )
    return run_dir
