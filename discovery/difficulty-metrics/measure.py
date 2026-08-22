"""What actually separates an easy board from a hard one.

Survival — whether propagation finishes at all — says a board is solvable, not how hard it was.
This measures the shape of the solution path instead, over real directions loaded from DGL:

  chain length      how many steps had to wait for the one before them
  frontier width    how many moves were available at each step; a width of one means the player
                    had to scan the whole board to find the only move there was
  families          which of the four kinds of reasoning the path actually needed

Plus two things specific to this board: how often a footnote term is load-bearing, and whether a
footnote whose row is ambiguous ever generates real work or always collapses on its own.

The question is whether these separate into bands or collapse into one pile. Bands make the weekly
difficulty curve a pool query; no bands means a different lever is needed. Thresholds are not set
here — those come from real solving times, not from anyone's estimate.

Read-only against DGL. Run from `forge/` so the package is importable.
"""

import random
import statistics
import sys
from collections import Counter
from pathlib import Path

# ⚠️ `pathlib`, not string surgery. (v36-P3-07) This split the path on the literal `discovery` and
# concatenated — in the single most-imported file in the tree, against the convention every sibling
# follows, and it would have produced nonsense the first time a directory above this one was named
# `discovery` too.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "forge" / "src"))

from boxscore_forge.boxscore import (
    Direction,
)
from boxscore_forge.constraints import (
    cell_values,
    shape_of,
)
from boxscore_forge.erasure import erasable
from boxscore_forge.errors import ContradictionError
from boxscore_forge.identities import (
    find_violations,
)

# ⚠️⚠️ **The pool moved to `boxscore_forge.pool` on 2026-08-22, and this is a re-export.**
#
# Everything below this block is research; everything named in it is the **pool rule**, which the
# production publisher depends on. It used to live here, which meant `write_reference_puzzles.py`
# imported the path that writes signed packages **out of a discovery script** — outside `mypy --strict`,
# inside the ratcheted lint tree, and free to be broken by any cleanup in this tree. See
# `docs/beta-0-plan.md`, A1.
#
# ⚠️ **A re-export, not a copy.** One definition with an alias. The alternative was rewriting 33 import
# lines across scripts that need a database to run — a change nobody could verify by running it, against
# `CLAUDE.md`'s rule that rewrites across call sites are verified by running and never by reading the
# diff. Every one of those scripts is untouched and keeps working.
#
# ⚠️ **`_parse_line_score` is in the list on purpose.** `discovery/innings/pool.py` imports it, so it is
# public in fact whatever the underscore says, and dropping it here would break that script silently at
# import time rather than loudly at review.
from boxscore_forge.pool import (
    ACCEPTED_SOURCES,
    CONNECTION,
    CONTRIBUTED,
    FIELDING_CODE,
    POSTSEASON,
    POSTSEASON_SOURCE,
    PROVENANCE_LITERAL,
    PROVENANCE_SOURCES,
    REGULAR,
    SEASON_WINDOW,
    SHAPE_CTE,
    TEAM_NAME_QUERY,
    Loaded,
    Season,
    _parse_line_score,
    eligibility,
    full_name,
    load,
    shape_cte,
    team_name,
    zero_density_clause,
)
from boxscore_forge.solver import Solution, solve

__all__ = [
    "ACCEPTED_SOURCES",
    "CONNECTION",
    "CONTRIBUTED",
    "FIELDING_CODE",
    "POSTSEASON",
    "POSTSEASON_SOURCE",
    "PROVENANCE_LITERAL",
    "PROVENANCE_SOURCES",
    "REGULAR",
    "SEASON_WINDOW",
    "SHAPE_CTE",
    "TEAM_NAME_QUERY",
    "Loaded",
    "Season",
    "_parse_line_score",
    "eligibility",
    "full_name",
    "load",
    "shape_cte",
    "team_name",
    "zero_density_clause",
]
"""Re-exported so `from measure import ...` keeps meaning what it meant. Ruff reads this list, so a
name dropped from it is a name that stops being importable — which is the point."""

ERASURE_COUNTS = (2, 4, 6, 8, 10, 12)
TRIALS_PER_COUNT = 15
AMBIGUITY_TRIALS = 20
TAIL_TRIM = 3
SEED = 20260817


def _sum(model: type, rows: tuple[object, ...], columns: tuple[str, ...]) -> object:
    return model(**{column: sum(getattr(row, column) for row in rows) for column in columns})


def leaned_on_a_footnote(direction: Direction, solution: Solution) -> bool:
    """Whether the solution used a row identity on a row that actually carries a footnote.

    A player has to notice the footnote is there before that row's identity is usable, and nine rows
    in ten have nothing in it. That is a difficulty signal distinct from how many cells are blank.

    Checked against the row rather than against what the deduction leaned on, because a footnote is
    always given: it is never deduced, so it never shows up as a dependency.
    """
    carrying = {
        index
        for index, footnotes in enumerate(direction.batter_footnotes)
        if footnotes.hit_by_pitch
        or footnotes.sacrifice_flies
        or footnotes.sacrifice_hits
        or footnotes.catcher_interference
    }
    return any(
        deduction.from_identity == "row_plate_appearances"
        and deduction.cell.startswith("batting[")
        and int(deduction.cell.split("[")[1].split("]")[0]) in carrying
        for deduction in solution.deductions
    )


def survey(sample: list[Loaded]) -> None:
    rng = random.Random(SEED)
    print("\n=== SOLUTION SHAPE BY ERASURE COUNT ===")
    print("erased  solved%  chain p50/p90/max   frontier min p50   mean frontier   footnote-needed%")
    rows_for_correlation: list[tuple[int, int, int]] = []

    bottleneck_counts: dict[int, Counter[int]] = {}
    attempts_per_puzzle: dict[int, float] = {}

    for count in ERASURE_COUNTS:
        chains: list[int] = []
        narrow_widths: list[int] = []
        mean_widths: list[float] = []
        bottlenecks: Counter[int] = Counter()
        family_sets: Counter[tuple[str, ...]] = Counter()
        solved = trials = footnote_needed = 0
        for loaded in sample:
            cells = erasable(loaded.direction)
            values = cell_values(loaded.direction)
            for _ in range(TRIALS_PER_COUNT):
                trials += 1
                erased = rng.sample(cells, count)
                puzzle = {k: v for k, v in values.items() if k not in erased}
                try:
                    solution = solve(shape_of(loaded.direction), puzzle)
                except ContradictionError:
                    continue
                if not solution.is_complete:
                    continue
                solved += 1
                chains.append(solution.chain_length)
                if solution.narrowest_frontier is not None:
                    narrow_widths.append(solution.narrowest_frontier)
                if solution.mean_frontier is not None:
                    mean_widths.append(solution.mean_frontier)
                if len(solution.deductions) > TAIL_TRIM:
                    # How often the board pinched, not just whether it ever did. One width-one step
                    # and six of them are very different solves and the minimum calls both "one".
                    bottlenecks[sum(1 for d in solution.deductions[:-TAIL_TRIM] if d.frontier == 1)] += 1
                family_sets[tuple(sorted(f.value for f in solution.families_used))] += 1
                if leaned_on_a_footnote(loaded.direction, solution):
                    footnote_needed += 1
                # Only boards long enough to have a frontier at all. Substituting a zero for the
                # ones that do not would put a fabricated value into the correlation.
                if solution.narrowest_frontier is not None:
                    rows_for_correlation.append((count, solution.chain_length, solution.narrowest_frontier))

        if not chains:
            print(f"{count:>6}  {0.0:>6.1f}%  no complete solutions")
            continue
        print(
            f"{count:>6}  {100.0 * solved / trials:>6.1f}%  "
            f"{_q(chains, 0.5):>5.0f}/{_q(chains, 0.9):>3.0f}/{max(chains):>3}   "
            f"{_q(narrow_widths, 0.0) if narrow_widths else 0:>11.0f} {_q(narrow_widths, 0.5) if narrow_widths else 0:>5.0f}   "
            f"{statistics.fmean(mean_widths) if mean_widths else 0:>13.2f}   "
            f"{100.0 * footnote_needed / max(solved, 1):>15.1f}%"
        )
        print(f"          families: {_top_families(family_sets)}")
        bottleneck_counts[count] = bottlenecks
        attempts_per_puzzle[count] = trials / max(solved, 1)

    _bottleneck_table(bottleneck_counts)
    _pool_cost(attempts_per_puzzle)
    _correlations(rows_for_correlation)
    _frontier_tail(sample, rng)


def _bottleneck_table(counts: dict[int, Counter[int]]) -> None:
    print("\n=== HOW OFTEN A BOARD PINCHES TO ONE MOVE (3-step tail trimmed) ===")
    print("erased   0     1     2     3    4+   mean")
    for erased, histogram in counts.items():
        total = sum(histogram.values()) or 1
        buckets = [100.0 * histogram[n] / total for n in range(4)]
        buckets.append(100.0 * sum(v for k, v in histogram.items() if k >= 4) / total)
        mean = sum(k * v for k, v in histogram.items()) / total
        print(f"{erased:>6}  " + "  ".join(f"{b:4.0f}%" for b in buckets) + f"  {mean:5.2f}")


def _pool_cost(attempts: dict[int, float]) -> None:
    print("\n=== WHAT EACH DIFFICULTY LEVEL COSTS THE POOL ===")
    print("  erased   attempts per valid puzzle")
    for erased, cost in attempts.items():
        print(f"  {erased:>6}   {cost:>6.2f}")
    print("\n  Illustration only — the mapping from weekday to erasure count is not decided.")
    print("  Taking one day each at 2, 4, 6, 8, 10 and 12 cells, a seven-day week with two easy days:")
    weekly = 2 * attempts[2] + attempts[4] + attempts[6] + attempts[8] + attempts[10] + attempts[12]
    print(f"    directions consumed per week : {weekly:.1f}")
    print(f"    per year                     : {weekly * 52:.0f}")
    print(f"    years of calendar from 55,024: {55024 / (weekly * 52):.1f}")


def _q(values: list[int], fraction: float) -> float:
    ordered = sorted(values)
    if fraction == 0.0:
        return float(ordered[0])
    return float(ordered[min(int(fraction * len(ordered)), len(ordered) - 1)])


def _top_families(counter: Counter[tuple[str, ...]]) -> str:
    total = sum(counter.values())
    return ", ".join(f"{'+'.join(k) or 'none'} {100.0 * v / total:.0f}%" for k, v in counter.most_common(4))


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or statistics.pstdev(xs) == 0 or statistics.pstdev(ys) == 0:
        return float("nan")
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / len(xs)
    return covariance / (statistics.pstdev(xs) * statistics.pstdev(ys))


def _correlations(rows: list[tuple[int, int, int]]) -> None:
    print("\n=== DO THE METRICS MOVE TOGETHER ===")
    erased = [float(r[0]) for r in rows]
    chain = [float(r[1]) for r in rows]
    frontier = [float(r[2]) for r in rows]
    print(f"  erasure count vs chain length   r = {_pearson(erased, chain):+.3f}")
    print(f"  erasure count vs frontier width r = {_pearson(erased, frontier):+.3f}")
    print(f"  chain length  vs frontier width r = {_pearson(chain, frontier):+.3f}")
    print("  (near +/-1 means one variable with three names; near 0 means independent levers)")


def _frontier_tail(sample: list[Loaded], rng: random.Random) -> None:
    """Whether the frontier distribution spikes at one because solutions narrow by exhaustion."""
    print("\n=== FRONTIER DISTRIBUTION, BY HOW MUCH OF THE TAIL IS TRIMMED ===")
    for trim in (1, 2, 3):
        widths: Counter[int] = Counter()
        for loaded in sample[:60]:
            cells = erasable(loaded.direction)
            values = cell_values(loaded.direction)
            for _ in range(TRIALS_PER_COUNT):
                erased = rng.sample(cells, 8)
                try:
                    solution = solve(shape_of(loaded.direction), {k: v for k, v in values.items() if k not in erased})
                except ContradictionError:
                    continue
                if not solution.is_complete or len(solution.deductions) <= trim:
                    continue
                widths[min(d.frontier for d in solution.deductions[:-trim])] += 1
        total = sum(widths.values()) or 1
        shape = ", ".join(f"{width}:{100.0 * count / total:.0f}%" for width, count in sorted(widths.items())[:6])
        print(f"  trimming {trim} step(s): {shape}")


def ambiguity(sample: list[Loaded], rng: random.Random) -> None:
    """⚠️ **Retired: this measured duplicate positions, not ambiguous footnote references.**

    It grouped rows by `loaded.labels` and erased the group's footnote cells as one ambiguous domain.
    That was sound while labels carried a suffix and a repeated label meant a shared lineup slot. It is
    not sound now: labels are bare positions, and **42.1% of repeated position labels span more than
    one slot**, so two `CF` rows are usually two men who never replaced each other. The experiment
    would build an artificial domain over unrelated rows and report the solver's reaction as footnote
    ambiguity — plausible percentages for a case the board does not contain.

    Its docstring described the opposite implementation, predicting no groups would be found. Left as a
    named refusal rather than deleted, so a reader who remembers it finds out why instead of finding
    nothing. The live question — whether an unassigned footnote resolves — belongs to
    `discovery/footnote-groups`, which groups by **slot** and reports per group size and term count.
    """
    del sample, rng
    message = "ambiguity() grouped by position label and no longer measures ambiguity; see discovery/footnote-groups"
    raise RuntimeError(message)


def main() -> None:
    # ⚠️ `gated=True` states what this call has always received (v36-P2-20). The flag did nothing
    # until 2026-08-21, so omitting it never meant ungated; naming it keeps this figure reproducible.
    sample = load(35, gated=True)
    balanced = [item for item in sample if not find_violations(item.direction)]
    print(f"loaded {len(sample)} directions, {len(balanced)} balance every identity")
    by_decade = Counter((item.season // 10) * 10 for item in balanced)
    print(f"decades: {dict(sorted(by_decade.items()))}")
    survey(balanced)


if __name__ == "__main__":
    main()
