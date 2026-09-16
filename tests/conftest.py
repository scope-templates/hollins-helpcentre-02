import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pymongo import MongoClient

from hollins.db import prepare

# One database per run of the suite, so two runs against the same server do not drop each
# other's data halfway through.
TEST_DATABASE = "hollins_test_" + uuid4().hex[:6]
NO_URI = "set MONGODB_URI to run database tests"

MONDAY = datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)

ARTICLES = [
    {
        "slug": "publishing-a-rota",
        "title": "Publishing a rota so staff can see it",
        "section": "rotas",
        "body": "Press Publish, read the summary and confirm it. Staff get an email.",
        "updated_at": MONDAY,
        "views": 900,
    },
    {
        "slug": "rota-emails-at-night",
        "title": "Stopping rota emails going out at night",
        "section": "rotas",
        "body": "Hold the email until the morning from the venue settings page.",
        "updated_at": MONDAY,
        "views": 410,
    },
    {
        "slug": "booking-time-off",
        "title": "Booking time off for a member of staff",
        "section": "time off",
        "body": "Pick the first and last day, then say whether it comes off the allowance.",
        "updated_at": MONDAY,
        "views": 1200,
    },
    {
        "slug": "holiday-allowance",
        "title": "The holiday allowance for a venue",
        "section": "time off",
        "body": "Set the allowance in days or in hours. Staff who joined partway get it pro rata.",
        "updated_at": MONDAY,
        "views": 260,
    },
    {
        "slug": "payroll-file",
        "title": "The payroll file and what is in each column",
        "section": "pay and hours",
        "body": "One row per member of staff, with the hours and the rate in separate columns.",
        "updated_at": MONDAY,
        "views": 75,
    },
    {
        "slug": "staff-hours-summary",
        "title": "Staff hours for the week at a glance",
        "section": "pay and hours",
        "body": "The summary adds up what everybody worked over the seven days.",
        "updated_at": MONDAY,
        "views": 40,
    },
]

ACCOUNTS = [
    {
        "account_id": "A2001",
        "name": "The Long Room Bistro",
        "plan": "team",
        "staff_count": 18,
        "town": "Marsden",
        "created_at": MONDAY - timedelta(days=400),
    },
    {
        "account_id": "A2002",
        "name": "Harbourgate Tap Room",
        "plan": "starter",
        "staff_count": 9,
        "town": "Denbury",
        "created_at": MONDAY - timedelta(days=90),
    },
]


def ticket(number, account, **over):
    row = {
        "number": number,
        "account_id": account,
        "channel": "email",
        "subject": "Rota will not publish",
        "message": "The publish button spins and then goes back to how it was.",
        "opened_at": MONDAY,
        "first_reply_at": None,
        "closed_at": None,
        "handled_by": None,
        "closed_by": None,
        "searched_for": "publish rota",
        "sent_article_slug": None,
        "reply": None,
        "status": "open",
    }
    row.update(over)
    return row


TICKETS = [
    ticket(
        5100,
        "A2001",
        first_reply_at=MONDAY + timedelta(hours=2),
        closed_at=MONDAY + timedelta(days=1),
        handled_by="Priya Nair",
        closed_by="Priya Nair",
        sent_article_slug="publishing-a-rota",
        reply="Hi, this article covers it.",
        status="closed",
    ),
    ticket(
        5101,
        "A2002",
        subject="Holiday allowance looks wrong",
        message="She says twelve days left and I make it nine.",
        searched_for="holiday allowance",
        first_reply_at=MONDAY + timedelta(hours=30),
        handled_by="Callum Doyle",
        reply="I have had a look at the account and put it right.",
        status="replied",
    ),
    ticket(5102, "A2001", subject="Printing the rota", searched_for=None),
]


def a_server_to_talk_to():
    return os.environ.get("MONGODB_URI")


@pytest.fixture()
def database():
    """A clean database of this run's own on the server MONGODB_URI names, dropped after."""
    client = MongoClient(a_server_to_talk_to(), tz_aware=True, serverSelectionTimeoutMS=5000)
    client.drop_database(TEST_DATABASE)
    handle = prepare(client[TEST_DATABASE])
    yield handle
    client.drop_database(TEST_DATABASE)
    client.close()


@pytest.fixture()
def desk(database):
    """The small help centre and the three tickets the database tests work against."""
    database.articles.insert_many([dict(row) for row in ARTICLES])
    database.accounts.insert_many([dict(row) for row in ACCOUNTS])
    database.tickets.insert_many([dict(row) for row in TICKETS])
    return database
