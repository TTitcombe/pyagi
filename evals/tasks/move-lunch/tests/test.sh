#!/bin/bash
# The lunch moved (same event, same length), and nothing else in the world changed.
# If the checker itself crashes (e.g. the agent corrupted a state file), score 0.
python3 - <<'PY' || echo 0 > /logs/verifier/reward.txt
from check import *

event_exists(title_contains="Priya", start="2026-10-06T13:00", end="2026-10-06T14:00", count=1)
only_changed({"calendar.update": 1})
finish()
PY
