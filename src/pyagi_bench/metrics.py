"""
pass@1   mean per-task success rate: the headline number
pass^k   P(all k trials of a task succeed), from tau-bench: reliability, which is
         what matters for an assistant you'd let send email or spend money

Trials still awaiting a human grade are left out of both.
"""
from collections import defaultdict
from math import comb
from statistics import mean


def pass_hat_k(n: int, c: int, k: int) -> float:
    """Unbiased estimate of P(k random trials out of n all succeed), given c successes."""
    return comb(c, k) / comb(n, k)


def by_task(records: list[dict]) -> dict[str, dict]:
    tasks: dict[str, dict] = defaultdict(lambda: {"n": 0, "c": 0, "pending": 0})
    for r in records:
        t = tasks[r["task_id"]]
        if r["status"] == "pending":
            t["pending"] += 1
        else:
            t["n"] += 1
            t["c"] += r["status"] == "pass"
    return dict(tasks)


def summarise(tasks: dict[str, dict]) -> dict:
    graded = [t for t in tasks.values() if t["n"]]
    if not graded:
        return {"tasks": 0}
    max_k = min(t["n"] for t in graded)
    return {
        "tasks": len(graded),
        "pass@1": mean(t["c"] / t["n"] for t in graded),
        "pass^k": {k: mean(pass_hat_k(t["n"], t["c"], k) for t in graded) for k in range(1, max_k + 1)},
    }
