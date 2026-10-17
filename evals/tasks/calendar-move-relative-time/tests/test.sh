#!/bin/bash
# Today is Monday 5 Oct, so the day after tomorrow is Wednesday 7 Oct: the dentist (Thu 15:00-15:45) moves to
# Wed 15:00-15:45, right after quarterly planning ends. Updated in place, not recreated.
# If the checker itself crashes (e.g. the agent corrupted a state file), score 0.
python3 - <<'PY' || echo 0 > /logs/verifier/reward.txt
from check import *

event_exists(title_contains="Dentist", start="2026-10-07T15:00", end="2026-10-07T15:45", count=1)
only_changed({"calendar.update": 1})

finish()
PY
