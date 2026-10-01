from pyagi_bench.grading.checks import CHECKS
from pyagi_bench.grading.context import CheckResult, GradeContext


def grade(ctx: GradeContext) -> list[CheckResult]:
    checks = list(ctx.task.checks)
    if ctx.task.side_effects != "any":
        checks.append({"side_effects": {"allowed": ctx.task.side_effects}})

    results = []
    for index, spec in enumerate(checks):
        ((name, args),) = spec.items()
        args = dict(args or {})
        group = args.pop("group", None)
        try:
            result = CHECKS[name](args, ctx)
        except Exception as e:
            result = CheckResult(name, "error", f"{type(e).__name__}: {e}")
        result.group, result.index = group, index
        results.append(result)
    return results


def outcome(results: list[dict]) -> tuple[str, float]:
    """
    Task status from its checks: any failure -> fail; else anything ungraded -> pending.
    Score is the fraction of graded checks that passed (partial credit for analysis;
    headline metrics use binary success).
    """
    statuses = [r["status"] for r in results]
    graded = [s for s in statuses if s in ("pass", "fail")]
    score = sum(s == "pass" for s in graded) / len(graded) if graded else 0.0
    if "fail" in statuses:
        return "fail", score
    if "error" in statuses:
        return "error", score
    if "pending" in statuses:
        return "pending", score
    return "pass", score
