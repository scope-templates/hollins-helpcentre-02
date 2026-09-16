"""Builds data/hollins.json: the help centre, the accounts and the last twelve months on the desk.

Everything comes off one seeded Random, so running it again writes the same bytes. Run it with
`python scripts/build_seed.py`, or with `--check` to confirm the committed file still matches.
"""

import argparse
import bisect
import json
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hollins.search import find_articles  # noqa: E402

SEED = 20260901
MOST_FILLER = 2
GENERAL_LINE_CAP = 8
ACCOUNTS = 338
STILL_ON_THE_DESK = 38
FORGOTTEN_VIEWS = 6
LOWEST_ORDINARY_VIEWS = 14
SEEN_AT_A_TIME = 5
RECENTLY = 180
NEWLINE = chr(10)

FROM = date(2025, 9, 1)
THROUGH = date(2026, 8, 31)
OUT = Path(__file__).resolve().parent.parent / "data" / "hollins.json"

DESK = ("Priya Nair", "Callum Doyle", "Marcus Hollins")
SECTIONS = (
    "rotas",
    "time off",
    "pay and hours",
    "staff accounts",
    "billing",
    "integrations",
    "mobile app",
)

# The page an article is about, worked out from its own steps so the opening line and the steps
# never name two different places. The fallback is the section's landing page.
PAGE_NAMES = [
    "Settings > Connections > Payroll",
    "Settings > Billing > Invoices",
    "Settings > Connections",
    "Settings > Permissions",
    "Settings > Billing",
    "Settings > Time off",
    "Settings > Rotas",
    "Settings > Plan",
    "Settings > Pay",
    "Settings > API",
    "Time off > Requests",
    "Rota > Templates",
    "Staff > Documents",
    "Rota > History",
    "Hours > Payroll",
    "Rota > Swaps",
    "Hours > Week",
    "Staff > Team",
]

SECTION_HOME = {
    "rotas": "Rota",
    "time off": "Time off",
    "pay and hours": "Hours",
    "staff accounts": "Staff",
    "billing": "Settings > Billing",
    "integrations": "Settings > Connections",
    "mobile app": "the app",
}

OPENS_AT = (
    ("Open Rota", "Rota"),
    ("Open the rota", "Rota"),
    ("Open Hours", "Hours"),
    ("Open Staff", "Staff"),
    ("Open Time off", "Time off"),
)


# An intro that talks about a recent rewrite only goes on a page that has had one.
INTROS = [
    ("any", "This article is about {thing}. Everything below is done from {where}, and you need to "
     "be a manager or the owner of the account to see the page at all."),
    ("fresh", "The page for {thing} is {where}. It has changed a little since last year and this "
     "article has been brought up to date with it."),
    ("any", "Two or three venues ask us about {thing} every month, usually on a Monday. Here is "
     "what we tell them, in the order we tell them it."),
    ("any", "Everything to do with {thing} sits on one page, which is {where}. You should not need "
     "to go anywhere else for it."),
    ("any", "Managers ask us about {thing} more than almost anything else, so here it is in full. "
     "You will find it under {where}."),
    ("fresh", "We rewrote this page after a busy first week of the month, when we were asked about "
     "{thing} a dozen times in three days. Start at {where}."),
    ("any", "Here is what we tell people who write in about {thing}. Start at {where} and work "
     "down the page."),
    ("any", "If you are new to Hollins Rota, {thing} is worth understanding before your first busy "
     "week. Open {where} and work down."),
    ("any", "This is our page on {thing}. The screens sit in slightly different places on a phone, "
     "but the order of the steps is the same either way."),
    ("any", "Short answer on {thing}: it is all at {where}, and the steps below take you through "
     "it."),
    ("any", "{Thing} comes up a lot with venues who have just taken a second site on. The page is "
     "{where}."),
    ("any", "A couple of the steps below depend on how your venue settings are set, so have those "
     "to hand before you start. The page is {where}."),
    ("any", "We get asked about {thing} in two or three different ways. The answer below is the "
     "one that suits most venues, and the note at the end covers the rest."),
    ("any", "The short version of {thing} is below. The note at the bottom is worth reading as "
     "well as the steps."),
    ("any", "This page covers {thing} from start to finish. It lives under {where}."),
    ("any", "People write in about {thing} most in the first week of the month, when everybody is "
     "publishing. The page is {where}."),
    ("any", "Here is what to do about {thing}, step by step. You will find the page at {where}."),
    ("any", "What follows is our answer on {thing}. Open {where} before you start."),
]

# A line about a change saving only belongs on a page where something is changed, so each one
# says which sort of page it suits.
EXPECT = [
    ("editing", "The change saves as you make it, and a confirmation runs along the top of the "
     "screen. If that confirmation does not appear, nothing has been written down."),
    ("editing", "Managers see the change straight away. Staff see it the next time they open the "
     "app or refresh the page."),
    ("any", "Give it a moment on venue wifi. The page catches up on its own and there is no need "
     "to do it twice."),
    ("editing", "Anything you change here goes into the account history with your name and the "
     "time against it, so there is always a record of who did what."),
    ("editing", "You can come back and change it later. Nothing on this page is set once and for "
     "all."),
    ("editing", "The rest of the team carry on working while you do this. Nothing is taken "
     "offline."),
    ("editing", "It applies from today forward. Anything that has already gone through is left as "
     "it was."),
    ("editing", "If the page looks the same after you save it, refresh it once. Some browsers hold "
     "on to the version they already had."),
    ("editing", "You are asked to confirm before anything is changed for good, and the "
     "confirmation says in plain words what is about to happen."),
    ("editing", "Nothing here happens overnight or on a timer. It is done when the page says it is "
     "done."),
    ("editing", "Whoever it affects is told by email, and the email says who made the change."),
    ("editing", "If two of you are in the same page at once, the last one to save wins, so it is "
     "worth saying out loud who is doing it."),
    ("reading", "What you are looking at is live rather than a snapshot, so a refresh gives you "
     "the newest version of it."),
    ("reading", "Every manager at that venue can open this, and so can the owner."),
    ("reading", "It is worth a look once a week rather than only when something has gone wrong."),
]

DETAIL = [
    ("editing", "If you look after more than one venue this is set per venue and is not shared "
     "between them, so it is worth doing at each site in one sitting."),
    ("editing", "Only owners and managers can do this. A staff account can see the page but the "
     "buttons are greyed out."),
    ("any", "It is easier on a laptop than on a phone, because there is more room on the screen."),
    ("editing", "Most venues set this up in their first fortnight and then leave it alone from one "
     "year to the next."),
    ("any", "There is no charge for any of this and it does not change what your plan costs."),
    ("editing", "Everything here can be undone from the same page, so it is worth trying it out on "
     "a quiet day before you lean on it."),
    ("editing", "If you are not sure whether something saved, the account history under Settings "
     "lists the last ninety days with a name against every line."),
    ("any", "The same page looks slightly different on the older layout. The buttons are in the "
     "same order, they are just along the top rather than down the side."),
    ("any", "If you want somebody here to do it with you on the phone, the desk is open weekdays "
     "from eight until six."),
    ("editing", "This is one of the few things an owner can do that a manager cannot, so it may "
     "need somebody else in the building."),
    ("editing", "It is worth writing down what you have set, because the next person to look after "
     "this will ask."),
    ("any", "If what you are looking at does not seem right, check the date range at the top of "
     "the page first. Nine times out of ten it is sitting on the wrong week."),
    ("any", "There is a printer icon at the top right of this page if you want it on paper."),
    ("any", "On a phone, turn it sideways. The columns fit much better that way."),
    ("reading", "Nothing on this page is worked out overnight; it is right as at the moment you "
     "open it."),
    ("reading", "Managers see their own venues here. The owner sees all of them together."),
]

# A few of the general notes only make sense on a page about the web app or about money.
OFF_TOPIC = {
    "mobile app": ("laptop", "older layout", "greyed out"),
    "billing": ("plan costs",),
    "integrations": ("laptop",),
}

# ---------------------------------------------------------- the help centre, article by article
#
# Each record is one page: its own steps, and its own note about the thing that catches people out.
# The intro and the general advice come from the banks above; everything specific is written here.

ARTICLES = [
    {
        "section": "rotas",
        "title": "Building next week's rota",
        "steps": [
            "Open Rota and move to the week you are building with the arrows on the date bar.",
            "Drag a name from the staff list on the left on to the day you want them on.",
            "Click the shift to set the start, the finish, the role it counts against and its break.",
            "Work across the week a day at a time; the totals under each column keep up as you go.",
            "Press Publish when the week is right, and read the summary before you confirm it.",
        ],
        "note": "A week you have not published yet is visible to managers only, so you can leave it "
        "half built overnight and come back to it. Staff see nothing until you press Publish.",
    },
    {
        "section": "rotas",
        "title": "Publishing a rota so staff can see it",
        "steps": [
            "Finish the week, then press Publish at the top right of the rota.",
            "The summary tells you how many shifts are going out and to how many people.",
            "Confirm it, and everybody with a shift that week gets an email and a push notification.",
            "The week's heading turns from Draft to Published once it has gone.",
        ],
        "note": "Anybody who has not accepted their invitation has no address to send to, so they "
        "are listed on the summary as not notified. Their shifts are still on the rota, and they "
        "will see them the first time they sign in.",
    },
    {
        "section": "rotas",
        "title": "Copying last week's rota forward",
        "steps": [
            "Move to the empty week you want to fill and press Copy week.",
            "Choose which week to copy from; it offers the one before by default.",
            "Say whether to bring notes and open cover shifts across as well as the shifts.",
            "Press Copy, and then edit whatever is different about this week before you publish.",
        ],
        "note": "Copying into a week that already has shifts on it adds to them rather than "
        "replacing them, so a week copied twice ends up with everything on twice. Clear the week "
        "first if you are starting again.",
    },
    {
        "section": "rotas",
        "title": "Saving a week as a template",
        "steps": [
            "Build the week the way you want it kept, then press Save as template.",
            "Give it a name your other managers will recognise, such as Summer week or Quiet week.",
            "Choose whether it keeps the names on the shifts or just the shape of the week.",
            "Apply it later from Rota > Templates on any empty week.",
        ],
        "note": "A template that keeps names goes stale as people leave. A template saved as the "
        "shape only never does, which is why most venues keep one of each.",
    },
    {
        "section": "rotas",
        "title": "Adding a shift to a rota you have already published",
        "steps": [
            "Add the shift as you normally would; the week stays published while you do it.",
            "The new shift shows with a dotted border until you press Publish changes.",
            "Press Publish changes, and only the people affected are told.",
        ],
        "note": "The email that goes out for a change lists what changed rather than repeating the "
        "whole week, so somebody who picks up one extra shift is not sent their whole rota again.",
    },
    {
        "section": "rotas",
        "title": "Moving a shift to somebody else",
        "steps": [
            "Drag the shift from one row to another, or click it and change the name in the box.",
            "Check the warning line if one appears; it will tell you about a clash or a holiday.",
            "Press Publish changes when you are done moving things about.",
        ],
        "note": "Both people are told: the one who has lost the shift and the one who has gained "
        "it. If you are moving several shifts, do them all before you publish so each person gets "
        "one email rather than four.",
    },
    {
        "section": "rotas",
        "title": "Getting back a shift you deleted",
        "steps": [
            "Press Undo in the toolbar, or Ctrl and Z, if you have not left the page.",
            "If you have, open Rota > History and find the line for the deletion.",
            "Press Restore against that line to put the shift back exactly as it was.",
        ],
        "note": "Restoring brings the shift back but does not un-send the email that went out when "
        "you deleted it, so it is worth a word with whoever was on it.",
    },
    {
        "section": "rotas",
        "title": "Putting a break on a shift",
        "steps": [
            "Click the shift and use the Break box to enter the length in minutes.",
            "Tick Unpaid if the break comes off what the shift is worth.",
            "Leave the start time of the break blank unless your venue fixes it.",
        ],
        "note": "A break longer than the shift is refused, and so is a break on a shift under four "
        "hours where the venue setting says breaks start at four.",
    },
    {
        "section": "rotas",
        "title": "Unpaid breaks and how they come off the total",
        "steps": [
            "Set whether breaks are paid or unpaid for the venue under Settings > Rotas.",
            "An unpaid break comes off both the rota'd hours and the worked hours.",
            "A paid break is left in both, and the hours read the same as the shift length.",
        ],
        "note": "Changing the venue setting does not go back and change weeks you have already "
        "published. Those keep whatever the setting was on the day they were built.",
    },
    {
        "section": "rotas",
        "title": "Running rotas for more than one venue",
        "steps": [
            "Use the venue picker at the top left to move between sites.",
            "Each venue has its own week, its own templates and its own publish button.",
            "Publish each venue separately so one site's staff are not told about another's week.",
        ],
        "note": "The staff list is shared across venues, so somebody can be rota'd at either. Their "
        "hours add up across both, which is why a clash warning can come from a site you do not "
        "manage.",
    },
    {
        "section": "rotas",
        "title": "Giving somebody shifts at two venues",
        "steps": [
            "Open the staff record and tick both venues under Works at.",
            "They now appear in the staff list at either site and can be dragged on to either rota.",
            "Set their job at each venue separately if they do different work at each.",
        ],
        "note": "Their contracted hours are one figure across both sites, not one each, so the "
        "warning about going over them counts everything they are on that week.",
    },
    {
        "section": "rotas",
        "title": "Changing the day your rota week starts on",
        "steps": [
            "Open Settings > Rotas and change Week starts on.",
            "Pick the day your trading week actually starts; most of our venues use Monday.",
            "Save, and the rota redraws from that day.",
        ],
        "note": "Weeks you have already published keep the shape they were published in. It is "
        "worth making this change on a quiet week rather than the week before Christmas.",
    },
    {
        "section": "rotas",
        "title": "Locking a rota so nobody else edits it",
        "steps": [
            "Open the week and press the padlock next to the week heading.",
            "The week stays readable but nobody can add, move or delete a shift on it.",
            "Press the padlock again to unlock it.",
        ],
        "note": "A week locked by one manager can still be unlocked by the owner, which is what to "
        "do when the person who locked it is on holiday.",
    },
    {
        "section": "rotas",
        "title": "Who is told when a rota changes",
        "steps": [
            "Everybody with a shift that week is told when you first publish.",
            "After that, only the people whose own shifts changed are told.",
            "Managers at that venue get a copy of every change, whoever made it.",
        ],
        "note": "Notes added to a day do not count as a change to anybody's shift, so nothing goes "
        "out for them. If a note matters, say so in a message rather than expecting the rota to "
        "carry it.",
    },
    {
        "section": "rotas",
        "title": "Stopping rota emails going out at night",
        "steps": [
            "Open Settings > Rotas and find Hold notifications until.",
            "Set a time in the morning, usually seven or eight.",
            "Anything you publish after the evening cut-off waits and goes out at that time.",
        ],
        "note": "The hold is for email and push only. A member of staff who opens the app at "
        "midnight sees the new week straight away, because the rota itself is already live.",
    },
    {
        "section": "rotas",
        "title": "Printing a rota for the back of house",
        "steps": [
            "Open the week and press Print at the top right.",
            "Choose Landscape, and tick Fit to one page if you have more than a dozen names.",
            "Tick Hide rates unless the sheet is only going in the office.",
        ],
        "note": "The printed sheet shows the week as it stands when you print it. If you publish "
        "changes afterwards, the sheet on the wall is out of date and nothing will tell you.",
    },
    {
        "section": "rotas",
        "title": "Sending a rota to a spreadsheet",
        "steps": [
            "Open the week and press Export, then choose the spreadsheet format.",
            "Pick whether you want one row per shift or one row per person.",
            "The file downloads with the venue name and the week in its name.",
        ],
        "note": "The export is a snapshot and does not update itself. Anybody working off it will "
        "be working off the week as it was the moment you pressed the button.",
    },
    {
        "section": "rotas",
        "title": "Roles on a shift and why they matter",
        "steps": [
            "Set up the roles your venue uses under Settings > Rotas, such as bar, floor or kitchen.",
            "Pick a role when you build a shift; the shift takes its colour from the role.",
            "Filter the rota by role to see one part of the venue on its own.",
        ],
        "note": "The role on a shift is what the minimum staffing warning counts, so a shift left "
        "with no role is invisible to it. Every shift is worth a role even when it seems obvious.",
    },
    {
        "section": "rotas",
        "title": "The warning when somebody is on twice",
        "steps": [
            "The shift shows a red corner and a line at the top of the column names the clash.",
            "Click the warning to see the other shift, whichever venue it is at.",
            "Move or shorten one of the two, and the warning clears on its own.",
        ],
        "note": "The warning is a warning and not a refusal, because a shift in two halves with a long gap "
        "is a real thing at some venues. You can publish through it and it stays on the rota as a "
        "reminder.",
    },
    {
        "section": "rotas",
        "title": "The warning when a shift goes over contracted hours",
        "steps": [
            "Set contracted hours on each staff record first, or the warning has nothing to count.",
            "Build the week as normal; the total under each name turns amber when it goes over.",
            "Hover the total to see the contracted figure and the difference.",
        ],
        "note": "It counts the rota'd hours for the week, not the worked hours, so a week that ends "
        "up over because somebody stayed late will not have warned you when you built it.",
    },
    {
        "section": "rotas",
        "title": "Staff swapping shifts between themselves",
        "steps": [
            "A member of staff opens their shift in the app and taps Offer to swap.",
            "The offer goes to everybody at that venue who is free and does that role.",
            "The first person to accept it takes the shift, and the swap waits for a manager.",
            "Approve or turn it down from Rota > Swaps, or from the email you are sent.",
        ],
        "note": "Nothing moves on the rota until a manager approves it, so an unapproved swap "
        "leaves the original person still on the shift and still responsible for it.",
    },
    {
        "section": "rotas",
        "title": "Approving a swap",
        "steps": [
            "Open Rota > Swaps, or follow the link in the email.",
            "Check the hours line, which shows what the week comes to for both people afterwards.",
            "Press Approve, and the two shifts change hands and both people are told.",
        ],
        "note": "Turning a swap down puts it back as it was and tells both of them. It is worth "
        "writing a line about why, because the app shows your words to both sides.",
    },
    {
        "section": "rotas",
        "title": "Offering a shift to the whole team",
        "steps": [
            "Click the shift and press Offer to team rather than putting a name on it.",
            "Choose which roles are allowed to pick it up.",
            "Publish, and everybody who qualifies sees it in the app as an open shift.",
        ],
        "note": "An offered shift with nobody on it still counts towards the minimum staffing "
        "warning as unfilled, which is what stops one quietly sitting there until the day.",
    },
    {
        "section": "rotas",
        "title": "Leaving a shift open for cover",
        "steps": [
            "Add the shift and leave the name blank; it shows as Cover needed in grey.",
            "Add a note on the shift saying what it is for, such as covering sickness.",
            "Fill it later by dragging a name on to it and publishing the change.",
        ],
        "note": "Open cover shifts are counted in the rota'd hours for the week even though nobody "
        "is on them, so the wage cost figure reads high until they are filled or removed.",
    },
    {
        "section": "rotas",
        "title": "Notes on a day of the rota",
        "steps": [
            "Click the date at the head of the column and type into the note box.",
            "Use it for the things the shifts cannot say, such as a delivery or a private party.",
            "The note shows to everybody at that venue, on the web and in the app.",
        ],
        "note": "A note is not a shift, so nobody is emailed about one and it does not appear on "
        "the printed sheet unless you tick Include notes before you print.",
    },
    {
        "section": "rotas",
        "title": "Rota history and who changed what",
        "steps": [
            "Open Rota > History and pick the week you are asking about.",
            "Every line has the time, the name of whoever did it, and what changed.",
            "Press Restore against a line to put the rota back to how it was before it.",
        ],
        "note": "History goes back a year. Restoring is itself a change and goes on the list, so "
        "there is no way to quietly undo something.",
    },
    {
        "section": "rotas",
        "title": "Bank holidays on the rota",
        "steps": [
            "Set which bank holidays your venue observes under Settings > Rotas.",
            "Observed days show shaded on the rota so nobody builds a normal week by accident.",
            "Rota staff on as usual if you are trading; the shading is a reminder, not a block.",
        ],
        "note": "Marking a day as observed does not change anybody's pay. Bank holiday rates, if "
        "you pay them, are set under Settings > Pay and applied to the day separately.",
    },
    {
        "section": "rotas",
        "title": "Christmas and new year weeks",
        "steps": [
            "Build the fortnight early and publish it in one go, so nobody has to ask.",
            "Use a template saved from last year if the shape of your Christmas is the same.",
            "Block the dates you are closed under Time off so nobody books them as holiday.",
        ],
        "note": "Our own desk is thin between Christmas and the new year, so anything you want "
        "changed for the fortnight is best asked about before the third week of December.",
    },
]

ARTICLES += [
    {
        "section": "time off",
        "title": "Booking time off for a member of staff",
        "steps": [
            "Open Time off and choose the name from the list on the left.",
            "Pick the first and the last day from the calendar.",
            "Choose full days or half days, and whether it comes off the allowance or is unpaid.",
            "Press Save; it goes to whoever manages that venue for approval.",
        ],
        "note": "Booking it yourself as a manager does not approve it. It still sits in the "
        "requests list until somebody with approval rights presses the button, which is deliberate "
        "so two managers do not let the same week go twice.",
    },
    {
        "section": "time off",
        "title": "Approving a holiday request",
        "steps": [
            "Open Time off > Requests, or follow the link in the email you were sent.",
            "Look at the calendar strip at the top, which shows anybody else off that week.",
            "Press Approve, and the days are blocked on the rota and come off the allowance.",
        ],
        "note": "Approving time off over a week you have already published does not delete the "
        "shifts on it. They stay, marked as a clash, until you take them off yourself.",
    },
    {
        "section": "time off",
        "title": "Turning a holiday request down",
        "steps": [
            "Open the request and press Decline.",
            "Write a line saying why; the member of staff sees exactly what you type.",
            "The days go back on their allowance straight away.",
        ],
        "note": "A declined request cannot be approved afterwards. If you change your mind, ask "
        "them to put it in again, or book it for them from the same page.",
    },
    {
        "section": "time off",
        "title": "Cancelling time off that was already approved",
        "steps": [
            "Open the booking from the staff record and press Cancel.",
            "Say whether the days go back on the allowance; they do by default.",
            "Confirm, and the block comes off the rota for those days.",
        ],
        "note": "Cancelling frees the days but does not put any shifts back. Whatever you took off "
        "the rota when the holiday was approved has to be rota'd again by hand.",
    },
    {
        "section": "time off",
        "title": "Setting your holiday year",
        "steps": [
            "Open Settings > Time off and set the month your holiday year starts.",
            "Most venues use January or April; it does not have to match your financial year.",
            "Save, and the allowance figures redraw against the new year.",
        ],
        "note": "Changing the month partway through leaves everybody with a short year, and the "
        "allowance is worked out pro rata for it. It is worth doing at the end of a year rather "
        "than the middle.",
    },
    {
        "section": "time off",
        "title": "The holiday allowance for a venue",
        "steps": [
            "Open Settings > Time off and set the standard allowance for the venue.",
            "Choose whether you are counting in days or in hours before you enter the figure.",
            "Override it on any individual staff record where somebody has a different deal.",
        ],
        "note": "Changing the venue allowance does not touch anybody who already has an override "
        "on their record, which is how a long-serving member of staff keeps their extra days when "
        "you change the standard.",
    },
    {
        "section": "time off",
        "title": "Allowance in days and allowance in hours",
        "steps": [
            "Pick one under Settings > Time off; it applies to everybody at that venue.",
            "In days, a booking takes a whole day off whatever length the shift would have been.",
            "In hours, a booking takes the hours the person would normally have worked that day.",
        ],
        "note": "Hours suit venues where people work very different shift lengths, and days suit "
        "everybody else. Switching between them converts the figures using the contracted hours on "
        "each record, so those need to be right before you switch.",
    },
    {
        "section": "time off",
        "title": "Pro rata allowance for part-time staff",
        "steps": [
            "Put the contracted hours on the staff record.",
            "Tick Work out pro rata on the same record.",
            "The allowance shows as a share of the venue standard, to the nearest half day.",
        ],
        "note": "Somebody who joins partway through the holiday year gets their allowance worked "
        "out from their start date as well, so both reductions apply to the same person.",
    },
    {
        "section": "time off",
        "title": "Carrying holiday into next year",
        "steps": [
            "Open Settings > Time off and set how many days may be carried.",
            "Set the date by which carried days must be taken, if you have one.",
            "On the first day of the new year, anything left up to that limit moves across.",
        ],
        "note": "The carry happens once, overnight on the first day of the new holiday year. "
        "Changing the limit after that does not go back and redo it, so anybody you have missed has "
        "to be adjusted on their own record.",
    },
    {
        "section": "time off",
        "title": "Booking a half day",
        "steps": [
            "Book the day as normal and choose Half day instead of Full day.",
            "Say whether it is the morning or the afternoon.",
            "The rota shows the day as half shaded, so you can still put a shift on the other half.",
        ],
        "note": "A half day always takes half of the standard day off the allowance, even at "
        "venues counting in hours, which keeps the figures readable.",
    },
    {
        "section": "time off",
        "title": "Time off that lands on a bank holiday",
        "steps": [
            "Check that the day is marked as observed under Settings > Rotas first.",
            "Book the time off as normal across the dates you want.",
            "Observed bank holidays inside the booking are skipped and not counted.",
        ],
        "note": "If the day is not marked as observed it counts as an ordinary day and comes off "
        "the allowance, which is the most common reason somebody says their allowance is a day out.",
    },
    {
        "section": "time off",
        "title": "Blocking dates nobody can book off",
        "steps": [
            "Open Settings > Time off and add a blocked period with a first and last day.",
            "Give it a reason, such as our busiest fortnight, so people know why.",
            "Requests over a blocked period are refused as they are made, with your reason shown.",
        ],
        "note": "Blocking dates does not cancel anything already approved over them. Have a look "
        "through what is already booked before you rely on a block.",
    },
    {
        "section": "time off",
        "title": "How many people you let off at once",
        "steps": [
            "Open Settings > Time off and set the most people who may be off on any one day.",
            "Set it per role if your kitchen and your floor need counting separately.",
            "Requests that would take you over show a warning to whoever is approving.",
        ],
        "note": "It warns, it does not refuse, because a manager often knows a week is quiet. The "
        "warning names who else is off so you can decide without leaving the page.",
    },
    {
        "section": "time off",
        "title": "Recording sickness",
        "steps": [
            "Open the staff record and press Add absence rather than booking time off.",
            "Choose Sickness, set the days and add a note if you need one.",
            "Sickness comes off the rota but never off the holiday allowance.",
        ],
        "note": "Sickness on a day somebody was rota'd leaves the shift showing as needing cover, "
        "which is what puts it in front of whoever is filling the week.",
    },
    {
        "section": "time off",
        "title": "Unpaid leave",
        "steps": [
            "Book it the same way as holiday and choose Unpaid for the type.",
            "The days block the rota and show on the year, but do not touch the allowance.",
            "Unpaid days are left out of the hours that go to payroll.",
        ],
        "note": "Unpaid leave still counts towards the how many people are off at once figure, "
        "because the venue is a body down either way.",
    },
    {
        "section": "time off",
        "title": "Who a holiday request goes to",
        "steps": [
            "A request goes to the managers of the venue on that person's staff record.",
            "Check the venue on the record if requests are landing with the wrong person.",
            "Add or remove managers for a venue under Settings > Permissions.",
        ],
        "note": "Somebody who works at two venues sends their requests to the managers of the "
        "venue marked as their main one, not to both.",
    },
    {
        "section": "time off",
        "title": "The allowance a member of staff sees left",
        "steps": [
            "They open the app, tap You, then Time off.",
            "The figure is the allowance less what is approved and less what is taken.",
            "Requests waiting on a manager are shown separately underneath.",
        ],
        "note": "The figure counts the whole holiday year, including days later in the year they "
        "have already booked, which is why it can look lower than somebody expects in the spring.",
    },
    {
        "section": "time off",
        "title": "Correcting an allowance halfway through the year",
        "steps": [
            "Open the staff record and set the override under Allowance.",
            "Add an adjustment line instead if you only want to give or take a day or two.",
            "Save, and the figure they see changes the next time they open the app.",
        ],
        "note": "An adjustment line stays on the record with your name and the date on it, which is "
        "the version to use when you want to be able to explain it later.",
    },
    {
        "section": "time off",
        "title": "Holiday owed to somebody leaving",
        "steps": [
            "Mark them as a leaver with their last day.",
            "Open their time off page and read the figure marked Owed at leaving.",
            "It is the allowance earned up to the last day, less what they have taken.",
        ],
        "note": "The figure can be negative if somebody has taken more than they had earned by the "
        "time they left, and the page says so in words rather than showing a minus sign.",
    },
]

ARTICLES += [
    {
        "section": "pay and hours",
        "title": "Where the hours on a payslip come from",
        "steps": [
            "Hours come from clock-ins where the venue uses them, and from the rota where it does not.",
            "Open Hours and pick the week to see the two side by side.",
            "Whatever is in the worked column when you approve the week is what goes to payroll.",
        ],
        "note": "A venue with clocking half turned on is the one case that catches people: staff "
        "who clock have their worked hours counted, and staff who do not fall back to the rota, in "
        "the same week.",
    },
    {
        "section": "pay and hours",
        "title": "Clocking in and out",
        "steps": [
            "Turn clocking on for the venue under Settings > Pay.",
            "Staff clock in at the start of the shift and out at the end, on the app or the tablet.",
            "A shift shows as running until they clock out.",
        ],
        "note": "Clocking in more than half an hour before the shift starts is refused with a line "
        "on screen, which is the setting most venues want and the one nobody expects.",
    },
    {
        "section": "pay and hours",
        "title": "Clocking in on the venue tablet",
        "steps": [
            "Sign the tablet in once as the venue under Settings > Pay, then leave it signed in.",
            "Staff tap their own name and enter their four digit code.",
            "The tablet shows who is on and who is due in for the rest of the day.",
        ],
        "note": "The tablet keeps clock-ins on the device when the wifi drops and sends them when "
        "it comes back, so the times are right even though they appear late.",
    },
    {
        "section": "pay and hours",
        "title": "Rounding clock-in times",
        "steps": [
            "Open Settings > Pay and choose the rounding, such as to the nearest five minutes.",
            "Choose whether it rounds in the venue's favour, the staff member's, or to nearest.",
            "Save; it applies to clock-ins from that point on.",
        ],
        "note": "Rounding is applied to the clock and never to the rota, so a rounded week can "
        "differ from the hours you rota'd by a few minutes even when everybody was on time.",
    },
    {
        "section": "pay and hours",
        "title": "Approving the week's hours",
        "steps": [
            "Open Hours and pick the week you are paying.",
            "Work down the flags: open shifts, big differences and anything corrected.",
            "Press Approve week when the totals look right.",
        ],
        "note": "Approving does not lock the week. It marks it ready and lets the payroll file be "
        "built; locking is a separate step and is the one that stops changes.",
    },
    {
        "section": "pay and hours",
        "title": "Editing hours you have already approved",
        "steps": [
            "Open the week and press Reopen at the top.",
            "Make the correction and say why in the box; the reason stays on the line.",
            "Approve the week again.",
        ],
        "note": "Reopening is refused once the period is locked. At that point the correction "
        "belongs on the next period as an adjustment, which is what payroll will be expecting.",
    },
    {
        "section": "pay and hours",
        "title": "Missed clock-outs and how to put them right",
        "steps": [
            "Open Hours; anything still running shows in amber with the word Open against it.",
            "Click the line and type the finish time the shift actually ended at.",
            "Give a reason, save, and the hours drop into the total.",
        ],
        "note": "A shift left open never counts towards the week at all, rather than counting as a "
        "very long one, so the week reads low rather than high until you fix it.",
    },
    {
        "section": "pay and hours",
        "title": "Hours worked against hours rota'd",
        "steps": [
            "Open Hours > Week; the two columns sit next to each other with the difference beside them.",
            "Sort by the difference to bring the biggest gaps to the top.",
            "Click any line to see the clock-ins behind the worked figure.",
        ],
        "note": "Open cover shifts count in the rota'd column with nobody on them, so a week with "
        "cover still unfilled will always read as rota'd more than worked.",
    },
    {
        "section": "pay and hours",
        "title": "Overtime and how it is counted",
        "steps": [
            "Put contracted hours on the staff record; overtime is anything over that in a week.",
            "Set the overtime rate under Settings > Pay, as a multiplier or a flat rate.",
            "The overtime column on the hours page fills in as the week goes past the contract.",
        ],
        "note": "Somebody with no contracted hours on their record has no threshold to pass, so "
        "they never show overtime however many hours they do.",
    },
    {
        "section": "pay and hours",
        "title": "Setting hourly rates",
        "steps": [
            "Open the staff record and enter the rate under Pay.",
            "Set the date it applies from; leave it as today for a rate starting now.",
            "Save, and the wage cost figures redo themselves from that date forward.",
        ],
        "note": "A rate that starts midweek applies from that day only, so one week can carry two "
        "rates for the same person and the payroll file shows them on two lines.",
    },
    {
        "section": "pay and hours",
        "title": "Different rates at different venues",
        "steps": [
            "Open the staff record and open the Pay tab.",
            "Add a rate against each venue rather than one rate for the person.",
            "Shifts are costed at the rate for the venue they are at.",
        ],
        "note": "Overtime for somebody working at two venues is paid at the rate of the venue where "
        "the hours took them over the contract, which is whichever shift came last in the week.",
    },
    {
        "section": "pay and hours",
        "title": "Holiday pay and the twelve week average",
        "steps": [
            "Turn the average on under Settings > Pay.",
            "It uses the twelve paid weeks before the holiday, skipping weeks with no hours.",
            "The figure shows on the holiday booking and goes into the payroll file as its own line.",
        ],
        "note": "Somebody who has been with you fewer than twelve weeks is averaged over what "
        "there is, and the booking says how many weeks it used.",
    },
    {
        "section": "pay and hours",
        "title": "Tronc and tips",
        "steps": [
            "Open Settings > Pay and turn Tronc on for the venue.",
            "Enter the pot for the week on the Hours page, once the week is approved.",
            "Choose how it divides: evenly, by hours worked, or by points you set per role.",
        ],
        "note": "Tronc sits outside the wage cost figures and is shown separately, because the two "
        "are not the same money and reading them together makes the percentage look wrong.",
    },
    {
        "section": "pay and hours",
        "title": "Sending hours to payroll",
        "steps": [
            "Approve the week, then open Hours > Payroll.",
            "Choose the pay period and press Build file.",
            "Download it, or let the nightly transfer send it if you have a connection set up.",
        ],
        "note": "Building the file twice for the same period gives you the same figures, not two "
        "sets. It is safe to rebuild it after a correction as long as the period is not locked.",
    },
    {
        "section": "pay and hours",
        "title": "The payroll file and what is in each column",
        "steps": [
            "The first columns are the payroll reference, the name and the venue.",
            "Then the basic hours, the overtime hours and the holiday hours, each to two decimals.",
            "Then the rate for each, and a line per rate where somebody had more than one.",
        ],
        "note": "The payroll reference comes from the staff record and is blank until somebody puts "
        "it there. A blank reference is the usual reason a file is refused at the other end.",
    },
    {
        "section": "pay and hours",
        "title": "Locking a pay period",
        "steps": [
            "Open Hours > Payroll and press Lock against the period once payroll has gone.",
            "Locked weeks cannot be reopened, corrected or rebuilt.",
            "Only the owner can unlock one, and it goes on the account history when they do.",
        ],
        "note": "Anything found after a lock goes on the next period as an adjustment line, which "
        "is why most venues lock the moment the file has been sent rather than at the month end.",
    },
    {
        "section": "pay and hours",
        "title": "Contracted hours and how to set them",
        "steps": [
            "Open the staff record and enter the hours under Contract.",
            "Enter nought for somebody on no fixed hours; the warnings then leave them alone.",
            "Save; the rota starts counting against the new figure from the next week you build.",
        ],
        "note": "The figure is per week even where you pay monthly, because the rota and the "
        "warnings both work in weeks.",
    },
    {
        "section": "pay and hours",
        "title": "Wage cost percentage on the rota",
        "steps": [
            "Enter the day's takings by hand, or bring them in from the till.",
            "The bar along the top of the rota shows wage cost against takings for each day.",
            "Set the figure you are aiming at under Settings > Pay so the bar can colour itself.",
        ],
        "note": "It is wage cost before employer costs, so it reads lower than the figure your "
        "accountant works to. Most venues set their target a few points under to allow for it.",
    },
]

ARTICLES += [
    {
        "section": "staff accounts",
        "title": "Adding a member of staff",
        "steps": [
            "Open Staff and press Add.",
            "Fill in the name, the job, the venue and their contracted hours.",
            "Add an email address if they have one, or leave it blank and use a code instead.",
            "Save; they appear in the staff list and can be rota'd straight away.",
        ],
        "note": "Somebody added on the first of the month counts towards that month's bill even if "
        "they have not accepted their invitation yet, because the count is of people on the books.",
    },
    {
        "section": "staff accounts",
        "title": "Inviting a member of staff by email",
        "steps": [
            "Open the staff record and check the email address is right.",
            "Press Invite; the email goes out within a minute or two.",
            "The record shows Invited until they set a password, then Active.",
        ],
        "note": "An invitation runs out after fourteen days. The link then says it is no longer "
        "valid, which is the usual reason a new starter cannot get in on their first shift.",
    },
    {
        "section": "staff accounts",
        "title": "Inviting somebody with no email address",
        "steps": [
            "Leave the email field blank on the staff record and save it.",
            "Press Get sign-in code; a six character code appears on screen.",
            "They enter their name and that code in the app to set a password.",
        ],
        "note": "The code is good for seven days and for one person only. Write it down when it "
        "appears, because the page will not show you the same one twice.",
    },
    {
        "section": "staff accounts",
        "title": "Sending an invitation again",
        "steps": [
            "Open the staff record and press Invite again.",
            "The old link stops working the moment the new one goes out.",
            "Check the address on the record first if the last one went nowhere.",
        ],
        "note": "Sending it a second time to the same address that swallowed the first rarely "
        "helps. A personal address usually gets through where a shared venue inbox does not.",
    },
    {
        "section": "staff accounts",
        "title": "An invitation that never arrived",
        "steps": [
            "Ask them to look in spam and in any promotions folder.",
            "Check the address on the staff record for a typo, which is most of them.",
            "If it is right, use a sign-in code instead and get them going today.",
        ],
        "note": "Venue inboxes on shared mail systems are the common culprit, because the filter "
        "treats a message that looks like an invitation to somebody else as suspicious.",
    },
    {
        "section": "staff accounts",
        "title": "Resetting a password somebody has forgotten",
        "steps": [
            "They tap Forgotten password on the sign-in screen and follow the email.",
            "If they cannot get at the address, change it on their record first.",
            "A manager can also press Send reset from the staff record.",
        ],
        "note": "The reset link runs out after two hours, which is short on purpose. A link that "
        "has expired says so plainly and they can ask for another straight away.",
    },
    {
        "section": "staff accounts",
        "title": "Changing the email on an account",
        "steps": [
            "Open the staff record and edit the address under Contact.",
            "Save; a note goes to both the old address and the new one.",
            "They sign in with the new address from that moment.",
        ],
        "note": "Changing the address signs them out of the app on every phone, so it is worth "
        "warning somebody before you do it mid-shift.",
    },
    {
        "section": "staff accounts",
        "title": "What managers can see",
        "steps": [
            "A manager sees the rota, the hours and the staff records for their venues.",
            "They can approve time off and swaps, and publish a rota.",
            "They cannot see billing, and they cannot change the plan or the card.",
        ],
        "note": "Wage costs are the line most people ask about: a manager sees them for their own "
        "venues only, and a shared report leaves out any venue they do not manage rather than "
        "refusing to open.",
    },
    {
        "section": "staff accounts",
        "title": "Making somebody a manager",
        "steps": [
            "Open the staff record and change Permission from Staff to Manager.",
            "Tick which venues they manage.",
            "Save; they see the manager screens the next time they sign in.",
        ],
        "note": "Making somebody a manager does not change their pay, their contract or anything "
        "on the rota. It only changes what they can see and press.",
    },
    {
        "section": "staff accounts",
        "title": "Keeping a manager to one venue",
        "steps": [
            "Open the staff record and open Permission.",
            "Untick every venue except the one they run.",
            "Save; anything belonging to the other venues disappears from their screens.",
        ],
        "note": "A manager limited to one venue still sees staff who work at both, because they "
        "have to be able to rota them. They see only the shifts at their own site.",
    },
    {
        "section": "staff accounts",
        "title": "Handing the owner account to somebody else",
        "steps": [
            "Sign in as the current owner and open Settings > Permissions.",
            "Press Hand over and choose a manager to hand it to.",
            "Confirm from the email that arrives; the change happens when you follow that link.",
        ],
        "note": "There is one owner on an account and the handover is not reversible from the new "
        "owner's side alone, so make sure it is going to the right person before you confirm.",
    },
    {
        "section": "staff accounts",
        "title": "Marking somebody as a leaver",
        "steps": [
            "Open the staff record and press Mark as leaver.",
            "Enter the date of their last shift.",
            "Save; they come off the rota from the day after and stop counting on the bill.",
        ],
        "note": "Shifts already on the rota after their last day stay there until you take them "
        "off, showing as needing cover, which is deliberate so a week does not quietly go short.",
    },
    {
        "section": "staff accounts",
        "title": "A leaver who comes back",
        "steps": [
            "Find them under Staff with the Leavers filter on.",
            "Press Reinstate and give the date they are starting again.",
            "Check the venue, the job and the rate, which are as they were when they left.",
        ],
        "note": "Their holiday allowance starts again from the new date, and last year's booked "
        "days stay on the record as history rather than counting against this year.",
    },
    {
        "section": "staff accounts",
        "title": "Staff who work at more than one venue",
        "steps": [
            "Open the staff record and tick every venue they work at under Works at.",
            "Mark one of them as their main venue; that is where their requests go.",
            "Set a job and a rate for each venue if the two are different.",
        ],
        "note": "They count once on the bill however many venues they work at, because the bill "
        "counts people rather than places.",
    },
    {
        "section": "staff accounts",
        "title": "Right to work documents",
        "steps": [
            "Open the staff record and go to Documents.",
            "Upload the document and give it a type and an expiry date.",
            "The record shows a green tick once a right to work document is on file.",
        ],
        "note": "Documents are visible to managers and owners only, never to the member of staff "
        "themselves, and they are kept for as long as the staff record is.",
    },
    {
        "section": "staff accounts",
        "title": "Documents that are about to run out",
        "steps": [
            "Reminders go to the venue managers sixty days and thirty days before an expiry.",
            "Open Staff > Documents and use the Expiring filter to see them together.",
            "Upload the new document against the same record; the old one stays as history.",
        ],
        "note": "Nothing happens automatically on the expiry date. Nobody comes off the rota and no "
        "shift is refused; the record simply shows the expiry in red until it is dealt with.",
    },
]

ARTICLES += [
    {
        "section": "billing",
        "title": "What a plan costs",
        "steps": [
            "Open Settings > Plan to see what you are on and what the others cost.",
            "Starter is for one venue and up to ten people on the books.",
            "Team is one venue and no limit on people; Venue is for more than one site.",
            "Every plan is priced per month per active member of staff, billed in arrears.",
        ],
        "note": "The page shows the price against your own staff count rather than a table, which "
        "is why two venues on the same plan see different figures.",
    },
    {
        "section": "billing",
        "title": "What counts as an active member of staff",
        "steps": [
            "The count is taken on the first of the month.",
            "Anybody not marked as a leaver on that day counts, whether or not they were rota'd.",
            "Leavers, and anybody added after the first, do not count until the next month.",
        ],
        "note": "Somebody who leaves on the second of the month is counted for that month in full. "
        "There is no part month for staff, only for plans.",
    },
    {
        "section": "billing",
        "title": "Moving from starter to team",
        "steps": [
            "Open Settings > Plan and press Change plan.",
            "Choose Team; the page shows what the rest of this month comes to.",
            "Confirm, and the extra is taken straight away.",
        ],
        "note": "Moving up takes effect the moment you press it, which is what you want when you "
        "have hit the starter limit and cannot add the person in front of you.",
    },
    {
        "section": "billing",
        "title": "Moving down a plan",
        "steps": [
            "Open Settings > Plan and choose the smaller plan.",
            "The page warns you about anything the smaller plan cannot hold.",
            "Confirm; the change happens on your next billing date, not today.",
        ],
        "note": "Nothing is deleted when you move down. A second venue on an account that drops to "
        "Team becomes read only rather than disappearing, and comes back if you move up again.",
    },
    {
        "section": "billing",
        "title": "Changing the card on the account",
        "steps": [
            "Open Settings > Billing and press Change card.",
            "Enter the new details; you may be sent to your bank to confirm.",
            "Save, and the old card is removed at the same moment.",
        ],
        "note": "A new card is checked with a small authorisation that is released within a few "
        "days. It is not a charge, although it shows as one on some banking apps.",
    },
    {
        "section": "billing",
        "title": "A card payment that failed",
        "steps": [
            "Open Settings > Billing; the failed charge is at the top with the reason given.",
            "Fix whatever the reason says, usually by putting a new card on.",
            "Press Retry to take the payment now rather than waiting.",
        ],
        "note": "A failed payment is tried again after three days and then after a week. Nothing "
        "stops working before the second of those, and rotas stay readable even after it.",
    },
    {
        "section": "billing",
        "title": "Where to find your invoices",
        "steps": [
            "Open Settings > Billing > Invoices.",
            "Every month is listed with the date, the amount and the staff count it was based on.",
            "Press the arrow at the end of a line to download it as a PDF.",
        ],
        "note": "Invoices stay downloadable for seven years, including after an account closes, so "
        "there is no need to save them all somewhere else as you go.",
    },
    {
        "section": "billing",
        "title": "Getting a VAT invoice",
        "steps": [
            "Open Settings > Billing and fill in the company name, address and VAT number.",
            "Save, then download the invoice you need.",
            "Older invoices can be rebuilt with the new details from the same list.",
        ],
        "note": "Rebuilding an old invoice keeps its original number and date and only changes the "
        "details at the top, which is what an accountant needs it to do.",
    },
    {
        "section": "billing",
        "title": "Changing the billing email",
        "steps": [
            "Open Settings > Billing and edit the address under Billing contact.",
            "Save; invoices and payment notices go there from now on.",
        ],
        "note": "The billing address is separate from any staff record, so changing somebody's "
        "staff email does not move the invoices, and this is where to look when they keep going to "
        "somebody who has left.",
    },
    {
        "section": "billing",
        "title": "Paying yearly instead of monthly",
        "steps": [
            "Open Settings > Plan and choose Yearly.",
            "The page works out the year from your current staff count and takes off what you have "
            "already paid this month.",
            "Confirm; the next charge is a year away.",
        ],
        "note": "A yearly account still counts staff every month, and a venue that grows a lot is "
        "billed for the difference at the year end rather than each month.",
    },
    {
        "section": "billing",
        "title": "Adding a second venue to the bill",
        "steps": [
            "Open Settings > Plan and press Add venue.",
            "Name it and give its town; it appears in the venue picker straight away.",
            "The bill changes from the day you add it, worked out for the rest of the month.",
        ],
        "note": "Adding a venue on Starter or Team moves you up to the Venue plan as part of the "
        "same step, and the page tells you what that comes to before you confirm.",
    },
    {
        "section": "billing",
        "title": "Taking a venue off the bill",
        "steps": [
            "Move or mark as leavers anybody who only worked at that venue.",
            "Open Settings > Plan and press Remove against the venue.",
            "Confirm; it comes off the bill on your next billing date.",
        ],
        "note": "The venue's rotas and hours stay readable afterwards and can still be exported. "
        "Nothing more can be published at it, which is what makes it safe to leave alone.",
    },
    {
        "section": "billing",
        "title": "Pausing an account over the winter",
        "steps": [
            "Open Settings > Plan and press Pause.",
            "Give the date you want to start again; you can change it later.",
            "Nothing is charged while paused, and it starts itself again on that date.",
        ],
        "note": "While paused, rotas and hours stay readable and nothing can be published. Staff "
        "can still sign in and look at what is already there, which suits a seasonal venue.",
    },
    {
        "section": "billing",
        "title": "Closing an account",
        "steps": [
            "Open Settings > Plan and press Close account at the foot of the page.",
            "Type the venue name to confirm you mean it.",
            "Export anything you want to keep before the date it closes.",
        ],
        "note": "The account closes at the end of the month you are paid up to rather than that "
        "day, so there is time to change your mind and time to get your exports out.",
    },
    {
        "section": "billing",
        "title": "Reading the charges on your statement",
        "steps": [
            "Every line names the month it covers and the number of staff it counted.",
            "Part months from a plan change show as their own line with the dates on them.",
            "Compare the line against the invoice of the same date under Invoices.",
        ],
        "note": "A month with a plan change in it has two lines rather than one, which is why a "
        "statement can show two charges in a month when nothing has gone wrong.",
    },
]

ARTICLES += [
    {
        "section": "integrations",
        "title": "Putting the rota in a calendar",
        "steps": [
            "Open the rota and press Calendar link at the top right.",
            "Copy the link it gives you.",
            "In your own calendar, add it as a subscribed calendar rather than importing it.",
        ],
        "note": "Importing it instead of subscribing gives you a one-off copy that never changes "
        "again, which is the usual reason somebody's calendar is stuck on an old week.",
    },
    {
        "section": "integrations",
        "title": "Calendar links and how they keep up to date",
        "steps": [
            "The link is live and always shows the rota as it stands.",
            "How often it is read is decided by your calendar, not by us.",
            "Force a refresh in your calendar if you need the newest week this minute.",
        ],
        "note": "Some calendars only look once every few hours, and a few only once a day, so a "
        "rota published this morning can take until the evening to appear.",
    },
    {
        "section": "integrations",
        "title": "Setting up the payroll connection",
        "steps": [
            "Open Settings > Connections and press Connect against your payroll provider.",
            "Sign in to them in the window that opens and allow the connection.",
            "Choose which venues it covers, then match your staff to theirs.",
            "Press Test to send one period through and read what comes back.",
        ],
        "note": "Anybody left unmatched is left out of every transfer without stopping it, so the "
        "matching screen is worth going through twice before you rely on it.",
    },
    {
        "section": "integrations",
        "title": "A payroll file that will not import",
        "steps": [
            "Open Hours > Payroll and download the file you sent.",
            "Check every line has a payroll reference; a blank one is refused at the far end.",
            "Check the pay period dates match the period your payroll is expecting.",
            "Rebuild the file and send it again once the records are right.",
        ],
        "note": "Providers differ on the column order and on how they want dates. The layout is "
        "set per connection under Settings > Connections, and changing it there rebuilds the file "
        "in the shape they want.",
    },
    {
        "section": "integrations",
        "title": "Matching staff records between two systems",
        "steps": [
            "Open Settings > Connections and press Matching.",
            "Names that agree on both sides are matched for you and shown with a tick.",
            "Pick the right record by hand for anybody else, or mark them as not in payroll.",
        ],
        "note": "Matching is by payroll reference first and by name second, so putting the "
        "reference on the staff record does most of the work before you open the screen at all.",
    },
    {
        "section": "integrations",
        "title": "Somebody who exists twice across the two systems",
        "steps": [
            "Open the matching screen and find the two lines.",
            "Match ours to the one payroll is actually paying.",
            "Mark the other as not in payroll so it stops appearing every time.",
        ],
        "note": "The screen will not guess between two records with the same name, and it stops "
        "rather than choosing, which is why a married name and a maiden name can hold up a whole "
        "week's transfer.",
    },
    {
        "section": "integrations",
        "title": "Bringing takings in from the till",
        "steps": [
            "Open Settings > Connections and connect your till system.",
            "Choose which venue each till maps to.",
            "Takings arrive each night and show on the wage cost bar the next morning.",
        ],
        "note": "A new till terminal is a new device to the till system, so it has to be mapped "
        "before its takings come through. Everything else keeps working while it is not.",
    },
    {
        "section": "integrations",
        "title": "Reconnecting something that stopped",
        "steps": [
            "Open Settings > Connections; anything that has stopped says so in amber.",
            "Press Reconnect and sign in to the provider again.",
            "Press Test, then look at the transfer log to see it go through.",
        ],
        "note": "Connections are signed in as a person, so one set up by somebody who has left "
        "stops when their account at the provider does. Reconnecting as yourself is the fix.",
    },
    {
        "section": "integrations",
        "title": "The nightly transfer and when it runs",
        "steps": [
            "It runs at two in the morning UK time, every night.",
            "It sends anything approved since the last run.",
            "The transfer log lists each run with the rows sent and anything refused.",
        ],
        "note": "Nothing that has not been approved is ever sent, so a week left unapproved on a "
        "Friday sits there all weekend and goes on the Monday night instead.",
    },
    {
        "section": "integrations",
        "title": "Reading a transfer error",
        "steps": [
            "Open Settings > Connections and then the transfer log.",
            "Click the red line; the error is written out in full underneath.",
            "Fix what it names, then press Send again against that run.",
        ],
        "note": "Most errors are one of three things: a locked period, a member of staff who is "
        "not matched, or a pay period the provider has already closed. The log says which.",
    },
    {
        "section": "integrations",
        "title": "Changing an API key",
        "steps": [
            "Open Settings > API and press New key.",
            "Copy it before you close the window; it is not shown again.",
            "Put the new key into whatever uses it, then press Revoke on the old one.",
        ],
        "note": "A revoked key carries on working for twenty-four hours, which is there so a "
        "nightly job does not fail overnight while you are asleep.",
    },
]

ARTICLES += [
    {
        "section": "mobile app",
        "title": "Getting the app on a phone",
        "steps": [
            "Look for Hollins Rota in the App Store or on Google Play.",
            "Install it, then open it and put in the email address your manager has on file.",
            "Allow notifications when it asks, so you hear about your rota.",
        ],
        "note": "It needs iOS 16 or Android 10. Anything older can still use the website on the "
        "phone, which does everything except clocking in.",
    },
    {
        "section": "mobile app",
        "title": "Signing in to the app",
        "steps": [
            "Enter the email address on your staff record, not a personal one you have not told us about.",
            "Enter the password you set when you accepted your invitation.",
            "Tap Forgotten password if you have never set one.",
        ],
        "note": "The app and the website share one password, so changing it on one changes it on "
        "the other.",
    },
    {
        "section": "mobile app",
        "title": "Signing in on a new phone",
        "steps": [
            "Install the app on the new phone and sign in as usual.",
            "Allow notifications again; the new phone asks on its own.",
            "Sign out on the old phone, or ask your manager to take it off your account.",
        ],
        "note": "You can be signed in on more than one phone at once. Signing out on one leaves "
        "the others signed in, which is why an old phone in a drawer keeps buzzing.",
    },
    {
        "section": "mobile app",
        "title": "Turning notifications on",
        "steps": [
            "Open the app, tap You, then Notifications.",
            "Turn on the ones you want: new rota, changes to your shifts, and shift reminders.",
            "Check your phone's own settings allow the app to notify you at all.",
        ],
        "note": "Both have to be on. Turning them on in the app does nothing if the phone is still "
        "blocking them, and the app cannot tell that the phone is.",
    },
    {
        "section": "mobile app",
        "title": "Notifications that do not arrive",
        "steps": [
            "Check the app's own settings under You > Notifications first.",
            "Then check the phone's settings for the app.",
            "Turn off any battery saving mode the phone is applying to the app.",
        ],
        "note": "Battery saving is the usual answer on Android, and it is set per app rather than "
        "for the phone, so one person on the team can be affected while nobody else is.",
    },
    {
        "section": "mobile app",
        "title": "Seeing your shifts for the week",
        "steps": [
            "Open the app; your own week is the first screen.",
            "Swipe left and right to move between weeks.",
            "Tap a shift to see its times, its break, its role and any note on it.",
        ],
        "note": "Weeks your manager has not published yet are not there at all, rather than being "
        "shown as empty, which is why next week can look blank on a Wednesday.",
    },
    {
        "section": "mobile app",
        "title": "Asking for time off from the app",
        "steps": [
            "Tap You, then Time off, then Request.",
            "Pick the first and last day, and choose full or half days.",
            "Add a line about why if it helps, and send it.",
        ],
        "note": "The screen shows what you have left before you send, but the figure does not come "
        "down until a manager approves it, so two requests in the same day can both look affordable.",
    },
    {
        "section": "mobile app",
        "title": "Swapping a shift from the app",
        "steps": [
            "Tap the shift you want to give away and tap Offer to swap.",
            "Everybody free who does your role sees it and can accept.",
            "Once somebody accepts, it waits for a manager to approve it.",
        ],
        "note": "The shift is still yours until a manager approves the swap, so turn up for it if "
        "the approval has not come through by the time it starts.",
    },
    {
        "section": "mobile app",
        "title": "Clocking in from the app",
        "steps": [
            "Open the app when you get to work and tap Clock in on today's shift.",
            "Tap Clock out at the end, and tap Break if your venue asks you to record them.",
            "The shift shows the running time while you are on.",
        ],
        "note": "Clocking in more than half an hour before the shift starts is refused, and the "
        "app says how long there is to go rather than just failing.",
    },
    {
        "section": "mobile app",
        "title": "Location and clocking in",
        "steps": [
            "Allow location when the app asks, if your venue has this turned on.",
            "The app checks you are at the venue and clocks you in.",
            "If it cannot find you, use the tablet on the bar instead.",
        ],
        "note": "Location is only asked for where the venue has turned it on, and a cellar or a "
        "back kitchen can be enough to defeat it, which is why every venue using it keeps a tablet.",
    },
    {
        "section": "mobile app",
        "title": "The app asking you to sign in again",
        "steps": [
            "Sign in again as normal; nothing has been lost.",
            "If it keeps happening, check whether your email address was changed recently.",
            "Update the app, then sign out and in once on that phone.",
        ],
        "note": "A change to the email address on your staff record signs you out everywhere, so a "
        "correction made by a manager on Monday is felt by the phone on Tuesday morning.",
    },
    {
        "section": "mobile app",
        "title": "Using the app with no signal",
        "steps": [
            "Your own shifts are kept on the phone and can be read with no signal at all.",
            "Clock-ins made offline are held and sent when the signal comes back.",
            "Swaps and time off requests need a signal and will say so.",
        ],
        "note": "An offline clock-in keeps the time you tapped it, not the time it reached us, so "
        "the hours are right even though the line appears in the list late.",
    },
    {
        "section": "mobile app",
        "title": "The app on an older phone",
        "steps": [
            "Check the phone is on iOS 16 or Android 10 or newer.",
            "If it is not, open the website in the phone's browser and sign in there.",
            "Ask your manager about the venue tablet for clocking in.",
        ],
        "note": "The website does everything the app does apart from clocking in and push "
        "notifications, so somebody on an older phone still sees their rota the moment it is out.",
    },
]

ARTICLES += [
    {
        "section": "rotas",
        "title": "Putting a trial shift on the rota",
        "steps": [
            "Add the person to Staff first, with the job they are trying out for.",
            "Tick Trial on their record so they are left out of the bill until you keep them on.",
            "Rota the shift as normal and put a note on it saying who is showing them round.",
        ],
        "note": "A trial shift still counts towards the hours for the week and still needs a break "
        "on it if it runs long enough, so build it the way you would build any other shift.",
    },
    {
        "section": "time off",
        "title": "Time off for somebody who works at two venues",
        "steps": [
            "Book it once, from either venue; it blocks both.",
            "The days come off one allowance, because the allowance belongs to the person.",
            "Both sets of managers see the booking on their own rota.",
        ],
        "note": "The request itself goes only to the managers of their main venue, so the other "
        "site finds out when the booking lands on the rota rather than being asked first.",
    },
    {
        "section": "pay and hours",
        "title": "Correcting last week's hours after payroll has run",
        "steps": [
            "Check whether the period is locked; if it is, the correction belongs on the next one.",
            "Add an adjustment line against the person with the hours and a reason.",
            "It appears on the next payroll file as its own line rather than changing the old one.",
        ],
        "note": "Tell whoever runs your payroll what the adjustment is for. The line carries your "
        "reason, but a note in advance saves them ringing you about it.",
    },
]

# --------------------------------------------------------------- what comes in, and what goes back
#
# One record per kind of ticket the desk sees. `articles` is what the desk would reach for, and
# `replies` is what it says when it writes one out by hand instead.

TOPICS = [
    {
        "section": "rotas",
        "subjects": [
            "Rota will not publish",
            "Publish does nothing",
            "rota stuck on draft",
            "Cannot publish next week",
            "Staff cannot see next week",
            "publishing not working",
        ],
        "kind": "broken",
        "problems": [
            "I have built next week's rota and when I press publish nothing happens. The staff say "
            "they still cannot see it on their phones.",
            "The publish button spins and then goes back to how it was. Nobody has had the email.",
        ],
        "extras": [
            "I have tried it in Chrome and in Edge and it does the same in both.",
            "Last week published fine on the Tuesday so I do not think I am doing it differently.",
        ],
        "searches": [
            "publish rota",
            "publish changes",
            "draft",
            "publish summary",
            "rota email",
            "publish",
        ],
        "articles": [
            "publishing-a-rota-so-staff-can-see-it",
            "building-next-weeks-rota",
            "who-is-told-when-a-rota-changes",
        ],
        "replies": [
            "Hi {first}, I have had a look and the week was stuck with two shifts that had no role "
            "on them, which is what the publish was waiting on. I have put a role on both and "
            "published it from this end, so your team have it now. {desk}",
            "Hello {first}, that was ours and I am sorry about it. Publishing was timing out for "
            "venues with more than thirty on the rota for about an hour this morning. It is fixed "
            "and your week has gone out. Nothing needed doing at your end. {desk}",
        ],
    },
    {
        "section": "rotas",
        "subjects": [
            "Saturday shifts have gone",
            "rota missing half a day",
            "shifts disappeared??",
            "Half of Saturday has vanished",
            "Shifts deleted by mistake",
            "Who changed the rota",
        ],
        "kind": "broken",
        "problems": [
            "Half of Saturday has vanished off the rota. There were six people on and now there "
            "are two.",
            "Some of the shifts I put in on Saturday are no longer there and I have no idea where "
            "they went.",
        ],
        "extras": [
            "My assistant manager was editing at the same time so it may be that.",
            "Is there any way of seeing what it looked like before?",
        ],
        "searches": [
            "rota history",
            "restore",
            "deleted shift",
            "undo",
            "lock rota",
            "shifts gone",
        ],
        "articles": [
            "rota-history-and-who-changed-what",
            "getting-back-a-shift-you-deleted",
            "locking-a-rota-so-nobody-else-edits-it",
        ],
        "replies": [
            "Hi {first}, the history has it: your assistant manager applied a template over the "
            "week at twenty past four, which cleared what was there first. I have restored the "
            "rota to twenty past three and Saturday is back as you had it. {desk}",
            "Hello {first}, four shifts were deleted on Friday evening from the same sign-in as "
            "yours. I have put all four back and left the rest of the week alone. Worth locking "
            "the week once it is right, so nobody can move it after you. {desk}",
        ],
    },
    {
        "section": "rotas",
        "subjects": [
            "Copying a week between venues",
            "Can I reuse a week at both sites",
            "template for two venues",
            "Same rota at both venues",
            "Copying the rota across",
        ],
        "kind": "how-to",
        "problems": [
            "We run two sites and the rota is nearly the same at both. Can I copy a week from one "
            "to the other rather than typing it twice?",
            "Is there a way of building one week and using it at both venues?",
        ],
        "extras": [
            "The staff are different at each but the shape of the week is identical.",
            "It is about twenty minutes a week I would rather not spend.",
        ],
        "searches": [
            "copy week",
            "template",
            "templates",
            "more than one venue",
            "venue picker",
        ],
        "articles": [
            "saving-a-week-as-a-template",
            "running-rotas-for-more-than-one-venue",
            "copying-last-weeks-rota-forward",
        ],
        "replies": [
            "Hi {first}, copy week works within a venue rather than across two, but a template "
            "saved as the shape only does exactly what you want. Save one off your main site and "
            "apply it at the other, then drop the names on. {desk}",
            "Hello {first}, I have saved a template for you off last week at the first site and "
            "made it available at both, so it is there the next time you open Templates. Drop the "
            "names on afterwards and it should be five minutes rather than twenty. {desk}",
        ],
    },
    {
        "section": "rotas",
        "subjects": [
            "Rota emails going out late at night",
            "emails at 11pm",
            "Can we hold the notifications",
            "Staff getting emails at night",
            "Notifications going out too late",
        ],
        "kind": "how-to",
        "problems": [
            "The team are getting rota emails at eleven at night and one of them has complained.",
            "Can we stop the system emailing staff after about nine? It went out at half past "
            "eleven on Sunday.",
        ],
        "extras": [
            "I do the rota after service so it is my fault for publishing then, but still.",
            "Ideally it would hold them until the morning.",
        ],
        "searches": [
            "rota emails",
            "hold notifications",
            "notifications",
            "night",
            "email staff",
        ],
        "articles": [
            "stopping-rota-emails-going-out-at-night",
            "who-is-told-when-a-rota-changes",
        ],
        "replies": [
            "Hi {first}, I have set the hold on your venue to eight in the morning. Publish when "
            "you like after service and nothing will leave until then. Anybody who opens the app "
            "before eight will still see the week, because the rota itself goes live at once. {desk}",
            "Hello {first}, that is a setting rather than something you are doing wrong. It is on "
            "for you now at seven thirty, which is what most of our late-finishing venues use. "
            "Shout if you want it later. {desk}",
        ],
    },
    {
        "section": "rotas",
        "subjects": [
            "Somebody on twice",
            "double booked a member of staff",
            "No clash warning",
            "On two shifts at once",
            "clash warning did not show",
            "Booked on twice",
        ],
        "kind": "broken",
        "problems": [
            "It let me put one of the girls on a bar shift and a kitchen shift at the same time "
            "and did not say anything.",
            "I have double booked somebody and only found out when she told me.",
        ],
        "extras": [
            "I thought there was meant to be a warning for that.",
            "She works at both of our sites which might be why.",
        ],
        "searches": [
            "clash",
            "warning",
            "on twice",
            "red corner",
            "two venues",
        ],
        "articles": [
            "the-warning-when-somebody-is-on-twice",
            "giving-somebody-shifts-at-two-venues",
            "roles-on-a-shift-and-why-they-matter",
        ],
        "replies": [
            "Hi {first}, the warning was there but it is on the other venue's rota, not yours, "
            "because the second shift was at the second site. It is a red corner on that week. I "
            "have shortened the kitchen shift by two hours so the two no longer overlap. {desk}",
            "Hello {first}, this is the one case the warning is quiet about: both shifts had no "
            "role on them, and the clash check counts by role. I have put roles on everything this "
            "week, so it will speak up next time. {desk}",
        ],
    },
    {
        "section": "rotas",
        "subjects": [
            "Printing the rota",
            "rota will not fit on one page",
            "Printed rota cut off",
            "printing for the kitchen",
            "How do I print the week",
        ],
        "kind": "how-to",
        "problems": [
            "I want to put the rota up in the kitchen but when I print it the week runs across two "
            "pages and half of Sunday is cut off.",
            "How do I get a printed rota that fits on one sheet?",
        ],
        "extras": [
            "Landscape helps a bit but not enough with fourteen names on it.",
            "The chef likes it on the wall so this matters more than it should.",
        ],
        "searches": [
            "print rota",
            "print",
            "fit to one page",
            "landscape",
            "export",
        ],
        "articles": [
            "printing-a-rota-for-the-back-of-house",
            "sending-a-rota-to-a-spreadsheet",
        ],
        "replies": [
            "Hi {first}, tick Fit to one page in the print box and choose landscape, and fourteen "
            "names will go on a sheet. If the chef only wants the kitchen, filter the rota by role "
            "before you print and it comes out bigger still. {desk}",
            "Hello {first}, the two page break is the browser rather than us. Print from the Print "
            "button on the rota rather than the browser's own print, and tick Fit to one page. I "
            "have just done it here with fourteen names and it sat on one sheet. {desk}",
        ],
    },
    {
        "section": "time off",
        "subjects": [
            "Holiday allowance looks wrong",
            "allowance does not match",
            "Days left are wrong",
            "holiday figures",
            "Allowance out by three days",
            "Her allowance is wrong",
        ],
        "kind": "broken",
        "problems": [
            "One of my supervisors says she has twelve days left and I make it nine. I cannot see "
            "where the difference is coming from.",
            "The allowance on the staff record does not match what I have written down.",
        ],
        "extras": [
            "She started partway through the year so it should be pro rata.",
            "We moved the holiday year over not long ago, which might be it.",
        ],
        "searches": [
            "holiday allowance",
            "allowance",
            "pro rata",
            "days left",
            "adjustment",
        ],
        "articles": [
            "the-holiday-allowance-for-a-venue",
            "pro-rata-allowance-for-part-time-staff",
            "the-allowance-a-member-of-staff-sees-left",
            "correcting-an-allowance-halfway-through-the-year",
        ],
        "replies": [
            "Hi {first}, the three days are the ones she has already booked for later in the "
            "year. Her figure counts the whole year including what is booked ahead, and yours "
            "was counting what she has taken so far. Both are right, they answer different "
            "questions. {desk}",
            "Hello {first}, it is the year change. When you moved the holiday year everybody got "
            "a short year worked out pro rata, and hers came out at nine and a half rounded "
            "down. I have put an adjustment of two and a half days on her record so she is not "
            "out of pocket. {desk}",
            "Hi {first}, she started partway through the holiday year, so her first year is pro "
            "rata from her start date, and that is where the difference is. I have put the "
            "working out on her record as a note so you can show it to her. {desk}",
        ],
    },
    {
        "section": "time off",
        "subjects": [
            "Cannot approve a request",
            "approve button does nothing",
            "Holiday request stuck",
            "approving time off",
            "Time off request will not approve",
        ],
        "kind": "broken",
        "problems": [
            "There is a holiday request sat in my list and the approve button does nothing when I "
            "press it.",
            "I cannot approve time off for one of the kitchen porters. Nothing happens at all.",
        ],
        "extras": [
            "I can approve everybody else's, it is just his.",
            "He works at both venues if that makes a difference.",
        ],
        "searches": [
            "approve",
            "approve holiday",
            "requests",
            "time off requests",
            "permission",
        ],
        "articles": [
            "approving-a-holiday-request",
            "who-a-holiday-request-goes-to",
            "keeping-a-manager-to-one-venue",
        ],
        "replies": [
            "Hi {first}, his main venue is the second site, so the request belongs to the managers "
            "there and your button is showing but not yours to press. I have added you as a manager "
            "at both venues, which is what you want anyway. {desk}",
            "Hello {first}, the request ran across dates you have blocked for the first week of "
            "December, and the approve was refusing quietly rather than saying so. That is ours and "
            "it is on the list to fix. I have approved it from this end. {desk}",
        ],
    },
    {
        "section": "time off",
        "subjects": [
            "Carrying days into next year",
            "carry over holiday",
            "Holiday year ending",
            "unused days",
            "Can they carry days over",
        ],
        "kind": "how-to",
        "problems": [
            "Two of the team have not taken their holiday and the year ends this month. Can they "
            "carry it over?",
            "How do I let somebody carry five days into next year?",
        ],
        "extras": [
            "We have always allowed up to five days.",
            "I do not want it to just disappear on the first.",
        ],
        "searches": [
            "carry",
            "carried",
            "holiday year",
            "carry limit",
            "allowance",
        ],
        "articles": [
            "carrying-holiday-into-next-year",
            "setting-your-holiday-year",
            "correcting-an-allowance-halfway-through-the-year",
        ],
        "replies": [
            "Hi {first}, I have set your carry limit to five days, so anything left up to that "
            "moves across on the first on its own. Nothing will be lost. If you want a date by "
            "which the carried days have to be used, say so and I will put that on too. {desk}",
            "Hello {first}, the carry runs overnight on the first day of the new year, so setting "
            "it before then is all you need to do. It is on for you now at five days. {desk}",
        ],
    },
    {
        "section": "time off",
        "subjects": [
            "Bank holiday counted as a day",
            "bank holiday came off the allowance",
            "bank holiday booking",
            "Bank holidays and allowance",
            "Day taken off for a bank holiday",
        ],
        "kind": "broken",
        "problems": [
            "Somebody booked the bank holiday Monday off and it has taken a whole day off her "
            "allowance. She does not normally work Mondays.",
            "The last bank holiday has come off two people's allowance and I do not think it "
            "should have.",
        ],
        "extras": [
            "We close on bank holidays anyway.",
            "Can I put the day back on without deleting the booking?",
        ],
        "searches": [
            "bank holiday",
            "observed",
            "allowance",
            "bank holidays",
            "venue settings",
        ],
        "articles": [
            "time-off-that-lands-on-a-bank-holiday",
            "bank-holidays-on-the-rota",
            "correcting-an-allowance-halfway-through-the-year",
        ],
        "replies": [
            "Hi {first}, the day was not marked as observed in your venue settings, so it counted "
            "as an ordinary Monday. I have marked all eight for this year and put the day back on "
            "both allowances. Bookings you make from now on will skip them. {desk}",
            "Hello {first}, you can leave the booking alone; I have put the day back with an "
            "adjustment rather than cancelling anything. The setting is fixed as well, so it will "
            "not happen at Christmas. {desk}",
        ],
    },
    {
        "section": "time off",
        "subjects": [
            "Requests going to the wrong person",
            "holiday requests coming to me",
            "wrong manager getting requests",
            "Requests for a venue I do not run",
            "Who gets the requests",
        ],
        "kind": "broken",
        "problems": [
            "Holiday requests from the cafe staff are coming to me and they should be going to the "
            "cafe manager.",
            "I am getting requests for a venue I do not run.",
        ],
        "extras": [
            "It started when we added the second site in {last_month}.",
            "She cannot see them at all at the moment which is the bigger problem.",
        ],
        "searches": [
            "requests",
            "main venue",
            "managers",
            "permissions",
            "holiday request",
        ],
        "articles": [
            "who-a-holiday-request-goes-to",
            "keeping-a-manager-to-one-venue",
            "making-somebody-a-manager",
        ],
        "replies": [
            "Hi {first}, the cafe staff still have the original venue as their main one on their "
            "records, which is why the requests are landing with you. I have moved all eleven of "
            "them across to the cafe, so anything new goes to her. {desk}",
            "Hello {first}, she was set up as a manager but with no venue ticked, so she could see "
            "nothing. I have ticked the cafe on her permissions and the four requests waiting are "
            "in her list now. {desk}",
        ],
    },
    {
        "section": "time off",
        "subjects": [
            "Cancelling approved holiday",
            "take a booking back off",
            "cancel a week off",
            "How do I cancel time off",
            "Cancelling a booking",
        ],
        "kind": "how-to",
        "problems": [
            "One of the bar team has asked to cancel the week he booked for {next_month}. How do "
            "I take it back off?",
            "I approved a week's holiday and he now wants to work it instead.",
        ],
        "extras": [
            "I want the days back on his allowance if that is possible.",
            "The rota for that week is already published.",
        ],
        "searches": [
            "cancel",
            "cancel booking",
            "approved time off",
            "booking",
            "allowance back",
        ],
        "articles": [
            "cancelling-time-off-that-was-already-approved",
            "approving-a-holiday-request",
            "booking-time-off-for-a-member-of-staff",
        ],
        "replies": [
            "Hi {first}, open the booking on his record and press Cancel, leaving the days going "
            "back on ticked. The block comes off the rota straight away, but it will not put his "
            "old shifts back, so that week needs building again for him. {desk}",
            "Hello {first}, done from this end: five days back on his allowance and the week "
            "unblocked. The rota for that week is still published without him on it, so you will "
            "want to add his shifts and publish the change. {desk}",
        ],
    },
]

TOPICS += [
    {
        "section": "pay and hours",
        "subjects": [
            "Hours do not match the rota",
            "worked and rota'd are six apart",
            "hours difference",
            "Which hours go to payroll",
            "Hours report does not add up",
            "hours out by six",
        ],
        "kind": "broken",
        "problems": [
            "The hours report says one hundred and ninety two and I have added the rota up at one "
            "hundred and eighty six. Which one goes to payroll?",
            "Worked hours and rota'd hours are six apart this week and I cannot see why.",
        ],
        "extras": [
            "Nobody has told me they stayed late.",
            "It has been right every other week since we started.",
        ],
        "searches": [
            "worked hours",
            "hours",
            "difference",
            "rounding",
            "payslip",
        ],
        "articles": [
            "hours-worked-against-hours-rotad",
            "where-the-hours-on-a-payslip-come-from",
            "approving-the-weeks-hours",
            "rounding-clock-in-times",
        ],
        "replies": [
            "Hi {first}, the worked column is what goes to payroll. The six hours are three people "
            "clocking out between twenty and forty minutes after their shift on the Saturday. The "
            "clock-ins are on the lines if you want to look before you approve it. {desk}",
            "Hello {first}, this week has two open cover shifts on the Friday that nobody was ever "
            "put on. They count in the rota'd column with nobody on them, which is your six hours. "
            "Take them off and the two columns agree. {desk}",
        ],
    },
    {
        "section": "pay and hours",
        "subjects": [
            "Missed clock out",
            "shift still running",
            "forgot to clock out",
            "Open shift on the hours page",
            "Chef did not clock out",
        ],
        "kind": "how-to",
        "problems": [
            "One of the chefs forgot to clock out on Friday and his shift is still showing as "
            "running. It says forty one hours.",
            "Somebody has left a shift open since Saturday night and it is throwing the week out.",
        ],
        "extras": [
            "Can I just type the right time in?",
            "I have already approved the week which may have been a mistake.",
        ],
        "searches": [
            "clock out",
            "open shift",
            "missed clock",
            "reopen",
            "correct",
        ],
        "articles": [
            "missed-clock-outs-and-how-to-put-them-right",
            "editing-hours-you-have-already-approved",
            "approving-the-weeks-hours",
        ],
        "replies": [
            "Hi {first}, yes, type it in. Click the amber line on the hours page, put in the time "
            "he actually finished and give a reason. Until you do, those hours are out of the week "
            "altogether rather than counting as forty one. {desk}",
            "Hello {first}, approving it is not a problem, you just have to reopen the week first. "
            "Press Reopen at the top, fix the Saturday, then approve it again. The period is not "
            "locked so there is nothing stopping you. {desk}",
        ],
    },
    {
        "section": "pay and hours",
        "subjects": [
            "Payroll file will not go in",
            "payroll cannot read the file",
            "import failing",
            "File refused by payroll",
            "Payroll import problem",
        ],
        "kind": "broken",
        "problems": [
            "Our payroll people say the file will not import. They said something about the date "
            "column.",
            "The export comes out but payroll cannot read it and I am running out of time before "
            "the cut off.",
        ],
        "extras": [
            "It worked last month with the same people.",
            "I can send you the file if that helps.",
        ],
        "searches": [
            "payroll file",
            "import",
            "payroll reference",
            "columns",
            "build file",
        ],
        "articles": [
            "a-payroll-file-that-will-not-import",
            "the-payroll-file-and-what-is-in-each-column",
            "sending-hours-to-payroll",
        ],
        "replies": [
            "Hi {first}, two of your new starters have no payroll reference on their staff records, "
            "and a blank reference is what their end refuses on. Put the two references in and "
            "rebuild the file and it will go. {desk}",
            "Hello {first}, your provider changed how they want dates at the start of the month. I "
            "have switched the date layout on your connection to the one they are now asking for "
            "and rebuilt the file, which is attached. You should make the cut off. {desk}",
        ],
    },
    {
        "section": "pay and hours",
        "subjects": [
            "Breaks not coming off",
            "break time still being paid",
            "unpaid breaks",
            "Half hour break in the total",
            "Breaks and hours",
        ],
        "kind": "broken",
        "problems": [
            "Everybody's half hour break is still in their total. I thought unpaid breaks came off "
            "automatically.",
            "The break time is being paid and it should not be.",
        ],
        "extras": [
            "It is a thirty minute break on anything over six hours.",
            "It was right at the other venue so it must be a setting.",
        ],
        "searches": [
            "unpaid breaks",
            "break",
            "breaks",
            "paid break",
            "venue setting",
        ],
        "articles": [
            "unpaid-breaks-and-how-they-come-off-the-total",
            "putting-a-break-on-a-shift",
            "approving-the-weeks-hours",
        ],
        "replies": [
            "Hi {first}, you are right, it is a setting, and this venue has breaks as paid while "
            "the other has them unpaid. I have changed it. It will not go back and change weeks "
            "you have already published, so this week is the first one it affects. {desk}",
            "Hello {first}, the setting was right but the shifts themselves had no break on them, "
            "so there was nothing to take off. I have put thirty minutes on everything over six "
            "hours this week; from next week it is worth adding them as you build. {desk}",
        ],
    },
    {
        "section": "pay and hours",
        "subjects": [
            "Overtime not counted",
            "overtime showing as zero",
            "no overtime this week",
            "No overtime showing at all",
            "Overtime missing",
        ],
        "kind": "broken",
        "problems": [
            "One of the team did fifty one hours and none of it has come out as overtime.",
            "Overtime is showing as zero for everybody this week which cannot be right.",
        ],
        "extras": [
            "Their contract says forty.",
            "We pay time and a quarter over that.",
        ],
        "searches": [
            "overtime",
            "contracted hours",
            "contract",
            "overtime rate",
            "threshold",
        ],
        "articles": [
            "overtime-and-how-it-is-counted",
            "contracted-hours-and-how-to-set-them",
            "the-warning-when-a-shift-goes-over-contracted-hours",
        ],
        "replies": [
            "Hi {first}, his staff record has no contracted hours on it, so there is no figure for "
            "the overtime to start above. I have put forty on his record and the eleven hours have "
            "come through. Worth checking the rest of the team while you are in there. {desk}",
            "Hello {first}, nobody at your venue has contracted hours set, which is why it is nought "
            "across the board. I have put the standard forty on everybody full time and left the "
            "part timers for you, since those will all be different. {desk}",
        ],
    },
    {
        "section": "pay and hours",
        "subjects": [
            "Rate changed halfway through the week",
            "rise from the Wednesday",
            "hourly rate date",
            "Rate applied to the whole week",
            "Changing a rate from a date",
        ],
        "kind": "how-to",
        "problems": [
            "I gave somebody a rise from the Wednesday and the whole week has gone through at the "
            "new rate.",
            "How do I change a rate from a particular day rather than from now?",
        ],
        "extras": [
            "It is only about eleven pounds but I would rather it were right.",
            "Payroll has not run yet so I can still fix it.",
        ],
        "searches": [
            "hourly rate",
            "rate",
            "applies from",
            "rates",
            "two rates",
        ],
        "articles": [
            "setting-hourly-rates",
            "different-rates-at-different-venues",
            "editing-hours-you-have-already-approved",
        ],
        "replies": [
            "Hi {first}, there is an applies from date next to the rate box, and leaving it as "
            "today is what caught you. I have set his rise to start on the Wednesday, so the week "
            "now shows two lines, two days at the old rate and three at the new. {desk}",
            "Hello {first}, fixed, and the eleven pounds with it. The week will go through as two "
            "lines for him on the payroll file, which is what your payroll expects when a rate "
            "changes midweek. {desk}",
        ],
    },
    {
        "section": "staff accounts",
        "subjects": [
            "Invitation never arrived",
            "new starter has had nothing",
            "invite not received",
            "Invitation email missing",
            "Invites and nothing back",
        ],
        "kind": "broken",
        "problems": [
            "I have invited a new starter three times and she says nothing has come through.",
            "Two new people have not had their invitation emails and they start Monday.",
        ],
        "extras": [
            "She has checked spam.",
            "It is a hotmail address if that means anything.",
        ],
        "searches": [
            "invitation",
            "invite",
            "sign-in code",
            "spam",
            "email address",
        ],
        "articles": [
            "an-invitation-that-never-arrived",
            "sending-an-invitation-again",
            "inviting-somebody-with-no-email-address",
        ],
        "replies": [
            "Hi {first}, all three bounced: the address on her record has a full stop where an "
            "at sign should be. I have not changed it in case I guess wrong, so correct it on her "
            "record and send it once more and it will land. {desk}",
            "Hello {first}, rather than fight their mail filter before Monday, use a sign-in code. "
            "Clear the email on each record, press Get sign-in code and give them the six "
            "characters. They can put an address on themselves later. {desk}",
        ],
    },
    {
        "section": "staff accounts",
        "subjects": [
            "New starter cannot set a password",
            "link no longer valid",
            "password setup",
            "Invitation link expired",
            "Cannot set his password",
        ],
        "kind": "broken",
        "problems": [
            "Our new bartender clicks the link in his email and it says the link is no longer "
            "valid.",
            "The password page says the invitation has expired but I only sent it last week.",
        ],
        "extras": [
            "I sent it on the day he accepted the job which was a while back now.",
            "He is on shift tonight so it would be good to sort it today.",
        ],
        "searches": [
            "invitation",
            "password",
            "reset",
            "link",
            "invite again",
        ],
        "articles": [
            "sending-an-invitation-again",
            "resetting-a-password-somebody-has-forgotten",
            "inviting-a-member-of-staff-by-email",
        ],
        "replies": [
            "Hi {first}, an invitation is good for fourteen days and his went out five weeks ago, "
            "which is all that is wrong. I have sent him a fresh one just now; it will be in his "
            "inbox and he can set a password before tonight. {desk}",
            "Hello {first}, that message means the link has run out rather than anything being "
            "wrong with his account. Press Invite on his record again and the new link replaces the "
            "old one. I have done it this time so he is not stuck. {desk}",
        ],
    },
    {
        "section": "staff accounts",
        "subjects": [
            "Manager can see the other site",
            "bar manager seeing cafe costs",
            "manager permissions",
            "Limiting a manager to one venue",
            "Permissions look wrong",
        ],
        "kind": "broken",
        "problems": [
            "My bar manager can see the wage costs for the cafe and she should only see the bar.",
            "One of the managers has access to a venue she does not run.",
        ],
        "extras": [
            "She has not done anything with it, I just noticed.",
            "Can I limit her to one venue?",
        ],
        "searches": [
            "permission",
            "manager",
            "wage costs",
            "venues",
            "managers",
        ],
        "articles": [
            "keeping-a-manager-to-one-venue",
            "what-managers-can-see",
            "making-somebody-a-manager",
        ],
        "replies": [
            "Hi {first}, both venues were ticked on her permissions, which happens when somebody is "
            "made a manager before the second site is added. I have unticked the cafe and she will see "
            "the bar only from her next sign-in. {desk}",
            "Hello {first}, yes, open her record, then Permission, and untick the cafe. I have done "
            "it for you. She will still see cafe staff who also work at the bar, because she has to "
            "be able to rota them, but not their cafe shifts or any of the costs. {desk}",
        ],
    },
    {
        "section": "staff accounts",
        "subjects": [
            "Leaver still on the rota",
            "she left and is still in the list",
            "leavers",
            "Still being billed for a leaver",
            "Marking somebody as a leaver",
        ],
        "kind": "broken",
        "problems": [
            "Somebody who left in {last_month} is still coming up when I build the rota.",
            "I marked a member of staff as a leaver and she is still in the staff list.",
        ],
        "extras": [
            "I do not want to delete her in case we need the records.",
            "She is also still on the bill by the look of it.",
        ],
        "searches": [
            "leaver",
            "leavers",
            "last day",
            "active",
            "staff list",
        ],
        "articles": [
            "marking-somebody-as-a-leaver",
            "what-counts-as-an-active-member-of-staff",
            "a-leaver-who-comes-back",
        ],
        "replies": [
            "Hi {first}, her record was saved with the leaver box ticked but no last day, so "
            "nothing took effect. I have put her last day on it. She is off the rota from the "
            "day after and off next month's bill. {desk}",
            "Hello {first}, she is marked correctly, but the staff list shows leavers unless you "
            "turn the filter off, which is the bit that looks wrong. Set the filter to Active and "
            "she goes. Her record stays for your records either way. {desk}",
        ],
    },
    {
        "section": "staff accounts",
        "subjects": [
            "Changing somebody's email",
            "update an email address",
            "email on a staff record",
            "New email for one of the team",
            "Where do I change an email",
        ],
        "kind": "how-to",
        "problems": [
            "One of the team has changed her email address. Where do I update it?",
            "I need to change the email on a staff record and I cannot find the field.",
        ],
        "extras": [
            "She cannot get into the old one at all any more.",
            "Will it sign her out of the app?",
        ],
        "searches": [
            "email address",
            "contact",
            "change email",
            "staff record",
            "sign in",
        ],
        "articles": [
            "changing-the-email-on-an-account",
            "resetting-a-password-somebody-has-forgotten",
            "signing-in-to-the-app",
        ],
        "replies": [
            "Hi {first}, it is on her staff record under Contact; you have to press Edit at the top "
            "before the field will take a change, which is the bit everybody misses. It will sign "
            "her out on her phone, so warn her before you do it mid-shift. {desk}",
            "Hello {first}, I have changed it for you. She will be asked to sign in again on her "
            "phone with the new address and her existing password. Nothing else on her record has "
            "moved. {desk}",
        ],
    },
    {
        "section": "staff accounts",
        "subjects": [
            "Right to work document running out",
            "visa expiring",
            "document expiry",
            "What happens when a document expires",
            "Reminder about a document",
        ],
        "kind": "how-to",
        "problems": [
            "I have had a reminder that somebody's document expires next month. What happens if I "
            "do nothing?",
            "A visa on one of the staff records runs out in three weeks and I want to know what "
            "the system does.",
        ],
        "extras": [
            "He has applied for the new one already.",
            "I do not want him coming off the rota automatically.",
        ],
        "searches": [
            "right to work",
            "documents",
            "expiry",
            "expires",
            "reminders",
        ],
        "articles": [
            "documents-that-are-about-to-run-out",
            "right-to-work-documents",
        ],
        "replies": [
            "Hi {first}, nothing happens on the date. Nobody comes off the rota and no shift is "
            "refused; the record shows the expiry in red and you get the reminders. Upload the new "
            "document when it comes and the old one stays underneath as history. {desk}",
            "Hello {first}, we deliberately do not take anybody off the rota for this, because that "
            "is your decision rather than ours. You will get one more reminder at thirty days. {desk}",
        ],
    },
]

TOPICS += [
    {
        "section": "billing",
        "subjects": [
            "Card declined",
            "payment failed email",
            "our payment bounced",
            "Failed payment",
            "Card not working",
        ],
        "kind": "broken",
        "problems": [
            "I have had an email saying the payment failed. The card is fine as far as I know.",
            "Our monthly payment has bounced and I do not want to lose access.",
        ],
        "extras": [
            "The bank has probably stopped it, they do that with anything new.",
            "Can I pay it now rather than wait for it to try again?",
        ],
        "searches": [
            "failed payment",
            "card",
            "retry",
            "payment",
            "billing",
        ],
        "articles": [
            "a-card-payment-that-failed",
            "changing-the-card-on-the-account",
            "reading-the-charges-on-your-statement",
        ],
        "replies": [
            "Hi {first}, the reason back from the bank is expired card, so a new one is the fix "
            "rather than trying the same one again. Put it on under Settings > Billing and press "
            "Retry. Nothing stops working in the meantime. {desk}",
            "Hello {first}, yes, you can pay it now: open Settings > Billing and press Retry "
            "against the failed line. If the bank blocked it as a new payee it usually goes through "
            "on the second try once you have told them to expect it. {desk}",
        ],
    },
    {
        "section": "billing",
        "subjects": [
            "VAT invoice needed",
            "accountant wants VAT invoices",
            "invoices for year end",
            "VAT number on invoices",
            "Proper invoices please",
        ],
        "kind": "how-to",
        "problems": [
            "My accountant needs proper VAT invoices for the last six months.",
            "The receipts I have do not show a VAT number and I need them to.",
        ],
        "extras": [
            "Our VAT number is on the account already I think.",
            "Year end is the end of this month.",
        ],
        "searches": [
            "vat invoice",
            "vat number",
            "invoices",
            "download",
            "billing details",
        ],
        "articles": [
            "getting-a-vat-invoice",
            "where-to-find-your-invoices",
            "changing-the-billing-email",
        ],
        "replies": [
            "Hi {first}, your VAT number was not on the account, which is why they came out as "
            "receipts. I have added it from your details and rebuilt all six. They keep their "
            "original numbers and dates, so your accountant will be happy. {desk}",
            "Hello {first}, they are all there under Settings > Billing > Invoices, and once the "
            "company details are filled in you can rebuild the older ones from the same list. I "
            "have done the six for you and they are ready to download. {desk}",
        ],
    },
    {
        "section": "billing",
        "subjects": [
            "Charged for staff who have left",
            "bill counts too many people",
            "staff count on the bill",
            "Paying for leavers",
            "Headcount on the invoice",
        ],
        "kind": "broken",
        "problems": [
            "This month's bill counts thirty one people and we only have twenty six.",
            "We are paying for five people who left months ago.",
        ],
        "extras": [
            "I marked them all as leavers in {last_month}.",
            "Can that be put right on the next bill?",
        ],
        "searches": [
            "active member of staff",
            "staff count",
            "leavers",
            "bill",
            "counted",
        ],
        "articles": [
            "what-counts-as-an-active-member-of-staff",
            "marking-somebody-as-a-leaver",
            "reading-the-charges-on-your-statement",
        ],
        "replies": [
            "Hi {first}, the five were marked as leavers on the fourth, and the count is taken on "
            "the first, so they were on the books that morning. The next bill will be twenty six. "
            "I have credited the five for this month as it was days rather than weeks. {desk}",
            "Hello {first}, four of the five had no last day on their record, so the leaver tick "
            "had not taken effect. I have dated all four and they come off from next month. The "
            "fifth was already right. {desk}",
        ],
    },
    {
        "section": "billing",
        "subjects": [
            "Pausing while we are closed",
            "putting the account on hold",
            "closing for a few weeks",
            "Can we pause the account",
            "Account on hold",
        ],
        "kind": "how-to",
        "problems": [
            "We shut for six or seven weeks while it is quiet. Can we pause the account rather "
            "than pay for it?",
            "Is there a way of putting the account on hold while we are shut?",
        ],
        "extras": [
            "We would want the rotas still there when we come back.",
            "It is six weeks, maybe seven.",
        ],
        "searches": [
            "pause",
            "paused",
            "plan",
            "hold",
            "closing an account",
        ],
        "articles": [
            "pausing-an-account-over-the-winter",
            "closing-an-account",
            "moving-down-a-plan",
        ],
        "replies": [
            "Hi {first}, yes, and it is built for exactly your case. Settings > Plan, press Pause, "
            "give the date you are opening again. Nothing is charged while you are shut, the rotas "
            "and hours stay readable, and it starts itself on the date you gave. {desk}",
            "Hello {first}, I have set it to pause from the date you gave me and start again six "
            "weeks later. Move either date whenever you like. Your staff can still sign in and "
            "look at what is there while you are shut. {desk}",
        ],
    },
    {
        "section": "billing",
        "subjects": [
            "Moving up a plan partway through the month",
            "changing plan mid month",
            "upgrading the plan",
            "What does the venue plan cost",
            "Going on to the venue plan",
        ],
        "kind": "how-to",
        "problems": [
            "We want to go on to the venue plan now rather than wait until the first. What does "
            "that cost?",
            "If I change plan today am I paying for both this month?",
        ],
        "extras": [
            "We are opening the second site on the twelfth.",
            "Happy either way, I just want to know before I press it.",
        ],
        "searches": [
            "change plan",
            "plan",
            "venue plan",
            "part month",
            "what a plan costs",
        ],
        "articles": [
            "moving-from-starter-to-team",
            "adding-a-second-venue-to-the-bill",
            "what-a-plan-costs",
            "reading-the-charges-on-your-statement",
        ],
        "replies": [
            "Hi {first}, you pay the difference for the rest of the month rather than both. The "
            "page works it out and shows you the figure before you confirm, so you can look without "
            "committing. Adding the venue moves the plan up as part of the same step. {desk}",
            "Hello {first}, for your staff count it comes to a little under half a month's "
            "difference if you press it on the twelfth. Your statement will show two lines for "
            "this month with the dates on them, which is normal and not a double charge. {desk}",
        ],
    },
    {
        "section": "billing",
        "subjects": [
            "Charge I was not expecting",
            "Query on the bill this month",
            "statement query",
            "Extra charge on the statement",
            "Charge I cannot account for",
        ],
        "kind": "broken",
        "problems": [
            "There is a charge on the statement for eighteen pounds that I cannot account for.",
            "We have been billed twice this month by the look of the bank statement.",
        ],
        "extras": [
            "The rest of it makes sense.",
            "It is dated the third which is not our usual date.",
        ],
        "searches": [
            "statement",
            "charges",
            "part month",
            "authorisation",
            "invoice",
        ],
        "articles": [
            "reading-the-charges-on-your-statement",
            "where-to-find-your-invoices",
            "changing-the-card-on-the-account",
        ],
        "replies": [
            "Hi {first}, that is the part month from when you added the second venue on the third, "
            "which is why the date looks odd. It sits next to the ordinary line for the month, so "
            "the two together are the full bill rather than two bills. {desk}",
            "Hello {first}, the smaller one is the authorisation from putting the new card on. It "
            "is not a charge and your bank will release it within a few days, although some banking "
            "apps show it as if it were. {desk}",
        ],
    },
    {
        "section": "integrations",
        "subjects": [
            "Payroll connection has stopped",
            "nothing going through to payroll",
            "payroll connection",
            "Connection needs signing in again",
            "Payroll transfers stopped",
        ],
        "kind": "broken",
        "problems": [
            "Nothing has gone through to payroll since the end of last month and nobody told us.",
            "The payroll connection says it needs signing in again and I do not have the login.",
        ],
        "extras": [
            "Our old finance manager set it up and she has left.",
            "We have a payroll run on Thursday.",
        ],
        "searches": [
            "connection",
            "reconnect",
            "connections",
            "transfer",
            "payroll",
        ],
        "articles": [
            "reconnecting-something-that-stopped",
            "setting-up-the-payroll-connection",
            "the-nightly-transfer-and-when-it-runs",
        ],
        "replies": [
            "Hi {first}, connections are signed in as a person, so it stopped when her account at "
            "the payroll end did. Open Settings > Connections and press Reconnect, signing in as "
            "yourself. Everything held since then goes on Thursday night. {desk}",
            "Hello {first}, you do not need her login, only your own at the payroll provider. Once "
            "you have reconnected, press Test before Thursday so you are not finding out on the "
            "night. Give me a shout if the test comes back with anything. {desk}",
        ],
    },
    {
        "section": "integrations",
        "subjects": [
            "Calendar is a week behind",
            "calendar showing last week",
            "calendar link",
            "Rota not updating in my calendar",
            "Old rota in the calendar",
        ],
        "kind": "broken",
        "problems": [
            "The rota in my calendar is showing last week's shifts. I published the new one on "
            "Monday.",
            "My phone calendar has not picked up the new rota at all.",
        ],
        "extras": [
            "Everybody else seems fine.",
            "I subscribed to the link about a year ago.",
        ],
        "searches": [
            "calendar link",
            "calendar",
            "subscribed",
            "subscription",
            "refresh",
        ],
        "articles": [
            "calendar-links-and-how-they-keep-up-to-date",
            "putting-the-rota-in-a-calendar",
        ],
        "replies": [
            "Hi {first}, your calendar has the rota as an import rather than a subscription, so it "
            "took a copy a year ago and has never looked again. Delete that calendar and add the "
            "link again as a subscribed calendar, and it will keep up on its own. {desk}",
            "Hello {first}, the link is live and showing this week when I open it here, so it is "
            "your calendar's refresh rather than the rota. Some of them only look once a day. "
            "Forcing a refresh in the calendar app will bring it straight down. {desk}",
        ],
    },
    {
        "section": "integrations",
        "subjects": [
            "Takings not coming through from the till",
            "no takings since Saturday",
            "till figures",
            "Wage cost has no takings",
            "Till connection",
        ],
        "kind": "broken",
        "problems": [
            "The wage cost report has no takings against it since Saturday.",
            "Till figures have stopped coming in and the percentage is useless without them.",
        ],
        "extras": [
            "We had a new till terminal put in on Friday.",
            "The hours side is working fine.",
        ],
        "searches": [
            "takings",
            "till",
            "wage cost",
            "transfer log",
            "mapped",
        ],
        "articles": [
            "bringing-takings-in-from-the-till",
            "wage-cost-percentage-on-the-rota",
            "reading-a-transfer-error",
        ],
        "replies": [
            "Hi {first}, the new terminal is a new device as far as the till system is concerned, "
            "so it was sending takings we had nothing to map them to. I have mapped it to your "
            "venue and pulled Saturday onwards back in. The percentage should read properly now. {desk}",
            "Hello {first}, the transfer log has been refusing since Friday evening with an "
            "unknown device. That will be the terminal. Open Settings > Connections, map it to the "
            "venue, and the nights since then come in on the next run. {desk}",
        ],
    },
    {
        "section": "integrations",
        "subjects": [
            "Same person twice across the two systems",
            "matching screen shows her twice",
            "duplicate record",
            "Transfer refusing one person",
            "Two records for one person",
        ],
        "kind": "broken",
        "problems": [
            "One of the kitchen team is in payroll under her married name and in here under her "
            "old one, and the transfer keeps refusing her.",
            "Somebody appears twice on the matching screen and I do not know which to pick.",
        ],
        "extras": [
            "Her hours have not gone through for two weeks now.",
            "I would rather not break the other one.",
        ],
        "searches": [
            "matching",
            "matched",
            "payroll reference",
            "not in payroll",
            "transfer log",
        ],
        "articles": [
            "somebody-who-exists-twice-across-the-two-systems",
            "matching-staff-records-between-two-systems",
            "reading-a-transfer-error",
        ],
        "replies": [
            "Hi {first}, match ours to whichever one payroll is actually paying, then mark the "
            "other as not in payroll so it stops coming back at you. Putting her payroll reference "
            "on her staff record here will keep the two tied together from now on. {desk}",
            "Hello {first}, I have matched her to the married name, which is the one with this "
            "year's payments against it, and marked the other as not in payroll. The two weeks of "
            "hours went through on tonight's run. {desk}",
        ],
    },
    {
        "section": "integrations",
        "subjects": [
            "Changing an API key",
            "rolling the key over",
            "api key",
            "New API key",
            "Replacing our key",
        ],
        "kind": "how-to",
        "problems": [
            "We need to change the API key our reporting uses. What happens to the old one?",
            "Our developer wants to know how to roll the key over without breaking the nightly job.",
        ],
        "extras": [
            "It runs at about three in the morning.",
            "There is only the one thing using it.",
        ],
        "searches": [
            "api key",
            "revoke",
            "new key",
            "key",
            "api",
        ],
        "articles": [
            "changing-an-api-key",
            "reading-a-transfer-error",
        ],
        "replies": [
            "Hi {first}, make the new key first, put it into your reporting, and only then revoke "
            "the old one. A revoked key keeps working for twenty-four hours, so even if you revoke "
            "in the wrong order the three in the morning job will not fail that night. {desk}",
            "Hello {first}, the old one stops being shown the moment you make a new one, so copy "
            "the new key before you close the window. Nothing else on the account changes and no "
            "other connection is affected. {desk}",
        ],
    },
    {
        "section": "integrations",
        "subjects": [
            "Nightly transfer failed",
            "red line in the transfer log",
            "transfer error",
            "Transfer failed overnight",
            "Error on last night's run",
        ],
        "kind": "broken",
        "problems": [
            "I have an email saying last night's transfer failed with an error and I do not "
            "understand what it means.",
            "The transfer log has a red line against Tuesday and no explanation I can follow.",
        ],
        "extras": [
            "It says something about a period being locked.",
            "Everything else in the log looks normal.",
        ],
        "searches": [
            "transfer log",
            "transfer",
            "error",
            "locked",
            "send again",
        ],
        "articles": [
            "reading-a-transfer-error",
            "the-nightly-transfer-and-when-it-runs",
            "locking-a-pay-period",
        ],
        "replies": [
            "Hi {first}, the period had been locked before the corrections went, so the transfer "
            "had nowhere to put them. I have unlocked it, the run has gone through, and I have "
            "locked it again behind me. Nothing is missing at the payroll end. {desk}",
            "Hello {first}, it means what it says: the week it was sending belongs to a pay period "
            "that is locked. Unlock it from Hours > Payroll, press Send again on that line in the "
            "log, then lock it back. {desk}",
        ],
    },
    {
        "section": "mobile app",
        "subjects": [
            "Cannot sign in to the app",
            "app says password wrong",
            "signing in",
            "Locked out of the app",
            "App will not let her in",
        ],
        "kind": "broken",
        "problems": [
            "Three of the team cannot get into the app. It says the email or password is wrong and "
            "they are sure it is not.",
            "One of the waitresses has a new phone and the app will not let her in.",
        ],
        "extras": [
            "They can get in on the website on a laptop.",
            "It started this week as far as I know.",
        ],
        "searches": [
            "sign in",
            "app",
            "password",
            "email address",
            "reset",
        ],
        "articles": [
            "signing-in-to-the-app",
            "signing-in-on-a-new-phone",
            "resetting-a-password-somebody-has-forgotten",
        ],
        "replies": [
            "Hi {first}, all three are typing a personal address rather than the one on their staff "
            "records, which is why the website lets them in and the app does not. Tell them which "
            "address we hold, or change the records to the ones they use. {desk}",
            "Hello {first}, her new phone is on an old version of the app from the phone shop's "
            "restore. Ask her to update it in the App Store and sign in again. If it still refuses, "
            "press Send reset on her record and she can set a new password. {desk}",
        ],
    },
    {
        "section": "mobile app",
        "subjects": [
            "No notifications when the rota goes out",
            "Push notifications not arriving",
            "notifications",
            "Nobody gets told about the rota",
            "Push notifications",
        ],
        "kind": "broken",
        "problems": [
            "Nobody gets a notification when I publish. They only find out if they open the app.",
            "Half the team get the push and half do not.",
        ],
        "extras": [
            "They are mostly on android.",
            "I have checked and notifications are on in their settings.",
        ],
        "searches": [
            "notifications",
            "push",
            "battery saving",
            "phone settings",
            "hold notifications",
        ],
        "articles": [
            "notifications-that-do-not-arrive",
            "turning-notifications-on",
            "stopping-rota-emails-going-out-at-night",
        ],
        "replies": [
            "Hi {first}, on Android it is nearly always battery saving, which is set per app rather "
            "than for the phone. Ask them to take the app out of battery saving and the pushes come "
            "through. That is why it is half of them and not all. {desk}",
            "Hello {first}, your venue has notifications held until eight in the morning, so a rota "
            "published in the evening goes out then rather than at once. I can move or remove the "
            "hold if you would rather they went straight away. {desk}",
        ],
    },
    {
        "section": "mobile app",
        "subjects": [
            "Clocking in and location",
            "app asks for location every time",
            "clock in refusing",
            "Cannot find the venue",
            "Location and the app",
        ],
        "kind": "broken",
        "problems": [
            "The app asks for location every time somebody clocks in and one of the team will not "
            "allow it.",
            "Clock in on the app says it cannot find the venue and refuses.",
        ],
        "extras": [
            "There is no signal in the cellar which may be part of it.",
            "The tablet on the bar works fine.",
        ],
        "searches": [
            "location",
            "clock in",
            "clocking in",
            "tablet",
            "venue",
        ],
        "articles": [
            "location-and-clocking-in",
            "clocking-in-from-the-app",
            "clocking-in-on-the-venue-tablet",
        ],
        "replies": [
            "Hi {first}, location is on for your venue, which is why it asks. The tablet on the bar "
            "does not use it at all, so anybody who would rather not allow it can clock in there. I "
            "can turn it off for the venue if it is causing more trouble than it saves. {desk}",
            "Hello {first}, the cellar will be it. The check needs a rough position and four walls "
            "of stone is enough to stop it. I have widened the radius on your venue, which helps at "
            "the door, but the tablet is the answer downstairs. {desk}",
        ],
    },
    {
        "section": "mobile app",
        "subjects": [
            "App keeps signing people out",
            "Being asked to sign in again",
            "app signing out",
            "Signed out again and again",
            "App not staying signed in",
        ],
        "kind": "broken",
        "problems": [
            "The app signs me out every couple of days and I have to put the password in again.",
            "Two of the supervisors are being asked to sign in again most mornings.",
        ],
        "extras": [
            "It is not the end of the world but it is putting people off using it.",
            "Both on iphones.",
        ],
        "searches": [
            "sign in again",
            "signed out",
            "app",
            "email address",
            "update the app",
        ],
        "articles": [
            "the-app-asking-you-to-sign-in-again",
            "signing-in-on-a-new-phone",
            "changing-the-email-on-an-account",
        ],
        "replies": [
            "Hi {first}, both of them had their email addresses corrected on their records in the "
            "last fortnight, and a change to the address signs that person out everywhere. It "
            "should settle now the records are right. {desk}",
            "Hello {first}, if it is still happening after a week, ask them to sign out properly "
            "once and back in rather than letting it drop out. That clears an old sign-in that "
            "keeps being refused, which is usually what is behind it. {desk}",
        ],
    },
    {
        "section": "mobile app",
        "subjects": [
            "Shifts not showing on the app",
            "App is empty for one of them",
            "next week missing on the app",
            "App shows nothing for next week",
            "Chef cannot see his shifts",
        ],
        "kind": "broken",
        "problems": [
            "I have published next week but one of the chefs says his app is empty.",
            "The app shows this week but nothing for next, and the rota is definitely published.",
        ],
        "extras": [
            "He has pulled down to refresh and it made no difference.",
            "Everybody else can see theirs.",
        ],
        "searches": [
            "shifts",
            "app",
            "refresh",
            "published",
            "week",
        ],
        "articles": [
            "seeing-your-shifts-for-the-week",
            "publishing-a-rota-so-staff-can-see-it",
            "signing-in-to-the-app",
        ],
        "replies": [
            "Hi {first}, he is on next week's rota at the second venue rather than yours, and the "
            "app shows him both, so his week is not empty here. Ask him to swipe once more; I "
            "suspect he is looking at the week after next. {desk}",
            "Hello {first}, next week was published at your other site but yours is still showing "
            "as Draft, which is why only some of them can see it. Press Publish on the week and "
            "they will all have it within a minute. {desk}",
        ],
    },
    {
        "section": "mobile app",
        "subjects": [
            "App on an older phone",
            "app not working on an old phone",
            "not compatible",
            "Old android phone",
            "App will not install",
        ],
        "kind": "broken",
        "problems": [
            "One of our KPs has an old android phone and the app closes as soon as it opens.",
            "The app will not install on one of the team's phones, it says it is not compatible.",
        ],
        "extras": [
            "He does not want a new phone and I do not blame him.",
            "Is there anything else he can use?",
        ],
        "searches": [
            "older phone",
            "android",
            "app store",
            "website",
            "install",
        ],
        "articles": [
            "the-app-on-an-older-phone",
            "getting-the-app-on-a-phone",
            "clocking-in-on-the-venue-tablet",
        ],
        "replies": [
            "Hi {first}, the app needs Android 10 and his will be on 9 or older. The website in his "
            "phone's browser does everything except clocking in, and the tablet on the bar covers "
            "that, so he is not stuck. {desk}",
            "Hello {first}, nothing he can do about the app itself, but bookmark the website on his "
            "home screen and it behaves much like the app. He will see his rota the moment it is "
            "published, same as everybody else. {desk}",
        ],
    },
]

# --------------------------------------------------------------------- the venues paying us

VENUE_FIRST = [
    "The Wharf", "Marlow Street", "Ostler's", "Brindle", "The Old Assembly", "Copperfield",
    "Nettlebed", "Harbourgate", "The Tannery", "Saltmarsh", "Greyfriars", "The Buttermarket",
    "Quarryman's", "Wickham", "The Malt House", "Pennyfield", "Ashcroft", "The Saltern",
    "Bramber", "Corncrake", "The Lamplighter", "Orchard Lane", "Stonebridge", "The Drapers",
    "Cobbleside", "Hartwell", "The Boathouse", "Ferrymount", "Larkspur", "The Printworks",
    "Culvert", "Winnow", "The Coalyard", "Sedgemill", "Thorne and Vale", "The Glasshouse",
    "Marram", "Halyard", "The Sorting Office", "Redbourne", "The Cooperage", "Kettlewick",
    "Alderfield", "The Bellhouse", "Fossgate", "Tarnside", "The Long Room", "Hesketh",
    "Barleycroft", "The Fenwick", "Ivy Gate", "Shorewell",
]

VENUE_KIND = [
    "Kitchen", "Bar", "Coffee House", "Tap Room", "Bistro", "Cafe", "Brasserie", "Dining Rooms",
    "Grill", "Wine Bar", "Leisure Centre", "Sports Centre", "Bar and Grill", "Rooms", "",
]

TWICE_OVER = "The Weighbridge Bar"

TOWNS = [
    "Whitcombe", "Ashbourne", "Netherton", "Marsden", "Ulverby", "Kirkby Mallow", "Stanwick",
    "Braithwell", "Denbury", "Ravensmoor", "Thornbury", "Calderwick", "Penrhyn", "Wenlock",
    "Beckthorpe", "Garstone", "Milldale", "Coldwell", "Harrowby", "Sedgeford", "Tarnbeck",
    "Whinfell", "Brackley", "Lowther", "Ingleby", "Farndon", "Carleton", "Weston Bray",
    "Northgate", "Eastrington", "Hollowmoor", "Kelsall", "Rydings", "Upton Gale", "Aldersby",
    "Pennerley",
]

# ------------------------------------------------------------------ how people write to us

OPENERS = [
    "Hi,", "Hello,", "Hi there,", "Hello Hollins,", "Hiya,", "Hi team,",
    "Hi, sorry to bother you again,", "Hello again,",
]

MORNING = ["Morning,", "Good morning,"]
AFTERNOON = ["Afternoon,", "Good afternoon,"]
EVENING = ["Evening,", "Good evening,"]

# Filler that fits whatever the ticket is about: who is asking, how they work, how they feel
# about writing in. Nothing here says anything about what the ticket is for.
NEUTRAL_FILLER = [
    "I have had a look through the help centre but I am going round in circles.",
    "There are two of us who do the rota so it may be worth telling us both.",
    "I have asked our area manager and she did not know either.",
    "We are a small team so it is usually me doing all of this.",
    "I am fairly new to running the rota here, so apologies if this is obvious.",
    "Whatever you can tell me is more than I know at the moment.",
    "I would rather ask than make a mess of it.",
    "Our general manager is on leave so it has landed with me.",
    "If there is a better way of doing this I am happy to hear it.",
    "We have three of us with manager access, in case that matters.",
    "I do the office side and my business partner does the floor.",
    "I would rather not have to ring in the middle of service.",
    "Sorry if this is a daft question.",
    "I have written it out as best I can, tell me what else you need.",
    "It is the sort of thing I should probably know by now.",
    "The rest of the system has been very good to us, for what it is worth.",
    "I have got the account open in front of me if you need anything from it.",
    "My assistant manager is the one who usually deals with this and she is off.",
    "I am the owner on the account so I should have the run of it.",
    "Happy to jump on a call if that is easier than typing it all out.",
    "We took the second site on a while back and I have not sat down with the settings since.",
    "For what it is worth we came off spreadsheets when we joined and nobody here has ever used "
    "anything like this before, so do tell me if I am looking in the wrong place entirely.",
    "My area manager is asking about it, which is really why I am writing rather than leaving it, "
    "and she will want something in writing that I can forward on to her.",
    "I did try ringing earlier but I think I caught you at lunch, so I thought I would write it "
    "all down instead and you can pick it up whenever suits.",
    "I have copied our other manager in so she can see what you say back.",
    "We have been with you long enough that I should know this, I am sure.",
]

# The same, but written against the account it came from.
ACCOUNT_FILLER = [
    "We are on the {plan} plan if that makes any difference.",
    "We are on {plan}, if that matters at all.",
    "We have been on the {plan} plan since we joined.",
    "There are {staff} of us on the books at the moment.",
    "We have {staff} on the books here.",
    "It is only {staff} of us at this site.",
]

# Only where something has stopped working. On a how do I question there was never a before.
BROKEN_FILLER = [
    "This started sometime last week I think.",
    "It was fine before, it has only started since the weekend.",
    "My assistant manager has tried it as well and gets exactly the same.",
    "I have looked twice and I am sure I am not imagining it.",
    "It has been like this for three or four days now.",
    "Nothing has changed at our end that I know of.",
    "It is happening every time, not now and then.",
    "It was working the week before, which is why it stands out.",
    "I should say the same thing happened a while back as well and it sorted itself out before I "
    "got round to writing in, so I do not know whether the two are connected.",
    "It is only a handful of people affected out of the whole team, and the ones it is affecting "
    "are all part time, in case that narrows it down at all.",
]

# Only on a ticket the writer is not in a hurry about, so it never sits under an urgent subject.
CALM_FILLER = [
    "It is not urgent today but I would like it sorted before the end of the month.",
    "Whenever somebody has five minutes is fine, we are quiet until Thursday.",
    "There is no hurry on this at all.",
    "Whenever you get to it is fine.",
]

# About a phone, a browser or a signal, and always about something not working. Used only where
# those are the subject, because on a billing question it reads like somebody else's ticket.
DEVICE_FILLER = [
    "It is the same whether I do it on the laptop or on my phone.",
    "We are in the middle of a refurb and the office wifi has been in and out all week, so I did "
    "wonder whether that had anything to do with it, but the tills are fine.",
    "I have tried it on two different phones and they both do exactly the same.",
    "Everything else on the phone seems to be fine, it is only this.",
    "I have updated the app and it made no difference.",
    "It is the same on the tablet behind the bar.",
]

# How many tickets any one of these lines may appear in. A line a reader meets twenty times reads
# as a template rather than as somebody writing in.
LINE_CAP = 40
RARE_LINES = {"I have had a look through the help centre but I am going round in circles.": 10}

CLOSERS = [
    "Thanks in advance.",
    "Any help appreciated.",
    "Cheers.",
    "Let me know when you can.",
    "Sorry if I have missed something obvious.",
    "Thanks for your time.",
    "Hope that makes sense.",
    "Please can somebody have a look.",
    "Thanks so much.",
    "Many thanks.",
    "Grateful for anything you can tell me.",
    "Thanks, as always.",
    "Ta.",
    "Appreciate it.",
    "Thank you.",
    "Let me know if you need anything else from me.",
    "Any steer welcome.",
    "Hope you can help.",
    "Thanks for reading all that.",
    "Speak soon.",
]

URGENT_CLOSERS = [
    "We open at five so ideally before then.",
    "Sorry to push but I need this sorted before the weekend.",
    "We are open tonight so anything you can do today would help.",
    "Today if at all possible, please.",
    "I know you are busy but this one is holding us up.",
    "Anything you can do this morning would be a help.",
]

CALM_CLOSERS = [
    "Not urgent but it is getting annoying.",
    "No rush on this one.",
    "Whenever you have a minute.",
    "Nothing pressing, just when you can.",
    "Next week is fine if that is easier.",
]

IN_A_RUSH = [
    "Sorry, dashing about.",
    "Sorry, typing this between tables.",
    "Excuse the typing, I am on the floor.",
    "Sorry to be brief.",
    "Written in a hurry, sorry.",
    "Sorry, one hand on the phone.",
    "Apologies, mid-service here.",
    "Short one, sorry, we are slammed.",
]


CUSTOMER_NAMES = [
    "Eleri", "Dan", "Saoirse", "Tomas", "Bethan", "Kwame", "Ines", "Rory", "Meera", "Lewis",
    "Aoife", "Zeynep", "Joss", "Nadia", "Fraser", "Orla", "Diego", "Hattie", "Ola", "Callie",
    "Rehan", "Tess", "Gwen", "Marek", "Isobel", "Sami", "Paulina", "Ciaran", "Yusuf", "Brid",
    "Leila", "Struan", "Verity", "Anton", "Delphine", "Kofi", "Maddy", "Tariq", "Elin", "Hugo",
]

TYPOS = [
    ("the", "teh"), ("and", "adn"), ("staff", "staf"), ("holiday", "holday"),
    ("because", "becuase"), ("please", "plese"), ("receive", "recieve"), ("payroll", "payrol"),
    ("account", "acount"), ("manager", "manger"), ("weekend", "weekeend"),
    ("tomorrow", "tommorow"), ("definitely", "definately"), ("separate", "seperate"),
    ("something", "somthing"), ("shifts", "shfits"),
]

# The shape of a reply that goes out with an article on it. The article named is the one the desk
# actually sent.
ARTICLE_REPLIES = [
    "Hi {first}, thanks for getting in touch. The steps are all in this one: {title}. Work down it "
    "and you should be there in a couple of minutes. Come back to me if it still will not behave "
    "and I will take a look at the account myself. {desk}",
    "Hello {first}, this article is the one you want: {title}. I have had a quick look at your "
    "account as well and everything on our side looks as it should. {desk}",
    "Hi {first}, no bother at all. Have a read of {title} and follow it through from the top. It "
    "catches most people out in the same place, about halfway down. {desk}",
    "Hello {first}, have a read of {title} and see whether it gets you where you want to be. If "
    "it does not quite fit what you are looking at, say so and I will dig into the account. {desk}",
    "Hi {first}, I have sent you {title}, which covers exactly this. Give it a go and let me know "
    "how you get on. {desk}",
    "Hello {first}, thanks for the detail, that helped narrow it down. {title} walks through it "
    "step by step. {desk}",
    "Hi {first}, this is covered in {title}. If you would rather I changed it at this end instead, "
    "just say and I will do it while you are on. {desk}",
    "Hi {first}, {title} is the article for this. Have a read, and if anything in it does "
    "not match what you are seeing, send me a screenshot and I will pick it up. {desk}",
]

# When the desk sends the nearest page rather than the right one, it says so rather than pretending.
NEARLY_REPLIES = [
    "Hi {first}, have a look at {title}, it covers the same ground and should get you moving. "
    "Give me a shout if you are still stuck after it. {desk}",
    "Hello {first}, {title} is the page I would start from for this. Work through it and come "
    "back to me with anything it leaves open. {desk}",
    "Hi {first}, {title} is the closest we have written down. Take what applies and I will fill "
    "in the rest if you need me to. {desk}",
]

MONTH_TICKETS = [
    ((2025, 9), 121),
    ((2025, 10), 107),
    ((2025, 11), 113),
    ((2025, 12), 178),
    ((2026, 1), 134),
    ((2026, 2), 97),
    ((2026, 3), 116),
    ((2026, 4), 109),
    ((2026, 5), 123),
    ((2026, 6), 101),
    ((2026, 7), 128),
    ((2026, 8), 110),
]

# The one section where a remark about a phone or a signal belongs in the ticket.
DEVICE_SECTIONS = ("mobile app",)

# ------------------------------------------------------------------------------- helpers


UNITS = (
    "nought one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen"
).split()
TENS = "  twenty thirty forty fifty sixty seventy eighty ninety".split(" ")


def in_words(number):
    """A headcount the way somebody would type it into an email."""
    if number < 20:
        return UNITS[number]
    if number < 100:
        tens, units = divmod(number, 10)
        word = TENS[tens]
        return word if not units else word + "-" + UNITS[units]
    hundreds, rest = divmod(number, 100)
    word = UNITS[hundreds] + " hundred"
    return word if not rest else word + " and " + in_words(rest)


def slugify(text):
    keep = []
    for ch in text.lower():
        if ch.isalnum():
            keep.append(ch)
        elif ch == "'":
            continue
        elif keep and keep[-1] != "-":
            keep.append("-")
    return "".join(keep).strip("-")


def stamp(when):
    return when.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def at(day, hour, minute, second=0):
    return datetime(day.year, day.month, day.day, hour, minute, second, tzinfo=timezone.utc)


# What makes a page one where something is changed rather than one that is only read. The general
# lines about saving and confirming belong on the first sort and nowhere else.
CHANGE_WORDS = (
    "Save", "Publish", "Confirm", "Set ", "Change", "Add ", "Tick", "Untick", "Upload", "Delete",
    "Approve", "Decline", "Mark ", "Book ", "Revoke", "Generate", "Remove", "Pause", "Lock",
    "Restore", "Cancel", "Drag", "Reinstate", "Invite", "Reconnect", "Connect", "Edit", "Correct",
    "Apply", "Undo", "Press Retry", "Press Copy", "Enter the new", "Copy week", "Fill it",
)


def page_kind(record):
    text = " ".join(record["steps"])
    return "editing" if any(word in text for word in CHANGE_WORDS) else "reading"


def take(bag, wants, barred=()):
    """The next line in the bag that suits this page, if there is one."""
    for spot in range(len(bag) - 1, -1, -1):
        kind, line = bag[spot]
        if kind not in ("any", wants):
            continue
        if any(word in line for word in barred):
            continue
        bag.pop(spot)
        return line
    return None


def word_count(text):
    return len(text.split())


def days_between(first, last):
    out = []
    day = first
    while day <= last:
        out.append(day)
        day = day + timedelta(days=1)
    return out


def where_for(record):
    """The page this article is about, taken from its own steps."""
    section = record["section"]
    text = " ".join(record["steps"])
    if section == "mobile app":
        if "tap You" in text or "Tap You" in text:
            return "the app, under You"
        if "wipe" in text:
            return "the app, under Shifts"
        return "the app"
    for name in PAGE_NAMES:
        if name in text:
            return name
    for opener, page in OPENS_AT:
        if opener in text:
            return page
    return SECTION_HOME[section]


def details_for(section):
    barred = OFF_TOPIC.get(section, ())
    return [line for line in DETAIL if not any(word in line for word in barred)]


# ------------------------------------------------------------------------------ articles


def dealt(rng, bank, cap):
    """A shuffled bag holding each line `cap` times, so nothing turns up more often than that."""
    bag = [line for line in bank for _ in range(cap)]
    rng.shuffle(bag)
    return bag


def build_articles(rng):
    articles = []
    seen = set()
    bags = {
        "intro": dealt(rng, INTROS, GENERAL_LINE_CAP),
        "expect": dealt(rng, EXPECT, GENERAL_LINE_CAP),
        "detail": dealt(rng, DETAIL, GENERAL_LINE_CAP),
    }
    for record in ARTICLES:
        slug = slugify(record["title"])
        if slug in seen:
            raise ValueError(f"two articles want the slug {slug}")
        seen.add(slug)
        touched = article_updated(rng)
        articles.append(
            {
                "slug": slug,
                "title": record["title"],
                "section": record["section"],
                "body": build_body(rng, record, bags, touched),
                "updated_at": stamp(touched),
                "views": 0,
            }
        )
    rng.shuffle(articles)
    # The oldest corner of the help centre: written once and never touched since. It is a page
    # nobody points anybody at, which is how it got that way.
    pointed_at = {slug for topic in TOPICS for slug in topic["articles"]}
    forgotten = next(a for a in articles if a["slug"] not in pointed_at)
    forgotten["updated_at"] = stamp(at(date(2023, 11, 2), 16, 41, 9))
    forgotten["forgotten"] = True
    return sorted(articles, key=lambda a: (a["section"], a["slug"]))


def forgotten_slug(articles):
    for article in articles:
        if article.get("forgotten"):
            return article["slug"]
    return None


def count_views(rng, articles, tickets):
    """Views follow how often a page gets sent out, loosely, the way they do in real life."""
    sent = {}
    for ticket in tickets:
        slug = ticket.get("sent_article_slug")
        if slug:
            sent[slug] = sent.get(slug, 0) + 1
    for article in articles:
        times = sent.get(article["slug"], 0)
        views = 30 + times * rng.randint(22, 58) + rng.randint(0, 240)
        if rng.random() < 0.12:
            views = int(views * (1 + rng.random() * 3))
        article["views"] = max(views, LOWEST_ORDINARY_VIEWS, times)
    for article in articles:
        if article.pop("forgotten", False):
            article["views"] = FORGOTTEN_VIEWS
    return articles


def build_body(rng, record, bags, touched):
    section = record["section"]
    title = record["title"]
    thing = title[0].lower() + title[1:]
    where = where_for(record)
    kind = page_kind(record)
    freshness = "fresh" if (THROUGH - touched.date()).days <= RECENTLY else "stale"

    paragraphs = [take(bags["intro"], freshness).format(thing=thing, Thing=title, where=where)]
    steps = record["steps"]
    if rng.random() < 0.25:
        paragraphs.append(NEWLINE.join("- " + s for s in steps))
    else:
        paragraphs.append(NEWLINE.join(f"{n}. {s}" for n, s in enumerate(steps, 1)))
    if rng.random() < 0.82:
        line = take(bags["expect"], kind)
        if line:
            paragraphs.append(line)
    paragraphs.append(record["note"])

    # A page carries a line or two of general advice and no more. Past that it stops being about
    # the thing in its title, which is the whole point of the page.
    barred = OFF_TOPIC.get(section, ())
    for _ in range(rng.choices([0, 1, 2], weights=[34, 48, 18], k=1)[0]):
        line = take(bags["detail"], kind, barred)
        if line:
            paragraphs.insert(-1, line)
    return (NEWLINE + NEWLINE).join(paragraphs)


def article_updated(rng):
    """Most pages were touched this year; a few have not been looked at in a long time."""
    roll = rng.random()
    if roll < 0.55:
        back = rng.randint(1, 210)
    elif roll < 0.85:
        back = rng.randint(211, 520)
    else:
        back = rng.randint(521, 900)
    day = THROUGH - timedelta(days=back)
    hour = rng.choices(
        [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        weights=[5, 11, 13, 12, 7, 6, 10, 11, 10, 8, 4, 3],
        k=1,
    )[0]
    return at(day, hour, rng.randint(0, 59), rng.randint(0, 59))


def check_topics(articles):
    """Every article a topic points at has to exist, or a ticket would name a page nobody has."""
    have = {article["slug"] for article in articles}
    for topic in TOPICS:
        missing = [slug for slug in topic["articles"] if slug not in have]
        if missing:
            raise ValueError(f"{topic['subject']} points at {missing}")


# ------------------------------------------------------------------------------ accounts


def build_accounts(rng, count=ACCOUNTS):
    names = []
    for first in VENUE_FIRST:
        for kind in VENUE_KIND:
            name = f"{first} {kind}".strip()
            if name != TWICE_OVER:
                names.append(name)
    rng.shuffle(names)
    chosen = names[: count - 2]
    # The one pair of venues with the same name, in two different towns, which is why the desk
    # asks which town somebody is ringing from before it opens anything.
    chosen = [TWICE_OVER, TWICE_OVER] + chosen

    accounts = []
    for name in chosen:
        on_the_books = staff_count(rng)
        accounts.append(
            {
                "name": name,
                "plan": account_plan(rng, on_the_books),
                "staff_count": on_the_books,
                "town": rng.choice(TOWNS),
                "created_at": stamp(account_created(rng)),
            }
        )
    while accounts[0]["town"] == accounts[1]["town"]:
        accounts[1]["town"] = rng.choice(TOWNS)
    accounts[3]["staff_count"] = 3
    accounts[3]["plan"] = "starter"
    accounts[11]["staff_count"] = 118
    accounts[11]["plan"] = "venue"

    # Account numbers were handed out in the order venues signed up, so they run with the dates.
    accounts.sort(key=lambda a: a["created_at"])
    for number, account in enumerate(accounts, start=1):
        account["account_id"] = f"A{2000 + number}"
    return [
        {
            "account_id": a["account_id"],
            "name": a["name"],
            "plan": a["plan"],
            "staff_count": a["staff_count"],
            "town": a["town"],
            "created_at": a["created_at"],
        }
        for a in accounts
    ]


def who_writes_in(rng, accounts):
    """One or two people at each venue do the writing in, and it is nearly always the same ones."""
    contacts = {}
    for account in accounts:
        how_many = 1 if rng.random() < 0.62 else 2
        contacts[account["account_id"]] = rng.sample(CUSTOMER_NAMES, how_many)
    return contacts


def account_plan(rng, staff):
    """The plan a venue of that size would be on, give or take the ones who never moved."""
    roll = rng.random()
    if staff <= 10:
        return "starter" if roll < 0.62 else ("team" if roll < 0.98 else "venue")
    if staff <= 26:
        return "starter" if roll < 0.10 else ("team" if roll < 0.88 else "venue")
    return "starter" if roll < 0.02 else ("team" if roll < 0.44 else "venue")


def staff_count(rng):
    roll = rng.random()
    if roll < 0.34:
        return rng.randint(6, 13)
    if roll < 0.78:
        return rng.randint(14, 26)
    return rng.randint(27, 40)


def account_created(rng):
    back = rng.randint(20, 1500)
    day = THROUGH - timedelta(days=back)
    return at(day, rng.randint(8, 21), rng.randint(0, 59), rng.randint(0, 59))


# ------------------------------------------------------------------------------- tickets


def build_tickets(rng, accounts, articles):
    by_slug = {article["slug"]: article for article in articles}
    by_section = {}
    for article in articles:
        by_section.setdefault(article["section"], []).append(article)
    never_sent = forgotten_slug(articles)

    contacts = who_writes_in(rng, accounts)
    in_order = sorted(accounts, key=lambda a: a["created_at"])
    opened_on = [account["created_at"] for account in in_order]

    bags = {
        "neutral": capped(rng, NEUTRAL_FILLER),
        "account": capped(rng, ACCOUNT_FILLER),
        "broken": capped(rng, BROKEN_FILLER),
        "calm": capped(rng, CALM_FILLER),
        "device": capped(rng, DEVICE_FILLER),
        "closer": capped(rng, CLOSERS),
        "urgent_closer": capped(rng, URGENT_CLOSERS),
        "calm_closer": capped(rng, CALM_CLOSERS),
    }

    opened = []
    for (year, month), count in MONTH_TICKETS:
        opened.extend(month_openings(rng, year, month, count))
    opened.sort()

    tickets = []
    number = 5100
    for when in opened:
        room = bisect.bisect_right(opened_on, stamp(when))
        account = rng.choice(in_order[:room] or in_order[:1])
        tickets.append(
            build_ticket(
                rng, number, when, account, contacts, articles, by_slug, by_section, bags, never_sent
            )
        )
        number += 1

    # One that came in while the desk was thin over the new year and nobody came back to it.
    january = [t for t in tickets if t["opened_at"].startswith("2026-01")]
    stale = january[len(january) // 3]
    stale["status"] = "open"
    stale["first_reply_at"] = None
    stale["closed_at"] = None
    stale["reply"] = None
    stale["sent_article_slug"] = None
    stale["handled_by"] = None
    stale["closed_by"] = None
    return tickets


def capped(rng, bank):
    """A bag of filler lines, none of them in more tickets than it has any business being in."""
    bag = []
    for line in bank:
        bag += [line] * RARE_LINES.get(line, LINE_CAP)
    rng.shuffle(bag)
    return bag


def month_openings(rng, year, month, count):
    first = date(year, month, 1)
    last = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    days = days_between(first, last)
    weights = []
    for day in days:
        weight = 3.1 if day.day <= 7 else 1.0
        if day.weekday() == 5:
            weight *= 0.4
        elif day.weekday() == 6:
            weight *= 0.25
        if month == 12 and 22 <= day.day <= 27:
            weight *= 1.8
        weights.append(weight)
    picked = rng.choices(days, weights=weights, k=count)
    out = []
    for day in picked:
        # Email comes in at all hours. The form inside the app mostly does not.
        hour = rng.choices(
            [0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
            weights=[3, 2, 1, 1, 2, 4, 9, 34, 78, 95, 86, 60, 52, 69, 78, 69, 52, 34, 26, 26, 17, 9, 5],
            k=1,
        )[0]
        out.append(at(day, hour, rng.randint(0, 59), rng.randint(0, 59)))
    return out


def build_ticket(
    rng, number, when, account, contacts, articles, by_slug, by_section, bags, never_sent
):
    topic = rng.choice(TOPICS)
    first = rng.choice(contacts[account["account_id"]])
    night = when.hour >= 23 or when.hour < 7
    if night:
        channel = "email" if rng.random() < 0.85 else "app"
    else:
        channel = "app" if rng.random() < 0.43 else "email"
    subject, urgent = dress_subject(rng, rng.choice(topic["subjects"]))
    said = date_words(when)
    typed = words_typed(rng, topic)
    message = build_message(rng, topic, first, urgent, account, said, bags, when)

    ticket = {
        "number": number,
        "account_id": account["account_id"],
        "channel": channel,
        "subject": subject,
        "message": message,
        "opened_at": stamp(when),
        "first_reply_at": None,
        "closed_at": None,
        "handled_by": None,
        "closed_by": None,
        "searched_for": typed,
        "sent_article_slug": None,
        "reply": None,
        "status": "open",
    }

    # Anything older than the last few weeks has been dealt with one way or another.
    fresh = (THROUGH - when.date()).days <= STILL_ON_THE_DESK
    if fresh:
        outcome = rng.choices(
            ["article", "hand", "no_reply", "open"], weights=[38, 28, 8, 26], k=1
        )[0]
    else:
        outcome = rng.choices(["article", "hand", "no_reply"], weights=[47, 35, 18], k=1)[0]
    if outcome == "open":
        return ticket

    handler = rng.choices(DESK, weights=[46, 45, 9], k=1)[0]

    if outcome == "no_reply":
        ticket["closed_at"] = stamp(
            when + timedelta(days=rng.randint(3, 21), minutes=rng.randint(0, 59))
        )
        ticket["closed_by"] = handler
        ticket["status"] = "closed"
        return ticket

    ticket["handled_by"] = handler
    replied = when + reply_wait(rng)
    if handler == "Marcus Hollins":
        replied = out_of_hours(rng, when, replied)
    else:
        replied = desk_hours(rng, when, replied)
    ticket["first_reply_at"] = stamp(replied)
    if outcome == "article":
        slug, spot_on = pick_article(rng, topic, typed, articles, never_sent)
        ticket["sent_article_slug"] = slug
        ticket["reply"] = rng.choice(ARTICLE_REPLIES if spot_on else NEARLY_REPLIES).format(
            first=first, title=by_slug[slug]["title"], desk=handler.split()[0], **said
        )
    else:
        ticket["reply"] = rng.choice(topic["replies"]).format(
            first=first, desk=handler.split()[0], **said
        )

    shut = rng.random() < 0.45 if fresh else True
    if shut:
        ticket["closed_at"] = stamp(
            replied + timedelta(hours=rng.randint(1, 96), minutes=rng.randint(0, 59))
        )
        ticket["closed_by"] = handler if rng.random() < 0.82 else rng.choice(DESK)
        ticket["status"] = "closed"
    else:
        ticket["status"] = "replied"
    return ticket


def desk_hours(rng, opened, replied):
    """Priya and Callum are on weekdays, give or take the odd late one or a Saturday morning."""
    day = replied.date()
    if rng.random() < 0.035:
        hour = rng.choice([7, 19, 20, 21]) if day.weekday() < 5 else rng.randint(9, 12)
        stamped = at(day, hour, rng.randint(0, 59), rng.randint(0, 59))
        if stamped > opened:
            return stamped
    hour = replied.hour
    while True:
        if day.weekday() < 5 and 8 <= hour <= 18:
            stamped = at(day, hour, rng.randint(0, 59), rng.randint(0, 59))
            if stamped > opened:
                return stamped
        day = day + timedelta(days=1)
        while day.weekday() >= 5:
            day = day + timedelta(days=1)
        hour = rng.randint(8, 18)


def out_of_hours(rng, opened, replied):
    """Marcus covers the evenings and the weekends, so his replies carry those times."""
    day = replied.date()
    hour = rng.randint(9, 21) if day.weekday() >= 5 else rng.randint(18, 22)
    stamped = at(day, hour, rng.randint(0, 59), rng.randint(0, 59))
    while stamped <= opened:
        day = day + timedelta(days=1)
        hour = rng.randint(9, 21) if day.weekday() >= 5 else rng.randint(18, 22)
        stamped = at(day, hour, rng.randint(0, 59), rng.randint(0, 59))
    return stamped


def date_words(when):
    """The months a customer would name in a message written on this day."""
    before = when.replace(day=1) - timedelta(days=1)
    after = (when.replace(day=28) + timedelta(days=7)).replace(day=1)
    return {
        "month": when.strftime("%B"),
        "last_month": before.strftime("%B"),
        "next_month": after.strftime("%B"),
    }


def pick_article(rng, topic, typed, articles, never_sent):
    """The desk sends a page it has just had on screen, unless it knew the one by heart."""
    results = []
    if typed:
        found = find_articles(articles, typed, page=1, per_page=SEEN_AT_A_TIME)["articles"]
        results = [a["slug"] for a in found if a["slug"] != never_sent]
    if results and rng.random() < 0.85:
        theirs = [slug for slug in results if slug in topic["articles"]]
        others = [slug for slug in results if slug not in topic["articles"]]
        if theirs and (not others or rng.random() < 0.93):
            return rng.choice(theirs), True
        if others:
            return rng.choice(others), False
        return rng.choice(theirs), True
    known = [slug for slug in topic["articles"] if slug != never_sent]
    return rng.choice(known), True


def words_typed(rng, topic):
    typed = rng.choice(topic["searches"])
    if typed is not None and rng.random() < 0.11:
        return None
    return typed


def dress_subject(rng, subject):
    """How the subject line comes out, and whether the writer is in a hurry about it."""
    roll = rng.random()
    if roll < 0.13:
        return subject.lower(), False
    if roll < 0.22:
        return subject + "?", False
    if roll < 0.28:
        return "URGENT - " + subject.lower(), True
    if roll < 0.34:
        return "Re: " + subject, False
    return subject, False


def filler_for(rng, topic, urgent, account, bags):
    """What this writer might pad with, given their ticket, their venue and how urgent it is."""
    wanted = ["neutral", "account"]
    if topic["kind"] == "broken":
        wanted.append("broken")
        if topic["section"] in DEVICE_SECTIONS:
            wanted.append("device")
    if not urgent:
        wanted.append("calm")
    lines = []
    for _ in range(MOST_FILLER):
        rng.shuffle(wanted)
        for name in wanted:
            if bags[name]:
                lines.append(bags[name].pop())
                break
    return [
        line.format(plan=account["plan"], staff=in_words(account["staff_count"]))
        for line in lines
    ]


def sign_off(rng, urgent, bags):
    """How the message ends. Plenty of people just stop, so an empty bag is no loss."""
    wanted = ["urgent_closer", "closer"] if urgent else ["closer", "calm_closer"]
    rng.shuffle(wanted)
    for name in wanted:
        if bags[name]:
            return [bags[name].pop()]
    return []


def greeting(rng, when):
    """Nobody writes Morning at six in the evening."""
    if 5 <= when.hour < 12:
        return rng.choice(OPENERS + MORNING)
    if 12 <= when.hour < 18:
        return rng.choice(OPENERS + AFTERNOON)
    return rng.choice(OPENERS + EVENING)


def build_message(rng, topic, first, urgent, account, said, bags, when):
    """Some people write two lines, some write half a page. Both come in every day.

    Whatever they write, it is about their own ticket and their own venue: two lines of padding at
    the outside, and nothing about how it used to work on a question about how it works now.
    """
    target = rng.choices([26, 52, 96, 130], weights=[24, 36, 26, 14], k=1)[0]
    style = rng.choices(
        ["plain", "lower", "hurried", "formal", "loose"],
        weights=[36, 15, 12, 20, 17],
        k=1,
    )[0]

    body = [rng.choice(topic["problems"]).format(**said)]
    pool = [line.format(**said) for line in rng.sample(topic["extras"], len(topic["extras"]))]
    pool += filler_for(rng, topic, urgent, account, bags)
    while word_count(" ".join(body)) < target and pool:
        body.append(pool.pop(0))

    opener = "Dear Hollins Rota support," if style == "formal" else greeting(rng, when)
    tail = sign_off(rng, urgent, bags)
    if style == "hurried":
        tail = tail + [rng.choice(IN_A_RUSH)]

    text = " ".join([opener] + body + tail)
    if style == "formal":
        text = text + NEWLINE + NEWLINE + "Kind regards," + NEWLINE + first
    else:
        text = text + NEWLINE + first

    if style == "lower":
        text = text.lower()
    elif style == "hurried":
        text = text.replace(".", "!", 1)
    if style in ("lower", "loose", "hurried"):
        for _ in range(rng.randint(1, 3)):
            right, wrong = rng.choice(TYPOS)
            text = text.replace(right, wrong, 1)
    return text


def reply_wait(rng):
    """Most things are answered the same shift; a few sit over a weekend."""
    roll = rng.random()
    if roll < 0.58:
        return timedelta(minutes=rng.randint(7, 240))
    if roll < 0.85:
        return timedelta(hours=rng.randint(5, 23), minutes=rng.randint(0, 59))
    if roll < 0.97:
        return timedelta(days=rng.randint(1, 3), hours=rng.randint(0, 9))
    return timedelta(days=rng.randint(4, 12), hours=rng.randint(0, 9))




# ---------------------------------------------------------------------------------- run


def build():
    rng = random.Random(SEED)
    articles = build_articles(rng)
    check_topics(articles)
    accounts = build_accounts(rng, ACCOUNTS)
    tickets = build_tickets(rng, accounts, articles)
    count_views(rng, articles, tickets)
    return {"articles": articles, "accounts": accounts, "tickets": tickets}


def as_text(data):
    return json.dumps(data, indent=1, ensure_ascii=False, sort_keys=False) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the bundled history.")
    parser.add_argument("--check", action="store_true", help="compare against the committed file")
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args(argv)

    text = as_text(build())
    target = Path(args.out)
    if args.check:
        if not target.exists():
            print(f"{target} is not there")
            return 1
        if target.read_text(encoding="utf-8") != text:
            print(f"{target} is not what this script builds")
            return 1
        print(f"{target} matches")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {target} ({target.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
