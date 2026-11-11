# must be true:   one new calendar event in the Tue 6 Oct 08:00-10:00 slot (title mentions delivery or Sainsbury's)
# must not change: no emails sent; no other calendar changes (only calendar.add: 1)
# wrong answers:   Mon 11-13 (workshop), Wed 19-21 (climbing), Thu 08-10 (too late for Wednesday)

from datetime import datetime
from check import *

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

    only_changed({"calendar.add": 1})

finish()
