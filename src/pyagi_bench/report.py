"""Load runs (with human reviews applied), and render summary / comparison markdown."""
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from pyagi_bench.grading import outcome
from pyagi_bench.metrics import by_task, paired_delta, summarise


def load_reviews(run_dir: Path) -> dict[tuple[str, int, int], dict]:
    path = run_dir / "reviews.jsonl"
    if not path.exists():
        return {}
    reviews = {}
    for row in map(json.loads, path.read_text().splitlines()):
        reviews[(row["task_id"], row["trial"], row["index"])] = row  # later reviews win
    return reviews


def load_results(run_dir: Path) -> list[dict]:
    """Trial records with human verdicts applied over pending (and spot-checked judge) checks."""
    reviews = load_reviews(run_dir)
    records = []
    for record in map(json.loads, (run_dir / "results.jsonl").read_text().splitlines()):
        for check in record["checks"]:
            review = reviews.get((record["task_id"], record["trial"], check["index"]))
            if review:
                check["machine_status"] = check["status"]
                check["status"] = review["verdict"]
                check["review"] = review
        if not record["error"]:  # crashed trials stay errors whatever their checks say
            record["status"], record["score"] = outcome(record["checks"])
        records.append(record)
    return records


def _pct(x: float) -> str:
    return "–" if x != x else f"{100 * x:.1f}%"


def _ci(ci: tuple[float, float]) -> str:
    return "–" if ci[0] != ci[0] else f"{_pct(ci[0])} – {_pct(ci[1])}"


def _slice_table(tasks: dict[str, dict], key: str) -> list[str]:
    groups: dict[str, dict] = defaultdict(dict)
    for tid, t in tasks.items():
        for value in (t[key] if isinstance(t[key], list) else [t[key]]):
            groups[value][tid] = t
    rows = [f"| {key} | tasks | pass@1 | 95% CI |", "|---|---:|---:|---|"]
    for value, subset in sorted(groups.items()):
        s = summarise(subset)
        if s["tasks"]:
            rows.append(f"| {value} | {s['tasks']} | {_pct(s['pass@1'])} | {_ci(s['ci95'])} |")
    return rows


def render_summary(run_dir: Path) -> str:
    meta = json.loads((run_dir / "run.json").read_text())
    records = load_results(run_dir)
    tasks = by_task(records)
    s = summarise(tasks)
    config = meta["config"]
    git = meta["git"]
    models = meta.get("models", {})

    lines = [
        f"# {meta['name']}",
        "",
        "| | |",
        "|---|---|",
        f"| config | `{meta['config_name']}` ({meta['config_hash']}) — agent `{config['agent']['type']}` |",
        *(f"| {role} model | `{m['name']}` {('`' + m['digest'].removeprefix('sha256:')[:12] + '`') if m.get('digest') else ''} |" for role, m in models.items()),
        f"| benchmark | `{meta['benchmark_version']}` — {meta['selection']}, {len(meta['tasks'])} tasks × {meta['trials']} trials |",
        f"| code | `{git['sha'][:10]}`{' (dirty)' if git.get('dirty') else ''} |",
        f"| when | {meta['created_at']} → {meta.get('finished_at', 'unfinished')} |",
        "",
    ]

    if not s["tasks"]:
        return "\n".join(lines + ["No graded trials yet."])

    # Checks on trials that already failed don't need a human.
    pending = sum(c["status"] == "pending" for r in records if r["status"] == "pending" for c in r["checks"])
    errors = sum(r["status"] == "error" for r in records)
    collateral = [c["status"] == "fail" for r in records for c in r["checks"] if c["check"] == "side_effects"]

    lines += [
        "## Headline",
        "",
        f"**pass@1 {_pct(s['pass@1'])}** (95% CI {_ci(s['ci95'])}) over {s['tasks']} tasks, {s['trials']} graded trials",
        "",
        "| k | " + " | ".join(map(str, s["pass^k"])) + " |",
        "|---|" + "---:|" * len(s["pass^k"]),
        "| pass^k (all k succeed) | " + " | ".join(_pct(v) for v in s["pass^k"].values()) + " |",
        "| pass@k (any succeeds) | " + " | ".join(_pct(v) for v in s["pass@k"].values()) + " |",
        "",
        f"- mean partial score: {_pct(s['mean_score'])}",
        f"- collateral damage (unexpected world changes): {_pct(mean(collateral)) if collateral else '–'} of trials",
        f"- crashed trials: {errors}",
        f"- checks awaiting human review: {pending}" + (" → `bench review`" if pending else ""),
        "",
    ]

    groups: dict[str, list[bool]] = defaultdict(list)
    for r in records:
        for c in r["checks"]:
            if c.get("group") and c["status"] in ("pass", "fail"):
                groups[c["group"]].append(c["status"] == "pass")
    if groups:
        lines += ["## Check groups", "", "| group | checks | pass rate |", "|---|---:|---:|"]
        lines += [f"| {g} | {len(v)} | {_pct(mean(v))} |" for g, v in sorted(groups.items())]
        lines.append("")

    judged = [c for r in records for c in r["checks"] if c.get("review") and c.get("machine_status") in ("pass", "fail")]
    if judged:
        agree = mean(c["machine_status"] == c["status"] for c in judged)
        lines += [f"Judge–human agreement: {_pct(agree)} on {len(judged)} spot-checked verdicts", ""]

    lines += ["## By category", "", *_slice_table(tasks, "category"), ""]
    lines += ["## By difficulty", "", *_slice_table(tasks, "difficulty"), ""]
    lines += ["## By tag", "", *_slice_table(tasks, "tags"), ""]

    metrics = [r["metrics"] for r in records]
    tool_calls = sum(m["tool_calls"] for m in metrics)
    tool_errors = Counter()
    for m in metrics:
        tool_errors.update(m["tool_errors"])
    lines += [
        "## Cost & tool use (per trial)",
        "",
        f"- wall clock: {mean(m['wall_seconds'] for m in metrics):.1f}s mean, {max(m['wall_seconds'] for m in metrics):.1f}s max",
        f"- agent turns: {mean(m['turns'] for m in metrics):.1f}; tool calls: {tool_calls / len(metrics):.1f}",
        f"- tool call errors: {_pct(sum(tool_errors.values()) / tool_calls) if tool_calls else '–'}"
        + (f" ({', '.join(f'{k}: {v}' for k, v in tool_errors.most_common())})" if tool_errors else ""),
    ]
    if any("model_calls" in m for m in metrics):
        lines.append(f"- model calls: {mean(m.get('model_calls', 0) for m in metrics):.1f}; model time: {mean(m.get('model_seconds', 0) for m in metrics):.1f}s")
    lines.append("")

    failing: dict[str, Counter] = defaultdict(Counter)
    for r in records:
        failing[r["task_id"]].update(c["check"] for c in r["checks"] if c["status"] in ("fail", "error"))
    lines += ["## Tasks", "", "| task | difficulty | passed | score | failing checks |", "|---|---|---:|---:|---|"]
    for tid, t in sorted(tasks.items()):
        fails = ", ".join(f"{name}×{n}" for name, n in failing[tid].most_common())
        pend = f" (+{t['pending']} pending)" if t["pending"] else ""
        score = _pct(mean(t["scores"])) if t["scores"] else "–"
        lines.append(f"| {tid} | {t['difficulty']} | {t['c']}/{t['n']}{pend} | {score} | {fails} |")

    return "\n".join(lines) + "\n"


def write_summary(run_dir: Path) -> str:
    text = render_summary(run_dir)
    (run_dir / "summary.md").write_text(text)
    return text


def render_compare(run_dirs: list[Path]) -> str:
    runs = [(d, json.loads((d / "run.json").read_text()), by_task(load_results(d))) for d in run_dirs]
    versions = {meta["benchmark_version"] for _, meta, _ in runs}
    lines = ["# Comparison", ""]
    if len(versions) > 1:
        lines += [f"> **Warning:** runs use different benchmark versions {sorted(versions)}; only shared tasks are paired.", ""]

    header = "| | " + " | ".join(f"`{meta['name']}`" for _, meta, _ in runs) + " |"
    lines += [header, "|---|" + "---:|" * len(runs)]
    summaries = [summarise(tasks) for _, _, tasks in runs]
    lines.append("| pass@1 | " + " | ".join(_pct(s.get("pass@1", float("nan"))) for s in summaries) + " |")
    lines.append("| tasks | " + " | ".join(str(s["tasks"]) for s in summaries) + " |")

    categories = sorted({t["category"] for _, _, tasks in runs for t in tasks.values()})
    for cat in categories:
        cells = [summarise({k: t for k, t in tasks.items() if t["category"] == cat}) for _, _, tasks in runs]
        lines.append(f"| {cat} | " + " | ".join(_pct(c.get("pass@1", float("nan"))) for c in cells) + " |")

    _, base_meta, base = runs[0]
    lines += ["", f"## Paired difference vs `{base_meta['name']}`", ""]
    for _, meta, tasks in runs[1:]:
        d = paired_delta(base, tasks)
        if d:
            lines.append(
                f"- `{meta['name']}`: {d['delta'] * 100:+.1f} pts (95% CI {d['ci95'][0] * 100:+.1f} – {d['ci95'][1] * 100:+.1f}) over {d['tasks']} shared tasks"
            )
            flips = [
                f"{tid} ({base[tid]['c']}/{base[tid]['n']} → {tasks[tid]['c']}/{tasks[tid]['n']})"
                for tid in sorted(set(base) & set(tasks))
                if base[tid]["n"] and tasks[tid]["n"] and base[tid]["c"] / base[tid]["n"] != tasks[tid]["c"] / tasks[tid]["n"]
            ]
            if flips:
                lines.append("  - changed: " + "; ".join(flips))
    return "\n".join(lines) + "\n"
