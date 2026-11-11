# One email to the landlord saying Thursday, and nothing else in the world changed.

from check import *

email_sent(to="martin.hughes@lettings.example", body_contains="Thursday", count=1)
only_changed({"mail.add": 1})
finish()
