"""Which puzzle is played on which date, and the rules that make that decision permanent.

**`docs/calendar.md` is the artefact this implements.** Read it first; the reasoning lives there and is
not repeated here.

The three rules, because they shape every function below:

- **§21 — the assignment is fixed and never recomputed.** There is no function from a date to a puzzle.
  There is a stored record of what was decided, and a builder that only ever adds to it. That is why
  `extend()` takes the existing calendar as its first argument and returns a new one rather than
  computing anything.
- **§21 — it extends, never rewrites.** A date at or before `today` is frozen. A future date can be
  replaced, because nobody has played it.
- **§7 — one game, one puzzle, over everything ever published.** The reveal prints both clubs, so the
  other direction's board travels *inside* the first one's reveal. No package can enforce this and no
  validation layer can see it: each file is individually perfect. It is a property of the set, and this
  module holds the set.

⚠️ **Named `calendar` although the standard library has one.** Python 3 resolves absolute imports, so
`boxscore_forge.calendar` shadows nothing for anyone; and the project's vocabulary is *calendar* in §21,
in `CLAUDE.md` and in every document. Inventing a second word for it would be two names for one thing,
which costs more than the resemblance does.

⚠️ **`today` is a parameter everywhere and is never read from the clock.** A function that asks the
system what day it is cannot be tested against a boundary, and the boundary is the whole rule.
"""

import json
from dataclasses import asdict, dataclass
from dataclasses import replace as with_fields
from datetime import date
from pathlib import Path
from typing import Final

ACTIVE: Final = "active"
VOID: Final = "void"

_FIELDS: Final = ("date", "puzzle_id", "game_id", "direction", "status", "assigned")
"""Every field an entry carries. **Spelled once**: `read()` validates against it and `write()` is
generated from the dataclass, so a field added to `Entry` and forgotten here fails on the round trip
rather than being silently dropped from disk."""


class CalendarError(Exception):
    """A refusal. Every one of them protects a decision that cannot be taken back."""


@dataclass(frozen=True, slots=True)
class Entry:
    """One date's assignment.

    ⚠️ **`game_id` and `direction` are here and never deploy.** §7 strips `game_id` from a published
    package precisely so a player cannot look the game up — but *one game, one puzzle* can only be
    checked against the game, so the source of truth has to carry the field the artefact is forbidden to
    carry. `for_serving()` is the only thing that crosses that line, and it drops both.

    `status` is `active` or `void`. A voided date **keeps its assignment**: deleting the entry would
    rewrite history, which is the thing §21 forbids.

    `assigned` names the generation the puzzle came from, so a board can be traced back to the run that
    made it.
    """

    date: str
    puzzle_id: str
    game_id: str
    direction: str
    status: str
    assigned: str


Calendar = tuple[Entry, ...]
"""The whole book, oldest date first. A tuple because §21 makes it append-only in fact, and a type that
cannot be mutated in place says so without a rule anybody has to remember."""


def games(calendar: Calendar) -> set[str]:
    """Every game this calendar has spent, **including voided dates**.

    ⚠️ A voided date still spent its game: the reveal was shown to whoever played it that day, and it
    printed both clubs. Voiding excludes a date from streaks and stats; it does not un-publish the other
    direction. **This is the one place where `void` and `replace` differ in kind** — a replaced future
    date was never seen, so `replace()` does return its game to the pool.
    """
    return {entry.game_id for entry in calendar}


def _refuse_the_past(when: str, today: date) -> None:
    if date.fromisoformat(when) <= today:
        message = f"{when} is today or in the past and cannot be assigned or replaced; the calendar extends"
        raise CalendarError(message)


def extend(calendar: Calendar, additions: Calendar, *, today: date) -> Calendar:
    """Add dates that have no entry, and refuse everything §21 and §7 forbid.

    **The whole extension mechanism is one sentence: write only dates with no entry.** That makes §21's
    two requirements the same requirement — idempotent because a second run has nothing to write, and
    extending rather than rewriting because there is no code path that touches an existing entry.

    ⚠️ **An addition landing on an assigned date is skipped, not an error.** Re-running the builder over
    an overlapping range is the normal way to top up a calendar, and making that fail would push the
    operator toward deleting the file — the one action that loses what cannot be recomputed.

    ⚠️ **A duplicate game *is* an error**, and it is checked against the calendar and the batch together.
    A batch clean on its own can still collide with something published months ago, which is exactly the
    case `write_reference_puzzles.refuse_second_direction` cannot see.
    """
    assigned = {entry.date for entry in calendar}
    spent = games(calendar)
    added: list[Entry] = []

    for entry in additions:
        if entry.date in assigned:
            continue
        _refuse_the_past(entry.date, today)
        if entry.game_id in spent:
            message = (
                f"{entry.game_id} has already been published, so {entry.date} would give its other "
                f"direction away: the reveal prints both clubs (§7)"
            )
            raise CalendarError(message)
        spent.add(entry.game_id)
        assigned.add(entry.date)
        added.append(entry)

    return tuple(sorted((*calendar, *added), key=lambda entry: entry.date))


def void(calendar: Calendar, when: str) -> Calendar:
    """Mark a date void, **keeping its assignment** (§21).

    Excluded from streaks and stats by whatever reads this; still occupying its date and still holding
    its game.

    ⚠️ **No `today`, and the first draft had one.** It was taken for symmetry with `extend` and
    `replace` and never read — a parameter that does nothing is the defect this project had in
    `load(gated=...)` for months, and *a parameter that lies about what it does is a hazard with no
    callers at all*, because it is read far more often than it is passed. A reader seeing `today` here
    would reasonably conclude voiding has a date boundary.

    **It has none, deliberately.** Any date can be voided: a puzzle found defective before anyone plays
    it can be voided as well as replaced, and refusing that would leave only the heavier option.
    """
    if not any(entry.date == when for entry in calendar):
        message = f"{when} has no assignment to void"
        raise CalendarError(message)
    return tuple(with_fields(e, status=VOID) if e.date == when else e for e in calendar)


def replace(calendar: Calendar, entry: Entry, *, today: date) -> Calendar:
    """Swap a **future** date's puzzle for another (§21).

    ⚠️ Refuses today and every past date. A played date cannot change: streaks, shared results and stats
    hang from it.

    ⚠️ **The dropped game returns to the pool**, which `void()` deliberately does not do. Nobody saw the
    replaced puzzle's reveal, so its other direction is still unpublished.
    """
    _refuse_the_past(entry.date, today)
    if not any(existing.date == entry.date for existing in calendar):
        message = f"{entry.date} has no assignment to replace; use extend() to add one"
        raise CalendarError(message)

    kept = tuple(existing for existing in calendar if existing.date != entry.date)
    if entry.game_id in games(kept):
        message = f"{entry.game_id} has already been published and cannot fill {entry.date} (§7)"
        raise CalendarError(message)
    return tuple(sorted((*kept, entry), key=lambda e: e.date))


def for_serving(calendar: Calendar) -> dict[str, str]:
    """What the VPS is allowed to know: **date to puzzle id, and nothing else.**

    ⚠️⚠️ **A `game_id` reaching the VPS is not untidiness — it is the answer.** §7 strips it from the
    package for the same reason. This function is the only crossing point, which is what makes it
    checkable; `test_calendar.py` asserts no game id survives it.

    Voided dates are dropped: there is nothing to serve on a date whose puzzle was withdrawn.

    ⚠️ **Derived, never hand-maintained.** Two files stating one mapping is this project's most-met
    defect; generating one from the other is the defence, and a test asserts they agree on every date.
    """
    return {entry.date: entry.puzzle_id for entry in calendar if entry.status == ACTIVE}


def write(path: Path, calendar: Calendar) -> None:
    """Persist the calendar, sorted and formatted so a diff shows one line per changed date."""
    rows = [asdict(entry) for entry in sorted(calendar, key=lambda entry: entry.date)]
    path.write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def read(path: Path) -> Calendar:
    """Load the calendar, or an empty one when there is none yet.

    ⚠️⚠️ **Validated at the boundary, and a half-parse is refused.** §21 makes these assignments
    irreproducible: a calendar that silently drops a malformed entry silently forgets a date nothing can
    recover. Every row must carry every field.

    ⚠️ **An absent file is the only thing that yields an empty calendar.** A file holding `[]` is a real
    calendar with no entries, which is the same thing here — but a *misspelled path* must not be able to
    look like a fresh start on a machine that already has months of assignments. That is why callers
    pass an explicit path and this raises on anything present and unreadable.
    """
    if not path.exists():
        return ()
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        message = f"{path} is not readable JSON: {exc}"
        raise CalendarError(message) from exc

    if not isinstance(rows, list):
        message = f"{path} holds {type(rows).__name__}, expected a list of entries"
        raise CalendarError(message)

    entries: list[Entry] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            message = f"{path} entry {index} is {type(row).__name__}, expected an object"
            raise CalendarError(message)
        missing = [field for field in _FIELDS if field not in row]
        if missing:
            message = f"{path} entry {index} ({row.get('date', 'no date')}) is missing {missing}"
            raise CalendarError(message)
        extra = [key for key in row if key not in _FIELDS]
        if extra:
            message = f"{path} entry {index} carries unknown fields {extra}"
            raise CalendarError(message)
        entries.append(Entry(**{field: str(row[field]) for field in _FIELDS}))

    return tuple(sorted(entries, key=lambda entry: entry.date))
