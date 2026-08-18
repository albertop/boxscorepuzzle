"""Boards built here rather than borrowed from the generator.

⚠️ Nothing in the verifier's tests imports `boxscore_forge`. A fixture produced by the thing under
judgement would agree with it by construction, which is the shape of failure §22 exists to prevent.
Boards are assembled from the identities as the design document states them, so a board that is valid
here is valid because the *document* says so.
"""

from collections.abc import Callable

import pytest

from boxscore_package.format import Board, LineScore

# One real-shaped board, arithmetic worked through by hand against §3:
#   nine batters at four plate appearances each, no walks and no footnote terms, so every row
#   identity reads 4 = 4 + 0. Eight hits, three runs, five strikeouts. Twenty-seven outs recorded by
#   two pitchers, which leaves 36 - 27 - 3 = 6 left on base for the global identity.
_HITS = (1, 1, 1, 1, 1, 1, 1, 1, 0)
_RUNS = (1, 1, 1, 0, 0, 0, 0, 0, 0)
_STRIKEOUTS = (1, 1, 1, 1, 1, 0, 0, 0, 0)


def whole_board() -> Board:
    """A boxscore that satisfies every identity and inequality in §3."""
    batting = tuple((4, 4, _RUNS[row], _HITS[row], 0, _STRIKEOUTS[row]) for row in range(9))
    return Board(
        batting=batting,
        batting_totals=(36, 36, sum(_RUNS), sum(_HITS), 0, sum(_STRIKEOUTS)),
        footnotes=tuple((0, 0, 0, 0) for _ in range(9)),
        footnote_totals=(0, 0, 0, 0),
        left_on_base=6,
        pitching=((18, 5, 2, 2, 0, 3), (9, 3, 1, 1, 0, 2)),
        pitching_totals=(27, 8, 3, 3, 0, 5),
        line_score=LineScore(
            offense_by_inning=(0, 1, 0, 0, 1, 0, 0, 1, 0),
            defense_by_inning=(1, 0, 0, 0, 0, 0, 0, 0, 0),
            offense_runs=3,
            offense_hits=8,
            offense_errors=0,
            defense_runs=1,
            defense_hits=4,
            defense_errors=1,
        ),
    )


def erased(board: Board, cells: dict[str, list[tuple[int, int]]]) -> Board:
    """Blank the named cells. Keys are `batting`, `batting_totals`, `pitching`, `pitching_totals`.

    A totals row is addressed with a row index of zero, so one shape of call covers both.
    """
    batting = [list(row) for row in board.batting]
    pitching = [list(row) for row in board.pitching]
    batting_totals = list(board.batting_totals)
    pitching_totals = list(board.pitching_totals)
    for row, column in cells.get("batting", []):
        batting[row][column] = None
    for _, column in cells.get("batting_totals", []):
        batting_totals[column] = None
    for row, column in cells.get("pitching", []):
        pitching[row][column] = None
    for _, column in cells.get("pitching_totals", []):
        pitching_totals[column] = None
    return Board(
        batting=tuple(tuple(row) for row in batting),
        batting_totals=tuple(batting_totals),
        footnotes=board.footnotes,
        footnote_totals=board.footnote_totals,
        left_on_base=board.left_on_base,
        pitching=tuple(tuple(row) for row in pitching),
        pitching_totals=tuple(pitching_totals),
        line_score=board.line_score,
    )


@pytest.fixture
def board() -> Board:
    return whole_board()


@pytest.fixture
def blank() -> Callable[[Board, dict[str, list[tuple[int, int]]]], Board]:
    """`erased` handed over as a fixture rather than imported.

    Tests reach helpers through fixtures here because importing `conftest` by name is invisible to
    the type checker, and a test file that mypy cannot follow is a test file where a wrong type
    survives.
    """
    return erased
