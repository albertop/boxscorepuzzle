"""Narrowing what a cell could be, which is what the fourth rung reasons with.

With the 2x2 rung unreachable on this board, bounding is the only technique between propagation and
the global identity. It is what has to make a puzzle hard, so it has to be right.
"""

import pytest
from hypothesis import given

from boxscore_forge.bounds import Bounds, narrow
from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import all_cells, cell_values, shape_of
from boxscore_forge.errors import ContradictionError
from tests.strategies import valid_directions


def _erase(direction: Direction, *cells: str) -> dict[str, int]:
    values = cell_values(direction)
    for cell in cells:
        del values[cell]
    return values


class TestBoundsType:
    def test_a_single_possible_value_is_fixed(self) -> None:
        assert Bounds(3, 3).fixed_value == 3

    def test_a_range_is_not_fixed(self) -> None:
        assert Bounds(0, 3).fixed_value is None

    def test_an_open_top_is_not_fixed(self) -> None:
        assert Bounds(0, None).fixed_value is None


class TestKnownCells:
    def test_a_given_cell_is_pinned_to_its_value(self, cubs_at_braves_1968: Direction) -> None:
        domains = narrow(shape_of(cubs_at_braves_1968), cell_values(cubs_at_braves_1968))

        assert domains["batting[1].hits"] == Bounds(2, 2)

    def test_every_cell_on_the_board_gets_a_domain(self, cubs_at_braves_1968: Direction) -> None:
        shape = shape_of(cubs_at_braves_1968)

        domains = narrow(shape, cell_values(cubs_at_braves_1968))

        assert domains.keys() == all_cells(shape)


class TestNonNegativity:
    def test_two_cells_that_sum_to_zero_are_both_zero(self, cubs_at_braves_1968: Direction) -> None:
        # Neither can be worked out on its own, because the column sum has two unknowns in it. But
        # they add to nothing and neither can be negative, so both are nothing. This is the whole
        # of the fourth rung in one step.
        domains = narrow(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[1].runs", "batting[3].runs"),
        )

        assert domains["batting[1].runs"] == Bounds(0, 0)
        assert domains["batting[3].runs"] == Bounds(0, 0)

    def test_leaves_a_genuinely_ambiguous_pair_open(self, cubs_at_braves_1968: Direction) -> None:
        # These two runs add to two, so each is somewhere between nothing and two. Narrowing that
        # to a single value would be a guess, and guessing is the one thing the solver may not do.
        domains = narrow(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[0].runs", "batting[2].runs"),
        )

        assert domains["batting[0].runs"] == Bounds(0, 2)
        assert domains["batting[2].runs"] == Bounds(0, 2)


class TestInequalities:
    def test_hits_are_capped_by_at_bats(self, cubs_at_braves_1968: Direction) -> None:
        # Two hits missing from one column, but the batter with three at-bats cannot have more than
        # three of them, and that is enough to pin the pair.
        domains = narrow(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[5].hits", "batting[5].at_bats"),
        )

        assert domains["batting[5].hits"].low <= 2 <= _upper(domains["batting[5].hits"])
        assert domains["batting[5].at_bats"].low >= domains["batting[5].hits"].low

    def test_earned_runs_cannot_exceed_runs(self, cubs_at_braves_1968: Direction) -> None:
        domains = narrow(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "pitching[0].earned_runs", "pitching[1].earned_runs"),
        )

        assert _upper(domains["pitching[1].earned_runs"]) == 0


class TestContradiction:
    def test_refuses_a_cell_with_no_value_left_open_to_it(self, cubs_at_braves_1968: Direction) -> None:
        values = _erase(cubs_at_braves_1968, "batting[4].hits")
        values["batting[4].at_bats"] = 0
        values["batting_totals.at_bats"] = 32
        values["batting_totals.hits"] = 12
        values["line_score.offense_hits"] = 12
        values["pitching_totals.hits"] = 12
        values["pitching[1].hits"] = 2

        with pytest.raises(ContradictionError):
            narrow(shape_of(cubs_at_braves_1968), values)


class TestItNeverExcludesTheTruth:
    @given(valid_directions())
    def test_the_real_value_always_stays_inside_its_domain(self, direction: Direction) -> None:
        # The property that makes bounding safe to deduce from. If narrowing ever pushed past the
        # true value, the solver would confidently produce a wrong board.
        original = cell_values(direction)
        shape = shape_of(direction)
        for cell in sorted(original):
            domains = narrow(shape, {name: value for name, value in original.items() if name != cell})
            bounds = domains[cell]

            assert bounds.low <= original[cell] <= _upper(bounds)


def _upper(bounds: Bounds) -> float:
    return float("inf") if bounds.high is None else bounds.high
