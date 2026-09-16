"""Tickets in and out, against a real server."""

import os

import pytest

from tests.conftest import NO_URI

if not os.environ.get("MONGODB_URI"):
    pytest.skip(NO_URI, allow_module_level=True)

from hollins import tickets  # noqa: E402
from hollins.rules import DeskRefusal  # noqa: E402


def test_a_ticket_off_the_form_goes_in_and_comes_back_by_its_number(desk):
    made = tickets.open_ticket(
        desk,
        account_id="A2002",
        channel="app",
        subject="Cannot sign in to the app",
        message="Three of the team cannot get into the app.",
        searched_for="app sign in",
    )
    assert made["number"] == 5103
    assert made["status"] == "open"

    again = tickets.get_ticket(desk, 5103)
    assert again["subject"] == "Cannot sign in to the app"
    assert again["searched_for"] == "app sign in"
    assert again["reply"] is None

    with pytest.raises(DeskRefusal) as no_account:
        tickets.open_ticket(
            desk,
            account_id="A9999",
            channel="app",
            subject="Rota",
            message="It will not publish.",
        )
    assert no_account.value.status == 404


def test_the_queue_narrows_by_status_and_by_account(desk):
    assert tickets.list_tickets(desk)["total"] == 3
    assert tickets.list_tickets(desk, status="closed")["total"] == 1
    for_one = tickets.list_tickets(desk, account="A2001")
    assert for_one["total"] == 2
    assert {t["account_id"] for t in for_one["tickets"]} == {"A2001"}


def test_a_reply_goes_down_with_the_article_the_desk_sent(desk):
    answered = tickets.reply_to_ticket(
        desk,
        5102,
        text="Hi, you want the print button at the top right.",
        handled_by="Priya Nair",
        article_slug="publishing-a-rota",
    )
    assert answered["status"] == "replied"
    assert answered["sent_article_slug"] == "publishing-a-rota"
    assert answered["first_reply_at"] is not None

    stored = tickets.get_ticket(desk, 5102)
    assert stored["handled_by"] == "Priya Nair"
    assert stored["first_reply_at"] == answered["first_reply_at"]


def test_one_message_gets_one_reply_and_a_closed_ticket_gets_none(desk):
    with pytest.raises(DeskRefusal) as answered_already:
        tickets.reply_to_ticket(desk, 5101, text="and again", handled_by="Priya Nair")
    assert "5101 was answered" in answered_already.value.message

    with pytest.raises(DeskRefusal) as shut:
        tickets.reply_to_ticket(desk, 5100, text="sorry for the wait", handled_by="Priya Nair")
    assert "5100 was closed" in shut.value.message


def test_closing_a_ticket_leaves_the_reply_with_whoever_wrote_it(desk):
    tickets.reply_to_ticket(desk, 5102, text="Here you go.", handled_by="Priya Nair")
    closed = tickets.close_ticket(desk, 5102, closed_by="Callum Doyle")
    assert closed["status"] == "closed"
    assert closed["closed_at"] is not None
    assert closed["closed_by"] == "Callum Doyle"
    assert closed["handled_by"] == "Priya Nair"
    with pytest.raises(DeskRefusal):
        tickets.close_ticket(desk, 5102, closed_by="Callum Doyle")
