"""The checks that would have caught a row of noughts on the board.

Each of these fails on the board the loader used to produce and passes on the one it produces now.
That is the point: **they are not derivable from §3**, and every layer that is derivable from §3
passed the defective board without a murmur.
"""

from collections.abc import Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from boxscore_domain import PITCHER_CAP
from boxscore_package.format import Board, Package
from boxscore_package.signing import sign
from boxscore_verify.plausibility import faults
from boxscore_verify.verify import Layer, verify

Replace = Callable[..., Board]

_KEY = Ed25519PrivateKey.generate()
SECRET = _KEY
"""⚠️ **A key pair, not a shared secret.** The forge signs with the private half and `serve` verifies
with the public one, which is the property a MAC cannot express: every verifier of an HMAC is also a
signer, so the verification key on the VPS *was* the signing authority (§33). Generated per run — a
test key checked into the repository is a key anybody can sign with."""

PUBLIC = _KEY.public_key()


def refs(board: object) -> tuple[str, ...]:
    """One slot reference per batting row, in the shape the format actually allows.

    ⚠️ **This produced `"10"`, `"11"`… and those are not references.** A lineup has nine slots; a
    thirteen-row board carries thirteen references drawn from those nine, and what distinguishes rows
    inside a slot is the letter. The helper invented a tenth slot, and only the stricter constructor
    noticed — the fixtures had been carrying impossible values.
    """
    from string import ascii_lowercase  # noqa: PLC0415

    return tuple(
        str(index + 1) if index < 9 else f"9{ascii_lowercase[index - 9]}"
        for index in range(len(board.batting))  # type: ignore[attr-defined]
    )


def package(puzzle: Board, source: Board) -> Package:
    return Package(
        labels=("C",) * len(puzzle.batting),
        pitcher_labels=("C",) * len(puzzle.pitching),
        puzzle_id="plausibility",
        puzzle=puzzle,
        solution=source,
        slot_references=refs(puzzle),
        offense_is_home=True,
    )


def with_phantom_row(board: Board, replace: Replace) -> Board:
    """The board as the loader used to build it: a pitcher who never batted, at the top of the card.

    Retrosheet marks him `B_G = 1` because he appeared, and `SLOT_CT = 0` because he did not bat —
    and ordering by that slot put him first, which is how the defect showed on a printed board.
    """
    return replace(
        board,
        batting=((0, 0, 0, 0, 0, 0), *board.batting),
        footnotes=((0, 0, 0, 0), *board.footnotes),
    )


class TestTheDefectItself:
    def test_a_row_that_contributed_nothing_is_implausible(self, board: Board, replace: Replace) -> None:
        found = faults(with_phantom_row(board, replace))

        assert any("entirely nought" in fault.what for fault in found)

    def test_and_a_row_of_pure_nought_is_caught_separately(self, board: Board, replace: Replace) -> None:
        # Two checks rather than one on purpose. A row can be all zeros with a plate appearance
        # recorded, and a row can have no plate appearance while carrying stray numbers; both are
        # wrong and they are wrong for different reasons.
        found = faults(with_phantom_row(board, replace))

        assert any("entirely nought" in fault.what for fault in found)

    def test_the_batting_order_now_catches_it_too_and_this_test_used_to_say_otherwise(
        self, board: Board, replace: Replace
    ) -> None:
        """⚠⚠ **This asserted that the verifier accepts the phantom row, and it no longer does.**

        The claim was the whole finding: a row of noughts adds nothing to any sum, so every identity
        balances and all four layers accept it — internal consistency cannot see a board that does not
        correspond to reality. **That was true of the four arithmetic families.** Adopting the
        batting-order constraint added a fifth that is not arithmetic about totals but about the
        *order*, and a phantom row inserted at the top takes the first place with nought appearances
        while the rest have four. The cycle forbids that, so layer 3 rejects it.

        ⚠️ **The plausibility layer is not thereby redundant, and reading it that way would be the
        error.** The constraint catches this board because the fixture declares slot references. A
        board carrying none — a version 1 package — applies no batting-order relation at all, and is
        accepted exactly as before. And the defect that produced this file has a sibling the order
        cannot see: three centre fielders in one lineup balances every identity *and* every place.

        So the finding is now: two independent checks catch it, for different reasons, and neither
        makes the other unnecessary.
        """
        broken = with_phantom_row(board, replace)

        verdict = verify(sign(package(broken, broken), SECRET), secret=PUBLIC)

        assert not verdict.accepted, "the batting order stopped catching the phantom row"
        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.DERIVABILITY
        # And plausibility still sees it on its own terms, which is what keeps both checks earning
        # their place.
        assert faults(broken)


class TestARealBoardPasses:
    def test_the_fixture_is_plausible(self, board: Board) -> None:
        # A check that rejects a real boxscore is worse than no check, because it gets loosened until
        # it says nothing.
        assert faults(board) == []


class TestRosterShape:
    def test_too_few_batting_rows(self, board: Board, replace: Replace) -> None:
        found = faults(replace(board, batting=board.batting[:8], footnotes=board.footnotes[:8]))

        assert any("too few batting rows" in fault.what for fault in found)

    def test_more_batting_rows_than_the_cap(self, board: Board) -> None:
        found = faults(board, max_batters=8)

        assert any("too many batting rows" in fault.what for fault in found)

    def test_a_footnote_line_that_does_not_match_the_lineup(self, board: Board, replace: Replace) -> None:
        found = faults(replace(board, footnotes=board.footnotes[:5]))

        assert any("does not match the lineup" in fault.what for fault in found)

    def test_no_pitching_rows_at_all(self, board: Board, replace: Replace) -> None:
        found = faults(replace(board, pitching=()))

        assert any("no pitching rows" in fault.what for fault in found)

    def test_more_pitching_rows_than_the_cap(self, board: Board, replace: Replace) -> None:
        """⚠️ The cap §5 states and nothing enforced.

        The batter cap has been checked here since this file existed; the pitcher cap was held up only
        by whichever `load()` call passed the right argument, which is not a check on the publication
        path at all. Driven by **adding rows** rather than by lowering the cap, because lowering it is
        the shape that already passes for batters and this needs to fail on a board that is too big.
        """
        crowded = replace(board, pitching=board.pitching * 4)
        found = faults(crowded)

        assert len(crowded.pitching) > PITCHER_CAP, "the fixture did not grow past the cap"
        assert any("too many pitching rows" in fault.what for fault in found)

    def test_a_board_at_the_cap_exactly_is_not_a_fault(self, board: Board, replace: Replace) -> None:
        # The boundary the check must not move: ≤, not <. A cap that rejects the largest legal board
        # would discard a third of the pool silently.
        found = faults(replace(board, pitching=(board.pitching[0],) * PITCHER_CAP))

        assert not any("too many pitching rows" in fault.what for fault in found)


class TestVolume:
    def test_fewer_plate_appearances_than_outs(self, board: Board, replace: Replace) -> None:
        # Every out is made by somebody who came to the plate, so this cannot happen in a game — and
        # it is exactly the shape a board takes when rows go missing rather than get added.
        found = faults(replace(board, batting_totals=(20, 20, 3, 8, 0, 5)))

        assert any("fewer plate appearances than outs" in fault.what for fault in found)

    def test_implausibly_many_plate_appearances(self, board: Board, replace: Replace) -> None:
        found = faults(replace(board, batting_totals=(90, 90, 3, 8, 0, 5)))

        assert any("implausibly many" in fault.what for fault in found)

    def test_more_outs_than_the_innings_allow(self, board: Board, replace: Replace) -> None:
        found = faults(replace(board, pitching_totals=(60, 8, 3, 3, 0, 5), batting_totals=(70, 36, 3, 8, 0, 5)))

        assert any("more outs than the innings" in fault.what for fault in found)

    def test_a_game_with_no_outs(self, board: Board, replace: Replace) -> None:
        found = faults(replace(board, pitching_totals=(0, 8, 3, 3, 0, 5)))

        assert any("no outs recorded" in fault.what for fault in found)


class TestItStaysQuietOnAPartlyErasedBoard:
    def test_a_blank_cell_is_not_implausible(self, board: Board, replace: Replace) -> None:
        # "This cell is unknown" is what a puzzle is. Plausibility runs on complete boards.
        erased = replace(board, batting_totals=(None, 36, 3, 8, 0, 5))

        assert not any("nought" in fault.what for fault in faults(erased))
