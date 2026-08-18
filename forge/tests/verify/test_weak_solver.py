"""Layer 3b: the solver that reads one relation at a time.

It exists because layer 3 is stronger than a person — interval propagation to a fixed point across
forty-odd simultaneous relations — so a board can pass layer 3 and still be underivable by hand. This
is the other end of that bracket, and the fifty-board hand-solve decides which end a player sits at.

Untested code deciding a product question is worse than no code, so what is pinned here is the
*difference* between the two solvers, not merely that this one runs.
"""

from collections.abc import Callable

from boxscore_package.format import Board, Package
from boxscore_verify.reason import derive, derive_in_view
from boxscore_verify.rules import all_cells, relations, values_of
from boxscore_verify.verify import derivable_in_view

Blank = Callable[[Board, dict[str, list[tuple[int, int]]]], Board]


def weakly(board: Board, **kwargs: bool) -> object:
    return derive_in_view(relations(board), all_cells(board), values_of(board), **kwargs)


class TestItSolvesWhatAnyoneCould:
    def test_a_complete_board_needs_no_work(self, board: Board) -> None:
        reached = weakly(board)

        assert reached.is_complete  # type: ignore[attr-defined]
        assert reached.values == values_of(board)  # type: ignore[attr-defined]

    def test_one_blank_is_a_subtraction(self, board: Board, blank: Blank) -> None:
        # An equation with a single unknown is what anybody does first, and it is the whole of the
        # weak solver's propagation step.
        puzzle = blank(board, {"batting": [(3, 3)]})

        reached = weakly(puzzle)

        assert reached.is_complete  # type: ignore[attr-defined]
        assert reached.values["bat[3].hits"] == 1  # type: ignore[attr-defined]

    def test_a_realistic_erasure_still_goes_through(self, board: Board, blank: Blank) -> None:
        puzzle = blank(board, {"batting": [(2, 0), (7, 4), (1, 1), (4, 3)], "pitching": [(1, 4)]})

        assert weakly(puzzle).is_complete  # type: ignore[attr-defined]


class TestItIsWeakerThanLayerThree:
    def test_bounding_can_be_switched_off_entirely(self, board: Board, blank: Blank) -> None:
        # With bounding off it is pure subtraction: an equality with exactly one unknown, nothing
        # else. That is the floor of what "no guessing" can possibly mean.
        puzzle = blank(board, {"batting": [(0, 3)]})

        assert weakly(puzzle, allow_bounding=False).is_complete  # type: ignore[attr-defined]

    def test_it_never_claims_more_than_the_strong_solver(self, board: Board, blank: Blank) -> None:
        # The bracket has to hold in the right direction. If the weak solver ever resolved a cell the
        # strong one could not, one of them would be wrong, and this is the cheapest place to notice.
        puzzle = blank(board, {"batting": [(0, 3), (1, 3), (2, 2), (5, 1)], "pitching_totals": [(0, 1)]})

        strong = derive(relations(puzzle), all_cells(puzzle), values_of(puzzle))
        weak = weakly(puzzle)

        assert set(weak.values) <= set(strong.values)  # type: ignore[attr-defined]
        for cell, value in weak.values.items():  # type: ignore[attr-defined]
            assert strong.values[cell] == value

    def test_it_reports_what_it_could_not_reach(self, board: Board, blank: Blank) -> None:
        # Two cells in one column with nothing to separate them: no single relation settles either,
        # so the weak solver stops and says so rather than guessing.
        puzzle = blank(board, {"batting": [(0, 3), (1, 3)]})

        reached = weakly(puzzle)

        assert not reached.is_complete  # type: ignore[attr-defined]
        assert "bat[0].hits" in reached.unresolved  # type: ignore[attr-defined]


class TestTheReportedProperty:
    def test_a_derivable_board_certifies(self, board: Board, blank: Blank) -> None:
        puzzle = blank(board, {"batting": [(3, 3)]})

        assert derivable_in_view(Package(puzzle_id="p", puzzle=puzzle, solution=board))

    def test_an_ambiguous_board_does_not(self, board: Board, blank: Blank) -> None:
        puzzle = blank(board, {"batting": [(0, 3), (1, 3)]})

        assert not derivable_in_view(Package(puzzle_id="p", puzzle=puzzle, solution=board))
