"""The footnote line is given. No per-batter cell is erasable.

⚠️ **These cells were opened on a measurement and closed on a measurement, and the second one is a
correction of the first rather than a new result.**

The run that opened them reported the median board going from 5 stalls to 15, and only 56% of boards
reaching five without them. Both halves were true and both were counting zeros: when `HBP`, `SF`, `SH`
and `CI` are all zero for a batter the row identity is `PA = AB + BB`, so an erased zero asked the solver
to deduce a value that existed only because the thing did not happen. It did, correctly, and recorded a
step each time.

The pool run: coverage with the cells erasable and with them given is **the same at every target**, and
pair by pair the two are identical on every field in 91% of trials. **96% of the pool's footnote terms
are zero**, and on most boards there is not one term to erase — which is why the two arms cannot be told
apart.

⚠️ **How it was found, because nothing here could have caught it.** The operator solved a 19-stall board
with the footnote values printed, found it hard, and noticed the number did not match the experience.
The solver was working correctly and the values were genuinely unknown to it. They were just worth zero.
This file is the guard that keeps the decision; it is not what would have found the defect.
"""

import pytest

from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import footnote_cell
from boxscore_forge.erasure import erasable, erase
from boxscore_forge.identities import FOOTNOTE_COLUMNS


class TestNoFootnoteCellIsACandidate:
    def test_the_erasable_set_offers_none_of_them(self, cubs_at_braves_1968: Direction) -> None:
        offered = set(erasable(cubs_at_braves_1968))
        every = {footnote_cell(i, c) for i in range(len(cubs_at_braves_1968.batting)) for c in FOOTNOTE_COLUMNS}

        assert every, "this board has no footnote cells, so the test proves nothing"
        assert not (offered & every), f"{len(offered & every)} footnote cells are still erasable"

    def test_the_grid_is_still_erasable(self, cubs_at_braves_1968: Direction) -> None:
        # A rule that emptied the candidate set would satisfy the test above and produce no puzzles.
        offered = set(erasable(cubs_at_braves_1968))

        assert len(offered) > 60, f"only {len(offered)} cells are erasable"
        assert any(name.startswith("batting[") for name in offered)
        assert any(name.startswith("pitching[") for name in offered)


class TestNoPuzzleCarriesAFootnoteBlank:
    @pytest.mark.parametrize("seed", [907, 908, 909])
    def test_an_erased_board_leaves_the_whole_line_given(self, seed: int, cubs_at_braves_1968: Direction) -> None:
        """The property at the level a player meets. The candidate set is the mechanism; a produced
        board is the promise, and only the second reaches a screen."""
        puzzle = erase(cubs_at_braves_1968, target_stalls=1, seed=seed)

        assert puzzle is not None
        blanks = [name for name in puzzle.erased if name.startswith("footnotes")]

        assert not blanks, f"seed {seed} erased {blanks}"

    def test_the_board_is_still_a_puzzle(self, cubs_at_braves_1968: Direction) -> None:
        puzzle = erase(cubs_at_braves_1968, target_stalls=1, seed=907)

        assert puzzle is not None
        assert len(puzzle.erased) > 15, f"only {len(puzzle.erased)} blanks survived"
