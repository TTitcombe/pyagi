#!/bin/bash
# TODO: write this checker (see tasks/date-night/tests/test.sh and check.py for the building blocks).
# must be true:   /app/meal-plan.txt with dinners for Monday, Wednesday and Thursday (not Tuesday), all vegetarian
#                  one order email to orders@sainsburys.example naming a valid slot (Tue 08-10, or Thu 08-10),
#                  not including olive oil or salt
#                  human check: uses leftovers and doesn't reorder what's in stock; Monday needs no delivery;
#                  Thursday fits an anniversary
# must not change: one email only; at most one calendar event (a delivery hold); no other changes
#                  (only_changed({"mail.add": 1, "calendar.add": 1}))
echo "checker not written yet"
echo 0 > /logs/verifier/reward.txt
