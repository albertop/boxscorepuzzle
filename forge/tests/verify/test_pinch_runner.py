"""A pinch runner scores without ever batting, and the board has to keep him.

The regression this guards is the second defect of the review round: a filter of "has a plate
appearance" removed non-batting pitchers and took pinch runners with them, deleting their runs. The
board stayed self-consistent — the loader sums its own totals — so every identity balanced and all
four verifier layers passed it.

Kept as its own file because the rule is easy to re-derive wrongly. "Every batting row has a plate
appearance" reads like an obvious invariant and is false.
"""

from collections.abc import Callable

from boxscore_package.format import Board
from boxscore_verify.plausibility import faults

Replace = Callable[..., Board]


def with_pinch_runner(board: Board, replace: Replace) -> Board:
    """A row with no plate appearance, no at-bat, and a run. Legal, and it happens constantly.

    The run has to come from somewhere, so it is taken off the batter in row one — a real pinch
    runner replaces a man on base and scores the run that was going to be his.
    """
    rows = [list(row) for row in board.batting]
    rows[0][2] = 0
    runner = (0, 0, 1, 0, 0, 0)
    return replace(
        board,
        batting=(*(tuple(row) for row in rows), runner),
        footnotes=(*board.footnotes, (0, 0, 0, 0)),
    )


class TestARunnerWhoNeverBatted:
    def test_he_is_not_implausible(self, board: Board, replace: Replace) -> None:
        # The whole point. He has PA = 0 and belongs on the board, so a check requiring a plate
        # appearance would reject a real boxscore — and did.
        assert faults(with_pinch_runner(board, replace)) == []

    def test_a_row_that_contributed_nothing_still_is(self, board: Board, replace: Replace) -> None:
        # The invariant is "contributed something", not "batted". This row did nothing at all.
        empty = replace(
            board,
            batting=(*board.batting, (0, 0, 0, 0, 0, 0)),
            footnotes=(*board.footnotes, (0, 0, 0, 0)),
        )

        assert any("entirely nought" in fault.what for fault in faults(empty))

    def test_the_two_cases_differ_only_by_the_run(self, board: Board, replace: Replace) -> None:
        # Stated as a test because the distinction is one cell wide and easy to lose in a filter.
        runner = with_pinch_runner(board, replace).batting[-1]
        nobody = (0, 0, 0, 0, 0, 0)

        assert runner != nobody
        assert sum(value or 0 for value in runner) == 1
