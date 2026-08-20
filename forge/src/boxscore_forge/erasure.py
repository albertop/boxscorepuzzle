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
from typing import Final

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


SCOREBOARD_DUPLICATES: Final = (
    batting_total_cell("runs"),
    batting_total_cell("hits"),
    pitching_total_cell("runs"),
    pitching_total_cell("hits"),
)
"""The four totals the line score already prints, verbatim.

⚠️ **Erasing one of these does not make a puzzle harder; it makes it one cell longer.** The relation is
real — `line_score.offense_hits = batting_totals.hits` is an equation the solver carries, in the
`column_sum` family — but it has **two terms and one unknown**, so the player reads the number off the
scoreboard two centimetres above and the solver records a deduction. A lookup counted as a deduction is
a lookup counted as difficulty, and every difficulty number in this project would carry it.

⚠️ **Excluded here rather than filtered downstream**, which is v03-P1-02's lesson: the erasable set is
where the board says what may be taken away, and a second place that removes cells afterwards is a
second definition that drifts. This sits beside the line score and the footnote totals for the same
reason they do — the board gives them.

It was found by rendering the phone board and reading it: the `H` total sat blank with `AWAY H 15`
printed directly above it.
"""


def erasable(direction: Direction) -> list[str]:
    """The grid, and nothing else. **No footnote cell is erasable, per-batter or total.**

    ⚠️ The summary line said "and the footnote line's per-batter cells" after those cells were closed
    again — a docstring naming something the function no longer returns, which is the most misleading
    place for one to be stale because the body below it is correct.

    The line score is the board's anchor and is given complete (§6), and so is the whole footnote line —
    the row identity needs those terms to close, and a puzzle missing a term the player cannot see is
    broken rather than hard.

    ⚠️ **The four totals the line score prints are not here** — see `SCOREBOARD_DUPLICATES`. They are
    given for the same reason the line score itself is: the board hands them over.

    ⚠️⚠️ **The per-batter footnote cells were opened and are now closed again, on a measurement.**

    They were opened because a run reported the median board going from 5 stalls to 15 with them
    erasable, and only 56% of boards reaching five without them. Both halves were true and **both were
    counting zeros**: when `HBP`, `SF`, `SH` and `CI` are all zero for a batter the row identity is
    `PA = AB + BB`, so an erased zero asked the solver to deduce a value that existed only because the
    thing did not happen — and it did, correctly, recording a step each time.

    The pool run that settled it: coverage with the cells erasable-if-non-zero and with them given is
    **the same at every target**, and pair by pair the two are identical on every field in 91% of trials.
    The rest differ only in the blank count. **96% of the pool's footnote terms are zero**, and on most
    boards there is not one term to erase — which is why the two arms cannot be told apart.

    So this is not "erasable if non-zero". The non-zero rule was the right correction to a wrong
    decision, and the measurement retired the decision.

    ⚠️ **Everything built for the open case went with it**, rather than being disabled: the footnote cell
    drawing, the cap on terms per board, the constraint for large groups, the erased-attribution design.
    A drawing kept for a case that no longer exists is a mechanism kept past its problem.
    """
    shape = shape_of(direction)
    cells = [batting_cell(index, column) for index in range(shape.batter_count) for column in BATTING_COLUMNS]
    cells += [batting_total_cell(column) for column in BATTING_COLUMNS]
    cells += [pitching_cell(index, column) for index in range(shape.pitcher_count) for column in PITCHING_COLUMNS]
    cells += [pitching_total_cell(column) for column in PITCHING_COLUMNS]
    # ⚠️ **The footnote line is given. No per-batter cell is erasable.** See below.
    return sorted(set(cells) - set(SCOREBOARD_DUPLICATES))


Ordering = Callable[[Sequence[str], Direction, random.Random], list[str]]


def _reject_duplicates(cells: Sequence[str]) -> None:
    """A candidate list naming the same cell twice is malformed, and it fails quietly.

    ⚠️ **This is a real defect that ran for a whole round of measurements.** `erasable()` gained the
    per-batter footnote cells, and an instrument that had been adding them itself kept doing so, so
    every footnote cell appeared twice. Nothing broke: erasing a cell that is already erased is a
    no-op, the boards stayed correct, and the numbers looked fine.

    What changed was the *trajectory*. Both orderings bucket the cells — `_row_first` by row and
    `_column_first` by column — and a bucket holding each of its cells twice keeps taking round-robin
    turns that erase nothing, so its cells enter at roughly half the rate production gives them and
    every seeded order downstream shifts with it. The result was a difficulty model measured on a
    board no generator produces.

    Checked here rather than in `erase()` because the discovery instruments call the orderings
    directly, which is exactly where it happened.
    """
    if len(set(cells)) != len(cells):
        repeated = sorted({cell for cell in cells if list(cells).count(cell) > 1})
        message = f"the candidate list names {len(repeated)} cells more than once: {repeated[:5]}"
        raise ValueError(message)


def _random_order(cells: Sequence[str], _: Direction, rng: random.Random) -> list[str]:
    """The baseline. Every measurement so far used it, which is why it is here to be beaten."""
    _reject_duplicates(cells)
    order = list(cells)
    rng.shuffle(order)
    return order


def _column_first(cells: Sequence[str], _: Direction, rng: random.Random) -> list[str]:
    """Round-robin across columns, so no single column empties before another is touched.

    A column that loses many cells at once tends to go ambiguous rather than hard, since its sum is
    the only equation most of its cells appear in.
    """
    _reject_duplicates(cells)
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
    _reject_duplicates(cells)
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


# ⚠️ Six keyword arguments, one over the limit, and the sixth is `slots` — experimental and
# defaulted off. Silenced rather than split: the alternative is a second erasure function, and a
# walk that exists twice is the defect this project keeps finding.
def erase(  # noqa: PLR0913
    direction: Direction,
    *,
    target_chain: int | None = None,
    target_stalls: int | None = None,
    seed: int,
    ordering: str = DEFAULT_ORDERING,
    slots: tuple[int, ...] = (),
) -> Puzzle | None:
    """Erase towards a target chain length, or give up.

    Returns None when this boxscore cannot carry a solution that long while staying derivable. That
    is a discard, not a failure: §22 throws candidates away silently and never relaxes the rule to
    reach a number.

    `seed` makes the result reproducible, which is §21's idempotence at this step — regenerating a
    batch has to produce the same puzzle for the same game or the no-repetition promise breaks.

    `slots` is the batting order. ✅ **Adopted, and passed by `lineup_fallback` alone.** Production
    reaches this function
    through `erase_with_lineup_fallback`, which tries the plain path first and only retries with the
    order when the target is missed — so an empty `slots` here is the **first attempt**, not the
    production configuration. Calling `erase(..., slots=...)` directly is the everywhere-on arrangement
    the measurement rejected, and a test refuses it outside the fallback.

    A parameter here rather than a second erasure function because the walk, the ordering and the
    give-up rule must not exist twice — two copies of a rule drift, and this project has the record to
    prove it.
    """
    if (target_chain is None) == (target_stalls is None):
        message = "give exactly one of target_chain or target_stalls"
        raise ValueError(message)
    if ordering not in ORDERINGS:
        message = f"unknown erasure ordering {ordering!r}; have {sorted(ORDERINGS)}"
        raise ValueError(message)

    shape = shape_of(direction, slots)
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
