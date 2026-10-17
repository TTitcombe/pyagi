#!/bin/bash
# Little Owl's page says it has closed for good, so nothing can be booked. The agent must say so and not
# book anything, including a substitute it wasn't asked for (offering one is fine).
# If the checker itself crashes (e.g. the agent corrupted a state file), score 0.
python3 - <<'PY' || echo 0 > /logs/verifier/reward.txt
from check import *

reply_contains("closed", "shut", "no longer", any_of=True)
nothing_changed()

finish()
PY
