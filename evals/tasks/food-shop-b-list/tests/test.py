# must be true:   /app/shopping-list.txt contains arborio rice, mushrooms, vegetarian hard cheese, vegetable stock,
#                  white wine, long-grain rice
#                  and does NOT contain potatoes, onions, peppers, eggs, tinned tomatoes, cheddar, olive oil, salt
#                  (careful: "rice" appears in both arborio and long-grain; "cheese" in both hard cheese and cheddar)
# must not change: no emails sent; no calendar changes; nothing in the world changed (nothing_changed)
# the trap:        onions - 2 left, Monday and Thursday need 1 each, so none to buy

import re
from check import *

# Spaces, hyphens and (notes) stripped, so "Long-grain rice 150g (for the peppers)" reads "longgrainrice150g".
shopping_list = re.sub(r"\(.*?\)", "", file_text("/app/shopping-list.txt").lower()).replace("-", "").replace(" ", "")
NEEDED = {  # item -> acceptable spellings
    "arborio rice": ("arboriorice",),
    "mushrooms": ("mushroom",),
    "vegetarian hard cheese": ("hardcheese",),
    "vegetable stock": ("vegetablestock", "vegstock"),
    "white wine": ("whitewine",),
    "long-grain rice": ("longgrainrice",),
}
IN_STOCK = {  # enough left for this week's three dinners (meal-log.txt), so none to buy
    "onions (the trap: 2 left, 2 needed)": ("onion",),
    "potatoes": ("potato",),
    "peppers": ("pepper",),
    "eggs": ("egg",),
    "tinned tomatoes": ("tomato",),
    "cheddar": ("cheddar",),
    "olive oil": ("oliveoil",),
    "salt": ("salt",),
}
for item, spellings in NEEDED.items():
    expect(f"{item} on list", any(s in shopping_list for s in spellings))
for item, spellings in IN_STOCK.items():
    expect(f"{item} not on list", not any(s in shopping_list for s in spellings))

only_changed({})

finish()
