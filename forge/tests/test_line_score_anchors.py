"""Every line-score total is loaded, never summed from the rows it verifies.

⚠️ The defect this guards: `offense_hits` was `sum(line.hits for line in batting)`. The verifier then
checked that the batting hits equalled the line score's hits — and both numbers came from the same
rows. An omitted batter, a duplicate, or a join fan-out satisfied every hit identity while the board
no longer corresponded to the historical boxscore. **The anchor was manufactured from what it was
supposed to anchor.**

The test is **per field**, not for hits alone. A human found this one by reading the file; the next
field added the same way should fail here instead. It reads the loader's source rather than running it
because the alternative needs a database, and a test that needs a DSN is skipped in CI and then never
runs at all.
"""

import ast
import re
from pathlib import Path

import pytest

LOADER = Path(__file__).resolve().parents[2] / "discovery" / "difficulty-metrics" / "measure.py"

FIELDS = (
    "offense_by_inning",
    "defense_by_inning",
    "offense_runs",
    "offense_hits",
    "offense_errors",
    "defense_runs",
    "defense_hits",
    "defense_errors",
)


def line_score_arguments() -> dict[str, str]:
    """How each line-score field is built, read out of the loader's `LineScore(...)` call."""
    tree = ast.parse(LOADER.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "LineScore":
            return {keyword.arg: ast.unparse(keyword.value) for keyword in node.keywords if keyword.arg is not None}
    message = "the loader no longer builds a LineScore"
    raise AssertionError(message)


class TestNoAnchorIsDerivedFromWhatItChecks:
    def test_every_field_is_present(self) -> None:
        # A field silently dropped would pass the per-field checks below by not existing.
        assert set(line_score_arguments()) == set(FIELDS)

    @pytest.mark.parametrize("field", FIELDS)
    def test_the_field_is_not_summed_from_the_board(self, field: str) -> None:
        expression = line_score_arguments()[field]

        assert not re.search(r"\bsum\(", expression), (
            f"{field} is summed from the rows it anchors, which is the defect this file exists for"
        )
        assert "batting" not in expression, f"{field} is built from the batting rows it verifies"
        assert "pitching" not in expression, f"{field} is built from the pitching rows it verifies"

    def test_the_inning_arrays_are_parsed_from_the_game_log(self) -> None:
        # These two are the exception that proves the rule: they come from the game log's line-score
        # string, which is a different file from the daily rows, so parsing is loading.
        arguments = line_score_arguments()

        for field in ("offense_by_inning", "defense_by_inning"):
            assert "innings" in arguments[field]

    def test_the_loader_rejects_a_direction_whose_hits_disagree(self) -> None:
        # The check itself, not only its inputs. Loading the anchor and then not comparing it would
        # look identical from the outside.
        text = LOADER.read_text(encoding="utf-8")

        assert "offensive hits disagree with the game table" in text
        assert re.search(r"offense_hits\s*!=\s*sum\(line\.hits", text)
