"""The identities restated as a linear system, which is the form the solver can reason over.

Two properties matter here. Agreement: the equation system must be exactly as strong as the
equality identities — weaker and the solver would call a cell undeducible that a player can work
out, stronger and it would deduce from a rule the board never states. And interconnection: the
graph must not be a forest.
"""

import dataclasses
import itertools

from hypothesis import given

from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import BoardShape, cell_values, equations, independent_cycles, shape_of
from boxscore_forge.identities import Identity, find_violations
from tests.strategies import valid_directions
from tests.test_identity_properties import _perturbations

EQUALITY_IDENTITIES = frozenset(
    {
        Identity.BATTING_COLUMN_SUM,
        Identity.FOOTNOTE_COLUMN_SUM,
        Identity.PITCHING_COLUMN_SUM,
        Identity.CROSS_TEAM_TOTAL,
        Identity.ROW_PLATE_APPEARANCES,
        Identity.GLOBAL_PLATE_APPEARANCES,
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


class TestInterconnection:
    @given(valid_directions())
    def test_the_constraint_graph_is_not_a_forest(self, direction: Direction) -> None:
        # The tripwire. A forest caps the board at trivial puzzles: every cell in one equation
        # means one blank is a subtraction and two blanks in one equation are ambiguous rather than
        # hard, so validation discards them and the generator has nowhere left to go.
        #
        # It guards interconnection, not a particular number, and it must fail if a future change
        # flattens the graph back down — which is what dropping the plate appearance column, or
        # collapsing footnotes back to team level, would do.
        assert independent_cycles(shape_of(direction)) > 0

    def test_the_row_identity_is_what_creates_the_cycles(self, cubs_at_braves_1968: Direction) -> None:
        shape = shape_of(cubs_at_braves_1968)
        with_rows = independent_cycles(shape)
        without_rows = _cycles_excluding(shape, Identity.ROW_PLATE_APPEARANCES)

        assert without_rows == 0
        assert with_rows > 0

    def test_at_bats_and_walks_each_live_in_two_equations(self, cubs_at_braves_1968: Direction) -> None:
        # The concrete form of the fix: an individual cell now has a second route into it, which is
        # what lets a deduction chain instead of standing alone.
        system = equations(shape_of(cubs_at_braves_1968))
        appearances = {
            cell: sum(1 for equation in system if any(term.cell == cell for term in equation.terms))
            for cell in ("batting[2].at_bats", "batting[2].walks", "batting[2].plate_appearances")
        }

        assert all(count >= 2 for count in appearances.values())


class TestTheTwoByTwoRungStaysUnreachable:
    @given(valid_directions())
    def test_no_two_equations_share_more_than_one_cell(self, direction: Direction) -> None:
        # Not a tripwire, a statement of fact: every identity is a sum over a row or over a column,
        # so two of them meet at most at the single cell where one row crosses one column. Adding
        # the row identity did not change it and no column set can.
        system = equations(shape_of(direction))
        overlaps = [
            (first.origin, second.origin)
            for first, second in itertools.combinations(system, 2)
            if len({term.cell for term in first.terms} & {term.cell for term in second.terms}) > 1
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


def _cycles_excluding(shape: BoardShape, identity: Identity) -> int:
    """Cycle count with one family of equations removed, to show which family creates them."""
    system = [equation for equation in equations(shape) if equation.origin != identity]
    cells = {term.cell for equation in system for term in equation.terms}
    parent: dict[str, str] = {**{cell: cell for cell in cells}, **{f"#{i}": f"#{i}" for i in range(len(system))}}

    def root(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for index, equation in enumerate(system):
        for term in equation.terms:
            left, right = root(term.cell), root(f"#{index}")
            if left != right:
                parent[left] = right

    edges = sum(len(equation.terms) for equation in system)
    nodes = len(cells) + len(system)
    return edges - nodes + len({root(node) for node in parent})
