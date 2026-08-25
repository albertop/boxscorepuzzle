"""The three routes, and what each one refuses.

**Driven through WSGI directly** — no server, no port, no network. The application is a function from an
environment to bytes, which is most of why it is plain WSGI: the parts worth testing are testable without
anything running.
"""

import io
import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from keep.app import create_app
from keep.store import SqliteStore

# ⚠️ Every migration in order, not a named one. A test naming `001-initial.sql` beside a directory
# of migrations builds a database production has moved past, and stays green while doing it.
_MIGRATIONS = sorted((Path(__file__).resolve().parents[1] / "migrations").glob("*.sql"))
assert _MIGRATIONS, "no migrations found; every test below would build an empty database"
_MIGRATION_SQL = chr(10).join(path.read_text(encoding="utf-8") for path in _MIGRATIONS)
TOKEN = "a" * 40


@pytest.fixture
def store() -> Iterator[SqliteStore]:
    connection = sqlite3.connect(":memory:")
    connection.executescript(_MIGRATION_SQL)
    yield SqliteStore(connection)
    connection.close()


@pytest.fixture
def call(store: SqliteStore) -> Any:
    application = create_app(store, TOKEN)

    def request(method: str, path: str, body: Any = None, *, token: str | None = TOKEN) -> tuple[int, Any]:
        payload = b"" if body is None else json.dumps(body).encode("utf-8")
        environ: dict[str, Any] = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "CONTENT_LENGTH": str(len(payload)),
            "wsgi.input": io.BytesIO(payload),
        }
        if token is not None:
            environ["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        seen: dict[str, Any] = {}

        def start(status: str, _headers: list[tuple[str, str]]) -> None:
            seen["status"] = status

        chunks = application(environ, start)
        return int(seen["status"].split()[0]), json.loads(b"".join(chunks))

    return request


def an_event(event_id: str = "e-1") -> dict[str, Any]:
    return {
        "event_id": event_id,
        "device_id": "d-1",
        "account_id": None,
        "puzzle_id": "p-1",
        "calendar_date": "2026-09-01",
        "played_on": "2026-08-31",
        "duration_ms": 61_000,
        "hints": 0,
        "errors": 1,
        "failed_checks": 0,
        "highest_technique": None,
        "solved": True,
        "assisted": False,
    }


class TestTheToken:
    def test_a_good_token_gets_through(self, call: Any) -> None:
        status, body = call("POST", "/events", {"events": [an_event()]})

        assert (status, body) == (200, {"stored": ["e-1"]})

    @pytest.mark.parametrize("offered", [None, "", "wrong", "a" * 39])
    def test_anything_else_is_refused(self, call: Any, offered: str | None) -> None:
        status, body = call("POST", "/events", {"events": [an_event()]}, token=offered)

        assert status == 401
        # ⚠️ **One answer for every way of being wrong.** A missing header, a malformed one and a token
        # that is nearly right all say the same thing: distinguishing them tells a caller how close it is.
        assert body == {"error": "unauthorized"}

    def test_a_refused_request_stores_nothing(self, call: Any, store: SqliteStore) -> None:
        call("POST", "/events", {"events": [an_event()]}, token="wrong")

        assert store._connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0

    def test_the_scheme_has_to_be_bearer(self, call: Any) -> None:
        # `Basic <token>` is a caller that has misread the contract, not one that may proceed.
        status, _body = call("POST", "/events", {"events": [an_event()]}, token=None)

        assert status == 401


class TestHealth:
    def test_it_answers_without_a_token(self, call: Any) -> None:
        # ⚠️ Uptime Kuma reaches it through `serve`'s proxy and holds no secret. Requiring one would mean
        # the monitor carries a credential whose only use is asking whether the service is up.
        status, body = call("GET", "/health", token=None)

        assert (status, body) == (200, {"status": "ok"})

    def test_a_dead_database_is_unavailable_rather_than_ok(self, store: SqliteStore) -> None:
        # ⚠️⚠️ **A live container with a dead database answers exactly like a healthy one** unless
        # something asks the database. This is that check, and it is why `alive()` runs a real query.
        store._connection.close()
        application = create_app(store, TOKEN)
        seen: dict[str, Any] = {}
        chunks = application(
            {"REQUEST_METHOD": "GET", "PATH_INFO": "/health"},
            lambda status, _headers: seen.__setitem__("status", status),
        )

        assert seen["status"].startswith("503")
        assert json.loads(b"".join(chunks)) == {"status": "unavailable"}

    def test_it_says_status_and_nothing_else(self, call: Any) -> None:
        # A public endpoint reporting that it cannot reach postgres at some host hands out more than it
        # needs to. The unavailable case above says the same amount.
        _status, body = call("GET", "/health", token=None)

        assert list(body) == ["status"]


class TestWhatABadBodyGets:
    def test_a_field_of_the_wrong_type_is_named(self, call: Any) -> None:
        # ⚠️ Validate at the boundary, and **name the field**. A 400 saying *invalid request* leaves the
        # fix to guesswork, and the caller is a client the operator also wrote.
        status, body = call("POST", "/events", {"events": [{**an_event(), "duration_ms": "61000"}]})

        assert status == 400
        assert "duration_ms" in body["error"]

    def test_a_boolean_is_not_a_duration(self, call: Any) -> None:
        # `bool` is an `int` in Python, so `true` would arrive as a perfectly good 1.
        status, body = call("POST", "/events", {"events": [{**an_event(), "duration_ms": True}]})

        assert status == 400
        assert "duration_ms" in body["error"]

    def test_an_unknown_field_is_refused_rather_than_ignored(self, call: Any) -> None:
        # ⚠️ An unrecognised key is either a newer client or a typo beside a real one. Ignoring it stores
        # an event that means something else while saying nothing, and C7 makes that permanent.
        status, body = call("POST", "/events", {"events": [{**an_event(), "duration_msec": 1}]})

        assert status == 400
        assert "duration_msec" in body["error"]

    def test_a_missing_account_field_is_refused(self, call: Any) -> None:
        # Present and null, never absent: a field that appears only sometimes is one consumers forget to
        # check for.
        row = an_event()
        del row["account_id"]

        status, body = call("POST", "/events", {"events": [row]})

        assert status == 400
        assert "account_id" in body["error"]

    def test_one_bad_member_refuses_the_whole_batch(self, call: Any, store: SqliteStore) -> None:
        # ⚠️⚠️ **All or nothing, and that is the safe direction.** Storing the good ones would leave the
        # client holding a queue it cannot drain — it has no way to know which member the complaint was
        # about — and would make a client bug look like intermittent loss.
        status, _body = call("POST", "/events", {"events": [an_event("e-1"), {"event_id": "e-2"}]})

        assert status == 400
        assert store._connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0

    def test_a_body_that_is_not_json_is_a_controlled_refusal(self) -> None:
        application = create_app(SqliteStore(sqlite3.connect(":memory:")), TOKEN)
        seen: dict[str, Any] = {}
        chunks = application(
            {
                "REQUEST_METHOD": "POST",
                "PATH_INFO": "/events",
                "CONTENT_LENGTH": "3",
                "wsgi.input": io.BytesIO(b"{,]"),
                "HTTP_AUTHORIZATION": f"Bearer {TOKEN}",
            },
            lambda status, _headers: seen.__setitem__("status", status),
        )

        assert seen["status"].startswith("400")
        assert "unreadable body" in json.loads(b"".join(chunks))["error"]


class TestTheRoutes:
    def test_an_unknown_path_is_not_found(self, call: Any) -> None:
        assert call("POST", "/whatever", {})[0] == 404

    def test_a_get_to_events_is_not_found(self, call: Any) -> None:
        # There is no read side. `keep` holds people and nothing reads them yet (`keep-api.md`).
        assert call("GET", "/events")[0] == 404

    def test_shares_take_the_same_contract(self, call: Any) -> None:
        """⚠️ The fourth route, and it exists because the share is its own event.

        `store.py`'s `Share` carries the argument: the share happens after the event is uploaded, and
        the insert that makes a retry free ignores a second arrival of the same id.
        """
        share = {
            "share_id": "s-1",
            "device_id": "d-1",
            "puzzle_id": "p-1",
            "event_id": "e-1",
            "channel": "native",
            "shared_on": "2026-08-31",
        }

        assert call("POST", "/shares", {"shares": [share]}) == (200, {"stored": ["s-1"]})

    def test_a_share_still_needs_the_token(self, call: Any) -> None:
        assert call("POST", "/shares", {"shares": []}, token=None)[0] == 401

    def test_a_get_to_shares_is_not_found(self, call: Any) -> None:
        assert call("GET", "/shares")[0] == 404

    def test_a_bad_channel_names_the_field(self, call: Any) -> None:
        """The refusal travels to the caller, because the caller is a client the operator also wrote."""
        share = {
            "share_id": "s-1", "device_id": "d-1", "puzzle_id": "p-1",
            "event_id": None, "channel": "carrier pigeon", "shared_on": None,
        }  # fmt: skip
        status, body = call("POST", "/shares", {"shares": [share]})

        assert status == 400
        assert "channel" in body["error"]

    def test_errors_take_the_same_contract(self, call: Any) -> None:
        report = {
            "error_id": "x-1",
            "device_id": "d-1",
            "message": "boom",
            "stack": "at draw()",
            "page": "/p/abc",
            "viewport": "375x812",
            "user_agent": "a browser",
        }

        assert call("POST", "/errors", {"errors": [report]}) == (200, {"stored": ["x-1"]})
