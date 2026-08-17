"""A solver restricted to the techniques a person can actually carry out.

This is not a constraint solver that happens to be limited. The limitation is the point: a puzzle
ships only if this solver finishes without ever guessing, because uniqueness alone does not make a
puzzle derivable, and a unique puzzle nobody can reason through is the worst failure the design
admits — it looks correct.

The ladder is walked from the bottom on every pass. A technique is only reached for when everything
below it has stopped making progress, which is how a person solves and the only way the record of
"highest technique required" means anything. Admitting the global team identity alongside the column
sums would have the easiest rule crack the hardest step, and every puzzle would look trivial.

There is no rung for solving a 2x2 system. It is not an omission: no two equations on this board
share more than one cell, so no pair of them ever has the same two unknowns. A test in
`test_constraints` holds that line, and will fail if a board change makes the rung reachable.

So far the ladder has three rungs: a single unknown in an equation, the same rule propagated to a
fixed point, and narrowing a cell's range until one value is left standing.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from boxscore_forge.bounds import narrow
from boxscore_forge.constraints import BoardShape, Equation, constrained_cells, equations
from boxscore_forge.errors import ContradictionError
from boxscore_forge.identities import Identity


class Technique(StrEnum):
    """The ladder. Order is meaningful: a solver reaches for the lowest rung that still moves.

    The values are the design's labels, and T3 is absent because this board cannot use it.
    """

    SINGLE_UNKNOWN = "T1"
    PROPAGATION = "T2"
    BOUNDING = "T4"


_LADDER: tuple[Technique, ...] = (Technique.SINGLE_UNKNOWN, Technique.PROPAGATION, Technique.BOUNDING)


@dataclass(frozen=True, slots=True)
class Deduction:
    """One cell worked out, and what it took to get there.

    `from_identity` is None for a bounding deduction. Nothing was computed from one rule there: the
    cell was cornered by everything on the board at once, and naming a single identity would be
    inventing a provenance the reasoning never had.
    """

    cell: str
    value: int
    technique: Technique
    from_identity: Identity | None


@dataclass(frozen=True, slots=True)
class Solution:
    values: dict[str, int]
    deductions: tuple[Deduction, ...]
    unsolved: frozenset[str]

    @property
    def is_complete(self) -> bool:
        return not self.unsolved

    @property
    def highest_technique(self) -> Technique | None:
        """The rung that decides the puzzle's difficulty. None when nothing had to be deduced."""
        if not self.deductions:
            return None
        return max((deduction.technique for deduction in self.deductions), key=_LADDER.index)

    @property
    def times_used(self) -> dict[Technique, int]:
        counts = dict.fromkeys(_LADDER, 0)
        for deduction in self.deductions:
            counts[deduction.technique] += 1
        return counts


def solve(shape: BoardShape, given: Mapping[str, int]) -> Solution:
    """Deduce as far as the implemented techniques reach, and stop.

    Whatever remains in `unsolved` is not a failure of arithmetic — it is the honest statement that
    a person restricted to these techniques could not get there either.
    """
    values = dict(given)
    system = tuple(equation for equation in equations(shape) if not equation.is_global)
    deductions: list[Deduction] = []

    # Givens that already disagree are caught here rather than later by bounding, so the complaint
    # names the identity that broke instead of whichever cell happened to run out of room first.
    _reject_contradictions(system, values)

    while True:
        # The ladder is walked from the bottom every time, so a cell that bounding opens up is
        # picked up again by the cheapest rule rather than by the one that happened to be running.
        deduction = _next_deduction(system, values, given) or _next_bounded_deduction(shape, values)
        if deduction is None:
            break
        values[deduction.cell] = deduction.value
        deductions.append(deduction)

    _reject_contradictions(system, values)
    return Solution(
        values=values,
        deductions=tuple(deductions),
        unsolved=frozenset(constrained_cells(shape) - values.keys()),
    )


def _next_deduction(
    system: tuple[Equation, ...], values: Mapping[str, int], given: Mapping[str, int]
) -> Deduction | None:
    """The first cell any equation forces. Equation order is fixed, so the walk is reproducible."""
    for equation in system:
        unknowns = equation.unknowns(values)
        if len(unknowns) != 1:
            continue
        cell = unknowns[0]
        return Deduction(
            cell=cell,
            value=_forced_value(equation, cell, values),
            technique=_technique_for(equation, cell, given),
            from_identity=equation.origin,
        )
    return None


def _next_bounded_deduction(shape: BoardShape, values: Mapping[str, int]) -> Deduction | None:
    """The first cell whose range has closed to a single value.

    Only one at a time, and then back to the bottom of the ladder. Taking every cornered cell in one
    sweep would be faster and would misreport the puzzle, crediting bounding for cells that a plain
    column sum could have produced once the first of them was known.
    """
    domains = narrow(shape, values)
    for cell in sorted(domains):
        if cell in values:
            continue
        value = domains[cell].fixed_value
        if value is not None:
            return Deduction(cell=cell, value=value, technique=Technique.BOUNDING, from_identity=None)
    return None


def _forced_value(equation: Equation, cell: str, values: Mapping[str, int]) -> int:
    """Move every known term across and divide by the unknown's coefficient.

    Every coefficient in this system is 1 or -1, so the division is exact by construction and a
    fractional result is not a case that can arise.
    """
    coefficient = next(term.coefficient for term in equation.terms if term.cell == cell)
    known = sum(term.coefficient * values[term.cell] for term in equation.terms if term.cell != cell)
    return (equation.constant - known) // coefficient


def _technique_for(equation: Equation, cell: str, given: Mapping[str, int]) -> Technique:
    """Whether this followed straight from the board as printed, or from earlier work.

    A deduction whose equation held nothing but givens is one a player makes on first reading. One
    that leaned on a cell somebody already worked out is a link in a chain, and chaining is what
    separates the second rung from the first.
    """
    leaned_on_earlier_work = any(term.cell != cell and term.cell not in given for term in equation.terms)
    return Technique.PROPAGATION if leaned_on_earlier_work else Technique.SINGLE_UNKNOWN


def _reject_contradictions(system: tuple[Equation, ...], values: Mapping[str, int]) -> None:
    """An equation with nothing unknown left in it must balance."""
    for equation in system:
        if equation.unknowns(values):
            continue
        residual = equation.residual(values)
        if residual != 0:
            message = f"{equation.origin} is off by {residual} with every cell in it known"
            raise ContradictionError(message)
