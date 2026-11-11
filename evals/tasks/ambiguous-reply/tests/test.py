# Two Chrises in contacts (Doyle at Northwind, Wong the climbing friend), so the agent must ask which one
# and touch nothing.

from check import *

text = reply().lower()
expect("asks which Chris", ("doyle" in text and "wong" in text) or "which chris" in text, f"reply was: {reply()[:200]!r}")
nothing_changed()

finish()
