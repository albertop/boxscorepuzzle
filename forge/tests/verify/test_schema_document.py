"""The schema document and the code have to say the same thing.

`serve` is built against `docs/package-format-v1.md`, not against this package's source, so a field
the document describes and the code does not ship — or the reverse — is a broken contract between two
systems that deploy separately (§33).

This is the same shape of defect as everything else this week: two places that must agree, with
nothing checking that they do.
"""

import re
from pathlib import Path

from boxscore_package.format import Board, Package, Reveal

DOCUMENT = Path(__file__).resolve().parents[3] / "docs" / "package-format-v1.md"
STRIPPED_KEYS = {"game_id", "retrosheet_id", "season", "date", "teams"}


def documented_fields() -> dict[str, str]:
    """Field name to its Published column, read out of the table rather than restated here."""
    text = DOCUMENT.read_text(encoding="utf-8")
    table = text[text.index("| Field | Type | Null? | Published |") : text.index("### board")]
    found: dict[str, str] = {}
    for line in table.splitlines():
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) == 5 and cells[0].startswith("`"):
            found[cells[0].strip("`")] = cells[3].replace("**", "")
    return found


def a_package(board: Board) -> Package:
    return Package(
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


class TestTheDocumentMatchesTheCode:
    def test_every_documented_field_is_published(self, board: Board) -> None:
        published = a_package(board).published().as_json()

        for name, disposition in documented_fields().items():
            if disposition == "kept":
                assert name in published, f"the document says {name} is kept and it is not published"

    def test_no_field_travels_undocumented(self, board: Board) -> None:
        # The direction that matters more: a field reaching `serve` that nobody wrote down is a
        # contract the client can come to depend on by accident.
        published = a_package(board).published().as_json()

        undocumented = set(published) - set(documented_fields())

        assert not undocumented, f"published but undocumented: {sorted(undocumented)}"

    def test_the_filtered_metadata_keys_are_the_documented_ones(self, board: Board) -> None:
        text = DOCUMENT.read_text(encoding="utf-8")
        named = set(re.findall(r"`(game_id|retrosheet_id|season|date|teams)`", text))
        published = a_package(board).published().as_json()

        assert named == STRIPPED_KEYS
        assert set(published["metadata"]) == {"chain_target"}

    def test_the_schema_version_the_document_states(self, board: Board) -> None:
        text = DOCUMENT.read_text(encoding="utf-8")

        assert "Always `1`" in text
        assert a_package(board).published().as_json()["schema"] == 1
