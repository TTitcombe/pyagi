import random
import json
from datetime import datetime
from typing import TypedDict
from pathlib import Path
from pyagi.tools.base import Toolset

class EmailHighlight(TypedDict):
    id: str
    sender: str
    subject: str
    sent_at: datetime

class Email(EmailHighlight):
    to: list[str]
    body: str


class MockEmail(Toolset):
    def __init__(self, email_filepath: str | Path, user_email: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.email_filepath = Path(email_filepath)
        self.user_email = user_email

        if not self.email_filepath.exists():
            self.email_filepath.write_text("[]")

    def process_emails(self) -> list[Email] | None:
        all_text = self.email_filepath.read_text()

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

    def list_emails(self, sender: str | None, search_string: str | None, since_timestamp: str | None, limit: int = 25) -> list[EmailHighlight]:
        limit = min(100, limit)
        emails = self.process_emails() or []
        inscope_emails: list[EmailHighlight] = []

        since_dt = datetime.fromisoformat(since_timestamp) if since_timestamp is not None else None

        for email in emails:
            if sender is not None and email["sender"] != sender:
                continue

            if search_string is not None and (search_string.lower() not in email["subject"] or search_string.lower() not in email["body"]):
                continue

            if since_dt is not None and email["sent_at"] < since_dt:
                continue

            inscope_emails.append({
                "id": email["id"],
                "sender": email["sender"],
                "sent_at": email["sent_at"],
                "subject": email["subject"]
            })

            if len(emails) >= limit:
                break

        return inscope_emails

    def read_email(self, email_id: str) -> Email | None:
        emails = self.process_emails() or []

        for email in emails:
            if email["id"] == email_id:
                return email

        return None

    def send_email(self, to: list[str], subject: str, body: str) -> str:
        emails = self.process_emails() or []

        id = str(random.random() * 10000).split(".")[0]
        new_email: Email = {
            "id": id,
            "sender": self.user_email,
            "to": to,
            "subject": subject,
            "body": body,
            "sent_at": datetime.now()
        }
        emails.append(new_email)
        self.email_filepath.write_text(json.dumps(emails))

        return f"Email {id} sent to {', '.join(to)}"
