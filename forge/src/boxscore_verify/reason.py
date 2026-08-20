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


def derive_in_view(
    relations: Iterable[Relation],
    cells: Iterable[str],
    given: Mapping[str, int],
    *,
    allow_bounding: bool = True,
) -> Derivation:
    """A deliberately weaker solver: one relation in view at a time.

    ⚠️ **`derive` is almost certainly stronger than a person.** It runs interval propagation to a
    fixed point across every relation at once, so a narrowing found in the pitching column is
    instantly available to the row identity twelve rows up. Nobody solves like that. §22 believes
    layer 3 is a human-derivability barrier; what layer 3 actually certifies is that *a machine with
    perfect simultaneous bookkeeping* needs no guess.

    This is the other end of the bracket. It looks at one relation at a time and never carries a
    narrowed range from one to the next:

      * an equality with exactly one unknown is a subtraction, which anyone can do
      * with `allow_bounding`, a single relation is also read against non-negativity alone — "these
        four are at least nought, so this one cannot exceed nine" — which is the bounding step §4
        describes, done the way a person does it rather than to a fixed point

    A board that passes **both** is derivable under a weak reading and unique under a strong one. The
    gap between them is uncertainty we otherwise cannot see, which is the whole reason this exists.
    """
    relations = tuple(relations)
    cells = tuple(cells)
    values = dict(given)

    while True:
        progressed = False
        for relation in relations:
            if not relation.equality:
                continue
            unknowns = [cell for cell in relation.cells() if cell not in values]
            if len(unknowns) != 1:
                continue
            cell = unknowns[0]
            coefficient = next(weight for name, weight in relation.terms if name == cell)
            rest = sum(weight * values[name] for name, weight in relation.terms if name != cell)
            remainder = relation.constant - rest
            if remainder % coefficient == 0:
                values[cell] = remainder // coefficient
                progressed = True
        if not progressed and allow_bounding:
            progressed = _bound_one_relation(relations, values)
        if not progressed:
            break

    unresolved = tuple(cell for cell in cells if cell not in values)
    return Derivation(values=values, unresolved=unresolved)


def _bound_one_relation(relations: tuple[Relation, ...], values: dict[str, int]) -> bool:
    """Read each relation on its own against non-negativity. Nothing is carried between them."""
    for relation in relations:
        unknowns = [cell for cell in relation.cells() if cell not in values]
        if not unknowns:
            continue
        for cell in unknowns:
            coefficient = next(weight for name, weight in relation.terms if name == cell)
            known_part = sum(weight * values[name] for name, weight in relation.terms if name in values)
            others = [weight for name, weight in relation.terms if name not in values and name != cell]
            # Everything unknown is somewhere in [0, CELL_CAP], and that is all this step may assume.
            rest_low = sum(min(weight * 0, weight * CELL_CAP) for weight in others)
            rest_high = sum(max(weight * 0, weight * CELL_CAP) for weight in others)
            window_high = relation.constant - known_part - rest_low
            window_low = relation.constant - known_part - rest_high
            # ⚠️⚠️ **v28-P2-01: an inequality bounds one side, and which side depends on the sign.**
            # This computed both ends of a finite window, then for an inequality reset `low` to zero
            # and left `high` alone. That is right only for a *positive* coefficient, where
            # `c*x + rest <= k` genuinely caps `x` from above. With a **negative** coefficient the same
            # relation is a lower bound and says nothing about how large the cell may be, so keeping
            # the equality-derived `high` collapsed an open range onto one fabricated number.
            #
            # `H - AB <= 0` is `AB >= H`. With `H = 0` every non-negative `AB` satisfies it, and this
            # recorded `AB = 0` — a value the relation does not determine, and wrong on any row with a
            # hit. `derive_in_view()` could then call a board human-derivable on invented numbers.
            #
            # ⚠️ **`narrow()` in this same module has always had the rule right** (see its comment on
            # the opposite side being left genuinely open). One rule, two implementations, and they
            # disagreed — so the sides are now derived the same way in both: the bound that always
            # holds, plus the opposite one **only for an equality**.
            if coefficient > 0:
                high = window_high // coefficient
                low = -(-window_low // coefficient) if relation.equality else 0
            else:
                low = -(-window_high // coefficient)
                high = window_low // coefficient if relation.equality else CELL_CAP
            low = max(low, 0)
            if low == high:
                values[cell] = low
                return True
    return False


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
