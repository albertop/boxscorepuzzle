"""The daily rotation: today and yesterday are public, and nothing else is.

**`docs/calendar.md` owns the access model; this is the code that enforces it.** Static delivery (§23)
and paid access (§9) pull opposite ways — a static file on a public path cannot be sold — and the
resolution is two paths rather than one: today's and yesterday's packages are public static files, and
everything else is on no public path at all.

⚠️⚠️ **The delete is the enforcement, and it is the step whose failure is invisible.** A rotation that
copies correctly and deletes nothing looks identical from the outside on day one, and on day two, and
by day thirty the archive §9 sells is public. **Anything fetched once is gone**, so the leak is
permanent and silent. Every test in this module's suite exists for that step rather than for the copies.

⚠️ **The date is an argument, never read from a clock in here.** A function that asks the machine what
day it is can only be tested against the day the suite runs, which is a test that reports the
environment. The caller decides; `serving_date()` below is what the caller uses.

⚠️ **No key, and no signature made here.** Every pointer was signed at generation (`build_inventory.py`),
so the daily step is a copy — the private key stays on the laptop (§16, §33).
"""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROLLOVER_OFFSET_HOURS = -8
"""The clock that decides which puzzle is today's. **`docs/calendar.md` owns the decision and the reason.**

The short version: the rollover must not land while people are playing, and at UTC it lands at 19:00 or
20:00 Eastern — a player who sits down a quarter of an hour earlier loses the board mid-game. At UTC-8
it lands at 03:00 Eastern and midnight Pacific in winter, 04:00 and 01:00 under daylight saving.

⚠️⚠️ **This is the number's third spelling, and that is forced rather than sloppy.** `forge` holds one
because it decides which dates are frozen; `serve` will hold one when E1 builds the loader. **`publish`
cannot import `forge`'s**: `forge` never reaches the VPS (§33) and this module runs there. The trees
share no code by rule, so the rule is shared by *document* — and `test_the_offset_matches_the_document`
asserts this constant against the figure `docs/calendar.md` states, which is what stops three spellings
from becoming three answers.
"""

DAYS = "days"
"""Where the signed per-date pointers live inside a generation, as `build_inventory.py` writes them."""

MANIFEST = "manifest.json"
TODAY = "today.json"
YESTERDAY = "yesterday.json"

PUBLIC_SCHEMA = 1
"""The public manifest's own format version. **Not the package schema and not the generation
manifest's** — it is a third document with a third version line, and `docs/package-format-v5.md` records
how easily a reader takes one `schema` field for another."""


class RotationError(RuntimeError):
    """The rotation could not be completed. **Nothing is left half-published when this is raised.**"""


def serving_date(now: datetime | None = None) -> date:
    """Which date's puzzle should be public right now.

    ⚠️ **A naive datetime is refused rather than assumed.** It means *whatever zone this machine is in*,
    which is the exact ambiguity the fixed offset exists to remove.

    ⚠️ **Normalised to UTC before the offset.** `.date()` reads the calendar of whatever zone is
    attached, so the same instant expressed in two zones would otherwise give two serving dates. The
    same defect was made and caught in `forge`'s copy on the day it was written.
    """
    moment = now if now is not None else datetime.now(tz=UTC)
    if moment.tzinfo is None:
        message = f"serving_date needs an aware datetime; {moment!r} names no zone"
        raise ValueError(message)
    return (moment.astimezone(UTC) + timedelta(hours=ROLLOVER_OFFSET_HOURS)).date()


@dataclass(frozen=True, slots=True)
class Rotation:
    """What one run did. **Returned rather than printed**, so a caller can assert on it.

    `published` is the dates now public, `retired` the package ids removed. ⚠️ **`retired` is the field
    the tests watch**: it is the only evidence the delete happened, and a run that copies perfectly and
    retires nothing is the failure this module exists to prevent.
    """

    published: tuple[str, ...]
    retired: tuple[str, ...]
    kept: tuple[str, ...]


def _pointer(inventory: Path, when: date) -> dict[str, object] | None:
    """The signed pointer for a date, from whichever generation holds it, or `None` if there is none.

    ⚠️ **Searched across generations, newest first.** After a top-up several exist, and only the newest
    holds a complete schedule — an older one was written before the later dates existed
    (`docs/calendar.md`). A pointer names the generation that owns its *package*, which is often not the
    one the pointer was found in.
    """
    for generation in sorted(inventory.iterdir(), reverse=True):
        candidate = generation / DAYS / f"{when.isoformat()}.json"
        if candidate.is_file():
            loaded = json.loads(candidate.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                message = f"{candidate} is not an object"
                raise RotationError(message)
            return loaded
    return None


def _package(inventory: Path, pointer: dict[str, object]) -> Path:
    """The package file a pointer names, refused loudly if it is not there.

    ⚠️⚠️ **The pointer's own `generation`, never the newest one.** They differ after a top-up, and using
    the newest is the defect v39-P1-01 closed on the writing side — reintroducing it here would produce
    a 404 on a legitimately assigned date, from a pointer the forge signed.
    """
    generation, puzzle_id = pointer.get("generation"), pointer.get("puzzle_id")
    if not isinstance(generation, str) or not isinstance(puzzle_id, str):
        message = f"a pointer names generation={generation!r} puzzle_id={puzzle_id!r}"
        raise RotationError(message)
    found = inventory / generation / f"{puzzle_id}.json"
    if not found.is_file():
        message = f"{found} does not exist; the generation holding it is not on this machine"
        raise RotationError(message)
    return found


PENDING = ".pending"
"""Suffix for a public file being written. ⚠️ It ends in `.pending`, **after** `.json`, so a half-written
package is not picked up by the `*.json` sweep as a real one -- and the sweep removes any it finds."""


def rotate(inventory: Path, public: Path, when: date) -> Rotation:
    """Make `when` and the day before public, and **remove everything else**.

    ⚠️⚠️ **Built by difference, not by deletion of a remembered third day.** The first shape of this was
    *delete the day before yesterday* — which leaves anything the previous run failed to remove in place
    forever, so one missed run becomes a permanent leak rather than a recoverable one. **This one
    computes the set that should be there and removes whatever else it finds**, so a run that has been
    broken for a week repairs the whole week the first time it succeeds.

    ⚠️ **Today is required; yesterday is not.** The first day of an inventory has no yesterday, and
    refusing to publish because of it would make the calendar's own first date unservable. A missing
    *today* is an error, because that is the day the game is.
    """
    pointers: dict[str, tuple[date, dict[str, object], Path]] = {}
    for label, day in ((TODAY, when), (YESTERDAY, when - timedelta(days=1))):
        found = _pointer(inventory, day)
        if found is None:
            if label == TODAY:
                message = f"no pointer for {day.isoformat()}; there is nothing to serve today"
                raise RotationError(message)
            continue
        pointers[label] = (day, found, _package(inventory, found))

    public.mkdir(parents=True, exist_ok=True)
    wanted = {source.name for _day, _pointer_doc, source in pointers.values()}

    # ⚠️ **Copied before anything is removed.** A failure part-way then leaves the public path holding
    # more than it should, which the health check reports — rather than holding less, which is a day
    # with no game and no signal.
    for label, (_day, pointer_doc, source) in pointers.items():
        _place(public / source.name, source.read_bytes())
        _place(public / label, (json.dumps(pointer_doc, indent=1, sort_keys=True) + "\n").encode("utf-8"))

    # ⚠️⚠️ **Its own sweep, and the first version folded it into the loop below.** That loop globs
    # `*.json` and a pending file ends in `.pending`, so the branch could never run — a check that
    # cannot fire, inside the fix for a check that did not exist. It was caught by the test asserting
    # a leftover is removed, which is the only reason to write that test rather than trust the branch.
    for pending in sorted(public.glob(f"*{PENDING}")):
        pending.unlink()

    retired = []
    # ⚠️ A different name from the pointer above on purpose: one `found` holding a parsed document in one
    # loop and a path in the next is how a type error becomes a runtime one.
    for stale in sorted(public.glob("*.json")):
        if stale.name in {MANIFEST, TODAY, YESTERDAY} or stale.name in wanted:
            continue
        stale.unlink()
        retired.append(stale.stem)

    if YESTERDAY not in pointers:
        # The first day of an inventory: no yesterday exists, so a stale one from a previous run must
        # not be left claiming to be it.
        (public / YESTERDAY).unlink(missing_ok=True)

    _write_public_manifest(public, wanted)
    return Rotation(
        published=tuple(day.isoformat() for day, _doc, _source in pointers.values()),
        retired=tuple(retired),
        kept=tuple(sorted(name.removesuffix(".json") for name in wanted)),
    )


def _write_public_manifest(public: Path, wanted: set[str]) -> None:
    """The manifest a browser may read: **the two ids that are public, and nothing else.**

    ⚠️⚠️ **This is the whole of A4.2.** The generation manifest lists every published id and stays behind
    the wall; a public one listing more than two hands out puzzles nobody has played yet. **Written from
    the files actually placed**, not from the calendar, so it cannot claim something the directory does
    not hold.
    """
    document = {
        "schema": PUBLIC_SCHEMA,
        "puzzles": sorted(name.removesuffix(".json") for name in wanted),
    }
    _place(public / MANIFEST, (json.dumps(document, indent=1, sort_keys=True) + "\n").encode("utf-8"))


def _place(destination: Path, content: bytes) -> None:
    """Write a public file so a failure leaves the **previous** bytes, never a torn file. (v40-P2-01)

    ⚠⚠ **Opening a file for writing truncates it before the new bytes arrive**, and that inverts this
    module's whole ordering. The copy-then-delete sequence above is deliberate: a part-way failure is
    meant to leave the public path holding *more* than it should, which the health check reports, rather
    than less, which is a day with no game and no signal. An in-place write of `today.json` breaks that
    at the one file that selects the day's puzzle -- a disk-full or short write destroys the pointer it
    was replacing and the rotation raises with neither the old one nor the new one valid.

    ⚠️ **Pending file, then `replace()`, which is atomic on the same filesystem** on Windows and on
    Linux alike. On a failure before the rename the pending file is removed and the served file is
    untouched -- so the failure mode is *the rotation did not happen*, which is exactly what the health
    check is built to notice.

    ⚠️ **No lock and no multi-file transaction.** There is one writer, once a day. What this closes is
    one process meeting one ordinary filesystem error, and a scheme that needs coordination would be
    solving a problem this deployment does not have.
    """
    pending = destination.with_name(destination.name + PENDING)
    try:
        pending.write_bytes(content)
        pending.replace(destination)
    except OSError:
        pending.unlink(missing_ok=True)
        raise
