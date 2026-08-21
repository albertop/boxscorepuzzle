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
from boxscore_forge.constraints import (
    batting_cell,
    cell_values,
    cells_in_family,
    constrained_cells,
    equations,
    shape_of,
    team_footnote_cell,
)
from boxscore_forge.erasure import erase
from boxscore_forge.errors import ContradictionError
from boxscore_forge.identities import FAMILY_OF, Family
from boxscore_forge.solver import (
    _ENOUGH_FOR_A_PERCENTILE,
    Deduction,
    Solution,
    Technique,
    _bounding_moves,
    _percentile,
    solve,
)
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
        assert solution.hardest_resolution == 0
        assert solution.chain_length == 1

    def test_a_trivial_step_can_still_have_been_hard_to_find(self, cubs_at_braves_1968: Direction) -> None:
        # The finding that split the metric in two: costing nothing to resolve says nothing about
        # what it cost to find. Both numbers exist for this step and only one of them is zero.
        solution = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "footnotes[3].sacrifice_flies"))
        step = solution.deductions[0]

        assert step.resolution_cost == 0
        assert step.search_cost is not None

    def test_charges_for_a_step_that_does_combine_numbers(self, cubs_at_braves_1968: Direction) -> None:
        # The hits column has seven non-zero entries to add up before the blank falls out.
        solution = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "batting[3].hits"))

        assert not solution.deductions[0].is_trivial
        assert solution.hardest_resolution is not None
        assert solution.hardest_resolution > 0

    def test_search_cost_is_a_fraction_and_cannot_grow_with_the_board(self, cubs_at_braves_1968: Direction) -> None:
        # The defect that failed falsification: the old form divided live equations by ready ones,
        # which grows without bound as a board empties and smuggled emptiness back in. A share of
        # the board that led nowhere is bounded by construction.
        few = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "batting[3].hits"))
        many = solve(
            shape_of(cubs_at_braves_1968),
            _erase(
                cubs_at_braves_1968,
                "batting[3].hits",
                "batting[6].strikeouts",
                "batting[2].walks",
                "batting[5].at_bats",
                "pitching[1].walks",
            ),
        )

        for solution in (few, many):
            assert solution.hardest_search is not None
            assert 0.0 <= solution.hardest_search < 1.0

    def test_separates_two_boards_that_raw_chain_length_calls_equal(self, cubs_at_braves_1968: Direction) -> None:
        # This is the whole point. Both boards are one step long; one is arithmetic and the other is
        # a zero falling out of an empty column, and raw chain length cannot tell them apart.
        boring = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "footnotes[3].sacrifice_flies"))
        real = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "batting[3].hits"))

        assert boring.chain_length == real.chain_length
        assert boring.hardest_resolution == 0
        assert real.hardest_resolution is not None
        assert real.hardest_resolution > 0

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
                "footnotes[2].catcher_interference",
            ),
        )
        one_real = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "batting[3].hits"))

        assert len(many_cheap.deductions) > len(one_real.deductions)
        assert many_cheap.hardest_resolution == 0
        assert one_real.hardest_resolution is not None
        assert one_real.hardest_resolution > 0

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

        for percentile, largest in (
            (solution.ninetieth_percentile_search, solution.hardest_search),
            (solution.ninetieth_percentile_resolution, solution.hardest_resolution),
        ):
            assert percentile is not None
            assert largest is not None
            assert percentile <= largest

    def test_a_step_costs_more_when_fewer_equations_are_ready(self, cubs_at_braves_1968: Direction) -> None:
        # One opening among many live equations is a harder thing to spot than one among few.
        step = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "batting[3].hits")).deductions[0]

        assert step.equations_solvable >= 1
        assert step.search_cost == 1.0 - step.equations_solvable / step.equations_live

    def test_reports_how_much_of_the_solve_was_trivial(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(shape_of(cubs_at_braves_1968), _erase(cubs_at_braves_1968, "footnotes[3].sacrifice_flies"))

        assert solution.trivial_share == 1.0

    def test_an_untouched_board_costs_nothing(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(shape_of(cubs_at_braves_1968), cell_values(cubs_at_braves_1968))

        assert solution.hardest_search is None
        assert solution.hardest_resolution is None
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


class TestTheGlobalIdentityWaitsItsTurn:
    """`PA = Outs + R + LOB` is admitted only when nothing simpler is available.

    ⚠️ The solver used to recombine the global equations with the rest before propagating, so a global
    move could be recorded while a column sum was still on the table. The numbers reached were right
    and the *path* was not one a player would follow — and the path is where chain length, family
    usage and stall position come from, so it was a measurement defect rather than a stylistic one.
    """

    def test_a_simpler_move_is_taken_first(self, cubs_at_braves_1968: Direction) -> None:
        # Left-on-base and one batting cell blank together. The global identity could resolve LOB
        # immediately; a column sum resolves the batting cell. The column sum must come first.
        shape = shape_of(cubs_at_braves_1968)
        values = cell_values(cubs_at_braves_1968)
        blanks = {team_footnote_cell("left_on_base"), batting_cell(0, "hits")}
        given = {name: value for name, value in values.items() if name not in blanks}

        solution = solve(shape, given)

        assert solution.is_complete
        first = solution.deductions[0]
        assert first.from_identity is not None
        assert FAMILY_OF[first.from_identity] is not Family.GLOBAL_IDENTITY

    def test_the_global_identity_is_still_reachable(self, cubs_at_braves_1968: Direction) -> None:
        # Holding it back must not mean never using it: with only left-on-base unknown, it is the
        # only route and the solver has to take it.
        shape = shape_of(cubs_at_braves_1968)
        values = cell_values(cubs_at_braves_1968)
        given = {name: value for name, value in values.items() if name != team_footnote_cell("left_on_base")}

        solution = solve(shape, given)

        assert solution.is_complete
        assert Family.GLOBAL_IDENTITY in solution.families_used


class TestTheGlobalIdentityStaysInItsPhase:
    """`PA = Outs + R + LOB` is the relation section 8 teaches last, and the solver holds it back.

    v02 fixed propagation's order. v03 found the boundary was only half there: search cost was
    measured over the whole system before the phase was known, and bounding narrowed against
    everything while its own docstring said otherwise.

    The measured answer is a null - across 72 boards and 768 bounding steps, not one needed the
    global relation. **That is exactly why these tests exist.** A flag that never fires on real data
    is indistinguishable from a flag that is broken, so the mechanism is tested directly rather than
    trusted because the boards are quiet.
    """

    def test_a_move_found_without_the_global_relation_is_not_charged_for_scanning_it(
        self, cubs_at_braves_1968: Direction
    ) -> None:
        shape = shape_of(cubs_at_braves_1968)
        non_global = [equation for equation in equations(shape) if not equation.is_global]
        # A real erasure rather than a slice of the cell names: an arbitrary set of blanks is usually
        # not derivable, and a solution with no deductions would pass every assertion below by being
        # empty.
        puzzle = erase(cubs_at_braves_1968, target_stalls=6, seed=4)

        assert puzzle is not None
        solution = puzzle.solution

        local = [
            step
            for step in solution.deductions
            if step.from_identity is not None and FAMILY_OF.get(step.from_identity) is not Family.GLOBAL_IDENTITY
        ]
        # Not vacuous: the board has to have produced such moves for the assertion to mean anything.
        assert local
        assert all(step.equations_live <= len(non_global) for step in local)

    def test_bounding_without_the_global_relation_cannot_reach_left_on_base(
        self, cubs_at_braves_1968: Direction
    ) -> None:
        # The one cell of the global relation that no other equation reaches. Both halves are
        # asserted: a guard that refuses everything would pass the first line alone.
        shape = shape_of(cubs_at_braves_1968)
        values = cell_values(cubs_at_braves_1968)
        hidden = "team_footnotes.left_on_base"
        without_it = {name: value for name, value in values.items() if name != hidden}
        non_global = tuple(equation for equation in equations(shape) if not equation.is_global)

        assert hidden not in dict(_bounding_moves(shape, without_it, non_global))
        assert hidden in dict(_bounding_moves(shape, without_it, equations(shape)))

    def test_the_other_three_cells_are_reachable_without_it(self, cubs_at_braves_1968: Direction) -> None:
        # Why the null is a null rather than a hole. Three of the four cells in the global relation
        # are already covered by column sums, so only left-on-base ever depends on it - and when that
        # is the single unknown, propagation takes it before bounding is ever reached.
        shape = shape_of(cubs_at_braves_1968)
        values = cell_values(cubs_at_braves_1968)
        non_global = tuple(equation for equation in equations(shape) if not equation.is_global)

        for cell in ("batting_totals.plate_appearances", "pitching_totals.outs", "batting_totals.runs"):
            without_it = {name: value for name, value in values.items() if name != cell}
            assert cell in dict(_bounding_moves(shape, without_it, non_global))

    def test_a_global_assisted_bound_is_reported_on_the_family_axis(self) -> None:
        """The reporting half, tested on its own because no real board reaches it.

        A bounding deduction names no identity, so before this the global relation could decide a
        cell on a board that reported never having touched it.
        """
        bounded = Deduction(
            cell="team_footnotes.left_on_base",
            value=7,
            technique=Technique.BOUNDING,
            from_identity=None,
            depth=1,
            frontier=1,
            depends_on=frozenset(),
            equations_live=1,
            equations_solvable=0,
            known_terms_combined=None,
            needed_global_identity=True,
        )
        solution = Solution(values={}, deductions=(bounded,), unsolved=frozenset())

        assert bounded.from_identity is None
        assert Family.GLOBAL_IDENTITY in solution.families_used

    def test_a_bound_that_did_not_need_it_does_not_claim_it(self) -> None:
        # The failing case. Without this the test above passes on a property that always returns the
        # global family, which would be worse than not reporting it at all.
        bounded = Deduction(
            cell="batting[0].hits",
            value=2,
            technique=Technique.BOUNDING,
            from_identity=None,
            depth=1,
            frontier=1,
            depends_on=frozenset(),
            equations_live=1,
            equations_solvable=0,
            known_terms_combined=None,
        )
        solution = Solution(values={}, deductions=(bounded,), unsolved=frozenset())

        assert solution.families_used == frozenset()


class TestTheTwoFamilyReportsAgree:
    """One solve must not give two answers about which reasoning it needed.

    ⚠️ `families_used` counted a bounding step that needed the global relation and `family_counts`
    counted only `from_identity`, which is `None` for every bounding step. The same immutable result
    said the family was required and returned zero for it, and there is no consumer yet — which is
    exactly when to fix it, because the two would have been read by different code.
    """

    def test_a_global_assisted_bound_is_counted_as_well_as_named(self) -> None:
        bounded = Deduction(
            cell="team_footnotes.left_on_base",
            value=7,
            technique=Technique.BOUNDING,
            from_identity=None,
            depth=1,
            frontier=1,
            depends_on=frozenset(),
            equations_live=1,
            equations_solvable=0,
            known_terms_combined=None,
            needed_global_identity=True,
        )
        solution = Solution(values={}, deductions=(bounded,), unsolved=frozenset())

        assert Family.GLOBAL_IDENTITY in solution.families_used
        assert solution.family_counts[Family.GLOBAL_IDENTITY] == 1

    def test_a_bound_that_did_not_need_it_counts_for_nothing(self) -> None:
        # The other direction: a property that always counted the global family would pass the first.
        bounded = Deduction(
            cell="batting[0].hits",
            value=2,
            technique=Technique.BOUNDING,
            from_identity=None,
            depth=1,
            frontier=1,
            depends_on=frozenset(),
            equations_live=1,
            equations_solvable=0,
            known_terms_combined=None,
        )
        solution = Solution(values={}, deductions=(bounded,), unsolved=frozenset())

        assert solution.families_used == frozenset()
        assert sum(solution.family_counts.values()) == 0

    def test_they_agree_on_a_real_board(self, cubs_at_braves_1968: Direction) -> None:
        # The invariant stated once, over whatever a real solve produces: a family is named if and
        # only if it is counted.
        puzzle = erase(cubs_at_braves_1968, target_stalls=7, seed=5)

        assert puzzle is not None
        counts = puzzle.solution.family_counts

        assert {family for family, n in counts.items() if n} == puzzle.solution.families_used


class TestTheNinetiethPercentileIsNotTheMaximum:
    """⚠️⚠️ **It was, on every board with fewer than ten costed steps.** (v36-P3-40)

    `_percentile` read `costs[min(int(0.9 * n), n - 1)]`, and `int(0.9n) == n - 1` for every `n <= 10`
    — so it returned the **maximum**, which is the exact degenerate value the p90 exists to avoid.
    `CLAUDE.md` §1 states the reason in one line: *p90, never max — the max is 8 or 9 on every board*.

    It was also wrong the other way for longer solves: `int(0.9 * 20)` is 18, the nineteenth of twenty
    values, nearer the 95th percentile than the 90th.

    **Measured when this was fixed:** over `cubs_at_braves_1968` erased at every target from 1 to 12
    across five seeds, 4 of 34 boards fall below ten costed steps — **all at target 1 or 2**, two of
    the six rungs in `STALL_TARGETS`. On those the metric that grades reported a maximum under a name
    promising otherwise.
    """

    def test_it_takes_the_nearest_rank_rather_than_truncating(self) -> None:
        # The old formula's answers are in the comments: it is wrong in both directions.
        assert _percentile(list(range(1, 21))) == 18  # was 19, the 95th percentile's neighbourhood
        assert _percentile(list(range(1, 101))) == 90  # was 91
        assert _percentile(list(range(1, 11))) == 9  # was 10, the maximum

    def test_a_short_solve_cannot_have_a_percentile_and_the_code_says_so(self) -> None:
        """⚠️ **Not a defect being papered over.** With four costed steps there is no freak step for a
        percentile to be robust against, so p90 and max coincide by arithmetic. What matters is that
        the floor is stated where the number is produced, because §31 grades on it."""
        for size in range(1, _ENOUGH_FOR_A_PERCENTILE):
            costs = list(range(1, size + 1))
            assert _percentile(costs) == costs[-1], f"{size} costed steps"
        # And at the floor it stops being the maximum, which is what the constant claims.
        at_floor = list(range(1, _ENOUGH_FOR_A_PERCENTILE + 1))
        assert _percentile(at_floor) != at_floor[-1]

    def test_nothing_costed_is_none_rather_than_zero(self) -> None:
        # A zero would read as an easy board rather than as an unmeasured one.
        assert _percentile([]) is None
