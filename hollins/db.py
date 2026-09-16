"""Opening the database and keeping the fields the desk looks things up by in place."""

import os
from typing import Optional

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database
from pymongo.errors import ServerSelectionTimeoutError

from hollins.rules import DeskRefusal

DEFAULT_URI = "mongodb://localhost:27017"
DEFAULT_NAME = "hollins"
# Long enough for a server that is starting, short enough that a missing one says so.
WAIT_FOR_A_SERVER = 5000

COLLECTIONS = ("articles", "accounts", "tickets")


def uri() -> str:
    return os.environ.get("MONGODB_URI") or DEFAULT_URI


def name() -> str:
    return os.environ.get("MONGODB_DB") or DEFAULT_NAME


def connect(where: Optional[str] = None, which: Optional[str] = None) -> Database:
    """A database handle. Callers that want their own connection use this directly.

    Times are read back with UTC on them, the way they went in, so nothing has to guess later.
    """
    client = MongoClient(
        where or uri(), tz_aware=True, serverSelectionTimeoutMS=WAIT_FOR_A_SERVER
    )
    return client[which or name()]


def prepare(database: Database) -> Database:
    """The fields the desk looks things up by: a slug, a ticket number, a queue."""
    database.articles.create_index([("slug", ASCENDING)], unique=True)
    database.articles.create_index([("section", ASCENDING), ("views", DESCENDING)])
    database.accounts.create_index([("account_id", ASCENDING)], unique=True)
    database.tickets.create_index([("number", ASCENDING)], unique=True)
    database.tickets.create_index([("status", ASCENDING), ("opened_at", DESCENDING)])
    database.tickets.create_index([("account_id", ASCENDING), ("opened_at", DESCENDING)])
    return database


def is_empty(database: Database) -> bool:
    return database.articles.estimated_document_count() == 0


_shared: Optional[Database] = None


def get_db() -> Database:
    """The desk's database. The first handle out fills an empty one from the bundled history."""
    global _shared
    if _shared is None:
        from hollins.seed_load import load_seed

        try:
            database = prepare(connect())
            if is_empty(database):
                load_seed(database)
        except ServerSelectionTimeoutError:
            raise DeskRefusal(
                f"no database answered at {uri()} within five seconds", 503
            ) from None
        _shared = database
    return _shared


def forget() -> None:
    """Drop the shared handle, so the next caller opens the database again."""
    global _shared
    _shared = None
