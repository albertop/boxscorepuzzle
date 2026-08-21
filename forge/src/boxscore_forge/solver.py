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
from boxscore_forge.constraints import (
    BoardShape,
    Equation,
    batting_cell,
    batting_total_cell,
    constrained_cells,
    equations,
)
from boxscore_forge.errors import ContradictionError
from boxscore_forge.identities import FAMILY_OF, Family, Identity


class Technique(StrEnum):
    """The first axis. Ordered easiest first: each is reached only when the ones before it are dry."""

    LINEUP_ARITHMETIC = "lineup_arithmetic"
    """Read the team's plate-appearance total, divide by nine, write the slot down.

    ⚠️ **Its own technique because it is the *easiest* move on the board, and it would otherwise have
    been recorded as the hardest.** Every deduction reached through an inequality is `BOUNDING`, so the
    cyclic step would have counted as a stall — inverting the exact distinction the batting-order
    experiment exists to draw. Four turns of nine and a remainder is not reasoning; it is arithmetic a
    player does once and then applies nine times without looking at the board.

    ⚠️ **This is why the constraint's worth depends on the PA total being erased.** With the total
    given, those nine cells are typed rather than deduced.
    """

    PROPAGATION = "propagation"
    BOUNDING = "bounding"


_TECHNIQUE_ORDER: tuple[Technique, ...] = (
    Technique.LINEUP_ARITHMETIC,
    Technique.PROPAGATION,
    Technique.BOUNDING,
)

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
        """How many steps each kind of reasoning supplied. Consistent with `families_used` by
        construction.

        ⚠️ **These two used to disagree.** `families_used` counts a bounding step that needed the
        global relation; this counted only `from_identity`, which is `None` for every bounding step. So
        one immutable result could say the global family was required and return a count of zero for
        it, and two plausible consumers would reach opposite conclusions from the same solve.

        The contract is *participation*: a step counts for a family if that family is why it was
        available. A global-assisted bound is one such step. `test_solver.py` asserts the two
        properties agree rather than trusting that they do.
        """
        counts = dict.fromkeys(Family, 0)
        for deduction in self.deductions:
            if deduction.from_identity is not None and deduction.from_identity in FAMILY_OF:
                counts[FAMILY_OF[deduction.from_identity]] += 1
            elif deduction.needed_global_identity:
                counts[Family.GLOBAL_IDENTITY] += 1
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
        """Counted rather than costed, because their difficulty is not on the same scale.

        ⚠️⚠️ **Counted by technique, because the cost proxy stopped meaning what it used to.** This read
        `not has_a_comparable_cost`, which was *equivalent* to `technique is BOUNDING` while bounding was
        the only step with no comparable cost. `LINEUP_ARITHMETIC` also has none — reading a total and
        dividing by nine combines no terms — so a total-visible board reported **nine bounding steps
        while using zero**, and `stalls`, which checks the technique, said zero on the same solution.
        Two public metrics disagreeing about one board.

        That is the exact inversion `LINEUP_ARITHMETIC` was introduced to remove, surviving one property
        away from where it was fixed: **the cheapest move on the board counted as the dearest.** The
        lesson is not about this line. An equivalence held by circumstance is a second definition of the
        thing, and it breaks the moment the circumstance changes — silently, because both readings have been
        true for years.

        **Technique identity is the contract; cost availability is no longer equivalent to it.**
        """
        return sum(1 for deduction in self.deductions if deduction.technique is Technique.BOUNDING)

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


_PERCENTILE = 0.9
_ENOUGH_FOR_A_PERCENTILE = 10
"""Below this many costed steps the 90th percentile **is** the maximum, by arithmetic.

⚠️ Nearest-rank puts the p90 at index `ceil(0.9n) - 1`, which is `n - 1` for every `n < 10`. That is
not a defect to fix — with four costed steps there is no freak step for a percentile to be robust
against — but it is a fact the reader of the number has to have, because §31 grades on it and
`CLAUDE.md` says *p90, never max — the max is 8 or 9 on every board*.

**Measured when this was written:** solving `cubs_at_braves_1968` at every target from 1 to 12 across
five seeds, 4 of 34 boards fall below the floor — **all of them at target 1 or 2**, which are two of
the six rungs in `STALL_TARGETS`. So the two easiest rungs report a maximum under a name promising
otherwise, and against a metric whose maximum barely varies they look like the hard ones.

⚠️⚠️ **This number came from the run and not from the reasoning, which is the reason the run was worth
doing.** It was written as 11 first, from the algebra of the defect: `int(0.9n) == n - 1` holds for
every `n <= 10`, so eleven looked like where the collapse ends. That algebra is about the **old**
formula. The floor is a property of the **new** one — nearest rank puts the p90 at `ceil(0.9n) - 1`,
which at `n = 10` is index 8 and no longer the last — so the collapse ends one step sooner and the
floor is 10.

**Both numbers are defensible from a sentence, and only one is true of the code.** The test below the
fix pins it from both sides — every size under the floor must return the maximum, and the floor itself
must not — so the off-by-one cannot come back by being reasoned about again.
"""


def _percentile[T: (int, float)](costs: list[T]) -> T | None:
    """The 90th percentile by nearest rank, or `None` when there is nothing to take it of.

    ⚠️⚠️ **This read `costs[min(int(0.9 * n), n - 1)]` and was wrong in two directions.** (v36-P3-40)

    For every `n <= 10`, `int(0.9n) == n - 1`, so it returned the **maximum** — the exact degenerate
    value the p90 exists to avoid. And for larger `n` it was off by one the other way: `int(0.9 * 20)`
    is 18, the nineteenth of twenty values, which is nearer the 95th percentile than the 90th.

    Nearest rank is `ceil(p * n) - 1`. The `min` stays as a guard, not as the rule.
    """
    if not costs:
        return None
    rank = -(-int(_PERCENTILE * 100) * len(costs) // 100)  # ceil, in integers
    return costs[min(rank - 1, len(costs) - 1)]


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
    # ⚠️ **Every relation, including the global one.** Holding `PA = Outs + R + LOB` back is about
    # which move a *player* would find next; it has nothing to do with whether the board is
    # consistent. Validating with the same restricted system let a complete board with only LOB wrong
    # return a finished solution: the global equation has no unknowns, so it offers no move, and
    # nothing ever checked that it balanced. The reason was sound for selection and travelled to
    # validation, where it is not.
    _reject_contradictions(system + global_equations, values)

    while True:
        deduction = _next_step(shape, system, global_equations, values, depths)
        if deduction is None:
            break
        values[deduction.cell] = deduction.value
        depths[deduction.cell] = deduction.depth
        deductions.append(deduction)

    # ⚠️ **Every relation, including the global one.** Holding `PA = Outs + R + LOB` back is about
    # which move a *player* would find next; it has nothing to do with whether the board is
    # consistent. Validating with the same restricted system let a complete board with only LOB wrong
    # return a finished solution: the global equation has no unknowns, so it offers no move, and
    # nothing ever checked that it balanced. The reason was sound for selection and travelled to
    # validation, where it is not.
    _reject_contradictions(system + global_equations, values)
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
    # ⚠️ **Before propagation, because it is cheaper than a subtraction.** Reading one number and
    # dividing by nine is the first thing a player does once the total is visible; taking it later would
    # credit propagation for work this did.
    lineup = _lineup_moves(shape, values)
    if lineup:
        cell, value, companions = lineup[0]
        # ⚠️ **The rows subtracted, not only the rule that authorised the move.** A shared slot is
        # computed as *the slot's total less the rows already known*, so those rows are part of the
        # arithmetic — and this recorded only the team total. On a substitution-heavy board the edge
        # and its depth were lost, and `chain_length` understated the path that produced the number.
        # The value was right; **the recorded graph was not the one that reached it**, which is exactly
        # what an instrument comparing chains is reading.
        #
        # ⚠️ Deduced cells only, which is the convention propagation already follows: a given was not
        # *reached*, so it is not an edge. The total is frequently a given and was being added anyway.
        leaned_on = frozenset(
            earlier for earlier in (batting_total_cell("plate_appearances"), *companions) if earlier in depths
        )
        return Deduction(
            cell=cell,
            value=value,
            technique=Technique.LINEUP_ARITHMETIC,
            from_identity=Identity.BATTING_ORDER,
            depth=1 + max((depths[earlier] for earlier in leaned_on), default=0),
            frontier=len(lineup),
            depends_on=leaned_on,
            equations_live=0,
            equations_solvable=0,
            known_terms_combined=None,
        )

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
            # ⚠️⚠️ **Measured over the phase that supplied the move, which is this module's own rule.**
            # (v36-P3-42) `live` above is counted over `system + global_equations`, because that is
            # what propagation last scanned — and it was being stored on this bounding deduction even
            # when `_bounding_moves` succeeded on `system` alone with `needed_global=False`. So a step
            # that demonstrably did not need `PA = Outs + R + LOB` reported a scan that included it,
            # overstating what the puzzle demanded in the one field meant to say what it demanded.
            equations_live=_scan_size(system + global_equations if needed_global else system, values)[0],
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


def _lineup_moves(shape: BoardShape, values: Mapping[str, int]) -> list[tuple[str, int, tuple[str, ...]]]:
    """Slots that the team's plate-appearance total settles outright.

    ⚠️⚠️ **The relations alone are exact and inert, which is the whole reason this exists.**
    Monotonicity plus a spread of one describes the feasible set perfectly, and interval propagation
    cannot *reach* it: with a total of 39 every slot's domain is `0..39`, each adjacent inequality
    compares two intervals that already overlap, and the fixed point leaves all nine untouched.
    **Measured rather than assumed — the solver deduced 0 of 9.**

    A model can be exactly right and deduce nothing, and **satisfaction tests cannot tell those apart**
    because they never ask the solver anything. The tests written for the relations checked that valid
    vectors satisfy them and impossible ones do not; none called `solve()`.

    So the arithmetic is done directly. `divmod(total, 9)` gives every slot's sum, and a slot with one
    unknown row left has that row's value.

    ⚠️ **Nothing at all without slots**, which keeps production exactly as it was.
    """
    if not shape.slots:
        return []
    total = values.get(batting_total_cell("plate_appearances"))
    if total is None:
        return []

    rows_in: dict[int, list[int]] = {}
    for index, slot in enumerate(shape.slots):
        rows_in.setdefault(slot, []).append(index)

    base, over = divmod(total, len(rows_in))
    found: list[tuple[str, int, tuple[str, ...]]] = []
    for position, slot in enumerate(sorted(rows_in), start=1):
        wanted = base + 1 if position <= over else base
        cells = [batting_cell(index, "plate_appearances") for index in rows_in[slot]]
        unknown = [cell for cell in cells if cell not in values]
        # One row still open: the slot's total less the rest. Two open rows are a sum the ordinary
        # machinery can carry, and splitting it here would be a guess.
        if len(unknown) == 1:
            known = tuple(cell for cell in cells if cell in values)
            value = wanted - sum(values[cell] for cell in known)
            if value >= 0:
                # The companions travel with the move: they are what the subtraction used.
                found.append((unknown[0], value, known))
    return found


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
