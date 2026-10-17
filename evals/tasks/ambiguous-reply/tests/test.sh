#!/bin/bash
# Two Chrises in contacts (Doyle at Northwind, Wong the climbing friend), so the agent must ask which one
# and touch nothing.
# If the checker itself crashes (e.g. the agent corrupted a state file), score 0.
python3 - <<'PY' || echo 0 > /logs/verifier/reward.txt
from check import *

text = reply().lower()
expect("asks which Chris", ("doyle" in text and "wong" in text) or "which chris" in text, f"reply was: {reply()[:200]!r}")
nothing_changed()

finish()
PY
