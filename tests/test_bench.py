import json
from dataclasses import replace
from pathlib import Path

import pytest

from pyagi_bench.config import RunConfig, load_config
from pyagi_bench.env import Environment
from pyagi_bench.grading import grade, outcome
from pyagi_bench.grading.context import GradeContext
from pyagi_bench.grading.matchers import match, match_record
from pyagi_bench.metrics import pass_at_k, pass_hat_k
from pyagi_bench.report import load_results
from pyagi_bench.runner import execute
from pyagi_bench.tasks import load_tasks

BENCHMARK = Path(__file__).parent.parent / "benchmark"


@pytest.fixture(scope="module")
def tasks():
    return {t.id: t for t in load_tasks(BENCHMARK / "tasks")}


def env_for(task) -> Environment:
    return Environment(task.build_world(BENCHMARK / "worlds"), [])


# --- matchers ----------------------------------------------------------------

@pytest.mark.parametrize("value, spec, expected", [
    ("Bob@X.example", "bob@x.example", True),
    (["a@x", "b@x"], "b@x", True),
    (["a@x", "b@x"], ["B@x", "a@x"], True),
    (["a@x", "b@x"], ["a@x"], False),
    ("2026-10-06T13:00", "2026-10-06T13:00:00", True),
    ("Thursday at 3pm", {"contains_any": ["15:00", "3pm"]}, True),
    ("Thursday at 3pm", {"contains": ["thursday", "4pm"]}, False),
    (["a@x", "b@x"], {"includes": ["a@x"], "excludes": ["c@x"]}, True),
    ("2026-10-11T16:00", {"gte": "2026-10-11T14:00", "lte": "2026-10-11T16:30"}, True),
    (24.0, {"lte": 50}, True),
])
def test_match(value, spec, expected):
    assert match(value, spec) is expected


def test_match_record_requires_field():
    assert not match_record({"to": ["a@x"]}, {"subject": "hi"})


# --- environment -------------------------------------------------------------

def test_tool_errors_are_returned_and_classified(tasks):
    env = env_for(tasks["email/dentist-time"])
    assert "error" in env.call("nope", {})
    assert "error" in env.call("email_read", {})
    assert "error" in env.call("email_read", {"email_id": "missing"})
    assert "error" in env.call("email_send", {"to": "not-a-list", "subject": "s", "body": "b"})
    assert [e["error"] for e in env.events] == ["unknown_tool", "invalid_args", "tool_error", "invalid_args"]


def test_null_optional_args_are_ignored(tasks):
    env = env_for(tasks["email/dentist-time"])
    assert isinstance(env.call("email_search", {"query": "dentist", "folder": None}), list)


def test_side_effects_budget(tasks):
    task = tasks["calendar/move-lunch"]
    env = env_for(task)
    env.call("calendar_update_event", {"event_id": "ev-lunch-priya", "start": "2026-10-06T13:00", "end": "2026-10-06T14:00"})
    env.call("email_send", {"to": ["priya.shah@northwind.example"], "subject": "moved", "body": "1pm"})
    results = grade(GradeContext(task, env.initial, env.world.snapshot(), env.events))
    by_name = {r.check: r for r in results}
    assert by_name["event_exists"].status == "pass"
    assert by_name["side_effects"].status == "fail"
    assert "emails.add" in by_name["side_effects"].detail


def test_wrong_answer_fails_its_check(tasks):
    task = tasks["calendar/move-lunch"]
    env = env_for(task)
    env.call("calendar_update_event", {"event_id": "ev-lunch-priya", "start": "2026-10-06T14:00", "end": "2026-10-06T15:00"})
    status, _ = outcome([r.to_dict() for r in grade(GradeContext(task, env.initial, env.world.snapshot(), env.events))])
    assert status == "fail"


# --- metrics -----------------------------------------------------------------

def test_pass_k():
    assert pass_hat_k(4, 4, 4) == 1
    assert pass_hat_k(4, 2, 1) == 0.5
    assert pass_hat_k(4, 3, 4) == 0
    assert pass_at_k(4, 1, 4) == 1
    assert pass_at_k(4, 0, 2) == 0


# --- config ------------------------------------------------------------------

def test_config_extends_overrides_and_env(tmp_path, monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://gpu-box:11434")
    (tmp_path / "base.yaml").write_text("agent: {type: noop, max_steps: 3}\nmodel: {name: a, url: '${OLLAMA_URL:-x}'}\n")
    (tmp_path / "child.yaml").write_text("extends: base.yaml\nmodel: {name: b}\n")
    config = load_config(tmp_path / "child.yaml", ["agent.max_steps=9"])
    assert config.name == "child"
    assert config.model == {"name": "b", "url": "http://gpu-box:11434"}
    assert config.agent["max_steps"] == 9


# --- the benchmark itself ----------------------------------------------------

def _run(kind: str, task_list, tmp_path) -> list[dict]:
    execute(RunConfig(kind, {"agent": {"type": kind}}), task_list, 1, BENCHMARK, tmp_path / kind, kind, progress=lambda _: None)
    return load_results(tmp_path / kind)


def test_oracle_solves_every_task(tasks, tmp_path):
    results = _run("oracle", [t for t in tasks.values() if t.oracle], tmp_path)
    failed = {r["task_id"]: [c for c in r["checks"] if c["status"] != "pass"] for r in results if r["status"] not in ("pass", "pending")}
    assert not failed


def test_noop_solves_nothing(tasks, tmp_path):
    results = _run("noop", list(tasks.values()), tmp_path)
    assert all(r["status"] == "fail" for r in results), [r["task_id"] for r in results if r["status"] != "fail"]


def test_rescore_uses_current_checks(tasks, tmp_path):
    from pyagi_bench.review import rescore

    task = tasks["calendar/move-lunch"]
    assert _run("oracle", [task], tmp_path)[0]["status"] == "pass"
    stricter = replace(task, checks=[{"event_exists": {"title": {"contains": "Priya"}, "start": "2026-10-06T14:00"}}])
    rescore(tmp_path / "oracle", {task.id: stricter})
    assert load_results(tmp_path / "oracle")[0]["status"] == "fail"
    assert json.loads((tmp_path / "oracle" / "run.json").read_text())["tasks"] == [task.id]


# --- model-backed graders (model call stubbed) -------------------------------

def test_judge_verdict_is_labelled(tasks, monkeypatch):
    from pyagi_bench import llm
    from pyagi_bench.grading.judge import Judge

    monkeypatch.setattr(llm, "chat", lambda *a, **k: '{"reasoning": "accurate and concise", "pass": true}')
    task = tasks["email/q3-summary"]
    env = env_for(task)
    result = Judge("judge:1b").grade("Is it good?", GradeContext(task, env.initial, env.world.snapshot(), env.events), None)
    assert (result.status, result.grader) == ("pass", "llm:judge:1b")

    monkeypatch.setattr(llm, "chat", lambda *a, **k: "not json")
    result = Judge("judge:1b").grade("Is it good?", GradeContext(task, env.initial, env.world.snapshot(), env.events), None)
    assert result.status == "error"


def test_llm_user_stops_on_sentinel(monkeypatch):
    from pyagi_bench import llm
    from pyagi_bench.user_sim import STOP, LLMUser

    replies = iter(["Chris Doyle please", f"Thanks! {STOP}"])
    monkeypatch.setattr(llm, "chat", lambda *a, **k: next(replies))
    user = LLMUser({"persona": "busy", "goal": "book chris"}, "Book Chris", {"model": "sim:1b"})
    assert user.reply("Which Chris?") == "Chris Doyle please"
    assert user.reply("Booked.") is None
