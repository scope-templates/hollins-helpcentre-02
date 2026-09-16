"""The HTTP side. Everything the desk and the in-app form talk to."""

from datetime import datetime
from typing import Any, Optional

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from hollins import __version__, articles, reports, search, tickets
from hollins.assistant import draft_for_ticket
from hollins.db import get_db
from hollins.rules import DeskRefusal

app = FastAPI(title="Hollins help centre", version=__version__)


class NewTicket(BaseModel):
    account_id: str
    channel: str = "app"
    subject: str
    message: str
    searched_for: Optional[str] = None


class Reply(BaseModel):
    text: str
    handled_by: str
    article_slug: Optional[str] = None


class Close(BaseModel):
    closed_by: str


def as_json(body: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(jsonable(body), status_code=status_code)


def jsonable(value: Any) -> Any:
    """Dates go out as text. Everything else is already plain."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    return value


@app.exception_handler(DeskRefusal)
async def refused(request: Request, err: DeskRefusal) -> JSONResponse:
    return JSONResponse({"error": err.message}, status_code=err.status)


@app.get("/health")
def health() -> JSONResponse:
    return as_json({"ok": True, "version": __version__})


@app.post("/tickets")
def post_ticket(body: NewTicket) -> JSONResponse:
    ticket = tickets.open_ticket(
        get_db(),
        account_id=body.account_id,
        channel=body.channel,
        subject=body.subject,
        message=body.message,
        searched_for=body.searched_for,
    )
    return as_json(ticket, 201)


@app.get("/tickets")
def get_tickets(
    status: Optional[str] = None,
    account: Optional[str] = None,
    page: int = 1,
) -> JSONResponse:
    return as_json(tickets.list_tickets(get_db(), status=status, account=account, page=page))


@app.get("/tickets/{number}")
def get_one_ticket(number: int) -> JSONResponse:
    return as_json(tickets.get_ticket(get_db(), number))


@app.post("/tickets/{number}/reply")
def post_reply(number: int, body: Reply) -> JSONResponse:
    ticket = tickets.reply_to_ticket(
        get_db(),
        number,
        text=body.text,
        handled_by=body.handled_by,
        article_slug=body.article_slug,
    )
    return as_json(ticket)


@app.post("/tickets/{number}/close")
def post_close(number: int, body: Close) -> JSONResponse:
    return as_json(tickets.close_ticket(get_db(), number, closed_by=body.closed_by))


@app.post("/tickets/{number}/draft")
def post_draft(number: int) -> JSONResponse:
    return as_json(draft_for_ticket(get_db(), number))


@app.get("/articles")
def get_articles(section: Optional[str] = None, page: int = 1) -> JSONResponse:
    return as_json(articles.list_articles(get_db(), section=section, page=page))


@app.get("/articles/search")
def get_article_search(q: str = Query(default=""), page: int = 1) -> JSONResponse:
    return as_json(search.search_articles(get_db(), q, page=page))


@app.get("/articles/{slug}")
def get_one_article(slug: str) -> JSONResponse:
    return as_json(articles.read_article(get_db(), slug))


@app.get("/sections")
def get_sections() -> JSONResponse:
    return as_json({"sections": articles.sections(get_db())})


@app.get("/reports/weekly")
def get_weekly(ending: Optional[str] = None) -> JSONResponse:
    """The last seven days, or the seven days up to `ending` when somebody asks for an older week."""
    last = read_day(ending)
    return as_json(reports.weekly(get_db(), end=last))


def read_day(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise DeskRefusal(f"{value} is not a date we can read", 400)
