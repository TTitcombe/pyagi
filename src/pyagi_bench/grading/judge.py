import json

from pyagi_bench import llm
from pyagi_bench.grading.context import CheckResult, GradeContext
from pyagi_bench.grading.materials import render

PROMPT = """You are grading whether an AI personal assistant did its job well.

The user's request(s):
{prompts}

Rubric (the ONLY criteria to apply):
{rubric}

What happened:
{materials}

Judge strictly against the rubric. Respond with JSON only:
{{"reasoning": "<two or three sentences>", "pass": true or false}}"""


class Judge:
    """
    LLM-as-judge for checks that can't be verified from state. Judge verdicts are
    labelled with the judge model so they're never mistaken for human grades; use
    `bench review --judged` to spot-check them and measure agreement.
    """

    def __init__(self, model: str, url: str | None = None, options: dict | None = None):
        self.model = model
        self.url = url
        self.options = options or {"temperature": 0}

    def grade(self, rubric: str, ctx: GradeContext, sections: list[str] | None) -> CheckResult:
        prompts = "\n".join(f"- {s.prompt.strip()}" for s in ctx.task.sessions)
        prompt = PROMPT.format(prompts=prompts, rubric=rubric.strip(), materials=render(ctx, sections))
        grader = f"llm:{self.model}"
        try:
            raw = llm.chat(self.model, [{"role": "user", "content": prompt}], url=self.url, json_mode=True, options=self.options)
            verdict = json.loads(raw)
            status = "pass" if verdict["pass"] is True else "fail"
            return CheckResult("llm_judge", status, verdict.get("reasoning", ""), grader=grader)
        except Exception as e:
            return CheckResult("llm_judge", "error", f"judge failed: {e}", grader=grader)
