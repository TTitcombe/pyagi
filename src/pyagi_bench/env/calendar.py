from pyagi_bench.env.tools import Param, ToolError, tool
from pyagi_bench.env.util import fmt, parse_when
from pyagi_bench.env.world import World


def _get(world: World, event_id: str) -> dict:
    event = world.collection("events").get(event_id)
    if event is None:
        raise ToolError(f"No event with id '{event_id}'")
    return event


def _check_times(start: str, end: str) -> tuple[str, str]:
    s, e = parse_when(start), parse_when(end)
    if e <= s:
        raise ToolError("Event end must be after its start")
    return fmt(s), fmt(e)


@tool(
    "calendar_list_events", "calendar",
    "List events overlapping a time range, in start order. A date-only end includes that whole day.",
    start=Param("string", "Range start, YYYY-MM-DD or YYYY-MM-DDTHH:MM"),
    end=Param("string", "Range end, YYYY-MM-DD or YYYY-MM-DDTHH:MM"),
)
def calendar_list_events(world: World, start: str, end: str):
    lo, hi = parse_when(start), parse_when(end, end_of_day=True)
    events = [
        e for e in world.collection("events").values()
        if parse_when(e["start"]) < hi and parse_when(e["end"]) > lo
    ]
    return sorted(events, key=lambda e: e["start"])


@tool(
    "calendar_create_event", "calendar", "Create a calendar event. Attendees receive an invitation.", mutates=True,
    title=Param("string", "Event title"),
    start=Param("string", "Start, YYYY-MM-DDTHH:MM local time"),
    end=Param("string", "End, YYYY-MM-DDTHH:MM local time"),
    attendees=Param("array", "Attendee email addresses", required=False, items="string"),
    location=Param("string", "Location", required=False),
    description=Param("string", "Description", required=False),
)
def calendar_create_event(world: World, title, start, end, attendees=None, location="", description=""):
    start, end = _check_times(start, end)
    event = {
        "id": world.new_id("event"),
        "title": title,
        "start": start,
        "end": end,
        "attendees": attendees or [],
        "location": location,
        "description": description,
        "organizer": world.user["email"],
    }
    world.collection("events")[event["id"]] = event
    return {"status": "created", "event": event}


@tool(
    "calendar_update_event", "calendar", "Change fields of an existing event. Omitted fields are unchanged.", mutates=True,
    event_id=Param("string", "Id of the event"),
    title=Param("string", "New title", required=False),
    start=Param("string", "New start, YYYY-MM-DDTHH:MM", required=False),
    end=Param("string", "New end, YYYY-MM-DDTHH:MM", required=False),
    attendees=Param("array", "New full attendee list", required=False, items="string"),
    location=Param("string", "New location", required=False),
    description=Param("string", "New description", required=False),
)
def calendar_update_event(world: World, event_id: str, **changes):
    event = _get(world, event_id)
    if not changes:
        raise ToolError("Nothing to update: pass at least one field to change")
    start, end = _check_times(changes.get("start", event["start"]), changes.get("end", event["end"]))
    event.update(changes, start=start, end=end)
    return {"status": "updated", "event": event}


@tool(
    "calendar_delete_event", "calendar", "Delete an event. Attendees are notified.", mutates=True,
    event_id=Param("string", "Id of the event"),
)
def calendar_delete_event(world: World, event_id: str):
    _get(world, event_id)
    del world.collection("events")[event_id]
    return {"status": "deleted", "id": event_id}
