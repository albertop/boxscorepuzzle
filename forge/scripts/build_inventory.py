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

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from boxscore_domain import ZERO_DENSITY_GATE  # noqa: E402
from boxscore_forge.calendar import Calendar, Entry, extend, games, read, write  # noqa: E402
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
from boxscore_package.format import Package  # noqa: E402
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
03:00 Eastern and midnight Pacific, where nobody in the contiguous states is at a board.

⚠️ **An offset, not `America/Los_Angeles`.** A named zone buys one hour of alignment between 03:00 and
04:00 Eastern — hours nobody is playing, so the drift it exists to prevent has nothing to prevent — and
costs a 23-hour day, a 25-hour day, an ambiguous local time twice a year, and a timezone database.

⚠⚠ **It rests on §10's premise that the audience is US baseball fans**, which already carries the
payments decision and the English-first decision. If that premise moves, **re-derive this rather than
carrying the conclusion across**: 03:00 Eastern is 10:00 in Madrid.

⚠️ **`serve` will spell this number again when E1 builds the loader, and that is prescribed rather than
sloppy** — §33 forbids the two trees sharing code and `CLAUDE.md` puts a decided value in one module *per
tree, never one module shared*. Neither CI workflow runs the other's suite, so **no test can compare
them**; both sides cite `docs/calendar.md` instead."""


def serving_date(now: datetime | None = None) -> date:
    """Which date's puzzle is being served right now.

    ⚠⚠ **This was `date.today()`, and it was the local day of whoever ran the build.** §21 freezes any
    date at or before today, so that boundary decided whether a puzzle already in front of players could
    be replaced — and it was answering with the operator's own calendar.

    **It was safe, for a reason that is not a guarantee:** Madrid runs nine or ten hours ahead of UTC-8,
    so the boundary was always *ahead* of the serving day and froze conservatively. **That is a fact
    about where the operator is sitting.** The same build from Los Angeles at 23:00 puts the boundary
    *behind* the serving day, and the command that refuses to touch the past would let you replace a
    puzzle already being served.
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


MANIFEST_SCHEMA = 1

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
        pointer = sign_manifest(
            {
                "date": entry.date,
                "puzzle_id": entry.puzzle_id,
                # ⚠️ **The generation that produced this package**, which after a top-up is not the one
                # being written now. `Entry.assigned` has recorded it since the calendar existed; the
                # defect was that nothing read it.
                "generation": entry.assigned,
                "schema": MANIFEST_SCHEMA,
            },
            key,
        )
        (days / f"{entry.date}.json").write_text(json.dumps(pointer, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        written += 1
    return written


def write_manifest(generation: str, out: Path, key: Ed25519PrivateKey) -> int:
    """The signed record that this generation is whole. **`serve` and the operator read it; the browser
    never does** (`docs/calendar.md`).

    ⚠⚠ **That second sentence is E1b's end state and is not true today**, and `docs/calendar.md` owns
    the fact rather than this docstring restating it: `serve/ui/phone/daily.js` fetches this file from
    the browser, on both player pages, and follows it to the package. It is scaffolding E1 retires.

    ⚠️ Built from the files on disk rather than from the calendar, deliberately: the calendar says what
    was *assigned* and this says what was *written*. Generating both from one list would make the
    manifest agree with the calendar by construction and check nothing about the deployment.
    """
    ids = sorted(path.stem for path in out.glob("*.json"))
    document = sign_manifest({"generation": generation, "puzzles": ids, "schema": MANIFEST_SCHEMA}, key)
    (out / "manifest.json").write_text(json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8")
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

    out = _ROOT / "forge" / "inventory" / f"gen{int(time.time()):x}"
    out.mkdir(parents=True, exist_ok=True)
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
    audit(calendar)

    # ⚠️ Written after the audit, never before: a manifest over a calendar that failed its quotas would
    # be a signed statement that a wrong set is whole.
    packages = write_manifest(out.name, out, key)
    pointers = write_pointers(calendar, out, key)
    _say(f"  manifest: {packages} packages; {pointers} dated pointers in {DAYS}/")

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
    first = date.fromisoformat(args.first) if args.first else today + timedelta(days=1)
    build(args.days, first, publication_key(), today)


if __name__ == "__main__":
    main()
