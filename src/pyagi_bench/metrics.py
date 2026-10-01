"""
Metrics over trial records.

pass@1   mean per-task success rate: the headline number
pass^k   P(all k trials succeed), from tau-bench: reliability, which is what
         matters for an assistant you'd let send email or spend money
pass@k   P(at least one of k succeeds): capability ceiling

Confidence intervals bootstrap over *tasks*, not trials: trials of one task are
correlated, so resampling them independently would overstate certainty.
Comparisons are paired on shared tasks, which is far more sensitive than
comparing two independent means.
"""
import random
from collections import defaultdict
from math import comb
from statistics import mean

SUCCESS = "pass"


def pass_hat_k(n: int, c: int, k: int) -> float:
    return comb(c, k) / comb(n, k)


def pass_at_k(n: int, c: int, k: int) -> float:
    return 1 - comb(n - c, k) / comb(n, k)


def by_task(records: list[dict]) -> dict[str, dict]:
    """Per task: graded trials n, successes c, plus pending/error counts. Pending trials are excluded from n."""
    tasks: dict[str, dict] = defaultdict(lambda: {"n": 0, "c": 0, "pending": 0, "errors": 0, "scores": []})
    for r in records:
        t = tasks[r["task_id"]]
        t.update(category=r["category"], difficulty=r["difficulty"], tags=r["tags"])
        if r["status"] == "pending":
            t["pending"] += 1
            continue
        t["n"] += 1
        t["c"] += r["status"] == SUCCESS
        t["errors"] += r["status"] == "error"
        t["scores"].append(r["score"])
    return dict(tasks)


def bootstrap_ci(values: list[float], iters: int = 2000, seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    if len(values) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    means = sorted(mean(rng.choices(values, k=len(values))) for _ in range(iters))
    return means[int(alpha / 2 * iters)], means[int((1 - alpha / 2) * iters) - 1]


def summarise(tasks: dict[str, dict]) -> dict:
    graded = {tid: t for tid, t in tasks.items() if t["n"]}
    rates = [t["c"] / t["n"] for t in graded.values()]
    if not rates:
        return {"tasks": 0}
    max_k = min(t["n"] for t in graded.values())
    return {
        "tasks": len(graded),
        "trials": sum(t["n"] for t in graded.values()),
        "pass@1": mean(rates),
        "ci95": bootstrap_ci(rates),
        "pass^k": {k: mean(pass_hat_k(t["n"], t["c"], k) for t in graded.values()) for k in range(1, max_k + 1)},
        "pass@k": {k: mean(pass_at_k(t["n"], t["c"], k) for t in graded.values()) for k in range(1, max_k + 1)},
        "mean_score": mean(s for t in graded.values() for s in t["scores"]),
    }


def paired_delta(a: dict[str, dict], b: dict[str, dict]) -> dict | None:
    """b minus a over tasks graded in both runs."""
    shared = [tid for tid in a if tid in b and a[tid]["n"] and b[tid]["n"]]
    if not shared:
        return None
    diffs = [b[t]["c"] / b[t]["n"] - a[t]["c"] / a[t]["n"] for t in shared]
    return {"tasks": len(shared), "delta": mean(diffs), "ci95": bootstrap_ci(diffs)}
