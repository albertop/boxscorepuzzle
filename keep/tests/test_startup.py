"""What `keep` refuses to start against.

⚠️⚠️ **Both checks, before the first request.** A service that starts and then rejects everything looks
like a client fault; one that will not come up is a deployment fault, and the difference decides who
spends the afternoon looking.
"""

import sqlite3
from pathlib import Path

import pytest

from keep.auth import TOKEN_VARIABLE, MisconfiguredError
from keep.main import build
from keep.store import SchemaMismatchError, SqliteStore

_MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "001-initial.sql"
GOOD = "t" * 40


def migrated() -> SqliteStore:
    connection = sqlite3.connect(":memory:")
    connection.executescript(_MIGRATION.read_text(encoding="utf-8"))
    return SqliteStore(connection)


def test_a_migrated_database_and_a_token_start(monkeypatch: pytest.MonkeyPatch) -> None:
    # ⚠️ The control. Without it every refusal below is consistent with a service that never starts.
    monkeypatch.setenv(TOKEN_VARIABLE, GOOD)

    assert callable(build(migrated()))


def test_no_token_refuses_before_anything_else(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(TOKEN_VARIABLE, raising=False)

    with pytest.raises(MisconfiguredError):
        build(migrated())


def test_an_unmigrated_database_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TOKEN_VARIABLE, GOOD)
    empty = sqlite3.connect(":memory:")
    empty.execute("CREATE TABLE keep_schema (version INTEGER NOT NULL)")

    with pytest.raises(SchemaMismatchError):
        build(SqliteStore(empty))


def test_the_token_is_checked_before_the_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    """⚠️ **The order matters and is asserted.** With neither configured, the operator should hear about
    the token — the check whose absence is silent — rather than about a schema they may not have reached
    yet. A wrong-shaped database at least shows up in a query error; a missing token shows up as an open
    door that looks like a working deployment."""
    monkeypatch.delenv(TOKEN_VARIABLE, raising=False)
    empty = sqlite3.connect(":memory:")
    empty.execute("CREATE TABLE keep_schema (version INTEGER NOT NULL)")

    with pytest.raises(MisconfiguredError):
        build(SqliteStore(empty))
