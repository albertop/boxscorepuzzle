"""Whether a valid boxscore is one this board can actually show.

Deliberately separate from `identities`. That module answers "is this boxscore wrong"; this one
answers "is this boxscore unusable". Both reject, and a rejection is only worth having if it says
which of the two happened — a boxscore rejected here is arithmetically correct and stays correct.

This is not the pool quality filter. Compressibility, zero density, line score variety and digit
range decide whether a usable boxscore makes a good *puzzle*, and they depend on measurements that
have not been taken. What is here is only the hard question of whether the board can represent the
game at all.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum

from boxscore_forge.boxscore import Direction


class BoardConflict(StrEnum):
    """Reasons a correct boxscore still cannot be published as a puzzle."""

    INTERFERENCE_HAS_NO_PLACE_ON_THE_BOARD = "interference_has_no_place_on_the_board"


@dataclass(frozen=True, slots=True)
class Conflict:
    rule: BoardConflict
    detail: str


def find_board_conflicts(direction: Direction) -> tuple[Conflict, ...]:
    """Return every reason the board cannot show this game. Empty means it can."""
    return tuple(_check_interference(direction))


def _check_interference(direction: Direction) -> Iterator[Conflict]:
    """Reaching base on defensive interference is a plate appearance with nowhere to be printed.

    The width budget allows six data columns and the footnote line already carries four values. A
    fifth that is zero in more than 99% of games costs board space in every puzzle to serve one in
    two hundred, so those games leave the pool instead.
    """
    reached = direction.footnotes.reached_on_interference
    if reached:
        yield Conflict(
            BoardConflict.INTERFERENCE_HAS_NO_PLACE_ON_THE_BOARD,
            f"{reached} batter(s) reached on defensive interference, which the board cannot show",
        )
