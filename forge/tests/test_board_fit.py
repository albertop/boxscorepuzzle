"""A correct boxscore is not automatically a boxscore this board can show.

Keeping this separate from the identities matters for the same reason a puzzle is discarded rather
than repaired: a rejection is only useful if it says which of the two happened. A boxscore that
fails an identity is wrong. A boxscore that fails here is right, and unusable.
"""

import dataclasses

from boxscore_forge.board_fit import BoardConflict, find_board_conflicts
from boxscore_forge.boxscore import Direction
from boxscore_forge.identities import find_violations


class TestRealGame:
    def test_accepts_a_game_the_board_can_show(self, cubs_at_braves_1968: Direction) -> None:
        assert find_board_conflicts(cubs_at_braves_1968) == ()


class TestDefensiveInterference:
    def test_rejects_a_game_where_someone_reached_on_interference(self, cubs_at_braves_1968: Direction) -> None:
        # Roughly one team-game in 200. The board carries no column or footnote for it, so the
        # player would be asked to close a plate appearance identity with a term they cannot see.
        with_interference = _interference_game(cubs_at_braves_1968)

        conflicts = find_board_conflicts(with_interference)

        assert BoardConflict.INTERFERENCE_HAS_NO_PLACE_ON_THE_BOARD in {conflict.rule for conflict in conflicts}

    def test_rejects_it_while_the_boxscore_itself_stays_valid(self, cubs_at_braves_1968: Direction) -> None:
        # The distinction the two modules exist to keep: this game is arithmetically correct and
        # still cannot be published.
        with_interference = _interference_game(cubs_at_braves_1968)

        assert find_violations(with_interference) == ()
        assert find_board_conflicts(with_interference) != ()


def _interference_game(direction: Direction) -> Direction:
    """The real game, with one at-bat that made an out turned into a reach on interference."""
    return dataclasses.replace(
        direction,
        batting=(dataclasses.replace(direction.batting[0], at_bats=3), *direction.batting[1:]),
        batting_totals=dataclasses.replace(direction.batting_totals, at_bats=35),
        pitching=(dataclasses.replace(direction.pitching[0], outs=19), direction.pitching[1]),
        pitching_totals=dataclasses.replace(direction.pitching_totals, outs=26),
        footnotes=dataclasses.replace(direction.footnotes, left_on_base=9, reached_on_interference=1),
    )
