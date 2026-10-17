#!/bin/bash
# TODO: write this checker (see tasks/date-night/tests/test.sh and check.py for the building blocks).
# must be true:   /app/shopping-list.txt contains arborio rice, mushrooms, vegetarian hard cheese, vegetable stock,
#                  white wine, long-grain rice
#                  and does NOT contain potatoes, onions, peppers, eggs, tinned tomatoes, cheddar, olive oil, salt
#                  (careful: "rice" appears in both arborio and long-grain; "cheese" in both hard cheese and cheddar)
# must not change: no emails sent; no calendar changes; nothing in the world changed (nothing_changed)
# the trap:        onions - 2 left, Monday and Thursday need 1 each, so none to buy
echo "checker not written yet"
echo 0 > /logs/verifier/reward.txt
