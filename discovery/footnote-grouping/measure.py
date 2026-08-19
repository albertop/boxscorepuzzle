"""One footnote column against four.

Opening the per-batter footnote cells took the stall ceiling from 5 to 15 and the pool reaching five
stalls from 56% to 100%. But it costs **four columns** in the batting grid — HBP, SF, SH and CI.

**The cheaper alternative is one column carrying the row's footnote total**, so the row identity reads
`PA = AB + BB + footnotes` with one unknown per row instead of four. The breakdown by type is shown at
the end with the real boxscore, where telling a sacrifice from a hit-by-pitch actually means something.

The hypothesis to test: **grouped should give nearly the same stall count**, because what creates a
stall is an equation carrying one more unknown, not how many categories that unknown is split into —
and three of the four terms are nought on most rows anyway.

⚠️ It is a hypothesis about mechanism, and three of those have turned out false this week when
measured. So it is measured.

**How grouped is modelled here.** The constraint system has four footnote cells per row and no single
grouped one, so grouped is approximated as *at most one erasable footnote cell per batter*. On a row
where the other three are nought — the common case — that is exactly the grouped semantics: one unknown
inside the row identity, closed by the same column sum. Where a row carries two live footnote terms
the approximation understates grouped slightly, which is the safe direction: it cannot make grouped
look better than it is.

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
    batting_cell,
    batting_total_cell,
    cell_values,
    footnote_cell,
    pitching_cell,
    pitching_total_cell,
    shape_of,
)
from boxscore_forge.erasure import ORDERINGS  # noqa: E402
from boxscore_forge.identities import (  # noqa: E402
    BATTING_COLUMNS,
    FOOTNOTE_COLUMNS,
    PITCHING_COLUMNS,
    find_violations,
)
from boxscore_forge.solver import solve  # noqa: E402

TARGETS = tuple(range(5, 13))
GATE = 0.25
SEEDS = (1, 2)
SAMPLE_PER_DECADE = 4

CONFIGURATIONS = ("given", "grouped", "separate")
COLUMNS = {"given": 6, "grouped": 7, "separate": 10}


@dataclass(frozen=True)
class Point:
    configuration: str
    target: int | None
    blanks: int
    stalls: int
    chain: int
    position: float
    categories: int


def _categories(loaded: Loaded) -> int:
    """How many of the four footnote kinds appear anywhere in this game.

    The operator's idea, turned the right way round: a filter on this would not be filtering to
    *simplify* but to complicate. With one category present, deducing a grouped total of 2 says it is
    two hit-by-pitches and the row is fully determined; with two or three present the total is
    deducible and the breakdown is not.

    ⚠️ Worth stating what that does and does not do. The **row identity only needs the total**, so an
    undetermined breakdown does not by itself hold anything up — it holds up only if the footnote
    *column sums* are on the board, because then each category has its own equation to close. Whether
    those columns are shown is a design question this measurement does not settle; what it can say is
    whether category count tracks stall count in the boards as they stand.
    """
    return sum(
        1 for column in FOOTNOTE_COLUMNS if any(getattr(note, column) for note in loaded.direction.batter_footnotes)
    )


def grid_cells(loaded: Loaded) -> list[str]:
    shape = shape_of(loaded.direction)
    cells = [batting_cell(index, column) for index in range(shape.batter_count) for column in BATTING_COLUMNS]
    cells += [batting_total_cell(column) for column in BATTING_COLUMNS]
    cells += [pitching_cell(index, column) for index in range(shape.pitcher_count) for column in PITCHING_COLUMNS]
    cells += [pitching_total_cell(column) for column in PITCHING_COLUMNS]
    return cells


def erasable_for(loaded: Loaded, configuration: str) -> list[str]:
    """The grid, plus however much of the footnote line this configuration exposes."""
    cells = grid_cells(loaded)
    rows = len(loaded.direction.batter_footnotes)
    if configuration == "separate":
        cells += [footnote_cell(index, column) for index in range(rows) for column in FOOTNOTE_COLUMNS]
    elif configuration == "grouped":
        # One per row: the cell carrying the value where there is one, otherwise the first. That is
        # the grouped column's single unknown, closed by the same footnote column sum.
        for index in range(rows):
            note = loaded.direction.batter_footnotes[index]
            live = [column for column in FOOTNOTE_COLUMNS if getattr(note, column)]
            cells.append(footnote_cell(index, live[0] if live else FOOTNOTE_COLUMNS[0]))
    return sorted(cells)


def walk(loaded: Loaded, configuration: str, seed: int) -> list[Point]:
    """Erase to the ceiling, recording each stall target on the way past it."""
    shape = shape_of(loaded.direction)
    values = cell_values(loaded.direction)
    rng = random.Random(seed)  # noqa: S311
    candidates = ORDERINGS["row_first"](erasable_for(loaded, configuration), loaded.direction, rng)

    found: list[Point] = []
    wanted = list(TARGETS)
    erased: set[str] = set()
    best = None
    for cell in candidates:
        trial = erased | {cell}
        solution = solve(shape, {name: value for name, value in values.items() if name not in trial})
        if not solution.is_complete:
            continue
        erased = trial
        best = solution
        while wanted and solution.stalls >= wanted[0]:
            found.append(
                Point(
                    configuration=configuration,
                    target=wanted.pop(0),
                    blanks=len(erased),
                    stalls=solution.stalls,
                    chain=solution.chain_length,
                    position=_mean_position(solution),
                    categories=_categories(loaded),
                )
            )
    if best is not None:
        found.append(
            Point(
                configuration=configuration,
                target=None,
                blanks=len(erased),
                stalls=best.stalls,
                chain=best.chain_length,
                position=_mean_position(best),
                categories=_categories(loaded),
            )
        )
    return found


def _mean_position(solution: object) -> float:
    """How far into the solve the stalls fall. Grouped may move them rather than remove them."""
    steps = solution.deductions  # type: ignore[attr-defined]
    if not steps:
        return 0.0
    from boxscore_forge.solver import Technique  # noqa: PLC0415

    positions = []
    previous = False
    for index, step in enumerate(steps):
        bounding = step.technique is Technique.BOUNDING
        if bounding and not previous:
            positions.append(index / len(steps))
        previous = bounding
    return statistics.fmean(positions) if positions else 0.0


def report(points: list[Point], runs: int) -> None:
    print("")
    print("=== CEILING AND COVERAGE, BY CONFIGURATION ===")
    heads = (
        f"{'configuration':>14}{'columns':>9}{'ceiling p50':>13}{'max':>6}{'blanks':>8}{'reach 5':>9}{'stall pos':>11}"
    )
    print(heads)
    for configuration in CONFIGURATIONS:
        ceilings = [p for p in points if p.configuration == configuration and p.target is None]
        at_five = [p for p in points if p.configuration == configuration and p.target == 5]
        if not ceilings:
            continue
        stalls = sorted(p.stalls for p in ceilings)
        print(
            f"{configuration:>14}{COLUMNS[configuration]:>9}{statistics.median(stalls):>13.0f}{stalls[-1]:>6}"
            f"{statistics.median([p.blanks for p in ceilings]):>8.0f}"
            f"{len(at_five) / runs:>8.0%}"
            f"{statistics.fmean([p.position for p in ceilings]):>10.0%}"
        )

    print("")
    print("=== BLANKS NEEDED AT EACH STALL TARGET ===")
    print(f"{'target':>8}" + "".join(f"{name:>22}" for name in CONFIGURATIONS))
    for target in TARGETS:
        row = f"{target:>8}"
        for configuration in CONFIGURATIONS:
            group = [p for p in points if p.configuration == configuration and p.target == target]
            if not group:
                row += f"{'-':>22}"
                continue
            share = len(group) / runs
            row += f"{statistics.median([p.blanks for p in group]):>14.0f} ({share:>4.0%})"
        print(row)
    print("")
    print("  If grouped comes within a stall or two of separate, grouped wins: three columns saved,")
    print("  one unknown per row instead of four, and the board stays closer to what §6 describes.")
    print("")
    print("=== DOES THE NUMBER OF FOOTNOTE CATEGORIES TRACK STALLS ===")
    print("  Not a filter to simplify. If two or three categories produce more stalls than one, it is")
    print("  a free selection criterion that complicates, and the column set does not change either way.")
    heads = f"{'categories':>12}{'share of pool':>15}{'ceiling p50':>13}{'stalls at 5':>13}{'blanks at 5':>13}"
    print(heads)
    ceilings = [p for p in points if p.target is None and p.configuration == "grouped"]
    at_five = [p for p in points if p.target == 5 and p.configuration == "grouped"]
    for count in range(1, 5):
        here = [p for p in ceilings if p.categories == count]
        five = [p for p in at_five if p.categories == count]
        if not here:
            continue
        print(
            f"{count:>12}{len(here) / max(len(ceilings), 1):>14.0%}"
            f"{statistics.median([p.stalls for p in here]):>13.0f}"
            f"{(statistics.median([p.stalls for p in five]) if five else float('nan')):>13.0f}"
            f"{(statistics.median([p.blanks for p in five]) if five else float('nan')):>13.0f}"
        )


def main() -> None:
    loaded = load(SAMPLE_PER_DECADE, gated=True, gate=GATE, max_batters=13, max_pitchers=4)
    sample = [item for item in loaded if not find_violations(item.direction)]
    print(f"{len(sample)} gated directions, gate {GATE:.0%}")
    print(f"decades: {dict(sorted(Counter((item.season // 10) * 10 for item in sample).items()))}")

    points = [
        point
        for item in sample
        for configuration in CONFIGURATIONS
        for seed in SEEDS
        for point in walk(item, configuration, seed)
    ]
    report(points, len(sample) * len(SEEDS))


if __name__ == "__main__":
    main()
