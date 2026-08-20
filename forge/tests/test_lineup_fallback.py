"""The conditional retry: try without the batting order, fall back to it only when the target is missed.

⚠️ **Experimental, not adopted.** `docs/reviews/batting-order-reversal.md` carries what is and is not
established. `test_lineup_fallback_cannot_publish.py` is the guard that these boards cannot ship;
this file is about whether the retry does what it says.

The reason the retry is conditional and not a switch: on boards that already reach the target, turning
the constraint on changes almost nothing and converts a median of eight steps into division filler —
a `batting_order` step reads the team's plate-appearance total, divides by nine, and writes the answer
down. **Boards that never need it must never see it**, and that is a property worth a test rather than
a comment.
"""

import pytest

from boxscore_domain import LINEUP_DIVISION_SHARE_CAP
from boxscore_forge.boxscore import Direction
from boxscore_forge.erasure import erase
from boxscore_forge.lineup_fallback import division_against_chain, erase_with_lineup_fallback
from boxscore_forge.solver import Technique

LINEUP = (1, 2, 3, 4, 5, 6, 7, 8, 9)


class TestTheOrdinaryPathIsTriedFirst:
    def test_a_board_that_reaches_the_target_never_sees_the_constraint(self, cubs_at_braves_1968: Direction) -> None:
        # ⚠️ The point of the whole design. Not "the result is the same" -- the constraint must not
        # have been *applied*, because applying it is what costs the filler.
        puzzle, reason = erase_with_lineup_fallback(cubs_at_braves_1968, LINEUP, target_stalls=1, seed=1)

        assert reason == "plain"
        assert puzzle is not None
        techniques = {step.technique for step in puzzle.solution.deductions}
        assert Technique.LINEUP_ARITHMETIC not in techniques, "the plain path produced a division step"
        assert division_against_chain(puzzle) == 0.0

    def test_the_plain_result_is_exactly_what_erase_gives_on_its_own(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️ The fallback must not perturb the boards it does not help.

        If the wrapper changed the seed, the ordering, or the order of attempts, the ordinary path
        would produce a different board than the generator produces today -- two things varying where
        one was intended, which is the confound this project keeps meeting.
        """
        direct = erase(cubs_at_braves_1968, target_stalls=1, seed=7)
        through, reason = erase_with_lineup_fallback(cubs_at_braves_1968, LINEUP, target_stalls=1, seed=7)

        assert reason == "plain"
        assert direct is not None and through is not None
        assert through.erased == direct.erased, "the wrapper produced a different board than erase() alone"
        assert through.given == direct.given


class TestTheFallbackIsOnlyReachedWhenTheTargetIsMissed:
    def test_an_unreachable_target_says_so_rather_than_returning_a_board(self, cubs_at_braves_1968: Direction) -> None:
        # A stall count no erasure of this board can reach, with or without the constraint.
        puzzle, reason = erase_with_lineup_fallback(cubs_at_braves_1968, LINEUP, target_stalls=99, seed=1)

        assert puzzle is None
        assert reason == "unreachable", "an unreachable target must not be reported as a discard"

    def test_the_retry_uses_the_same_seed_and_ordering(self, cubs_at_braves_1968: Direction) -> None:
        """The two attempts differ in treatment, never in trajectory.

        ⚠️ Checked by reconstructing the retry independently: whatever the fallback returns for an
        unreachable-without-the-constraint target must equal `erase(..., slots=LINEUP)` at the same
        seed. A re-seeded retry would still return *a* board, and the report would read as clean as an
        honest one.
        """
        target = 99
        assert erase(cubs_at_braves_1968, target_stalls=target, seed=3) is None, (
            "this board reaches the target without the constraint, so the retry is never exercised"
        )
        expected = erase(cubs_at_braves_1968, target_stalls=target, seed=3, slots=LINEUP)
        puzzle, _ = erase_with_lineup_fallback(cubs_at_braves_1968, LINEUP, target_stalls=target, seed=3)

        assert (puzzle is None) == (expected is None)
        if puzzle is not None and expected is not None:
            assert puzzle.erased == expected.erased


class TestTheFallbackActuallyProducesBoards:
    """⚠️ The branch the whole design exists for, exercised rather than assumed.

    Targets 4 to 7 at seed 1 are missed by the ordinary path on the shared fixture and reached with
    the batting order on. Without a test that lands here, `fallback` and `discarded_filler` are two
    untaken branches and the retry is a thing nobody has seen work.
    """

    @pytest.mark.parametrize("target", [4, 5, 6, 7])
    def test_a_missed_target_is_reached_through_the_fallback(self, cubs_at_braves_1968: Direction, target: int) -> None:
        assert erase(cubs_at_braves_1968, target_stalls=target, seed=1) is None, (
            f"the ordinary path reaches {target} stalls, so this case no longer tests the fallback"
        )
        puzzle, reason = erase_with_lineup_fallback(cubs_at_braves_1968, LINEUP, target_stalls=target, seed=1)

        assert reason == "fallback"
        assert puzzle is not None
        assert puzzle.solution.stalls >= target, "the fallback returned a board short of its target"
        assert division_against_chain(puzzle) <= LINEUP_DIVISION_SHARE_CAP


class TestTheFillerCapDiscardsRatherThanRepairs:
    def test_a_fallback_board_over_the_cap_is_discarded_and_says_why(
        self, cubs_at_braves_1968: Direction, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """⚠️ The discard branch, reached by lowering the cap rather than hunting for a filler-heavy board.

        The condition being tested is *share exceeds cap*, and which side of it moves is irrelevant to
        the branch. Hunting the pool for a board above 20% would make this test depend on the pool.

        ⚠️ It must not be enough that `None` comes back: `unreachable` also returns `None`, and those
        are different populations. The reason is the thing under test.
        """
        monkeypatch.setattr("boxscore_forge.lineup_fallback.LINEUP_DIVISION_SHARE_CAP", -1.0)
        puzzle, reason = erase_with_lineup_fallback(cubs_at_braves_1968, LINEUP, target_stalls=4, seed=1)

        assert puzzle is None, "a board over the cap was returned"
        assert reason == "discarded_filler", "a discard was reported as something else"

    def test_the_same_board_is_kept_when_the_cap_allows_it(self, cubs_at_braves_1968: Direction) -> None:
        # ⚠️ The other half. Without it the test above passes if the fallback returns None always.
        puzzle, reason = erase_with_lineup_fallback(cubs_at_braves_1968, LINEUP, target_stalls=4, seed=1)

        assert reason == "fallback"
        assert puzzle is not None

    @pytest.mark.parametrize(
        ("division", "total", "kept"),
        [(0, 20, True), (4, 20, True), (5, 20, False), (10, 20, False)],
    )
    def test_the_cap_is_a_strict_ceiling_at_the_boundary(self, division: int, total: int, *, kept: bool) -> None:
        """⚠️ The boundary itself, because `>` against `>=` is the classic off-by-one in a filter.

        At the cap of 0.20, four steps in twenty is exactly 20% and is kept; five is 25% and is not.
        Written as a table so the boundary case is a row rather than a thing someone reasoned about.
        """
        share = division / total

        assert (share <= LINEUP_DIVISION_SHARE_CAP) is kept

    def test_a_board_with_nothing_to_deduce_has_a_share_of_zero(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️ Not a stub: a board with every cell given is a real board, and it deduces nothing.

        The guard exists so an empty path is *zero division*, never a `ZeroDivisionError`. Reached with
        a genuine `Puzzle` rather than a fake one, because a fake object would prove the arithmetic and
        not the case.
        """
        from boxscore_forge.constraints import cell_values, shape_of  # noqa: PLC0415
        from boxscore_forge.erasure import Puzzle  # noqa: PLC0415
        from boxscore_forge.solver import solve  # noqa: PLC0415

        shape = shape_of(cubs_at_braves_1968)
        given = cell_values(cubs_at_braves_1968)
        solution = solve(shape, given)

        assert not solution.deductions, "an unerased board deduced something, so this is the wrong case"
        assert division_against_chain(Puzzle(shape=shape, given=given, erased=frozenset(), solution=solution)) == 0.0

    def test_the_ratio_counts_only_lineup_steps(self, cubs_at_braves_1968: Direction) -> None:
        puzzle = erase(cubs_at_braves_1968, target_stalls=1, seed=5)

        assert puzzle is not None
        counted = sum(1 for step in puzzle.solution.deductions if step.technique is Technique.LINEUP_ARITHMETIC)
        assert counted == 0, "a board erased without slots cannot contain a lineup step"
        assert division_against_chain(puzzle) == 0.0

    def test_the_denominator_is_chain_length_and_not_the_deduction_count(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️⚠️ v27-P2-13. **A test that changes its verdict when the denominator changes.**

        The previous test for this asserted the ratio equalled `lineup / len(deductions)` — and passed,
        because the board it used has zero lineup steps and `0/a == 0/b` for every denominator. It
        agreed with both implementations and could distinguish neither.

        This one takes a real fallback board that *has* lineup steps, requires the two candidate
        denominators to actually differ, and pins the ratio to the one the cap was measured with. Swap
        `chain_length` for `len(deductions)` in the implementation and this fails.
        """
        puzzle, reason = erase_with_lineup_fallback(cubs_at_braves_1968, LINEUP, target_stalls=7, seed=1)

        assert reason == "fallback" and puzzle is not None, "no fallback board, so there is nothing to pin"
        lineup_steps = sum(1 for step in puzzle.solution.deductions if step.technique is Technique.LINEUP_ARITHMETIC)
        chain = puzzle.solution.chain_length
        deductions = len(puzzle.solution.deductions)

        assert lineup_steps > 0, "this board has no division steps, so the denominator cannot be told apart"
        assert chain != deductions, (
            f"chain_length and the deduction count are both {chain} on this board, so it cannot "
            f"discriminate between the two denominators"
        )
        assert division_against_chain(puzzle) == lineup_steps / chain
        assert division_against_chain(puzzle) != lineup_steps / deductions

    def test_the_two_boards_the_cap_exists_to_discard_are_over_it_in_this_unit(self) -> None:
        """⚠️ The cap has to reject the cases that produced it, or it protects nothing.

        `9 / 24 = 0.375` and `9 / 26 = 0.346` are the two ATL boards, measured against `chain_length`,
        which is where `0.20` came from. Under the deduction-count denominator the same boards sit near
        `0.24` and `0.18` and **at least one of them passes the cap** — which is exactly what
        v27-P2-13 was. Written as literal arithmetic because the boards themselves are not in the test
        fixtures; the point being pinned is the threshold's unit, not those two directions.
        """
        for lineup_steps, chain in ((9, 24), (9, 26)):
            assert lineup_steps / chain > LINEUP_DIVISION_SHARE_CAP, (
                f"the cap no longer rejects {lineup_steps}/{chain}, one of the two boards that set it"
            )


class TestTheReasonIsReturnedNotInferred:
    def test_every_reason_the_function_can_return_is_one_of_the_four_documented(
        self, cubs_at_braves_1968: Direction
    ) -> None:
        """⚠️ A caller that has to work out which path produced a board will work it out wrongly.

        Every measurement comparing these boards needs to know which population each one is in, and
        `plain` and `fallback` are different populations -- that is the entire finding behind this
        design. A typo'd reason string would split a population silently.
        """
        allowed = {"plain", "fallback", "discarded_filler", "unreachable"}
        seen = {
            erase_with_lineup_fallback(cubs_at_braves_1968, LINEUP, target_stalls=target, seed=seed)[1]
            for target in (1, 4, 99)
            for seed in (1, 2)
        }

        assert seen <= allowed, f"undocumented reason: {seen - allowed}"
        # ⚠️ Each named, not "at least two of them". A set that happened to contain one value would
        # satisfy a weaker assertion and prove that only one path was ever taken.
        assert "plain" in seen, "no attempt took the ordinary path"
        assert "fallback" in seen, "no attempt reached its target through the constraint"
        assert "unreachable" in seen, "no attempt missed the target under both treatments"
