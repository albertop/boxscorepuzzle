"""What each layer refuses, exercised directly. (coverage of `verify.py`'s rejection paths)

⚠️⚠️ **`verify.py` was the last module under 90%, and everything missing was a rejection.** That is
the worst shape for a gap: this project's standing rule is that **the absence of a check reads as the
presence of a passing one**, and a rejection path no test has watched fire is a check nobody has seen
work. A `raise` deleted, or a condition narrowed until it never holds, leaves the suite green and the
malformed package accepted.

⚠️ These drive the layer functions rather than `verify()`, because `verify()` stops at the first
rejection — so a fault reachable only after an earlier layer would pass is unreachable through the
front door, and a test that went through it would be asserting the *order* of the layers instead of
the refusal.
"""

import pytest

from boxscore_package.format import Board, Package
from boxscore_package.signing import sign
from boxscore_verify.verify import (
    UNSIGNED,
    Fault,
    Layer,
    check_signature,
    slots_of,
)
from tests.verify.helpers import PUBLIC, SECRET, refs


def _package(board: Board) -> Package:
    return Package(
        labels=("C",) * len(board.batting),
        pitcher_labels=("C",) * len(board.pitching),
        puzzle_id="000000000000001f",
        puzzle=board,
        solution=board,
        slot_references=refs(board),
        offense_is_home=True,
    )


class TestTheSignatureLayerRefusesToBeSkippedByAccident:
    """⚠️⚠️ **`None` is an error and `UNSIGNED` is a decision, and the difference is the whole point.**

    A caller who forgets the argument gets a loud `ValueError`; a caller who means *do not check this*
    has to say so in a word that appears in the source. **A default of "skip" is how verification that
    passes when its secret is missing gets shipped** — the shape `CLAUDE.md` records under *fail closed
    at boundaries*, and the reason `verify()` has no default for `secret`.
    """

    def test_no_secret_at_all_is_an_error_rather_than_a_skipped_layer(self, board: Board) -> None:
        with pytest.raises(ValueError, match="pass UNSIGNED to skip this layer, deliberately"):
            check_signature(_package(board), None, board)

    def test_unsigned_skips_the_layer_and_says_nothing(self, board: Board) -> None:
        """The other half. A guard that refused both would satisfy the test above and be useless."""
        assert check_signature(_package(board), UNSIGNED, board) is None

    def test_an_unsigned_package_is_refused_when_a_key_is_supplied(self, board: Board) -> None:
        rejection = check_signature(_package(board), PUBLIC, board)

        assert rejection is not None
        assert rejection.layer is Layer.SIGNATURE
        assert rejection.fault is Fault.CORRUPTED

    def test_a_signed_package_passes_the_layer(self, board: Board) -> None:
        assert check_signature(sign(_package(board), SECRET), PUBLIC, board) is None

    def test_a_signature_from_another_key_is_refused(self, board: Board) -> None:
        """⚠️ A valid signature that is not *this* key's. The layer must compare rather than merely
        find something signature-shaped."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: PLC0415

        stranger = Ed25519PrivateKey.generate()
        rejection = check_signature(sign(_package(board), stranger), PUBLIC, board)

        assert rejection is not None
        assert rejection.fault is Fault.CORRUPTED


class TestTheLineupIsReadFromWhatThePackagePublishes:
    def test_the_slots_are_the_leading_digits_of_the_references(self, board: Board) -> None:
        """⚠️ Derived from `slot_references` rather than carried alongside — a second copy would be a
        second thing to disagree. `9a` and `9b` are two rows sharing the ninth place."""
        assert slots_of(_package(board)) == tuple(range(1, len(board.batting) + 1))

    def test_two_rows_sharing_a_slot_report_the_same_place(self, board: Board) -> None:
        package = _package(board)
        shared = (*refs(board)[:-2], "9a", "9b")
        from dataclasses import replace  # noqa: PLC0415

        assert slots_of(replace(package, slot_references=shared))[-2:] == (9, 9)
