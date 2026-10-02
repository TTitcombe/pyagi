import json
from collections import Counter
from pathlib import Path

from pyagi_bench.metrics import by_task, summarise


def load_results(run_dir: Path) -> list[dict]:
    return [json.loads(line) for line in (run_dir / "results.jsonl").read_text().splitlines()]


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def write_summary(run_dir: Path) -> str:
    meta = json.loads((run_dir / "run.json").read_text())
    config = meta["config"]
    records = load_results(run_dir)
    tasks = by_task(records)
    s = summarise(tasks)
    git = meta["git"]

    lines = [
        f"# {meta['name']}",
        "",
        f"- config: `{config['name']}` ({meta['config_hash']}), agent `{config['agent']['type']}`"
        + (f", model `{config['model']['name']}`" if config.get("model") else ""),
        f"- benchmark `{meta['benchmark_version']}`: {meta['selection']}, {len(meta['tasks'])} tasks × {meta['trials']} trials",
        f"- code `{git['sha'][:10]}`{' (dirty)' if git.get('dirty') else ''}, {meta['created_at']}",
        "",
    ]
    if s["tasks"]:
        lines += [
            f"**pass@1 {_pct(s['pass@1'])}** over {s['tasks']} graded tasks",
            "",
            "| k | " + " | ".join(map(str, s["pass^k"])) + " |",
            "|---|" + "---:|" * len(s["pass^k"]),
            "| pass^k | " + " | ".join(_pct(v) for v in s["pass^k"].values()) + " |",
            "",
        ]
    if pending := sum(t["pending"] for t in tasks.values()):
        lines += [f"{pending} trial(s) waiting on human-graded checks.", ""]

    failing: dict[str, Counter] = {tid: Counter() for tid in tasks}
    for r in records:
        failing[r["task_id"]].update(c["check"] for c in r["checks"] if c["status"] in ("fail", "error"))
    lines += ["| task | passed | pending | failing checks |", "|---|---:|---:|---|"]
    for tid, t in sorted(tasks.items()):
        fails = ", ".join(f"{name}×{n}" for name, n in failing[tid].most_common())
        lines.append(f"| {tid} | {t['c']}/{t['n']} | {t['pending']} | {fails} |")

    text = "\n".join(lines) + "\n"
    (run_dir / "summary.md").write_text(text)
    return text
