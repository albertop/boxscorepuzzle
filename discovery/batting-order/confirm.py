"""Does the adoption hold on boards that can actually publish?

⚠️⚠️ **Everything that decided this was measured while no such board existed.** `boxscore_verify` had
no value-producing lineup step, so layer 3 refused anything leaning on the cyclic order. The 47 causal
deductions and the nine-of-eleven-with-no-filler describe **what the generator produces**, not what can
ship. The step exists now; this is the re-run.

⚠️⚠️ **PRE-REGISTERED. The categories and the reading are fixed here, before the run.**
`batting-order-reversal.md` records a subgroup chosen *after* seeing an aggregate producing the answer
the pressure pointed at. This file is written first so that cannot happen twice.

**The three categories, defined now:**

  gained    the direction reaches the target through the fallback and does not reach it plain
  lost      it reaches the target plain and not through the fallback
  common    both reach it

**What would confirm the adoption**, decided before any number is seen:

  1. `gained` stays materially above `lost` at the hard end, per seed rather than best-of-three.
     The earlier figure was +5 to +9 net per seed. **Anything at or below zero overturns it.**
  2. The gained boards still pass **all five certification layers**, not merely the generator.
     This is the number that did not exist before. **If most of them fail, the adoption is not
     supported by boards that can ship, whatever the generator says.**
  3. Causal deductions still outnumber division filler on the gained boards. The earlier split was
     nine of eleven with no filler at all. **A majority carrying filler overturns it.**

**What would NOT count as confirmation:** a favourable total that comes from a different subgroup, a
different seed treatment, or a target the earlier figures did not use. Those are the moves that
produced the reversal.

⚠️ **This is also the authoritative coverage instrument.** Coverage at eight stalls has had three
values — 33%, 50% and 79% — from three instruments that counted different things, and 60% from an
ad-hoc calculation that was never code. Here it is one definition, stated once: **a direction is
covered at a target when a board reaching that target passes every certification layer.** Anything
weaker is a number about the generator rather than about the product.

Read-only against DGL. Run from anywhere.
"""

import json
import statistics
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parents[1] / "discovery"))
from bootstrap import bootstrap  # noqa: E402

bootstrap()

from measure import Loaded, load, slot_references  # noqa: E402

from boxscore_domain import ZERO_DENSITY_GATE  # noqa: E402
from boxscore_forge.erasure import erase  # noqa: E402
from boxscore_forge.identities import find_violations  # noqa: E402
from boxscore_forge.identity import puzzle_id  # noqa: E402
from boxscore_forge.lineup_fallback import erase_with_lineup_fallback  # noqa: E402
from boxscore_forge.publish import to_board  # noqa: E402
from boxscore_forge.solver import Technique  # noqa: E402
from boxscore_package.format import Package  # noqa: E402
from boxscore_verify.verify import UNSIGNED, verify  # noqa: E402

TARGETS = (3, 4, 5, 6, 8)
SEEDS = (1, 2, 3)
SAMPLE_PER_DECADE = 4
"""The same draw as `arms.py`, so the figures are comparable to the ones being tested."""


@dataclass(frozen=True, slots=True)
class Row:
    """One direction, one seed, one target, one arm."""

    game: str
    offense: str
    season: int
    seed: int
    target: int
    arm: str
    """`plain` or `fallback` — the two the adoption is between. `on everywhere` is not a candidate."""
    reached: bool
    certified: bool
    """⚠️ **The field that did not exist before.** Passing every layer, not merely being produced."""
    rejected_by: str
    blanks: int
    stalls: int
    chain: int
    division: int
    causal: int
    """Deductions that combined terms, against `division` which read one total and divided by nine."""
    reason: str


def _package(loaded: Loaded, erased: frozenset[str] | None) -> Package:
    return Package(
        puzzle_id=puzzle_id(loaded.game_id, loaded.offense_team),
        puzzle=to_board(loaded.direction, erased),
        solution=to_board(loaded.direction, None),
        labels=loaded.labels,
        pitcher_labels=loaded.pitcher_labels,
        slot_references=slot_references(loaded.slots),
        offense_is_home=loaded.offense_is_home,
    )


def _steps(solution: object) -> tuple[int, int]:
    """Division filler against causal deductions.

    ⚠️ The split that decided the adoption, so it is counted the same way it was then: a
    `LINEUP_ARITHMETIC` step read one total and divided by nine and is filler; everything else combined
    terms the player had to find.
    """
    division = sum(1 for step in solution.deductions if step.technique is Technique.LINEUP_ARITHMETIC)
    return division, len(solution.deductions) - division


def _measure(loaded: Loaded, seed: int) -> list[Row]:
    rows: list[Row] = []
    slots = tuple(loaded.slots)
    for target in TARGETS:
        for arm in ("plain", "fallback"):
            if arm == "plain":
                puzzle = erase(loaded.direction, target_stalls=target, seed=seed)
                reason = "plain" if puzzle else "unreachable"
            else:
                puzzle, reason = erase_with_lineup_fallback(loaded.direction, slots, target_stalls=target, seed=seed)
            if puzzle is None:
                rows.append(
                    Row(
                        game=loaded.game_id,
                        offense=loaded.offense_team,
                        season=loaded.season,
                        seed=seed,
                        target=target,
                        arm=arm,
                        reached=False,
                        certified=False,
                        rejected_by="",
                        blanks=0,
                        stalls=0,
                        chain=0,
                        division=0,
                        causal=0,
                        reason=reason,
                    )
                )
                continue
            # ⚠⚠ Every layer, not a subset. A board the generator likes and the verifier refuses is
            # exactly what the earlier figures could not distinguish.
            verdict = verify(_package(loaded, puzzle.erased), secret=UNSIGNED)
            division, causal = _steps(puzzle.solution)
            rows.append(
                Row(
                    game=loaded.game_id,
                    offense=loaded.offense_team,
                    season=loaded.season,
                    seed=seed,
                    target=target,
                    arm=arm,
                    reached=True,
                    certified=verdict.accepted,
                    rejected_by="" if verdict.accepted else f"{verdict.rejection.layer}/{verdict.rejection.fault}",
                    blanks=len(puzzle.erased),
                    stalls=puzzle.solution.stalls,
                    chain=puzzle.solution.chain_length,
                    division=division,
                    causal=causal,
                    reason=reason,
                )
            )
    return rows


def _covered(rows: list[Row], arm: str, target: int, seed: int | None = None) -> set[tuple[str, str]]:
    """Directions covered: reached AND certified. One definition, used everywhere below."""
    return {
        (row.game, row.offense)
        for row in rows
        if row.arm == arm and row.target == target and row.certified and (seed is None or row.seed == seed)
    }


def report(rows: list[Row]) -> None:
    directions = {(row.game, row.offense) for row in rows}
    print("")
    print(f"{len(directions)} directions x {len(SEEDS)} seeds x {len(TARGETS)} targets x 2 arms")
    print("")
    print("=== COVERAGE: reached AND certified by all five layers, per direction on any seed ===")
    print(f"  {'target':>7}{'plain':>14}{'fallback':>14}{'gained':>9}{'lost':>7}")
    for target in TARGETS:
        plain = _covered(rows, "plain", target)
        fallback = _covered(rows, "fallback", target)
        print(
            f"  {target:>7}{f'{len(plain)}/{len(directions)}':>14}{f'{len(fallback)}/{len(directions)}':>14}"
            f"{len(fallback - plain):>9}{len(plain - fallback):>7}"
        )

    print("")
    print("=== THE SAME, PER SEED — the check that caught best-of-three bookkeeping last time ===")
    for target in (6, 8):
        for seed in SEEDS:
            plain = _covered(rows, "plain", target, seed)
            fallback = _covered(rows, "fallback", target, seed)
            print(
                f"  target {target}, seed {seed}: plain {len(plain):>2}, fallback {len(fallback):>2}, "
                f"gained {len(fallback - plain):>2}, lost {len(plain - fallback):>2}"
            )

    print("")
    print("=== !! CERTIFICATION: boards the generator produced and the verifier refused ===")
    print("  This is the number that did not exist when the adoption was decided.")
    for arm in ("plain", "fallback"):
        produced = [row for row in rows if row.arm == arm and row.reached]
        refused = [row for row in produced if not row.certified]
        share = len(refused) / len(produced) if produced else 0
        print(f"  {arm:<10}{len(produced):>5} produced, {len(refused):>4} refused ({share:.1%})")
        for fault, count in Counter(row.rejected_by for row in refused).most_common(4):
            print(f"       {count:>4}  {fault}")

    print("")
    print("=== THE GAINED DIRECTIONS AT 8 STALLS, WHICH IS WHERE THE CASE RESTS ===")
    gained = _covered(rows, "fallback", 8) - _covered(rows, "plain", 8)
    print(f"  {len(gained)} directions, against 11 before the verifier could certify them")
    print(f"  {'game':<14}{'off':<5}{'stalls':>7}{'chain':>7}{'blanks':>7}{'division':>9}{'causal':>7}")
    filler_free = 0
    for game, offense in sorted(gained):
        best = max(
            (r for r in rows if (r.game, r.offense) == (game, offense) and r.arm == "fallback" and r.certified),
            key=lambda r: r.stalls,
        )
        filler_free += best.division == 0
        print(
            f"  {game:<14}{offense:<5}{best.stalls:>7}{best.chain:>7}{best.blanks:>7}{best.division:>9}{best.causal:>7}"
        )
    print(f"  {filler_free} of {len(gained)} carry no division filler, against 9 of 11 before")

    print("")
    print("=== CAUSAL DEDUCTIONS AGAINST DIVISION FILLER, certified boards only ===")
    for arm in ("plain", "fallback"):
        certified = [row for row in rows if row.arm == arm and row.certified]
        division = sum(row.division for row in certified)
        causal = sum(row.causal for row in certified)
        share = division / max(causal + division, 1)
        print(f"  {arm:<10}{causal:>7} causal, {division:>6} division ({share:.1%} filler)")

    print("")
    print("=== STALL CEILING AND BLANKS, certified boards only ===")
    for arm in ("plain", "fallback"):
        certified = [row for row in rows if row.arm == arm and row.certified]
        if not certified:
            print(f"  {arm:<10}nothing certified")
            continue
        ceilings = [
            max(r.stalls for r in certified if (r.game, r.offense) == board)
            for board in {(r.game, r.offense) for r in certified}
        ]
        print(
            f"  {arm:<10}ceiling median {statistics.median(ceilings):.0f}, max {max(ceilings)}; "
            f"blanks median {statistics.median([r.blanks for r in certified]):.0f}"
        )


def main() -> None:
    # ⚠️ The pool rule applied with the slots, which is the whole point: without them
    # `find_violations` skips the batting-order check and the cohort would include the 35.
    sample = [
        item
        for item in load(SAMPLE_PER_DECADE, gated=True, gate=ZERO_DENSITY_GATE)
        if not find_violations(item.direction, tuple(item.slots))
    ]
    if not sample:
        message = "no directions survived the gate and the pool rule; the filters here are wrong"
        raise SystemExit(message)
    print(f"{len(sample)} directions through the gate and the batting-order pool rule")

    rows: list[Row] = []
    for number, loaded in enumerate(sample, start=1):
        for seed in SEEDS:
            rows.extend(_measure(loaded, seed))
        if number % 5 == 0:
            print(f"  {number}/{len(sample)} measured", flush=True)

    # Persisted before formatting: the rows are the expensive half and everything below can fail.
    (_HERE / "confirm.json").write_text(
        json.dumps([asdict(row) for row in rows], indent=1, sort_keys=True), encoding="utf-8", newline="\n"
    )
    print(f"wrote {len(rows)} rows to confirm.json before formatting anything")
    report(rows)


if __name__ == "__main__":
    if "--report-only" in sys.argv[1:]:
        report([Row(**row) for row in json.loads((_HERE / "confirm.json").read_text(encoding="utf-8"))])
    else:
        main()
