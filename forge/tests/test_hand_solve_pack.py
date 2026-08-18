"""The hand-solve pack asserts its own constraints, because it is a launch gate.

§22 makes solving fifty by hand a gate rather than a review step, and the pack carries an experiment
inside it: a third of the boards come from the set layer 3b cannot certify. **A pack that reports
quotas it does not meet invalidates that experiment silently**, and it has happened once — weighted
sampling produced zero boards at the easiest rung and only the printed summary showed it.

So the audit is tested for what it *rejects*. An audit that never fires cannot be told apart from one
that is broken.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "discovery" / "hand-solve"))

from build_pack import (  # type: ignore[import-not-found]
    PRE_1950_ALLOWANCE,
    QUOTAS,
    WANTED,
    audit,
)


def board(target: int, index: int, **changes: object) -> SimpleNamespace:
    """A stand-in carrying only what the audit reads, so the test needs no database."""
    fields: dict[str, object] = {
        "target": target,
        "certified": True,
        "has_substitution": True,
        "has_live_footnote": True,
        "season": 1990,
        "game_id": f"game{index}",
    }
    fields.update(changes)
    return SimpleNamespace(
        target=fields["target"],
        certified=fields["certified"],
        has_substitution=fields["has_substitution"],
        has_live_footnote=fields["has_live_footnote"],
        loaded=SimpleNamespace(season=fields["season"], game_id=fields["game_id"]),
    )


def a_valid_pack() -> list[SimpleNamespace]:
    """Fifty boards that satisfy every quota, so the failures below differ by one thing each."""
    pack: list[SimpleNamespace] = []
    index = 0
    uncertified_left = round(WANTED / 3)
    for target, quota in QUOTAS.items():
        # Spread across rungs, and never a whole rung. Layer 3b's uncertified boards concentrate at
        # the hard end, and a pack where one rung is entirely uncertified compares that rung against
        # the rest — difficulty wearing certification's clothes.
        here = min(uncertified_left, quota // 2)
        uncertified_left -= here
        for position in range(quota):
            pack.append(board(target, index, certified=position >= here))
            index += 1
    return pack


class TestTheAuditPasses:
    def test_a_pack_that_meets_every_quota(self) -> None:
        audit(a_valid_pack())


class TestTheAuditRejects:
    def test_a_missing_chain_rung(self) -> None:
        # The failure that already happened: every board at the hard end and none at the easy one.
        pack = a_valid_pack()
        pack[0] = board(13, 900)

        with pytest.raises(SystemExit, match="chain 5 has"):
            audit(pack)

    def test_too_few_boards(self) -> None:
        with pytest.raises(SystemExit, match=f"wanted {WANTED}"):
            audit(a_valid_pack()[:-1])

    def test_the_uncertified_share_drifting(self) -> None:
        # The experiment needs about a third from the set 3b cannot certify. Without them the pack
        # measures nothing about whether 3b should become a gate.
        pack = [board(item.target, index, certified=True) for index, item in enumerate(a_valid_pack())]

        with pytest.raises(SystemExit, match="uncertified boards"):
            audit(pack)

    def test_the_era_allowance_exceeded(self) -> None:
        pack = a_valid_pack()
        for item in pack[: PRE_1950_ALLOWANCE + 1]:
            item.loaded.season = 1930

        with pytest.raises(SystemExit, match="pre-1950 boards"):
            audit(pack)

    def test_the_same_game_twice(self) -> None:
        # One board per game, so no solver meets the same lineup twice and recognises it.
        pack = a_valid_pack()
        pack[1].loaded.game_id = pack[0].loaded.game_id

        with pytest.raises(SystemExit, match="the same game appears twice"):
            audit(pack)

    def test_a_rung_that_is_entirely_uncertified(self) -> None:
        # ⚠️ The confound the real pack fell into: layer 3b certifies every chain-5 board and 91% of
        # chain-11 ones, so filling the hardest rung first made all seventeen uncertified boards
        # chain 11 — and every chain-11 board uncertified. Uncertified and hard would have been the
        # same variable and the afternoon would have measured difficulty.
        pack = [board(item.target, index, certified=item.target != 5) for index, item in enumerate(a_valid_pack())]

        with pytest.raises(SystemExit, match="entirely uncertified"):
            audit(pack)

    def test_no_board_with_a_suffixed_label(self) -> None:
        pack = a_valid_pack()
        for item in pack:
            item.has_substitution = False

        with pytest.raises(SystemExit, match="suffixed label"):
            audit(pack)

    def test_no_board_with_a_live_footnote(self) -> None:
        pack = a_valid_pack()
        for item in pack:
            item.has_live_footnote = False

        with pytest.raises(SystemExit, match="live footnote"):
            audit(pack)
