"""Tickets in and out: what the desk does all day."""

from typing import Any, Dict, Optional

from pymongo import DESCENDING
from pymongo.database import Database

from hollins import rules
from hollins.rules import DeskRefusal

PER_PAGE = 25
FIELDS = {"_id": 0}


def next_number(database: Database) -> int:
    top = database.tickets.find_one({}, {"_id": 0, "number": 1}, sort=[("number", DESCENDING)])
    return rules.next_number(top["number"] if top else None)


def open_ticket(
    database: Database,
    account_id: str,
    channel: str,
    subject: str,
    message: str,
    searched_for: Optional[str] = None,
) -> Dict[str, Any]:
    """A ticket off the in-app form. Email comes in the same way, with channel set to email."""
    rules.check_channel(channel)
    rules.check_new_ticket(subject, message)
    if database.accounts.count_documents({"account_id": account_id}, limit=1) == 0:
        raise DeskRefusal(f"there is no account {account_id}", 404)

    ticket = {
        "number": next_number(database),
        "account_id": account_id,
        "channel": channel,
        "subject": subject.strip(),
        "message": message.strip(),
        "opened_at": rules.now(),
        "first_reply_at": None,
        "closed_at": None,
        "handled_by": None,
        "closed_by": None,
        "searched_for": searched_for,
        "sent_article_slug": None,
        "reply": None,
        "status": "open",
    }
    database.tickets.insert_one(dict(ticket))
    return ticket


def get_ticket(database: Database, number: int) -> Dict[str, Any]:
    ticket = database.tickets.find_one({"number": number}, FIELDS)
    if ticket is None:
        raise DeskRefusal(f"there is no ticket {number}", 404)
    return ticket


def list_tickets(
    database: Database,
    status: Optional[str] = None,
    account: Optional[str] = None,
    page: int = 1,
    per_page: int = PER_PAGE,
) -> Dict[str, Any]:
    """The queue: newest first, narrowed by status or by account the way the desk narrows it."""
    if status is not None and status not in rules.STATUSES:
        raise DeskRefusal(f"a ticket is {', '.join(rules.STATUSES)}, not {status}", 400)
    query: Dict[str, Any] = {}
    if status is not None:
        query["status"] = status
    if account is not None:
        query["account_id"] = account
    total = database.tickets.count_documents(query)
    cursor = (
        database.tickets.find(query, FIELDS)
        .sort([("opened_at", DESCENDING), ("number", DESCENDING)])
        .skip(max(page - 1, 0) * per_page)
        .limit(per_page)
    )
    return {
        "status": status,
        "account": account,
        "page": page,
        "per_page": per_page,
        "total": total,
        "tickets": list(cursor),
    }


def reply_to_ticket(
    database: Database,
    number: int,
    text: str,
    handled_by: str,
    article_slug: Optional[str] = None,
) -> Dict[str, Any]:
    """The desk answers. An article slug goes down when the desk sent one with the reply."""
    ticket = get_ticket(database, number)
    rules.check_handler(handled_by)
    rules.check_reply(ticket, text)
    if article_slug is not None:
        if database.articles.count_documents({"slug": article_slug}, limit=1) == 0:
            raise DeskRefusal(f"there is no article at {article_slug}", 404)

    when = rules.now()
    change = {
        "reply": text.strip(),
        "handled_by": handled_by,
        "sent_article_slug": article_slug,
        "first_reply_at": rules.first_reply_at(ticket, when),
        "status": "replied",
    }
    database.tickets.update_one({"number": number}, {"$set": change})
    ticket.update(change)
    return ticket


def close_ticket(database: Database, number: int, closed_by: str) -> Dict[str, Any]:
    """Whoever closes it signs the closing. The reply still belongs to whoever wrote it."""
    ticket = get_ticket(database, number)
    rules.check_handler(closed_by)
    rules.check_close(ticket)
    change = {"closed_at": rules.now(), "status": "closed", "closed_by": closed_by}
    database.tickets.update_one({"number": number}, {"$set": change})
    ticket.update(change)
    return ticket
