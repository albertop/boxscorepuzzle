"""The puzzle identifier leaks nothing and never changes."""

import pytest

from boxscore_forge.identity import puzzle_id


class TestOpacity:
    def test_carries_no_trace_of_the_game_it_came_from(self) -> None:
        # The whole point. A Retrosheet id spells out the team and the date, which section 7
        # withholds until the player has earned them, so transcribing it hands over the reveal.
        identifier = puzzle_id("SLN191310050", "PIT")

        assert "SLN" not in identifier.upper()
        assert "PIT" not in identifier.upper()
        assert "1913" not in identifier

    def test_is_short_enough_to_live_in_a_url(self) -> None:
        assert len(puzzle_id("SLN191310050", "PIT")) == 16
        assert puzzle_id("SLN191310050", "PIT").isalnum()


class TestIdempotence:
    def test_the_same_game_always_gives_the_same_id(self) -> None:
        # Section 21 requires this: regenerating a batch must create no duplicates. Note the id is
        # derived from the game and never from the date it is published on.
        assert puzzle_id("ATL196808080", "CHN") == puzzle_id("ATL196808080", "CHN")

    def test_the_two_directions_of_one_game_are_different_puzzles(self) -> None:
        assert puzzle_id("ATL196808080", "CHN") != puzzle_id("ATL196808080", "ATL")

    def test_different_games_give_different_ids(self) -> None:
        assert puzzle_id("ATL196808080", "CHN") != puzzle_id("ATL196808090", "CHN")

    def test_survives_a_restart(self) -> None:
        # Guards against `hash()` sneaking in: string hashing is salted per interpreter run, so an
        # id built on it would change on every process and break the calendar.
        assert puzzle_id("BAL199404260", "BAL") == "80dbd0c1db735654"


class TestRefusal:
    @pytest.mark.parametrize(("game", "team"), [("", "PIT"), ("SLN191310050", ""), ("", "")])
    def test_refuses_an_incomplete_input(self, game: str, team: str) -> None:
        # A ValueError rather than a project error: an empty argument is a programming mistake, not
        # a boxscore that failed to balance, and the two should not be caught together.
        with pytest.raises(ValueError, match="needs both a game"):
            puzzle_id(game, team)
