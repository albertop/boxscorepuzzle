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
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from math import ceil
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from boxscore_domain import ZERO_DENSITY_GATE  # noqa: E402
from boxscore_forge.calendar import Entry, extend, games, read, write  # noqa: E402
from boxscore_forge.pool import Loaded, load  # noqa: E402
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


def _entries(sample: list[Loaded], dates: list[str], spent: set[str], batch: Batch) -> list[Entry]:
    """Produce a board per date, skipping games the calendar has already spent.

    ⚠️⚠️ **The producer avoids duplicate games and the calendar enforces the rule.** `extend()` *raises*
    on a game already published, which is right for a caller making a mistake — but a batch draws the
    other direction of something about 10% of the time, and a run that aborted on the first one would be
    useless. So this skips them and the calendar's refusal stays as the last line of defence. **Two
    layers, and the outer one is not a substitute for the inner one.**
    """
    entries: list[Entry] = []
    for item in sample:
        if len(entries) == len(dates):
            break
        if item.game_id in spent:
            batch.counts["duplicate game"] += 1
            continue
        package = _hardest_target(item, batch.key, batch.counts, batch.refusals)
        if package is None:
            continue
        spent.add(item.game_id)
        # ⚠️ `write()` from the package format, not a hand-rolled dump. `as_json()` returns a mapping;
        # spelling the serialisation here would be a second definition of what a package file looks
        # like, and the signature is computed over exactly what that function writes.
        write_package(batch.out / f"{package.puzzle_id}.json", package)
        entries.append(
            Entry(
                date=dates[len(entries)],
                puzzle_id=package.puzzle_id,
                game_id=item.game_id,
                direction=item.offense_team,
                status="active",
                assigned=batch.out.name,
            )
        )
    return entries


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
    wanted = [
        when.isoformat()
        for offset in range(days)
        if (when := first + timedelta(days=offset)).isoformat() not in assigned
    ]
    if not wanted:
        _say(f"nothing to do: all {days} days from {first} are already assigned")
        return
    if date.fromisoformat(wanted[0]) <= today:
        message = f"{wanted[0]} is today or earlier; the calendar extends and never rewrites (§21)"
        raise SystemExit(message)

    per_decade = draw_size(days)
    _say(f"filling {len(wanted)} of the {days} days from {first}; drawing {per_decade} per decade")

    started = time.monotonic()
    sample = load(per_decade, gated=True, gate=ZERO_DENSITY_GATE)
    _say(f"  {len(sample)} directions in {time.monotonic() - started:.1f}s")

    out = _ROOT / "forge" / "inventory" / f"gen{int(time.time()):x}"
    out.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()
    refusals: Counter[str] = Counter()
    started = time.monotonic()
    entries = _entries(sample, wanted, spent, Batch(key, out, counts, refusals))
    building = time.monotonic() - started

    # ⚠️ The calendar refuses anything the producer let through — a duplicate game, a past date, a date
    # already assigned. It is the check no package can perform on itself, and it runs even though the
    # loop above tried to make it unnecessary.
    write(CALENDAR, extend(calendar, tuple(entries), today=today))

    _say("")
    _say(f"assigned {len(entries)} of {len(wanted)} dates from {len(sample)} directions")
    _say(f"  packages in {out}")
    _say(f"  {building / 60:.1f} min building ({building / max(len(entries), 1):.1f}s per board)")
    _say(f"  attempts by outcome: {dict(counts)}")
    _say(f"  refusals by check: {dict(refusals) or 'none'}")
    if len(entries) < len(wanted):
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
        short = len(wanted) - len(entries)
        message = (
            f"{short} of {len(wanted)} dates unfilled. The {len(entries)} boards produced are written "
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

    today = date.today()  # noqa: DTZ011 — the calendar's boundary is the local day, not an instant
    first = date.fromisoformat(args.first) if args.first else today + timedelta(days=1)
    build(args.days, first, publication_key(), today)


if __name__ == "__main__":
    main()
