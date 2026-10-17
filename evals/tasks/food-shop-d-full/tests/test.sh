#!/bin/bash
# must be true:   /app/meal-plan.txt with dinners for Monday, Wednesday and Thursday (not Tuesday), all vegetarian
#                  one order email to orders@sainsburys.example naming a valid slot (Tue 08-10, or Thu 08-10),
#                  not including olive oil or salt
#                  human check: uses leftovers and doesn't reorder what's in stock; Monday needs no delivery;
#                  Thursday fits an anniversary
# must not change: one email only; at most one calendar event (a delivery hold); no other changes
#                  (only_changed({"mail.add": 1, "calendar.add": 1}))
python3 - <<'PY' || echo 0 > /logs/verifier/reward.txt
import re
from datetime import datetime
from check import *

only_changed({"mail.add": 1, "calendar.add": 1})

# list
shopping_list = file_text("/app/shopping-list.txt").lower().replace("-", "").replace(" ", "")
expect("Arborio rice on list", "arboriorice" in shopping_list)
expect("Mushrooms on list", "mushrooms" in shopping_list)
expect("hard cheese on list", "vegetarianhardcheese" in shopping_list)
expect("Veg stock on list", "vegetablestock" in shopping_list or "vegstock" in shopping_list)
expect("White wine on list", "whitewine" in shopping_list)
expect("Long grain rice on list", "longgrainrice" in shopping_list)

# Email to order
emails = sent_emails()
expect("Sent 1 email", len(emails) == 1)

if len(emails) > 0:
    email = emails[0]
    expect("Sent to sainsbury's", email["to"] == orders@sainsburys.com)
    expect("Subject about food order", re.compile("food|order|request|delivery|shop").search(email["subject"]))


    # TODO: LLM as a judge for body politeness and relevance

    expect("Email contains date")
    expect("Date mentioned", mentions_date(email["body"], "2026-10-06"))
    expect("Start time mentioned", mentions_time(email["body"], "08:00"))
    expect("End time mentioned", mentions_time(email["body"], "10:00"))

# calendar event
events = new_events()

expect("One new event made", len(events) == 1)

if len(events) > 0:
    title = events[0]["title"].lower().replace(" ", "")
    expect("Event for sainsburys delivery", "sainsbury" in title or "delivery" in title or "food" in title or "grocer" in title or "shop" in title)

    start = datetime.fromisoformat(events[0]["start"])
    end = datetime.fromisoformat(events[0]["end"])
    expect("Starts the correct day", start.year == 2026 and start.month == 10 and start.day == 6)
    expect("Ends on the correct day", end.year == 2026 and end.month == 10 and end.day == 6)
    expect("Time within available hours", start.hour >= 8 and (end.hour <= 9 or (end.hour == 10 and end.minute == 0)))

finish()
PY
