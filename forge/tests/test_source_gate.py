"""The source gate must fail closed: absence of a provenance row is not approval.

⚠️ The defect this guards let a game with **no** provenance row into the pool. The filter was
`NOT EXISTS` over an exclusion list, and a game with no row satisfies "not excluded" — so a partial
import, a new season or an identifier mismatch would silently turn "source unknown" into "source
approved". Those games pass every arithmetic identity and still break §32's source policy.

The predicate lives in SQL against a database, so these tests cannot execute it. Two things are checked
instead, and they are not the same strength:

⚠️ **The rendered query**, wherever possible. `eligibility()` builds the whole candidate cohort as a
string with no database involved, so a test can read what the loader will actually send. That survives
renaming, reformatting and moving code between files.

**The source text**, only for the shape of the mistake coming back — an exclusion list where an
acceptance list belongs. That one is about the words, because the defect was the words.

⚠️ **A test that pins a spelling fails on a rename and says nothing about the rule.** One here asserted
the literal `p.source_type IN ({accepted})` and went red when the accepted-source list was hoisted to a
module constant — the rule was intact and the guard could not tell. Rewritten against the rendered SQL,
which is the thing that has to be right.
"""

import ast
import re
import sys
from pathlib import Path

import pytest

LOADER = Path(__file__).resolve().parents[2] / "discovery" / "difficulty-metrics" / "measure.py"
sys.path.insert(0, str(LOADER.parent))
# ⚠️ Safe to import, and the note that said otherwise is retired: `pyodbc` and `connect()` are both
# inside functions, so nothing here opens a database. Checked by parsing before relying on it.
from measure import eligibility  # noqa: E402

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
        """⚠️ **Against the SQL the loader will send, not against how the file spells it.**

        This asserted the literal `p.source_type IN ({accepted})` and broke when that list was hoisted
        to a module constant — the rule was untouched and the guard could not tell the difference. It
        had already been rewritten once before, from `AND EXISTS (...)`, for the same reason.

        The rule: a game with no accepted, non-deduced provenance row produces **no row at all**. It is
        a `CROSS APPLY` rather than an `EXISTS` so that the acceptance predicate and the evidence
        projection come from one row instead of two independent subqueries — but what must hold is that
        the requirement is *positive*, because a `NOT EXISTS` passes when the row is missing.
        """
        rendered = eligibility()
        applied = re.search(r"CROSS APPLY \(SELECT TOP 1 .*?\) AS prov", rendered, re.S)

        assert applied, "the provenance row is no longer selected by a CROSS APPLY; check the rule survived"
        assert "p.is_deduced = 0" in applied.group(0), "a deduced source would now qualify"
        for source in accepted_sources():
            assert f"'{source}'" in applied.group(0), f"{source} is accepted by the constant and not by the SQL"

    def test_the_rendered_cohort_carries_every_filter_the_pool_depends_on(self) -> None:
        """⚠️ **Sharing part of a cohort is worse than sharing none**, and that is how it went wrong.

        `footnote-multiplicity` was repaired to take the shape CTE and the zero-density gate from the
        loader and still wrote its own `admissible` block — so it counted games `load()` cannot return
        while calling the number the production pool. Everything the pool depends on is one string now,
        and this is the check that it stays one.
        """
        rendered = eligibility(gate_clause="AND 1 = 1")

        for required, why in (
            ("dbo.retroGameLogs", "the game-log join is what makes the cross-check an independent source"),
            ("l.VisLineScore IS NOT NULL", "a direction with no line score cannot become a board"),
            ("g.SEASON BETWEEN", "Retrosheet reaches back to 1871 and the sampler never touches those games"),
            ("retroGameProvenance", "§32's source rule"),
            ("AND 1 = 1", "the gate is interpolated where it was asked for"),
        ):
            assert required in rendered, f"{required} left the shared cohort: {why}"

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
