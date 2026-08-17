"""Taking cells away until the board is a puzzle.

The input is a **target chain length**, not a number of cells. Of the three metrics that describe a
solution path, chain length is the one that grades effort cleanly, so it is the objective and the
cell count is whatever reaching it costs (§21, §31).

⚠️ **This module contains one of the two solvers the project deliberately keeps.** The generator
needs a solver to know when to stop; the verifier needs one to confirm the result is derivable, and
§22 requires that verifier to share no code with what it judges. If the two were factored together,
a bug in the solver would pass validation by being present on both sides, and the whole guarantee
would be theatre. **The duplication is the design.** See `docs/design-boxscore-puzzle.md` §22 before
attempting to remove it.

The stopping condition is exactly §22's third layer: the solver finishes without ever guessing. A
board that cannot reach its target is discarded rather than relaxed — with thousands of candidates,
throwing one away costs nothing and bending the rule costs everything.
"""

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import (
    BoardShape,
    batting_cell,
    batting_total_cell,
    cell_values,
    pitching_cell,
    pitching_total_cell,
    shape_of,
)
from boxscore_forge.identities import BATTING_COLUMNS, PITCHING_COLUMNS
from boxscore_forge.solver import Solution, solve


@dataclass(frozen=True, slots=True)
class Puzzle:
    """What the player is handed, plus the proof that it can be reasoned through."""

    shape: BoardShape
    given: dict[str, int]
    erased: frozenset[str]
    solution: Solution


def erasable(direction: Direction) -> list[str]:
    """The grid, and only the grid.

    The line score is the board's anchor and is given complete (§6); the footnotes are given too,
    because without them the row identity does not close and the puzzle would need a term the
    player cannot see.
    """
    shape = shape_of(direction)
    cells = [batting_cell(index, column) for index in range(shape.batter_count) for column in BATTING_COLUMNS]
    cells += [batting_total_cell(column) for column in BATTING_COLUMNS]
    cells += [pitching_cell(index, column) for index in range(shape.pitcher_count) for column in PITCHING_COLUMNS]
    cells += [pitching_total_cell(column) for column in PITCHING_COLUMNS]
    return sorted(cells)


Ordering = Callable[[Sequence[str], Direction, random.Random], list[str]]


def _random_order(cells: Sequence[str], _: Direction, rng: random.Random) -> list[str]:
    """The baseline. Every measurement so far used it, which is why it is here to be beaten."""
    order = list(cells)
    rng.shuffle(order)
    return order


def _column_first(cells: Sequence[str], _: Direction, rng: random.Random) -> list[str]:
    """Round-robin across columns, so no single column empties before another is touched.

    A column that loses many cells at once tends to go ambiguous rather than hard, since its sum is
    the only equation most of its cells appear in.
    """
    buckets: dict[str, list[str]] = {}
    for cell in cells:
        buckets.setdefault(cell.rsplit(".", 1)[1], []).append(cell)
    for bucket in buckets.values():
        rng.shuffle(bucket)
    order: list[str] = []
    while any(buckets.values()):
        for column in sorted(buckets):
            if buckets[column]:
                order.append(buckets[column].pop())
    return order


def _row_first(cells: Sequence[str], _: Direction, rng: random.Random) -> list[str]:
    """Round-robin across rows instead, spreading the blanks down the board rather than across it."""
    buckets: dict[str, list[str]] = {}
    for cell in cells:
        buckets.setdefault(cell.rsplit(".", 1)[0], []).append(cell)
    for bucket in buckets.values():
        rng.shuffle(bucket)
    order: list[str] = []
    while any(buckets.values()):
        for row in sorted(buckets):
            if buckets[row]:
                order.append(buckets[row].pop())
    return order


def _mirrored(cells: Sequence[str], direction: Direction, rng: random.Random) -> list[str]:
    """Pair each batting row with its opposite from the other end of the lineup.

    Sudoku erases symmetrically for visual reasons and it is unmeasured whether that helps or hurts
    here. The ordering exists so the question can be answered rather than assumed.
    """
    rows = len(direction.batting)
    order = _random_order(cells, direction, rng)
    paired: list[str] = []
    for cell in order:
        paired.append(cell)
        if cell.startswith("batting["):
            index = int(cell.split("[", 1)[1].split("]", 1)[0])
            mirror = cell.replace(f"batting[{index}]", f"batting[{rows - 1 - index}]", 1)
            if mirror != cell and mirror in cells:
                paired.append(mirror)
    seen: set[str] = set()
    deduped: list[str] = []
    for cell in paired:
        if cell not in seen:
            seen.add(cell)
            deduped.append(cell)
    return deduped


ORDERINGS: dict[str, Ordering] = {
    "random": _random_order,
    "column_first": _column_first,
    "row_first": _row_first,
    "mirrored": _mirrored,
}


def erase(
    direction: Direction,
    *,
    target_chain: int,
    seed: int,
    ordering: str = "random",
) -> Puzzle | None:
    """Erase towards a target chain length, or give up.

    Returns None when this boxscore cannot carry a solution that long while staying derivable. That
    is a discard, not a failure: §22 throws candidates away silently and never relaxes the rule to
    reach a number.

    `seed` makes the result reproducible, which is §21's idempotence at this step — regenerating a
    batch has to produce the same puzzle for the same game or the no-repetition promise breaks.
    """
    if ordering not in ORDERINGS:
        message = f"unknown erasure ordering {ordering!r}; have {sorted(ORDERINGS)}"
        raise ValueError(message)

    shape = shape_of(direction)
    values = cell_values(direction)
    # Seeded on purpose. Section 21 needs the same game to produce the same puzzle every time, and
    # unseeded randomness would make a regenerated batch full of near-duplicates. Nothing here is a
    # secret, so a cryptographic generator would buy nothing and cost reproducibility.
    rng = random.Random(seed)  # noqa: S311
    candidates = ORDERINGS[ordering](erasable(direction), direction, rng)

    erased: set[str] = set()
    for cell in candidates:
        trial = erased | {cell}
        given = {name: value for name, value in values.items() if name not in trial}
        # No `except ContradictionError` here on purpose. Erasing only makes cells unknown, so it
        # cannot make a consistent boxscore inconsistent — a contradiction at this point means the
        # boxscore never passed layer 1 of §22 and reached the generator broken. Swallowing it would
        # hide that; letting it out is the whole reason "fail loud" is a rule.
        solution = solve(shape, given)
        if not solution.is_complete:
            continue
        erased = trial
        if solution.chain_length >= target_chain:
            return Puzzle(shape=shape, given=given, erased=frozenset(erased), solution=solution)
    return None
