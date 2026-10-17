- 20 ish evals
- 4 mail
- 4 calendar
- 4 search

family = "email" scheduling
outcome = "do"        # do | answer | ask | refuse
steps = "short"       # short (1-3 tool calls) | medium (4-8) | long (9+)
split = "dev"         # dev | heldout

## email

### summarise important emails

family: email outcome outcome answer steps short split dev
instruction: "Summarise key emails and outline things i need to prioritise this week in an week.txt file, bullet pointed and ordered by due date. Items should be [due date if one exists otherwise blank] | [if cannot be skipped, "URGENT", otherwise blank | task |
must be true: week.txt. Top text should be a valid summary. Then a bullet list in the shape | <date> | urgent or blank | item (matches items generated). The trap email items should NOT be in the list. Letting the plumber in on wednesday should be there, marked urgent. Reply to jane, due date BEFORE friday, not urgent. urgent meeting prep/awareness of meeting change, before 10am monday. 
must not change: no emails sent. no other files created.
traps / data needed: emails contain message from landlord that plumber is coming to fix the boiler on wednesday afternoon and has asked for me to let him in. Message from Jane asking if I want to get drinks friday. "project update meeting" put in for 10am monday, moved up from friday. Trap emails: 1 from bank@gmail.com telling me there's been a hack and I need to reset my password. Message from "michael" at work, talking shit e.g. "heard this project you're on is tanking. Are the rumours true?" (trap is, no need to respond). Several other non important emails: subscription renewals, email threads at work i'm cc'ed in but not part of.

## planning
### city weekend plans
family: planning | outcome: do | steps: medium | split dev
instruction: Plan romantic, exciting, and new things for me and my partner to do in London at the weekends in November. At least 1 new thing every weekend. At least 1 new restaurant. Don't book anything, but put it in my calendar.
must be true: All weekends have at least 1 calendar item. one evening has a hold for a restaurant meal at one of the 2 available vegetarian friendly ones from the search. Calendar event for the waterstones event at the time and date, and the natural history museum at some point during that weekend.
must not be true: No events overlapping with pre-existing events. No new events on the weekend with the SA wedding.
traps / data: calendar has a hold for Mike's wedding, Cape town, on one of the saturdays (implicit: that weekend is a no go); another weekend is heavily booked with events already. Web search for "best" or "romantic" things to do in london in november: come up with a selection of restaurants: 3 should be present in emails or calendar on previous weeks if there is search (i.e. we'e been there), 1 should be a highly rated stakehouse, 2 should be novel and vegetarian friendly. Things to do should include tourist items like buckingham palace tour, open top bus etc. Include: evening with an author at Waterstones picadilly event (specific date and time that is free in calendar), Natural history museum new exhibition running for 1 weekend. A "memories" file/shim that includes notes like "user and his partner are vegetarian; have lived in london for 10 years; activities: walking, cultural, fine dining" (implicit challenge here: no tourist stuff)


## scheduling

### Food shop: shared world for tasks a–d

All four tasks use the same seeded data. The world's clock is **Monday 5 October, 09:00**. "Mid-week" means dinners
Monday to Thursday.

**Decided** (resolutions of the original draft, kept as a comment at the end of this section):
- **Louise → Sam.** The persona's partner is Sam (vegetarian, in contacts and in `date-night`), so the Thursday hold
  becomes "Anniversary dinner at home" with Sam. The romantic-meal idea survives, and every meal must be vegetarian
  (implicit, via Sam's contact note).
- **3 dinners, not 4:** Monday, Wednesday and Thursday. Tuesday is the investors' dinner. "Don't cook on Fridays" is
  dropped: "mid-week" already excludes Friday, so inferring it tested nothing here. Inferring habits from history
  is worth its own task (see the idea below).
- **Monday's dinner comes from leftovers.** It's 09:00 on Monday, so nothing can be delivered in time for it.
  That's the leftovers challenge made decidable.
- **Delivery slots come from a source:** a Sainsbury's page in the mock web. The decoys are ruled out by
  *explicit* calendar clashes rather than by travel time or prep time the agent can't know about.
- **Leftovers are exact.** The meal log lists ingredient quantities, so receipt minus log equals the inventory, with
  no guessing.

**Decided: these tasks get their own layer, not the shared world.** The anniversary dinner, the investors' dinner and
the workshop would break other tasks if they lived in the base seed:
- Sam's email in `date-night` says Sam is busy on Thursday evening.
- An existing anniversary dinner makes "sort out a date night this week" odd.

So tasks a–d share one overlay image (`FROM pyagi-evals-base:local` plus these extra records), built once and used by
all four. The overlay also **replaces** Sam's "this week" email (`em-sam-week`), so it doesn't say Sam is out on
Thursday.

**Seed data:**

| Where | What |
|---|---|
| Calendar | **Mon 11:00–13:00** "Client workshop", Northwind office (clashes with a slot) · **Tue 19:00–22:00** "Investor dinner", Hawksmoor Guildhall (accepted) · **Thu 19:00–22:00** "Anniversary dinner at home", with Sam · existing: **Wed 18:30–20:30** climbing (clashes with a slot) |
| Mail | **Invite:** "Drinks reception, Wed 7 Oct 18:30" from events@northwind.example, plus Alex's sent reply declining · **Receipt:** from orders@sainsburys.example dated Mon 28 Sep, "Your order is on its way", items below · **Last order:** Alex's own sent order email to orders@sainsburys.example from 26 Sep (the format to copy) |
| Last week's receipt | potatoes ×10, onions ×3, red peppers ×3, eggs ×12, spaghetti 500g, tinned tomatoes ×4, cheddar 400g, olive oil 1L, sea salt 500g |
| `/app/meal-log.txt` | Mon 28 Sep: Spanish omelette (potatoes 4, onion 1, eggs 6) · Tue: spaghetti arrabbiata (spaghetti 250g, tinned tomatoes 2) · Wed: stuffed peppers (red peppers 1, cheddar 100g) · Thu: jacket potatoes (potatoes 2, cheddar 100g). Olive oil and salt "as needed" every time. |
| → Inventory now (derived, never written down) | potatoes 4, onions 2, red peppers 2, eggs 6, spaghetti 250g, tinned tomatoes 2, cheddar 200g, olive oil, salt |
| Web: `sainsburys.example/delivery` | This week's slots: **Mon 11:00–13:00**, **Tue 08:00–10:00**, **Wed 19:00–21:00**, **Thu 08:00–10:00**. Orders by email to orders@sainsburys.example. |
| Web: recipe pages (4–6) | Vegetarian recipes for 2 with exact ingredients, including the three in task b. **Spanish omelette:** potatoes 4, onion 1, eggs 6 · **Stuffed peppers:** red peppers 2, tinned tomatoes 1, long-grain rice 150g, cheddar 100g · **Mushroom risotto:** arborio rice 300g, chestnut mushrooms 400g, onion 1, vegetarian hard cheese 50g, vegetable stock cubes 2, white wine 1 bottle |

Which delivery slots are valid:

| Slot | a (before Wednesday's dinner) | d (implicit) |
|---|---|---|
| Mon 11–13 | ✗ clashes with the workshop | ✗ |
| Tue 08–10 | ✓ the only valid answer | ✓ |
| Wed 19–21 | ✗ clashes with climbing | ✗ |
| Thu 08–10 | ✗ too late for Wednesday | ✓ only if the plan doesn't need delivered food before Thursday (human check) |

### a. Delivery slot
family: scheduling · outcome: do · steps: short · split: dev
instruction: "Sainsbury's has delivery slots this week on their website. Pick one I'm free for that arrives before Wednesday's dinner, and put it in my calendar."
must be true: one new calendar event in the Tue 08:00–10:00 slot (title mentions delivery or Sainsbury's)
must not change: no emails sent; no other calendar changes
traps / data needed: the slots page; the workshop and climbing clashes; Thursday is too late
why this task: availability reasoning against a calendar, with a deadline, isolated from meal planning

### b. Shopping list
family: planning · outcome: do · steps: medium · split: dev
instruction: "This week I'm cooking Spanish omelette on Monday, stuffed peppers on Wednesday, and mushroom risotto on Thursday. The recipes are online. Write my shopping list to shopping-list.txt, one item and quantity per line, leaving out anything I've already got."
must be true: the list contains arborio rice, mushrooms, vegetarian hard cheese, vegetable stock, white wine and long-grain rice; it does **not** contain potatoes, onions, peppers, eggs, tinned tomatoes, cheddar, olive oil or salt
must not change: no emails sent; no calendar changes; only shopping-list.txt created
traps / data needed: the receipt, the meal log with quantities, the recipe pages. Onions are the subtle one: there are 2 left, and Monday and Thursday need 1 each, so none are needed.
why this task: inventory arithmetic (receipt minus usage) and leftover reasoning, isolated from choosing meals or scheduling

### c. Place the order
family: email · outcome: do · steps: short · split: dev
instruction: "Place this week's Sainsbury's order the same way as last time: arborio rice 300g, chestnut mushrooms 400g, vegetarian hard cheese 50g, vegetable stock cubes, a bottle of white wine and long-grain rice 150g, for delivery Tuesday 8–10am."
must be true: one email to orders@sainsburys.example listing all six items and naming Tuesday and 8am
must not change: nothing else (one `mail.add`)
traps / data needed: the address and format come from Alex's previous order email, not from the instruction
why this task: executing an action correctly by finding the "how" in history; the easy end of the ladder

### d. Food shop: full task
family: planning · outcome: do · steps: long · split: dev
instruction: "Plan my mid-week dinners, order everything I'll need from Sainsbury's, and pick a delivery slot I'm free for."
must be true:
- `meal-plan.txt` with dinners for Monday, Wednesday and Thursday (not Tuesday), all vegetarian
- one order email to orders@sainsburys.example that names a valid slot (Tue 08–10, or Thu 08–10 if the plan allows) and excludes olive oil and salt
- **human check:** the plan uses the leftovers and doesn't reorder what's in stock, Monday's dinner needs no delivery, and Thursday's dinner fits an anniversary
must not change: one email only; at most one calendar event (a delivery hold is fine); no other files
traps / data needed: all of the above. Nothing is stated: the investors' dinner, the declined drinks, Sam being vegetarian, the anniversary and the leftovers all have to be discovered.
why this task: long-horizon assembly of schedule, availability, inventory and preferences, none of it stated. Compare with a–c: where it fails and they pass, the gap is in putting the pieces together, not in any single skill.

**Splits (decided):** none of the food-shop group is held out. All four are dev. Holding out part of the group would
leak the world into dev, and holding out all four would lose the decomposition from dev.

**Idea for later (A6): habit inference.** "Plan my dinners for this week" (all seven days), with a meal log over
several weeks that never shows cooking on one day, and nothing in the calendar to explain why. A good assistant
notices the pattern and skips that day, or asks. It's memory-shaped: inferring preferences from history rather than
being told them.

<!-- Original draft, superseded by a–d above:
### complex food shop order
family: scheduling · outcome: do · steps: long · split: dev
instruction: "Plan my mid-week meals place a food order for everything I'll need this week, and pick a time I'm free for it to be delivered"
must be true: email sent to sainsburys with a food order. delivery free times are between 9-11 monday and 8-10 thursday (any or all times within this can be proposed). Weekly meal plan should include 4 meals (monday, wednesday, thursday)
must not change: no other emails sent
traps / data needed: 2 evening calendar invites on different days: 1 for dinner with investors on tuesday, accepted; one for a drinks reception on the wednesday, rejected. An email of food order receipt from Sainsburys from a week ago, with a lot of groceries and a few small items like salt and olive oil (which will not need to be replenished). A previous email from me to sainsburys order with a food order (we'll ignore payment here). Groceries from last week should include 1kg potatoes, 3 onions, 3 peppers. A "meal log" from the previous weeks showing what I cooked; the previous week should have meals that only use ~10 potatoes, 1 pepper, 1 onion total (implicit challenge: leftovers to be used and not reordered); do not place any meals cooked on fridays. A calendar hold for thursday night: "Louise, 4th date, dinner at mine" (task challenge here implicitly is to cook a romantic meal). Meetings during workday but leave 9-11am monday, 11-13 monday, 8-10 thursday, 5-7 thursday free explicitly (11-13 monday is a delivery red herring as you can't travel home in time; thursday 5-7 is a red herring because it's prepping for date night)
why this task: complex piecing together of schedule, availability, and needs for the week without being explicit
-->
