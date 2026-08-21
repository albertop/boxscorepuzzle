"""A signed package cannot be edited through its metadata. (v37-P3-01)

⚠️⚠️ **The fourth field `v36-P3-05` named, and the only one left mutable.** `Solution.values`,
`Puzzle.given` and `Derivation.values` were frozen when that finding was closed; `Package.metadata`
was not, and **it is the one where mutability is worst.**

`canonical_bytes` is `published().as_json()`, so adding, removing or replacing a metadata key
**changes the bytes the signature covers** while the signature stays where it is. The object goes on
reporting itself as frozen and as signed, and the two statements stop being about the same thing: a
valid signature over a package that is no longer the package that was signed.

⚠️ Nothing did this. The point is that `frozen=True` on the dataclass is what a reader checks, and it
was answering a different question from the one they were asking.
"""

from dataclasses import replace
from typing import Any

import pytest

from boxscore_package.format import Board, Package
from boxscore_package.signing import canonical_bytes, sign
from boxscore_package.signing import verify as verify_signature
from tests.verify.helpers import PUBLIC, SECRET, refs


def _package(board: Board, metadata: dict[str, Any]) -> Package:
    """A signed package carrying exactly this metadata.

    ⚠️ Built here rather than reusing `test_layers.package`, which takes no metadata — and noted
    rather than quietly copied: **that factory now stands in three verify files**, which is the shape
    `v36-P3-08` closed for `refs()` and the key pair. Recorded in `docs/reviews/todo.md`.
    """
    return sign(
        Package(
            labels=("C",) * len(board.batting),
            pitcher_labels=("C",) * len(board.pitching),
            puzzle_id="000000000000001f",
            puzzle=board,
            solution=board,
            slot_references=refs(board),
            offense_is_home=True,
            metadata=metadata,
        ),
        SECRET,
    )


@pytest.fixture
def signed(board: Board) -> Package:
    return _package(board, {"note": "original", "families": ["column_sum", "row_identity"]})


class TestTheMappingItselfRefusesToBeWritten:
    def test_a_key_cannot_be_replaced(self, signed: Package) -> None:
        with pytest.raises(TypeError):
            signed.metadata["note"] = "edited"  # type: ignore[index]

    def test_a_key_cannot_be_added(self, signed: Package) -> None:
        """⚠️ The shape that matters most: `game_id` put back on a published package would defeat
        `check_no_leaking_metadata`, which reads this mapping."""
        with pytest.raises(TypeError):
            signed.metadata["game_id"] = "SLN19680808"  # type: ignore[index]

    def test_a_list_inside_the_metadata_cannot_be_appended_to(self, signed: Package) -> None:
        """⚠️ `families` is the one nested container this schema carries, and a frozen mapping over a
        live list is the freeze with a hole exactly where the interesting field is."""
        assert isinstance(signed.metadata["families"], tuple)

        with pytest.raises(AttributeError):
            signed.metadata["families"].append("invented")  # type: ignore[attr-defined]


class TestTheSignatureGoesOnDescribingThePackage:
    def test_editing_the_dict_it_was_built_from_does_not_move_the_signed_bytes(self, board: Board) -> None:
        """⚠️⚠️ Stated as the signature rather than as the attribute, because that is the damage.

        Without the copy in `__post_init__` the caller keeps a handle on the mapping the signature
        covers, and `frozen=True` says nothing about it.
        """
        metadata: dict[str, Any] = {"note": "original", "families": ["column_sum"]}
        package = _package(board, metadata)
        before = canonical_bytes(package)

        metadata["note"] = "edited"
        metadata["families"].append("invented")

        assert canonical_bytes(package) == before
        verify_signature(package, PUBLIC)

    def test_as_json_hands_out_a_copy_rather_than_the_mapping_itself(self, signed: Package) -> None:
        """⚠️ Without this the freeze is one `as_json()` away from irrelevant."""
        document = signed.as_json()

        document["metadata"]["note"] = "edited"

        assert signed.metadata["note"] == "original"

    def test_the_published_shape_is_frozen_too(self, signed: Package) -> None:
        """`published()` rebuilds through the same constructor, so the shape that actually travels —
        the one `canonical_bytes` signs — carries the same guarantee rather than a fresh mutable dict."""
        travelling = signed.published()

        with pytest.raises(TypeError):
            travelling.metadata["note"] = "edited"  # type: ignore[index]


class TestTheRoundTripSurvivesTheFreeze:
    """⚠️ The cost this change could have had, asserted rather than assumed.

    List values become tuples in the constructor. `from_json` builds metadata from parsed JSON, where
    arrays are lists — so if the constructor did not normalise both sides, **a package read from disk
    would stop comparing equal to the one that wrote it**, and every round-trip test in the tree would
    be asserting something weaker than it reads as.
    """

    def test_a_package_read_back_equals_the_one_that_wrote_it(self, signed: Package) -> None:
        restored = Package.from_json(signed.as_json())

        assert restored == signed
        assert restored.metadata["families"] == signed.metadata["families"]

    def test_a_tuple_and_a_list_of_the_same_families_are_the_same_package(self, board: Board) -> None:
        as_list = _package(board, {"families": ["column_sum", "row_identity"]})
        as_tuple = replace(as_list, metadata={"families": ("column_sum", "row_identity")})

        assert canonical_bytes(as_tuple) == canonical_bytes(as_list)
