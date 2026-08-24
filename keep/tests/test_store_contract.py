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

from keep.store import (
    SCHEMA_VERSION,
    ErrorReport,
    Event,
    PostgresStore,
    SchemaMismatchError,
    Share,
    SqliteStore,
    Store,
)

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


def a_share(share_id: str = "s-1", *, event_id: str | None = "e-1") -> Share:
    return Share(
        share_id=share_id,
        device_id="d-1",
        puzzle_id="p-1",
        event_id=event_id,
        channel="native",
        shared_on="2026-08-31",
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
        # ⚠️⚠️ **Derived from the database, never a list kept by hand.** This was
        # `DROP TABLE IF EXISTS events, client_errors, keep_schema` -- three names spelled here and
        # created in `001-initial.sql`, two places encoding one fact. Adding `shares` to the migration
        # and not to that line left the table behind between tests, and every Postgres case after the
        # first died on `DuplicateTable`. **The migration is the only place a table is named**, and a
        # fifth one next year is dropped by existing rather than by somebody remembering this line.
        cursor.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()",
        )
        existing = [row[0] for row in cursor.fetchall()]
        if existing:
            # Quoted and CASCADE: a name needing quotes would otherwise fail here, and a future foreign
            # key between two of these would make the drop order matter.
            names = ", ".join(f'"{table}"' for table in existing)
            cursor.execute(f"DROP TABLE IF EXISTS {names} CASCADE")
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

    def test_shares_deduplicate_the_same_way(self, store: Store) -> None:
        """⚠️ The retry contract holds for shares too, and it is the reason they are their own event.

        A share arrives after the game was uploaded, so it could never be recorded by re-sending the
        event -- `ON CONFLICT DO NOTHING` ignores that. What makes the share's own retry free is this.
        """
        store.store_shares([a_share()])
        store.store_shares([a_share()])

        assert _count(store, "shares") == 1

    def test_a_share_reports_its_id_rather_than_a_count(self, store: Store) -> None:
        assert store.store_shares([a_share()]) == ["s-1"]

    def test_a_share_whose_game_has_not_uploaded_yet_is_stored(self, store: Store) -> None:
        """⚠️⚠️ **`event_id` carries no foreign key and this is the test that says why.**

        Events and shares travel in separate batches through one queue, so the share can land first --
        or the event can be lost entirely. Refusing the share would discard the only measurement the
        product's growth mechanism has, to protect a reference nothing reads.
        """
        assert store.store_shares([a_share(event_id=None)]) == ["s-1"]
        assert _count(store, "shares") == 1

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


class TestOneBadRowIsNotAnOutage:
    """⚠️⚠️ v39-P2-01. A failed statement aborts the Postgres transaction, and Postgres then refuses
    **every later statement on that connection** until somebody rolls back. `keep` reuses one
    connection, so a single rejected row took down every upload, every error report and the health
    check until the process was restarted.

    ⚠️ **These run against Postgres and only Postgres, on purpose.** The aborted-transaction state is
    the behaviour under test and SQLite does not have it — running them on both would produce a green
    result on the engine that cannot exhibit the defect, which is the whole reason `keep-api.md` refuses
    to call the cross-engine suite a compatibility guarantee.
    """

    def test_a_rejected_insert_leaves_the_connection_able_to_work(self, postgres_store: Store) -> None:
        # Past what an INTEGER column holds: the boundary reader refuses this now, but the store must
        # survive it whatever the reason a statement fails — a full disk and a constraint do the same.
        too_large = replace(an_event("e-big"), duration_ms=2**31)

        with pytest.raises(Exception, match=r"(?i)range|overflow|integer"):
            postgres_store.store_events([too_large])

        assert postgres_store.store_events([an_event("e-1")]) == ["e-1"], (
            "one rejected row left the connection aborted, so nothing could be stored afterwards"
        )

    def test_a_rejected_insert_leaves_the_health_check_answering(self, postgres_store: Store) -> None:
        # ⚠️ The endpoint that reports the outage must not be the thing extending it past its cause.
        with pytest.raises(Exception, match=r"(?i)range|overflow|integer"):
            postgres_store.store_events([replace(an_event("e-big"), duration_ms=2**31)])

        assert postgres_store.alive() is True, "a rejected row made the health check report an outage"

    def test_the_failure_is_raised_rather_than_swallowed(self, postgres_store: Store) -> None:
        # ⚠️ Rolling back and reporting success would make a lost write look like a stored one, and the
        # client would drop it from its queue on the strength of that. The rollback repairs the
        # connection; what happened to the row is still an error.
        with pytest.raises(Exception):  # noqa: B017 - the driver's own class, whatever it is
            postgres_store.store_events([replace(an_event("e-big"), duration_ms=2**31)])

        assert _count(postgres_store, "events") == 0, "a row that could not be stored was reported as stored"


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
