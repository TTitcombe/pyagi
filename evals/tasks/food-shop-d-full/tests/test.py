# must be true:   /app/meal-plan.txt with a dinner from the recipe site for Monday, Wednesday and Thursday, none on Tuesday
#                  (investor dinner), none with meat (Sam is vegetarian)
#                  Monday's dinner needs no delivery (the earliest free slot is Tuesday): Spanish omelette or spaghetti
#                  Thursday's dinner fits the anniversary: the only vegetarian "special occasion" recipe is the risotto
#                  one order email to orders@sainsburys.example naming a valid slot, with what the plan needs from the
#                  shop, and not olive oil or salt (in stock)
#                  valid slots: Tue 08-10; Thu 08-10 only if Wednesday's dinner also needs no delivery
#                  (Mon 11-13 clashes with the workshop, Wed 19-21 with climbing)
# human check:     the order uses the leftovers and doesn't reorder what's in stock (e.g. onions: 2 left)
# must not change: one email only; at most one calendar event, a delivery hold in the chosen slot

import re
from check import *

ORDERS = "orders@sainsburys.example"
RECIPES = {  # recipe -> word that identifies it in free text
    "spanish omelette": "omelette", "stuffed peppers": "stuffed pepper", "mushroom risotto": "risotto",
    "chickpea curry": "chickpea", "spaghetti": "spaghetti", "jacket potatoes": "jacket", "steak": "steak",
}
IN_STOCK = {"spanish omelette", "spaghetti"}  # cookable from what's left (meal-log.txt): no delivery needed
ORDER_NEEDS = {  # what each recipe needs from the shop: each tuple lists acceptable ways to name one item
    "stuffed peppers": [("long grain",)],
    "chickpea curry": [("chickpea",), ("coconut",), ("long grain",), ("curry",)],
    "jacket potatoes": [("beans",)],
    "mushroom risotto": [("arborio",), ("mushroom",), ("hard cheese",), ("stock",), ("wine",)],
}
SLOTS = {"Tue 08-10": ("2026-10-06T08:00", "2026-10-06T10:00"), "Thu 08-10": ("2026-10-08T08:00", "2026-10-08T10:00")}


def dinners(plan: str) -> dict[str, list[str]]:
    """Split the plan at each weekday name and list the recipes named after it, in order of mention."""
    parts = re.split(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", plan.lower())
    found: dict[str, list[str]] = {}
    for day, text in zip(parts[1::2], parts[2::2]):
        hits = sorted((text.find(word), name) for name, word in RECIPES.items() if word in text)
        found.setdefault(day, []).extend(name for _, name in hits)
    return found


# --- the meal plan
plan = dinners(file_text("/app/meal-plan.txt"))
dish = {day: (plan.get(day) or [None])[0] for day in ("monday", "wednesday", "thursday")}
expect("plan has a recipe for Monday, Wednesday and Thursday", all(dish.values()), str(dish))
expect("no dinner cooked on Tuesday (investor dinner)", not plan.get("tuesday"), str(plan.get("tuesday")))
expect("all dinners vegetarian", "steak" not in dish.values(), str(dish))
expect("Monday's dinner needs no delivery", dish["monday"] in IN_STOCK, str(dish["monday"]))
expect("Thursday's dinner fits the anniversary", dish["thursday"] == "mushroom risotto", str(dish["thursday"]))

# --- the order
email_sent(to=ORDERS, count=1)
orders = [m for m in sent_emails() if ORDERS in m["to"]]
slot = None
if orders:
    email = orders[0]
    expect("Subject about food order", bool(re.search("food|order|request|delivery|shop", email["subject"].lower())))
    text = f"{email['subject']} {email['body']}".lower().replace("-", " ")

    named = [s for s, (start, _) in SLOTS.items() if mentions_date(text, start) and mentions_time(text, start)]
    expect("order names one valid slot", len(named) == 1, f"slots named: {named}")
    slot = named[0] if len(named) == 1 else None
    if slot == "Thu 08-10":
        expect("Thursday delivery leaves Wednesday's dinner cookable", dish["wednesday"] in IN_STOCK, str(dish["wednesday"]))

    for recipe in set(dish.values()) & set(ORDER_NEEDS):
        missing = [names[0] for names in ORDER_NEEDS[recipe] if not any(n in text for n in names)]
        expect(f"order covers {recipe}", not missing, f"missing: {missing}")
    expect("order leaves out olive oil and salt", "olive oil" not in text and not re.search(r"\bsalt\b", text), "")

# --- an optional delivery hold, in the chosen slot
events = new_events()
if events and slot:
    start, end = SLOTS[slot]
    event_exists(new_only=True, start=start, end=end, count=1)

only_changed({"mail.add": 1, "calendar.add": 1})
finish()
