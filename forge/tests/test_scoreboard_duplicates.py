"""The four totals the line score already prints are never erased.

⚠️ **The defect this closes was found by rendering the phone board and reading it**, not by a check.
The `H` total sat blank with `AWAY H 15` printed two centimetres above it: the cell had been copied, not
deduced. Four cells are in that position, and `line_score.offense_hits = batting_totals.hits` is a real
equation the solver carries — but it has **two terms and one unknown**, so the player performs a lookup
and the solver records a deduction. *A lookup counted as a deduction is a lookup counted as difficulty.*

It is the independent-blank filler the pruning experiment chased, appearing in the one row that had been
treated as a read-only anchor until the real packages showed it carries blanks.

Excluded in `erasable()` rather than filtered afterwards — v03-P1-02's lesson. A second place that
removes cells downstream is a second definition, and two definitions drift.
"""

import pytest

from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import batting_total_cell, cell_values, pitching_total_cell
from boxscore_forge.erasure import SCOREBOARD_DUPLICATES, erasable, erase


class TestTheyAreOutOfTheErasableSet:
    def test_none_of_the_four_is_a_candidate(self, cubs_at_braves_1968: Direction) -> None:
        candidates = set(erasable(cubs_at_braves_1968))

        assert candidates.isdisjoint(SCOREBOARD_DUPLICATES), (
            f"the erasable set still offers {candidates & set(SCOREBOARD_DUPLICATES)}"
        )

    def test_the_rest_of_the_totals_row_is_still_erasable(self, cubs_at_braves_1968: Direction) -> None:
        """A guard that emptied the totals row would satisfy the test above.

        The row is an input surface — the real packages erase from it — and only the four the scoreboard
        prints are exempt. Removing more would be trading one defect for a duller board.
        """
        candidates = set(erasable(cubs_at_braves_1968))

        assert batting_total_cell("plate_appearances") in candidates
        assert batting_total_cell("at_bats") in candidates
        assert batting_total_cell("walks") in candidates
        assert batting_total_cell("strikeouts") in candidates
        assert pitching_total_cell("earned_runs") in candidates

    def test_the_four_are_the_ones_the_line_score_states(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️ The exclusion is justified by an identity, so the identity is asserted rather than trusted.

        If a future board stopped satisfying these, the exclusion would be removing cells for a reason
        that had quietly stopped being true — the scoped-justification defect this project has recorded.
        """
        values = cell_values(cubs_at_braves_1968)

        assert values[batting_total_cell("runs")] == values["line_score.offense_runs"]
        assert values[batting_total_cell("hits")] == values["line_score.offense_hits"]
        assert values[pitching_total_cell("runs")] == values["line_score.offense_runs"]
        assert values[pitching_total_cell("hits")] == values["line_score.offense_hits"]

    def test_every_excluded_cell_is_named_by_an_identity_check(self) -> None:
        # The set and the reason cannot drift apart: each name here is one of the two line-score
        # relations, on one of the two sides of the board.
        assert set(SCOREBOARD_DUPLICATES) == {
            batting_total_cell("runs"),
            batting_total_cell("hits"),
            pitching_total_cell("runs"),
            pitching_total_cell("hits"),
        }


class TestAPuzzleNeverCarriesOne:
    @pytest.mark.parametrize("seed", [11, 12, 13])
    def test_an_erased_board_leaves_all_four_given(self, seed: int, cubs_at_braves_1968: Direction) -> None:
        """The property at the level that matters. The set being clean is the mechanism; a produced
        puzzle being clean is the promise, and only the second is what a player meets."""
        puzzle = erase(cubs_at_braves_1968, target_stalls=8, seed=seed)

        assert puzzle is not None
        assert puzzle.erased.isdisjoint(SCOREBOARD_DUPLICATES), (
            f"seed {seed} erased {puzzle.erased & set(SCOREBOARD_DUPLICATES)}, which the scoreboard prints"
        )

    def test_the_board_is_still_a_puzzle_after_the_exclusion(self, cubs_at_braves_1968: Direction) -> None:
        # A fix that made boards unerasable would satisfy every test above by producing nothing.
        puzzle = erase(cubs_at_braves_1968, target_stalls=8, seed=11)

        assert puzzle is not None
        assert len(puzzle.erased) > 20, f"only {len(puzzle.erased)} blanks survived the exclusion"
