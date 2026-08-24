"""Fill the calendar: produce validated puzzles at volume and assign them to dates.

**`docs/beta-0-plan.md` group A, and `docs/calendar.md` is the artefact.** This is the one command the
runbook (A5) will document, and the one that gets re-run whenever the curve or the caps change.

**Two modes, and only one of them is safe to run without meaning to:**

    uv run python scripts/build_inventory.py --measure --per-decade 2   # read-only
    uv run python scripts/build_inventory.py --days 150 --from 2026-09-01

⚠️⚠️ **The default invocation writes.** It signs packages into `forge/inventory/` and extends
`forge/calendar.json`, which §21 makes **permanent for every date it touches**. `--measure` is the
read-only mode and it is the flag, not the default — so a maintainer skimming this header must not come
away thinking the bare command is a dry run. (v38-P3-01: this paragraph said *"measuring is all it does
today"* after the writing half was added, which is operator-facing guidance that had become false on a
script that mutates publication state.)

**The yield was unknown and is not any more** (2026-08-22, `docs/reviews/todo.md`). Two samples, 48
gated directions, **48 boards — the pipeline loses none**, and ~22 minutes for 150. So the batch does
not over-sample and needs no retry machinery.

⚠️ **What costs directions is duplicate games, not yield.** `load()` returns both directions of one game
about 10% of the time and the calendar refuses the second (§7). `DRAW_MARGIN` covers that, and a reader
who takes it for a cushion against production failures will lower it on seeing nothing fail.

⚠️ **Every refusal is counted by cause.** A pool that cannot be erased and a board the gate rejects are
different problems with different fixes, and a producer that reports one number cannot tell them apart —
which is why `produce()` returns its cause rather than printing it.

**What the assignment does, and all three come from `boxscore_forge.calendar`:** it reads
`forge/calendar.json` before it starts, writes only dates with no entry — §21's idempotence and its
extends-never-rewrites are the same mechanism — and refuses any game the calendar has already spent
(§7), which is the check no package can perform on itself.

⚠️ **The producer avoids duplicate games and the calendar refuses them.** A batch draws the other
direction of something about 10% of the time, so a run that aborted on the first one would be useless;
the loop skips them and the calendar's refusal stays as the last line rather than as a substitute.

⚠️⚠️ **This paragraph described the assignment half as missing until 2026-08-22**, after it was built —
*"what is missing is the producer that feeds it"*. (v38-P3-01, second pass.) The header above had
already been corrected and this one had not, which is the harder half of a stale-documentation finding:
**one true paragraph makes the file read as up to date**, and the false one sits below the fold.
"""

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from itertools import pairwise
from math import ceil
from pathlib import Path
from string import ascii_lowercase

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from boxscore_domain import (  # noqa: E402
    AUTOMATIC_RUNNER_FROM,
    MAX_INNINGS,
    REGULATION_INNINGS,
    ZERO_DENSITY_GATE,
)
from boxscore_forge.calendar import Calendar, Entry, extend, games, read, replace, write  # noqa: E402
from boxscore_forge.pool import SEASON_WINDOW, Loaded, load  # noqa: E402
from boxscore_forge.produce import produce  # noqa: E402
from boxscore_forge.publication_key import publication_key  # noqa: E402

# ⚠️⚠️ **Every one of these lines carries its own `noqa`, and combining two of them does not work.**
# (v38-P1-01) The aliased import was written as one line with one suppression, and ruff's isort **splits
# an aliased import onto its own line** — leaving the second half without the comment and a hard `E402`
# that fails the pre-push hook.
#
# ⚠️ Spelled around rather than quoted: writing the directive inside a comment *about* the directive
# makes ruff read it as one, and it warns about an invalid code on a line that is prose.
#
# ⚠️ **Two lessons, and the second is the useful one.** A suppression does not survive a tool that
# rewrites the line it sits on. And **re-run the linter after `--fix`, never before**: the run that said
# *all checks passed* was describing the file as it was, and the fix is what broke it.
from boxscore_package.format import SCHEMA_VERSION, Package  # noqa: E402
from boxscore_package.format import pointer as pointer_body  # noqa: E402
from boxscore_package.format import write as write_package  # noqa: E402
from boxscore_package.signing import sign_manifest  # noqa: E402

CALENDAR = _ROOT / "forge" / "calendar.json"
"""⚠️ **Committed, unlike the packages** (`docs/calendar.md`). §21 makes the assignment *fixed and never
recomputed*, so there is nothing to recompute it from: it is the one artefact here that cannot be
regenerated, and §33 names Git as the backup for a laptop that is a single point of failure."""

NOTE = "daily inventory"

CEILING = 12
"""The hardest stall target to ask a board for, counting down. **Ask the board rather than tell it** —
only about 20% of boards reach 12, so a producer that demanded it would discard four in five."""

DRAW_MARGIN = 1.15
"""How much more to draw than the number of dates wanted. **Measured, not guessed** (2026-08-22).

⚠️ **It is not about yield.** Of the directions that pass §5's gate and the caps, *every one* produced a
publishable board — 48 of 48 across two samples, 235 attempts. The pipeline loses nothing.

**What costs directions is `load()` returning both directions of one game**, which the calendar refuses
under §7: 3 of 36 drawn twice, 7 of 72. About 10%, so 15% of headroom covers it with room to spare. A
producer sized on yield would have drawn 150 for 150 dates and come up fifteen short without knowing why.
"""

FLOOR = 1
"""The easiest target worth producing. A board that reaches nothing from the ceiling down to here has
nothing to offer and is discarded silently (§22): with a pool this size, throwing away 30% costs
nothing."""


PRE_1950_SHARE = 0.05
"""§6's quota: **pre-1950 boards must not exceed 5% of what the player sees** — about eighteen a year,
one every three weeks, so that Ruth is **an event rather than the scenery**.

⚠️ **It selects rather than corrects, and that is still the reason for it.** §10's re-measurement found
pre-1950 is 29% of the pool naturally rather than 78%, so the quota stopped being a fix for a broken
distribution — and the operator's original argument never depended on the distribution: **the most
committed fan cannot name twenty players from before 1930, and a 1922 boxscore reveals eight strangers
even to him.**

⚠️⚠️ **Spelled here rather than imported, and that is a defect this file is carrying knowingly.**
`CLAUDE.md` says a number encoding a domain decision lives in `forge/src/boxscore_domain/` and is never
spelled elsewhere. This one is a *calendar* rule and `boxscore_domain` holds *board* rules; promoting it
is the right move and it is not this change. Recorded in `docs/reviews/todo.md`.
"""

DIVIDE = 1950
"""Where §6 draws the line. `SEASON_WINDOW` starts at 1910, so the eras are 1910-1949 and 1950-2029."""

ROLLOVER_OFFSET_HOURS = -8
"""The clock that defines which puzzle is today's. **`docs/calendar.md` is the decision and the reason.**

The short version: the rollover must not land while people are playing, and at UTC it lands at **20:00
Eastern** — a player who sits down at 19:45 loses the board fifteen minutes later. At UTC-8 it lands at
03:00 Eastern and midnight Pacific in winter, 04:00 and 01:00 under daylight saving — nobody in the
contiguous states is at a board at any of the four.

⚠️ **An offset, not `America/Los_Angeles`.** A named zone buys one hour of alignment between 03:00 and
04:00 Eastern — hours nobody is playing, so the drift it exists to prevent has nothing to prevent — and
costs a 23-hour day, a 25-hour day, an ambiguous local time twice a year, and a timezone database.

⚠⚠ **It rests on §10's premise that the audience is US baseball fans**, which already carries the
payments decision and the English-first decision. If that premise moves, **re-derive this rather than
carrying the conclusion across**: an offset chosen because the contiguous states span UTC-4 to UTC-8
is not automatically right for an audience that does not.

⚠️ **`serve` will spell this number again when E1 builds the loader, and that is prescribed rather than
sloppy** — §33 forbids the two trees sharing code and `CLAUDE.md` puts a decided value in one module *per
tree, never one module shared*. Neither CI workflow runs the other's suite, so **no test can compare
them**; both sides cite `docs/calendar.md` instead."""


def serving_date(now: datetime | None = None) -> date:
    """Which date's puzzle is being served right now.

    ⚠⚠ **This was `date.today()`, and it was the local day of whoever ran the build.** §21 freezes any
    date at or before today, so that boundary decided whether a puzzle already in front of players could
    be replaced — and it was answering with the operator's own calendar.

    **It was safe, for a reason that is not a guarantee: the machine happened to be east of UTC-8.**
    Anywhere east of the serving clock the local day runs *ahead* of the serving day, so the boundary
    froze more than it had to — conservative, and harmless. **That is a fact about where the build is
    run, not about the code.** At or west of UTC-8 it inverts: the same build from Los Angeles at 23:00
    puts the boundary *behind* the serving day, and the command that refuses to touch the past would let
    you replace a puzzle already being served.
    """
    moment = now if now is not None else datetime.now(tz=UTC)
    if moment.tzinfo is None:
        # ⚠️ **Refused rather than assumed.** A naive datetime means *whatever zone this machine is in*,
        # which is the exact ambiguity this function exists to remove. Guessing here would put the
        # operator's longitude back into the answer through a different door.
        message = f"serving_date needs an aware datetime; {moment!r} names no zone"
        raise ValueError(message)
    # ⚠⚠ **Normalised to UTC before the offset, and it was not.** `.date()` reads the calendar of
    # whatever zone is attached, so the same instant expressed in two zones gave two different serving
    # dates — the arithmetic was right and the reading was local. Found by the test asking whether seven
    # observers agree, which is the property the whole decision is about.
    return (moment.astimezone(UTC) + timedelta(hours=ROLLOVER_OFFSET_HOURS)).date()


MINIMUM_EARLY_GAP = 14
"""How close two pre-1950 boards may be, in days. **A bunching guard, not a second quota.**

⚠⚠ **Because counting is not placing, and the count already has an assertion.** §6 asks for pre-1950
boards *one every three weeks* so Ruth is an event; seven of them on seven consecutive days satisfies
the ceiling and defeats the point entirely. `spread()` places them and **nothing checked that it had**,
which is the audit's own rule — any composition property the pipeline cannot see needs an assertion
here — applied to the one property it was missing.

**Where 14 comes from, since a threshold set by eye gets loosened until it says nothing.** The quota is
5%, so the planned spacing is one board per 20 days. The only way two planned boards land closer is at
a seam between two build windows, and the worst seam `spread()` can produce still leaves 21 days. So 14
is below every legitimate gap with room to spare, and far above the failure it is watching for."""


def _is_early(entry: Entry) -> bool:
    """Whether this board is from before §6's divide.

    ⚠️ **One predicate, one place.** The season is characters 3 to 7 of a Retrosheet game id, and the
    era plan and the audit both need to ask. Two copies of that would be the shape this project meets
    most often — and the second copy was written the same day the first one was.
    """
    return int(entry.game_id[3:7]) < DIVIDE


def era_quota(days: int) -> tuple[int, int]:
    """How many boards each side of 1950 may have: `(pre_1950, rest)`.

    ⚠️ **`floor`, not `round`.** A quota is a ceiling, so 150 days gives **7**, not 8 — rounding up
    would put the calendar one board over the rule it exists to keep.
    """
    pre = int(days * PRE_1950_SHARE)
    return pre, days - pre


def draw_size(days: int) -> int:
    """How many directions to draw per decade to cover `days` dates.

    ⚠️ **`ceil`, not `round`.** A margin that can round *down* is not a margin: at 149 days `round()`
    gives 14 per decade, below the measured 15% headroom, silently. (v38-P2-01)

    ⚠️⚠️ **Extracted so a test can call it, and that is not a style preference.** The first test of this
    computed `ceil(days * DRAW_MARGIN / 12)` in the assertion — so it tested `math.ceil` and passed
    happily with `round()` still in the builder. **An instrument supplying the property under test**,
    which is the failure `CLAUDE.md` records as the one that survives a full pass of checks. Caught by
    mutating `ceil` back to `round` and seeing nothing turn red.
    """
    return max(1, ceil(days * DRAW_MARGIN / 12))


def _hardest_target(
    loaded: Loaded, key: Ed25519PrivateKey, counts: Counter[str], refusals: Counter[str]
) -> Package | None:
    """The hardest target this board reaches, or nothing — counting the cause of every refusal.

    ⚠️ **Counted per cause, not per board.** One board can fail the erasure at twelve stalls and pass
    the gate at nine; a tally that only recorded the board's final outcome would report the pool as
    healthier than it is and would hide which check is doing the discarding.
    """
    for target in range(CEILING, FLOOR - 1, -1):
        attempt = produce(loaded, target, key, note=NOTE)
        counts[attempt.cause or "published"] += 1
        # ⚠️ **Per check, not per attempt.** A total says the gate refused N boards; this says *which*
        # layer did it. §22's four layers are only worth what they individually catch, and a gate that
        # refuses nothing at volume is a finding about the gate — recorded in `docs/reviews/todo.md`
        # after 235 attempts produced zero refusals.
        for refusal in attempt.refusals:
            refusals[refusal.split(":")[0].strip()] += 1
        if attempt.package is not None:
            return attempt.package
    return None


def _say(message: str) -> None:
    """Print and flush.

    ⚠️⚠️ **A long run that says nothing is indistinguishable from a hung one.** Python buffers stdout
    when it is not a terminal, so the first version of this printed *nothing at all* for minutes while
    it worked — and the operator watching it had no way to tell it from a stalled connection. The
    runbook (`docs/beta-0-plan.md` A5.2) requires every step to say what it prints when it is working;
    a step whose success looks like silence is a step nobody can tell failed.
    """
    print(message, flush=True)


def measure(per_decade: int, key: Ed25519PrivateKey) -> None:
    """How many directions a board costs, and which check spends them.

    ⚠️⚠️ **`per_decade`, not a total, and this argument was called `--directions` for one run.**
    `load()`'s `limit` is `SELECT TOP (?)` **per decade**, over `SEASON_WINDOW` — twelve decades today.
    So `--directions 12` asked for about 144 directions, not twelve, and the run was still going ten
    minutes later with nothing on screen. **A name that misdescribes a scale factor of twelve is the
    same defect as `gated: bool = False`**: read far more often than it is passed, and wrong in the
    direction that costs time.

    ⚠️ **This is a measurement and it prints a number that decides a spend**, so it says where the
    number came from: the sample size, the gate, and the caps in force. A figure without its
    provenance is the shape this project has had to correct twice.
    """
    _say(f"loading up to {per_decade} directions per decade, gate {ZERO_DENSITY_GATE}")
    started = time.monotonic()
    sample = load(per_decade, gated=True, gate=ZERO_DENSITY_GATE)
    loaded_in = time.monotonic() - started
    _say(f"  {len(sample)} directions in {loaded_in:.1f}s ({loaded_in / max(len(sample), 1):.2f}s each)")

    counts: Counter[str] = Counter()
    refusals: Counter[str] = Counter()
    produced = 0
    started = time.monotonic()
    for item in sample:
        if _hardest_target(item, key, counts, refusals) is not None:
            produced += 1
    building = time.monotonic() - started

    _say("")
    _say(f"produced {produced} of {len(sample)} directions ({produced / max(len(sample), 1):.0%})")
    _say(f"  {building:.1f}s building, {building / max(len(sample), 1):.2f}s per direction")
    _say(f"  attempts by outcome: {dict(counts)}")
    _say(f"  refusals by check: {dict(refusals) or 'none'}")
    if produced:
        each = (loaded_in + building) / produced
        _say(f"  ~{each:.1f}s per published board; 150 boards ~= {each * 150 / 60:.0f} min")
    else:
        _say("  WARNING: nothing was produced, so nothing here sizes a batch")


@dataclass(frozen=True, slots=True)
class Batch:
    """What does not change from board to board: the key, where packages go, and the two tallies.

    ⚠️ A bundle rather than seven parameters. Grouping them is not tidiness — `counts` and `refusals`
    are accumulated across every board and passing them separately invites a caller to hand in a fresh
    one per board, which is how a total silently becomes a per-item count.
    """

    key: Ed25519PrivateKey
    out: Path
    counts: Counter[str]
    refusals: Counter[str]


def spread(total: int, count: int) -> set[int]:
    """Which of `total` date slots get one of `count` special boards, spaced evenly.

    ⚠️⚠️ **The quota is about what the player meets, not about a tally.** §6 asks for pre-1950 boards
    *one every three weeks* so that Ruth is an event; seven of them on seven consecutive days satisfies
    the count and defeats the intent entirely. **Counting is not placing**, and a quota implemented as a
    count only would have passed its own assertion.
    """
    if count <= 0:
        return set()
    return {round(index * total / count) for index in range(count)}


def _fill(
    sample: list[Loaded],
    dates: list[str],
    calendar: Calendar,
    batch: Batch,
    today: date,
) -> Calendar:
    """Produce a board for each date and **write the calendar after every one**.

    ⚠️⚠️ **Checkpointed, and it was not.** (A2.3) The calendar used to be written once after the loop,
    so a crash at board 140 of 150 left 140 signed packages on disk and **lost every assignment** — the
    work survived and the record of it did not. The short-run case working was not the same thing, and a
    successful run hid the difference.

    Writing a 26 KB file per board costs nothing against ten seconds of signing, and `extend()` is
    append-only, so each checkpoint is the previous calendar plus one row.

    ⚠️ **The producer skips a game the calendar has spent and the calendar refuses it anyway.** Two
    layers; the outer one exists so a run does not abort on the ~10% of draws that are the other
    direction of something, and it is not a substitute for the inner one.
    """
    filled = 0
    for item in sample:
        if filled == len(dates):
            break
        if item.game_id in games(calendar):
            batch.counts["duplicate game"] += 1
            continue
        package = _hardest_target(item, batch.key, batch.counts, batch.refusals)
        if package is None:
            continue
        write_package(batch.out / f"{package.puzzle_id}.json", package)
        entry = Entry(
            date=dates[filled],
            puzzle_id=package.puzzle_id,
            game_id=item.game_id,
            direction=item.offense_team,
            status="active",
            assigned=batch.out.name,
        )
        calendar = extend(calendar, (entry,), today=today)
        write(CALENDAR, calendar)
        filled += 1
    return calendar


MANIFEST = "manifest.json"
"""The generation manifest's filename. ⚠️ Named once so `write_manifest` can exclude it from its own
listing -- a literal spelled twice is how it came to list itself."""

MANIFEST_SCHEMA = 1
"""The manifest's version. **The manifest only, since 2026-08-24.**

⚠️⚠️ **This named the pointer's version too, and that was a recorded defect before it cost anything.**
One constant for two documents means a field added to either forces a version bump on both -- so the
pointer gaining `next_rotation` would have republished every manifest under a version 2 that describes
no change to it, and a reader checking manifests would have had to accept a number that meant nothing.

`docs/reviews/todo.md` carried it as *two on `MANIFEST_SCHEMA`*; this is where it came due.
"""

DAYS = "days"
"""Where the per-date pointers go, inside the generation.

⚠️⚠️ **These are not deployed to the served root.** A pointer is named by its date and a date is not a
secret, so anything that can add one day to today can read tomorrow's — which is the whole leak A4.2
exists to close (`docs/calendar.md`). **A daily job copies one of them out**, and only that one is
reachable. The job needs no key: every pointer is signed here, at generation."""


def write_pointers(calendar: Calendar, out: Path, key: Ed25519PrivateKey) -> int:
    """One signed pointer per date: *this puzzle is this date's, and the forge says so.*

    ⚠️⚠️ **The generation comes from `entry.assigned`, never from the run writing the pointers.**
    (v39-P1-01) This took the current generation as an argument and stamped it on **every** date, so the
    first top-up rewrote generation-A dates claiming their packages lived in B — and `gen B/<old-id>.json`
    does not exist, because the second run only produced the second run's boards. The runbook says
    several generations after a top-up are normal, so this was not an edge case: it was the second run.

    ⚠️ **The signature is what makes it worse rather than what catches it.** A pointer signs the pairing
    of a date to a package; a wrong pairing signed by the forge reads as authoritative, and the failure
    surfaces as a 404 on a legitimately assigned date. The parameter is gone rather than corrected, so
    there is no longer a way to pass the wrong one.

    ⚠️ **This is the client's whole set-integrity guarantee**, and it replaces a manifest listing every
    id. `sign_manifest`'s own docstring says a per-package signature proves each puzzle genuine and
    **only the manifest proves the set is** — so dropping the list without this would leave a swapped
    but genuine package undetectable. A pointer signs the *pairing*, which is what the client depends on.

    ⚠️ Voided dates get no pointer. There is nothing to serve on a date whose puzzle was withdrawn, and
    writing one would make a withdrawn assignment fetchable.
    """
    days = out / DAYS
    days.mkdir(parents=True, exist_ok=True)
    written = 0
    for entry in calendar:
        if entry.status != "active":
            # ⚠️⚠️ **Removed, not merely skipped.** Skipping was the first version and a test caught it:
            # a date voided *after* its pointer was written kept the old file on disk, and the daily
            # copy would have served a withdrawn puzzle. **Not writing something is not the same as
            # unpublishing it** — the same distinction §21 draws when it says a voided date keeps its
            # assignment and stops counting.
            (days / f"{entry.date}.json").unlink(missing_ok=True)
            continue
        # ⚠️ **The body comes from `boxscore_package.format`, and it used to be spelled here.** Two
        # scripts write this document; `write_reference_puzzles` writes the development batch. Their
        # *dating* is deliberately separate and their *field set* is one contract, and adding
        # `next_rotation` to this one and not the other is what proved it.
        # ⚠️ **The body comes from `boxscore_package.format`, and it used to be spelled here.** Two
        # scripts write this document; `write_reference_puzzles` writes the development batch. Their
        # *dating* is deliberately separate and their *field set* is one contract, and adding
        # `next_rotation` to this one and leaving the other at schema 1 is what proved it.
        #
        # ⚠️ `generation` is **the one that produced this package**, which after a top-up is not the one
        # being written now. `Entry.assigned` has recorded it since the calendar existed; the defect was
        # that nothing read it.
        #
        signed = sign_manifest(
            pointer_body(
                day=entry.date,
                puzzle_id=entry.puzzle_id,
                generation=entry.assigned,
            ),
            key,
        )
        (days / f"{entry.date}.json").write_text(json.dumps(signed, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        written += 1
    return written


def write_manifest(generation: str, out: Path, key: Ed25519PrivateKey) -> int:
    """The signed record that this generation is whole. **`serve` and the operator read it; the browser
    never does** (`docs/calendar.md`).

    ✔ **That second sentence became true at E1, 2026-08-23.** `serve/ui/phone/daily.js` fetched this
    file from the browser on both player pages until then; it reads `today.json` now and no code under
    `serve/` opens a manifest at all. `docs/calendar.md` owns the fact and this points at it.

    ⚠️ Built from the files on disk rather than from the calendar, deliberately: the calendar says what
    was *assigned* and this says what was *written*. Generating both from one list would make the
    manifest agree with the calendar by construction and check nothing about the deployment.
    """
    # ⚠⚠ **The manifest is excluded from its own listing, and it was not.** `out.glob("*.json")` finds
    # `manifest.json` too, so the document listed **`manifest` as a puzzle id**. It could not show up on
    # a first write -- the file does not exist yet -- and appeared the first time a generation was
    # signed twice, which `--republish` made possible on 2026-08-23.
    #
    # ⚠️ **A signed claim about the set, wrong about the set**, and wrong in a way that only a second
    # run produces: exactly the shape that survives every test written against a fresh directory.
    ids = sorted(path.stem for path in out.glob("*.json") if path.name != MANIFEST)
    document = sign_manifest({"generation": generation, "puzzles": ids, "schema": MANIFEST_SCHEMA}, key)
    (out / MANIFEST).write_text(json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return len(ids)


def audit(calendar: Calendar) -> None:
    """Assert what the calendar is, after it is built. **Never printed and believed.**

    ⚠️⚠️ **A3.5, and its absence is the whole reason the first inventory was wrong.** The run reported
    `assigned 150 of 150` — true about the count, silent about the composition — while the calendar was
    **34% pre-1950 against a 5% ceiling**. `CLAUDE.md` records the same shape from a weighted draw that
    produced zero boards at the easiest rung and reported quotas it had not met.

    ⚠️⚠️ **Weighting the draw is not enough on its own.** It makes the violation rarer, not impossible —
    and rarer is worse than never in one specific way: it stops being reproducible. **Any composition
    property the pipeline cannot see needs its own assertion here.** Era was only the first because it
    was the first with a written quota; a game published twice, a date assigned twice and a puzzle used
    twice are the same class, and all four are checked below.
    """
    if not calendar:
        return
    faults: list[str] = []

    pre = [entry for entry in calendar if _is_early(entry)]
    allowed, _rest = era_quota(len(calendar))
    if len(pre) > allowed:
        faults.append(f"{len(pre)} pre-{DIVIDE} boards of {len(calendar)}, above §6's ceiling of {allowed}")

    # ⚠⚠ **Placement, not only the count.** `spread()` exists because seven early boards on seven
    # consecutive days meet the ceiling and defeat what it is for — and until now nothing asserted that
    # it had done its job. This is the audit's own rule turned on the property it was missing.
    early_dates = sorted(date.fromisoformat(entry.date) for entry in pre)
    bunched = [
        (before.isoformat(), after.isoformat())
        for before, after in pairwise(early_dates)
        if (after - before).days < MINIMUM_EARLY_GAP
    ]
    if bunched:
        faults.append(
            f"pre-{DIVIDE} boards closer than {MINIMUM_EARLY_GAP} days: {bunched[:5]} "
            f"— §6 asks for one every three weeks, and the ceiling alone cannot say that"
        )

    for what, seen in (
        ("games", [entry.game_id for entry in calendar]),
        ("dates", [entry.date for entry in calendar]),
        ("puzzle ids", [entry.puzzle_id for entry in calendar]),
    ):
        if len(set(seen)) != len(seen):
            repeated = sorted({item for item in seen if seen.count(item) > 1})
            faults.append(f"{what} repeated: {repeated[:5]}")

    faults.extend(_inadmissible_boards(calendar))

    if faults:
        detail = "".join(f"\n  {fault}" for fault in faults)
        message = f"the calendar is not what it claims:{detail}"
        raise SystemExit(message)
    _say(f"  audit: {len(pre)} pre-{DIVIDE} of {len(calendar)} (ceiling {allowed}), no repeats")


def _era_plan(days: int, window: list[str], wanted: list[str], calendar: Calendar) -> tuple[list[str], list[str]]:
    """Which of the window's gaps get a pre-1950 board, and which get a modern one.

    ⚠⚠ **Both halves are derived from the whole window and then reconciled with what it already
    holds** (v39-P1-02). Deriving either from the gaps is what let a retry grant itself a second
    allowance:

    - **The slots** come from `spread(days, ...)`, so their offsets are the same on every run over the
      same window. Computed over the gaps they moved, and historical boards meant to arrive three weeks
      apart could land next to each other.
    - **The allowance** is the window's, minus the early boards already sitting in it. If a previous
      pass spent the lot, this one gets none — and the open early slots fall to the modern arm rather
      than going unfilled, because a date with no board is a failed run and a modern board there is
      merely not the plan.

    ⚠️ **The two halves defend each other, which is worth stating because it changes what the tests
    prove.** Reverting either one alone leaves the behaviour correct: with the offsets fixed there are
    no open early slots for a second allowance to land on, and with the allowance reconciled a drifting
    plan has nothing left to spend. **So no test goes red for a single line here** — what the three
    cases pin is the pair, and reverting both together (which is the code as it stood) turns two of them
    red with the finding's own numbers: seven early boards becoming thirteen, and gaps of `[21, 1, 20,
    1, ...]` days.
    """
    open_gaps = set(wanted)
    allowance, _rest = era_quota(days)
    planned = spread(days, allowance)
    already_early = sum(1 for entry in calendar if entry.date in set(window) and _is_early(entry))
    left = max(0, allowance - already_early)

    early: list[str] = []
    for offset in sorted(planned):
        if len(early) == left:
            break
        if window[offset] in open_gaps:
            early.append(window[offset])
    return early, [when for when in wanted if when not in set(early)]


def _inadmissible_boards(calendar: Calendar) -> list[str]:
    """Ask the **shipped population** whether it is clean, from disk and without a database.

    ⚠⚠ **This is what a rule living in a `WHERE` clause does not have.** The pool excludes these games
    and `produce()` refuses them, but neither leaves anything behind that can be asked afterwards —
    which is exactly how a seventeen-inning board reached 2026-11-01, signed and dated, and stayed there
    until something tried to read it. **`docs/excluded-games.md` is the register of what may not be here.**

    **What each fact is read from**, and the split is not arbitrary:

    - **innings, account, disposition** — `metadata`, written by `produce()` for this purpose.
    - **season** — the calendar's `game_id`, because §7 strips it from the published package. The same
      read `_is_early` does.

    ⚠️ **A package with no admissibility metadata is a fault, not a pass.** Those are boards produced
    before the facts were recorded, and *the absence of a check must not read as the check passing*.
    """
    faults: list[str] = []
    inventory = _ROOT / "forge" / "inventory"
    for entry in calendar:
        package = inventory / entry.assigned / f"{entry.puzzle_id}.json"
        where = f"{entry.date} {entry.puzzle_id}"
        if not package.is_file():
            # ⚠⚠ **A missing package is a fault, never a skip**, and skipping was the first version of
            # this line. There is no ordering that produces one legitimately: `_fill` writes the package
            # *before* it extends the calendar, so an entry always postdates its file. A skip would have
            # made every unreadable board audit clean -- the absence of the evidence reading as the
            # evidence passing, one more time, in the check written to stop exactly that.
            faults.append(f"{where} has no package under {entry.assigned}/")
            continue
        metadata = json.loads(package.read_text(encoding="utf-8")).get("metadata", {})
        innings, account = metadata.get("innings"), metadata.get("account")
        if innings is None or account is None:
            faults.append(f"{where} carries no admissibility metadata")
            continue
        if innings > MAX_INNINGS:
            faults.append(f"{where} is {innings} innings and the board draws {MAX_INNINGS}")
        if account != "Y":
            faults.append(f"{where} has a {account!r} game account, not a complete one")
        if metadata.get("disposition"):
            faults.append(f"{where} is {metadata['disposition']!r}: forfeit, protest or completed later")
        # ⚠️⚠️ **This applies the regular-season rule to every board, and `produce()` does not.** The
        # operator settled the boundary on 2026-08-24: 2020 onward, **regular season only**, never the
        # postseason. `inadmissible()` can honour the second half because `Loaded` carries
        # `source_type`; **the metadata here does not, so this check cannot tell the two apart.**
        #
        # ⚠️ **What makes it sound today, stated rather than assumed:** this producer draws no
        # postseason games at all — there is no postseason path in it, and every board it has ever
        # written is regular season. So a 2020+ extra-inning board here *is* a fault.
        #
        # ⚠️⚠️ **What would make it wrong, so it is not discovered by a false fault:** the day the batch
        # draws postseason games, a legitimate 2020+ postseason extra-inning board is flagged here and
        # the build stops on a good board. Closing that needs the postseason fact carried in the
        # metadata, which is a §7 question about what a published package may say — a postseason flag
        # narrows the game to 0.6% of the pool, which is the kind of hint §7 strips `season` to avoid.
        # `docs/excluded-games.md` §2 carries it as owed.
        if innings > REGULATION_INNINGS and int(entry.game_id[3:7]) >= AUTOMATIC_RUNNER_FROM:
            faults.append(f"{where} is an extra-inning game from the automatic-runner era")
    return faults


def _publish(calendar: Calendar, out: Path, key: Ed25519PrivateKey) -> None:
    """Audit the calendar, then sign the two documents that make a generation servable.

    ⚠⚠ **The order is the point and it is why this is one function.** The manifest and the pointers
    are signed statements that a set is whole and that a date names a package; writing either over a
    calendar that failed its quotas would be the forge asserting a wrong set is right. `build()` and
    `replace_dates()` both end here so there is no second ordering to get wrong.
    """
    audit(calendar)
    packages = write_manifest(out.name, out, key)
    pointers = write_pointers(calendar, out, key)
    _say(f"  manifest: {packages} packages; {pointers} dated pointers in {DAYS}/")


def republish(key: Ed25519PrivateKey) -> None:
    """Re-sign the newest generation's manifest and the whole calendar's pointers. **Writes no board.**

    ⚠⚠ **For the run that produced boards and then failed its audit**, which is not hypothetical: the
    2026-08-23 replacement wrote five packages and five calendar entries, then `audit()` refused the run
    because 145 *other* boards carried no admissibility metadata. Correct refusal, and it left a
    generation on disk with no manifest and no pointers -- servable content nothing points at.

    ⚠️ **Recovery is a command rather than a repair by hand.** The alternative was writing the two
    documents from a shell, which signs them outside the one place that audits first.
    """
    inventory = _ROOT / "forge" / "inventory"
    generations = sorted(path for path in inventory.iterdir() if path.is_dir())
    if not generations:
        message = f"no generation under {inventory}"
        raise SystemExit(message)

    calendar = read(CALENDAR)
    audit(calendar)

    # ⚠⚠ **Every generation's manifest, not only the newest one.** A manifest says *this generation is
    # whole* and is built from the files on disk, so a generation that **lost** a package -- which is
    # what `--replace` leaves behind, since the withdrawn board is deleted -- carries a signed document
    # naming a file that is not there. Re-signing only the newest one would leave that standing.
    for generation in generations:
        _say(f"  {generation.name}: {write_manifest(generation.name, generation, key)} packages")

    # ⚠️ **The pointers go in the newest**, because that is where the daily job looks and because
    # `write_pointers` writes the whole calendar's worth: each entry names its own generation, so one
    # complete set in one place is correct and several partial sets are not.
    pointers = write_pointers(calendar, generations[-1], key)
    _say(f"  {generations[-1].name}: {pointers} dated pointers in {DAYS}/")


ADMISSIBILITY = ("innings", "account", "disposition")

ADDED_BY_SCHEMA_6 = ("game_id",)
"""What schema 6 adds to `reveal`, named so `restamp` can tell an addition from a different board.

⚠️⚠️ **Without this the restamp refuses all 150.** `_refuse_a_different_board` compares field by field
and treats any difference as a finding about determinism — correctly, because writing over a package
that came back different would turn a re-signing pass into an unlogged regeneration of the artefact §21
calls irreproducible. **A schema addition is the one difference that is expected**, so it is named here
rather than the check being loosened.

⚠️ It is a tuple and not a boolean for the same reason `ADMISSIBILITY` is: the next schema adds its own
fields, and a check that asked *is the schema different* would wave through a board that changed for
some other reason at the same time.
"""
"""The facts `produce()` records so the population can be audited from disk (`docs/excluded-games.md`).
Named once, because `restamp()` has to subtract exactly this set to compare an old package with a new
one and a second spelling of it would compare the wrong thing."""


def restamp(key: Ed25519PrivateKey) -> None:
    """Record the admissibility facts on boards produced before there were any. **Same board, resigned.**

    ⚠⚠ **The rules arrived after 150 dates were assigned, which is the ordinary case.** A register of
    what may not ship (`docs/excluded-games.md`) is written when somebody notices, and the inventory
    always predates it. `audit()` refuses a package with no admissibility metadata -- correctly, because
    *the absence of the evidence must not read as the evidence* -- so every existing board has to be
    asked the question rather than assumed to pass it.

    ⚠⚠ **This is not a regeneration and §21 is not in play.** `produce()` is deterministic: the same
    game at the same target yields the same board, so no date changes its assignment and no puzzle id
    moves. What changes is that the package now carries the facts and is signed over them.

    ** ⚠⚠ And it is asserted, not assumed.** Every field of the rebuilt package is compared against the
    one on disk before it is written. A board that came back **different** is not restamped and not
    quietly replaced: it is a finding about determinism, and it stops the run. Writing it either way
    would turn a re-signing pass into an unlogged regeneration of the artefact §21 calls irreproducible.

    ⚠️ **A game the rules now refuse stops the run too**, naming the date, because that date needs
    `--replace` rather than a stamp -- and deciding that here would be this function replacing boards
    under the name of a metadata pass.
    """
    calendar = read(CALENDAR)
    inventory = _ROOT / "forge" / "inventory"
    stale: list[tuple[Entry, Path, dict[str, object]]] = []
    for entry in calendar:
        path = inventory / entry.assigned / f"{entry.puzzle_id}.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        # ⚠️⚠️ **Two reasons to be stale, and the schema one was missing.** This asked only whether the
        # admissibility facts were recorded, so once they were, the pass reported `0 of 150` and
        # returned — **a re-signing tool that could never be used again.** A package written under an
        # older schema is exactly as stale as one written before the facts existed: the reader in
        # `serve` refuses it, so it is a board that cannot be played.
        recorded = all(fact in document.get("metadata", {}) for fact in ADMISSIBILITY)
        current = document.get("schema") == SCHEMA_VERSION
        if recorded and current:
            continue
        stale.append((entry, path, document))
    _say(f"{len(stale)} of {len(calendar)} packages are missing facts or written under an older schema")
    if not stale:
        return

    wanted = {(entry.game_id, entry.direction): (entry, path, document) for entry, path, document in stale}
    sample = load(0, gated=True, gate=ZERO_DENSITY_GATE, also=tuple(sorted({key_[0] for key_ in wanted})))
    found = {(item.game_id, item.offense_team): item for item in sample}

    counts: Counter[str] = Counter()
    refusals: Counter[str] = Counter()
    done = 0
    for (game_id, direction), (entry, path, document) in sorted(wanted.items()):
        item = found.get((game_id, direction))
        if item is None:
            # ⚠⚠ **The pool refusing to hand the game back is the answer, not a gap.** The clauses that
            # exclude a forfeit, a protest, a tie or a partial account live in the query, so a board
            # already published from one of those games simply stops being loadable -- which is this
            # pass discovering exactly what it was written to discover.
            message = (
                f"{entry.date} {entry.puzzle_id}: the pool no longer offers {game_id} ({direction}), so it is "
                f"a game the rules now exclude (docs/excluded-games.md). Replace the date: "
                f"--replace {entry.date}"
            )
            raise SystemExit(message)
        package = _hardest_target(item, key, counts, refusals)
        if package is None:
            message = f"{entry.date} {entry.puzzle_id}: {game_id} ({direction}) no longer produces a board at all"
            raise SystemExit(message)
        rebuilt = json.loads(json.dumps(_as_document(package, path)))
        _refuse_a_different_board(entry, document, rebuilt)
        write_package(path, package)
        done += 1
        if done % 25 == 0:
            _say(f"  {done} of {len(stale)}")
    _say(f"restamped {done} packages, every one identical to what it replaced but for the schema's additions")
    _say(f"  attempts by outcome: {dict(counts)}")
    audit(read(CALENDAR))


def _as_document(package: Package, path: Path) -> dict[str, object]:
    """The package as it will be written, read straight back off disk. **Never a second serialiser.**

    ⚠️ Comparing an in-memory object against a parsed file compares two shapes, and the difference
    that matters -- what `write()` actually puts in the file -- is exactly what such a comparison cannot
    see. So this writes it and reads it, to a scratch name beside the original.
    """
    scratch = path.with_suffix(".restamp")
    write_package(scratch, package)
    document: dict[str, object] = json.loads(scratch.read_text(encoding="utf-8"))
    scratch.unlink()
    return document


def _metadata(document: dict[str, object]) -> dict[str, object]:
    """A package's metadata block, typed. `json.loads` hands back `object` and mypy is strict here."""
    block = document.get("metadata", {})
    return dict(block) if isinstance(block, dict) else {}


def _refuse_a_different_board(entry: Entry, before: dict[str, object], after: dict[str, object]) -> None:
    """Assert the rebuilt package is the published one plus the facts, and nothing else.

    ⚠⚠ **`signature` is excluded and that is the point of the exclusion being named.** The signature
    is over the content, so a package that gained a field must carry a different one; comparing it would
    make every board look changed and the check would be dropped as noisy. Everything the signature is
    *over* is compared instead, field by field, which is the stronger statement.
    """
    # ⚠️⚠️ **Stripped from BOTH sides, and it was stripped from one.** This was written for the original
    # pass, where the published package had no admissibility facts and the rebuilt one did — so removing
    # them from the new side made the two comparable. **They are on both sides now**, since the
    # 2026-08-23 restamp, and removing them from only the new one made every package differ by
    # construction: the schema-6 pass refused all 150 on its first board.
    #
    # ⚠️ These are the fields this pass is *allowed* to write, so they are excluded from the comparison
    # symmetrically rather than compared against an assumption about which side has them.
    old_metadata = {name: value for name, value in _metadata(before).items() if name not in ADMISSIBILITY}
    new_metadata = {name: value for name, value in _metadata(after).items() if name not in ADMISSIBILITY}
    # ⚠️ The rebuilt reveal minus what schema 6 adds, so an addition is not read as a different board.
    # Everything else in the block is still compared, including the printed boxscore.
    trimmed = dict(after)
    reveal = trimmed.get("reveal")
    if isinstance(reveal, dict):
        trimmed["reveal"] = {name: value for name, value in reveal.items() if name not in ADDED_BY_SCHEMA_6}
    differing = sorted(
        name
        # ⚠️ `schema` joins `signature` and `metadata` in the exclusions **because bumping it is the
        # point of the pass**. It is not unchecked: `write_package` stamps `SCHEMA_VERSION` and the
        # reader refuses anything else, so a wrong value cannot reach disk in the first place.
        for name in set(before) | set(trimmed)
        if name not in ("signature", "metadata", "schema") and before.get(name) != trimmed.get(name)
    )
    if old_metadata != new_metadata:
        differing.append("metadata")
    if differing:
        message = (
            f"{entry.date} {entry.puzzle_id}: rebuilding {entry.game_id} produced a different board "
            f"({', '.join(differing)}). Production is meant to be deterministic, so this is a finding "
            f"about the producer and not something to write over the published package."
        )
        raise SystemExit(message)


def _generation() -> Path:
    """A directory nothing has used yet, under `forge/inventory/`.

    ⚠⚠ **`gen{time():x}` alone collides at one-second resolution**, and a replacement run immediately
    after a build is exactly when that happens. Two runs sharing a directory are not a name clash: the
    manifest is built from *the files on disk*, so the second run would sign a document claiming the
    first run's packages are its own, and `Entry.assigned` would point two generations at one place. The
    suffix keeps the identity, which is the whole of what a generation is.
    """
    inventory = _ROOT / "forge" / "inventory"
    stamp = f"gen{int(time.time()):x}"
    for suffix in ("", *ascii_lowercase):
        out = inventory / f"{stamp}{suffix}"
        if not out.exists():
            out.mkdir(parents=True)
            return out
    message = f"{stamp} and every suffix of it already exist under {inventory}"
    raise SystemExit(message)


def _era_of(entry: Entry) -> tuple[int, int]:
    """The era window a replacement must be drawn from, so swapping a board does not move the mix.

    ⚠️ Four of the five boards withdrawn on 2026-08-23 were pre-1950 and §6 allows seven in a
    150-day calendar. Replacing them from the modern half would satisfy the *ceiling* while quietly
    spending the early allowance on nothing -- and `spread()` had already placed those four where the
    gap rule wanted them. **A replacement inherits its predecessor's era**, which keeps both properties
    without re-deriving either.
    """
    return (SEASON_WINDOW[0], DIVIDE - 1) if _is_early(entry) else (DIVIDE, SEASON_WINDOW[1])


def replace_dates(dates: list[str], key: Ed25519PrivateKey, today: date) -> None:
    """Withdraw a future date's board and put another in its place (§21).

    ⚠⚠ **Replacement, not voiding, and the difference is the date.** §21 splits on whether the
    puzzle has been played: a past date keeps its assignment and stops counting, a future one is simply
    swapped, because nobody has seen it. `calendar.replace()` refuses today and every day before it, so
    the distinction is enforced rather than remembered.

    ⚠⚠ **Nothing here says why a board is being withdrawn**, deliberately. The reasons live in
    `docs/excluded-games.md` and the *guarantee* lives in `produce()` and in `audit()` -- so a board
    withdrawn here cannot come back, whatever it was withdrawn for. If the pool still offered it, this
    would draw it again on the next line.
    """
    calendar = read(CALENDAR)
    by_date = {entry.date: entry for entry in calendar}
    missing = [when for when in dates if when not in by_date]
    if missing:
        message = f"not assigned, so there is nothing to replace: {missing}"
        raise SystemExit(message)

    out = _generation()
    batch = Batch(key, out, Counter(), Counter())
    done = 0
    for when in sorted(dates):
        going = by_date[when]
        era = _era_of(going)
        _say(f"{when}: withdrawing {going.puzzle_id} ({going.game_id}), drawing from {era[0]}-{era[1]}")
        # ⚠️ **A fresh draw per date**, not one sample spread across them: the eras differ board by
        # board here, where a build's two draws each cover many dates.
        for item in load(REPLACEMENT_DRAW, gated=True, gate=ZERO_DENSITY_GATE, window=era):
            if item.game_id in games(calendar):
                batch.counts["duplicate game"] += 1
                continue
            package = _hardest_target(item, batch.key, batch.counts, batch.refusals)
            if package is None:
                continue
            write_package(out / f"{package.puzzle_id}.json", package)
            calendar = replace(
                calendar,
                Entry(
                    date=when,
                    puzzle_id=package.puzzle_id,
                    game_id=item.game_id,
                    direction=item.offense_team,
                    status="active",
                    assigned=out.name,
                ),
                today=today,
            )
            write(CALENDAR, calendar)
            _say(f"  {when}: {package.puzzle_id} ({item.game_id}), {item.season}")
            done += 1
            break
        else:
            message = f"{when}: {REPLACEMENT_DRAW} directions from {era[0]}-{era[1]} and none produced a board"
            raise SystemExit(message)

    _say("")
    _say(f"replaced {done} of {len(dates)} dates")
    _say(f"  attempts by outcome: {dict(batch.counts)}")
    _say(f"  refusals by check: {dict(batch.refusals) or 'none'}")
    _publish(calendar, out, key)


REPLACEMENT_DRAW = 40
"""Directions drawn per date being replaced. ⚠️ **Per decade**, which is what `load()` takes: an era
window spans four decades or eight, so this is a floor on the draw rather than its size. Sized to make a
refusal mean *the pool has nothing here* rather than *the draw was small*, which is the distinction a
`SystemExit` on this path has to carry."""


def build(days: int, first: date, key: Ed25519PrivateKey, today: date) -> None:
    """Cover the `days`-day window starting at `first`, producing a board for each unassigned date.

    ⚠️ **The calendar on disk is the authority on what is spent** — which dates have an assignment and
    which games have been published (§7). A producer keeping its own set would be a second copy of the
    state that matters, and §21 makes that state irrecoverable if the two disagree.
    """
    calendar = read(CALENDAR)
    assigned = {entry.date for entry in calendar}
    spent = games(calendar)
    _say(f"{len(calendar)} dates already assigned, {len(spent)} games spent")

    # ⚠️⚠️ **A window, not a count of new dates**, and the first version was the second.
    #
    # `--days 150 --from 2026-09-01` means **those 150 days are covered**, not *add 150 more*. The
    # difference only shows on a re-run: under the old reading a short run that filled 4 of 10 would fill
    # 10 *more* on the retry and leave 14 assigned — so the command was not idempotent and the runbook's
    # "re-run it if it comes up short" would quietly overshoot.
    #
    # §21 wants the same call to be safe twice. A window makes that exact: the gaps inside it get filled
    # and nothing outside it is touched, however many times it runs.
    window = [(first + timedelta(days=offset)).isoformat() for offset in range(days)]
    wanted = [when for when in window if when not in assigned]
    # ⚠⚠ **The population is audited before the work, not only after it**, and the early return below
    # is the reason. A window that is already full does no building, writes no manifest and reaches no
    # `audit()` -- so over a finished calendar, which is the state an inventory spends most of its life
    # in, the register would never be asked. It is also the cheap ordering: an inadmissible board stops
    # the run in a second rather than after twenty minutes of signing.
    audit(calendar)
    if not wanted:
        _say(f"nothing to do: all {days} days from {first} are already assigned")
        return
    if date.fromisoformat(wanted[0]) <= today:
        message = f"{wanted[0]} is today or earlier; the calendar extends and never rewrites (§21)"
        raise SystemExit(message)

    # ⚠️⚠️ **Two draws, one per era, because a flat draw cannot meet a weighted quota.** `load()` takes
    # *n per decade*; over twelve decades that is a third of the sample before 1950, against §6's one in
    # twenty. The first 150-board calendar came out **34% pre-1950** exactly this way. Asking each side
    # for its own share is what "sample with the quota applied" means — the alternative is drawing flat
    # and hoping, which is what happened.
    #
    # ⚠️⚠️ **The plan is over the whole window, never over the gaps.** (v39-P1-02) Both the quota and
    # the spacing were computed from `wanted`, so **every retry granted itself a fresh 5%** and a fresh
    # spacing plan relative to whatever was left. The runbook's own recovery path — *re-run it if it
    # comes up short* — was therefore the way to exceed §6's ceiling: a 150-day window that had already
    # spent all seven of its early boards would allow two more across the 43 remaining gaps.
    #
    # ⚠️ **And the audit could not see it**, because it reads the whole calendar: an older window with
    # unused allowance leaves room for a malformed one to pass, and `_fill` has already checkpointed
    # every assignment to disk by the time it runs.
    early_dates, rest_dates = _era_plan(days, window, wanted, calendar)
    eras = (
        ("pre-1950", (SEASON_WINDOW[0], DIVIDE - 1), early_dates),
        ("1950 on", (DIVIDE, SEASON_WINDOW[1]), rest_dates),
    )
    _say(f"filling {len(wanted)} of the {days} days from {first}")
    _say(
        f"  era quota (§6): {len(early_dates)} pre-1950 of the window's {era_quota(days)[0]}, "
        f"{len(rest_dates)} from 1950 on"
    )

    out = _generation()
    batch = Batch(key, out, Counter(), Counter())
    started = time.monotonic()
    drawn = 0
    for name, era, dates in eras:
        if not dates:
            continue
        decades = max(1, (era[1] - era[0] + 1) // 10)
        per_decade = max(1, ceil(len(dates) * DRAW_MARGIN / decades))
        sample = load(per_decade, gated=True, gate=ZERO_DENSITY_GATE, window=era)
        drawn += len(sample)
        _say(f"  {name}: {len(sample)} directions for {len(dates)} dates ({per_decade} per decade)")
        calendar = _fill(sample, dates, calendar, batch, today)
    building = time.monotonic() - started

    filled = len(calendar) - len(assigned)
    _say("")
    _say(f"assigned {filled} of {len(wanted)} dates from {drawn} directions")
    _say(f"  packages in {out}")
    _say(f"  {building / 60:.1f} min building ({building / max(filled, 1):.1f}s per board)")
    _say(f"  attempts by outcome: {dict(batch.counts)}")
    _say(f"  refusals by check: {dict(batch.refusals) or 'none'}")
    _publish(calendar, out, key)

    if filled < len(wanted):
        # ⚠️⚠️ **The work is kept and the run still fails.** (v38-P2-01) This printed a warning and exited
        # zero, so a short calendar looked like a finished one — and the calendar is the artefact §21
        # makes irreproducible, read as serving truth.
        #
        # ⚠️ **Refusing to write at all was the other repair and it is wrong here.** A2.3 requires a run
        # that dies at board 400 of 450 not to start over; discarding a partial batch throws away twenty
        # minutes of signing and every package already on disk. `extend()` only adds dates that have no
        # entry, so **re-running fills the gaps** — the partial state is resumable by construction.
        #
        # So: keep the boards, keep the assignments, and **exit non-zero** so nothing downstream and
        # nobody reading a terminal mistakes a short run for a complete one.
        short = len(wanted) - filled
        message = (
            f"{short} of {len(wanted)} dates unfilled. The {filled} boards produced are written "
            f"and their dates are assigned, so re-running fills the gaps. If it comes up short again, "
            f"raise DRAW_MARGIN ({DRAW_MARGIN}) — the draw, not the yield, is what runs out."
        )
        raise SystemExit(message)


def main() -> None:
    # ⚠️⚠️ **Not `description=__doc__`, and that cost a `UnicodeEncodeError` on `--help`.** argparse
    # writes its help to stdout, this module's docstring is full of warning signs and section marks, and
    # a redirected stream on Windows is cp1252. **The fourth occurrence of the class `CLAUDE.md` records
    # — and the first one the existing guard could not see**, because that guard reads `print` arguments
    # and argparse prints the docstring itself. The guard grew; see
    # `test_reports_survive_a_redirected_stream.py`.
    parser = argparse.ArgumentParser(description="Produce daily puzzles and assign them to dates.")
    parser.add_argument("--measure", action="store_true", help="report the yield and build nothing")
    parser.add_argument(
        "--republish",
        action="store_true",
        help="re-sign the newest generation's manifest and every date's pointer; produces nothing",
    )
    parser.add_argument(
        "--restamp",
        action="store_true",
        help="record the admissibility facts on boards produced before they were recorded",
    )
    parser.add_argument(
        "--replace",
        default="",
        help="comma-separated future dates whose board is withdrawn and drawn again (§21)",
    )
    parser.add_argument("--days", type=int, default=150, help="how many dates to fill; five months of runway")
    parser.add_argument("--from", dest="first", default="", help="first date to fill, ISO; default tomorrow")
    # ⚠️ `--per-decade`, because that is what `load()` takes. See `measure()`.
    parser.add_argument(
        "--per-decade",
        dest="per_decade",
        type=int,
        default=2,
        help="directions to draw per decade; the pool spans twelve",
    )
    args = parser.parse_args()

    if args.measure:
        # ⚠️ **A throwaway key while measuring.** The gate verifies against the key's own public half, so
        # any pair satisfies it — and the real signing key has no business on the path of a measurement
        # (§33). Building for publication takes the real one.
        measure(args.per_decade, Ed25519PrivateKey.generate())
        return

    today = serving_date()
    if args.republish:
        republish(publication_key())
        return

    if args.restamp:
        restamp(publication_key())
        return

    if args.replace:
        replace_dates([when.strip() for when in args.replace.split(",") if when.strip()], publication_key(), today)
        return

    first = date.fromisoformat(args.first) if args.first else today + timedelta(days=1)
    build(args.days, first, publication_key(), today)


if __name__ == "__main__":
    main()
