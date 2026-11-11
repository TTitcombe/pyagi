#!/bin/bash
mail send --to orders@sainsburys.example \
  --subject "Order for delivery Tuesday 6 October, 8-10am" \
  --reply-to em-sainsburys-last-order \
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
