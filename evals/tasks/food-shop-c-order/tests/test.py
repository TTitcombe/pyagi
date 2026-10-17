# must be true:   one email to orders@sainsburys.example listing all six items and naming Tuesday and 8am
#                  (mentions_date / mentions_time in check.py help here)
# must not change: nothing else (only mail.add: 1)
# the trap:        the address and format come from Alex's previous order email, not the instruction

import re
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
    ITEMS = {  # item -> acceptable spellings
        "arborio rice": ("arboriorice",),
        "mushrooms": ("mushroom",),
        "vegetarian hard cheese": ("veghardcheese", "vegetarianhardcheese"),
        "vegetable stock": ("vegstock", "vegetablestock"),
        "white wine": ("whitewine",),
        "long-grain rice": ("longgrainrice",),
    }
    for item, spellings in ITEMS.items():
        expect(f"{item} in order", any(s in body for s in spellings))
    for item in ("oliveoil", "salt"):  # on last time's order, but still in stock
        expect(f"{item} not in order", item not in body)

only_changed({"mail.add": 1})

finish()
