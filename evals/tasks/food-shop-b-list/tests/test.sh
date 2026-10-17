#!/bin/bash
# must be true:   /app/shopping-list.txt contains arborio rice, mushrooms, vegetarian hard cheese, vegetable stock,
#                  white wine, long-grain rice
#                  and does NOT contain potatoes, onions, peppers, eggs, tinned tomatoes, cheddar, olive oil, salt
#                  (careful: "rice" appears in both arborio and long-grain; "cheese" in both hard cheese and cheddar)
# must not change: no emails sent; no calendar changes; nothing in the world changed (nothing_changed)
# the trap:        onions - 2 left, Monday and Thursday need 1 each, so none to buy
python3 - <<'PY' || echo 0 > /logs/verifier/reward.txt
import re
from datetime import datetime
from check import *

shopping_list = file_text("/app/shopping-list.txt").lower().replace("-", "").replace(" ", "")
expect("Arborio rice on list", "arboriorice" in shopping_list)
expect("Mushrooms on list", "mushrooms" in shopping_list)
expect("hard cheese on list", "vegetarianhardcheese" in shopping_list)
expect("Veg stock on list", "vegetablestock" in shopping_list or "vegstock" in shopping_list)
expect("White wine on list", "whitewine" in shopping_list)
expect("Long grain rice on list", "longgrainrice" in shopping_list)
expect("Onions NOT on list", "onion" not in shopping_list)

only_changed({})

finish()
PY
