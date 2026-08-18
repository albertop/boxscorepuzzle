"""The verifier derives the puzzle identifier again, and the two derivations must agree.

§22 forbids the verifier importing generator code, so `expected_puzzle_id` restates the rule rather
than calling it. Two copies of a rule drift — this project has watched it happen four times — so the
copies are asserted equal here instead of being trusted.

⚠️ **Asserted on a spread of inputs, not on one.** Two functions agreeing on a single game would also
agree if both returned a constant, and a constant identifier binds nothing at all.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from boxscore_forge.identity import puzzle_id
from boxscore_verify.expected_id import LENGTH, NAMESPACE, expected_puzzle_id


class TestTheTwoDerivationsAgree:
    @given(
        game=st.text(min_size=1, max_size=20).filter(lambda value: value.strip() != ""),
        team=st.text(min_size=1, max_size=5).filter(lambda value: value.strip() != ""),
    )
    def test_they_agree_on_anything(self, game: str, team: str) -> None:
        assert expected_puzzle_id(game, team) == puzzle_id(game, team)

    def test_they_agree_on_the_shape_of_a_real_game(self) -> None:
        assert expected_puzzle_id("SLN19131005", "CHN") == puzzle_id("SLN19131005", "CHN")

    def test_the_namespace_is_the_same_string(self) -> None:
        # The one input neither function takes. If the forge changed its namespace, every identifier
        # would move and the property above would catch it — but only after both had been changed.
        source = (__import__("boxscore_forge.identity", fromlist=["identity"]),)
        assert source[0]._NAMESPACE == NAMESPACE
        assert source[0]._LENGTH == LENGTH


class TestItDistinguishes:
    def test_the_two_directions_of_one_game_differ(self) -> None:
        # Not a formality: a game yields up to two puzzles and they are different puzzles, so an
        # identifier that ignored the batting team would collide them and the gate would accept
        # evidence for either.
        assert expected_puzzle_id("SLN19131005", "CHN") != expected_puzzle_id("SLN19131005", "SLN")

    def test_two_games_differ(self) -> None:
        assert expected_puzzle_id("SLN19131005", "CHN") != expected_puzzle_id("SLN19131006", "CHN")

    @pytest.mark.parametrize(("game", "team"), [("", "CHN"), ("SLN19131005", ""), ("", "")])
    def test_an_empty_input_is_refused(self, game: str, team: str) -> None:
        # Fail closed. An empty side would hash to a stable value that binds nothing, which is worse
        # than no identifier because it looks like one.
        with pytest.raises(ValueError, match="needs both a game"):
            expected_puzzle_id(game, team)
