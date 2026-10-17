#!/bin/bash
# TODO: write this checker (see tasks/date-night/tests/test.sh and check.py for the building blocks).
# must be true:   one new calendar event in the Tue 6 Oct 08:00-10:00 slot (title mentions delivery or Sainsbury's)
# must not change: no emails sent; no other calendar changes (only calendar.add: 1)
# wrong answers:   Mon 11-13 (workshop), Wed 19-21 (climbing), Thu 08-10 (too late for Wednesday)
echo "checker not written yet"
echo 0 > /logs/verifier/reward.txt

python3 - <<'PY' || echo 0 > /logs/verifier/reward.txt
import re
from datetime import datetime
from check import *

events = new_events()

expect("One new event made", len(events) == 1)
expect("Event for sainsburys delivery", "sainsbury's" in event[0]["title"].lower())
PY
