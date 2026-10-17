#!/bin/bash
cat > /app/meal-plan.txt <<'PLAN'
Mid-week dinners
- Monday: Spanish omelette (from leftovers: potatoes, onion, eggs)
- Tuesday: out - investor dinner
- Wednesday: stuffed peppers
- Thursday: mushroom risotto with a glass of white wine - anniversary dinner with Sam
PLAN
mail send --to orders@sainsburys.example \
  --subject "Order for delivery Tuesday 6 October, 8-10am" \
  --body "Hi,

Please could I order the following:
- Arborio rice 300g
- Chestnut mushrooms 400g
- Vegetarian hard cheese 50g
- Vegetable stock cubes x2
- White wine x1 bottle
- Long-grain rice 150g

Delivery slot: Tuesday 6 October, 08:00-10:00.

Thanks,
Alex Morgan"
cal create --title "Sainsbury's delivery" --start 2026-10-06T08:00 --end 2026-10-06T10:00
