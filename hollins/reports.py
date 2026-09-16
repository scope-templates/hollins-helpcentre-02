"""The weekly figures Marcus reads on a Monday morning."""

from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Mapping, Optional

from pymongo.database import Database

from hollins import rules
from hollins.articles import titles_by_slug

TOP_ARTICLES = 10
TOP_SECTIONS = 5


def share(part: int, whole: int) -> float:
    """A share as a percentage to one decimal place, and nought when there is nothing to divide."""
    if not whole:
        return 0.0
    return round(part * 100.0 / whole, 1)


def summarise(
    tickets: Iterable[Mapping[str, Any]], section_of: Optional[Mapping[str, str]] = None
) -> Dict[str, Any]:
    """The week's figures off a list of tickets, which is all the maths there is to this."""
    section_of = section_of or {}
    rows = list(tickets)
    replied = [t for t in rows if t.get("reply")]
    with_article = [t for t in replied if t.get("sent_article_slug")]
    by_hand = [t for t in replied if not t.get("sent_article_slug")]
    quick = [t for t in rows if rules.replied_within_a_day(t)]
    closed = [t for t in rows if t.get("status") == "closed"]

    sent = Counter(t["sent_article_slug"] for t in with_article)
    sections = Counter(
        section_of[t["sent_article_slug"]]
        for t in with_article
        if t["sent_article_slug"] in section_of
    )

    return {
        "opened": len(rows),
        "replied": len(replied),
        "replied_within_a_day": len(quick),
        "closed": len(closed),
        "replied_with_an_article": len(with_article),
        "replied_by_hand": len(by_hand),
        "share_with_an_article": share(len(with_article), len(replied)),
        "share_by_hand": share(len(by_hand), len(replied)),
        "articles_sent": [
            {"slug": slug, "sent": count} for slug, count in sent.most_common(TOP_ARTICLES)
        ],
        "busiest_sections": [
            {"section": name, "sent": count} for name, count in sections.most_common(TOP_SECTIONS)
        ],
    }


def week_ending(day: Optional[datetime] = None) -> Dict[str, datetime]:
    """The seven days up to the moment asked for, which is how the desk reads a week."""
    end = day or rules.now()
    start = end - timedelta(days=7)
    return {"from": start, "to": end}


def weekly(
    database: Database, start: Optional[datetime] = None, end: Optional[datetime] = None
) -> Dict[str, Any]:
    """Everything opened in the window, summed up, with the articles named rather than slugged."""
    window = week_ending(end)
    first = start or window["from"]
    last = end or window["to"]
    rows = list(
        database.tickets.find({"opened_at": {"$gte": first, "$lt": last}}, {"_id": 0})
    )
    section_of = sections_by_slug(database, rows)
    figures = summarise(rows, section_of)
    titles = titles_by_slug(database, [row["slug"] for row in figures["articles_sent"]])
    for row in figures["articles_sent"]:
        row["title"] = titles.get(row["slug"], row["slug"])
    figures["from"] = first
    figures["to"] = last
    return figures


def sections_by_slug(
    database: Database, tickets: Iterable[Mapping[str, Any]]
) -> Dict[str, str]:
    slugs: List[str] = sorted(
        {t["sent_article_slug"] for t in tickets if t.get("sent_article_slug")}
    )
    if not slugs:
        return {}
    rows = database.articles.find({"slug": {"$in": slugs}}, {"_id": 0, "slug": 1, "section": 1})
    return {row["slug"]: row["section"] for row in rows}
