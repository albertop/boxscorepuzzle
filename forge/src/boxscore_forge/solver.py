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
    equations_live: int
    equations_solvable: int
    known_terms_combined: int | None
    needed_global_identity: bool = False
    """Whether this step could only be made once `PA = Outs + R + LOB` was admitted.

    Only ever true of a bounding step. Propagation names the identity it used, so the family axis
    already carries the answer there; bounding names none, and without this the global relation could
    decide a cell and leave no trace in `families_used`.

    Not folded into `from_identity`. A bound is not derived *from* one relation — it is what the whole
    board leaves standing — and naming one would invent a provenance the reasoning never had.
    """

    @property
    def search_cost(self) -> float | None:
        """How hard this move was to *find*, as a share of the board that led nowhere.

        Zero when every live equation was ready to give; approaching one when almost none were. It is
        deliberately a fraction rather than a count: an earlier version divided live equations by
        ready ones, which grows without bound as a board empties out, so it smuggled the board's
        emptiness back in through the numerator and correlated with zero density all over again.

        None for a bounding step, whose moves are narrowed domains rather than ready equations and
        so are not on this scale.
        """
        if not self.has_a_comparable_cost or self.equations_live == 0:
            return None
        return 1.0 - self.equations_solvable / self.equations_live

    @property
    def resolution_cost(self) -> int | None:
        """How hard the arithmetic was once the move had been found: how many additions it took.

        Combining k numbers takes k-1 additions, so a value copied or a zero falling out of an empty
        column costs nothing. Kept apart from search cost on purpose — scanning and calculating are
        different activities, and the data says a step can be free to resolve and expensive to find.
        """
        if self.known_terms_combined is None:
            return None
        return max(self.known_terms_combined - 1, 0)

    @property
    def is_trivial(self) -> bool:
        """Whether the step required any arithmetic at all.

        A column that sums to nothing forces every blank in it, and an equation with a single
        non-zero known is a value copied rather than computed. Neither asks the player to combine
        anything, so neither is difficulty however long the cascade of them runs. This is structural
        rather than a heuristic: it counts the non-zero numbers the deduction had to add up.

        Undefined for a bounding step, which combines no particular set of terms. Those are left out
        of the cost metric and counted on their own rather than given a flattering number.
        """
        return self.known_terms_combined is not None and self.known_terms_combined <= 1

    @property
    def has_a_comparable_cost(self) -> bool:
        """Whether this step's cost belongs in the same scale as the others.

        Bounding does not: it draws on the whole board rather than on one equation, so any scan cost
        assigned to it would be an invention, and under a metric that takes the maximum a single
        invented number would decide the board's score.
        """
        return self.known_terms_combined is not None


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
        """The second axis: which kinds of reasoning the path needed, not which were available.

        A bounding step that only came out once the global identity was admitted counts as having
        used it. It names no identity of its own, so before this the global family could decide cells
        on a board that reported never having touched it.
        """
        named = frozenset(
            FAMILY_OF[deduction.from_identity]
            for deduction in self.deductions
            if deduction.from_identity is not None and deduction.from_identity in FAMILY_OF
        )
        if any(deduction.needed_global_identity for deduction in self.deductions):
            return named | {Family.GLOBAL_IDENTITY}
        return named

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
    def hardest_search(self) -> float | None:
        """The move that took the most looking for. Applies to every step, trivial or not.

        Kept apart from resolution rather than folded into one index. Searching and calculating are
        different things to a player, and measured they behave differently: steps that ask for no
        arithmetic at all are, on average, the *most* expensive ones to find. An index that zeroed
        both together threw that away.

        A maximum rather than a total, because a sum grows with the number of steps and a board of
        forty cheap ones would outscore one with three hard ones.
        """
        return _largest(self._search_costs)

    @property
    def ninetieth_percentile_search(self) -> float | None:
        """The same, less hostage to one freak step."""
        return _percentile(self._search_costs)

    @property
    def hardest_resolution(self) -> int | None:
        """The most arithmetic any single step demanded."""
        return _largest(self._resolution_costs)

    @property
    def ninetieth_percentile_resolution(self) -> int | None:
        return _percentile(self._resolution_costs)

    @property
    def _search_costs(self) -> list[float]:
        return sorted(cost for cost in (deduction.search_cost for deduction in self.deductions) if cost is not None)

    @property
    def _resolution_costs(self) -> list[int]:
        return sorted(cost for cost in (deduction.resolution_cost for deduction in self.deductions) if cost is not None)

    @property
    def stalls(self) -> int:
        """How many times propagation ran dry — **the difficulty variable**.

        A stall is the *transition*: subtraction had nothing left to work on and something beyond it
        was needed to restart. A run of consecutive bounding steps is **one** stall, because the
        player stopped once and had to think once. Counting the steps instead inflates the figure by
        between 1.6 and 2.6 times, measured, and would make a standard of five accept a board that
        stops the player twice.

        ⚠️ This is what chain length was standing in for and could not do. Chain counts how long a
        solve is: a chain-10 board is ten subtractions in single file, and one was solved by hand in
        under a minute. The stall is where the thinking happens.
        """
        count = 0
        previous_was_bounding = False
        for step in self.deductions:
            bounding = step.technique is Technique.BOUNDING
            if bounding and not previous_was_bounding:
                count += 1
            previous_was_bounding = bounding
        return count

    @property
    def bounding_steps(self) -> int:
        """Counted rather than costed, because their difficulty is not on the same scale."""
        return sum(1 for deduction in self.deductions if not deduction.has_a_comparable_cost)

    @property
    def trivial_share(self) -> float | None:
        """What fraction of the solve asked the player to combine nothing."""
        if not self.deductions:
            return None
        return sum(1 for deduction in self.deductions if deduction.is_trivial) / len(self.deductions)

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


def _largest[T: (int, float)](costs: list[T]) -> T | None:
    return costs[-1] if costs else None


def _percentile[T: (int, float)](costs: list[T]) -> T | None:
    return costs[min(int(0.9 * len(costs)), len(costs) - 1)] if costs else None


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
    # ⚠️ **Two phases, and the order is the finding.** `constraints.py` says the global identity is
    # held back until the simpler families are exhausted, and this function used to recombine the two
    # sets on its first line — so a global move could be taken while a column sum or a row identity
    # was still available. The board still reached the right numbers; the *recorded path* was not one
    # a player would follow, and that path is where chain length, family usage and stall position all
    # come from. A measurement-correctness defect rather than a stylistic one.
    #
    # `PA = Outs + R + LOB` is the identity §8 teaches last because nobody knows it. Crediting it for
    # work a subtraction could have done overstates what the board demanded.
    # ⚠️ Measured over the phase that supplied the move, not over the whole board. Search cost is
    # how much of what the player scanned led nowhere, so counting relations they had not reached for
    # yet inflates the cost of every move found without them.
    available = _propagation_moves(system, values)
    scanned = system if available else system + global_equations
    if not available:
        available = _propagation_moves(scanned, values)
    live, solvable = _scan_size(scanned, values)

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
            equations_live=live,
            equations_solvable=solvable,
            known_terms_combined=sum(1 for term in equation.terms if term.cell != cell and values[term.cell] != 0),
        )

    # Bounding is admitted only after propagation has nothing left in either phase, and it takes the
    # same two phases for the same reason: a cell that the board corners without `PA = Outs + R + LOB`
    # did not need it, and crediting it anyway overstates what the puzzle demanded.
    bounded = _bounding_moves(shape, values, system)
    needed_global = False
    if not bounded:
        bounded = _bounding_moves(shape, values, system + global_equations)
        needed_global = True
    if bounded:
        cell, value = bounded[0]
        return Deduction(
            cell=cell,
            value=value,
            technique=Technique.BOUNDING,
            from_identity=None,
            needed_global_identity=needed_global,
            # Narrowing draws on the whole board, so the honest answer is that it leaned on
            # everything worked out so far rather than on one equation's terms.
            depth=1 + max(depths.values(), default=0),
            frontier=len(bounded),
            depends_on=frozenset(depths),
            equations_live=live,
            equations_solvable=len(bounded),
            # Not applicable rather than expensive. Bounding reaches for the whole board instead of
            # one equation, so any number here would be invented, and under a metric that takes the
            # maximum an invented number would decide the score.
            known_terms_combined=None,
        )
    return None


def _scan_size(system: tuple[Equation, ...], values: Mapping[str, int]) -> tuple[int, int]:
    """How many equations still have anything unknown in them, and how many are ready to give."""
    live = solvable = 0
    for equation in system:
        unknowns = len(equation.unknowns(values))
        if unknowns:
            live += 1
        if unknowns == 1:
            solvable += 1
    return live, solvable


def _propagation_moves(system: tuple[Equation, ...], values: Mapping[str, int]) -> list[tuple[str, Equation]]:
    """Every cell some equation forces right now. Its length is the frontier width."""
    moves: dict[str, Equation] = {}
    for equation in system:
        unknowns = equation.unknowns(values)
        if len(unknowns) == 1 and unknowns[0] not in moves:
            moves[unknowns[0]] = equation
    return sorted(moves.items())


def _bounding_moves(
    shape: BoardShape, values: Mapping[str, int], system: tuple[Equation, ...]
) -> list[tuple[str, int]]:
    """Every cell whose range has closed to one value, under the relations it is given.

    The caller passes the phase's relations rather than this choosing them. It used to claim the
    global identity stayed out while `narrow` put it in, and a docstring that contradicts the function
    it calls three lines later is worse than none: it reads as a guarantee.
    """
    domains = narrow(shape, values, system=system)
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
