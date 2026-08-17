"""The solver, and the two axes it reports a puzzle's difficulty on.

Three things matter more than the arithmetic. It must never guess, so everything it produces has to
match the boxscore it came from. It must reach for bounding only after propagation has stopped, or
the harder technique gets credited for work the easier one could have done. And it must describe
the *shape* of the solution path, because how long the chain ran and how narrow the choice of next
move became are what tell one puzzle from another — cell count alone cannot.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import cell_values, cells_in_family, constrained_cells, shape_of
from boxscore_forge.errors import ContradictionError
from boxscore_forge.identities import Family
from boxscore_forge.solver import Technique, solve
from tests.strategies import valid_directions


def _erase(direction: Direction, *cells: str) -> dict[str, int]:
    values = cell_values(direction)
    for cell in cells:
        del values[cell]
    return values


class TestPropagation:
    def test_recovers_a_single_erased_cell(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "batting[3].hits"))

        assert solution.is_complete
        assert solution.values["batting[3].hits"] == 1
        assert solution.hardest_technique == Technique.PROPAGATION

    def test_reports_which_identity_it_deduced_from(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "batting[3].hits"))

        assert solution.deductions[0].from_identity == "batting_column_sum"
        assert solution.families_used == frozenset({Family.COLUMN_SUM})


class TestNothingToDo:
    def test_reports_no_technique_when_the_board_is_already_complete(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(shape_of(cubs_at_braves_1968), cell_values(cubs_at_braves_1968))

        assert solution.deductions == ()
        assert solution.hardest_technique is None
        assert solution.narrowest_frontier is None
        assert solution.chain_length == 0


class TestTheRowIdentityEarnsItsPlace:
    def test_recovers_a_cell_its_column_sum_cannot_reach(self, cubs_at_braves_1968: Direction) -> None:
        # Two blanks in the at-bats column. On a board without the row identity this is ambiguous
        # and the puzzle is thrown away; here one of them comes back through its own row.
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[1].at_bats", "batting[3].at_bats"),
        )

        assert solution.is_complete
        assert solution.values["batting[1].at_bats"] == 5
        assert solution.values["batting[3].at_bats"] == 4
        assert Family.ROW_IDENTITY in solution.families_used

    def test_the_deduction_chains_rather_than_standing_alone(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[1].at_bats", "batting[3].at_bats"),
        )

        assert solution.chain_length >= 2


class TestFamiliesReported:
    def test_reports_the_cross_team_family_when_the_path_needed_it(self, cubs_at_braves_1968: Direction) -> None:
        # Two blanks in the pitching strikeout column, so its own sum cannot reach either of them.
        # The only way in is across the board: the batters struck out five times, so the pitchers
        # recorded five.
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "pitching_totals.strikeouts", "pitching[0].strikeouts"),
        )

        assert solution.is_complete
        assert Family.CROSS_TEAM in solution.families_used

    def test_reports_the_global_family_when_the_path_needed_it(self, cubs_at_braves_1968: Direction) -> None:
        # Runners left on base appear in no equation but the global identity, so a board missing
        # that cell can only be closed by counting plate appearances backward.
        solution = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "team_footnotes.left_on_base"))

        assert solution.is_complete
        assert solution.values["team_footnotes.left_on_base"] == 8
        assert Family.GLOBAL_IDENTITY in solution.families_used

    def test_reports_only_the_families_actually_used(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "batting[3].hits"))

        assert Family.GLOBAL_IDENTITY not in solution.families_used


class TestBounding:
    def test_solves_a_pair_that_no_single_equation_can_reach(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[1].runs", "batting[3].runs"),
        )

        assert solution.is_complete
        assert solution.values["batting[1].runs"] == 0
        assert solution.hardest_technique == Technique.BOUNDING

    def test_claims_no_identity_for_a_bounded_deduction(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[1].runs", "batting[3].runs"),
        )

        bounded = [d for d in solution.deductions if d.technique == Technique.BOUNDING]
        assert bounded and all(deduction.from_identity is None for deduction in bounded)

    def test_propagation_runs_to_a_fixed_point_before_bounding_starts(self, cubs_at_braves_1968: Direction) -> None:
        # An exact value beats a narrowed range. If bounding ran first it would take cells a plain
        # subtraction could have produced, and every puzzle would look harder than it is.
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[1].runs", "batting[3].runs", "batting[0].hits"),
        )

        techniques = [deduction.technique for deduction in solution.deductions]
        assert techniques[0] == Technique.PROPAGATION

    def test_refuses_to_pick_one_of_two_possibilities(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[0].runs", "batting[2].runs"),
        )

        assert solution.unsolved == frozenset({"batting[0].runs", "batting[2].runs"})


class TestSolutionShape:
    def test_a_lone_deduction_reports_no_frontier_at_all(self, cubs_at_braves_1968: Direction) -> None:
        # One blank is one move. The board never offered a choice, so there is no width to report,
        # and calling it a bottleneck of one would put it alongside puzzles that really are tight.
        solution = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "batting[3].hits"))

        assert solution.chain_length == 1
        assert solution.narrowest_frontier is None
        assert solution.mean_frontier is None

    def test_independent_deductions_do_not_lengthen_the_chain(self, cubs_at_braves_1968: Direction) -> None:
        # Two blanks in different columns that never depend on each other, so both are one step deep.
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[3].hits", "batting[6].strikeouts"),
        )

        assert solution.chain_length == 1

    def test_reports_no_frontier_for_a_board_that_is_all_tail(self, cubs_at_braves_1968: Direction) -> None:
        # A solution narrows by exhaustion as it runs out of cells, so the closing steps say nothing
        # about difficulty and are ignored. A board short enough to be nothing but closing steps has
        # no width worth reporting at all.
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[3].hits", "batting[6].strikeouts"),
        )

        assert solution.narrowest_frontier is None
        assert solution.mean_frontier is None

    def test_a_bottleneck_shows_up_once_the_board_is_long_enough(self, cubs_at_braves_1968: Direction) -> None:
        # Six blanks spread across columns. The width reported is what the player faced while there
        # was still a board to scan, not what was left at the end.
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(
                cubs_at_braves_1968,
                "batting[0].hits",
                "batting[1].runs",
                "batting[2].strikeouts",
                "batting[3].walks",
                "batting[4].at_bats",
                "batting[5].plate_appearances",
            ),
        )

        assert solution.is_complete
        assert solution.narrowest_frontier == 4
        assert solution.mean_frontier is not None


class TestWeightedChain:
    def test_charges_nothing_for_a_step_that_combines_nothing(self, cubs_at_braves_1968: Direction) -> None:
        # Nobody hit a sacrifice fly in this game, so that column is nothing but zeros and its total
        # is zero. Filling a blank in it asks the player to add nothing up — it is the shape a board
        # full of zeros takes, and the reason raw chain length overstates such boards.
        solution = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "footnotes[3].sacrifice_flies"))

        assert solution.deductions[0].is_trivial
        assert solution.hardest_step is None
        assert solution.chain_length == 1

    def test_charges_for_a_step_that_does_combine_numbers(self, cubs_at_braves_1968: Direction) -> None:
        # The hits column has seven non-zero entries to add up before the blank falls out.
        solution = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "batting[3].hits"))

        assert not solution.deductions[0].is_trivial
        assert solution.hardest_step is not None

    def test_separates_two_boards_that_raw_chain_length_calls_equal(self, cubs_at_braves_1968: Direction) -> None:
        # This is the whole point. Both boards are one step long; one is arithmetic and the other is
        # a zero falling out of an empty column, and raw chain length cannot tell them apart.
        boring = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "footnotes[3].sacrifice_flies"))
        real = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "batting[3].hits"))

        assert boring.chain_length == real.chain_length
        assert boring.hardest_step is None
        assert real.hardest_step is not None

    def test_a_long_cheap_solve_does_not_outscore_a_short_expensive_one(self, cubs_at_braves_1968: Direction) -> None:
        # The failure a summed metric has by construction: many cheap steps beating a few costly
        # ones. Taking the maximum removes it without any correction for volume.
        # One blank in each of three columns that are nothing but zeros. Three steps, none of which
        # asks the player to add anything up.
        many_cheap = solve(
            shape_of(cubs_at_braves_1968),
            _erase(
                cubs_at_braves_1968,
                "footnotes[0].sacrifice_flies",
                "footnotes[1].hit_by_pitch",
                "footnotes[2].reached_on_interference",
            ),
        )
        one_real = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "batting[3].hits"))

        assert len(many_cheap.deductions) > len(one_real.deductions)
        assert many_cheap.hardest_step is None
        assert one_real.hardest_step is not None

    def test_bounding_is_counted_rather_than_costed(self, cubs_at_braves_1968: Direction) -> None:
        # Bounding draws on the whole board, so any scan cost given to it would be invented — and
        # under a maximum, one invented number would decide the score.
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[1].runs", "batting[3].runs"),
        )

        assert solution.bounding_steps >= 1
        assert not any(
            deduction.has_a_comparable_cost
            for deduction in solution.deductions
            if deduction.technique == Technique.BOUNDING
        )

    def test_the_ninetieth_percentile_never_exceeds_the_maximum(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[3].hits", "batting[6].strikeouts", "batting[2].walks"),
        )

        assert solution.ninetieth_percentile_step is not None
        assert solution.hardest_step is not None
        assert solution.ninetieth_percentile_step <= solution.hardest_step

    def test_a_step_costs_more_when_fewer_equations_are_ready(self, cubs_at_braves_1968: Direction) -> None:
        # Scan cost is the share of live equations that are ready to give. One opening among many
        # live equations is a harder thing to spot than one among few.
        solution = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "batting[3].hits"))

        assert solution.deductions[0].scan_cost >= 1.0
        assert solution.deductions[0].equations_solvable >= 1

    def test_reports_how_much_of_the_solve_was_trivial(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "footnotes[3].sacrifice_flies"))

        assert solution.trivial_share == 1.0

    def test_an_untouched_board_costs_nothing(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(shape_of(cubs_at_braves_1968), cell_values(cubs_at_braves_1968))

        assert solution.hardest_step is None
        assert solution.ninetieth_percentile_step is None
        assert solution.trivial_share is None
        assert solution.bounding_steps == 0


class TestTallies:
    def test_counts_how_often_each_technique_was_needed(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[1].runs", "batting[3].runs"),
        )

        assert solution.times_used[Technique.BOUNDING] >= 1
        assert sum(solution.times_used.values()) == len(solution.deductions)

    def test_counts_how_often_each_family_was_needed(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[1].at_bats", "batting[3].at_bats"),
        )

        assert solution.family_counts[Family.ROW_IDENTITY] >= 1
        assert solution.family_counts[Family.GLOBAL_IDENTITY] == 0

    def test_reports_which_cells_a_family_can_reach_at_all(self, cubs_at_braves_1968: Direction) -> None:
        # Which cells a kind of reasoning could ever touch, as opposed to which it did. The erasure
        # algorithm will need this to aim a puzzle at a particular family.
        reachable = cells_in_family(shape_of(cubs_at_braves_1968), Family.GLOBAL_IDENTITY)

        assert "team_footnotes.left_on_base" in reachable
        assert "batting[0].hits" not in reachable


class TestItNeverGuesses:
    @given(valid_directions(), st.data())
    def test_recovers_any_single_erased_cell_exactly(self, direction: Direction, data: st.DataObject) -> None:
        cell = data.draw(st.sampled_from(sorted(constrained_cells(shape_of(direction)))))
        original = cell_values(direction)

        solution = solve(shape_of(direction), _erase(direction, cell))

        assert solution.is_complete
        assert solution.values == original

    @given(valid_directions(), st.data())
    def test_deduces_nothing_that_contradicts_the_boxscore(self, direction: Direction, data: st.DataObject) -> None:
        cells = sorted(constrained_cells(shape_of(direction)))
        erased = data.draw(st.lists(st.sampled_from(cells), min_size=1, max_size=8, unique=True))
        original = cell_values(direction)

        solution = solve(shape_of(direction), _erase(direction, *erased))

        assert all(solution.values[cell] == original[cell] for cell in solution.values)


class TestContradiction:
    def test_refuses_givens_that_cannot_all_be_true(self, cubs_at_braves_1968: Direction) -> None:
        values = cell_values(cubs_at_braves_1968)
        values["line_score.offense_runs"] = 5

        with pytest.raises(ContradictionError, match="line_score_runs"):
            solve(shape_of(cubs_at_braves_1968), values)

    def test_refuses_a_contradiction_that_only_appears_after_a_deduction(self, cubs_at_braves_1968: Direction) -> None:
        values = _erase(cubs_at_braves_1968, "batting_totals.hits")
        values["pitching_totals.hits"] = 12

        with pytest.raises(ContradictionError):
            solve(shape_of(cubs_at_braves_1968), values)
