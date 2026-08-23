"""Where events go, behind an interface that hides which database is underneath.

**`docs/keep-api.md` is the contract; `docs/data-layer.md` is why the service exists.**

⚠️⚠️ **Two engines behind one interface is this project's most-met defect wearing a coat**, and the
danger is not that they disagree — it is that **the tests run against the one that is not in
production**, so the disagreement is invisible until a player meets it.

**So the promise is narrowed rather than dressed up: Postgres is production, SQLite is a development
convenience and is not supported.** A behavioural difference is a bug in the *tests*, not in `keep`. The
contract suite runs against both as a smoke alarm for the suite; it is not a compatibility guarantee, and
calling it one would be the more generous claim and the less honest one.

⚠️ **The deduplication is tested against Postgres specifically**, because it is the one piece whose
correctness rests on an upsert's exact semantics — and `ON CONFLICT DO NOTHING` is where the two engines
are most likely to differ in a way a green SQLite suite would not show.
"""

import sqlite3
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = 1
"""What this code expects the database to be.

⚠️⚠️ **Migrations are manual and startup refuses a mismatch** (`data-layer.md` §7), and neither half
works alone: manual without the check gives silent drift between what the code expects and what exists;
the check without manual migrations gives a deploy the power to alter data at three in the morning, which
is the one failure on that list a rollback does not undo."""


@dataclass(frozen=True, slots=True)
class Event:
    """One finished game, as `game.record()` produces it.

    ⚠️ **`event_id` is made by the client when the event is created, never when it is sent.** The client
    cannot tell a lost response from a request that never arrived, so it retries — and an id generated
    per *attempt* is new every time and deduplicates nothing while looking like it does.

    ⚠️ **`account_id` is present and null.** The event is claimable: registering attaches an account to a
    device's history. A subject that is one fixed column cannot become claimable later without rewriting
    the history C7 exists to keep.
    """

    event_id: str
    device_id: str
    account_id: str | None
    puzzle_id: str
    calendar_date: str | None
    played_on: str | None
    duration_ms: int
    hints: int
    errors: int
    failed_checks: int
    highest_technique: str | None
    solved: bool
    assisted: bool


@dataclass(frozen=True, slots=True)
class ErrorReport:
    """An uncaught client error. ⚠️ No IP and no geolocation (§35): a user agent and a viewport are what
    reproduce a rendering fault, and anything past that is collected because it was easy."""

    error_id: str
    device_id: str
    message: str
    stack: str
    page: str
    viewport: str
    user_agent: str


class SchemaMismatchError(RuntimeError):
    """The database is not the shape this code expects. **Refused at startup, never worked around.**"""


class Store(ABC):
    """What `keep` needs from a database, and nothing else.

    ⚠️ Deliberately small. Every method here is something a route calls; a store that grew query helpers
    for reports would put the metrics path and the operational path on one connection, which
    `data-layer.md` §8 forbids for a reason — a thirty-day retention query must not be able to slow down
    a player uploading a result.
    """

    @abstractmethod
    def schema_version(self) -> int | None:
        """What the database says it is, or `None` when it has never been migrated."""

    @abstractmethod
    def store_events(self, events: Sequence[Event]) -> list[str]:
        """Persist events, ignoring any already held. **Returns the ids now stored, not a count.**

        ⚠️ A count says how many landed and not *which*, so a partial success would force the client to
        re-send everything — reintroducing the duplication the id exists to prevent.

        ⚠️ **An id already held counts as stored.** The client asked *is this recorded*; it is. Reporting
        it as a conflict would make the honest retry look like a failure.
        """

    @abstractmethod
    def store_errors(self, reports: Sequence[ErrorReport]) -> list[str]:
        """Same contract as `store_events`, for client error reports."""

    @abstractmethod
    def alive(self) -> bool:
        """⚠️ **A real query against a known table**, not `SELECT 1`. A live container with a dead
        database answers exactly like a healthy one, and `SELECT 1` succeeds against an empty database,
        the wrong database, and one whose migrations never ran.

        **What is tested is that the query does not error**, never the row count: a table legitimately
        empty on a fresh deployment is not an outage, and a check that says it is gets muted within a
        week."""

    def require_schema(self) -> None:
        """Refuse to serve against a database this code does not expect.

        ⚠️ **`None` is refused too, and that is the fail-closed half.** A database with no version row
        has never been migrated; treating that as *probably fine* is the absence of a check reading as
        the presence of a passing one.
        """
        found = self.schema_version()
        if found != SCHEMA_VERSION:
            message = (
                f"keep expects schema {SCHEMA_VERSION} and the database says {found}. "
                f"Migrations are manual: run them, then start the service. Nothing is migrated on boot."
            )
            raise SchemaMismatchError(message)


_EVENT_COLUMNS = (
    "event_id", "device_id", "account_id", "puzzle_id", "calendar_date", "played_on",
    "duration_ms", "hints", "errors", "failed_checks", "highest_technique", "solved", "assisted",
)  # fmt: skip

_ERROR_COLUMNS = ("error_id", "device_id", "message", "stack", "page", "viewport", "user_agent")


def _row(item: Event | ErrorReport, columns: tuple[str, ...]) -> tuple[Any, ...]:
    return tuple(getattr(item, column) for column in columns)


class SqliteStore(Store):
    """SQLite, for tests and local development. **Not production** — see the module docstring."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def schema_version(self) -> int | None:
        rows = self._connection.execute("SELECT version FROM keep_schema").fetchall()
        return int(rows[0][0]) if rows else None

    def store_events(self, events: Sequence[Event]) -> list[str]:
        return self._insert("events", _EVENT_COLUMNS, events)

    def store_errors(self, reports: Sequence[ErrorReport]) -> list[str]:
        return self._insert("client_errors", _ERROR_COLUMNS, reports)

    def _insert(self, table: str, columns: tuple[str, ...], items: Iterable[Event | ErrorReport]) -> list[str]:
        rows = [_row(item, columns) for item in items]
        if not rows:
            return []
        placeholders = ", ".join("?" * len(columns))
        # ⚠️ `OR IGNORE` on the primary key: a retry of something already held is a no-op rather than an
        # error. The client asked whether it is recorded, and it is.
        self._connection.executemany(
            f"INSERT OR IGNORE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",  # noqa: S608
            rows,
        )
        self._connection.commit()
        return [str(row[0]) for row in rows]

    def alive(self) -> bool:
        self._connection.execute("SELECT 1 FROM keep_schema LIMIT 1").fetchall()
        return True


class PostgresStore(Store):
    """Postgres, which is production.

    ⚠️ Takes a connection rather than making one: the pool belongs to the caller, and `data-layer.md` §8
    wants the reporting side on its own pool with its own `statement_timeout` so a heavy report cannot
    queue behind a player uploading a result.
    """

    def __init__(self, connection: Any) -> None:  # noqa: ANN401 - psycopg publishes no stubs
        self._connection = connection

    def schema_version(self) -> int | None:
        with self._connection.cursor() as cursor:
            cursor.execute("SELECT version FROM keep_schema")
            rows = cursor.fetchall()
        return int(rows[0][0]) if rows else None

    def store_events(self, events: Sequence[Event]) -> list[str]:
        return self._insert("events", _EVENT_COLUMNS, events)

    def store_errors(self, reports: Sequence[ErrorReport]) -> list[str]:
        return self._insert("client_errors", _ERROR_COLUMNS, reports)

    def _insert(self, table: str, columns: tuple[str, ...], items: Iterable[Event | ErrorReport]) -> list[str]:
        rows = [_row(item, columns) for item in items]
        if not rows:
            return []
        placeholders = ", ".join(["%s"] * len(columns))
        with self._connection.cursor() as cursor:
            # ⚠️⚠️ **`ON CONFLICT DO NOTHING`, and this is the line the whole retry story rests on.**
            # It is also where SQLite and Postgres are most likely to differ in a way a green SQLite
            # suite would not reveal, which is why the contract suite is not a compatibility guarantee.
            cursor.executemany(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "  # noqa: S608
                f"ON CONFLICT ({columns[0]}) DO NOTHING",
                rows,
            )
        self._connection.commit()
        return [str(row[0]) for row in rows]

    def alive(self) -> bool:
        with self._connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM keep_schema LIMIT 1")
            cursor.fetchall()
        return True
