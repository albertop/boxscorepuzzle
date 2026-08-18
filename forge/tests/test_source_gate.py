"""The source gate must fail closed: absence of a provenance row is not approval.

⚠️ The defect this guards let a game with **no** provenance row into the pool. The filter was
`NOT EXISTS` over an exclusion list, and a game with no row satisfies "not excluded" — so a partial
import, a new season or an identifier mismatch would silently turn "source unknown" into "source
approved". Those games pass every arithmetic identity and still break §32's source policy.

The predicate lives in SQL against a database, so these tests read the query text rather than run it.
That is a weaker check than executing it and it is the one available; what it does catch is the shape
of the mistake coming back, which is exactly how it arrived — the same words in a different file.
"""

import ast
import re
from pathlib import Path

import pytest

LOADER = Path(__file__).resolve().parents[2] / "discovery" / "difficulty-metrics" / "measure.py"
SQL_SCRIPTS = sorted((Path(__file__).resolve().parents[2] / "discovery").rglob("*.ps1"))


def loader_text() -> str:
    return LOADER.read_text(encoding="utf-8")


def accepted_sources() -> tuple[str, ...]:
    """Read the constant out of the file rather than importing it.

    The loader opens a database connection on import in some call paths, and a test that needs a DSN
    to check a SQL predicate is a test that gets skipped in CI and then never runs at all.
    """
    tree = ast.parse(loader_text())
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "ACCEPTED_SOURCES":
            return tuple(ast.literal_eval(node.value))  # type: ignore[arg-type]
    message = "the loader no longer defines ACCEPTED_SOURCES"
    raise AssertionError(message)


class TestTheGateIsAnAcceptanceList:
    def test_the_loader_does_not_filter_provenance_by_exclusion(self) -> None:
        # The exact form that failed open. A future edit that reintroduces it fails here.
        text = loader_text()

        # Tightened to the SQL form. A prose mention of the old mistake in a comment is a warning,
        # not a reintroduction of it, and a test that cannot tell those apart would be un-writable.
        offending = re.findall(r"NOT EXISTS \(SELECT[^;]{0,200}?retroGameProvenance", text, re.S)

        assert not offending, "provenance filtered by exclusion again; absence would read as approval"

    def test_the_loader_requires_a_provenance_row(self) -> None:
        text = loader_text()

        assert re.search(r"AND EXISTS \(SELECT 1 FROM dbo\.retroGameProvenance", text)

    def test_it_names_the_sources_it_accepts(self) -> None:
        # An acceptance list is the point: a source kind nobody has seen yet is excluded by not being
        # named, rather than admitted because nobody remembered to exclude it.
        sources = accepted_sources()

        assert sources
        assert "EVR" not in sources, "Negro Leagues games are excluded by §32"
        assert not any(source.startswith("ED") for source in sources), "deduced files are excluded"

    def test_the_accepted_sources_appear_in_the_query(self) -> None:
        text = loader_text()

        assert "source_type IN" in text
        for source in accepted_sources():
            assert source in text


class TestTheSqlScriptsAgree:
    @pytest.mark.parametrize("script", SQL_SCRIPTS, ids=lambda path: path.name)
    def test_no_script_filters_provenance_by_exclusion(self, script: Path) -> None:
        # ⚠️ The same rule in every place that queries the pool. The one predicate that mattered was
        # copied across four files this project, and two of the copies drifted.
        text = script.read_text(encoding="utf-8")

        assert "NOT EXISTS" not in text or "retroGameProvenance" not in text
