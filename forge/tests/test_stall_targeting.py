"""Erasing towards stalls, which is the target that grades difficulty.

A stall is the moment propagation runs dry and something beyond direct substitution is needed to
restart it. Chain length counts how long a solve is instead — a chain-10 board is ten subtractions in
single file, and one was solved by hand in under a minute. These tests fix the distinction so it
cannot quietly collapse back.
"""

import pytest

from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import cell_values, shape_of
from boxscore_forge.erasure import erase
from boxscore_forge.solver import Technique, solve


class TestAStallIsATransition:
    def test_consecutive_bounding_steps_count_once(self, cubs_at_braves_1968: Direction) -> None:
        # ⚠️ The whole distinction. If propagation halts once and three bounding steps follow before
        # it flows again, the player stopped once and thought once. Counting the steps inflates the
        # figure by between 1.6 and 2.6 times, measured, and a standard of five would then accept a
        # board that stops the player twice.
        puzzle = erase(cubs_at_braves_1968, target_stalls=2, seed=1)

        assert puzzle is not None
        runs = 0
        previous = False
        for step in puzzle.solution.deductions:
            bounding = step.technique is Technique.BOUNDING
            runs += bounding and not previous
            previous = bounding

        assert puzzle.solution.stalls == runs
        assert puzzle.solution.stalls <= puzzle.solution.bounding_steps

    def test_a_board_needing_no_bounding_has_no_stalls(self, cubs_at_braves_1968: Direction) -> None:
        # The complete board deduces nothing, so there is nothing to stall on. A metric that cannot
        # report zero cannot report a floor either.
        solution = solve(shape_of(cubs_at_braves_1968), cell_values(cubs_at_braves_1968))

        assert solution.stalls == 0


class TestItAimsAtStalls:
    def test_reaches_the_target(self, cubs_at_braves_1968: Direction) -> None:
        puzzle = erase(cubs_at_braves_1968, target_stalls=3, seed=2)

        assert puzzle is not None
        assert puzzle.solution.stalls >= 3

    def test_a_higher_target_costs_more_cells(self, cubs_at_braves_1968: Direction) -> None:
        # The cell count is whatever reaching the target costs, so asking for more stalls must not
        # arrive at the same board.
        #
        # The ceiling is discovered rather than assumed. This fixture is a nine-batter, two-pitcher
        # 1968 board and how far it stalls depends on the erasure order, so a hardcoded target passes
        # or fails by luck of the seed. That the ceiling is this low is worth knowing on its own: the
        # standard of five needs the footnote line opened as unknowns, which the pool measurement
        # showed and §6 has not yet decided.
        seed = 3
        ceiling = max(
            (target for target in range(1, 8) if erase(cubs_at_braves_1968, target_stalls=target, seed=seed)),
            default=0,
        )
        assert ceiling >= 2, "the fixture stalls at most once, so there is nothing to compare"

        easy = erase(cubs_at_braves_1968, target_stalls=1, seed=seed)
        harder = erase(cubs_at_braves_1968, target_stalls=ceiling, seed=seed)

        assert easy is not None
        assert harder is not None
        assert len(easy.erased) < len(harder.erased)

    def test_it_gives_up_rather_than_relaxing_the_standard(self, cubs_at_braves_1968: Direction) -> None:
        # §22 discards silently and never bends a rule to reach a number.
        assert erase(cubs_at_braves_1968, target_stalls=500, seed=4) is None

    def test_stalls_and_chain_are_different_targets(self, cubs_at_braves_1968: Direction) -> None:
        # If the two produced the same board the new target would be a rename, and the project has
        # carried a renamed metric before.
        by_stalls = erase(cubs_at_braves_1968, target_stalls=3, seed=5)
        by_chain = erase(cubs_at_braves_1968, target_chain=3, seed=5)

        assert by_stalls is not None
        assert by_chain is not None
        assert by_stalls.erased != by_chain.erased


class TestItRefusesAnAmbiguousRequest:
    def test_both_targets_at_once(self, cubs_at_braves_1968: Direction) -> None:
        with pytest.raises(ValueError, match="exactly one"):
            erase(cubs_at_braves_1968, target_chain=5, target_stalls=5, seed=6)

    def test_neither_target(self, cubs_at_braves_1968: Direction) -> None:
        # A silent default would be the worse failure: the caller believes it asked for difficulty.
        with pytest.raises(ValueError, match="exactly one"):
            erase(cubs_at_braves_1968, seed=7)


class TestItStaysReproducible:
    def test_the_same_inputs_give_the_same_puzzle(self, cubs_at_braves_1968: Direction) -> None:
        # §21's idempotence holds for the new target too, or a regenerated batch breaks the calendar.
        first = erase(cubs_at_braves_1968, target_stalls=3, seed=42)
        second = erase(cubs_at_braves_1968, target_stalls=3, seed=42)

        assert first is not None
        assert second is not None
        assert first.erased == second.erased
