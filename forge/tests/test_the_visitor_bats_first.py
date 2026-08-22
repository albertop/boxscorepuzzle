"""Every board comes from a game the visiting club batted first.

**A construction rule, not data quality.** Retrosheet is describing something real — 49 regular-season
games where the designated home club led off, at neutral sites and rescheduled dates. **The board is
what cannot represent it**: the `x` for the half-inning never played, which side is `AWAY BATTING`, and
the outs for a home team that wins without batting in the ninth all assume the visitor bats first. A
reversed game is a different object, and 49 of them do not justify a special case running on every board
forever.

⚠️⚠️ **No validation layer can see it.** Such a board balances every identity perfectly and is wrong
only about which team is which — the same shape as the three-centre-fielders defect, which four layers
passed and a person found by reading a printed page.

⚠️⚠️ **An acceptance test, never an exclusion.** `EXISTS` over games whose first event has the visitor
batting, not `NOT EXISTS` over the 49: an exclusion list lets a game with *no event rows* through, which
is the fail-open shape `CLAUDE.md` records twice and the one §32 already closed for provenance.
Coverage was measured before relying on it — **100% of games from 1910 to 2029 have a first event** — so
requiring one costs nothing.

**These read the SQL rather than run it.** The rule is stated in a query, and a test needing a DSN is a
test that never runs in CI. `test_the_pool_refuses_them` is the one live check and it skips without a
database rather than passing without one.
"""

import re

import pytest

from boxscore_forge.pool import CONNECTION, POSTSEASON, REGULAR, eligibility, shape_cte

_HOME_BATS_FIRST = """
    SELECT DISTINCT GAME_ID FROM {events} WHERE EVENT_ID = 1 AND BAT_HOME_ID = 1
"""


def statements(query: str) -> str:
    """The query with its comments stripped.

    ⚠️ Written because the first version of this scan searched the raw text for `NOT EXISTS` and found
    it — **in a comment explaining why there is no `NOT EXISTS`**. A guard that reads its own
    documentation as code reports the opposite of the truth.
    """
    return "\n".join(line for line in query.splitlines() if not line.strip().startswith("--"))


class TestTheRuleIsAnAcceptanceTest:
    @pytest.mark.parametrize("season", [REGULAR, POSTSEASON], ids=["regular", "postseason"])
    def test_the_query_requires_a_first_event_with_the_visitor_batting(self, season: object) -> None:
        sql = statements(eligibility(season=season))  # type: ignore[arg-type]

        assert re.search(r"EXISTS\s*\(SELECT 1 FROM \S+ ev", sql), "no first-event requirement at all"
        assert "BAT_HOME_ID = 0" in sql, "the predicate no longer asks who batted first"

    @pytest.mark.parametrize("season", [REGULAR, POSTSEASON], ids=["regular", "postseason"])
    def test_it_is_never_written_as_an_exclusion(self, season: object) -> None:
        # ⚠️ The whole point. `NOT EXISTS ... BAT_HOME_ID = 1` looks equivalent and is not: a game with
        # no event rows satisfies it, so the absence of evidence reads as the presence of a pass.
        sql = statements(eligibility(season=season))  # type: ignore[arg-type]

        assert "NOT EXISTS" not in sql, "the rule became an exclusion; absence would read as a pass"

    def test_each_season_reads_its_own_events_table(self) -> None:
        # A shared literal would read regular-season rows for a postseason game, find no first event,
        # and exclude every postseason board — silently, since an empty pool looks like a strict filter.
        assert "dbo.retroEventsReg" in statements(eligibility(season=REGULAR))
        assert "dbo.retroEventsPost" in statements(eligibility(season=POSTSEASON))

    def test_no_lint_directive_reached_the_sql(self) -> None:
        # The `noqa` for S608 sits after the closing quotes; inside them it would be sent to the server.
        assert "noqa" not in eligibility()


def _cursor() -> object:
    """A live cursor, or a skip. ⚠️ **Not an environment flag**: `skipif` on a variable nobody sets is a
    test that never runs anywhere, which is indistinguishable from one that is broken. This runs on the
    machine that has the database and skips on the one that does not."""
    try:
        import pyodbc  # noqa: PLC0415

        connection = pyodbc.connect(CONNECTION, timeout=15)
    except Exception as unreachable:
        pytest.skip(f"the Retrosheet database is not reachable: {str(unreachable)[:60]}")
    return connection


class TestItActuallyRefusesThem:
    """⚠️ The live half. A scan proving the SQL *says* something is not proof that the server agrees."""

    @pytest.mark.parametrize("season", [REGULAR, POSTSEASON], ids=["regular", "postseason"])
    def test_the_pool_admits_no_game_whose_home_club_batted_first(self, season: object) -> None:
        connection = _cursor()
        with connection:  # type: ignore[attr-defined]
            cursor = connection.cursor()  # type: ignore[attr-defined]
            reversed_games = sorted(
                row[0]
                for row in cursor.execute(_HOME_BATS_FIRST.format(events=season.events))  # type: ignore[attr-defined]
            )
            if not reversed_games:
                # ⚠️ **The postseason has none today, and that is the point of covering it.** The
                # protection is preventive: Retrosheet publishing one later must not need this rule
                # rediscovered. Reported rather than passed silently, so an empty arm never reads as a
                # verified one.
                pytest.skip(f"{season.events} has no such game today; the rule here is preventive")  # type: ignore[attr-defined]

            admitted = {
                row[0]
                for row in cursor.execute(
                    # ⚠️ `seasons="1=1"`: the default fragment carries its own two `?` for the season
                    # window, so the named games would arrive two parameters short of the markers. The
                    # window is irrelevant here — the question is whether *these* games are admitted.
                    # ⚠️ `shape_cte` first: `eligibility()` joins a CTE it does not declare, which is
                    # deliberate — the cohort is composed, not self-contained — and a caller that
                    # forgets it gets `Invalid object name 'shape'` rather than a wrong answer.
                    f"{shape_cte(season)} SELECT g.GAME_ID "  # type: ignore[arg-type]
                    f"{eligibility(season=season, seasons='1=1')} "
                    f"AND g.GAME_ID IN ({','.join('?' * len(reversed_games))})",
                    *reversed_games,
                )
            }

        assert not admitted, f"the pool still admits {sorted(admitted)[:5]}"

    def test_at_least_one_season_actually_has_some(self) -> None:
        # ⚠️ Both arms skipping would look like a pass. The regular season has 49; if it ever has none,
        # either the data changed or this scan stopped finding them, and both are worth a red test.
        connection = _cursor()
        with connection:  # type: ignore[attr-defined]
            found = (
                connection.cursor()
                .execute(  # type: ignore[attr-defined]
                    _HOME_BATS_FIRST.format(events=REGULAR.events)
                )
                .fetchall()
            )

        assert found, "no game anywhere has the home club batting first, so both arms above prove nothing"
