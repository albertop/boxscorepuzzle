"""The identifier a puzzle carries once it leaves the forge.

Seam C2 asks for an immutable identifier derived from the game. It must be **derived, not
transcribed**: a Retrosheet game id like `SLN191310050` spells out the team and the date, and those
are what section 7 withholds until the player has earned them. Shipping it as the puzzle's id hands
the reveal to anyone who opens the developer tools once, with no effort and no intent.

That is a different thing from the solution being findable. Section 9 already accepts that the
answer lives in the client and is visible to anyone who looks, because the streak is against
yourself. What this avoids is the answer being *legible at a glance*, which costs nothing to
prevent and does not pretend to stop anyone determined.

**The mapping from puzzle id back to game lives in the forge and does not ship** (section 33).
"""

import hashlib

# Domain separation, so an id from this project cannot collide with a hash of the same game
# computed for some other purpose later.
_NAMESPACE = "boxscorepuzzle/puzzle/v1"

# Long enough that collisions are not a practical concern and short enough to sit in a URL.
_LENGTH = 16


def puzzle_id(game_id: str, offense_team: str) -> str:
    """A stable, opaque identifier for one direction of one game.

    Idempotent by construction, which is what section 21 requires: the same game always produces the
    same puzzle with the same id, so regenerating a batch creates no duplicates. Uses `hashlib`
    rather than `hash()` because string hashing is salted per interpreter run and would produce a
    different id on every process.

    The offense team is part of the input because a game yields up to two puzzles, one per
    direction, and they are different puzzles.
    """
    if not game_id or not offense_team:
        message = "a puzzle id needs both a game and the team batting in it"
        raise ValueError(message)
    digest = hashlib.sha256(f"{_NAMESPACE}|{game_id}|{offense_team}".encode())
    return digest.hexdigest()[:_LENGTH]
