"""Loading the bundled history, and the weekly figures off it, against a real server."""

import os
from datetime import timedelta

import pytest

from tests.conftest import MONDAY, NO_URI

if not os.environ.get("MONGODB_URI"):
    pytest.skip(NO_URI, allow_module_level=True)

from hollins.reports import weekly  # noqa: E402
from hollins.rules import SECTIONS  # noqa: E402
from hollins.seed_load import load_seed, read_history  # noqa: E402


def test_the_bundled_history_goes_into_an_empty_database_and_is_left_alone_after_that(database):
    history = read_history()
    written = load_seed(database)
    for collection in ("articles", "accounts", "tickets"):
        assert written[collection] == len(history[collection])
        assert database[collection].count_documents({}) == len(history[collection])

    again = load_seed(database)
    assert again == {"articles": 0, "accounts": 0, "tickets": 0}
    assert database.articles.count_documents({}) == written["articles"]


def test_the_history_arrives_with_dates_and_sections_the_rest_of_the_app_understands(database):
    load_seed(database)
    article = database.articles.find_one({})
    assert article["body"]
    assert article["section"] in SECTIONS
    oldest = database.tickets.find_one({}, sort=[("opened_at", 1)])
    newest = database.tickets.find_one({}, sort=[("opened_at", -1)])
    assert oldest["opened_at"] < newest["opened_at"]
    assert newest["opened_at"].year == 2026


def test_the_weekly_figures_come_off_the_tickets_in_the_window(desk):
    figures = weekly(desk, start=MONDAY - timedelta(hours=1), end=MONDAY + timedelta(days=1))
    assert figures["opened"] == 3
    assert figures["replied"] == 2
    assert figures["replied_with_an_article"] == 1
    assert figures["replied_by_hand"] == 1
    assert figures["articles_sent"][0]["title"] == "Publishing a rota so staff can see it"
    assert figures["busiest_sections"][0] == {"section": "rotas", "sent": 1}
