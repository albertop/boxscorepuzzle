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

import re
import sys
from pathlib import Path

import pytest

LOADER = Path(__file__).resolve().parents[2] / "discovery" / "difficulty-metrics" / "measure.py"
sys.path.insert(0, str(LOADER.parent))
# ⚠️ Safe to import, and the note that said otherwise is retired: `pyodbc` and `connect()` are both
# inside functions, so nothing here opens a database. Checked by parsing before relying on it.
import measure  # noqa: E402
from measure import POSTSEASON, REGULAR, Season, eligibility, shape_cte  # noqa: E402

SQL_SCRIPTS = sorted((Path(__file__).resolve().parents[2] / "discovery").rglob("*.ps1"))


def loader_text() -> str:
    return LOADER.read_text(encoding="utf-8")


def accepted_sources() -> tuple[str, ...]:
    """What the publication gate accepts: the provenanced kinds plus the postseason.

    ⚠️⚠️ **This parsed the assignment with `ast.literal_eval` and that was the wrong instrument.** It
    worked only while the tuple was spelled out, and it raised `ValueError: malformed node` the moment
    the list became `(*PROVENANCE_SOURCES, POSTSEASON_SOURCE)` — a guard failing because the *spelling*
    changed while the rule held exactly. That is the failure this file already records twice in its own
    docstring, met a third time in the helper rather than in a test.

    The note it used to carry — that importing the loader would need a DSN — is retired and was already
    retired above: `pyodbc` and `connect()` are both inside functions.
    """
    return tuple(measure.ACCEPTED_SOURCES)


def provenance_sources() -> tuple[str, ...]:
    """What a `dbo.retroGameProvenance` row may say, which is what the regular season's SQL interpolates.

    ⚠️ **Narrower than `accepted_sources()` on purpose.** `EVE` is the postseason and has no provenance
    row; putting it in the predicate that admits the existing pool widens that predicate, which is a
    change to what the pool contains whether or not today's data notices.
    """
    return tuple(measure.PROVENANCE_SOURCES)


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
        for source in provenance_sources():
            assert f"'{source}'" in applied.group(0), f"{source} is accepted by the constant and not by the SQL"
        assert "'EVE'" not in applied.group(0), "the postseason source widened the regular season's predicate"

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
        for sources in (accepted_sources(), provenance_sources()):
            assert sources
            assert "EVR" not in sources, "Negro Leagues games are excluded by §32"
            assert not any(source.startswith("ED") for source in sources), "deduced files are excluded"

    def test_the_accepted_sources_appear_in_the_query(self) -> None:
        text = loader_text()

        assert "source_type IN" in text
        for source in provenance_sources():
            assert source in text


class TestTheSqlScriptsAgree:
    @pytest.mark.parametrize("script", SQL_SCRIPTS, ids=lambda path: path.name)
    def test_no_script_filters_provenance_by_exclusion(self, script: Path) -> None:
        # ⚠️ The same rule in every place that queries the pool. The one predicate that mattered was
        # copied across four files this project, and two of the copies drifted.
        text = script.read_text(encoding="utf-8")

        assert "NOT EXISTS" not in text or "retroGameProvenance" not in text


class TestTheSeasonsFailTheSameWay:
    """⚠️⚠️ **The postseason is a second admission rule, and a second rule is how a gate gets weaker.**

    `dbo.retroGamesPost` has no row in `dbo.retroGameProvenance` — that table was built from
    `events-reg` — so the pool's `CROSS APPLY` drops every postseason game. **Today the postseason is
    excluded correctly and by accident**, and the obvious way to admit it is to loosen that apply to
    `OUTER`.

    That change would also make a *regular-season* game with a missing provenance row admissible, with
    nulls where the source used to be. It is this project's recorded defect stated exactly — *the
    absence of a check reading as the presence of a passing one* — arriving in the half nobody was
    editing, attached to a feature that has nothing to do with it.

    So each season carries its own positive admission and both produce **no row** when the game does
    not qualify. These tests are what stops the two from diverging.
    """

    def test_neither_season_admits_by_outer_apply(self) -> None:
        for season in (REGULAR, POSTSEASON):
            rendered = eligibility(season=season)

            assert "OUTER APPLY" not in rendered, f"{season.games} admits a game with no qualifying row"
            assert "CROSS APPLY" in rendered, f"{season.games} lost the apply that makes absence a rejection"

    def test_the_postseason_is_admitted_by_a_floor_and_nothing_else(self) -> None:
        from boxscore_domain import POSTSEASON_SEASON_FLOOR  # noqa: PLC0415

        rendered = eligibility(season=POSTSEASON)
        applied = re.search(r"CROSS APPLY \(.*?\) AS prov", rendered, re.S)

        assert applied, "the postseason lost its admission entirely"
        assert f"g.SEASON >= {POSTSEASON_SEASON_FLOOR}" in applied.group(0), "the season floor is not the admission"
        assert "retroGameProvenance" not in applied.group(0), "the postseason has no provenance table to read"

    def test_the_regular_season_still_requires_a_provenance_row(self) -> None:
        """The half that must not have moved. Stated again here because the postseason change is
        exactly the kind that edits one branch and takes the other with it."""
        applied = re.search(r"CROSS APPLY \(SELECT TOP 1 .*?\) AS prov", eligibility(season=REGULAR), re.S)

        assert applied, "the regular season no longer requires a provenance row"
        assert "p.is_deduced = 0" in applied.group(0), "a deduced source would now qualify"

    def test_a_season_never_mixes_its_tables(self) -> None:
        """⚠️ **The three tables travel as one record because a half-swapped set is silent.**

        A cohort reading `retroGamesPost` and `retroDailyReg` would return rows — the daily table has
        every game — and they would be the wrong rows, balancing perfectly. Nothing downstream can see
        that, which is the whole reason `Season` is a record rather than three arguments.
        """
        for season, wrong in ((REGULAR, "Post"), (POSTSEASON, "Reg")):
            surface = eligibility(season=season) + shape_cte(season)

            assert wrong not in surface, f"{season.games}'s cohort reads a {wrong} table"

    def test_every_field_of_a_season_is_used_somewhere(self) -> None:
        """⚠️ **A field nobody renders is a table nobody swapped.** `substitutions` is read only by the
        row queries inside `load()`, so the rendered cohort cannot see it — the loader's source is
        checked instead, because an unused field would leave `dbo.retroSubstitutionsReg` hardcoded and
        a postseason board would carry the wrong men's entry positions while balancing.
        """
        text = loader_text()

        for field in ("games", "daily", "substitutions", "admission"):
            assert f"season.{field}" in text, f"Season.{field} is declared and never interpolated"

    def test_the_seasons_are_the_only_two(self) -> None:
        # A third season type (All-Star) exists in the database and is deliberately not admitted: 95
        # games, 2 admissible directions, and an exhibition where the rosters are not a club's.
        declared = [value for value in vars(sys.modules["measure"]).values() if isinstance(value, Season)]

        assert len(declared) == 2, f"{len(declared)} seasons are declared; each one needs its own admission rule"
