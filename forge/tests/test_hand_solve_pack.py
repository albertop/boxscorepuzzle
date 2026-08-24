"""The hand-solve pack asserts its own constraints, because it is a launch gate.

§22 makes solving fifty by hand a gate rather than a review step, and the pack carries an experiment
inside it: a third of the boards come from the set layer 3b cannot certify. **A pack that reports
quotas it does not meet invalidates that experiment silently**, and it has happened once — weighted
sampling produced zero boards at the easiest rung and only the printed summary showed it.

So the audit is tested for what it *rejects*. An audit that never fires cannot be told apart from one
that is broken.
"""

import random
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
        # ⚠️ **Flat, not nested under `loaded`.** A `Candidate` is read from a shipped package now, and
        # §7 strips the season from one -- so `season` comes from the calendar's game id and both live
        # on the candidate itself. The old stub carried them one level down and no longer stands in for
        # anything.
        season=fields["season"],
        game_id=fields["game_id"],
    )


def a_valid_pack() -> list[SimpleNamespace]:
    """`WANTED` boards satisfying every quota, so the failures below differ by one thing each."""
    pack: list[SimpleNamespace] = []
    index = 0
    for target, quota in QUOTAS.items():
        # ⚠️ **Certification is not arranged here any more.** The fixture used to spread uncertified
        # boards across rungs to satisfy a quota the audit enforced; that quota was removed on
        # 2026-08-23 and the audit asks nothing about certification, so arranging it would be the
        # fixture describing a rule that no longer exists.
        for _position in range(quota):
            pack.append(board(target, index))
            index += 1
    # Shuffled, because the audit now rejects a pack ordered by chain — an ascending sequence
    # produces an ascending rating whatever the boards are like. A fixture built in rung order was
    # the audit working, not the audit misfiring.
    random.Random(7).shuffle(pack)  # noqa: S311  - a fixture order, not a secret
    return pack


class TestTheAuditPasses:
    def test_a_pack_that_meets_every_quota(self) -> None:
        audit(a_valid_pack())


class TestCertificationIsReportedRatherThanRequired:
    """⚠⚠ **Two assertions were removed here on 2026-08-23 and this is what stands in their place.**

    The audit used to require about a third of the pack uncertified, and to refuse a rung that was
    *entirely* uncertified. Both were right about a population where certification varied. It does not:
    **5 of 75 shipped boards are certified**, so an unfiltered pack is ~15 of 16 uncertified and every
    rung is uncertified — which the second assertion would have refused, and which is the honest
    description of what ships.

    ⚠️ **Removing an assertion needs a test saying so**, or the next reader cannot tell a rule that
    was retired from one that was never written. `report()` prints the certified count; nothing asserts
    a target, because nobody chose one.
    """

    def test_a_wholly_uncertified_pack_passes(self) -> None:
        pack = [board(item.target, index, certified=False) for index, item in enumerate(a_valid_pack())]

        audit(pack)

    def test_a_wholly_certified_pack_passes_too(self) -> None:
        """⚠️ The other direction. A check that only accepted the *current* mix would be asserting the
        pool's composition under the name of a property of the pack."""
        pack = [board(item.target, index, certified=True) for index, item in enumerate(a_valid_pack())]

        audit(pack)

    def test_a_rung_that_is_entirely_uncertified_passes(self) -> None:
        """The exact shape the removed assertion refused."""
        pack = [board(item.target, index, certified=item.target != 5) for index, item in enumerate(a_valid_pack())]

        audit(pack)


class TestTheAuditRejects:
    def test_a_missing_stall_rung(self) -> None:
        # The failure that already happened: every board at the hard end and none at the easy one.
        # Found by target rather than by index: the pack is shuffled now, so position 0 is not the
        # easiest rung and a test that assumed it was would pass for the wrong reason.
        #
        # ⚠️ **Renamed from `chain` on 2026-08-22**, with the rungs. The pack targeted chain while the
        # generator targeted stalls — the last chain-targeted thing in the tree — and this test named
        # the axis in its own title, so leaving it would have kept the retired word alive in the one
        # place a reader checks what the pack measures.
        pack = a_valid_pack()
        victim = next(index for index, item in enumerate(pack) if item.target == 5)
        pack[victim] = board(11, 900)

        with pytest.raises(SystemExit, match="stall rung 5 has"):
            audit(pack)

    def test_too_few_boards(self) -> None:
        with pytest.raises(SystemExit, match=f"wanted {WANTED}"):
            audit(a_valid_pack()[:-1])

    def test_the_era_allowance_exceeded(self) -> None:
        pack = a_valid_pack()
        for item in pack[: PRE_1950_ALLOWANCE + 1]:
            item.season = 1930

        with pytest.raises(SystemExit, match="pre-1950 boards"):
            audit(pack)

    def test_the_same_game_twice(self) -> None:
        # One board per game, so no solver meets the same lineup twice and recognises it.
        pack = a_valid_pack()
        pack[1].game_id = pack[0].game_id

        with pytest.raises(SystemExit, match="the same game appears twice"):
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
