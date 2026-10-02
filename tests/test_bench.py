from dataclasses import replace
from pathlib import Path

import pytest

from pyagi_bench.config import RunConfig
from pyagi_bench.env import Environment
from pyagi_bench.grading import grade, outcome
from pyagi_bench.grading.context import GradeContext
from pyagi_bench.grading.matchers import match
from pyagi_bench.metrics import pass_hat_k
from pyagi_bench.report import load_results
from pyagi_bench.runner import execute
from pyagi_bench.tasks import load_tasks

BENCHMARK = Path(__file__).parent.parent / "benchmark"
REFERENCE = "email/reply-landlord"


@pytest.fixture(scope="module")
def tasks():
    return {t.id: t for t in load_tasks(BENCHMARK / "tasks")}


def env_for(task) -> Environment:
    return Environment(task.build_world(BENCHMARK / "world"), [])


def status_of(task, env) -> tuple[str, list]:
    results = [r.to_dict() for r in grade(GradeContext(task, env.initial, env.world.snapshot(), env.events))]
    return outcome(results)[0], results


@pytest.mark.parametrize("value, spec, expected", [
    ("Bob@X.example", "bob@x.example", True),
    (["a@x", "b@x"], "b@x", True),
    ("2026-10-06T13:00", "2026-10-06T13:00:00", True),
    ("Thursday at 3pm", {"contains_any": ["15:00", "3pm"]}, True),
    ("Thursday at 3pm", {"contains": ["thursday", "4pm"]}, False),
])
def test_match(value, spec, expected):
    assert match(value, spec) is expected


def test_tool_errors_are_returned_and_classified(tasks):
    env = env_for(tasks[REFERENCE])
    assert "error" in env.call("nope", {})
    assert "error" in env.call("email_read", {})
    assert "error" in env.call("email_read", {"email_id": "missing"})
    assert [e["error"] for e in env.events] == ["unknown_tool", "invalid_args", "tool_error"]


def test_wrong_recipient_fails(tasks):
    task = tasks[REFERENCE]
    env = env_for(task)
    env.call("email_send", {"to": ["someone@else.example"], "subject": "Re", "body": "Thursday works"})
    assert status_of(task, env)[0] == "fail"


def test_collateral_damage_fails(tasks):
    task = tasks[REFERENCE]
    env = env_for(task)
    env.call("email_send", {"to": ["landlord@lettings.example"], "subject": "Re", "body": "Thursday works"})
    env.call("calendar_delete_event", {"event_id": "ev-placeholder-1"})
    status, results = status_of(task, env)
    assert status == "fail"
    assert next(r for r in results if r["check"] == "side_effects")["status"] == "fail"


def test_pass_hat_k():
    assert pass_hat_k(4, 4, 4) == 1
    assert pass_hat_k(4, 2, 1) == 0.5
    assert pass_hat_k(4, 3, 4) == 0


def _run(kind: str, task_list, tmp_path) -> list[dict]:
    execute(RunConfig(kind, {"agent": {"type": kind}}), task_list, 1, BENCHMARK, tmp_path / kind, kind, progress=lambda _: None)
    return load_results(tmp_path / kind)


def test_oracle_solves_every_task(tasks, tmp_path):
    results = _run("oracle", [t for t in tasks.values() if t.oracle], tmp_path)
    assert all(r["status"] in ("pass", "pending") for r in results), results


def test_doing_nothing_solves_nothing(tasks, tmp_path):
    results = _run("noop", list(tasks.values()), tmp_path)
    assert all(r["status"] == "fail" for r in results), [r["task_id"] for r in results if r["status"] != "fail"]


def test_human_check_stays_pending(tasks, tmp_path):
    task = replace(tasks[REFERENCE], checks=[*tasks[REFERENCE].checks, {"human": {"rubric": "Polite?"}}])
    assert _run("oracle", [task], tmp_path)[0]["status"] == "pending"
