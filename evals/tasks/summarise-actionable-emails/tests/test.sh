#!/bin/bash
# An answer task: the final reply must cover the six emails that ask Alex for something, and nothing may change.
# The checker only covers coverage (who, and Jordan's deadline). Whether the summary is concise, prioritised and
# leaves out the noise (newsletters, bank statement) is a judgement call: TODO for the A2 judge.
# Optional mentions (no check): Chris Wong's climbing check, the HR expenses deadline.
# If the checker itself crashes, score 0.
python3 - <<'PY' || echo 0 > /logs/verifier/reward.txt
from check import *

text = reply().lower()
NEEDS_INPUT = {  # email -> words, any of which shows it was covered
    "em-landlord-boiler": ("boiler", "martin", "landlord"),
    "em-priya-lunch": ("priya",),
    "em-jordan-q3": ("q3 report", "q3 summary", "board"),
    "em-invite-atlas": ("atlas",),
    "em-invite-ben": ("ben", "the lamb"),
    "em-mum-sunday": ("mum", "sunday lunch", "roast"),
}
for email_id, words in NEEDS_INPUT.items():
    expect(f"covers {email_id}", any(w in text for w in words), f"looked for any of {words}")
expect("gives Jordan's deadline (Wednesday)", "wednesday" in text, "")
nothing_changed()
finish()
PY
