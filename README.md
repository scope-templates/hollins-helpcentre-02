# Hollins help centre

Hollins Rota is our staff scheduling product, used by cafés, bars, restaurants, hotels and leisure centres:
fifteen hundred venues paying us, most of them with between six and forty people on the books. This is the
support desk that sits behind it. Sixty people work the desk in four teams (two email desks, the in-app
chat team and the evenings-and-weekends team), each with a lead, and I run it. Tickets arrive by email and
from the form inside the app, whoever picks one up looks up a help-centre article and either sends one or
writes the reply out by hand, and the assistant drafts a reply from the articles they found. Since January
the assistant also answers customers inside the app before anybody on the desk sees the question. It has
carried about twelve thousand tickets in the last twelve months against a help centre of a hundred and
twenty three articles, and it is busiest in the first week of every month, when everybody publishes their
rotas, and all through December.

## What is in it

Three collections in the database, and the rest alongside as files. `articles` is the help centre: a slug,
a title, the section it sits in (rotas, time off, pay and hours, staff accounts, billing, integrations,
mobile app), the body, when it was last touched and how many times it has been opened. `accounts` is the
venues paying us, with their plan, how many staff they have on and the town they are in. `tickets` is the
work: the number, the account, whether it came in by email or through the app, the subject and the
customer's own words, the category whoever handled it filed it under, when it opened, when it was first
answered and when it was closed, who answered it and who closed it, the words the desk typed into article
search, the article they sent if they sent one, the reply, and where it got to.

The operations, and what each one will not do:

- `open_ticket` takes a ticket off the in-app form, or off the mail relay with the channel set to
  email, and gives it the next number. A ticket needs a subject and the customer's words, and it
  needs an account we have heard of. Numbers carry on from 5100, where the old desk left off.
- `reply_to_ticket` writes the reply down, against the article the desk sent if there was one. One
  message gets one reply: a customer who writes in again opens a ticket of their own. It refuses on
  a ticket somebody has closed, and it refuses an article slug that is not in the help centre. The
  first reply sets the clock, and nothing after it moves that.
- `close_ticket` closes one, answered or not, because plenty of them are closed by the customer
  sorting it themselves. It signs the closing with its own name and leaves the reply with whoever
  wrote it. Nothing is closed twice.
- `list_tickets` is the queue, newest first, narrowed by status or by account.
- `search_articles` is what the desk types into the box above the ticket. It splits what you typed
  on the spaces and wants every word somewhere in the title or the body, whatever the capitals; the
  article with most of the words in its title comes first, then the one people have opened most.
- `list_articles` and `read_article` are the help centre itself. Reading one counts the read, which
  is how we know which pages earn their keep.
- `draft_for_ticket` takes the top three articles for the words the desk typed, or for the subject
  line when nobody wrote anything down, and asks a language model for a reply in our tone using only
  those articles. It comes back with the draft and the articles it was written from. Without
  `OPENAI_API_KEY` it says so and does nothing else.
- `weekly` is what the leads read on a Monday: what came in, what was answered inside a day, what was
  closed, how much of it went out with an article against how much was written by hand, the ten
  articles that went out most and the sections they came from.

`hollins/db.py` opens the database and keeps the field indexes. `hollins/rules.py` is the desk's
rules on their own, with no database anywhere near them. `hollins/search.py`, `articles.py`,
`tickets.py`, `reports.py`, `assistant.py` and `seed_load.py` are the parts above, and
`hollins/app.py` is the HTTP end of it.

## Running locally

```
docker compose up -d
python -m pip install -r requirements.txt
python -m uvicorn hollins.app:app
```

`docker compose up -d` brings up `mongo:8` on the usual port. If you already have a server
somewhere, skip it and point `MONGODB_URI` at yours instead; it defaults to
`mongodb://localhost:27017`. The database is called `hollins` unless `MONGODB_DB` says otherwise.
The first request against an empty database fills it from the bundled history, so there is
something to look at straight away.

Drafts are the only thing that needs anything else: set `OPENAI_API_KEY`, and `ASSISTANT_MODEL` if
you want a model other than the default. Everything else works without it.

## Tests

```
python -m pytest
```

The rules, the article lookup, the weekly sums and the assistant's prompt run on their own. The
database tests need a server, so set `MONGODB_URI` before you run them; without it they skip and say
so.

## The data

Everything under `data/` is the last twelve months, September 2025 to August 2026, exported on the
fourteenth of September 2026.

- `data/hollins.json`: the help centre (123 articles), the venues (1,500 accounts) and the desk's
  tickets (about 12,000), as the app loads them. `python scripts/seed.py` loads it by hand, with
  `--drop` to empty the collections and load it again.
- `data/staff.csv`: everybody on the desk, their team, their lead, their hours and when they started.
- `data/accounts.csv`: the venues again with what they pay us a year, when they renew, who looks after
  them on our side, and the ones that have left.
- `data/calls/index.csv` and `data/calls/*.txt`: about fifteen hundred recorded calls, transcribed:
  sales calls in and out, the account managers' check-ins and renewal calls, and the support line.
  `docs/call-handling.md` is what everybody on a phone is supposed to do.
- `data/surveys.csv`: the "how did we do" replies that came back after a ticket closed. Most do not.
- `data/assistant_chats.jsonl`: every conversation the in-app assistant has had with a customer since it
  went live in January, one chat per line, with the messages and who, if anybody, took over.
