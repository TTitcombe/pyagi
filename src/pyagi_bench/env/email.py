from pyagi_bench.env.tools import Param, ToolError, tool
from pyagi_bench.env.util import fmt, matches_query
from pyagi_bench.env.world import World

FOLDERS = ("inbox", "sent", "drafts", "archive", "trash")


def _summary(e: dict) -> dict:
    return {
        "id": e["id"],
        "folder": e["folder"],
        "from": e["from"],
        "to": e["to"],
        "subject": e["subject"],
        "date": e["date"],
        "snippet": e["body"][:120],
    }


def _get(world: World, email_id: str) -> dict:
    email = world.collection("emails").get(email_id)
    if email is None:
        raise ToolError(f"No email with id '{email_id}'")
    return email


def _check_addresses(addresses: list[str]) -> None:
    if not addresses:
        raise ToolError("At least one recipient is required")
    bad = [a for a in addresses if "@" not in a]
    if bad:
        raise ToolError(f"Invalid email address(es): {bad}. Look up contacts to find addresses.")


@tool(
    "email_search", "email",
    "Search the mailbox, newest first. Every word of the query must appear in the sender, "
    "recipients, subject or body. Searches all folders except trash unless a folder is given.",
    query=Param("string", "Words to search for. Empty matches everything.", required=False),
    folder=Param("string", "Only search this folder", required=False, enum=FOLDERS),
    sender=Param("string", "Only emails whose sender address contains this text", required=False),
    limit=Param("integer", "Maximum results (default 10)", required=False),
)
def email_search(world: World, query: str = "", folder: str | None = None, sender: str | None = None, limit: int = 10):
    results = [
        e for e in world.collection("emails").values()
        if (e["folder"] == folder if folder else e["folder"] != "trash")
        and (sender is None or sender.lower() in e["from"].lower())
        and matches_query(query, e["from"], e["to"], e.get("cc", []), e["subject"], e["body"])
    ]
    results.sort(key=lambda e: e["date"], reverse=True)
    return [_summary(e) for e in results[:limit]]


@tool(
    "email_read", "email", "Read the full content of an email.",
    email_id=Param("string", "Id of the email"),
)
def email_read(world: World, email_id: str):
    return _get(world, email_id)


def _compose(world: World, folder: str, to, subject, body, cc, in_reply_to) -> dict:
    cc = cc or []
    _check_addresses(to)
    if cc:
        _check_addresses(cc)
    if in_reply_to is not None:
        _get(world, in_reply_to)

    email = {
        "id": world.new_id("email"),
        "folder": folder,
        "from": world.user["email"],
        "to": to,
        "cc": cc,
        "subject": subject,
        "body": body,
        "date": fmt(world.now),
        "in_reply_to": in_reply_to,
    }
    world.collection("emails")[email["id"]] = email
    return email


COMPOSE_PARAMS = dict(
    to=Param("array", "Recipient email addresses", items="string"),
    subject=Param("string", "Subject line"),
    body=Param("string", "Plain-text body"),
    cc=Param("array", "CC email addresses", required=False, items="string"),
    in_reply_to=Param("string", "Id of the email being replied to, if this is a reply", required=False),
)


@tool("email_send", "email", "Send an email immediately. This cannot be undone.", mutates=True, **COMPOSE_PARAMS)
def email_send(world: World, to, subject, body, cc=None, in_reply_to=None):
    email = _compose(world, "sent", to, subject, body, cc, in_reply_to)
    return {"status": "sent", "id": email["id"]}


@tool("email_draft", "email", "Save an email as a draft without sending it.", mutates=True, **COMPOSE_PARAMS)
def email_draft(world: World, to, subject, body, cc=None, in_reply_to=None):
    email = _compose(world, "drafts", to, subject, body, cc, in_reply_to)
    return {"status": "draft saved", "id": email["id"]}


@tool(
    "email_move", "email", "Move an email to another folder (e.g. archive or trash).", mutates=True,
    email_id=Param("string", "Id of the email"),
    folder=Param("string", "Destination folder", enum=("inbox", "archive", "trash")),
)
def email_move(world: World, email_id: str, folder: str):
    _get(world, email_id)["folder"] = folder
    return {"status": "moved", "id": email_id, "folder": folder}
