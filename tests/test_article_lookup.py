"""The article lookup, run over a list held in memory."""

from hollins.search import find_articles, patterns_for, split_words, words_in_title

SHELF = [
    {
        "slug": "publishing-a-rota",
        "title": "Publishing a rota so staff can see it",
        "section": "rotas",
        "body": "Press Publish, read the summary and confirm it. Staff get an email.",
        "views": 900,
    },
    {
        "slug": "rota-emails-at-night",
        "title": "Stopping rota emails going out at night",
        "section": "rotas",
        "body": "Hold the email until the morning from the venue settings page.",
        "views": 410,
    },
    {
        "slug": "booking-time-off",
        "title": "Booking time off for a member of staff",
        "section": "time off",
        "body": "Pick the first and last day, then say whether it comes off the allowance.",
        "views": 1200,
    },
    {
        "slug": "holiday-allowance",
        "title": "The holiday allowance for a venue",
        "section": "time off",
        "body": "Set the allowance in days or in hours. Staff who joined partway get it pro rata.",
        "views": 260,
    },
    {
        "slug": "payroll-file",
        "title": "The payroll file and what is in each column",
        "section": "pay and hours",
        "body": "One row per member of staff, with the hours and the rate in separate columns.",
        "views": 75,
    },
    {
        "slug": "staff-hours-summary",
        "title": "Staff hours for the week at a glance",
        "section": "pay and hours",
        "body": "The summary adds up what everybody worked over the seven days.",
        "views": 40,
    },
    {
        "slug": "wage-cost",
        "title": "Wage cost (percentage) on the rota",
        "section": "pay and hours",
        "body": "The bar along the top is wage cost against takings for the day.",
        "views": 320,
    },
]


def slugs(result):
    return [article["slug"] for article in result["articles"]]


def test_the_words_are_whatever_was_typed_between_the_spaces():
    assert split_words("  holiday   allowance ") == ["holiday", "allowance"]
    assert slugs(find_articles(SHELF, "(percentage)")) == ["wage-cost"]
    assert slugs(find_articles(SHELF, "publish")) == ["publishing-a-rota"]
    empty = find_articles(SHELF, "   ")
    assert empty["words"] == []
    assert empty["articles"] == []


def test_a_word_in_the_title_or_in_the_body_finds_the_article():
    assert slugs(find_articles(SHELF, "publishing")) == ["publishing-a-rota"]
    assert slugs(find_articles(SHELF, "takings")) == ["wage-cost"]


def test_capitals_make_no_difference():
    assert slugs(find_articles(SHELF, "PAYROLL")) == slugs(find_articles(SHELF, "payroll"))
    assert slugs(find_articles(SHELF, "Allowance")) == ["holiday-allowance", "booking-time-off"]


def test_every_word_has_to_be_there_somewhere():
    assert slugs(find_articles(SHELF, "holiday allowance")) == ["holiday-allowance"]
    assert slugs(find_articles(SHELF, "night morning")) == ["rota-emails-at-night"]


def test_more_of_the_words_in_the_title_comes_first_then_the_most_read():
    assert slugs(find_articles(SHELF, "staff hours"))[0] == "staff-hours-summary"
    patterns = patterns_for(["staff", "hours"])
    assert words_in_title(SHELF[2], patterns) == 1
    assert words_in_title(SHELF[5], patterns) == 2
    assert slugs(find_articles(SHELF, "staff"))[0] == "booking-time-off"


def test_results_come_a_page_at_a_time():
    first = find_articles(SHELF, "the", page=1, per_page=2)
    second = find_articles(SHELF, "the", page=2, per_page=2)
    assert len(first["articles"]) == 2
    assert first["total"] == second["total"]
    assert not set(slugs(first)) & set(slugs(second))
    assert find_articles(SHELF, "staff")["total"] == 5
