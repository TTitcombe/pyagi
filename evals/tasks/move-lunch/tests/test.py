# The lunch moved (same event, same length), and nothing else in the world changed.

from check import *

event_exists(title_contains="Priya", start="2026-10-06T13:00", end="2026-10-06T14:00", count=1)
only_changed({"calendar.update": 1})
finish()
