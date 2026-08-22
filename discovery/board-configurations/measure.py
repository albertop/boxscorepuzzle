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

from boxscore_domain import ZERO_DENSITY_GATE  # noqa: E402
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

GATE = ZERO_DENSITY_GATE
"""§5's zero-density gate, from the one place it is decided.

⚠️⚠️ **This read `GATE = 0.25` and the figures this script has published were measured at 0.25**, not at
the decided 0.30 — recorded here rather than in a commit message so a stale number is interpretable
instead of mysterious, and so a re-run's difference from it is explainable rather than a new
discrepancy. Fourteen instruments carried the literal; twelve of them, including this one, were
silently stricter than the pool the board actually draws from.

⚠️ **A stricter gate is not a smaller sample of the same thing.** It removes the zero-heavy boards,
which are the ones that compress least, so every figure about coverage, reachable stall targets or
chain length was taken over a livelier population than production. See `docs/reviews/todo.md` for the
two instruments whose disagreement this explains.
"""
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


CONFIGURATIONS = ("baseline", "footnotes>0", "footnotes", "footnotes+lob")
"""The arms, in the order that makes the report explain itself.

⚠️⚠️ **`footnotes>0` was added on 2026-08-22 and it is the whole reason this table can be read.**
Without it the comparison is *given* against *fully erasable* — **the exact comparison the pool run
superseded, missing the arm that refutes it** — and it prints a median of 16 stalls against 6 under a
heading reading *what each configuration buys*. Anyone reading the output without reading the warning
above it takes away a board ten stalls harder.

**With three arms the numbers do the explaining**: giving the footnotes and opening only the non-zero
ones come out the same, and the jump appears only when the zeros are opened too. **The whole
difference is zeros** — `PA = AB + BB` when `HBP`, `SF`, `SH` and `CI` are all nought for a batter, so
an erased term asks the solver to deduce a value that exists because the thing did not happen. 96% of
the pool's footnote terms are zero.

⚠️ **A label depends on someone reading it; an arm that reproduces the result does not.** The
docstring and the printed heading stay as well — they say the question is settled, and this shows why.

`discovery/zero-footnotes/` is where this comparison was run to decide it, with arms `all`,
`non_zero` and `given`. **That instrument kept the wrong arm and named it wrong, which is the evidence
of a correction; this one measured the same option without the arm that refutes it, which reproduces
the error.** The three names differ because the two files were written apart; what they compute does
not.
"""


def erasable_for(loaded: Loaded, configuration: str) -> list[str]:
    """Which cells this configuration allows to be unknown.

    The baseline is §6's board: the grid only, with the line score and the footnote line given.

    ⚠️⚠️ **The two other configurations measure an option that was decided against and whose production
    machinery was deleted**, and this function is where it survives — `erasable()` returns no footnote
    cell, and the lines below add them back. Their figures are **the zero-counting ones**: when `HBP`,
    `SF`, `SH` and `CI` are all zero for a batter the row identity is `PA = AB + BB`, so an erased term
    asks the solver to deduce a value that exists only because the thing did not happen. It does,
    correctly, recording a step each time — **96% of the pool's footnote terms are zero.**

    **So the `footnotes` arm reporting a median of 16 against the baseline's 6 is not a board that is
    ten stalls harder; it is a board with ten more zeros to type.** The pool run that settled this found
    coverage identical at every target with the cells open and given, field-for-field in 91% of paired
    trials.

    ⚠️ **Kept and labelled rather than deleted**, because the recorded figures belong to it and an
    instrument that cannot reproduce them is worse than one that can — but **nothing may draw a
    conclusion from those two arms**, and a reader of the comparison table has to be told that here
    rather than work it out. Whether they go is an operator decision, recorded in
    `docs/reviews/todo.md`.
    """
    cells = list(erasable(loaded.direction))
    opened = [
        footnote_cell(index, field)
        for index in range(len(loaded.direction.batter_footnotes))
        for field in FOOTNOTE_COLUMNS
    ]
    if configuration in {"footnotes", "footnotes+lob"}:
        cells += opened
    if configuration == "footnotes>0":
        # ⚠️ The arm that makes the other two readable: the same cells, minus the ones whose value is
        # nought. A zero term is not an unknown the player meets — it is a term that did not happen,
        # and the row identity closes without it.
        values = cell_values(loaded.direction)
        cells += [name for name in opened if values[name] != 0]
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
    # ⚠️ Printed with the table rather than left to the reader. Two of these three rows measure an
    # option that was decided against, on a measurement, and their numbers are inflated by the solver
    # deducing footnote zeros. See `erasable_for`.
    print("  ONLY `baseline` IS A LIVE CONFIGURATION -- the footnote line is given (section 6).")
    print("  Read `footnotes>0` against `footnotes`: same cells minus the ones whose value is nought.")
    print("  The gap between them is zeros the player never types, not difficulty. See erasable_for().")
    print("Ceiling is not chain length. Chain measures how long the board is, not how hard.")
    heads = (
        f"{'configuration':>16}{'boards':>8}{'blanks':>8}{'chain':>7}"
        f"{'stalls':>9}{'search p90':>12}{'resolution':>12}{'cycles':>8}"
    )
    print(heads)
    for configuration in CONFIGURATIONS:
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
    for configuration in CONFIGURATIONS:
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
        for configuration in CONFIGURATIONS
        for seed in SEEDS
        if (found := ceiling_for(item, configuration, seed)) is not None
    ]
    print(f"{len(results)} measured ceilings")
    report(results)


if __name__ == "__main__":
    main()
