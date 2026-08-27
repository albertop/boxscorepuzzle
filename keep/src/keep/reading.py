"""Turning a request body into an `Event` or an `ErrorReport`, or refusing it by name.

⚠️⚠️ **Validate at the boundary, not downstream.** `CLAUDE.md` records this as its own rule and the
package reader already follows it: a malformed body must produce a controlled rejection **naming the
field**, not an uncontrolled `TypeError` three layers later where the message describes a symptom.

⚠️ **A field this reader does not know is refused rather than ignored.** An unknown key is either a newer
client or a typo beside a real one — `duration_ms` next to `duration_msec`, say — and ignoring it stores
an event that means something else while saying nothing. C7 makes that permanent.

⚠️ **Nothing here trusts a type.** Every value is checked, because the caller is `serve` relaying a
browser: `duration_ms` arriving as a string is a thing that happens, and a database column will accept
it in one engine and refuse it in another.
"""

from typing import Any

# ⚠️ **`Any` on the readers below is the honest annotation, not a gap.** Their whole job is to take
# something that *might be anything* — JSON off a request, relayed from a browser — and either produce a
# record or refuse by name. A narrower type would be a claim about the input that nothing has checked
# yet, which is the claim these functions exist to make rather than assume.
from keep.store import ErrorReport, Event, Share


class MalformedError(ValueError):
    """A body that cannot become a record. **Names the field**, so the fix is not a guess."""


LARGEST_STORED_INTEGER = 2**31 - 1
"""The biggest number the schema's `INTEGER` columns hold.

⚠⚠ **A fact about the database, not a judgement about the game** (v39-P2-01). Every numeric field
here lands in a Postgres `INTEGER`, and a larger value was accepted at the boundary and rejected by the
column — which aborted the transaction and, on a reused connection, **took the service down until it
was restarted.** Checking it here is `CLAUDE.md`'s own rule: validate at the boundary, so a malformed
request is a controlled rejection rather than a failure three layers later in a different vocabulary.

⚠️ **This is not the sanity check `CLAUDE.md` asks for on durations.** That one is *"absurd values
must not corrupt percentiles"*, and 2³¹-1 milliseconds is twenty-five days — far past absurd and still
accepted here. A ceiling on plausible play is a product decision with a number in it, so it is
`docs/reviews/open-decisions.md` rather than a value invented in this file (§7)."""


def _text(row: dict[str, Any], field: str, *, optional: bool = False) -> str | None:
    value = row.get(field)
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value:
        message = f"{field} is {value!r}, expected a non-empty string"
        raise MalformedError(message)
    return value


DURATION_CEILING_MS = 8 * 60 * 60 * 1000
"""The longest a game may be recorded as taking. **Operator's decision, 2026-08-26: eight hours.**

⚠️⚠️ **The clock is a duration the CLIENT reports**, accumulated in the browser and paused when the page
is hidden — so a machine asleep with the tab open, a clock that ran while nobody played, or a client
sending anything at all can put a number here that no game produced. **`CLAUDE.md` asks for this under
Security**: sanity-check client-reported durations before storing, so absurd values do not corrupt
percentiles.

⚠️ **Why it corrupts rather than merely looks wrong:** §26 sells comparison, and a handful of eleven-day
games drags the median far enough that *faster than 78%* stops being true. **And it cannot be repaired
afterwards** — nothing in the row says which number was the real one.

⚠️ **Eight hours is deliberately generous.** It is not a guess at how long a puzzle takes; it is a bound
above anything a person does in one sitting, chosen so a slow honest solve is never touched. A board is
solved in minutes.
"""


def _capped_duration(row: dict[str, Any]) -> int:
    """The reported duration, or the ceiling when it is past it. **Clamped, not refused.**

    ⚠️⚠️ **This is the opposite of the rule three lines down, and the two cases are genuinely different.**
    A value above `LARGEST_STORED_INTEGER` **cannot be stored** — refusing is the only honest answer, and
    the comment there explains why a clamp would be a wrong number wearing a measurement's clothes.

    **A twelve-hour duration is storable and merely implausible**, and the operator's decision is that
    the game should still be recorded: refusing it would throw away a real player's real solve because
    their laptop slept, and §27's *you can never lose* is the same principle one layer down.

    ⚠️ **So a clamped row IS a wrong number, knowingly.** What makes it acceptable is that every value it
    can produce is 8h exactly, which is outside the range any honest solve occupies — a percentile
    computed over these can be read as *this many players took more than eight hours*, and that is a
    fact rather than a corruption.
    """
    value = _whole(row, "duration_ms")
    return min(value, DURATION_CEILING_MS)


def _whole(row: dict[str, Any], field: str) -> int:
    value = row.get(field)
    # ⚠️ `bool` is an `int` in Python, so `solved: true` would arrive as a perfectly good `1` for a
    # duration. Rejected explicitly, the same way the pool's numeric guard does it.
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        message = f"{field} is {value!r}, expected a whole number that is not negative"
        raise MalformedError(message)
    if value > LARGEST_STORED_INTEGER:
        # ⚠️ **Refused rather than clamped.** A clamped duration is a wrong number that looks like a
        # measurement, and C7 makes it permanent. A refusal is visible: the client's outbox drops that
        # one event, and the split retry keeps every other event in the batch (`serve/engine/outbox.js`).
        message = f"{field} is {value!r}, above {LARGEST_STORED_INTEGER}, which is all the column holds"
        raise MalformedError(message)
    return value


def _flag(row: dict[str, Any], field: str) -> bool:
    value = row.get(field)
    if not isinstance(value, bool):
        message = f"{field} is {value!r}, expected true or false"
        raise MalformedError(message)
    return value


def _no_unknown_fields(row: dict[str, Any], known: tuple[str, ...]) -> None:
    extra = sorted(set(row) - set(known))
    if extra:
        message = f"unknown fields {extra}; this reader stores what it understands and refuses the rest"
        raise MalformedError(message)


_EVENT_FIELDS = (
    "event_id", "device_id", "account_id", "puzzle_id", "calendar_date", "played_on",
    "duration_ms", "hints", "errors", "failed_checks", "highest_technique", "solved", "assisted",
)  # fmt: skip

_ERROR_FIELDS = ("error_id", "device_id", "message", "stack", "page", "viewport", "user_agent")

_SHARE_FIELDS = ("share_id", "device_id", "puzzle_id", "event_id", "channel", "shared_on")

SHARE_CHANNELS = ("native", "clipboard")
"""How the share left the device. **An acceptance list, and the two are not interchangeable.**

`native` is `navigator.share` and `clipboard` is the fallback where it does not exist
(`docs/beta-0-plan.md` G2). They have different semantics -- a share sheet that opened is not a link
that was pasted -- so a combined figure erases the only distinction that would let the number be read
later. A third channel is a decision, and it arrives by being added here rather than by a client
sending a word nobody has seen.

⚠️ **Acceptance, never exclusion.** A channel this reader does not know is refused by name, which is
the shape §32 records for provenance: absence must not read as permission."""


def read_event(row: Any) -> Event:  # noqa: ANN401
    """One event, checked field by field."""
    if not isinstance(row, dict):
        message = f"an event is {type(row).__name__}, expected an object"
        raise MalformedError(message)
    _no_unknown_fields(row, _EVENT_FIELDS)
    return Event(
        event_id=_text(row, "event_id") or "",
        device_id=_text(row, "device_id") or "",
        # ⚠️ Optional and **required to be present**: `account_id` must be `null` rather than missing,
        # because a field that appears only sometimes is one consumers forget to check for.
        account_id=_text(row, "account_id", optional=True) if "account_id" in row else _absent("account_id"),
        puzzle_id=_text(row, "puzzle_id") or "",
        calendar_date=_text(row, "calendar_date", optional=True),
        played_on=_text(row, "played_on", optional=True),
        duration_ms=_capped_duration(row),
        hints=_whole(row, "hints"),
        errors=_whole(row, "errors"),
        failed_checks=_whole(row, "failed_checks"),
        highest_technique=_text(row, "highest_technique", optional=True),
        solved=_flag(row, "solved"),
        assisted=_flag(row, "assisted"),
    )


def _absent(field: str) -> str:
    message = f"{field} is missing; it must be present and null rather than left out"
    raise MalformedError(message)


def read_error(row: Any) -> ErrorReport:  # noqa: ANN401
    """One client error report."""
    if not isinstance(row, dict):
        message = f"an error report is {type(row).__name__}, expected an object"
        raise MalformedError(message)
    _no_unknown_fields(row, _ERROR_FIELDS)
    return ErrorReport(**{field: _text(row, field) or "" for field in _ERROR_FIELDS})


def read_share(row: Any) -> Share:  # noqa: ANN401
    """One share, checked field by field.

    ⚠️ `event_id` is optional and **required to be present** -- null rather than missing, the same rule
    `account_id` follows on an event, and for the same reason: a field that appears only sometimes is
    one consumers forget to check for. A share whose game has not uploaded yet carries `null`.
    """
    if not isinstance(row, dict):
        message = f"a share is {type(row).__name__}, expected an object"
        raise MalformedError(message)
    _no_unknown_fields(row, _SHARE_FIELDS)
    channel = _text(row, "channel") or ""
    if channel not in SHARE_CHANNELS:
        message = f"channel is {channel!r}, expected one of {list(SHARE_CHANNELS)}"
        raise MalformedError(message)
    return Share(
        share_id=_text(row, "share_id") or "",
        device_id=_text(row, "device_id") or "",
        puzzle_id=_text(row, "puzzle_id") or "",
        event_id=_text(row, "event_id", optional=True) if "event_id" in row else _absent("event_id"),
        channel=channel,
        shared_on=_text(row, "shared_on", optional=True),
    )


def read_batch(body: Any, key: str, one: Any) -> list[Any]:  # noqa: ANN401
    """The `{"events": [...]}` envelope, refused as a whole if any member is malformed.

    ⚠️⚠️ **All or nothing, and that is the safe direction here.** Storing the good ones and reporting the
    bad would leave the client holding a queue it cannot drain — it has no way to know which member the
    complaint was about — and it would make a client bug look like intermittent loss. A refused batch is
    retried whole, and the id makes that free.
    """
    if not isinstance(body, dict):
        message = f"the body is {type(body).__name__}, expected an object"
        raise MalformedError(message)
    rows = body.get(key)
    if not isinstance(rows, list):
        message = f"{key} is {type(rows).__name__}, expected a list"
        raise MalformedError(message)
    return [one(row) for row in rows]
