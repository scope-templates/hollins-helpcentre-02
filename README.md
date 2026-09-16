# Hollins help centre

Hollins Rota is our staff scheduling product, used by cafés, bars, small restaurants and a handful
of leisure centres — three hundred and thirty eight venues paying us, most of them with between six
and forty people on the books. This is the support desk that sits behind it, and it is what Priya
and Callum work in all day. Tickets arrive by email and from the form inside the app, whoever is on
the desk looks up a help-centre article and either sends one or writes the reply out by hand, and
the assistant drafts a reply from the articles they found so there is something to cut about rather
than a blank box. I pick up the evenings and the weekends. It has carried fourteen hundred and
thirty seven tickets in the last twelve months against a help centre of a hundred and twenty three
articles, and it is busiest in the first week of every month, when everybody publishes their rotas,
and all through December.

## What is in it

Three collections. `articles` is the help centre: a slug, a title, the section it sits in (rotas,
time off, pay and hours, staff accounts, billing, integrations, mobile app), the body, when it was
last touched and how many times it has been opened. `accounts` is the venues paying us, with their
plan, how many staff they have on and the town they are in. `tickets` is the work: the number, the
account, whether it came in by email or through the app, the subject and the customer's own words,
when it opened, when it was first answered and when it was closed, who answered it and who closed
it, the words the desk typed into article search, the article they sent if they sent one, the reply,
and where it got to.

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
- `weekly` is what I read on a Monday: what came in, what was answered inside a day, what was
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

`data/hollins.json` is twelve months of the desk: the last ticket came in on the thirty-first of
August 2026 and the last of those were closed a fortnight into September. A hundred and twenty
three articles, three hundred and thirty eight accounts and fourteen hundred and thirty seven
tickets, with the months and the sections as uneven as they are in real life. It is built by
`python scripts/build_seed.py`, which runs off a fixed seed and writes the same bytes every time —
`--check` tells you whether the file still matches the script. The app loads it the first time it
opens an empty database, and `python scripts/seed.py` does the same by hand, with `--drop` to empty
the collections and load it again.
