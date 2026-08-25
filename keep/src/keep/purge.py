"""Delete rows nobody will read again. **`events` is never touched** -- percentiles need history.

Run inside the running `keep` container, so `KEEP_DATABASE_URL` is already there and no password goes
anywhere new:

    docker exec bxcpze-keep python -m keep.purge
"""

import os
from datetime import UTC, datetime, timedelta
from typing import Any

RETENTION_DAYS = {"shares": 365, "client_errors": 180}
"""How long each table keeps a row. **Operator's decision, 2026-08-24.**

⚠️ `events` is deliberately absent. §26 sells comparison and percentiles, and those need history.
"""


def purge(connection: Any, now: datetime | None = None, placeholder: str = "%s") -> dict[str, int]:  # noqa: ANN401
    """Delete aged rows, returning what went from each table.

    ⚠️ The cutoff is worked out here and passed as a parameter, rather than written as SQL date
    arithmetic. Both engines then run the same query, and a test can hand it a `now` instead of waiting
    a year.

    ⚠️ `placeholder` because the two engines disagree: psycopg wants `%s` and sqlite wants `?`. It is not
    a `Store` method -- that class's own docstring refuses query helpers, so the retention sweep does not
    end up on the same connection as a player uploading a result (`data-layer.md` §8).
    """
    moment = now if now is not None else datetime.now(tz=UTC)
    gone = {}
    cursor = connection.cursor()
    for table, days in RETENTION_DAYS.items():
        # ⚠️ The table name is a literal from the dict above, never a caller's string -- an identifier
        # cannot be bound, so anything reaching this from outside would be an injection.
        cutoff = (moment - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(f"DELETE FROM {table} WHERE received_at < {placeholder}", (cutoff,))  # noqa: S608
        gone[table] = cursor.rowcount
    connection.commit()
    return gone


def main() -> None:  # pragma: no cover - the process entry point; `purge` is what is tested
    dsn = os.environ.get("KEEP_DATABASE_URL", "")
    if not dsn:
        message = "KEEP_DATABASE_URL is not set. keep needs a database and does not invent one."
        raise SystemExit(message)

    import psycopg  # noqa: PLC0415 - imported here so the module loads without a driver present

    with psycopg.connect(dsn, autocommit=False) as connection:
        gone = purge(connection)
    for table, rows in gone.items():
        # ⚠️ stdout is the whole record of this run. ofelia captures it into the scheduler's log, and a
        # sweep that deleted nothing and one that never ran look identical without a line saying so.
        print(f"purged {rows} from {table}")  # noqa: T201


if __name__ == "__main__":  # pragma: no cover
    main()
