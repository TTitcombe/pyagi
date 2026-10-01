import argparse
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from pyagi_bench.config import RunConfig, load_config
from pyagi_bench.report import load_results, render_compare, write_summary
from pyagi_bench.tasks import Task, load_tasks, select


def _tasks(args) -> list[Task]:
    return load_tasks(args.benchmark_dir / "tasks")


def _selected(args) -> tuple[list[Task], str]:
    tasks = select(
        _tasks(args), ids=args.task, categories=args.category, tags=args.tag, split=args.split, difficulty=args.difficulty
    )
    parts = [args.split, *(args.category or []), *(args.tag or []), args.difficulty]
    if args.task:
        parts.append(f"{len(tasks)}-tasks")
    return tasks, "-".join(p for p in parts if p) or "all"


def cmd_list(args) -> None:
    tasks, selection = _selected(args)
    print(f"{'task':<42} {'difficulty':<10} {'split':<5} {'checks':>6}  oracle  tags")
    for t in tasks:
        print(f"{t.id:<42} {t.difficulty:<10} {t.split:<5} {len(t.checks):>6}  {'yes' if t.oracle else 'NO ':<6}  {', '.join(t.tags)}")
    print(f"\n{len(tasks)} tasks ({selection})")


def cmd_tools(args) -> None:
    from pyagi_bench.env.tools import all_tools

    for t in all_tools():
        print(f"{t.name}{' [mutates]' if t.mutates else ''}\n  {t.description}")
        for name, p in t.params.items():
            print(f"    {name}: {p.type}{'' if p.required else '?'} — {p.description}")


def cmd_run(args) -> None:
    from pyagi_bench.runner import execute, run_name

    if args.resume:
        run_dir = Path(args.resume)
        meta = json.loads((run_dir / "run.json").read_text())
        by_id = {t.id: t for t in _tasks(args)}
        tasks = [by_id[tid] for tid in meta["tasks"]]
        config = RunConfig(meta["config_name"], meta["config"])
        execute(config, tasks, meta["trials"], args.benchmark_dir, run_dir, meta["selection"])
        print(f"\n{write_summary(run_dir)}")
        return

    if not args.config:
        sys.exit("bench run: pass --config (or --resume)")
    tasks, selection = _selected(args)
    if not tasks:
        sys.exit("No tasks match the selection")

    run_dirs = []
    for config_path in args.config:
        config = load_config(Path(config_path), args.set)
        run_dir = args.runs_dir / run_name(config, selection, args.label, datetime.now())
        print(f"\n▶ {run_dir.name}: {len(tasks)} tasks × {args.trials} trials")
        execute(config, tasks, args.trials, args.benchmark_dir, run_dir, selection)
        summary = write_summary(run_dir)
        print(f"\n{summary.split('## By category')[0].strip()}\n\nFull report: {run_dir / 'summary.md'}")
        run_dirs.append(run_dir)

    if len(run_dirs) > 1:
        print("\n" + render_compare(run_dirs))


def cmd_validate(args) -> None:
    """Schema-check every task, then prove each is solvable (oracle) and not vacuous (noop)."""
    from pyagi_bench.runner import execute

    tasks, _ = _selected(args)
    print(f"✓ {len(tasks)} tasks parse")
    for t in tasks:
        t.build_world(args.benchmark_dir / "worlds")
    print("✓ worlds and setups load")

    simulated = [t for t in tasks if any(s.simulator for s in t.sessions)]
    if simulated:
        print(f"! skipping tasks with an LLM-simulated user (need a model): {', '.join(t.id for t in simulated)}")
        tasks = [t for t in tasks if t not in simulated]

    problems = 0
    with tempfile.TemporaryDirectory() as tmp:
        for kind in ("oracle", "noop"):
            run_dir = Path(tmp) / kind
            subset = [t for t in tasks if t.oracle] if kind == "oracle" else tasks
            execute(RunConfig(kind, {"agent": {"type": kind}}), subset, 1, args.benchmark_dir, run_dir, kind, progress=lambda _: None)
            for r in load_results(run_dir):
                bad = [f"{c['check']}: {c['detail']}" for c in r["checks"] if c["status"] in ("fail", "error")]
                if kind == "oracle" and (r["status"] in ("fail", "error")):
                    problems += 1
                    print(f"✗ oracle fails {r['task_id']}: {r['error'] or '; '.join(bad)}")
                if kind == "noop" and r["status"] in ("pass", "pending"):
                    problems += 1
                    print(f"✗ noop agent {r['status']}es {r['task_id']} — some check is passing vacuously")

    missing = [t.id for t in tasks if not t.oracle]
    if missing:
        print(f"! no oracle solution (can't prove solvable): {', '.join(missing)}")
    print("✓ all good" if not problems else f"\n{problems} problem(s)")
    sys.exit(1 if problems else 0)


def cmd_report(args) -> None:
    print(write_summary(Path(args.run)))


def cmd_compare(args) -> None:
    text = render_compare([Path(r) for r in args.runs])
    if args.out:
        Path(args.out).write_text(text)
    print(text)


def cmd_review(args) -> None:
    from pyagi_bench.review import review

    review(Path(args.run), {t.id: t for t in _tasks(args)}, include_judged=args.judged)


def cmd_rescore(args) -> None:
    from pyagi_bench.review import rescore
    from pyagi_bench.runner import make_judge

    run_dir = Path(args.run)
    meta = json.loads((run_dir / "run.json").read_text())
    judge = make_judge(RunConfig(meta["config_name"], meta["config"])) if args.judge else None
    n = rescore(run_dir, {t.id: t for t in _tasks(args)}, judge)
    print(f"Re-graded {n} trials with current checks{' (judge re-run)' if judge else ''}; previous results backed up.")
    print(write_summary(run_dir))


def _add_selection(p: argparse.ArgumentParser) -> None:
    p.add_argument("--task", action="append", help="task id or glob, e.g. 'email/*' (repeatable)")
    p.add_argument("--category", action="append", help="repeatable")
    p.add_argument("--tag", action="append", help="repeatable; tasks with any of the tags")
    p.add_argument("--split", choices=("dev", "test"))
    p.add_argument("--difficulty", choices=("easy", "medium", "hard"))


def main() -> None:
    parser = argparse.ArgumentParser(prog="bench", description="pyagi personal-assistant benchmark")
    parser.add_argument("--benchmark-dir", type=Path, default=Path("benchmark"))
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="list tasks")
    _add_selection(p)
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("tools", help="print the mock world's tool API")
    p.set_defaults(fn=cmd_tools)

    p = sub.add_parser("run", help="run agent config(s) over tasks")
    p.add_argument("-c", "--config", action="append", help="run config YAML (repeat to sweep configs)")
    p.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="override a config value, e.g. model.name=qwen3:8b")
    p.add_argument("--trials", type=int, default=1, help="trials per task (≥4 for meaningful pass^k)")
    p.add_argument("--label", help="free text appended to the run name")
    p.add_argument("--runs-dir", type=Path, default=Path("runs"))
    p.add_argument("--resume", metavar="RUN_DIR", help="continue an interrupted run")
    _add_selection(p)
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("validate", help="check tasks: schema, oracle solves them, noop fails them")
    _add_selection(p)
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("report", help="regenerate a run's summary.md")
    p.add_argument("run")
    p.set_defaults(fn=cmd_report)

    p = sub.add_parser("compare", help="compare runs, paired on shared tasks (first run is the baseline)")
    p.add_argument("runs", nargs="+")
    p.add_argument("--out", help="also write markdown here")
    p.set_defaults(fn=cmd_compare)

    p = sub.add_parser("review", help="human-grade pending checks of a run")
    p.add_argument("run")
    p.add_argument("--judged", action="store_true", help="also spot-check LLM judge verdicts (measures judge agreement)")
    p.set_defaults(fn=cmd_review)

    p = sub.add_parser("rescore", help="re-grade a run's saved trajectories with the current checks")
    p.add_argument("run")
    p.add_argument("--judge", action="store_true", help="re-run LLM judge checks too")
    p.set_defaults(fn=cmd_rescore)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
