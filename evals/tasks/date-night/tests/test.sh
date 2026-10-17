#!/bin/bash
# Long-horizon planning task, graded on rules rather than one fixed answer:
#   - Sam's free:   Sam's email says Tuesday and Thursday evenings are out
#   - Alex is free: no clash in the calendar (climbing Wednesday, leaving drinks Friday)
#   - Venue:        new to them (calendar/email history: Dishoom, Greenhouse Kitchen, Padella),
#                   vegetarian-friendly, takes bookings, open that day (web pages)
#   - Booked:       an email to the venue's booking address with the date, time and party size
#   - Todo ticked:  todo.txt mentions the venue
# If the checker itself crashes (e.g. the agent corrupted a state file), score 0.
python3 - <<'PY' || echo 0 > /logs/verifier/reward.txt
import re
from datetime import datetime
from check import *

SAM = "sam.patel@mail.example"
SAM_BUSY = {"Tuesday", "Thursday"}
VALID_VENUES = {
    "verdant": {"email": "bookings@verdant.example",
                "days": {"Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}, "seating": ("18:00", "21:00")},
    "osteria lupa": {"email": "table@osterialupa.example",
                     "days": {"Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"}, "seating": ("17:30", "21:30")},
}

dates = [e for e in new_events() if SAM in [a.lower() for a in e["attendees"]]]
expect("one new calendar event with Sam", len(dates) == 1, f"{len(dates)} new event(s) with Sam")
venue_email = None

if dates:
    event = dates[0]
    start = datetime.fromisoformat(event["start"])
    day, time = f"{start:%A}", f"{start:%H:%M}"
    where = f"{event['title']} {event['location']}".lower()
    venue = next((name for name in VALID_VENUES if name in where), None)

    expect("it's this week", "2026-10-05" <= start.date().isoformat() <= "2026-10-11", event["start"])
    expect("Sam is free that evening", day not in SAM_BUSY, day)
    expect("no clash in the calendar", not clashes(event), str([e["title"] for e in clashes(event)]))
    expect("venue is new to them, vegetarian-friendly and bookable", venue is not None, f"event says: {where!r}")

    if venue:
        rules = VALID_VENUES[venue]
        venue_email = rules["email"]
        lo, hi = rules["seating"]
        expect("venue is open then", day in rules["days"] and lo <= time <= hi, f"{venue}: {day} {time}")

        bookings = [m for m in sent_emails() if venue_email in [a.lower() for a in m["to"]]]
        expect("booking email sent to the venue", len(bookings) == 1, f"{len(bookings)} email(s) to {venue_email}")
        if bookings:
            text = f"{bookings[0]['subject']} {bookings[0]['body']}"
            expect("booking gives date, time and party of 2",
                   mentions_date(text, event["start"]) and mentions_time(text, event["start"])
                   and re.search(r"\b(2|two)\b", text.lower()) is not None,
                   text[:200])

        expect("todo list ticked off", venue in file_text("/app/todo.txt").lower(), file_text("/app/todo.txt"))

recipients = {a.lower() for m in sent_emails() for a in m["to"] + m["cc"]}
expect("emails only went to the venue or Sam", recipients <= {venue_email, SAM}, str(sorted(recipients)))
only_changed({"calendar.add": 1, "mail.add": 2})
finish()
PY
