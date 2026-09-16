"""The routes the in-app form and the desk actually call."""

import os

import pytest

from tests.conftest import NO_URI

if not os.environ.get("MONGODB_URI"):
    pytest.skip(NO_URI, allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402

from hollins import db  # noqa: E402
from hollins.app import app  # noqa: E402


@pytest.fixture()
def client(desk):
    db._shared = desk
    with TestClient(app) as opened:
        yield opened
    db.forget()


def test_a_ticket_off_the_form_is_taken_and_can_be_read_back(client):
    made = client.post(
        "/tickets",
        json={
            "account_id": "A2002",
            "channel": "app",
            "subject": "Notifications are not arriving",
            "message": "Half the team get the push and half do not.",
            "searched_for": "push notifications",
        },
    )
    assert made.status_code == 201
    number = made.json()["number"]

    again = client.get(f"/tickets/{number}")
    assert again.status_code == 200
    assert again.json()["subject"] == "Notifications are not arriving"

    queue = client.get("/tickets", params={"status": "open"})
    assert number in [t["number"] for t in queue.json()["tickets"]]


def test_the_desk_looks_articles_up_by_the_words_it_types(client):
    found = client.get("/articles/search", params={"q": "holiday allowance"})
    assert found.status_code == 200
    assert [a["slug"] for a in found.json()["articles"]] == ["holiday-allowance"]

    one = client.get("/articles/holiday-allowance")
    assert one.json()["title"] == "The holiday allowance for a venue"


def test_a_reply_on_a_closed_ticket_comes_back_as_a_plain_refusal(client):
    refused = client.post(
        "/tickets/5100/reply",
        json={"text": "sorry for the wait", "handled_by": "Priya Nair"},
    )
    assert refused.status_code == 409
    assert "5100 was closed" in refused.json()["error"]
