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
from keep.store import ErrorReport, Event


class MalformedError(ValueError):
    """A body that cannot become a record. **Names the field**, so the fix is not a guess."""


def _text(row: dict[str, Any], field: str, *, optional: bool = False) -> str | None:
    value = row.get(field)
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value:
        message = f"{field} is {value!r}, expected a non-empty string"
        raise MalformedError(message)
    return value


def _whole(row: dict[str, Any], field: str) -> int:
    value = row.get(field)
    # ⚠️ `bool` is an `int` in Python, so `solved: true` would arrive as a perfectly good `1` for a
    # duration. Rejected explicitly, the same way the pool's numeric guard does it.
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        message = f"{field} is {value!r}, expected a whole number that is not negative"
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
        duration_ms=_whole(row, "duration_ms"),
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
