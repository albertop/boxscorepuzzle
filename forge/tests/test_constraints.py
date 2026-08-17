"""The identities restated as a linear system, which is the form the solver can reason over.

The property that matters here is agreement: the equation system must be exactly as strong as the
equality identities. Weaker, and the solver would call a cell undeducible that a player can in fact
work out. Stronger, and it would deduce from a rule the board never states.
"""

import dataclasses
import itertools

from hypothesis import given

from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import cell_values, equations, shape_of
from boxscore_forge.identities import Identity, find_violations
from tests.strategies import valid_directions
from tests.test_identity_properties import _perturbations

EQUALITY_IDENTITIES = frozenset(
    {
        Identity.BATTING_COLUMN_SUM,
        Identity.PITCHING_COLUMN_SUM,
        Identity.CROSS_TEAM_TOTAL,
        Identity.PLATE_APPEARANCES,
        Identity.LINE_SCORE_RUNS,
        Identity.LINE_SCORE_HITS,
    }
)


def _all_satisfied(direction: Direction) -> bool:
    values = cell_values(direction)
    return all(equation.residual(values) == 0 for equation in equations(shape_of(direction)))


def _breaks_an_equality_identity(direction: Direction) -> bool:
    return any(violation.identity in EQUALITY_IDENTITIES for violation in find_violations(direction))


class TestRealGame:
    def test_every_equation_holds_for_the_real_game(self, cubs_at_braves_1968: Direction) -> None:
        assert _all_satisfied(cubs_at_braves_1968)

    def test_every_cell_named_by_an_equation_exists_on_the_board(self, cubs_at_braves_1968: Direction) -> None:
        # An equation over a cell nobody can see would let the solver deduce from thin air.
        values = cell_values(cubs_at_braves_1968)
        named = {term.cell for equation in equations(shape_of(cubs_at_braves_1968)) for term in equation.terms}

        assert named <= values.keys()


class TestAgreementWithTheIdentities:
    @given(valid_directions())
    def test_every_equation_holds_for_any_balanced_boxscore(self, direction: Direction) -> None:
        assert _all_satisfied(direction)

    @given(valid_directions())
    def test_the_system_is_exactly_as_strong_as_the_equality_identities(self, direction: Direction) -> None:
        disagreements = [
            path
            for path, perturbed in _perturbations(direction, 1)
            if _all_satisfied(perturbed) != (not _breaks_an_equality_identity(perturbed))
        ]

        assert disagreements == []


class TestTheTwoByTwoRungIsUnreachable:
    @given(valid_directions())
    def test_no_two_equations_share_more_than_one_cell(self, direction: Direction) -> None:
        # Solving a 2x2 system needs two equations whose unknowns are the same pair, which needs
        # them to share two cells. Nothing here shares more than one, so that rung of the ladder
        # cannot fire on this board — the constraint graph is tree-like, and every hard step has to
        # come from bounding or from the global identity instead.
        #
        # This is a tripwire, not a decoration. If the board ever gains a column or moves the
        # footnotes to per-player attribution, overlaps appear, the rung becomes reachable, and this
        # failing is the notice that it now has to be implemented.
        system = equations(shape_of(direction))
        overlaps = [
            (first.origin, second.origin, sorted(shared))
            for first, second in itertools.combinations(system, 2)
            if len(shared := {term.cell for term in first.terms} & {term.cell for term in second.terms}) > 1
        ]

        assert overlaps == []


class TestShape:
    def test_equations_depend_on_the_shape_and_not_on_the_values(self, cubs_at_braves_1968: Direction) -> None:
        # The solver is handed equations plus whichever cells are still given. If the equations
        # changed with the values, erasing a cell could erase a constraint along with it.
        emptied = dataclasses.replace(
            cubs_at_braves_1968,
            batting_totals=dataclasses.replace(cubs_at_braves_1968.batting_totals, hits=0),
        )

        assert equations(shape_of(emptied)) == equations(shape_of(cubs_at_braves_1968))
