"""Retention: shares after 365 days, client errors after 180. **`events` is never touched.**

⚠️ **The third table is the assertion, not an omission.** §26 sells comparison and percentiles, and
those need history — a sweep that quietly took `events` too would look identical on the day it ran and
cost the paid feature. Every case below checks the event count is unchanged.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from keep.purge import RETENTION_DAYS, purge
from keep.store import Share

_MIGRATIONS = sorted((Path(__file__).resolve().parents[1] / "migrations").glob("*.sql"))
assert _MIGRATIONS, "no migrations found; every test below would run against an empty database"

NOW = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)


def _stamp(days_ago: int) -> str:
    return (NOW - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")


@pytest.fixture
def db() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    for path in _MIGRATIONS:
        connection.executescript(path.read_text(encoding="utf-8"))
    return connection


def _rows(db: sqlite3.Connection, table: str) -> int:
    return int(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0])  # noqa: S608


def _seed(db: sqlite3.Connection, table: str, ident: str, days_ago: int) -> None:
    columns = {
        "events": (
            "event_id",
            "device_id",
            "puzzle_id",
            "duration_ms",
            "hints",
            "errors",
            "failed_checks",
            "solved",
            "assisted",
            "received_at",
        ),
        "shares": ("share_id", "device_id", "puzzle_id", "channel", "received_at"),
        "client_errors": ("error_id", "device_id", "message", "stack", "page", "viewport", "user_agent", "received_at"),
    }[table]
    # ⚠️ `events` carries integers and booleans where the other two carry text, so the filler cannot be
    # one value: a table's own shape decides what a plausible row looks like.
    filler = {
        # puzzle_id, duration_ms, hints, errors, failed_checks, solved, assisted
        "events": ["p", 1, 0, 0, 0, 1, 0],
        # puzzle_id, channel
        "shares": ["x"] * 2,
        # message, stack, page, viewport, user_agent
        "client_errors": ["x"] * 5,
    }[table]
    values = [ident, "d", *filler, _stamp(days_ago)]
    assert len(values) == len(columns), f"{table}: {len(values)} values for {len(columns)} columns"
    db.execute(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})", values)  # noqa: S608


def test_the_two_windows_are_the_operators_decision() -> None:
    """⚠️ Spelled once, here, so a future reader sees a decision rather than a number in a query."""
    assert RETENTION_DAYS == {"events": 730, "shares": 365, "client_errors": 180}


def test_a_row_past_its_window_goes_and_one_inside_it_stays(db: sqlite3.Connection) -> None:
    # ⚠️ **One day either side of each boundary**, because a window is a threshold and a test that
    # samples far from it passes for any window at all -- including the wrong one.
    _seed(db, "shares", "old", 366)
    _seed(db, "shares", "new", 364)
    _seed(db, "client_errors", "old", 181)
    _seed(db, "client_errors", "new", 179)

    gone = purge(db, now=NOW, placeholder="?")

    assert gone == {"events": 0, "shares": 1, "client_errors": 1}
    assert [r[0] for r in db.execute("SELECT share_id FROM shares")] == ["new"]
    assert [r[0] for r in db.execute("SELECT error_id FROM client_errors")] == ["new"]


def test_an_event_survives_two_years_and_goes_after(db: sqlite3.Connection) -> None:
    """⚠️⚠️ **`events` was deliberately uncapped until 2026-08-26, and the reason it was still stands.**

    §26 sells comparison and percentiles, and **a deleted event is a game gone from every percentile that
    would have counted it**. The operator was told that before deciding and set two years anyway, which
    is a choice about how far back a comparison reaches.

    ⚠️ **One day either side of the boundary**, because a window is a threshold and a test that samples
    far from it passes for any window at all -- including the wrong one. That is this file's own recorded
    finding: a test that samples cannot see what lives between its samples.
    """
    _seed(db, "events", "old", 731)
    _seed(db, "events", "new", 729)

    gone = purge(db, now=NOW, placeholder="?")

    assert gone["events"] == 1
    assert [r[0] for r in db.execute("SELECT event_id FROM events")] == ["new"]


def test_an_empty_database_is_not_an_error(db: sqlite3.Connection) -> None:
    # It runs nightly and most nights there is nothing to delete.
    assert purge(db, now=NOW, placeholder="?") == {"events": 0, "shares": 0, "client_errors": 0}


def test_a_row_arriving_today_survives_every_window(db: sqlite3.Connection) -> None:
    # ⚠️ The migration gives existing rows CURRENT_TIMESTAMP, so the first run after deploying must not
    # delete the history it just stamped. This is that case.
    _seed(db, "shares", "today", 0)
    _seed(db, "client_errors", "today", 0)

    assert purge(db, now=NOW, placeholder="?") == {"events": 0, "shares": 0, "client_errors": 0}


def test_received_at_is_utc_from_the_application(db: sqlite3.Connection) -> None:
    """⚠️⚠️ **`DEFAULT CURRENT_TIMESTAMP` meant two different things, and production got the wrong one.**

    In Postgres it is a `timestamptz`; casting it into a TEXT column renders it **in the session's
    timezone**, and the first rows on the live database read `2026-08-24 23:28:02.569817-04`. In SQLite
    the same keyword yields `2026-08-25 03:28:02`, UTC, no offset. **One migration, one column, two
    formats** -- and the purge compares that column as a string against a cutoff computed in UTC, so it
    was four hours out and correct only by accident of the year sorting first.

    The value comes from `_now()` now. This asserts the shape, because the shape is the contract: the
    comparison in `purge()` is lexicographic, and two spellings of the same instant do not compare.
    """
    from keep.store import SqliteStore  # noqa: PLC0415

    store = SqliteStore(db)
    store.store_shares(
        [Share(share_id="s", device_id="d", puzzle_id="p", event_id=None, channel="native", shared_on=None)]
    )

    stamped = db.execute("SELECT received_at FROM shares").fetchone()[0]

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stamped), (
        f"received_at is {stamped!r}; the purge compares this as a string and needs one spelling"
    )
    # ⚠️ And that it is actually UTC rather than merely shaped like it. A local clock formatted with a
    # `Z` is the same defect with better manners.
    assert (
        abs(
            (
                datetime.strptime(stamped, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC) - datetime.now(tz=UTC)
            ).total_seconds()
        )
        < 120
    ), f"received_at is {stamped!r}, which is not the current UTC instant"


def test_no_database_default_can_put_a_local_time_back(db: sqlite3.Connection) -> None:
    """⚠️ The other half: an insert that forgets the column must not silently get one from the database.

    The empty-string default exists only because SQLite refuses a NOT NULL column without one. If it ever
    starts producing values again, the two-format defect is back and nothing else would notice.
    """
    db.execute("INSERT INTO shares (share_id, device_id, puzzle_id, channel) VALUES ('x', 'd', 'p', 'native')")

    assert db.execute("SELECT received_at FROM shares WHERE share_id = 'x'").fetchone()[0] == "", (
        "the database supplied a received_at; that is where the timezone came from last time"
    )
