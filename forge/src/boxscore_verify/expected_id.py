"""The puzzle identifier, derived again on the verifying side.

⚠️ **This is a deliberate second implementation of `boxscore_forge.identity.puzzle_id`.** §22 forbids
the verifier importing generator code — a checker that shares functions with the thing it checks
inherits its bugs and the validation is theatre. So the rule is restated here rather than imported,
and `tests/verify/test_expected_id.py` asserts the two agree on a spread of inputs rather than
trusting that they do.

**What it is for.** A published package carries no game id — §7 withholds the team and the date until
the player has earned them, and `published()` strips the field. The only thing tying a package to the
game the producer claims it came from is the identifier, and the identifier is a function of the game.
So the gate recomputes it from the evidence and compares. Without that, `Evidence` is an unbound
assertion by the same producer that built the package: evidence from a different game with matching
totals would satisfy every check.

The duplication is the smallest part of this file. The reason it exists is the part worth reading.
"""

import hashlib
from typing import Final

NAMESPACE: Final = "boxscorepuzzle/puzzle/v1"
"""Domain separation. Stated here as well as in the forge, and the two are asserted equal."""

LENGTH: Final = 16


def expected_puzzle_id(game_id: str, offense_team: str) -> str:
    """What a package's identifier must be, if it is the puzzle the evidence describes.

    Both inputs are required and neither may be empty: a blank game or a blank team would hash to a
    stable value and bind nothing, which is the failure this is here to prevent rather than a corner
    case to tolerate.
    """
    if not game_id or not offense_team:
        message = "an expected puzzle id needs both a game and the team batting in it"
        raise ValueError(message)
    return hashlib.sha256(f"{NAMESPACE}|{game_id}|{offense_team}".encode()).hexdigest()[:LENGTH]


__all__ = ["LENGTH", "NAMESPACE", "expected_puzzle_id"]
