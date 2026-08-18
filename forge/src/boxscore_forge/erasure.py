"""Taking cells away until the board is a puzzle.

The input is a target and the cell count is whatever reaching it costs (§21, §31). Two targets exist
and **the one that grades difficulty is `target_stalls`**.

⚠️ **`target_chain` measures length, not difficulty.** A chain-10 board is ten subtractions in single
file and one was solved by hand in under a minute. A *stall* is the moment propagation runs dry and
something beyond direct substitution is needed to restart it, which is where the thinking happens.
Chain is kept because every measurement before this one used it and they have to stay comparable, but
a board meant to be hard is erased towards stalls.

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
    footnote_cell,
    pitching_cell,
    pitching_total_cell,
    shape_of,
)
from boxscore_forge.identities import BATTING_COLUMNS, FOOTNOTE_COLUMNS, PITCHING_COLUMNS
from boxscore_forge.solver import Solution, solve


@dataclass(frozen=True, slots=True)
class Puzzle:
    """What the player is handed, plus the proof that it can be reasoned through."""

    shape: BoardShape
    given: dict[str, int]
    erased: frozenset[str]
    solution: Solution


def erasable(direction: Direction) -> list[str]:
    """The grid, and the footnote line's per-batter cells.

    The line score is the board's anchor and is given complete (§6), and so is the **footnote totals**
    row — the row identity needs those to close, and a puzzle missing a term the player cannot see is
    broken rather than hard.

    ⚠️ **The per-batter footnote cells are unknowns, and that is a change to §6.** They were given
    because the identity needs the numbers, and the totals row supplies them: HBP, SF, SH and CI are
    each an unknown *inside* the row identity with its column sum available to close it.

    Measured, which is why it changed: with the footnote line given, the median board stalls 5 times
    at full erasure and only 56% reach five. With these cells open it is 15 and every board reaches
    five. It costs no column and no pixel — the footnote line is already on the board.
    """
    shape = shape_of(direction)
    cells = [batting_cell(index, column) for index in range(shape.batter_count) for column in BATTING_COLUMNS]
    cells += [batting_total_cell(column) for column in BATTING_COLUMNS]
    cells += [pitching_cell(index, column) for index in range(shape.pitcher_count) for column in PITCHING_COLUMNS]
    cells += [pitching_total_cell(column) for column in PITCHING_COLUMNS]
    cells += [footnote_cell(index, column) for index in range(shape.batter_count) for column in FOOTNOTE_COLUMNS]
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


ORDERINGS: dict[str, Ordering] = {
    "row_first": _row_first,
    "random": _random_order,
    "column_first": _column_first,
}
DEFAULT_ORDERING = "row_first"
"""Measured, not chosen. All orderings reach the same ceiling, and this one gives the least padded
easy board — 12% trivial steps at a chain target of 5 against 19-20% for the others."""

# A fourth ordering, `mirrored`, erased each batting row together with its opposite from the other
# end of the lineup. It was removed after being measured: it really is symmetric (72.9% of erased
# batting cells paired, against a 42.9% coincidence baseline) and it really is free (same ceiling,
# same cell count). But mirroring a boxscore pairs the leadoff hitter with the ninth, which means
# nothing in baseball, so it bought nothing for the complexity it carried.


def erase(
    direction: Direction,
    *,
    target_chain: int | None = None,
    target_stalls: int | None = None,
    seed: int,
    ordering: str = DEFAULT_ORDERING,
) -> Puzzle | None:
    """Erase towards a target chain length, or give up.

    Returns None when this boxscore cannot carry a solution that long while staying derivable. That
    is a discard, not a failure: §22 throws candidates away silently and never relaxes the rule to
    reach a number.

    `seed` makes the result reproducible, which is §21's idempotence at this step — regenerating a
    batch has to produce the same puzzle for the same game or the no-repetition promise breaks.
    """
    if (target_chain is None) == (target_stalls is None):
        message = "give exactly one of target_chain or target_stalls"
        raise ValueError(message)
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
        reached = solution.stalls if target_stalls is not None else solution.chain_length
        wanted = target_stalls if target_stalls is not None else target_chain
        if wanted is not None and reached >= wanted:
            return Puzzle(shape=shape, given=given, erased=frozenset(erased), solution=solution)
    return None
