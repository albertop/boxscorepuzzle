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


_COLUMNS = (0, 1, 2, 3, "4+")
"""Exact term counts, and one honest tail bucket rather than a fourth column pretending to be four."""


def _label(terms: object) -> str:
    return f"{terms} terms" if terms != 1 else "1 term"


def _header() -> str:
    return f"{'rows':>5}" + "".join(f"{_label(terms):>16}" for terms in _COLUMNS)


def _cohort(cells: dict, rows: int, terms: object) -> list:
    if terms == "4+":
        return [g for key, here in cells.items() if key[0] == rows and key[1] >= 4 for g in here]
    return cells.get((rows, terms), [])


def report(groups: list[Group]) -> None:
    cells: dict[tuple[int, int], list[Group]] = defaultdict(list)
    for group in groups:
        # ⚠️ **`min(group.terms, 4)` filed every group of four or more under *four*.** The contract for
        # this run is explicit that group size and term count stay separate, because an aggregate can
        # look reassuring while one (rows, terms) cohort fails — which is the threshold the run exists
        # to find. Exact counts, with a `4+` column that says what it is.
        cells[(group.rows, group.terms)].append(group)

    print("")
    print("=== UNIQUELY SOLVABLE WITH THE ASSIGNMENT UNKNOWN, PER CELL ===")
    print("Rows down, terms across. n in brackets. The one-term column of row 2 is the old measurement.")
    print(_header())
    for rows in sorted({group.rows for group in groups}):
        line = f"{rows:>5}"
        for terms in _COLUMNS:
            here = _cohort(cells, rows, terms)
            share = f"{sum(g.unique for g in here) / len(here):.0%} [{len(here)}]" if here else "-"
            line += f"{share:>16}"
        print(line)

    print("")
    print("=== OF THE SOLVABLE ONES, HOW OFTEN THE REST WAITED ON IT ===")
    print(_header())
    for rows in sorted({group.rows for group in groups}):
        line = f"{rows:>5}"
        for terms in _COLUMNS:
            here = [g for g in _cohort(cells, rows, terms) if g.unique]
            share = f"{sum(g.had_to_resolve for g in here) / len(here):.0%} [{len(here)}]" if here else "-"
            line += f"{share:>16}"
        print(line)

    print("")
    print("=== WHICH TECHNIQUE RESOLVED IT, PER CELL ===")
    print("Keyed the same way as everything above. Aggregating over terms would hide the cell where")
    print("bounding starts being needed, which is the point the run is looking for.")
    for rows in sorted({group.rows for group in groups}):
        for terms in _COLUMNS:
            here = [g for g in _cohort(cells, rows, terms) if g.unique]
            if not here:
                continue
            counted = Counter(g.technique for g in here)
            shown = ", ".join(f"{name} {n / len(here):.0%}" for name, n in counted.most_common())
            print(f"  {rows} row(s), {_label(terms):<8} [{len(here):>4}]  {shown}")

    print("")
    print("=== THE CONTROL ===")
    print("⚠️ Exactly two terms on both sides. It used to be `>= 2`, which compares populations that")
    print("   are composed differently: a multi-row group has more chances to contain events, so its")
    print("   term distribution is heavier, and a lower rate could come from carrying more terms, from")
    print("   assignment ambiguity, or from both. The aggregate could not tell them apart while the")
    print("   text beside it claimed it could — which is the confound this control exists to avoid.")
    for terms in (2, 3):
        one = _cohort(cells, 1, terms)
        two = _cohort(cells, 2, terms)
        if not one or not two:
            continue
        print(f"  {terms} terms exactly:")
        print(f"    one row  (not ambiguous at all): {sum(g.unique for g in one) / len(one):.0%} unique [{len(one)}]")
        print(f"    two rows (assignment unknown):   {sum(g.unique for g in two) / len(two):.0%} unique [{len(two)}]")
    print("  Term count is held fixed and only the number of possible carriers changes, so a difference")
    print("  is the assignment. The stratified table above is authoritative; this is one slice of it.")


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
