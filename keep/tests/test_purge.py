"""Retention: shares after 365 days, client errors after 180. **`events` is never touched.**

⚠️ **The third table is the assertion, not an omission.** §26 sells comparison and percentiles, and
those need history — a sweep that quietly took `events` too would look identical on the day it ran and
cost the paid feature. Every case below checks the event count is unchanged.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from keep.purge import RETENTION_DAYS, purge

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
        "shares": ("share_id", "device_id", "puzzle_id", "channel", "received_at"),
        "client_errors": ("error_id", "device_id", "message", "stack", "page", "viewport", "user_agent", "received_at"),
    }[table]
    values = [ident] + ["x"] * (len(columns) - 2) + [_stamp(days_ago)]
    db.execute(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})", values)  # noqa: S608


def test_the_two_windows_are_the_operators_decision() -> None:
    """⚠️ Spelled once, here, so a future reader sees a decision rather than a number in a query."""
    assert RETENTION_DAYS == {"shares": 365, "client_errors": 180}
    assert "events" not in RETENTION_DAYS


def test_a_row_past_its_window_goes_and_one_inside_it_stays(db: sqlite3.Connection) -> None:
    # ⚠️ **One day either side of each boundary**, because a window is a threshold and a test that
    # samples far from it passes for any window at all -- including the wrong one.
    _seed(db, "shares", "old", 366)
    _seed(db, "shares", "new", 364)
    _seed(db, "client_errors", "old", 181)
    _seed(db, "client_errors", "new", 179)

    gone = purge(db, now=NOW, placeholder="?")

    assert gone == {"shares": 1, "client_errors": 1}
    assert [r[0] for r in db.execute("SELECT share_id FROM shares")] == ["new"]
    assert [r[0] for r in db.execute("SELECT error_id FROM client_errors")] == ["new"]


def test_events_are_never_touched(db: sqlite3.Connection) -> None:
    """⚠️⚠️ **The whole reason `events` is absent from `RETENTION_DAYS`**, asserted rather than assumed.

    Seen red by adding `"events": 1` to the dict: the row disappears and this is what says so.
    """
    db.execute(
        "INSERT INTO events (event_id, device_id, puzzle_id, calendar_date, played_on, duration_ms, "
        "hints, errors, failed_checks, solved, assisted) "
        "VALUES ('e', 'd', 'p', '2020-01-01', '2020-01-01', 1, 0, 0, 0, 1, 0)"
    )

    purge(db, now=NOW, placeholder="?")

    assert _rows(db, "events") == 1, "the retention sweep took an event; percentiles need history"


def test_an_empty_database_is_not_an_error(db: sqlite3.Connection) -> None:
    # It runs nightly and most nights there is nothing to delete.
    assert purge(db, now=NOW, placeholder="?") == {"shares": 0, "client_errors": 0}


def test_a_row_arriving_today_survives_every_window(db: sqlite3.Connection) -> None:
    # ⚠️ The migration gives existing rows CURRENT_TIMESTAMP, so the first run after deploying must not
    # delete the history it just stamped. This is that case.
    _seed(db, "shares", "today", 0)
    _seed(db, "client_errors", "today", 0)

    assert purge(db, now=NOW, placeholder="?") == {"shares": 0, "client_errors": 0}
