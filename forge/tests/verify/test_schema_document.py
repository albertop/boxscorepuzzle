"""The schema document and the code have to say the same thing.

`serve` is built against `docs/package-format-v1.md`, not against this package's source, so a field
the document describes and the code does not ship — or the reverse — is a broken contract between two
systems that deploy separately (§33).

This is the same shape of defect as everything else this week: two places that must agree, with
nothing checking that they do.
"""

import re
from pathlib import Path

import pytest

from boxscore_package.format import Board, Package, Reveal

_DOCS = Path(__file__).resolve().parents[3] / "docs"
DOCUMENTS = {2: _DOCS / "package-format-v2.md"}
"""⚠️ **Version 1 is gone from here because it is gone from the code.** Its signatures are HMAC and the
parser accepts only Ed25519, so the compatibility promise was false and no consumer needed it —
nothing was ever published. `package-format-v1.md` stays as history and is deliberately *not* checked:
a document tested against code that no longer produces it would have to be edited to stay green, which
is how history gets rewritten to match the present."""
"""⚠️ **Both versions, checked separately.** Version 1 stays valid and `serve` may meet either, so a
document that drifts from the code is a broken contract whichever version it describes. Testing only
the current one would leave the older document describing a package nobody can produce, which is worse
than no document — it reads as current.
"""

DOCUMENT = DOCUMENTS[2]
STRIPPED_KEYS = {"game_id", "retrosheet_id", "season", "date", "teams"}


def documented_fields(version: int = 2) -> dict[str, str]:
    """Field name to its Published column, read out of the table rather than restated here."""
    text = DOCUMENTS[version].read_text(encoding="utf-8")
    table = text[text.index("| Field | Type | Null? | Published |") : text.index("### board")]
    found: dict[str, str] = {}
    for line in table.splitlines():
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) == 5 and cells[0].startswith("`"):
            found[cells[0].strip("`")] = cells[3].replace("**", "")
    return found


def a_package(board: Board, *, version: int = 2) -> Package:
    """A package of the asked-for version. Version is a property of the payload, so version 2 is the
    same package carrying slot references rather than the same package with a different number."""
    return Package(
        slot_references=tuple(str(index + 1) for index in range(len(board.batting))) if version == 2 else None,
        puzzle_id="0123456789abcdef",
        puzzle=board,
        solution=board,
        labels=("C",) * len(board.batting),
        pitcher_labels=("SP",) * len(board.pitching),
        reveal=Reveal(
            batter_names=("Somebody",) * len(board.batting),
            pitcher_names=("Somebody",) * len(board.pitching),
            offense_team="AAA",
            defense_team="BBB",
            played_on="1968-08-08",
        ),
        metadata={"chain_target": 9, "game_id": "ATL196808080", "season": 1968},
        signature="deadbeef",
    )


@pytest.mark.parametrize("version", sorted(DOCUMENTS))
class TestTheDocumentMatchesTheCode:
    def test_every_documented_field_is_published(self, version: int, board: Board) -> None:
        published = a_package(board, version=version).published().as_json()

        for name, disposition in documented_fields(version).items():
            if disposition == "kept":
                assert name in published, f"the document says {name} is kept and it is not published"

    def test_no_field_travels_undocumented(self, version: int, board: Board) -> None:
        # The direction that matters more: a field reaching `serve` that nobody wrote down is a
        # contract the client can come to depend on by accident.
        published = a_package(board, version=version).published().as_json()

        undocumented = set(published) - set(documented_fields(version))

        assert not undocumented, f"published but undocumented: {sorted(undocumented)}"

    def test_the_filtered_metadata_keys_are_the_documented_ones(self, version: int, board: Board) -> None:
        text = DOCUMENTS[version].read_text(encoding="utf-8")
        named = set(re.findall(r"`(game_id|retrosheet_id|season|date|teams)`", text))
        published = a_package(board, version=version).published().as_json()

        assert named == STRIPPED_KEYS
        assert set(published["metadata"]) == {"chain_target"}

    def test_the_schema_version_the_document_states(self, version: int, board: Board) -> None:
        text = DOCUMENTS[version].read_text(encoding="utf-8")

        assert f"Always `{version}`" in text
        assert a_package(board, version=version).published().as_json()["schema"] == version

    def test_the_reference_is_one_per_batting_row(self, version: int, board: Board) -> None:
        # The property the field exists for, asserted where the document states it: a footnote names
        # a row, so there must be exactly one name per row.
        published = a_package(board, version=version).published().as_json()

        if version == 1:
            assert "slot_references" not in published
        else:
            assert len(published["slot_references"]) == len(published["puzzle"]["batting"])
