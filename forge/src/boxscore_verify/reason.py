"""Two ways of reaching a solution, kept apart on purpose.

`derive` never guesses. It narrows what each cell can be until something is pinned, and stops when
nothing more follows. That is §4's publication rule stated as code: a puzzle ships only if this
finishes, because a board that needs a guess is one the player experiences as trial and error.

`solutions` does guess. It exists to answer a different question — *how many* solutions are there —
which §22 makes a layer of its own, and answering it needs a search that a human would never perform.
Keeping the two in one function would let a puzzle pass the derivability layer on the strength of a
branch, which is the failure §22 calls the worst: unique, apparently fine, and underivable.

⚠️ **This is the second of the two solvers the project deliberately keeps.** The generator has one so
it knows when to stop erasing; this one confirms the result independently, and §22 requires that they
share no code. If they were factored together a bug would sit on both sides of the check and the
guarantee would be theatre. **The duplication is the design.** See `boxscore_verify/verify.py` and
§22 before attempting to tidy it away.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Final

from boxscore_verify.rules import Relation

CELL_CAP: Final = 200
"""A modelling bound, **not** something §3 states.

The search needs finite domains and §3 only gives non-negativity, so cells start at `[0, 200]`. No
quantity on a boxscore comes close — a team's plate appearances run to about sixty in a long game —
but the cap is an assumption rather than a fact, so `solutions` refuses to answer rather than return
a result that touches it.
"""

NODE_BUDGET: Final = 200_000
"""How much searching before the verifier says it does not know.

A verifier that runs forever is a verifier nobody waits for, and one that quietly gives up is worse
than one that says so. Exhausting this raises `UndecidedError`, which is not a pass.
"""


class ContradictionError(Exception):
    """The board cannot be satisfied: some cell's range emptied out."""


class UndecidedError(Exception):
    """The search hit a limit. Not a pass and not a failure — an answer we do not have."""


@dataclass(frozen=True, slots=True)
class Derivation:
    """What `derive` reached, and whether it got all the way."""

    values: dict[str, int]
    unresolved: tuple[str, ...]

    @property
    def is_complete(self) -> bool:
        return not self.unresolved


def _initial(cells: Iterable[str], known: Mapping[str, int]) -> dict[str, tuple[int, int]]:
    return {cell: (known[cell], known[cell]) if cell in known else (0, CELL_CAP) for cell in cells}


def _narrow_once(relation: Relation, bounds: dict[str, tuple[int, int]]) -> bool:
    """Push one relation against the current ranges. True if anything moved.

    For `Σ cᵢxᵢ = k`, each term in turn is what the others leave over, which bounds it from both
    sides. An inequality only bounds it from one — that is the whole difference between the two.
    """
    changed = False
    contributions = [(cell, coefficient, bounds[cell]) for cell, coefficient in relation.terms]
    for index, (cell, coefficient, _) in enumerate(contributions):
        rest_low = 0
        rest_high = 0
        for other, (other_cell, other_coefficient, (low, high)) in enumerate(contributions):
            if other == index:
                continue
            del other_cell
            rest_low += min(other_coefficient * low, other_coefficient * high)
            rest_high += max(other_coefficient * low, other_coefficient * high)

        # `coefficient * cell <= window_high` always. The opposite side exists only for an equality,
        # and when it does not it is left genuinely open rather than given a large finite stand-in.
        # An earlier version fabricated one from the cell cap and it produced *false* bounds as soon
        # as the cap was small — a bound invented for convenience is still a bound the search obeys.
        window_high = relation.constant - rest_low
        window_low = relation.constant - rest_high

        low, high = bounds[cell]
        if coefficient > 0:
            new_high = min(high, window_high // coefficient)
            new_low = max(low, -(-window_low // coefficient)) if relation.equality else low
        else:
            new_low = max(low, -(-window_high // coefficient))
            new_high = min(high, window_low // coefficient) if relation.equality else high
        if new_low > new_high:
            message = f"{cell} has no value left: {relation.origin} forces [{new_low}, {new_high}]"
            raise ContradictionError(message)
        if (new_low, new_high) != (low, high):
            bounds[cell] = (new_low, new_high)
            changed = True
    return changed


def narrow(relations: Iterable[Relation], cells: Iterable[str], known: Mapping[str, int]) -> dict[str, tuple[int, int]]:
    """Tighten every cell's range until nothing moves. Raises `ContradictionError` if a range empties."""
    relations = tuple(relations)
    bounds = _initial(cells, known)
    moving = True
    while moving:
        moving = False
        for relation in relations:
            moving |= _narrow_once(relation, bounds)
    return bounds


def derive(relations: Iterable[Relation], cells: Iterable[str], given: Mapping[str, int]) -> Derivation:
    """Solve without ever guessing, which is the only kind of solving a puzzle may require (§4)."""
    relations = tuple(relations)
    cells = tuple(cells)
    values = dict(given)
    while True:
        bounds = narrow(relations, cells, values)
        settled = {cell: low for cell, (low, high) in bounds.items() if low == high and cell not in values}
        if not settled:
            break
        values.update(settled)
    unresolved = tuple(cell for cell in cells if cell not in values)
    return Derivation(values=values, unresolved=unresolved)


def solutions(
    relations: Iterable[Relation],
    cells: Iterable[str],
    given: Mapping[str, int],
    *,
    limit: int = 2,
) -> list[dict[str, int]]:
    """Every way the board can be completed, up to `limit`.

    `limit=2` is what uniqueness needs: one is unique, two is enough to know it is not, and counting
    further is work nobody reads. Guessing is allowed here and only here.
    """
    relations = tuple(relations)
    cells = tuple(cells)
    found: list[dict[str, int]] = []
    budget = [NODE_BUDGET]

    def walk(values: dict[str, int]) -> None:
        if len(found) >= limit:
            return
        budget[0] -= 1
        if budget[0] <= 0:
            message = f"gave up after {NODE_BUDGET} steps; this is not a pass"
            raise UndecidedError(message)
        try:
            settled = derive(relations, cells, values)
        except ContradictionError:
            return
        if settled.is_complete:
            if any(value >= CELL_CAP for value in settled.values.values()):
                message = "a solution reached the modelling cap, so the search cannot be trusted"
                raise UndecidedError(message)
            found.append(settled.values)
            return
        bounds = narrow(relations, cells, settled.values)
        # Branch on the tightest unknown. A cell with two candidates settles the question in two
        # steps where one with forty would spend the budget before saying anything.
        cell = min(settled.unresolved, key=lambda name: bounds[name][1] - bounds[name][0])
        low, high = bounds[cell]
        for candidate in range(low, high + 1):
            walk({**settled.values, cell: candidate})
            if len(found) >= limit:
                return

    walk(dict(given))
    return found
