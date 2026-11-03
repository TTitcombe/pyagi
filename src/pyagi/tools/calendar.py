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
    start: str
    end: str
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

        for event in all_events:
            if from_datetime is not None and event["start"] < from_datetime:
                continue
            if to_datetime is not None and event["start"] > to_datetime:
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

    def delete_event(self, event_id: str):
        events = self.process_events()
        if events is None:
            return f"No events to delete."

        new_events = [event for event in events if event["id"] != event_id]
        if len(new_events) == len(events):
            self.calendar_file.write_text(json.dumps(new_events))
            return f"Event {event_id} deleted."
        else :
            return f"Event {event_id} does not exist."


    def add_event(self, title: str, description: str, invitees: list[str], location: str | None, start_datetime: str):
        start_dt = datetime.fromisoformat(start_datetime)
        dt_return = start_dt.isoformat()

        if start_datetime != dt_return:
            return f"Event could not be created - {start_datetime} invalid ISO datetime for meeting."

        invitees.append(self.user_email)
        id = self.id_generation(title)

        new_event: CalendarEvent = {
            "attendees": invitees,
            "description": description,
            "title": title,
            "location": location,
            "start": start_datetime,
            "end": start_datetime, # todo: add 30min default to end, or take optional length
            "id": id,
        }

        existing_events = self.process_events() or []
        existing_events.append(new_event)

        self.calendar_file.write_text(json.dumps(existing_events))
        return f"Added event {id} at {start_datetime}."

    def edit_event(self, event_id: str, invitees: list[str] | None = None, location: str | None = None, start_datetime: str | None = None) -> str:
        event = self.get_event(event_id)
        if event is None:
            return f"Event {event_id} does not exist"

        event["attendees"] = invitees if invitees is not None else event["attendees"]
        event["location"] = location or event["location"]
        event["start"] = start_datetime or event["start"]
        event["end"] = event["start"] # TODO: get the duration

        events = [event for event in (self.process_events() or []) if event["id"] != event_id ]
        events.append(event)
        events.sort(key=lambda x: x["start"])

        self.calendar_file.write_text(json.dumps(events))
        return f"Event {event_id} updated."

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
                "parameters": {"title": "str", "description": "str", "invitees": "list[str], excluding the user", "location": "str | None", "start_datetime": "str, ISO format"}
            },
            {
                "tool_name": "delete_event",
                "description": "Delete/cancel an existing calendar event.",
                "parameters": {"event_id": "str"}
            },
            {
                "tool_name": "edit_event",
                "description": "Edit the location, start time, or attendees of an existing calendar event. Only provide data to replace.",
                "parameters": {"event_id": "str", "invitees": "list[str] | None, optional, excluding the user", "location": "str | None, optional", "start_datetime": "str | None, optional, ISO format"}
            },
        ]

    @property
    def tool_mapping(self) -> dict[str, Callable]:
        return {
            "list_events": self.list_events,
            "get_event": self.get_event,
            "add_event": self.add_event,
            "delete_event": self.delete_event,
            "edit_event": self.edit_event,
        }
