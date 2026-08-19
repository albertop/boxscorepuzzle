"""How much difficulty each addition to the board actually buys.

⚠️ **Written after optimising the wrong variable for weeks.** Chain length measures *length*, not
difficulty: a chain-10 board is ten subtractions in single file, and the operator solved one in under
a minute. Pruning made that worse rather than better — handing a blank back as *given* does not
remove filler, it removes an unknown, and a board with fewer unknowns has more equations with exactly
one of them, which is a board that falls out by immediate subtraction.

**What makes a deduction puzzle hard is reaching a state where no equation has a single unknown**, so
two constraints have to be combined. The solver already records that: it is the bounding technique,
used exactly when propagation stalls. It was measured, reported, and set aside as a property instead
of pursued. This measures against it.

So the ceiling is defined four ways, none of them chain length:

  blanks       most unknowns a board carries with a unique, backtrack-free solution
  stalls       share of steps needing bounding — propagation had nothing left to subtract
  search       how hard the next move was to find, p90
  cycles       independent cycles in the constraint graph, the topology that caught the forest

Configurations 1 and 2 cost nothing: no column, no pixel. They make cells that are given today into
unknowns — the footnote line, and left-on-base. §6 gives them complete because the row identity does
not close without them, and that is exactly what makes them candidates: an unknown inside an identity
is worth more than an unknown outside one.

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

from boxscore_forge.constraints import (  # noqa: E402
    cell_values,
    equations,
    footnote_cell,
    independent_cycles,
    shape_of,
    team_footnote_cell,
)
from boxscore_forge.erasure import ORDERINGS, erasable  # noqa: E402
from boxscore_forge.identities import FOOTNOTE_COLUMNS, find_violations  # noqa: E402
from boxscore_forge.solver import Technique, solve  # noqa: E402

GATE = 0.25
SEEDS = (1, 2, 3)
SAMPLE_PER_DECADE = 4


@dataclass(frozen=True, slots=True)
class Ceiling:
    configuration: str
    blanks: int
    chain: int
    stalls: int
    bounding_steps: int
    search: float | None
    resolution: int | None
    cycles: int
    equations: int


def _stalls(solution: object) -> int:
    """How many times propagation ran dry, not how many bounding steps followed.

    A run of consecutive bounding steps is one stall: the player stopped once. The two numbers are
    reported side by side because the difference between them decides whether a threshold of five is
    the standard it sounds like.
    """
    count = 0
    previous_was_bounding = False
    for step in solution.deductions:  # type: ignore[attr-defined]
        is_bounding = step.technique is Technique.BOUNDING
        if is_bounding and not previous_was_bounding:
            count += 1
        previous_was_bounding = is_bounding
    return count


def erasable_for(loaded: Loaded, configuration: str) -> list[str]:
    """Which cells this configuration allows to be unknown.

    The baseline is §6's board: the grid only, with the line score and the footnote line given. The
    two free configurations open the footnote line and left-on-base, which sit *inside* identities
    rather than beside them.
    """
    cells = list(erasable(loaded.direction))
    if configuration in {"footnotes", "footnotes+lob"}:
        cells += [
            footnote_cell(index, field)
            for index in range(len(loaded.direction.batter_footnotes))
            for field in FOOTNOTE_COLUMNS
        ]
    if configuration == "footnotes+lob":
        cells.append(team_footnote_cell("left_on_base"))
    return sorted(cells)


def ceiling_for(loaded: Loaded, configuration: str, seed: int) -> Ceiling | None:
    """Erase as far as the board goes, then describe what the hardest version of it looks like."""
    shape = shape_of(loaded.direction)
    values = cell_values(loaded.direction)
    rng = random.Random(seed)  # noqa: S311
    candidates = ORDERINGS["row_first"](erasable_for(loaded, configuration), loaded.direction, rng)

    erased: set[str] = set()
    best = None
    for cell in candidates:
        trial = erased | {cell}
        solution = solve(shape, {name: value for name, value in values.items() if name not in trial})
        if not solution.is_complete:
            continue
        erased = trial
        best = solution
    if best is None:
        return None
    return Ceiling(
        configuration=configuration,
        blanks=len(erased),
        chain=best.chain_length,
        # The direct measure of "two constraints had to be combined": propagation found no equation
        # with a single unknown and the solver had to bound instead.
        # ⚠️ **The target variable, and it counts transitions rather than steps.** A stall is the
        # moment propagation runs dry and something beyond direct substitution is needed to restart
        # it. If it halts once and three consecutive bounding steps are needed before it flows again,
        # the player stopped **once** and had to think — counting three would inflate the number and
        # make a standard of five considerably softer than the specification asks for.
        stalls=_stalls(best),
        bounding_steps=sum(1 for step in best.deductions if step.technique is Technique.BOUNDING),
        search=best.ninetieth_percentile_search,
        resolution=best.ninetieth_percentile_resolution,
        cycles=independent_cycles(shape),
        equations=len(equations(shape)),
    )


def report(results: list[Ceiling]) -> None:
    print("")
    print("=== WHAT EACH CONFIGURATION BUYS, AGAINST THE BASELINE ===")
    print("Ceiling is not chain length. Chain measures how long the board is, not how hard.")
    heads = (
        f"{'configuration':>16}{'boards':>8}{'blanks':>8}{'chain':>7}"
        f"{'stalls':>9}{'search p90':>12}{'resolution':>12}{'cycles':>8}"
    )
    print(heads)
    for configuration in ("baseline", "footnotes", "footnotes+lob"):
        group = [r for r in results if r.configuration == configuration]
        if not group:
            continue
        searches = [r.search for r in group if r.search is not None]
        resolutions = [float(r.resolution) for r in group if r.resolution is not None]
        print(
            f"{configuration:>16}{len(group):>8}"
            f"{statistics.median([r.blanks for r in group]):>8.0f}"
            f"{statistics.median([r.chain for r in group]):>7.0f}"
            f"{statistics.median([r.stalls for r in group]):>9.0f}"
            f"{(statistics.median(searches) if searches else float('nan')):>12.2f}"
            f"{(statistics.median(resolutions) if resolutions else float('nan')):>12.0f}"
            f"{statistics.median([r.cycles for r in group]):>8.0f}"
        )
    print("")
    print("  stalls is the target variable and the count is what matters, not the share.")
    print("")
    print("=== HOW MANY TIMES THE BOARD MAKES THE PLAYER STOP ===")
    print("  The single most important number here. If the maximum is one or two, no erasure rule")
    print("  reaches five and the answer is a wider board rather than a different rule.")
    for configuration in ("baseline", "footnotes", "footnotes+lob"):
        group = [r for r in results if r.configuration == configuration]
        if not group:
            continue
        ordered = sorted(r.stalls for r in group)
        steps = sorted(r.bounding_steps for r in group)
        reaching = sum(1 for value in ordered if value >= 5) / len(ordered)
        print(
            f"  {configuration:>15}: stalls p50 {statistics.median(ordered):.0f}"
            f"  p90 {ordered[9 * len(ordered) // 10]:.0f}  max {ordered[-1]}"
            f"  |  none {sum(1 for v in ordered if v == 0) / len(ordered):.0%}"
            f"  five or more {reaching:.0%}"
        )
        print(
            f"  {'':>15}  bounding steps p50 {statistics.median(steps):.0f}  max {steps[-1]}"
            f"   <- counting these instead would inflate the standard"
        )


def main() -> None:
    loaded = load(SAMPLE_PER_DECADE, gated=True, gate=GATE)
    sample = [item for item in loaded if not find_violations(item.direction)]
    print(f"{len(sample)} gated directions, gate {GATE:.0%}")
    print(f"decades: {dict(sorted(Counter((item.season // 10) * 10 for item in sample).items()))}")

    results = [
        found
        for item in sample
        for configuration in ("baseline", "footnotes", "footnotes+lob")
        for seed in SEEDS
        if (found := ceiling_for(item, configuration, seed)) is not None
    ]
    print(f"{len(results)} measured ceilings")
    report(results)


if __name__ == "__main__":
    main()
