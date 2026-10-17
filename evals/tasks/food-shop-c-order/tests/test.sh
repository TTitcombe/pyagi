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
    expect("Sent to sainsbury's", "orders@sainsburys.example" in email["to"])
    expect("Subject about food order", bool(re.compile("food|order|request|delivery|shop").search(email["subject"])))

    # TODO: LLM as a judge for body politeness and relevance

    expect("Date mentioned", mentions_date(email["body"], "2026-10-06"))
    expect("Slot mentioned", "8-10" in email["body"] or "08:00-10:00" in email["body"])

    body = email["body"].lower().replace(" ", "").replace("-", "")
    expect("expected items in body",
        "arboriorice" in body and
        "mushrooms" in body and
        ("veghardcheese" in body or "vegetarianhardcheese" in body) and
        ("vegstock" in body or "vegetablestock" in body) and
        "whitewine" in body and
        "longgrainrice" in body
    )

    expect("items we already have are not included", "oliveoil" not in body and "salt" not in body)

only_changed({"mail.add": 1})

finish()
PY
