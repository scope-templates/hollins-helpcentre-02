"""Drafting a reply from the articles the desk has in front of it.

The draft is written by a language model. It is a first pass for a person to read, cut about and
send, not something that goes out on its own.
"""

import os
from typing import Any, Dict, List, Mapping, Optional, Sequence

from pymongo.database import Database

from hollins.rules import DeskRefusal
from hollins.search import top_articles_for
from hollins.tickets import get_ticket

DEFAULT_MODEL = "gpt-4o-mini"
ARTICLES_IN_A_DRAFT = 3
TEMPERATURE = 0.3

TONE = (
    "You write replies for the support desk at Hollins Rota, a staff scheduling product used by "
    "cafes, bars, small restaurants and leisure centres. Write the way Priya and Callum write: "
    "British English, plain words, short sentences, warm but not chatty, no exclamation marks, no "
    "bullet points unless the customer asked for steps. Open by naming what they are dealing "
    "with. Use only what is in the help centre articles below; if they do not answer the "
    "question, say plainly that you will look at the account and come back to them. Never invent "
    "a screen, a setting or a price. Sign off with the first name of whoever is on the desk."
)


def model_name() -> str:
    return os.environ.get("ASSISTANT_MODEL") or DEFAULT_MODEL


def have_a_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def make_client() -> Any:
    """The SDK client, built when we need it so nothing outside a draft touches the key."""
    if not have_a_key():
        raise DeskRefusal("drafts need OPENAI_API_KEY to be set", 503)
    from openai import OpenAI

    return OpenAI()


def article_block(article: Mapping[str, Any]) -> str:
    return (
        f"Article: {article.get('title')}\n"
        f"Section: {article.get('section')}\n"
        f"{article.get('body')}"
    )


def build_messages(
    ticket: Mapping[str, Any], articles: Sequence[Mapping[str, Any]]
) -> List[Dict[str, str]]:
    """What goes to the model: the tone, the articles the desk found, then the ticket itself."""
    if articles:
        pages = "\n\n---\n\n".join(article_block(a) for a in articles)
    else:
        pages = "There are no help centre articles to work from for this one."
    desk = ticket.get("handled_by") or "Priya Nair"
    asked = (
        f"Subject: {ticket.get('subject')}\n"
        f"From the customer:\n{ticket.get('message')}\n\n"
        f"On the desk: {desk.split()[0]}"
    )
    return [
        {"role": "system", "content": TONE},
        {"role": "user", "content": f"Help centre articles:\n\n{pages}\n\n{asked}"},
    ]


def draft_reply(
    ticket: Mapping[str, Any],
    articles: Sequence[Mapping[str, Any]],
    client: Any,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """One call, one draft, and a note of which articles it was written from."""
    used = model or model_name()
    answer = client.chat.completions.create(
        model=used,
        messages=build_messages(ticket, articles),
        temperature=TEMPERATURE,
    )
    return {
        "number": ticket.get("number"),
        "model": used,
        "draft": answer.choices[0].message.content,
        "articles": [
            {"slug": a.get("slug"), "title": a.get("title")} for a in articles
        ],
    }


def words_to_look_up(ticket: Mapping[str, Any]) -> str:
    """What the desk typed, or the subject line when nobody wrote anything down."""
    return ticket.get("searched_for") or ticket.get("subject") or ""


def draft_for_ticket(
    database: Database, number: int, client: Any = None
) -> Dict[str, Any]:
    ticket = get_ticket(database, number)
    articles = top_articles_for(
        database, words_to_look_up(ticket), count=ARTICLES_IN_A_DRAFT
    )
    return draft_reply(ticket, articles, client or make_client())
