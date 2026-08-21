"""How small a range each cell can be squeezed into, given everything else on the board.

This is the machinery behind the fourth rung. A player who cannot compute a cell outright can often
still rule values out — a column with two blanks that add to nothing has two zeros in it, and a
batter with three at-bats has at most three hits. When the ruling-out leaves exactly one value
standing, the cell is deduced without ever having been calculated.

Narrowing is monotone: a lower bound only rises, an upper bound only falls, and the true value is
never excluded. That last part is what makes it safe to deduce from, and it is under property test.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Final

from boxscore_forge.constraints import (
    BoardShape,
    Equation,
    Inequality,
    Term,
    all_cells,
    equations,
    inequalities,
)
from boxscore_forge.errors import ContradictionError


@dataclass(frozen=True, slots=True)
class Bounds:
    """The range a cell could still be in. `high` of None means nothing caps it yet."""

    low: int
    high: int | None

    @property
    def fixed_value(self) -> int | None:
        """The only value left open, if there is exactly one."""
        return self.low if self.high == self.low else None

    @property
    def is_empty(self) -> bool:
        return self.high is not None and self.low > self.high


_PASSES_PER_CELL: Final = 4
"""Tightening passes allowed per cell before the system is called contradictory. **Measured.**

The worst of 10,442 real calls took 5 passes over 143 cells — 0.035 per cell. This is 114x that.
"""

_MINIMUM_PASSES: Final = 64
"""A floor, so a small shape is not held to a tighter bound than a large one. **Chosen, not measured.**"""


def narrow(
    shape: BoardShape,
    given: Mapping[str, int],
    *,
    system: tuple[Equation, ...] | None = None,
) -> dict[str, Bounds]:
    """Squeeze every cell as far as the given relations and the inequalities allow.

    ⚠️ **`system` used to be implicit, and the docstring here contradicted the one in the caller.**
    This said the global identity was in with everything else and justified it by saying that which
    puzzles needed it is recorded on the family axis. `solver._bounding_moves` said the opposite three
    lines above the call. The code followed this one.

    The justification was the part that was wrong. It holds for propagation, where every deduction
    names the identity it came from, and it does not hold here: a bounding deduction carries no
    identity, so the global relation could corner a cell without ever appearing in `families_used`.
    A phase that reports nothing cannot be audited by the report.

    So the caller now says which relations the player is using, and `None` means every relation on the
    board. That default is the mathematically complete answer rather than a permissive one — omitting
    the argument narrows *harder*, never further than the board allows.
    """
    domains = {
        cell: Bounds(given[cell], given[cell]) if cell in given else Bounds(0, None) for cell in all_cells(shape)
    }
    relations = equations(shape) if system is None else system
    bounds_rules = inequalities(shape)

    # ⚠️⚠️ **Bounded, because an inconsistent system made this loop run for ever.** (v36-P2-01)
    #
    # Every unknown is seeded `Bounds(0, None)` — no upper bound is claimed, which is the honest
    # starting state. But `is_empty` needs `high is not None`, so on a contradictory cycle among cells
    # that never acquire an upper bound the lower bounds climb by a positive constant every pass and
    # **nothing ever reports the contradiction**. `a = b + 1` with `b = a + 1` does it.
    #
    # `erase()` reaches `solve()` on directions loaded from the database *before* any layer-1
    # validation, and `erasure.py` promises a broken boxscore "fails loud" via `ContradictionError`.
    # In this shape it hung the batch instead — **worse than the crash that was promised**, because a
    # hang has no message and no exit code.
    #
    # ⚠️ **The seeding is deliberately not changed.** The verifier's twin is immune because it seeds
    # every unknown `(0, CELL_CAP)`, and copying that here would narrow *harder* — a different answer
    # about which boards are solvable, which would silently move the pool and invalidate every
    # difficulty measurement taken so far. The loop is bounded; the arithmetic is untouched.
    #
    # **The cap is measured.** Over 10,442 real `narrow()` calls, solving `cubs_at_braves_1968` erased
    # to every target from 1 to 12 across three seeds: **the worst call took 5 passes** on a 143-cell
    # board, 0.035 passes per cell. Four per cell is **114 times** the observed maximum, and the floor
    # of 64 keeps a tiny shape from being capped tighter than a large one. A bound that could reject a
    # real board would get raised until it said nothing.
    ceiling = max(_MINIMUM_PASSES, _PASSES_PER_CELL * len(domains))
    for _ in range(ceiling):
        if not _tighten_once(domains, relations, bounds_rules):
            return domains
    message = (
        f"bounding did not settle in {ceiling} passes over {len(domains)} cells. "
        f"The measured worst case is 0.035 passes per cell, so this is a contradictory system whose "
        f"cells have no upper bound rather than a slow one."
    )
    raise ContradictionError(message)


def _tighten_once(domains: dict[str, Bounds], system: Iterable[Equation], bounds_rules: Iterable[Inequality]) -> bool:
    changed = False
    for equation in system:
        for term in equation.terms:
            changed |= _apply(domains, term.cell, _from_equation(domains, equation, term))
    for inequality in bounds_rules:
        for term in inequality.terms:
            changed |= _apply(domains, term.cell, _from_inequality(domains, inequality, term))
    return changed


def _from_equation(domains: Mapping[str, Bounds], equation: Equation, target: Term) -> Bounds:
    """What the equation alone says about the target, given where the other terms can reach.

    With the target moved to one side, its coefficient times its value equals the constant minus
    everything else, so the widest the others can swing is exactly how much room the target has.
    """
    others = tuple(term for term in equation.terms if term.cell != target.cell)
    lowest, highest = _reach(domains, others)
    return _divide(
        low=_subtract(equation.constant, highest),
        high=_subtract(equation.constant, lowest),
        coefficient=target.coefficient,
    )


def _from_inequality(domains: Mapping[str, Bounds], inequality: Inequality, target: Term) -> Bounds:
    """An inequality gives one side only: the target must at least offset the rest.

    ⚠️ The zero this used to subtract from was the constant, assumed absent. It is a field now, so a
    bound like *at most one apart* propagates instead of being inexpressible.
    """
    others = tuple(term for term in inequality.terms if term.cell != target.cell)
    _, highest = _reach(domains, others)
    limit = _subtract(-inequality.constant, highest)
    if target.coefficient > 0:
        return Bounds(limit if limit is not None else 0, None)
    return Bounds(0, None if limit is None else -limit)


def _reach(domains: Mapping[str, Bounds], terms: Iterable[Term]) -> tuple[int | None, int | None]:
    """The lowest and highest the given terms can sum to. None on either side means unbounded."""
    lowest: int | None = 0
    highest: int | None = 0
    for term in terms:
        bounds = domains[term.cell]
        if term.coefficient > 0:
            lowest = _add(lowest, bounds.low)
            highest = _add(highest, bounds.high)
        else:
            lowest = _add(lowest, None if bounds.high is None else -bounds.high)
            highest = _add(highest, -bounds.low)
    return lowest, highest


def _divide(low: int | None, high: int | None, coefficient: int) -> Bounds:
    """Every coefficient in this system is 1 or -1, so this only ever divides by one or flips."""
    if coefficient > 0:
        return Bounds(low if low is not None else 0, high)
    flipped_low = None if high is None else -high
    return Bounds(flipped_low if flipped_low is not None else 0, None if low is None else -low)


def _apply(domains: dict[str, Bounds], cell: str, candidate: Bounds) -> bool:
    """Keep the tighter of what we had and what was just derived, and refuse an empty result."""
    current = domains[cell]
    low = max(current.low, candidate.low)
    high = _tighter_upper(current.high, candidate.high)
    if (low, high) == (current.low, current.high):
        return False

    tightened = Bounds(low, high)
    if tightened.is_empty:
        message = f"{cell} has no value left open to it: {low} to {high}"
        raise ContradictionError(message)
    domains[cell] = tightened
    return True


def _tighter_upper(current: int | None, candidate: int | None) -> int | None:
    if current is None:
        return candidate
    if candidate is None:
        return current
    return min(current, candidate)


def _add(first: int | None, second: int | None) -> int | None:
    return None if first is None or second is None else first + second


def _subtract(constant: int, amount: int | None) -> int | None:
    return None if amount is None else constant - amount
