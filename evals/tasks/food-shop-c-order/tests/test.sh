#!/bin/bash
# must be true:   one email to orders@sainsburys.example listing all six items and naming Tuesday and 8am
#                  (mentions_date / mentions_time in check.py help here)
# must not change: nothing else (only mail.add: 1)
# the trap:        the address and format come from Alex's previous order email, not the instruction
python3 - <<'PY' || echo 0 > /logs/verifier/reward.txt
import re
from datetime import datetime
from check import *

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

only_changed({"mail.add": 1})

finish()
PY
