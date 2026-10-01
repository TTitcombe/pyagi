"""
Human grading and re-grading of saved runs.

`review` walks checks that need a person (pending `human`/`llm_judge` checks,
and optionally judge verdicts to spot-check) and appends verdicts to
reviews.jsonl. Results are never edited in place; reviews are applied on load.

`rescore` re-grades saved trajectories with the *current* task checks, so a
fixed check doesn't require re-running a slow local model.
"""
import json
import os
from datetime import datetime
from pathlib import Path

from pyagi_bench.grading import grade, outcome
from pyagi_bench.grading.context import GradeContext
from pyagi_bench.grading.materials import render
from pyagi_bench.report import load_results, write_summary
from pyagi_bench.tasks import Task


def _context(run_dir: Path, record: dict, task: Task, judge=None) -> GradeContext:
    trajectory = json.loads((run_dir / record["trajectory"]).read_text())
    return GradeContext(task, trajectory["initial"], trajectory["final"], trajectory["events"], judge)


def review(run_dir: Path, tasks: dict[str, Task], include_judged: bool = False) -> None:
    queue = [
        (r, c) for r in load_results(run_dir) for c in r["checks"]
        if (c["status"] == "pending" and r["status"] == "pending")
        or (include_judged and c["grader"].startswith("llm:") and "review" not in c)
    ]
    if not queue:
        print("Nothing to review.")
        return

    reviewer = os.environ.get("USER", "unknown")
    with (run_dir / "reviews.jsonl").open("a") as out:
        for i, (record, check) in enumerate(queue, 1):
            task = tasks[record["task_id"]]
            spec = task.checks[check["index"]] if check["index"] < len(task.checks) else {}
            args = next(iter(spec.values()), None) or {}
            rubric = args.get("rubric", check["detail"])

            print("\n" + "=" * 80)
            print(f"[{i}/{len(queue)}] {record['task_id']} trial {record['trial']} — {check['check']} ({check['grader']})")
            print("=" * 80)
            print(render(_context(run_dir, record, task), args.get("show")))
            print(f"\n## Rubric\n{rubric}")
            if check["grader"].startswith("llm:"):
                print(f"\n## Judge said: {check['status'].upper()} — {check['detail']}")

            answer = ""
            while answer not in ("p", "f", "s", "q"):
                answer = input("\n[p]ass / [f]ail / [s]kip / [q]uit > ").strip().lower()
            if answer == "q":
                break
            if answer == "s":
                continue
            note = input("note (optional) > ").strip()
            out.write(json.dumps({
                "task_id": record["task_id"],
                "trial": record["trial"],
                "index": check["index"],
                "check": check["check"],
                "verdict": "pass" if answer == "p" else "fail",
                "note": note,
                "reviewer": reviewer,
                "at": datetime.now().isoformat(timespec="seconds"),
            }) + "\n")
            out.flush()

    write_summary(run_dir)


def rescore(run_dir: Path, tasks: dict[str, Task], judge=None) -> int:
    path = run_dir / "results.jsonl"
    records = [json.loads(line) for line in path.read_text().splitlines()]
    for record in records:
        task = tasks[record["task_id"]]
        previous = {c["index"]: c for c in record["checks"]}
        checks = [c.to_dict() for c in grade(_context(run_dir, record, task, judge))]
        if judge is None:
            # Without a judge these would all reset to pending; keep the verdicts we paid for.
            checks = [
                previous[c["index"]] if c["check"] == "llm_judge" and previous.get(c["index"], {}).get("grader", "").startswith("llm:") else c
                for c in checks
            ]
        record["checks"] = checks
        status, score = outcome(record["checks"])
        record["status"] = "error" if record["error"] else status
        record["score"] = round(score, 3)

    path.rename(run_dir / f"results.{datetime.now():%Y%m%d-%H%M%S}.bak.jsonl")
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    write_summary(run_dir)
    return len(records)
