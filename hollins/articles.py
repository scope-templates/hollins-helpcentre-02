"""The help centre: listing articles, reading one, and counting who read it."""

from typing import Any, Dict, List, Optional

from pymongo import DESCENDING
from pymongo.database import Database

from hollins.rules import DeskRefusal, SECTIONS

PER_PAGE = 20
FIELDS = {"_id": 0}
SUMMARY = {"_id": 0, "slug": 1, "title": 1, "section": 1, "views": 1, "updated_at": 1}


def list_articles(
    database: Database,
    section: Optional[str] = None,
    page: int = 1,
    per_page: int = PER_PAGE,
) -> Dict[str, Any]:
    """Everything in a section, or the whole help centre, most read first."""
    if section is not None and section not in SECTIONS:
        raise DeskRefusal(f"there is no {section} section in the help centre", 404)
    query: Dict[str, Any] = {} if section is None else {"section": section}
    total = database.articles.count_documents(query)
    cursor = (
        database.articles.find(query, SUMMARY)
        .sort([("views", DESCENDING), ("slug", 1)])
        .skip(max(page - 1, 0) * per_page)
        .limit(per_page)
    )
    return {
        "section": section,
        "page": page,
        "per_page": per_page,
        "total": total,
        "articles": list(cursor),
    }


def get_article(database: Database, slug: str) -> Dict[str, Any]:
    article = database.articles.find_one({"slug": slug}, FIELDS)
    if article is None:
        raise DeskRefusal(f"there is no article at {slug}", 404)
    return article


def read_article(database: Database, slug: str) -> Dict[str, Any]:
    """What a reader gets. The view count is what tells us which pages earn their keep."""
    article = get_article(database, slug)
    database.articles.update_one({"slug": slug}, {"$inc": {"views": 1}})
    article["views"] = (article.get("views") or 0) + 1
    return article


def sections(database: Database) -> List[Dict[str, Any]]:
    """The sections with a count against each, in the order they appear in the sidebar."""
    counted = {
        row["_id"]: row["articles"]
        for row in database.articles.aggregate(
            [{"$group": {"_id": "$section", "articles": {"$sum": 1}}}]
        )
    }
    return [{"section": name, "articles": counted.get(name, 0)} for name in SECTIONS]


def titles_by_slug(database: Database, slugs: List[str]) -> Dict[str, str]:
    """Titles for a handful of slugs, for reports that would otherwise print slugs at people."""
    if not slugs:
        return {}
    rows = database.articles.find({"slug": {"$in": slugs}}, {"_id": 0, "slug": 1, "title": 1})
    return {row["slug"]: row["title"] for row in rows}
