#!/bin/bash
# Grades the end state: the new item is on the list, and every original item is still there.
for item in "oat milk" "eggs" "bread" "coffee beans"; do
  if ! grep -qi "$item" /app/shopping.txt 2>/dev/null; then
    echo "missing: $item"
    echo 0 > /logs/verifier/reward.txt
    exit 0
  fi
done
echo 1 > /logs/verifier/reward.txt
