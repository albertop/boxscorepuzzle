"""The erased set must survive the trip into the package, in every section.

⚠️ The defect this guards is the one that made a whole round of measurement void. The adapter
consulted the erased set for batting and pitching rows and copied every footnote value regardless, so
the generator could erase a footnote, grade a solution path that used it as an unknown, and the
package would hand the value back. The verifier then validated an easier board than the one measured,
and the metadata described neither.

The test is written per section rather than as one blanket check, so a section added later without the
rule fails here instead of shipping quietly.
"""

import pytest

from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import (
    batting_cell,
    batting_total_cell,
    footnote_cell,
    footnote_total_cell,
    pitching_cell,
    pitching_total_cell,
    team_footnote_cell,
)
from boxscore_forge.identities import BATTING_COLUMNS, FOOTNOTE_COLUMNS, PITCHING_COLUMNS
from boxscore_forge.publish import to_board


class TestEverySectionHonoursTheErasedSet:
    def test_a_batting_cell(self, cubs_at_braves_1968: Direction) -> None:
        board = to_board(cubs_at_braves_1968, frozenset({batting_cell(0, "hits")}))

        assert board.batting[0][BATTING_COLUMNS.index("hits")] is None

    def test_a_batting_total(self, cubs_at_braves_1968: Direction) -> None:
        board = to_board(cubs_at_braves_1968, frozenset({batting_total_cell("runs")}))

        assert board.batting_totals[BATTING_COLUMNS.index("runs")] is None

    def test_a_pitching_cell(self, cubs_at_braves_1968: Direction) -> None:
        board = to_board(cubs_at_braves_1968, frozenset({pitching_cell(0, "outs")}))

        assert board.pitching[0][PITCHING_COLUMNS.index("outs")] is None

    def test_a_pitching_total(self, cubs_at_braves_1968: Direction) -> None:
        board = to_board(cubs_at_braves_1968, frozenset({pitching_total_cell("walks")}))

        assert board.pitching_totals[PITCHING_COLUMNS.index("walks")] is None

    def test_a_footnote_cell(self, cubs_at_braves_1968: Direction) -> None:
        # ⚠️ The one that was broken. §6 gives the footnote line complete today, so nothing erases it
        # — and the adapter must not depend on that, because the decision has already flipped once
        # this project and the silent failure would come back with it.
        board = to_board(cubs_at_braves_1968, frozenset({footnote_cell(0, "sacrifice_hits")}))

        assert board.footnotes[0][FOOTNOTE_COLUMNS.index("sacrifice_hits")] is None

    def test_a_footnote_total(self, cubs_at_braves_1968: Direction) -> None:
        board = to_board(cubs_at_braves_1968, frozenset({footnote_total_cell("hit_by_pitch")}))

        assert board.footnote_totals[FOOTNOTE_COLUMNS.index("hit_by_pitch")] is None

    def test_the_team_footnote(self, cubs_at_braves_1968: Direction) -> None:
        board = to_board(cubs_at_braves_1968, frozenset({team_footnote_cell("left_on_base")}))

        assert board.left_on_base is None


class TestNothingElseChanges:
    def test_an_empty_erased_set_gives_the_whole_board(self, cubs_at_braves_1968: Direction) -> None:
        board = to_board(cubs_at_braves_1968)

        assert all(value is not None for row in board.batting for value in row)
        assert all(value is not None for row in board.pitching for value in row)
        assert all(value is not None for row in board.footnotes for value in row)
        assert board.left_on_base is not None

    def test_the_line_score_is_never_erased(self, cubs_at_braves_1968: Direction) -> None:
        # The anchor is copied whole rather than passed through the erasure rule: a blank there is
        # malformed rather than difficult (§6), so naming one must not produce one.
        board = to_board(cubs_at_braves_1968, frozenset({"line_score.offense_runs"}))

        assert board.line_score.offense_runs == cubs_at_braves_1968.line_score.offense_runs

    @pytest.mark.parametrize("section", ["batting", "pitching", "footnotes"])
    def test_row_counts_are_preserved(self, cubs_at_braves_1968: Direction, section: str) -> None:
        board = to_board(cubs_at_braves_1968)
        expected = {
            "batting": len(cubs_at_braves_1968.batting),
            "pitching": len(cubs_at_braves_1968.pitching),
            "footnotes": len(cubs_at_braves_1968.batter_footnotes),
        }

        assert len(getattr(board, section)) == expected[section]
