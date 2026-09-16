"""The sums behind the weekly figures, done on a list of tickets."""

from datetime import datetime, timedelta, timezone

from hollins.reports import share, summarise, week_ending

MONDAY = datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)

SECTION_OF = {
    "publishing-a-rota": "rotas",
    "rota-emails-at-night": "rotas",
    "holiday-allowance": "time off",
    "payroll-file": "pay and hours",
}


def ticket(number, hours=None, slug=None, reply=None, status="closed"):
    return {
        "number": number,
        "opened_at": MONDAY,
        "first_reply_at": None if hours is None else MONDAY + timedelta(hours=hours),
        "reply": reply,
        "sent_article_slug": slug,
        "status": status,
    }


WEEK = [
    ticket(5201, hours=2, slug="publishing-a-rota", reply="sent the article"),
    ticket(5202, hours=5, slug="publishing-a-rota", reply="sent the article"),
    ticket(5203, hours=30, slug="holiday-allowance", reply="sent the article"),
    ticket(5204, hours=1, reply="wrote it out by hand"),
    ticket(5205, hours=9, reply="wrote it out by hand"),
    ticket(5206, hours=None, status="closed"),
    ticket(5207, hours=None, status="open"),
]


def test_the_week_counts_what_came_in_what_was_answered_and_what_was_closed():
    figures = summarise(WEEK, SECTION_OF)
    assert figures["opened"] == 7
    assert figures["replied"] == 5
    assert figures["replied_within_a_day"] == 4
    assert figures["closed"] == 6


def test_an_article_or_by_hand_splits_the_replies_between_them():
    figures = summarise(WEEK, SECTION_OF)
    assert figures["replied_with_an_article"] == 3
    assert figures["replied_by_hand"] == 2
    assert figures["share_with_an_article"] == 60.0
    assert figures["share_by_hand"] == 40.0


def test_the_articles_sent_and_the_sections_they_came_from_are_most_sent_first():
    figures = summarise(WEEK, SECTION_OF)
    assert figures["articles_sent"][0] == {"slug": "publishing-a-rota", "sent": 2}
    assert {"slug": "holiday-allowance", "sent": 1} in figures["articles_sent"]
    assert figures["busiest_sections"][0] == {"section": "rotas", "sent": 2}
    assert {"section": "time off", "sent": 1} in figures["busiest_sections"]


def test_a_quiet_week_comes_out_at_nought_rather_than_falling_over():
    figures = summarise([], SECTION_OF)
    assert figures["opened"] == 0
    assert figures["share_with_an_article"] == 0.0
    assert figures["articles_sent"] == []
    assert share(1, 3) == 33.3
    assert share(0, 0) == 0.0
    window = week_ending(MONDAY)
    assert window["to"] == MONDAY
    assert window["to"] - window["from"] == timedelta(days=7)
