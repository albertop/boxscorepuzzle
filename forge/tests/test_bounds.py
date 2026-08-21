"""Narrowing what a cell could be, which is the second of the two techniques.

Bounding is also how the board handles a footnote whose row is ambiguous — one of two shortstops
was hit by a pitch, the term has a domain of nought or one in each row, and the rest of the board
settles which. That is reasoning over ranges, not trying both and keeping whichever balances, which
would be backtracking and is exactly what the publication rule forbids.
"""

import pytest
from hypothesis import given

from boxscore_forge import bounds as bounds_module
from boxscore_forge.bounds import Bounds, narrow
from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import Equation, Term, all_cells, cell_values, shape_of
from boxscore_forge.errors import ContradictionError
from boxscore_forge.identities import Identity
from tests.strategies import valid_directions


def _erase(direction: Direction, *cells: str) -> dict[str, int]:
    values = cell_values(direction)
    for cell in cells:
        del values[cell]
    return values


def _upper(bounds: Bounds) -> float:
    return float("inf") if bounds.high is None else bounds.high


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

        assert narrow(shape, cell_values(cubs_at_braves_1968)).keys() == all_cells(shape)


class TestNonNegativity:
    def test_two_cells_that_sum_to_zero_are_both_zero(self, cubs_at_braves_1968: Direction) -> None:
        # Neither can be worked out on its own, because the column sum has two unknowns in it. But
        # they add to nothing and neither can be negative, so both are nothing.
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


class TestAmbiguousFootnoteAssignment:
    """A footnote whose row is ambiguous, modelled by leaving both candidate cells unknown.

    The board says one sacrifice hit happened among two rows sharing a position label, without
    saying which. Nothing extra is needed to state that: the footnote's own column sum already says
    the pair adds to one.
    """

    def test_the_row_identity_settles_it_on_its_own(self, cubs_at_braves_1968: Direction) -> None:
        # And usually it settles immediately. Row four's plate appearances are already accounted for
        # by its at-bats and walks, so it has no room for a sacrifice; row nought's are one short,
        # so it must have had it. Nobody tried both — each row's own identity forced the answer.
        domains = narrow(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "footnotes[0].sacrifice_hits", "footnotes[4].sacrifice_hits"),
        )

        assert domains["footnotes[4].sacrifice_hits"] == Bounds(0, 0)
        assert domains["footnotes[0].sacrifice_hits"] == Bounds(1, 1)

    def test_it_stays_open_when_the_rows_themselves_are_incomplete(self, cubs_at_braves_1968: Direction) -> None:
        # Take the at-bats away from both candidate rows and neither identity can settle its own
        # footnote any more. Narrowing keeps both honest at nought-or-one rather than choosing.
        domains = narrow(
            shape_of(cubs_at_braves_1968),
            _erase(
                cubs_at_braves_1968,
                "footnotes[0].sacrifice_hits",
                "footnotes[4].sacrifice_hits",
                "batting[0].at_bats",
                "batting[4].at_bats",
            ),
        )

        assert domains["footnotes[0].sacrifice_hits"] == Bounds(0, 1)
        assert domains["footnotes[4].sacrifice_hits"] == Bounds(0, 1)


class TestInequalities:
    def test_earned_runs_cannot_exceed_runs(self, cubs_at_braves_1968: Direction) -> None:
        domains = narrow(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "pitching[0].earned_runs", "pitching[1].earned_runs"),
        )

        assert _upper(domains["pitching[1].earned_runs"]) == 0

    def test_plate_appearances_bound_at_bats_from_above(self, cubs_at_braves_1968: Direction) -> None:
        # The bound the plate appearance column makes available, narrowing from the opposite side to
        # the row identity.
        domains = narrow(
            shape_of(cubs_at_braves_1968),
            _erase(cubs_at_braves_1968, "batting[1].at_bats", "batting_totals.at_bats"),
        )

        assert _upper(domains["batting[1].at_bats"]) <= 5


class TestContradiction:
    def test_refuses_a_cell_with_no_value_left_open_to_it(self, cubs_at_braves_1968: Direction) -> None:
        values = _erase(cubs_at_braves_1968, "batting[4].hits")
        values["batting[4].at_bats"] = 0
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
            bounds = narrow(shape, {name: value for name, value in original.items() if name != cell})[cell]

            assert bounds.low <= original[cell] <= _upper(bounds)


class TestAContradictionIsRaisedRatherThanRunForever:
    """⚠️⚠️ **The loop had no bound and an inconsistent system made it run for ever.** v36-P2-01.

    Every unknown starts `Bounds(0, None)` — no upper bound claimed, which is the honest state. But
    `is_empty` needs `high is not None`, so on a contradictory cycle among cells that never gain an
    upper bound the lower bounds climb by a positive constant every pass and **nothing ever reports
    it**. `erase()` reaches `solve()` on directions loaded from the database *before* any layer-1
    validation, and `erasure.py` promises a broken boxscore "fails loud" via `ContradictionError`.
    It hung the batch instead — **worse than the crash that was promised**, because a hang carries no
    message and no exit code.

    ⚠️ **The verifier's twin was immune and that is the finding, not the consolation.** `reason.py`
    seeds `(0, CELL_CAP)`, so it terminates. Two independent implementations of one technique
    disagreeing about whether bad data ends — §22's independence working exactly as intended to
    surface it, and the disagreement is the defect.
    """

    @staticmethod
    def _impossible_pair(shape: object) -> tuple[Equation, ...]:
        """`a = b + 1` and `b = a + 1` over two real cells: satisfiable by nothing, bounded by nothing."""
        cells = sorted(all_cells(shape))
        a, b = cells[0], cells[1]
        return (
            Equation(terms=(Term(a, 1), Term(b, -1)), constant=1, origin=Identity.ROW_PLATE_APPEARANCES),
            Equation(terms=(Term(b, 1), Term(a, -1)), constant=1, origin=Identity.ROW_PLATE_APPEARANCES),
        )

    def test_an_unsatisfiable_system_raises_instead_of_hanging(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️ **If the cap is removed this test does not fail — it hangs**, and a CI timeout is what
        reports it. That is uncomfortable and it is the honest assertion: the property under test is
        *termination*, and there is no way to assert termination that terminates when it is absent."""
        shape = shape_of(cubs_at_braves_1968)

        with pytest.raises(ContradictionError, match="did not settle"):
            narrow(shape, {}, system=self._impossible_pair(shape))

    def test_the_message_names_the_shape_rather_than_blaming_the_board(self, cubs_at_braves_1968: Direction) -> None:
        # The operator reading this is looking at a batch that stopped. "Slow" and "impossible" need
        # different responses, and the message has to say which one this is.
        shape = shape_of(cubs_at_braves_1968)

        with pytest.raises(ContradictionError) as raised:
            narrow(shape, {}, system=self._impossible_pair(shape))

        assert "contradictory" in str(raised.value)
        assert "passes per cell" in str(raised.value), "the message does not say what normal looks like"

    def test_a_real_board_settles_far_inside_the_cap(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️ **The other half, and the one that keeps the cap honest.** A bound that could reject a real
        board would be raised until it said nothing, so this asserts the headroom is real: the whole
        board narrows without coming near the ceiling.

        Measured when the cap was set: the worst of 10,442 real calls took **5 passes** over 143 cells.
        """
        shape = shape_of(cubs_at_braves_1968)
        passes = {"count": 0}
        original = bounds_module._tighten_once

        def counted(*args: object) -> bool:
            passes["count"] += 1
            return original(*args)

        bounds_module._tighten_once = counted
        try:
            narrow(shape, _erase(cubs_at_braves_1968, *sorted(all_cells(shape))[:6]))
        finally:
            bounds_module._tighten_once = original

        ceiling = max(bounds_module._MINIMUM_PASSES, bounds_module._PASSES_PER_CELL * len(all_cells(shape)))
        assert passes["count"] < ceiling / 10, (
            f"a real board took {passes['count']} passes against a ceiling of {ceiling}; "
            f"the headroom this cap was set with is gone"
        )
