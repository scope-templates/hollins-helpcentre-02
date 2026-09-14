"""The desk's rules, written down so they hold wherever a ticket is touched from."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

SECTIONS = (
    "rotas",
    "time off",
    "pay and hours",
    "staff accounts",
    "billing",
    "integrations",
    "mobile app",
)
CHANNELS = ("email", "app")
PLANS = ("starter", "team", "venue")
STATUSES = ("open", "replied", "closed")
DESK = (
    "Priya Nair", "Dara Vance", "Sana Dunne", "Pip Iqbal", "Dev Grant", "Imogen Yates", "Maya Ellis", "Xavier Bishop", "Wren Parry", "Owen Tanaka", "Priya Evans", "Cerys Reid", "Mo Pryce", "Aisha Ahmed", "Ivy Lindqvist", "Nico Fletcher", "Lena Haddad", "Callum Rahman", "Callum Doyle", "Gus Turner", "Marcus Rossi", "Petra Whitfield", "Kieran Delgado", "Eilidh Kaur", "Lou Sato", "Umar Oyelaran", "Bea Lowe", "Jade Marsh", "Esme Varga", "Jun Yilmaz", "Eli Zielinski", "Hana Sheridan", "Chloe Jensen", "Will Usher", "Jonah Hollins", "Hamid Patel", "Yasmin Kelly", "Kit Walsh", "Oona Brennan", "Ben Cole", "Abe Nair", "Farah Moran", "Quinn Byrne", "Yara Gibson", "Una Shah", "Rosa Nolan", "Finn Adeyemi", "Amara Okonkwo", "Cal Hussain", "Fay Quigley", "Seb Webb", "Bram Mbeki", "Niamh Osei", "Dot Doyle", "Grace Novak", "Idris Farrell", "Kat Vance", "Tola Dunne", "Rhys Iqbal", "Zach Grant", "Marcus Hollins",
)

FIRST_NUMBER = 5100
SUBJECT_LIMIT = 140
A_DAY = timedelta(hours=24)


class DeskRefusal(Exception):
    """Something the desk will not do, said the way it would be said to a customer."""

    def __init__(self, message: str, status: int = 409) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def on_day(when: Optional[datetime]) -> str:
    """A date in the form the desk writes it, so a refusal reads like a sentence."""
    if when is None:
        return "an unrecorded day"
    return f"{when.day} {when.strftime('%B')}"


def now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def check_channel(channel: str) -> str:
    if channel not in CHANNELS:
        raise DeskRefusal(f"a ticket comes in by {' or '.join(CHANNELS)}, not by {channel}", 400)
    return channel


def check_handler(name: str) -> str:
    if name not in DESK:
        raise DeskRefusal(f"{name} is not on the support desk", 400)
    return name


def check_new_ticket(subject: str, message: str) -> None:
    if not (subject or "").strip():
        raise DeskRefusal("a ticket needs a subject", 400)
    if len(subject) > SUBJECT_LIMIT:
        raise DeskRefusal(f"a subject runs to {SUBJECT_LIMIT} characters", 400)
    if not (message or "").strip():
        raise DeskRefusal("a ticket needs the customer's message", 400)


def check_reply(ticket: Dict[str, Any], text: str) -> None:
    """One reply to one message: a customer who writes again opens a ticket of their own."""
    if not (text or "").strip():
        raise DeskRefusal("a reply needs something in it", 400)
    if ticket.get("status") == "closed":
        raise DeskRefusal(
            f"ticket {ticket['number']} was closed on {on_day(ticket.get('closed_at'))}"
        )
    if ticket.get("reply"):
        raise DeskRefusal(
            f"ticket {ticket['number']} was answered on {on_day(ticket.get('first_reply_at'))}"
        )


def check_close(ticket: Dict[str, Any]) -> None:
    """A ticket is closed once, answered or not: plenty are closed because the customer sorted it."""
    if ticket.get("status") == "closed":
        raise DeskRefusal(
            f"ticket {ticket['number']} was closed on {on_day(ticket.get('closed_at'))}"
        )


def first_reply_at(ticket: Dict[str, Any], when: datetime) -> datetime:
    """The clock starts on the first reply and is not restarted by anything after it."""
    return ticket.get("first_reply_at") or when


def reply_delay(ticket: Dict[str, Any]) -> Optional[timedelta]:
    """How long the customer waited, or nothing at all while they are still waiting."""
    opened = ticket.get("opened_at")
    replied = ticket.get("first_reply_at")
    if opened is None or replied is None:
        return None
    return replied - opened


def replied_within_a_day(ticket: Dict[str, Any]) -> bool:
    waited = reply_delay(ticket)
    return waited is not None and waited <= A_DAY


def next_number(highest: Optional[int]) -> int:
    """Ticket numbers carry on from the desk's old system rather than starting at one."""
    if highest is None or highest < FIRST_NUMBER:
        return FIRST_NUMBER
    return highest + 1
