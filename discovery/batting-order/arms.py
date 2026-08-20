"""What the batting-order constraint is worth, and what has to be controlled for it to be worth it.

⚠️ **The correction this instrument exists to settle.** An earlier reading said the constraint determines
the whole PA column and called that the payoff. **Determining cells is filler, not difficulty.** If the
team's PA total is given, the player computes nine slots from one number — four turns and a remainder —
and types nine cells without thinking.

**With the total erased it works the other way.** Each slot bounds the next and the player has to chain,
and it bounds **in both directions**: knowing slots 3 and 6 puts 4 and 5 between them without fixing
either. That restricts without determining, which is what produces a stall.

**So the rule is good and what needs controlling is the total.** Three arms, and the one that answers the
question is `off` against `on_total_erasable`:

  off                today's solver
  on_total_given     constraint on, the PA total never erased
  on_total_erasable  constraint on, the PA total erasable like any other cell

The middle arm exists so the choice about the total is **visible rather than assumed**.

⚠️ **One canonical walk, filtered per arm.** The arms must differ in *treatment* and not in *trajectory*.
Ordering each arm's own candidate list separately would vary two things at once, and the report would read
exactly as clean as an honest one — a confound has no signature in the output and can only be prevented
here, while the instrument is being built.

⚠️ **The pool rule is applied.** 5 directions in 100,226 break the cycle; a constraint true 99.995% of the
time is a trap rather than a weaker rule, so the exceptions are excluded rather than tolerated. Measuring
without the rule would be measuring a constraint nobody would ship.

Read-only against DGL. Run from `forge/`.
"""

import random
import statistics
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))
sys.path.insert(0, str(_ROOT / "forge" / "src"))

import json  # noqa: E402

from measure import Loaded, load  # noqa: E402

from boxscore_forge.boxscore import Direction  # noqa: E402
from boxscore_forge.constraints import batting_total_cell, cell_values, shape_of  # noqa: E402
from boxscore_forge.erasure import DEFAULT_ORDERING, ORDERINGS, erasable  # noqa: E402
from boxscore_forge.identities import find_violations  # noqa: E402
from boxscore_forge.solver import Solution, Technique, solve  # noqa: E402

ARMS = ("off", "on_total_given", "on_total_erasable")
TARGETS = (3, 4, 5, 6, 8)
SAMPLE_PER_DECADE = 4
GATE = 0.30
SEEDS = (1, 2, 3)
PA_TOTAL = batting_total_cell("plate_appearances")
PA_COLUMN = ".plate_appearances"
SLOTS = 9


@dataclass(frozen=True, slots=True)
class Row:
    """One direction, one seed, one arm, one target."""

    game: str
    # ⚠️ **`offense` and `seed`, because without them the rows cannot be paired.** `Row` said it was
    # one direction, one seed, one arm and one target, and stored neither the seed nor the side. Three
    # seeds run per direction, so ambiguity was guaranteed rather than unlucky — and if both directions
    # of one game entered the sample their rows were indistinguishable. The expensive artifact could
    # not answer the one question it exists for: what did the three arms do on *this* walk.
    offense: str
    season: int
    seed: int
    arm: str
    target: int
    reached: bool
    blanks: int
    pa_blanks: int
    stalls: int
    chain: int
    families: str
    pa_by_propagation: int
    pa_by_bounding: int


def predicted(total: int) -> tuple[int, ...]:
    base, over = divmod(total, SLOTS)
    return tuple(base + 1 if slot <= over else base for slot in range(1, SLOTS + 1))


def obeys_the_cycle(loaded: Loaded) -> bool:
    """The pool rule, applied here so the constraint is exact on everything measured.

    ⚠️ Five directions in 100,226 break it. Measuring without this would be measuring a constraint the
    generator would never be allowed to use.
    """
    per_slot: dict[int, int] = {}
    for row, slot in zip(loaded.direction.batting, loaded.slots, strict=True):
        per_slot[slot] = per_slot.get(slot, 0) + row.plate_appearances
    ordered = tuple(value for _, value in sorted(per_slot.items()))
    return len(ordered) == SLOTS and ordered == predicted(sum(ordered))


def _canonical(direction: Direction, seed: int) -> list[str]:
    """The one walk every arm follows, in the generator's own default ordering."""
    rng = random.Random(seed)  # noqa: S311
    return list(ORDERINGS[DEFAULT_ORDERING](erasable(direction), direction, rng))


def _offered(arm: str, walk: list[str]) -> list[str]:
    """The same walk, filtered. ⚠️ Filtered, never re-ordered: that is the whole confound control."""
    if arm == "on_total_given":
        return [cell for cell in walk if cell != PA_TOTAL]
    return list(walk)


def _pa_techniques(solution: Solution, erased: set[str]) -> tuple[int, int]:
    """How the erased PA cells were reached.

    ⚠️ **This is the question that separates filler from difficulty.** If they fall to propagation the
    moment the total is known, the constraint bought arithmetic. If they need bounding, it bought
    reasoning.
    """
    propagation = bounding = 0
    for step in solution.deductions:
        if step.cell not in erased or not step.cell.endswith(PA_COLUMN):
            continue
        if step.technique is Technique.BOUNDING:
            bounding += 1
        else:
            propagation += 1
    return propagation, bounding


def _stalls(solution: Solution) -> int:
    count = 0
    previous = False
    for step in solution.deductions:
        bounding = step.technique is Technique.BOUNDING
        count += bounding and not previous
        previous = bounding
    return count


def _measure(loaded: Loaded, seed: int) -> list[Row]:
    direction = loaded.direction
    values = cell_values(direction)
    walk = _canonical(direction, seed)
    without = shape_of(direction)
    with_order = shape_of(direction, tuple(loaded.slots))

    rows: list[Row] = []
    for arm in ARMS:
        shape = without if arm == "off" else with_order
        offered = _offered(arm, walk)
        erased: set[str] = set()
        best: dict[int, Solution] = {}
        best_erased: dict[int, set[str]] = {}
        for cell in offered:
            trial = erased | {cell}
            solution = solve(shape, {name: value for name, value in values.items() if name not in trial})
            if not solution.is_complete:
                continue
            erased = trial
            reached = _stalls(solution)
            for target in TARGETS:
                if reached >= target and target not in best:
                    best[target] = solution
                    best_erased[target] = set(erased)

        for target in TARGETS:
            solution = best.get(target)
            got = best_erased.get(target, set())
            propagation, bounding = _pa_techniques(solution, got) if solution else (0, 0)
            rows.append(
                Row(
                    game=loaded.game_id,
                    offense=loaded.offense_team,
                    season=loaded.season,
                    seed=seed,
                    arm=arm,
                    target=target,
                    # ⚠️ A target no arm reached is a row, not a missing row. Dropping it would summarise
                    # the survivors and call the difference a null.
                    reached=solution is not None,
                    blanks=len(got),
                    pa_blanks=sum(1 for cell in got if cell.endswith(PA_COLUMN)),
                    stalls=_stalls(solution) if solution else 0,
                    chain=solution.chain_length if solution else 0,
                    families=",".join(sorted(family.value for family in solution.families_used))
                    if solution
                    else "",
                    pa_by_propagation=propagation,
                    pa_by_bounding=bounding,
                )
            )
    return rows


def _median(values: list[int]) -> float:
    return statistics.median(values) if values else 0.0


def _report(rows: list[Row]) -> None:
    print("")
    print("=== COVERAGE: SHARE OF BOARD-AND-SEED TRIALS REACHING EACH TARGET ===")
    print(f"  {'target':<8}" + "".join(f"{arm:>20}" for arm in ARMS))
    for target in TARGETS:
        line = f"  {target:<8}"
        for arm in ARMS:
            here = [row for row in rows if row.arm == arm and row.target == target]
            got = sum(1 for row in here if row.reached)
            line += f"{f'{got}/{len(here)} ({100.0 * got / max(len(here), 1):.0f}%)':>20}"
        print(line)

    print("")
    print("=== BLANKS AT EACH TARGET, AND HOW MANY OF THEM ARE PA CELLS (medians, reached only) ===")
    print(f"  {'target':<8}" + "".join(f"{arm:>20}" for arm in ARMS))
    for target in TARGETS:
        line = f"  {target:<8}"
        for arm in ARMS:
            here = [row for row in rows if row.arm == arm and row.target == target and row.reached]
            line += f"{f'{_median([r.blanks for r in here]):.0f} ({_median([r.pa_blanks for r in here]):.0f} PA)':>20}"
        print(line)

    print("")
    print("=== HOW THE ERASED PA CELLS WERE REACHED - the question that separates filler from work ===")
    print("  If they fall to propagation the moment the total is known, the constraint bought arithmetic.")
    print("  If they need bounding, it bought reasoning.")
    print(f"  {'arm':<20}{'PA by propagation':>20}{'PA by bounding':>18}{'share bounding':>16}")
    for arm in ARMS:
        here = [row for row in rows if row.arm == arm and row.reached]
        prop = sum(row.pa_by_propagation for row in here)
        bound = sum(row.pa_by_bounding for row in here)
        share = f"{100.0 * bound / (prop + bound):.1f}%" if prop + bound else "n/a"
        print(f"  {arm:<20}{prop:>20,}{bound:>18,}{share:>16}")

    print("")
    print("=== FAMILIES THE SOLUTION NEEDED (share of reached trials) ===")
    for arm in ARMS:
        here = [row for row in rows if row.arm == arm and row.reached]
        counted: Counter = Counter()
        for row in here:
            for family in row.families.split(","):
                if family:
                    counted[family] += 1
        parts = ", ".join(f"{name} {100.0 * count / len(here):.0f}%" for name, count in sorted(counted.items()))
        print(f"  {arm:<20} {parts}")

    print("")
    print("=== STALL CEILING PER BOARD (best reached, medians) ===")
    for arm in ARMS:
        ceilings = [
            max(
                (
                    row.stalls
                    for row in rows
                    if row.arm == arm and (row.game, row.offense) == board and row.reached
                ),
                default=0,
            )
            # By direction, not by game: a game is two boards and merging them would average a
            # winning offence with a losing one.
            for board in {(row.game, row.offense) for row in rows}
        ]
        print(f"  {arm:<20} median {_median(ceilings):.0f}, max {max(ceilings, default=0)}")


def main() -> None:
    sample = [
        item
        for item in load(SAMPLE_PER_DECADE, gated=True, gate=GATE)
        if not find_violations(item.direction) and obeys_the_cycle(item)
    ]
    if not sample:
        message = "no directions survived the gate and the cycle rule; the filters here are wrong"
        raise SystemExit(message)
    print(f"{len(sample)} directions x {len(SEEDS)} seeds x {len(ARMS)} arms, targets {TARGETS}")
    print("One canonical walk per (direction, seed), FILTERED per arm - never re-ordered.")

    rows: list[Row] = []
    for number, loaded in enumerate(sample, start=1):
        for seed in SEEDS:
            rows.extend(_measure(loaded, seed))
        if number % 5 == 0:
            print(f"  {number}/{len(sample)} measured", flush=True)

    # Persisted before formatting: the rows are the expensive half and everything below can fail.
    (_HERE / "arms.json").write_text(
        json.dumps([asdict(row) for row in rows], indent=1, sort_keys=True), encoding="utf-8", newline="\n"
    )
    print(f"wrote {len(rows)} rows to arms.json before formatting anything")
    _report(rows)

    print("")
    print("NOTE: the comparison that answers the question is `off` against `on_total_erasable`.")
    print("  `on_total_given` is there so the choice about the total is visible rather than assumed:")
    print("  with the total given the nine slots follow from one number and the player types filler.")


if __name__ == "__main__":
    main()
