"""Looking up help-centre articles by the words the desk types."""

import re
from typing import Any, Dict, Iterable, List, Optional, Pattern, Sequence

from pymongo.database import Database

PER_PAGE = 10
MAX_WORDS = 12


def split_words(query: Optional[str]) -> List[str]:
    """The words the desk typed, whitespace apart, capped so a pasted message cannot run away."""
    if not query:
        return []
    return query.split()[:MAX_WORDS]


def patterns_for(words: Sequence[str]) -> List[Pattern[str]]:
    """One case-insensitive pattern per word, with the word's own punctuation taken literally."""
    return [re.compile(re.escape(word), re.IGNORECASE) for word in words]


def article_matches(article: Dict[str, Any], patterns: Sequence[Pattern[str]]) -> bool:
    """True when every word is somewhere in the title or the body."""
    title = article.get("title") or ""
    body = article.get("body") or ""
    return all(pattern.search(title) or pattern.search(body) for pattern in patterns)


def words_in_title(article: Dict[str, Any], patterns: Sequence[Pattern[str]]) -> int:
    """How many of the words are in the title, which is what puts one article above another."""
    title = article.get("title") or ""
    return sum(1 for pattern in patterns if pattern.search(title))


def order_articles(
    articles: Iterable[Dict[str, Any]], patterns: Sequence[Pattern[str]]
) -> List[Dict[str, Any]]:
    """Most of the words in the title first, then the ones people read most."""
    rows = list(articles)
    rows.sort(key=lambda a: (-words_in_title(a, patterns), -(a.get("views") or 0), a["slug"]))
    return rows


def page_of(rows: Sequence[Dict[str, Any]], page: int, per_page: int) -> List[Dict[str, Any]]:
    first = max(page - 1, 0) * per_page
    return list(rows[first : first + per_page])


def query_for(patterns: Sequence[Pattern[str]]) -> Dict[str, Any]:
    """A document matches when each word is in its title or its body."""
    return {
        "$and": [
            {"$or": [{"title": pattern}, {"body": pattern}]} for pattern in patterns
        ]
    }


def find_articles(
    articles: Iterable[Dict[str, Any]],
    query: Optional[str],
    page: int = 1,
    per_page: int = PER_PAGE,
) -> Dict[str, Any]:
    """The same lookup over a list already in hand, which is how the tests exercise it."""
    words = split_words(query)
    if not words:
        return {"query": query or "", "words": [], "total": 0, "page": page, "articles": []}
    patterns = patterns_for(words)
    found = [a for a in articles if article_matches(a, patterns)]
    ordered = order_articles(found, patterns)
    return {
        "query": query or "",
        "words": words,
        "total": len(ordered),
        "page": page,
        "articles": page_of(ordered, page, per_page),
    }


FIELDS = {"_id": 0, "slug": 1, "title": 1, "section": 1, "body": 1, "views": 1, "updated_at": 1}


def search_articles(
    database: Database,
    query: Optional[str],
    page: int = 1,
    per_page: int = PER_PAGE,
) -> Dict[str, Any]:
    """Articles carrying every word the desk typed, the likeliest one first."""
    words = split_words(query)
    if not words:
        return {"query": query or "", "words": [], "total": 0, "page": page, "articles": []}
    patterns = patterns_for(words)
    rows = list(database.articles.find(query_for(patterns), FIELDS))
    ordered = order_articles(rows, patterns)
    return {
        "query": query or "",
        "words": words,
        "total": len(ordered),
        "page": page,
        "articles": page_of(ordered, page, per_page),
    }


def top_articles_for(database: Database, query: Optional[str], count: int = 3) -> List[Dict[str, Any]]:
    """The handful of articles the desk would have in front of it for those words."""
    return search_articles(database, query, page=1, per_page=count)["articles"]
