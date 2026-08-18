"""Taking cells away until the board is a puzzle, and not one cell further.

Two things matter more than which cells come out. The result must be derivable — the solver finishes
without ever guessing, which is the publication rule and the boundary with layer 3 of section 22.
And the same inputs must always produce the same puzzle, because section 21 requires regenerating a
batch to create no duplicates.
"""

import random

import pytest

from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import cell_values, shape_of
from boxscore_forge.erasure import ORDERINGS, erasable, erase
from boxscore_forge.solver import solve


class TestItProducesAPuzzle:
    def test_erases_something(self, cubs_at_braves_1968: Direction) -> None:
        puzzle = erase(cubs_at_braves_1968, target_chain=5, seed=1)

        assert puzzle is not None
        assert puzzle.erased

    def test_what_it_produces_is_derivable(self, cubs_at_braves_1968: Direction) -> None:
        # The publication rule, and the reason the generator needs a solver at all.
        puzzle = erase(cubs_at_braves_1968, target_chain=8, seed=2)

        assert puzzle is not None
        assert solve(shape_of(cubs_at_braves_1968), puzzle.given).is_complete

    def test_recovers_the_original_boxscore_exactly(self, cubs_at_braves_1968: Direction) -> None:
        puzzle = erase(cubs_at_braves_1968, target_chain=8, seed=3)

        assert puzzle is not None
        assert solve(shape_of(cubs_at_braves_1968), puzzle.given).values == cell_values(cubs_at_braves_1968)

    def test_the_given_cells_and_the_erased_ones_partition_the_board(self, cubs_at_braves_1968: Direction) -> None:
        puzzle = erase(cubs_at_braves_1968, target_chain=6, seed=4)

        assert puzzle is not None
        assert puzzle.given.keys() | puzzle.erased == cell_values(cubs_at_braves_1968).keys()
        assert not (puzzle.given.keys() & puzzle.erased)


class TestItAimsAtAChain:
    def test_reaches_the_target(self, cubs_at_braves_1968: Direction) -> None:
        puzzle = erase(cubs_at_braves_1968, target_chain=10, seed=5)

        assert puzzle is not None
        assert puzzle.solution.chain_length >= 10

    def test_stops_rather_than_erasing_everything_it_can(self, cubs_at_braves_1968: Direction) -> None:
        # The cell count is whatever reaching the target costs, so a low target must not walk the
        # board to its compressibility ceiling.
        easy = erase(cubs_at_braves_1968, target_chain=3, seed=6)
        hard = erase(cubs_at_braves_1968, target_chain=15, seed=6)

        assert easy is not None
        assert hard is not None
        assert len(easy.erased) < len(hard.erased)

    def test_gives_up_rather_than_guessing_when_the_target_is_out_of_reach(
        self, cubs_at_braves_1968: Direction
    ) -> None:
        # A target beyond what this boxscore can carry returns nothing. Section 22 discards
        # silently; it never relaxes the rule to hit a number.
        assert erase(cubs_at_braves_1968, target_chain=500, seed=7) is None


class TestItOnlyTouchesTheGrid:
    def test_never_erases_the_line_score(self, cubs_at_braves_1968: Direction) -> None:
        # Section 6: the line score is the board's anchor, given complete and never erased.
        puzzle = erase(cubs_at_braves_1968, target_chain=8, seed=8)

        assert puzzle is not None
        assert not any(cell.startswith("line_score") for cell in puzzle.erased)

    def test_never_erases_the_footnote_totals_or_the_team_footnote(self, cubs_at_braves_1968: Direction) -> None:
        # ⚠️ Narrower than it was. A **per-batter** footnote cell is now erasable — it is an unknown
        # inside the row identity, and opening them takes the median board from 5 stalls to 15. What
        # stays given is the totals row and left-on-base: without those the row identity has two
        # unknowns and no way to separate them, which is a broken puzzle rather than a hard one.
        puzzle = erase(cubs_at_braves_1968, target_chain=8, seed=9)

        assert puzzle is not None
        assert not any(cell.startswith(("footnote_totals", "team_footnotes")) for cell in puzzle.erased)

    @pytest.mark.parametrize("name", sorted(ORDERINGS))
    def test_no_ordering_reaches_outside_the_grid(self, cubs_at_braves_1968: Direction, name: str) -> None:
        # The two rules above stated once as an invariant, so a new ordering cannot quietly acquire
        # the ability to erase something the player is meant to be given.
        puzzle = erase(cubs_at_braves_1968, target_chain=8, seed=10, ordering=name)

        assert puzzle is not None
        assert puzzle.erased <= set(erasable(cubs_at_braves_1968))


class TestItIsReproducible:
    def test_the_same_inputs_give_the_same_puzzle(self, cubs_at_braves_1968: Direction) -> None:
        # Section 21's idempotence, at the erasure step. Without it, regenerating a batch produces
        # different puzzles for the same game and the calendar's no-repetition promise breaks.
        first = erase(cubs_at_braves_1968, target_chain=9, seed=42)
        second = erase(cubs_at_braves_1968, target_chain=9, seed=42)

        assert first is not None
        assert second is not None
        assert first.erased == second.erased

    def test_a_different_seed_gives_a_different_puzzle(self, cubs_at_braves_1968: Direction) -> None:
        first = erase(cubs_at_braves_1968, target_chain=9, seed=42)
        second = erase(cubs_at_braves_1968, target_chain=9, seed=43)

        assert first is not None
        assert second is not None
        assert first.erased != second.erased


class TestOrderings:
    @pytest.mark.parametrize("name", sorted(ORDERINGS))
    def test_every_ordering_produces_a_derivable_puzzle(self, cubs_at_braves_1968: Direction, name: str) -> None:
        puzzle = erase(cubs_at_braves_1968, target_chain=8, seed=11, ordering=name)

        assert puzzle is not None
        assert solve(shape_of(cubs_at_braves_1968), puzzle.given).is_complete

    def test_orderings_differ_from_one_another(self, cubs_at_braves_1968: Direction) -> None:
        # If two strategies produced the same puzzle there would be nothing to measure between them.
        produced = {
            name: erase(cubs_at_braves_1968, target_chain=8, seed=12, ordering=name) for name in sorted(ORDERINGS)
        }
        patterns = {frozenset(p.erased) for p in produced.values() if p is not None}

        assert len(patterns) > 1

    def test_refuses_an_ordering_it_does_not_have(self, cubs_at_braves_1968: Direction) -> None:
        with pytest.raises(ValueError, match="unknown erasure ordering"):
            erase(cubs_at_braves_1968, target_chain=8, seed=13, ordering="spiral")

    def test_the_default_is_the_measured_one(self, cubs_at_braves_1968: Direction) -> None:
        # Not a tautology: it guards the default against drifting back to whichever ordering is
        # convenient. row_first was chosen because it pads the easy board least, and the erasure a
        # player gets should be the one that was measured.
        default = erase(cubs_at_braves_1968, target_chain=8, seed=15)
        named = erase(cubs_at_braves_1968, target_chain=8, seed=15, ordering="row_first")

        assert default is not None
        assert named is not None
        assert default.erased == named.erased

class TestItRefusesADuplicatedCandidateList:
    """The failure that ran for a whole round of measurements, made to fail on its own.

    `erasable()` gained the footnote cells and an instrument that had been adding them itself kept
    doing so. Nothing raised: erasing an already-erased cell is a no-op and the boards stayed valid.
    Only the trajectory moved, because the orderings bucket the cells and a bucket holding each of
    its own entries twice spends half its round-robin turns erasing nothing.

    Tested on every ordering rather than the default, because the two that bucket are the two that
    distort and the third would otherwise look like coverage.
    """

    @pytest.mark.parametrize("ordering", sorted(ORDERINGS))
    def test_every_ordering_rejects_a_repeated_cell(
        self, ordering: str, cubs_at_braves_1968: Direction
    ) -> None:
        cells = erasable(cubs_at_braves_1968)
        doubled = [*cells, *(cell for cell in cells if cell.startswith("footnotes["))]

        with pytest.raises(ValueError, match="more than once"):
            ORDERINGS[ordering](doubled, cubs_at_braves_1968, random.Random(1))  # noqa: S311

    @pytest.mark.parametrize("ordering", sorted(ORDERINGS))
    def test_the_canonical_list_is_accepted(self, ordering: str, cubs_at_braves_1968: Direction) -> None:
        # The other half of the check. A guard that rejects everything is not a guard, and this is
        # the case that proves the canonical list has no duplicates of its own.
        order = ORDERINGS[ordering](erasable(cubs_at_braves_1968), cubs_at_braves_1968, random.Random(1))  # noqa: S311

        assert sorted(order) == erasable(cubs_at_braves_1968)

    def test_the_canonical_list_carries_the_footnote_cells(self, cubs_at_braves_1968: Direction) -> None:
        # The fact the duplication came from not knowing. Stated once, here, so an instrument does
        # not have to re-derive it and get it wrong again.
        assert any(cell.startswith("footnotes[") for cell in erasable(cubs_at_braves_1968))
