import random
import json
from typing import Callable, TypedDict, Union, Literal
from pyagi.types import Tool
import os
import statistics
from pathlib import Path
from pyagi.tools.base import Toolset
from datetime import datetime

#
#   {
#     "id": "ev-past-greenhouse",
#     "title": "Date night",
#     "start": "2026-09-11T19:00",
#     "end": "2026-09-11T21:00",
#     "attendees": [
#       "sam.patel@mail.example"
#     ],
#     "location": "The Greenhouse Kitchen, Camden",
#     "description": "Booked by email"
#   },

class CalendarEvent(TypedDict):
    id: str
    title: str
    start: datetime
    end: datetime
    attendees: list[str]
    location: str | None
    description: str | None


class MockCalendar(Toolset):
    """
    Mock calendar service which expects calendar data to be mounted at <...>.
    """

    def __init__(self, calendar_filepath: Path | str, user_email: str, do_create_calendar_file: bool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calendar_file = Path(calendar_filepath)
        self.user_email = user_email

        if not self.calendar_file.exists() and do_create_calendar_file:
            self.calendar_file.write_text("[]")

        if not self.calendar_file.exists() or not self.calendar_file.is_file():
            raise Exception(f"{str(self.calendar_file)} does not exist or is not a file")

    def process_events(self) -> list[CalendarEvent] | None:
        all_text = self.calendar_file.read_text()

        try:
            as_json = json.loads(all_text)
        except Exception as e:
            # TODO: log error here?
            return None

        if not isinstance(as_json, list):
            # TODO: log error here?
            return None

        # TODO: validate that each item is a calendar event kind
        return as_json

    @staticmethod
    def id_generation(title: str) -> str:
        base = "-".join(title.lower().split(" ")[:2])
        rand_num = str(100 * random.random())[:3]
        return base + "-" + rand_num

    @staticmethod
    def to_datetime(dt: str | None) -> datetime | None:
        if dt is None:
            return None

        t = datetime.fromisoformat(dt)
        return t

    def list_events(self, *, from_datetime: str | None, to_datetime: str | None, limit: int = 100) -> list[CalendarEvent]:
        all_events = self.process_events()
        events: list[CalendarEvent] = []

        if all_events is None:
            return [] # TODO: raise/log error here?

        from_dt = self.to_datetime(from_datetime)
        to_dt = self.to_datetime(to_datetime)

        for event in all_events:
            if from_dt is not None and event["start"] < from_dt:
                continue
            if to_dt is not None and event["start"] > to_dt:
                continue

            events.append(event)
            if len(events) >= limit:
                break

        return events

    def get_event(self, event_id: str) -> CalendarEvent | None:
        all_events = self.process_events()

        for event in (all_events or []):
            if event["id"] == event_id:
                return event

        return None

    def add_event(self, title: str, description: str, invitees: list[str], location: str | None, start_timestamp: str):
        start_dt = datetime.fromisoformat(start_timestamp)
        invitees.append(self.user_email)
        id = self.id_generation(title)

        new_event: CalendarEvent = {
            "attendees": invitees,
            "description": description,
            "title": title,
            "location": location,
            "start": start_dt,
            "end": start_dt, # todo: add 30min default to end, or take optional length
            "id": id,
        }

        existing_events = self.process_events() or []
        existing_events.append(new_event)

        self.calendar_file.write_text(json.dumps(existing_events))
        return f"Added event {id} at {start_dt}."

    # @staticmethod
    # def edit_event(event_id: str, *, from_datetime: str | None, to_datetime: str | None, description: str | None, location: str | None, invitees: list[str] | None):
    #     ...

    @property
    def tools(self) -> list[Tool]:
        return [
            {
                "tool_name": "list_events",
                "description": "List events in the calendar. If either timestamps are provided (ISO format), return events that take place within the bounds",
                "parameters": {"from_datetime": "str | None, ISO format", "to_datetime": "str | None, ISO format", "limit": "int | None, default 100"}
            },
            {
                "tool_name": "get_event",
                "description": "Read an event by a given id. Returns None if no event has that id.",
                "parameters": {"event_id": "str"}
            },
            {
                "tool_name": "add_event",
                "description": "Create a new calendar event and invite attendees.",
                "parameters": {"title": "str", "description": "str", "invitees": "list[str], excluding the user", "location": "str | None", "start_timestamp": "str, ISO format"}
            },
        ]

    @property
    def tool_mapping(self) -> dict[str, Callable]:
        return {
            "list_events": self.list_events,
            "get_event": self.get_event,
            "add_event": self.add_event,
        }
