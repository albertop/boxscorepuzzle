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
"""

import re
from typing import Final

OUTS_PER_INNING: Final = 3
_PATTERN: Final = re.compile(r"^(\d+)(?:\.([0-9]))?$")


class InningsError(ValueError):
    """The text is not innings pitched, or names a fraction of an inning that cannot exist."""


def to_display(outs: int) -> str:
    """Outs as the board prints them: 13 → `4.1`.

    Whole innings keep their `.0` — a column where some rows read `4.1` and others read `4` does not
    line up, and the trailing digit is the part carrying the information.
    """
    if outs < 0:
        message = f"innings pitched cannot be negative, got {outs} outs"
        raise InningsError(message)
    return f"{outs // OUTS_PER_INNING}.{outs % OUTS_PER_INNING}"


def from_display(text: str) -> int:
    """`4.1` back to 13 outs, refusing anything baseball does not write.

    Refuses `.3` through `.9` explicitly rather than rounding or truncating them. A player cannot
    enter them through the keypad §9 describes, but a value arriving from anywhere else must be
    rejected rather than quietly reinterpreted — silently turning `4.3` into `4.1` would put a number
    on the board that nobody typed.
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
