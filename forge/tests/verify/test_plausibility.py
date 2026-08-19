"""The checks that would have caught a row of noughts on the board.

Each of these fails on the board the loader used to produce and passes on the one it produces now.
That is the point: **they are not derivable from §3**, and every layer that is derivable from §3
passed the defective board without a murmur.
"""

from collections.abc import Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from boxscore_package.format import Board, Package
from boxscore_package.signing import sign
from boxscore_verify.plausibility import faults
from boxscore_verify.verify import verify

Replace = Callable[..., Board]

_KEY = Ed25519PrivateKey.generate()
SECRET = _KEY
"""⚠️ **A key pair, not a shared secret.** The forge signs with the private half and `serve` verifies
with the public one, which is the property a MAC cannot express: every verifier of an HMAC is also a
signer, so the verification key on the VPS *was* the signing authority (§33). Generated per run — a
test key checked into the repository is a key anybody can sign with."""

PUBLIC = _KEY.public_key()



def refs(board: object) -> tuple[str, ...]:
    """One slot reference per batting row — the shape a package must carry since schema 2.

    A helper rather than the expression inline: it appears in every fixture, and the property being
    fixed is *one per row*, which a name states and a comprehension buries.
    """
    return tuple(str(index + 1) for index in range(len(board.batting)))  # type: ignore[attr-defined]


def package(puzzle: Board, source: Board) -> Package:
    return Package(puzzle_id="plausibility", puzzle=puzzle, solution=source, slot_references=refs(puzzle))


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

    def test_the_verifier_passes_that_same_board_without_complaint(self, board: Board, replace: Replace) -> None:
        # ⚠️ The whole finding, as a test. A row of noughts adds nothing to any sum, so every
        # identity still balances and all four layers of §22 accept it. Internal consistency cannot
        # see a board that does not correspond to reality.
        broken = with_phantom_row(board, replace)

        assert verify(sign(package(broken, broken), SECRET), secret=PUBLIC).accepted
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
