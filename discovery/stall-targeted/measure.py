"""Erasing to a stall target instead of a chain target.

⚠️ **The variable changed and this is the first measurement taken against the right one.** Chain
length counts how long a solve is; a chain-10 board is ten subtractions in single file and was solved
in under a minute. What makes the board hard is the moment propagation runs dry — no equation left
with a single unknown — and something beyond direct substitution is needed to restart it. **That is a
stall, and the specification is five of them.**

A stall is a **transition**, not a bounding step. If propagation halts once and three consecutive
bounding steps follow before it flows again, the player stopped once and had to think. Counting the
steps would inflate the standard between 1.6 and 2.6 times, measured.

Footnotes are unknowns here. They cost no column and no pixel, they put unknowns *inside* the row
identity, and they take the stall ceiling from 5 to 15. Left-on-base is left out: it added nothing on
top of them.

**The question this answers:** how many blanks does five stalls actually require, and how much of the
pool reaches each target. If five stalls come out at twenty blanks rather than thirty-six, the board
the operator asked for already exists and nothing needs widening.

Read-only against DGL. Run from `forge/`.
"""

import random
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))

from measure import Loaded, load  # noqa: E402

from boxscore_forge.constraints import cell_values, footnote_cell, shape_of  # noqa: E402
from boxscore_forge.erasure import ORDERINGS, erasable  # noqa: E402
from boxscore_forge.identities import FOOTNOTE_COLUMNS, FAMILY_OF, find_violations  # noqa: E402
from boxscore_forge.solver import Solution, Technique, solve  # noqa: E402

TARGETS = tuple(range(5, 13))
GATE = 0.25
SEEDS = (1, 2)
SAMPLE_PER_DECADE = 4


@dataclass(frozen=True)
class Reached:
    target: int
    blanks: int
    stalls: int
    chain: int
    trivial: float
    families: frozenset[str]
    resolved_by: tuple[str, ...]
    positions: tuple[float, ...]


def stalls_in(solution: Solution) -> int:
    """Transitions into bounding, not bounding steps. One halt is one stall however long it lasts."""
    count = 0
    previous = False
    for step in solution.deductions:
        bounding = step.technique is Technique.BOUNDING
        count += bounding and not previous
        previous = bounding
    return count


def stall_detail(solution: Solution) -> tuple[tuple[str, ...], tuple[float, ...]]:
    """What broke each stall, and how far into the solve it happened.

    ⚠️ **Attributed to the first propagation step *after* the stall, not to the bounding step itself.**
    The earlier version recorded the bounding deduction's identity, and a bounding deduction has none
    — it narrows against a fixed point over the whole board rather than through one relation — so
    every stall came back as "bounding only" on 100% of boards. A figure that reaches 100% is almost
    never a figure; it is an instrument that does not distinguish.

    What a player experiences is: subtraction runs out, they bound something, and then **a particular
    identity opens up again**. That identity is the answer to "what did I have to see", and it is what
    this records.

    If every stall breaks the same way, that is a variety problem — by the tenth day the player knows
    what to reach for. If they vary, there is a character dimension nobody knew existed, sitting
    exactly where the thinking happens.
    """
    resolved: list[str] = []
    positions: list[float] = []
    steps = len(solution.deductions) or 1
    previous = False
    for index, step in enumerate(solution.deductions):
        bounding = step.technique is Technique.BOUNDING
        if bounding and not previous:
            positions.append(index / steps)
            resolved.append(_restarted_by(solution, index))
        previous = bounding
    return tuple(resolved), tuple(positions)


def _restarted_by(solution: Solution, stall_at: int) -> str:
    """The family of the first propagation deduction after the stall, or what happened instead."""
    for step in solution.deductions[stall_at:]:
        if step.technique is not Technique.BOUNDING and step.from_identity is not None:
            return FAMILY_OF[step.from_identity].value
    # A stall the board never recovers from by propagation: it bounded its way to the end. Named
    # rather than folded into the families, because it is a different thing and hiding it inside a
    # distribution is how the last version of this report said nothing.
    return "bounded to the end"


def erasable_with_footnotes(loaded: Loaded) -> list[str]:
    """The grid, plus the footnote line. No column, no pixel, and unknowns inside the row identity."""
    cells = list(erasable(loaded.direction))
    cells += [
        footnote_cell(index, field)
        for index in range(len(loaded.direction.batter_footnotes))
        for field in FOOTNOTE_COLUMNS
    ]
    return sorted(cells)


def erase_to_stalls(loaded: Loaded, seed: int) -> list[Reached]:
    """Stop when the stall target is reached, not when a chain length is."""
    shape = shape_of(loaded.direction)
    values = cell_values(loaded.direction)
    rng = random.Random(seed)  # noqa: S311
    candidates = ORDERINGS["row_first"](erasable_with_footnotes(loaded), loaded.direction, rng)

    found: list[Reached] = []
    wanted = list(TARGETS)
    erased: set[str] = set()
    for cell in candidates:
        trial = erased | {cell}
        solution = solve(shape, {name: value for name, value in values.items() if name not in trial})
        if not solution.is_complete:
            continue
        erased = trial
        stalls = stalls_in(solution)
        while wanted and stalls >= wanted[0]:
            resolved, positions = stall_detail(solution)
            found.append(
                Reached(
                    target=wanted.pop(0),
                    blanks=len(erased),
                    stalls=stalls,
                    chain=solution.chain_length,
                    trivial=solution.trivial_share or 0.0,
                    families=frozenset(family.value for family in solution.families_used),
                    resolved_by=resolved,
                    positions=positions,
                )
            )
        if not wanted:
            break
    return found


def report(results: list[Reached], attempts: int) -> None:
    print("")
    print("=== ERASING TO A STALL TARGET ===")
    print("The comparison that matters: five stalls used to arrive at 36 blanks by chasing chain.")
    heads = f"{'stalls':>8}{'boards':>8}{'of pool':>9}{'blanks p50':>12}{'p10-p90':>12}{'chain':>7}{'trivial':>9}"
    print(heads)
    for target in TARGETS:
        group = [r for r in results if r.target == target]
        if not group:
            print(f"{target:>8}{0:>8}{0.0:>8.0%}")
            continue
        blanks = sorted(r.blanks for r in group)
        span = f"{blanks[len(blanks) // 10]}-{blanks[9 * len(blanks) // 10]}"
        print(
            f"{target:>8}{len(group):>8}{len(group) / attempts:>8.0%}"
            f"{statistics.median(blanks):>12.0f}{span:>12}"
            f"{statistics.median([r.chain for r in group]):>7.0f}"
            f"{statistics.fmean([r.trivial for r in group]):>9.0%}"
        )
    print("  Trivial steps are context rather than a problem: they cost time and punish carelessness,")
    print("  which the operator is explicit about wanting. What was missing is the stalls.")

    print("")
    print("=== WHAT BREAKS EACH STALL, AND WHERE IN THE SOLVE ===")
    for target in (5, 8, 12):
        group = [r for r in results if r.target == target]
        if not group:
            continue
        families: Counter[str] = Counter()
        for board in group:
            families.update(board.resolved_by)
        total = sum(families.values()) or 1
        shown = ", ".join(f"{name} {count / total:.0%}" for name, count in families.most_common(4))
        early = statistics.fmean([p for board in group for p in board.positions] or [0.0])
        print(f"  {target:>2} stalls: {shown}")
        print(f"{'':>12}mean position in the solve: {early:.0%} of the way through")


def main() -> None:
    loaded = load(SAMPLE_PER_DECADE, gated=True, gate=GATE, max_batters=13, max_pitchers=4)
    sample = [item for item in loaded if not find_violations(item.direction)]
    print(f"{len(sample)} gated directions, gate {GATE:.0%}, footnotes erasable")
    print(f"decades: {dict(sorted(Counter((item.season // 10) * 10 for item in sample).items()))}")

    results = [found for item in sample for seed in SEEDS for found in erase_to_stalls(item, seed)]
    report(results, len(sample) * len(SEEDS))


if __name__ == "__main__":
    main()
