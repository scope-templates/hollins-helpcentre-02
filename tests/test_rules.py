from datetime import datetime, timedelta, timezone

import pytest

from hollins import rules
from hollins.rules import DeskRefusal

OPENED = datetime(2026, 3, 4, 9, 30, tzinfo=timezone.utc)


def ticket(**over):
    base = {
        "number": 5123,
        "status": "open",
        "opened_at": OPENED,
        "first_reply_at": None,
        "closed_at": None,
        "reply": None,
    }
    base.update(over)
    return base


def test_a_ticket_needs_a_subject_and_a_message():
    with pytest.raises(DeskRefusal):
        rules.check_new_ticket("   ", "the rota will not publish")
    with pytest.raises(DeskRefusal):
        rules.check_new_ticket("Rota", "  ")
    rules.check_new_ticket("Rota", "the rota will not publish")


def test_a_ticket_comes_in_by_email_or_the_app_and_is_handled_by_the_desk():
    assert rules.check_channel("email") == "email"
    assert rules.check_handler("Priya Nair") == "Priya Nair"
    with pytest.raises(DeskRefusal):
        rules.check_channel("phone")
    with pytest.raises(DeskRefusal) as refused:
        rules.check_handler("Someone Else")
    assert "not on the support desk" in refused.value.message


def test_one_message_gets_one_reply():
    answered = ticket(status="replied", reply="sent you the article", first_reply_at=OPENED)
    with pytest.raises(DeskRefusal) as refused:
        rules.check_reply(answered, "and another thing")
    assert "5123 was answered on 4 March" in refused.value.message


def test_a_closed_ticket_is_left_as_it_was():
    shut = ticket(status="closed", closed_at=OPENED + timedelta(days=2))
    with pytest.raises(DeskRefusal) as refused:
        rules.check_reply(shut, "sorry for the delay")
    assert "was closed on 6 March" in refused.value.message
    with pytest.raises(DeskRefusal):
        rules.check_close(shut)
    rules.check_close(ticket(status="open", reply=None))
    rules.check_close(ticket(status="replied", reply="here you go"))


def test_the_clock_starts_on_the_first_reply_and_stays_there():
    first = OPENED + timedelta(hours=2)
    assert rules.first_reply_at(ticket(), first) == first
    already = ticket(first_reply_at=first)
    assert rules.first_reply_at(already, OPENED + timedelta(days=3)) == first
    assert rules.reply_delay(already) == timedelta(hours=2)
    assert rules.reply_delay(ticket()) is None


def test_a_ticket_answered_inside_a_day_counts_as_answered_inside_a_day():
    quick = ticket(first_reply_at=OPENED + timedelta(hours=23, minutes=59))
    slow = ticket(first_reply_at=OPENED + timedelta(hours=26))
    assert rules.replied_within_a_day(quick) is True
    assert rules.replied_within_a_day(slow) is False
    assert rules.replied_within_a_day(ticket()) is False


def test_ticket_numbers_carry_on_from_the_old_system():
    assert rules.next_number(None) == 5100
    assert rules.next_number(5100) == 5101
    assert rules.next_number(6482) == 6483
    assert rules.on_day(datetime(2026, 12, 1, tzinfo=timezone.utc)) == "1 December"
