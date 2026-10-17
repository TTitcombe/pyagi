#!/bin/bash
# Mail rejects a bare name, so the agent must look Jordan up in contacts first. One email to Jordan that says
# Alex is late and which meeting.
# If the checker itself crashes (e.g. the agent corrupted a state file), score 0.
python3 - <<'PY' || echo 0 > /logs/verifier/reward.txt
from check import *

JORDAN = "jordan.lee@northwind.example"
ONE_TO_ONE = ("1:1", "1-1", "1 on 1", "1-on-1", "one-to-one", "one to one", "one-on-one", "one on one")

email_sent(to=JORDAN, count=1)
emails = [m for m in sent_emails() if JORDAN in m["to"]]
if emails:
    text = f"{emails[0]['subject']} {emails[0]['body']}".lower()
    expect("says Alex is late", "late" in text, text[:200])
    expect("names the 1:1", any(t in text for t in ONE_TO_ONE), text[:200])
only_changed({"mail.add": 1})

finish()
PY
