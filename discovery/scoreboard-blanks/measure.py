"""Do the four totals the scoreboard already prints inflate the difficulty numbers?

`line_score.offense_hits = batting_totals.hits` and three siblings are **two-term** equations with one
unknown. The relation is real and the solver carries it in the `column_sum` family — but the player
reads the number off the scoreboard printed two centimetres above, and the solver records a deduction.
**A lookup counted as a deduction is a lookup counted as difficulty**, and every standing figure in this
project would carry it.

Found by rendering the phone board and reading it: the `H` total sat blank with `AWAY H 15` above it. On
the six reference packages every single board erased one of the four, 2.9% of blanks — too small a
sample to act on, which is what this measures properly.

⚠️ **How the ordering is kept stable, stated here at the point of comparison.**

The two arms have different candidate lists: `before` may erase the four, `after` may not. Ordering each
list separately would let the arms differ in *trajectory* as well as in *treatment* — a shared cell
could be reached at a different point in the walk — and that is the confound this project has produced
twice, most recently in a ladder whose report read exactly as clean as an honest one.

So the canonical order is computed **once per (direction, seed), over the union**, and the `after` arm
takes that same order **filtered**. Every cell both arms can erase keeps its relative position by
construction. A confound has no signature in the output, so this cannot be checked afterwards by reading
the numbers; it is only prevented here, by how the instrument is built.

⚠️ **The comparison must be able to show no difference.** 2.9% of blanks is small and the honest
expectation is that little moves. A null is a result — what must not happen is reporting one without
both arms having run on the same boards, which is why every row carries both and the per-board changed
count is printed rather than only the medians.

Read-only against DGL. Run from `forge/`.
"""

import contextlib
import io
import json
import os
import secrets
import statistics
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

NL = chr(10)
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))

from measure import load  # noqa: E402

from boxscore_forge import erasure  # noqa: E402
from boxscore_forge.erasure import SCOREBOARD_DUPLICATES, erase  # noqa: E402
from boxscore_forge.identities import find_violations  # noqa: E402

SAMPLE_PER_DECADE = 6
GATE = 0.25
SEEDS = (401, 402)
TARGETS = (5, 8, 11, 14, 17)
"""Stratified across the range the ladder uses, so *whether they cluster at any stall target* is
answerable rather than assumed."""

RESULT_SCHEMA = 1


@dataclass(frozen=True, slots=True)
class Arm:
    """One board, one seed, one target, one treatment.

    ⚠️ **`reached` exists because failing to reach a target is the finding, not its absence.** This
    instrument used to return an empty list the moment either arm's `erase()` came back `None`, so a
    pair where the `before` arm reached a target *only because a scoreboard duplicate was erasable*
    vanished from the comparison entirely — the single strongest piece of evidence, converted into
    silence. The report would then have shown unchanged medians over the survivors and called it a null.

    That is the false-null failure this project has already built an instrument to prevent, arriving
    through the door that instrument left open. A null must stay data.
    """

    game: str
    seed: int
    target: int
    treatment: str
    reached: bool
    blanks: int
    chain: int
    stalls: int
    duplicates_erased: int


def _canonical(direction: object, seed: int) -> list[str]:
    """The union's order, computed once. Both arms walk it."""
    import random  # noqa: PLC0415

    union = sorted(set(erasure.erasable(direction)) | set(SCOREBOARD_DUPLICATES))
    return erasure.ORDERINGS[erasure.DEFAULT_ORDERING](union, direction, random.Random(seed))  # noqa: S311


def _measure(direction: object, game: str, seed: int, target: int) -> list[Arm]:
    order = _canonical(direction, seed)
    rows = []
    for treatment, allowed in (("before", set(order)), ("after", set(order) - set(SCOREBOARD_DUPLICATES))):
        # Both arms are handed the same walk, filtered. The ordering hook returns it untouched, so
        # nothing downstream can reorder one arm and not the other.
        candidates = [cell for cell in order if cell in allowed]
        original_erasable, original_orderings = erasure.erasable, dict(erasure.ORDERINGS)
        erasure.erasable = lambda _direction, _cells=candidates: list(_cells)
        erasure.ORDERINGS = dict(original_orderings)
        erasure.ORDERINGS[erasure.DEFAULT_ORDERING] = lambda cells, _direction, _rng: list(cells)
        try:
            puzzle = erase(direction, target_stalls=target, seed=seed)
        finally:
            erasure.erasable, erasure.ORDERINGS = original_erasable, original_orderings
        rows.append(
            Arm(
                game=game,
                seed=seed,
                target=target,
                treatment=treatment,
                reached=puzzle is not None,
                blanks=len(puzzle.erased) if puzzle else 0,
                chain=puzzle.solution.chain_length if puzzle else 0,
                stalls=puzzle.solution.stalls if puzzle else 0,
                duplicates_erased=len(puzzle.erased & set(SCOREBOARD_DUPLICATES)) if puzzle else 0,
            )
        )
    return rows


def report(rows: list[Arm]) -> None:
    before = {(r.game, r.seed, r.target): r for r in rows if r.treatment == "before"}
    after = {(r.game, r.seed, r.target): r for r in rows if r.treatment == "after"}
    shared = sorted(before.keys() & after.keys())

    print("=== HOW OFTEN A SCOREBOARD DUPLICATE IS ERASED, BEFORE THE FIX ===")
    print("  the four are batting_totals.R/H and pitching_totals.R/H, each equal to a line-score value")
    print(f"{'target':>8}{'boards':>9}{'with one':>11}{'share':>9}{'blanks':>9}{'as % of blanks':>17}")
    for target in TARGETS:
        at = [before[key] for key in shared if key[2] == target]
        if not at:
            print(f"{target:>8}{0:>9}{'-':>11}{'-':>9}{'-':>9}{'-':>17}")
            continue
        with_one = sum(1 for row in at if row.duplicates_erased)
        blanks = sum(row.blanks for row in at)
        erased = sum(row.duplicates_erased for row in at)
        print(f"{target:>8}{len(at):>9}{with_one:>11}{with_one / len(at):>9.0%}{blanks:>9}{erased / blanks:>17.1%}")

    # ⚠️ Reachability first, and unconditionally. If the exclusion costs coverage, that is the answer
    # — and it would be invisible in any table that summarises only the pairs where both arms produced a
    # board.
    print("")
    print("=== NOTE: REACHABILITY, BEFORE ANY SUMMARY OF WHAT REACHED ===")
    for target in TARGETS:
        keys = [key for key in shared if key[2] == target]
        was = sum(before[key].reached for key in keys)
        now = sum(after[key].reached for key in keys)
        lost = [key for key in keys if before[key].reached and not after[key].reached]
        gained = [key for key in keys if after[key].reached and not before[key].reached]
        print(
            f"  target {target:>3}: before {was}/{len(keys)}, after {now}/{len(keys)}, lost {len(lost)}, gained {len(gained)}"
        )

    print("")
    print("=== WHAT THE FIX MOVES, SAME BOARDS AND SAME WALK ===")
    print(f"{'target':>8}{'pairs':>7}{'chain':>16}{'stalls':>16}{'blanks':>16}{'boards changed':>16}")
    for target in TARGETS:
        # Only pairs where both arms produced a board can have their chain and stalls compared; the
        # ones that could not are counted above rather than dropped here.
        keys = [key for key in shared if key[2] == target and before[key].reached and after[key].reached]
        if not keys:
            continue
        moved = sum(
            1
            for key in keys
            if (before[key].chain, before[key].stalls, before[key].blanks)
            != (after[key].chain, after[key].stalls, after[key].blanks)
        )
        cells = []
        for field in ("chain", "stalls", "blanks"):
            was = statistics.median([getattr(before[key], field) for key in keys])
            now = statistics.median([getattr(after[key], field) for key in keys])
            cells.append(f"{was:g} -> {now:g}")
        print(f"{target:>8}{len(keys):>7}{cells[0]:>16}{cells[1]:>16}{cells[2]:>16}{f'{moved}/{len(keys)}':>16}")

    # ⚠️ The number a median cannot show. Two boards moving opposite ways leave every summary untouched,
    # and "nothing moved" read off medians is not a null — it is an instrument that cannot distinguish.
    print("")
    print("=== PER BOARD, BECAUSE A MEDIAN HIDES OPPOSITE MOVEMENTS ===")
    changed = Counter()
    for key in shared:
        for field in ("chain", "stalls", "blanks"):
            if getattr(before[key], field) != getattr(after[key], field):
                changed[field] += 1
    print(f"  {len(shared)} pairs compared")
    if not changed:
        print("  not one pair changed on any field. The null is a real null.")
    for field, count in changed.most_common():
        print(f"  {field}: {count} of {len(shared)} pairs changed ({count / len(shared):.0%})")

    print("")
    print("=== A HANDFUL OF PAIRS, RENDERED RATHER THAN SUMMARISED ===")
    print("  any measurement producing a distribution also produces examples checked by eye")
    for key in [key for key in shared if before[key].duplicates_erased][:6]:
        b, a = before[key], after[key]
        print(
            f"  {key[0]} seed {key[1]} target {key[2]}: "
            f"blanks {b.blanks}->{a.blanks}, chain {b.chain}->{a.chain}, stalls {b.stalls}->{a.stalls}"
        )


def _git(*arguments: str) -> str:
    """Git output, or `unknown`.

    ⚠️ **A `# noqa` was inserted after the argument list and commented out the rest of the call.**
    `capture_output=True, text=True, check=True, timeout=10` became part of the comment, so git wrote to
    the terminal and `.stdout` was `None` — and the run died in the stamp after seventy-two boards had
    been measured. Ruff passed, because the result is valid syntax. **Ruff is not running the code**, and
    the rule this broke is written down: verify against the real artifact before spending an hour of
    compute against it.

    Each argument on its own line now, so nothing can be swallowed by a trailing comment.
    """
    try:
        return subprocess.run(  # noqa: S603
            ["git", "-C", str(_ROOT), *arguments],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return "unknown"


def provenance(directions: int, pairs: int) -> str:
    revision = _git("rev-parse", "--short", "HEAD")
    dirty = _git("status", "--porcelain", "--untracked-files=all")
    return "\n".join(
        [
            "=== WHAT PRODUCED THIS ===",
            f"  result schema      {RESULT_SCHEMA}",
            f"  revision           {revision}",
            f"  tree               {'clean' if dirty == '' else f'{len(dirty.splitlines())} files dirty'}",
            f"  sample             {directions} directions, {SAMPLE_PER_DECADE} per decade, gate {GATE:.0%}",
            f"  seeds              {SEEDS}; targets {TARGETS}",
            f"  pairs              {pairs}",
            "  ordering           one canonical walk per (direction, seed) over the union, filtered",
            "                     for the `after` arm, so shared cells keep their relative order",
            "COMPLETE",
        ]
    )


def main() -> None:
    out = _HERE / "results.txt"
    sample = [
        item
        for item in load(SAMPLE_PER_DECADE, gated=True, gate=GATE)
        if not find_violations(item.direction)
    ]
    if not sample:
        message = f"no directions survived the {GATE:.0%} gate"
        raise SystemExit(message)
    print(f"{len(sample)} gated directions", flush=True)

    rows: list[Arm] = []
    for number, item in enumerate(sample, start=1):
        for seed in SEEDS:
            for target in TARGETS:
                rows.extend(_measure(item.direction, item.game_id, seed, target))
        if number % 10 == 0:
            print(f"  {number}/{len(sample)} boards, {len(rows) // 2} pairs", flush=True)

    # ⚠️ **The rows go to disk before anything is formatted.** The first run of this instrument measured
    # all seventy-two boards and then died inside the stamp, and every pair was lost because the report
    # had not been written yet. Compute is the expensive part and formatting is the fragile part; they
    # should not share a failure.
    raw = _HERE / "rows.json"
    raw.write_text(json.dumps([asdict(row) for row in rows], indent=1, sort_keys=True), encoding="utf-8", newline=NL)
    print(f"{len(rows)} rows saved to {raw}", flush=True)

    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        report(rows)
        print("")
        print(provenance(len(sample), len(rows) // 2))
    text = captured.getvalue()
    print(text)
    pending = out.with_name(f"{out.name}.pending-{os.getpid()}-{secrets.token_hex(4)}")
    try:
        pending.write_text(text, encoding="utf-8")
        pending.replace(out)
    finally:
        pending.unlink(missing_ok=True)
    print(f"written to {out}")


if __name__ == "__main__":
    main()
