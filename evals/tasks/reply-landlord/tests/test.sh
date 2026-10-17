#!/bin/bash
# One email to the landlord saying Thursday, and nothing else in the world changed.
# If the checker itself crashes (e.g. the agent corrupted a state file), score 0.
python3 - <<'PY' || echo 0 > /logs/verifier/reward.txt
from check import *

email_sent(to="martin.hughes@lettings.example", body_contains="Thursday", count=1)
only_changed({"mail.add": 1})
finish()
PY
