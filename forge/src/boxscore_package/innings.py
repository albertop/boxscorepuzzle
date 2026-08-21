"""Innings pitched: outs on one side, `4.1` on the other, and one place that converts.

**`4.1` is not a decimal.** It is four innings and one out, so `4.1 + 0.2` is five innings and not
`4.3`. Every quantity in this project is an integer for exactly that reason: the identity tying the
pitching section to the global count is `Outs = 3 x IP`, and a decimal representation turns it into
floating-point arithmetic that fails validation for no visible reason.

**The editable domain is thirds, and that is information rather than a limitation.** A cell can hold
`.0`, `.1` or `.2` and never `.3`, because three outs is a whole inning. A player who knows that
knows something true about the game, and a board that accepts `4.7` is a board whose pitching column
stops adding up to the defensive innings.

This module belongs to the format rather than to the generator or the verifier: the conversion is
part of what the file means, and both sides plus every renderer need the same answer.

⚠️⚠️ **One conversion, two notations, and they are not a contradiction.** `PRINTED` writes `9.0` and
`BOARD` writes `9`; both are correct about their own surface and each had a docstring defending it as
though the other were a mistake.

  **PRINTED** — the reveal and the hand-solve pack. A newspaper boxscore writes `9.0`, and the reveal
  exists to be that object. The trailing digit is also what carries the information in a column where
  some rows read `4.1`: a mixture of `4.1` and `4` does not line up.

  **BOARD** — the grid the player types into. The thirds keys offer `.1` and `.2`, so a whole inning is
  entered as `4` and reads back as `4`; padding it to `4.0` would show the player a form the keypad
  never produces.

**The formula is here and nowhere else.** It existed in five copies outside tests and they had already
drifted in front of the player — the board printing `4` while the reveal printed `9.0` for the same
kind of value. `forge/tests/test_one_innings_conversion.py` refuses a re-introduced copy.
"""

import re
from enum import Enum
from typing import Final

OUTS_PER_INNING: Final = 3


class Innings(Enum):
    """Which notation a surface writes. **Named at the call site, never inferred.**

    A boolean would read `to_display(outs, True)`, and the next reader would have to come here to learn
    what `True` means about a boxscore.
    """

    PRINTED = "printed"
    BOARD = "board"
_PATTERN: Final = re.compile(r"^(\d+)(?:\.([0-9]))?$")


class InningsError(ValueError):
    """The text is not innings pitched, or names a fraction of an inning that cannot exist."""


def to_display(outs: int, notation: Innings = Innings.PRINTED) -> str:
    """Outs as a surface writes them: 13 → `4.1` either way, 12 → `4.0` printed and `4` on the board.

    ⚠️ **The default is `PRINTED` because the hand-solve pack takes it**, and the pack is §22's launch
    gate — it must not change while it is being solved, so the notation it already receives is the one
    that costs nothing to keep. Every other caller names its notation.
    """
    if outs < 0:
        message = f"innings pitched cannot be negative, got {outs} outs"
        raise InningsError(message)
    whole, thirds = divmod(outs, OUTS_PER_INNING)
    if notation is Innings.BOARD and thirds == 0:
        return str(whole)
    return f"{whole}.{thirds}"


def from_display(text: str) -> int:
    """`4.1` back to 13 outs, refusing anything baseball does not write.

    Refuses `.3` through `.9` explicitly rather than rounding or truncating them. A player cannot
    enter them through the keypad §9 describes, but a value arriving from anywhere else must be
    rejected rather than quietly reinterpreted — silently turning `4.3` into `4.1` would put a number
    on the board that nobody typed.

    ⚠️ **Both notations parse.** `4` and `4.0` are the same twelve outs written for two surfaces, and a
    parser that accepted only one would make the notation choice a data question.
    """
    match = _PATTERN.match(text.strip())
    if match is None:
        message = f"{text!r} is not innings pitched"
        raise InningsError(message)
    whole, fraction = match.group(1), match.group(2) or "0"
    if int(fraction) >= OUTS_PER_INNING:
        message = f"{text!r} claims {fraction} outs into an inning, and three outs is a whole one"
        raise InningsError(message)
    return int(whole) * OUTS_PER_INNING + int(fraction)


def enterable_fractions() -> tuple[str, ...]:
    """What a keypad may offer beyond the digits: `.1` and `.2`, and deliberately no decimal point.

    A decimal-point key would let `.3` through `.9` be typed and then rejected. Two explicit keys
    make the domain visible on the keypad itself and wrong values unenterable by construction.
    """
    return tuple(f".{fraction}" for fraction in range(1, OUTS_PER_INNING))
