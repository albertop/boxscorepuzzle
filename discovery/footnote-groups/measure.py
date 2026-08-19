"""Is an unassigned footnote resolvable? Per group size and per term count, never aggregated.

⚠️ **Stall count says how often a player has to think. It does not say whether the thing to think
about can be resolved.** The paired measurement settled that opening the per-batter footnote cells is
what makes a pool exist above five stalls; it says nothing about whether *which row* an HBP belongs to
can be worked out. Those are different problems, and only the second one can leave a board underivable.

The old figure — 18 never-mattered, 5 had-to-resolve, 8 non-unique out of 31 — covers **one cell**:
two rows sharing a slot, one term between them. The pool holds 2,412 two-row groups with **two** terms,
720 three-row groups with two, 103 four-row groups with two, and a five-row tail.

**Nothing here is aggregated.** If solvability falls with group size or term count, *where* it falls is
the finding, and "three or more" destroys it.

**The one-row cells are the control.** One row with two terms is not ambiguous at all — both terms are
hers. If those resolve and two-row two-term groups do not, the difficulty is the **assignment** rather
than carrying several terms, which is two explanations an aggregate would confuse.

Three answers per cell: how often the board stays **uniquely solvable** with the assignment unknown,
how often it must be **resolved before the rest proceeds**, and **which technique** resolves it.

Read-only against DGL. Run from `forge/`.
"""

import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))

from measure import Loaded, load  # noqa: E402

from boxscore_forge.constraints import cell_values, footnote_cell, shape_of  # noqa: E402
from boxscore_forge.identities import FOOTNOTE_COLUMNS, find_violations  # noqa: E402
from boxscore_forge.solver import Technique, solve  # noqa: E402

SAMPLE_PER_DECADE = 60
GATE = 0.25


@dataclass(frozen=True)
class Group:
    rows: int
    terms: int
    unique: bool
    had_to_resolve: bool
    technique: str


def groups_in(loaded: Loaded) -> list[Group]:
    """Every slot group, with its footnote cells hidden, asked whether the board still closes."""
    direction = loaded.direction
    shape, values = shape_of(direction), cell_values(direction)
    by_slot: dict[int, list[int]] = defaultdict(list)
    for index, slot in enumerate(loaded.slots):
        by_slot[slot].append(index)

    found: list[Group] = []
    for indexes in by_slot.values():
        terms = sum(
            getattr(direction.batter_footnotes[index], column) for index in indexes for column in FOOTNOTE_COLUMNS
        )
        hidden = {footnote_cell(index, column) for index in indexes for column in FOOTNOTE_COLUMNS}
        solution = solve(shape, {name: value for name, value in values.items() if name not in hidden})
        # Unique when every hidden cell comes back, and back to the value it had.
        unique = solution.is_complete and all(solution.values.get(cell) == values[cell] for cell in hidden)
        technique = "unsolved"
        if unique:
            steps = [step for step in solution.deductions if step.cell in hidden]
            technique = "bounding" if any(s.technique is Technique.BOUNDING for s in steps) else "propagation"
        # Whether the rest of the board waited on it: does anything deduced later lean on these cells?
        had_to_resolve = unique and any(
            hidden & step.depends_on for step in solution.deductions if step.cell not in hidden
        )
        found.append(
            Group(rows=len(indexes), terms=terms, unique=unique, had_to_resolve=had_to_resolve, technique=technique)
        )
    return found


def report(groups: list[Group]) -> None:
    cells: dict[tuple[int, int], list[Group]] = defaultdict(list)
    for group in groups:
        cells[(group.rows, min(group.terms, 4))].append(group)

    print("")
    print("=== UNIQUELY SOLVABLE WITH THE ASSIGNMENT UNKNOWN, PER CELL ===")
    print("Rows down, terms across. n in brackets. The one-term column of row 2 is the old measurement.")
    print(f"{'rows':>5}" + "".join(f"{f'{terms} term' + ('s' if terms > 1 else ''):>16}" for terms in range(0, 5)))
    for rows in sorted({group.rows for group in groups}):
        line = f"{rows:>5}"
        for terms in range(0, 5):
            here = cells.get((rows, terms), [])
            share = f"{sum(g.unique for g in here) / len(here):.0%} [{len(here)}]" if here else "-"
            line += f"{share:>16}"
        print(line)

    print("")
    print("=== OF THE SOLVABLE ONES, HOW OFTEN THE REST WAITED ON IT ===")
    print(f"{'rows':>5}" + "".join(f"{f'{terms} term' + ('s' if terms > 1 else ''):>16}" for terms in range(0, 5)))
    for rows in sorted({group.rows for group in groups}):
        line = f"{rows:>5}"
        for terms in range(0, 5):
            here = [g for g in cells.get((rows, terms), []) if g.unique]
            share = f"{sum(g.had_to_resolve for g in here) / len(here):.0%} [{len(here)}]" if here else "-"
            line += f"{share:>16}"
        print(line)

    print("")
    print("=== WHICH TECHNIQUE RESOLVED IT ===")
    for rows in sorted({group.rows for group in groups}):
        here = [g for g in groups if g.rows == rows and g.unique]
        if not here:
            continue
        counted = Counter(g.technique for g in here)
        total = sum(counted.values())
        print(f"  {rows} row(s): " + ", ".join(f"{name} {n / total:.0%}" for name, n in counted.most_common()))

    print("")
    print("=== THE CONTROL ===")
    one = [g for g in groups if g.rows == 1 and g.terms >= 2]
    two = [g for g in groups if g.rows == 2 and g.terms >= 2]
    for name, here in (("one row, 2+ terms (not ambiguous at all)", one), ("two rows, 2+ terms", two)):
        if here:
            print(f"  {name}: {sum(g.unique for g in here) / len(here):.0%} unique [{len(here)}]")
    print("  If the first resolves and the second does not, the difficulty is the assignment rather than")
    print("  carrying several terms — two explanations an aggregate would confuse.")


def main() -> None:
    sample = [item for item in load(SAMPLE_PER_DECADE, gated=True, gate=GATE, max_batters=13, max_pitchers=4)
              if not find_violations(item.direction)]
    if not sample:
        raise SystemExit(f"no directions survived the {GATE:.0%} gate")
    print(f"{len(sample)} gated directions", flush=True)

    groups: list[Group] = []
    for number, item in enumerate(sample, start=1):
        groups.extend(groups_in(item))
        if number % 50 == 0:
            print(f"  {number}/{len(sample)} boards, {len(groups)} groups", flush=True)
    report(groups)
    print(f"\n({len(groups)} slot groups from {len(sample)} boards)")


if __name__ == "__main__":
    main()
