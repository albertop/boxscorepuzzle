"""One contract, run against both engines.

⚠️⚠️ **Not two suites.** Two implementations of one contract are two places that should say the same
thing, and the danger is not that they disagree — it is that **the tests run against the one that is not
in production**, so the disagreement is invisible until a player meets it. A suite green on SQLite says
nothing about Postgres and says it convincingly.

⚠️ **And what this buys is narrower than it looks, which is why SQLite is a development convenience and
not a supported engine** (`docs/keep-api.md`). Running one suite against both is a **smoke alarm for the
suite**: a failure means a test assumed something one engine does not promise. It is not a compatibility
guarantee, and calling it one would be the more generous claim and the less honest one.

⚠️⚠️ **The Postgres arm fails when there is no server — it does not skip.** A skip is honest about
itself and was still wrong here: without it `PostgresStore` is 80% covered and the suite is 92%, under
its own 95% floor, **so the floor only held on a machine that happened to have Postgres running.** The
message says how to start one.
"""

import os
import sqlite3
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from keep.store import SCHEMA_VERSION, ErrorReport, Event, PostgresStore, SchemaMismatchError, SqliteStore, Store

_MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "001-initial.sql"
POSTGRES_VARIABLE = "KEEP_TEST_POSTGRES"


def an_event(event_id: str = "e-1", *, device: str = "d-1") -> Event:
    return Event(
        event_id=event_id,
        device_id=device,
        account_id=None,
        puzzle_id="p-1",
        calendar_date="2026-09-01",
        played_on="2026-08-31",
        duration_ms=61_000,
        hints=0,
        errors=1,
        failed_checks=0,
        highest_technique=None,
        solved=True,
        assisted=False,
    )


def a_report(error_id: str = "x-1") -> ErrorReport:
    return ErrorReport(
        error_id=error_id,
        device_id="d-1",
        message="boom",
        stack="at draw()",
        page="/p/abc",
        viewport="375x812",
        user_agent="a browser",
    )


@pytest.fixture
def sqlite_store() -> Iterator[Store]:
    connection = sqlite3.connect(":memory:")
    connection.executescript(_MIGRATION.read_text(encoding="utf-8"))
    yield SqliteStore(connection)
    connection.close()


@pytest.fixture
def postgres_store() -> Iterator[Store]:
    """A throwaway schema on a real Postgres, or a skip.

    ⚠️⚠️ **Unset is a failure, not a skip.** It was a skip, which was honest about itself and still
    wrong: it took the suite from 100% to 92%, under its own floor, **so the floor only held on a
    machine that happened to have a database running.** A guarantee that depends on somebody's local
    Docker is not one.
    """
    dsn = os.environ.get(POSTGRES_VARIABLE)
    if not dsn:
        # ⚠️⚠️ **A failure, not a skip, and that changed on 2026-08-22.** It skipped, and the skip was
        # honest about itself — but it took `PostgresStore` from 100% to **80%** and the whole suite from
        # 100% to 92%, under the 95% floor. **So the floor only held when somebody happened to have a
        # database running**, which is a guarantee that is true on the machine that wrote it and nowhere
        # else.
        #
        # ⚠️ **The tempting repair was a fake connection**, which would have covered `PostgresStore` to
        # 100% while proving nothing about Postgres — coverage theatre, and the number would then lie in
        # exactly the place it is relied on. Postgres is production; its store is tested against Postgres.
        pytest.fail(
            f"{POSTGRES_VARIABLE} is not set and this suite does not run without it: Postgres is "
            f"production, and skipping it drops keep's coverage under its own floor while looking "
            f"green. Start one with:  docker run -d --name keep-test-pg -e POSTGRES_PASSWORD=keep "
            f"-e POSTGRES_DB=keep -p 55432:5432 postgres:17-alpine  --  then set "
            f"{POSTGRES_VARIABLE}=postgresql://postgres:keep@localhost:55432/keep"
        )
    psycopg = pytest.importorskip("psycopg")
    connection = psycopg.connect(dsn, autocommit=False)
    with connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS events, client_errors, keep_schema")
        cursor.execute(_MIGRATION.read_text(encoding="utf-8"))
    connection.commit()
    yield PostgresStore(connection)
    connection.close()


@pytest.fixture(params=["sqlite", "postgres"])
def store(request: pytest.FixtureRequest) -> Any:
    """Both engines, one body of tests."""
    return request.getfixturevalue(f"{request.param}_store")


class TestTheRetryContract:
    """⚠️⚠️ The reason the schema has a client-generated id at all. The client cannot tell a lost
    response from a request that never arrived, so it retries — and with events feeding streaks and
    percentiles, a duplicate is a game that never happened."""

    def test_an_event_is_stored_once(self, store: Store) -> None:
        assert store.store_events([an_event()]) == ["e-1"]

    def test_the_same_event_twice_is_stored_once(self, store: Store) -> None:
        store.store_events([an_event()])
        store.store_events([an_event()])

        assert _count(store, "events") == 1

    def test_a_retry_reports_the_id_as_stored_rather_than_as_a_conflict(self, store: Store) -> None:
        # ⚠️ The client asked *is this recorded*, and it is. Reporting a conflict would make the honest
        # retry look like a failure and leave the queue undrainable.
        store.store_events([an_event()])

        assert store.store_events([an_event()]) == ["e-1"]

    def test_a_retry_never_overwrites_what_was_first_recorded(self, store: Store) -> None:
        """⚠️⚠️ **The property counting rows cannot see**, and a mutation found it missing.

        `INSERT OR REPLACE` keeps exactly one row too, so every count-based test above passes with it —
        and it **overwrites the original with the retry's values**. That matters: a queued event whose
        clock kept running, or a client that rebuilt a record slightly differently, would rewrite what
        happened. **C7 stores what happened, and the first telling is the one that did.**

        Postgres says `ON CONFLICT DO NOTHING` and SQLite says `OR IGNORE`; this is the test that pins
        both to the same meaning rather than to the same row count.
        """
        store.store_events([an_event("e-1")])
        # ⚠️ `slots=True` means no `__dict__`, so `replace` rather than `vars`.
        louder = replace(an_event("e-1"), duration_ms=999_999, hints=3)

        store.store_events([louder])

        assert _first(store, "e-1") == (61_000, 0), "the retry overwrote the record it was retrying"

    def test_a_batch_half_of_which_is_already_held_stores_the_rest(self, store: Store) -> None:
        store.store_events([an_event("e-1")])

        assert store.store_events([an_event("e-1"), an_event("e-2")]) == ["e-1", "e-2"]
        assert _count(store, "events") == 2

    def test_error_reports_deduplicate_the_same_way(self, store: Store) -> None:
        store.store_errors([a_report()])
        store.store_errors([a_report()])

        assert _count(store, "client_errors") == 1

    def test_an_empty_batch_is_not_an_error(self, store: Store) -> None:
        # A queue that drains to nothing sends nothing. Refusing it would make the ordinary case an error.
        assert store.store_events([]) == []


class TestWhatItRefusesToStartAgainst:
    def test_the_expected_schema_is_accepted(self, store: Store) -> None:
        assert store.schema_version() == SCHEMA_VERSION
        store.require_schema()

    def test_a_database_that_has_never_been_migrated_is_refused(self) -> None:
        # ⚠️⚠️ **The fail-closed half.** A database with no version row has never been migrated, and
        # treating that as *probably fine* is the absence of a check reading as a passing one.
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE keep_schema (version INTEGER NOT NULL)")

        with pytest.raises(SchemaMismatchError, match="says None"):
            SqliteStore(connection).require_schema()

    def test_a_different_schema_version_is_refused(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE keep_schema (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO keep_schema (version) VALUES (99)")

        with pytest.raises(SchemaMismatchError, match="expects schema 1"):
            SqliteStore(connection).require_schema()

    def test_the_refusal_says_migrations_are_manual(self) -> None:
        # The operator meeting this months later needs to know that starting again will not fix it.
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE keep_schema (version INTEGER NOT NULL)")

        with pytest.raises(SchemaMismatchError, match="Migrations are manual"):
            SqliteStore(connection).require_schema()


class TestTheHealthQuery:
    def test_a_migrated_database_is_alive(self, store: Store) -> None:
        assert store.alive() is True

    def test_a_database_missing_its_tables_is_not(self) -> None:
        # ⚠️ **A real query against a known table, not `SELECT 1`.** `SELECT 1` succeeds against an empty
        # database, the wrong database, and one whose migrations never ran — so it would answer *healthy*
        # in exactly the situations the check exists to catch.
        connection = sqlite3.connect(":memory:")

        with pytest.raises(sqlite3.OperationalError):
            SqliteStore(connection).alive()


def _first(store: Store, event_id: str) -> tuple[int, int]:
    """The stored duration and hints for one event, past the interface for the same reason `_count` is."""
    reading = "SELECT duration_ms, hints FROM events WHERE event_id = "
    if isinstance(store, SqliteStore):
        row = store._connection.execute(reading + "?", (event_id,)).fetchone()
    else:
        with store._connection.cursor() as cursor:  # type: ignore[attr-defined]
            cursor.execute(reading + "%s", (event_id,))
            row = cursor.fetchone()
    return (int(row[0]), int(row[1]))


def _count(store: Store, table: str) -> int:
    """How many rows the store holds, reaching past the interface on purpose.

    ⚠️ The interface has no `count` and should not: nothing `keep` serves needs one, and a method
    existing only for tests is a method production carries for nobody. This is a test helper that knows
    which engine it is looking at, which is the honest place for that knowledge.
    """
    # ⚠️ S608 is answered rather than waived: `table` comes from this file's own two literals, and a
    # parameterised table name is not something any database supports.
    counting = f"SELECT COUNT(*) FROM {table}"  # noqa: S608
    if isinstance(store, SqliteStore):
        return int(store._connection.execute(counting).fetchone()[0])
    with store._connection.cursor() as cursor:  # type: ignore[attr-defined]
        cursor.execute(counting)
        return int(cursor.fetchone()[0])
