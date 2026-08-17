"""A solver restricted to the reasoning a person can actually carry out.

This is not a constraint solver that happens to be limited. The limitation is the point: a puzzle
ships only if this solver finishes without ever guessing, because uniqueness alone does not make a
puzzle derivable, and a unique puzzle nobody can reason through is the worst failure the design
admits — it looks correct.

There is no linear T1-to-T5 ladder any more, because it does not describe this system. The 2x2 rung
cannot fire at all: every identity is a sum over a row or a column, so two of them meet at most at
one cell. With that gone, single-unknown solving and propagating it to a fixed point are one
operation rather than two, and the global identity is not a technique but one more equation inside
that propagation. Only bounding is genuinely different, because it reasons over ranges instead of
values.

What replaces the ladder is two axes:

  Technique  — propagation alone, or propagation plus bounding
  Family     — which of column sums, row identity, cross-team and the global identity a solution
               path actually had to use

The publication rule is unchanged in substance: a puzzle ships only if this finishes without
backtracking. Neither axis on its own says how hard a puzzle feels, which is why the solver also
records the shape of the solution path — how long the chain of dependent steps ran, and how narrow
the choice of next move became.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from boxscore_forge.bounds import narrow
from boxscore_forge.constraints import BoardShape, Equation, constrained_cells, equations
from boxscore_forge.errors import ContradictionError
from boxscore_forge.identities import FAMILY_OF, Family, Identity


class Technique(StrEnum):
    """The first axis. Ordered: bounding is only reached for when propagation has stopped."""

    PROPAGATION = "propagation"
    BOUNDING = "bounding"


_TECHNIQUE_ORDER: tuple[Technique, ...] = (Technique.PROPAGATION, Technique.BOUNDING)

# How much of the tail to ignore when reading frontier width. A solution narrows by exhaustion as it
# runs out of cells, not by difficulty: the last step always has one move because one cell is left,
# and the two before it are nearly as forced. Measured over 420 real directions, trimming one step
# still leaves 43% of boards reporting a bottleneck of one; trimming three brings that to 10% and
# the distribution comes out smooth. Anything less and the metric mostly reports its own artefact.
_TAIL_STEPS_IGNORED = 3
_ENOUGH_STEPS_TO_HAVE_HAD_A_CHOICE = _TAIL_STEPS_IGNORED + 1


@dataclass(frozen=True, slots=True)
class Deduction:
    """One cell worked out, and everything about how it was reached.

    `from_identity` is None for a bounding deduction: nothing was computed from one rule there, the
    cell was cornered by the whole board at once, and naming an identity would invent a provenance
    the reasoning never had.

    `depth` is how many dependent steps had to happen first. `frontier` is how many other moves were
    available at the moment this one was taken — a frontier of one means the player had to scan the
    whole board to find the only move there was. `depends_on` names the cells already worked out that
    this one leaned on, which is what makes the solution path a graph rather than a list.
    """

    cell: str
    value: int
    technique: Technique
    from_identity: Identity | None
    depth: int
    frontier: int
    depends_on: frozenset[str]


@dataclass(frozen=True, slots=True)
class Solution:
    values: dict[str, int]
    deductions: tuple[Deduction, ...]
    unsolved: frozenset[str]

    @property
    def is_complete(self) -> bool:
        return not self.unsolved

    @property
    def techniques_used(self) -> frozenset[Technique]:
        return frozenset(deduction.technique for deduction in self.deductions)

    @property
    def hardest_technique(self) -> Technique | None:
        """The first axis. None when nothing had to be deduced at all."""
        if not self.deductions:
            return None
        return max(self.techniques_used, key=_TECHNIQUE_ORDER.index)

    @property
    def families_used(self) -> frozenset[Family]:
        """The second axis: which kinds of reasoning the path needed, not which were available."""
        return frozenset(
            FAMILY_OF[deduction.from_identity]
            for deduction in self.deductions
            if deduction.from_identity is not None and deduction.from_identity in FAMILY_OF
        )

    @property
    def times_used(self) -> dict[Technique, int]:
        counts = dict.fromkeys(_TECHNIQUE_ORDER, 0)
        for deduction in self.deductions:
            counts[deduction.technique] += 1
        return counts

    @property
    def family_counts(self) -> dict[Family, int]:
        counts = dict.fromkeys(Family, 0)
        for deduction in self.deductions:
            if deduction.from_identity is not None and deduction.from_identity in FAMILY_OF:
                counts[FAMILY_OF[deduction.from_identity]] += 1
        return counts

    @property
    def chain_length(self) -> int:
        """The longest run of steps that each had to wait for the one before it.

        Ten cells recovered in ten independent steps is a different puzzle from ten recovered in a
        chain of ten, and cell count alone cannot tell them apart.
        """
        return max((deduction.depth for deduction in self.deductions), default=0)

    @property
    def narrowest_frontier(self) -> int | None:
        """The tightest the choice of next move ever got, ignoring the final step.

        The hypothesis is that this predicts perceived difficulty better than anything else here: a
        board that bottlenecks to a single available move, even once, makes the player scan
        everything to find it.

        The last step is excluded because it is always forced — when one cell remains there is by
        definition one move — so including it would report a bottleneck on every board ever solved
        and separate nothing from anything. None when the board was never in a position to offer a
        choice at all.
        """
        if len(self.deductions) < _ENOUGH_STEPS_TO_HAVE_HAD_A_CHOICE:
            return None
        return min(deduction.frontier for deduction in self.deductions[:-_TAIL_STEPS_IGNORED])

    @property
    def mean_frontier(self) -> float | None:
        """How much choice the player had on average, over the steps where there was any to have."""
        if len(self.deductions) < _ENOUGH_STEPS_TO_HAVE_HAD_A_CHOICE:
            return None
        kept = self.deductions[:-_TAIL_STEPS_IGNORED]
        return sum(deduction.frontier for deduction in kept) / len(kept)


def solve(shape: BoardShape, given: Mapping[str, int]) -> Solution:
    """Deduce as far as the implemented reasoning reaches, and stop.

    Whatever remains in `unsolved` is not a failure of arithmetic — it is the honest statement that
    a person restricted to this reasoning could not get there either.
    """
    values = dict(given)
    system = tuple(equation for equation in equations(shape) if not equation.is_global)
    global_equations = tuple(equation for equation in equations(shape) if equation.is_global)
    deductions: list[Deduction] = []
    depths: dict[str, int] = {}

    # Givens that already disagree are caught here rather than later by bounding, so the complaint
    # names the identity that broke instead of whichever cell happened to run out of room first.
    _reject_contradictions(system, values)

    while True:
        deduction = _next_step(shape, system, global_equations, values, depths)
        if deduction is None:
            break
        values[deduction.cell] = deduction.value
        depths[deduction.cell] = deduction.depth
        deductions.append(deduction)

    _reject_contradictions(system, values)
    return Solution(
        values=values,
        deductions=tuple(deductions),
        unsolved=frozenset(constrained_cells(shape) - values.keys()),
    )


def _next_step(
    shape: BoardShape,
    system: tuple[Equation, ...],
    global_equations: tuple[Equation, ...],
    values: Mapping[str, int],
    depths: Mapping[str, int],
) -> Deduction | None:
    """Propagation first, always, and only then bounding.

    An exact value beats a narrowed range: taking the bounded move while a plain subtraction is
    still available would credit the harder technique for work the easier one could have done.
    """
    available = _propagation_moves(system + global_equations, values)
    if available:
        cell, equation = available[0]
        leaned_on = frozenset(term.cell for term in equation.terms if term.cell != cell and term.cell in depths)
        return Deduction(
            cell=cell,
            value=_forced_value(equation, cell, values),
            technique=Technique.PROPAGATION,
            from_identity=equation.origin,
            depth=1 + max((depths[earlier] for earlier in leaned_on), default=0),
            frontier=len(available),
            depends_on=leaned_on,
        )

    bounded = _bounding_moves(shape, values)
    if bounded:
        cell, value = bounded[0]
        return Deduction(
            cell=cell,
            value=value,
            technique=Technique.BOUNDING,
            from_identity=None,
            # Narrowing draws on the whole board, so the honest answer is that it leaned on
            # everything worked out so far rather than on one equation's terms.
            depth=1 + max(depths.values(), default=0),
            frontier=len(bounded),
            depends_on=frozenset(depths),
        )
    return None


def _propagation_moves(system: tuple[Equation, ...], values: Mapping[str, int]) -> list[tuple[str, Equation]]:
    """Every cell some equation forces right now. Its length is the frontier width."""
    moves: dict[str, Equation] = {}
    for equation in system:
        unknowns = equation.unknowns(values)
        if len(unknowns) == 1 and unknowns[0] not in moves:
            moves[unknowns[0]] = equation
    return sorted(moves.items())


def _bounding_moves(shape: BoardShape, values: Mapping[str, int]) -> list[tuple[str, int]]:
    """Every cell whose range has closed to one value. The global identity stays out of the
    narrowing for the same reason it stays out of propagation's first pass."""
    domains = narrow(shape, values)
    return sorted(
        (cell, bounds.fixed_value)
        for cell, bounds in domains.items()
        if cell not in values and bounds.fixed_value is not None
    )


def _forced_value(equation: Equation, cell: str, values: Mapping[str, int]) -> int:
    """Move every known term across and divide by the unknown's coefficient.

    Every coefficient in this system is 1 or -1, so the division is exact by construction and a
    fractional result is not a case that can arise.
    """
    coefficient = next(term.coefficient for term in equation.terms if term.cell == cell)
    known = sum(term.coefficient * values[term.cell] for term in equation.terms if term.cell != cell)
    return (equation.constant - known) // coefficient


def _reject_contradictions(system: tuple[Equation, ...], values: Mapping[str, int]) -> None:
    """An equation with nothing unknown left in it must balance."""
    for equation in system:
        if equation.unknowns(values):
            continue
        residual = equation.residual(values)
        if residual != 0:
            message = f"{equation.origin} is off by {residual} with every cell in it known"
            raise ContradictionError(message)
