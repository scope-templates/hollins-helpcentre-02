"""What the assistant sends off and what it hands back, with a stand-in for the SDK."""

import pytest

from hollins.assistant import DEFAULT_MODEL, build_messages, draft_reply, words_to_look_up
from hollins.rules import DeskRefusal

TICKET = {
    "number": 5311,
    "subject": "Holiday allowance looks wrong",
    "message": "One of my supervisors says she has twelve days left and I make it nine.",
    "handled_by": "Callum Doyle",
    "searched_for": "holiday allowance",
}

PAGES = [
    {
        "slug": "holiday-allowance",
        "title": "The holiday allowance for a venue",
        "section": "time off",
        "body": "Set the allowance in days or in hours.",
    },
    {
        "slug": "pro-rata-allowance",
        "title": "Pro rata allowance for part-time staff",
        "section": "time off",
        "body": "Somebody who joined partway through the year gets a part of the allowance.",
    },
]


class Recorded:
    """Stands in for the SDK: keeps what it was called with and hands back a fixed draft."""

    def __init__(self, text="Hi Ellie, the allowance is set per venue."):
        self.text = text
        self.calls = []
        self.chat = self

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        message = type("Message", (), {"content": self.text})
        choice = type("Choice", (), {"message": message})
        return type("Answer", (), {"choices": [choice]})


def test_the_desk_tone_goes_first_and_the_ticket_goes_second():
    messages = build_messages(TICKET, PAGES)
    assert [m["role"] for m in messages] == ["system", "user"]
    assert "British English" in messages[0]["content"]
    assert "Holiday allowance looks wrong" in messages[1]["content"]


def test_the_articles_the_desk_found_go_in_whole_under_the_name_on_the_desk():
    sent = build_messages(TICKET, PAGES)[1]["content"]
    assert "The holiday allowance for a venue" in sent
    assert "Set the allowance in days or in hours." in sent
    assert "Pro rata allowance for part-time staff" in sent
    assert "On the desk: Callum" in sent
    nobody_yet = {k: v for k, v in TICKET.items() if k != "handled_by"}
    assert "On the desk: Priya" in build_messages(nobody_yet, PAGES)[1]["content"]
    assert "no help centre articles" in build_messages(TICKET, [])[1]["content"]


def test_the_draft_comes_back_with_the_articles_it_was_written_from():
    client = Recorded()
    drafted = draft_reply(TICKET, PAGES, client)
    assert drafted["draft"] == client.text
    assert drafted["number"] == 5311
    assert drafted["articles"] == [
        {"slug": "holiday-allowance", "title": "The holiday allowance for a venue"},
        {"slug": "pro-rata-allowance", "title": "Pro rata allowance for part-time staff"},
    ]
    assert client.calls[0]["model"] == DEFAULT_MODEL
    draft_reply(TICKET, PAGES, client, model="something-else")
    assert client.calls[1]["model"] == "something-else"


def test_the_desk_looks_up_what_it_typed_and_otherwise_the_subject():
    assert words_to_look_up(TICKET) == "holiday allowance"
    without = dict(TICKET, searched_for=None)
    assert words_to_look_up(without) == "Holiday allowance looks wrong"


def test_a_draft_needs_a_key_and_says_so_plainly(monkeypatch):
    from hollins import assistant

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(DeskRefusal) as refused:
        assistant.make_client()
    assert refused.value.status == 503
    assert refused.value.message == "drafts need OPENAI_API_KEY to be set"
    monkeypatch.setenv("ASSISTANT_MODEL", "gpt-4o")
    assert assistant.model_name() == "gpt-4o"
    monkeypatch.delenv("ASSISTANT_MODEL")
    assert assistant.model_name() == DEFAULT_MODEL


