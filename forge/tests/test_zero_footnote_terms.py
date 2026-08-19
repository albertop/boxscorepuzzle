"""A footnote term worth zero is never erased.

⚠️ **How this was found, because no test could have caught it.** The operator solved a 19-stall board
with the footnote line visible — the `v05-P1-02` defect handed the terms back on the printed page — and
it was hard. So the difficulty was there *without* them. Meanwhile the measurement said opening the
footnotes tripled the stall count.

Both were true. When `HBP`, `SF`, `SH` and `CI` are all zero for a batter the row identity is
`PA = AB + BB`: the four terms contribute nothing **because they did not happen**. Erasing one asked the
solver to deduce a zero, which it did, correctly, and recorded as a step. The solver stalled sixteen
times filling in zeros and a person never met a single one.

**The instrument was working and pointed at the wrong thing.** Every other measurement defect recorded
in this project was a broken instrument; this one computed exactly what it claimed to compute. That is
why no test caught it and why a human solving a board did.

⚠️ **A consequence worth stating, and it is the open question the re-measurement settles.** If only the
non-zero terms are erasable, the *positions* of the blanks announce which rows carry the term: a player
seeing `HBP: 3` above three boxes knows those three rows have it, and with a total of 3 each box is 1.
The deduction left is only where one row holds two of something. So this fix may not make footnotes
cheap — it may reveal that they were never expensive. The measurement the operator ordered is what
decides whether they stay erasable at all.
"""

import pytest

from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import cell_values, footnote_cell
from boxscore_forge.erasure import erasable, erase
from boxscore_forge.identities import FOOTNOTE_COLUMNS


def footnote_cells(direction: Direction) -> list[str]:
    return [footnote_cell(index, column) for index in range(len(direction.batting)) for column in FOOTNOTE_COLUMNS]


class TestOnlyNonZeroTermsAreCandidates:
    def test_no_zero_footnote_cell_is_erasable(self, cubs_at_braves_1968: Direction) -> None:
        values = cell_values(cubs_at_braves_1968)
        candidates = set(erasable(cubs_at_braves_1968))

        offered_zeros = [
            name for name in footnote_cells(cubs_at_braves_1968) if name in candidates and values[name] == 0
        ]

        assert not offered_zeros, (
            f"the erasable set offers {len(offered_zeros)} footnote zeros, e.g. {offered_zeros[:3]}"
        )

    def test_the_non_zero_ones_are_still_offered(self, cubs_at_braves_1968: Direction) -> None:
        """A rule that removed every footnote cell would satisfy the test above.

        The live terms are what the cells were opened for — the row identity closes on them and they are
        the only ones a player can be asked anything about.
        """
        values = cell_values(cubs_at_braves_1968)
        candidates = set(erasable(cubs_at_braves_1968))
        live = [name for name in footnote_cells(cubs_at_braves_1968) if values[name] != 0]

        assert live, "this board carries no live footnote term, so the test proves nothing"
        assert all(name in candidates for name in live), "a live term was excluded along with the zeros"

    def test_this_board_is_almost_entirely_zeros(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️ The number that explains the whole correction, asserted so it cannot quietly change.

        §6 warns that nine boards in ten have every footnote term at zero. On this one it is 35 of 36 —
        so the measurement that opened these cells was, on a board like this, measuring one real cell
        and thirty-five zeros.
        """
        values = cell_values(cubs_at_braves_1968)
        names = footnote_cells(cubs_at_braves_1968)

        zeros = [name for name in names if values[name] == 0]

        assert len(names) == 36
        assert len(zeros) == 35, f"{len(zeros)} of {len(names)} are zero; the fixture has changed"


class TestAPuzzleNeverAsksForAZero:
    @pytest.mark.parametrize("seed", [907, 908, 909])
    def test_no_erased_footnote_cell_is_worth_zero(self, seed: int, cubs_at_braves_1968: Direction) -> None:
        """The property at the level a player meets. The candidate set is the mechanism; a produced
        board is the promise, and only the second is what reaches a screen."""
        values = cell_values(cubs_at_braves_1968)
        puzzle = erase(cubs_at_braves_1968, target_stalls=1, seed=seed)

        assert puzzle is not None
        zeros = [name for name in puzzle.erased if name.startswith("footnotes") and values[name] == 0]

        assert not zeros, f"seed {seed} erased {zeros}, each a box asking the player to type 0"

    def test_the_board_is_still_erasable_at_all(self, cubs_at_braves_1968: Direction) -> None:
        # A rule that made boards unerasable would satisfy every test above by producing nothing.
        puzzle = erase(cubs_at_braves_1968, target_stalls=1, seed=907)

        assert puzzle is not None
        assert len(puzzle.erased) > 15, f"only {len(puzzle.erased)} blanks survived"
