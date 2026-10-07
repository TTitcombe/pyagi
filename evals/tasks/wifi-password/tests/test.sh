#!/bin/bash
# Grades the agent's final reply (saved by the adapter to /logs/agent/response.txt).
if grep -q "kettle-orbit-42" /logs/agent/response.txt 2>/dev/null; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
