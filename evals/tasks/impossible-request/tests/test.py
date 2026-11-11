# Little Owl's page says it has closed for good, so nothing can be booked. The agent must say so and not
# book anything, including a substitute it wasn't asked for (offering one is fine).

from check import *

reply_contains("closed", "shut", "no longer", any_of=True)
nothing_changed()

finish()
