#!/bin/bash
# The checks are in test.py. If it crashes (e.g. the agent corrupted a state file), score 0.
python3 "$(dirname "$0")/test.py" || echo 0 > /logs/verifier/reward.txt
