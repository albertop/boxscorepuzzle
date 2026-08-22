"""`load()`'s bookkeeping, driven off fixed rows instead of a server.

⚠️⚠️ **A blanket `pragma: no cover` was written on `load()` first, and it was wrong.** It opens a
connection, so excluding it looked defensible — and **the line between "needs a server" and "needs rows"
is not "touches the database"**. What is inside is mostly logic: the rejection tally, `also`, the
deduplication keyed on game **and** offensive team, and the row-to-`Direction` mapping.

**That is exactly where the pinch-runner defect lived** — a shape query counting "contributed anything"
and a row query counting `PA > 0`, disagreeing, deleting a run. A pragma there would have covered the
one region of this codebase with the worst history, behind an infrastructure excuse.

`pyodbc` is imported **inside** `load()`, which is what makes this possible: a fake in `sys.modules` and
the whole function runs off tuples. Only `_rows` keeps a pragma, because it calls `setinputsizes` with
driver constants and its body is one fetch.

**Every test here was verified by reverting what it asserts.** A test that cannot fail is worse than the
uncovered line it replaced, because it reads as covered.
"""

import sys
from collections import Counter
from types import ModuleType, SimpleNamespace

import pytest

from boxscore_forge.pool import load

_CANDIDATE_COLUMNS = 18


def candidate(game: str, offense: str, defense: str = "OPP", year: int = 1975) -> tuple[object, ...]:
    """One row of the cohort query, in the order `load()` unpacks it."""
    row = [game, year, offense, defense, 0, 8, "000000000", "000000000", 1, 1, 5, 5, 3, 2, "EVN", 0, 30, 8]
    assert len(row) == _CANDIDATE_COLUMNS, "the cohort query's column count changed"
    return tuple(row)


class _Cursor:
    """Answers by looking at the SQL, because `load()` issues five different queries on one cursor."""

    def __init__(self, plan: "_Plan") -> None:
        self._plan, self._answer = plan, []

    def setinputsizes(self, _sizes: object) -> None:
        return None

    def execute(self, sql: str, *params: object) -> "_Cursor":
        self._plan.queries.append((sql, params))
        if "WITH shape" in sql or "SELECT TOP (?)" in sql:
            self._answer = self._plan.candidates_for(params)
        elif "retroTeams" in sql:
            self._answer = self._plan.club
        else:
            # ⚠️ **Keyed on the team, not just the query.** `load()` asks the same two queries twice —
            # once for each club — and a fake that answered by query text alone could not tell the
            # offense's rows from the defense's. The first version could not, so the test for *the
            # other direction has no rows to print* never reached that branch: it stopped at the
            # earlier skip and passed on the wrong refusal.
            #
            # ⚠️ And **(kind, team)**, not team alone: each club is asked for batting *and* pitching, so
            # keying on the club emptied both and the run stopped at the earlier skip again. Two
            # near-misses on the same test, each passing on a refusal it was not written for.
            team = params[1] if len(params) > 1 else ""
            kind = "pitching" if "P_GS" in sql else "batting"
            rows = self._plan.pitching if kind == "pitching" else self._plan.batting
            self._answer = [] if (kind, team) in self._plan.empty_for else rows
        return self

    def fetchall(self) -> list[object]:
        return self._answer


class _Plan:
    """What the fake server holds, and a record of what it was asked."""

    def __init__(  # noqa: PLR0913 - six knobs because `load()` issues five different queries
        self,
        candidates: list[tuple[object, ...]],
        *,
        named: list[tuple[object, ...]] | None = None,
        batting: list[object] | None = None,
        pitching: list[object] | None = None,
        club: list[object] | None = None,
        empty_for: set[tuple[str, str]] | None = None,
    ) -> None:
        self._candidates, self._named = candidates, named or []
        self.batting = batting if batting is not None else [SimpleNamespace()]
        self.pitching = pitching if pitching is not None else [SimpleNamespace()]
        self.club = club if club is not None else [("Boston", "Red Sox")]
        self.empty_for = empty_for or set()
        self.queries: list[tuple[str, tuple[object, ...]]] = []
        self._drawn = False

    def candidates_for(self, params: tuple[object, ...]) -> list[tuple[object, ...]]:
        # The decade sweep passes (limit, decade, decade + 9); the `also` query passes game ids.
        if params and isinstance(params[0], str):
            return self._named
        if self._drawn:
            return []
        self._drawn = True
        return self._candidates

    def cursor(self) -> _Cursor:
        return _Cursor(self)

    def __enter__(self) -> "_Plan":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


@pytest.fixture
def driver(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201 - a factory, typed at each call site
    """Install a fake `pyodbc` and return a function that runs `load()` against a plan."""

    def run(plan: _Plan, **kwargs: object) -> tuple[list[object], Counter[str]]:
        fake = ModuleType("pyodbc")
        fake.connect = lambda *_a, **_k: plan  # type: ignore[attr-defined]
        fake.SQL_VARCHAR = 1  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "pyodbc", fake)
        # ⚠️ The tally comes back, and that is why these tests can fail. Asserting on the returned list
        # alone proved nothing: **an empty list is what every path returns**, so three tests here passed
        # with the refusals they were written for deleted from the loader.
        rejected: Counter[str] = Counter()
        return load(1, rejected=rejected, **kwargs), rejected  # type: ignore[arg-type]

    return run


class TestWhatItRefuses:
    """⚠️⚠️ **Each of these asserts the *reason*, not the empty list.** Written against `loaded == []`
    first, all three passed with the refusal deleted from `load()` — because every rejection path and the
    success path with no rows all return `[]`. **Found by reverting each check and watching nothing turn
    red**, which is the only way a guard's own worth is established."""

    def test_a_direction_with_no_rows_is_dropped_before_anything_else(self, driver) -> None:  # noqa: ANN001
        # No batting rows means no board. It is the one skip that is *not* tallied — the direction never
        # entered the pool, as opposed to entering and failing.
        loaded, rejected = driver(_Plan([candidate("BOS19750101", "BOS")], empty_for={("batting", "BOS")}))

        assert loaded == []
        assert rejected == Counter(), f"a missing-rows skip should not be counted as a rejection: {rejected}"

    def test_a_direction_whose_other_half_cannot_be_printed_is_counted(self, driver) -> None:  # noqa: ANN001
        # ⚠️ The reveal prints **both** clubs (schema 5). A game whose other direction has no rows
        # cannot produce a boxscore, and it is a *counted* rejection rather than a silent skip: a pool
        # that quietly shrinks is the shape §22 says to discard loudly.
        loaded, rejected = driver(_Plan([candidate("BOS19750101", "BOS")], empty_for={("batting", "OPP")}))

        assert loaded == []
        assert rejected["the other direction has no rows to print"] == 1

    def test_a_club_the_season_cannot_name_is_refused(self, driver) -> None:  # noqa: ANN001
        # §7 draws the real boxscore with names. A club named `Unknown` shipped once, from a join that
        # resolved 98.4% of rows — which looks exactly like one that resolved all of them.
        loaded, rejected = driver(_Plan([candidate("BOS19750101", "BOS")], club=[]))

        assert loaded == []
        assert rejected["retroTeams cannot name a club for that season"] == 1


class TestTheDraw:
    def test_one_query_per_decade_across_the_window(self, driver) -> None:  # noqa: ANN001
        plan = _Plan([], batting=[])
        driver(plan, window=(1910, 1949))

        decades = [params[1] for sql, params in plan.queries if "SELECT TOP (?)" in sql]
        assert decades == [1910, 1920, 1930, 1940], f"the sweep visited {decades}"

    def test_the_window_is_what_decides_the_eras_visited(self, driver) -> None:  # noqa: ANN001
        # ⚠️ The whole reason `window` exists: §6 caps pre-1950 boards at 5%, and a draw that is flat
        # across all twelve decades cannot meet a weighted quota except by accident. It did not, once.
        plan = _Plan([], batting=[])
        driver(plan, window=(1950, 1979))

        decades = [params[1] for sql, params in plan.queries if "SELECT TOP (?)" in sql]
        assert decades == [1950, 1960, 1970]

    def test_the_other_direction_of_a_drawn_game_is_still_added(self, driver) -> None:  # noqa: ANN001
        """⚠️⚠️ Keyed on game **and** offensive team, because a game is two directions and they are two
        different boards. Deduplicating on the game id alone silently halves what `also` asked for.

        ⚠️ **Counted by how many directions were processed, not by whether a query was issued.** The
        first version asserted the `also` query happened at all — which is true whatever the dedup key
        is, so it passed with the key broken. Each surviving candidate costs exactly one row query here,
        because the batting rows come back empty and the loop moves on.
        """
        drawn = candidate("BOS19750101", "BOS")
        other_way = candidate("BOS19750101", "OPP", defense="BOS")
        empty = {("batting", "BOS"), ("batting", "OPP")}
        plan = _Plan([drawn], named=[drawn, other_way], empty_for=empty)
        driver(plan, also=("BOS19750101",))

        # One batting query per direction that survived the dedup. ⚠️ Counting *all* row queries gives
        # two per direction, because the pitching rows are fetched before the emptiness check — a number
        # that happens to be twice the answer and would have made the assertion read as coincidence.
        offenses = [p[1] for sql, p in plan.queries if "P_GS" not in sql and len(p) == 2]
        assert offenses == ["BOS", "OPP"], (
            f"processed {offenses}; keyed on the game alone the other direction is dropped and `also` "
            f"returns half of what it was asked for"
        )

    def test_no_named_game_means_no_second_query(self, driver) -> None:  # noqa: ANN001
        plan = _Plan([], batting=[])
        driver(plan)

        assert all(params[0:1] != ("BOS19750101",) for _sql, params in plan.queries)
