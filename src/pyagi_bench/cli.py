import argparse
import sys
import tempfile
from pathlib import Path

from pyagi_bench.config import RunConfig, load_config
from pyagi_bench.report import load_results, write_summary
from pyagi_bench.tasks import Task, load_tasks, select


def _selected(args) -> tuple[list[Task], str]:
    tasks = select(load_tasks(args.benchmark_dir / "tasks"), ids=args.task, split=args.split)
    parts = [args.split, f"{len(tasks)}-tasks" if args.task else None]
    return tasks, "-".join(p for p in parts if p) or "all"


def cmd_list(args) -> None:
    tasks, selection = _selected(args)
    for t in tasks:
        print(f"{t.id:<40} {t.split:<5} {len(t.checks)} checks  oracle: {'yes' if t.oracle else 'NO'}")
    print(f"\n{len(tasks)} tasks ({selection})")


def cmd_run(args) -> None:
    from pyagi_bench.runner import execute, run_name

    tasks, selection = _selected(args)
    if not tasks:
        sys.exit("No tasks match the selection")
    config = load_config(Path(args.config))
    run_dir = args.runs_dir / run_name(config, selection, args.label)
    print(f"▶ {run_dir.name}: {len(tasks)} tasks × {args.trials} trials")
    execute(config, tasks, args.trials, args.benchmark_dir, run_dir, selection)
    print(f"\n{write_summary(run_dir)}\nRun saved to {run_dir}")


def cmd_validate(args) -> None:
    """Prove each task is solvable (the oracle passes) and not vacuous (doing nothing fails)."""
    from pyagi_bench.runner import execute

    tasks, _ = _selected(args)
    for t in tasks:
        t.build_world(args.benchmark_dir / "world")
    print(f"✓ {len(tasks)} tasks parse and their worlds load")

    problems = 0
    with tempfile.TemporaryDirectory() as tmp:
        for kind in ("oracle", "noop"):
            run_dir = Path(tmp) / kind
            subset = [t for t in tasks if t.oracle] if kind == "oracle" else tasks
            execute(RunConfig(kind, {"agent": {"type": kind}}), subset, 1, args.benchmark_dir, run_dir, kind, progress=lambda _: None)
            for r in load_results(run_dir):
                if kind == "oracle" and r["status"] in ("fail", "error"):
                    problems += 1
                    bad = [f"{c['check']}: {c['detail']}" for c in r["checks"] if c["status"] in ("fail", "error")]
                    print(f"✗ oracle fails {r['task_id']}: {r['error'] or '; '.join(bad)}")
                if kind == "noop" and r["status"] in ("pass", "pending"):
                    problems += 1
                    print(f"✗ doing nothing {r['status']}es {r['task_id']}: some check passes vacuously")

    if missing := [t.id for t in tasks if not t.oracle]:
        print(f"! no oracle, so not proven solvable: {', '.join(missing)}")
    print("✓ all good" if not problems else f"\n{problems} problem(s)")
    sys.exit(1 if problems else 0)


def main() -> None:
    parser = argparse.ArgumentParser(prog="bench", description="pyagi personal-assistant benchmark")
    parser.add_argument("--benchmark-dir", type=Path, default=Path("benchmark"))
    sub = parser.add_subparsers(dest="command", required=True)

    def selection_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--task", action="append", help="task id or glob, e.g. 'email/*' (repeatable)")
        p.add_argument("--split", choices=("dev", "test"))

    p = sub.add_parser("list", help="list tasks")
    selection_args(p)
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("validate", help="check tasks: the oracle solves them, doing nothing fails them")
    selection_args(p)
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("run", help="run an agent config over tasks")
    p.add_argument("-c", "--config", required=True, help="run config YAML")
    p.add_argument("--trials", type=int, default=1, help="trials per task (several are needed for pass^k)")
    p.add_argument("--label", help="free text appended to the run name")
    p.add_argument("--runs-dir", type=Path, default=Path("runs"))
    selection_args(p)
    p.set_defaults(fn=cmd_run)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
