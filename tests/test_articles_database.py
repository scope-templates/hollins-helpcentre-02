"""The help centre and its lookup, against a real server."""

import os

import pytest

from tests.conftest import NO_URI

if not os.environ.get("MONGODB_URI"):
    pytest.skip(NO_URI, allow_module_level=True)

from hollins.articles import list_articles, read_article  # noqa: E402
from hollins.search import search_articles  # noqa: E402


def slugs(result):
    return [article["slug"] for article in result["articles"]]


def test_a_word_in_the_title_or_in_the_body_finds_the_article(desk):
    assert slugs(search_articles(desk, "publishing")) == ["publishing-a-rota"]
    assert slugs(search_articles(desk, "morning")) == ["rota-emails-at-night"]


def test_capitals_make_no_difference(desk):
    assert slugs(search_articles(desk, "PAYROLL")) == slugs(search_articles(desk, "payroll"))
    assert slugs(search_articles(desk, "Allowance")) == ["holiday-allowance", "booking-time-off"]


def test_every_word_has_to_be_there_somewhere(desk):
    assert slugs(search_articles(desk, "holiday allowance")) == ["holiday-allowance"]
    assert slugs(search_articles(desk, "night morning")) == ["rota-emails-at-night"]


def test_more_of_the_words_in_the_title_comes_first(desk):
    found = search_articles(desk, "staff hours")
    assert slugs(found)[0] == "staff-hours-summary"
    assert found["total"] == 3


def test_a_section_lists_on_its_own_most_read_first_and_reading_one_counts(desk):
    listed = list_articles(desk, section="time off")
    assert listed["total"] == 2
    assert slugs(listed) == ["booking-time-off", "holiday-allowance"]

    opened = read_article(desk, "payroll-file")
    assert opened["views"] == 76
    assert desk.articles.find_one({"slug": "payroll-file"})["views"] == 76
