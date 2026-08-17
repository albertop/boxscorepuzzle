"""The bottom of the technique ladder: forced single-unknown deductions, propagated.

Two things are under test that matter more than the arithmetic. The solver must never guess, so
everything it produces has to match the boxscore it came from. And it must not reach for the global
team identity while easier rules still work, or the hardest step in a puzzle gets solved by the
easiest technique and the puzzle is reported as trivial.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import cell_values, constrained_cells, shape_of
from boxscore_forge.errors import ContradictionError
from boxscore_forge.solver import Technique, solve
from tests.strategies import valid_directions


def _erase(direction: Direction, *cells: str) -> dict[str, int]:
    values = cell_values(direction)
    for cell in cells:
        del values[cell]
    return values


class TestSingleUnknown:
    def test_recovers_a_single_erased_cell(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "batting[3].hits"))

        assert solution.is_complete
        assert solution.values["batting[3].hits"] == 1
        assert solution.highest_technique == Technique.SINGLE_UNKNOWN

    def test_reports_which_identity_it_deduced_from(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "batting[3].hits"))

        assert [deduction.cell for deduction in solution.deductions] == ["batting[3].hits"]
        assert solution.deductions[0].from_identity == "batting_column_sum"


class TestNothingToDo:
    def test_reports_no_technique_when_the_board_is_already_complete(self, cubs_at_braves_1968: Direction) -> None:
        # A board with nothing erased is not a puzzle. It demands no technique, and saying it
        # required the easiest one would put it in the same bucket as a puzzle that did.
        solution = solve(shape_of(cubs_at_braves_1968), cell_values(cubs_at_braves_1968))

        assert solution.is_complete
        assert solution.deductions == ()
        assert solution.highest_technique is None


class TestPropagation:
    def test_chains_deductions_and_marks_the_later_ones(self, cubs_at_braves_1968: Direction) -> None:
        # The batting total for hits has to be recovered first, from the line score, before the
        # column sum has only one unknown left in it.
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting_totals.hits", "batting[0].hits"),
        )

        assert solution.is_complete
        assert solution.values["batting_totals.hits"] == 11
        assert solution.values["batting[0].hits"] == 1
        assert solution.highest_technique == Technique.PROPAGATION

    def test_counts_how_often_each_technique_was_needed(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting_totals.hits", "batting[0].hits"),
        )

        assert solution.times_used[Technique.SINGLE_UNKNOWN] == 1
        assert solution.times_used[Technique.PROPAGATION] == 1


class TestTheGlobalIdentityIsWithheld:
    def test_leaves_a_cell_only_the_team_identity_could_reach(self, cubs_at_braves_1968: Direction) -> None:
        # Runners left on base appear in no equation but the global team identity. Until the ladder
        # admits it, this cell has to stay unsolved rather than be picked up by the easy rule.
        solution = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "footnotes.left_on_base"))

        assert not solution.is_complete
        assert solution.unsolved == frozenset({"footnotes.left_on_base"})


class TestItNeverGuesses:
    @given(valid_directions(), st.data())
    def test_recovers_any_single_erased_cell_exactly(self, direction: Direction, data: st.DataObject) -> None:
        # Every cell that takes part in an equation is reachable when it is the only one missing,
        # and what comes back must be the number that was there. A solver that returns a plausible
        # value instead of the true one is the failure mode the whole design exists to prevent.
        cell = data.draw(st.sampled_from(sorted(constrained_cells(shape_of(direction)))))
        original = cell_values(direction)

        solution = solve(shape_of(direction), _erase(direction, cell))

        assert solution.is_complete
        assert solution.values == original

    @given(valid_directions(), st.data())
    def test_deduces_nothing_that_contradicts_the_boxscore(self, direction: Direction, data: st.DataObject) -> None:
        cells = sorted(constrained_cells(shape_of(direction)))
        erased = data.draw(st.lists(st.sampled_from(cells), min_size=1, max_size=6, unique=True))
        original = cell_values(direction)

        solution = solve(shape_of(direction), _erase(direction, *erased))

        assert all(solution.values[cell] == original[cell] for cell in solution.values)


class TestContradiction:
    def test_refuses_givens_that_cannot_all_be_true(self, cubs_at_braves_1968: Direction) -> None:
        # An equation with nothing left unknown that still does not balance means the givens
        # contradict each other. That is a broken puzzle, not a hard one, and it must stop rather
        # than produce a confident answer.
        values = cell_values(cubs_at_braves_1968)
        values["line_score.offense_runs"] = 5

        with pytest.raises(ContradictionError, match="line_score_runs"):
            solve(shape_of(cubs_at_braves_1968), values)

    def test_refuses_a_contradiction_that_only_appears_after_a_deduction(self, cubs_at_braves_1968: Direction) -> None:
        values = _erase(cubs_at_braves_1968, "batting_totals.hits")
        values["pitching_totals.hits"] = 12

        with pytest.raises(ContradictionError):
            solve(shape_of(cubs_at_braves_1968), values)
