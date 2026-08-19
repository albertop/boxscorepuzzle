"""The three measurements, as pure functions over a board.

⚠️ **Separated from the run so the tests can exercise the production predicate**, rather than reading
the script for fragments and hoping the fragment still governs the table. Every defect this instrument
has had was in one of these three functions, and every test written for it so far asserted on source
text or on trace activity instead of on the predicate itself.

Nothing here touches the database, the report, or the clock.
"""

from collections.abc import Mapping

from boxscore_forge.constraints import BoardShape
from boxscore_forge.solver import solve


def completions(board: object) -> int:
    """How many ways the board can be finished with the group unknown, counted to two.

    Cardinality is a property of the board; derivability is a property of a technique. The version
    that conflated them called both "not uniquely solvable", which points at two different fixes:
    several completions is a **generator constraint**, one completion the solver misses is a
    **technique question**.
    """
    from boxscore_verify.reason import solutions  # noqa: PLC0415
    from boxscore_verify.rules import all_cells, relations, values_of  # noqa: PLC0415

    # The board handed in already has the group hidden; the caller did that when it built it.
    return len(solutions(relations(board), all_cells(board), values_of(board), limit=2))


def derivable(shape: BoardShape, values: Mapping[str, int], hidden: frozenset[str]) -> bool:
    """Whether propagation plus bounding reaches the hidden values on an otherwise complete board."""
    solution = solve(shape, {name: value for name, value in values.items() if name not in hidden})
    return solution.is_complete and all(solution.values.get(cell) == values[cell] for cell in hidden)


def stops_progress(
    shape: BoardShape,
    values: Mapping[str, int],
    erased: frozenset[str],
    hidden: frozenset[str],
) -> bool:
    """Does hiding the group stop the rest of an erased board from progressing?

    ⚠️ **The baseline restores the group whatever the erasure did to it.** The version this replaces
    built the baseline by removing every cell in `erased` — and `erased` can already contain footnote
    cells, because they are erasable. When the sampled erasure had already hidden the group, baseline
    and treatment were the same board and blockage was forced to `False` **on precisely the published
    states where the question matters**. A low rate could not be told from a baseline that never
    revealed the assignment.

    So the baseline excludes `erased - hidden` and the treatment excludes `erased | hidden`, and the
    only difference between them is the thing being measured.

    ⚠️ **Counterfactual, not observed dependency.** Marking a group when some outside deduction
    *recorded a dependency* on it is evidence a solver path used the value. When hiding the group
    prevents that deduction from happening at all there is no such step — so the strongest blockage
    read as none. This compares closures: an outside cell the baseline settles and the treatment does
    not.
    """
    baseline = solve(shape, {name: value for name, value in values.items() if name not in (erased - hidden)})
    treatment = solve(shape, {name: value for name, value in values.items() if name not in (erased | hidden)})
    before = {cell for cell in baseline.values if cell not in hidden}
    after = {cell for cell in treatment.values if cell not in hidden}
    return bool(before - after)


def uses_the_group(
    shape: BoardShape,
    values: Mapping[str, int],
    erased: frozenset[str],
    hidden: frozenset[str],
) -> bool:
    """Whether any outside deduction leaned on the group. The weaker claim, kept separate.

    Using a value and needing it are different, and folding the first into the second is how blockage
    came to be measured as dependency in the first place.
    """
    treatment = solve(shape, {name: value for name, value in values.items() if name not in (erased | hidden)})
    return any(hidden & step.depends_on for step in treatment.deductions if step.cell not in hidden)


__all__ = ["completions", "derivable", "stops_progress", "uses_the_group"]
