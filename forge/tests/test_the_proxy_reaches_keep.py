"""F1.3b — `serve` proxies `/api/events` and `/api/errors` to `keep`, adding the token at the edge.

⚠️⚠️ **The browser must never reach `keep`.** Its port is not published and the shared token must not
travel to a browser (`docs/data-layer.md` §4), so the client posts to `serve` and **the edge adds the
token**, where the secret already lives.

⚠️⚠️ **The token here is generated per run, in memory, and handed to the containers as an environment
variable.** There is no token file in the tree and no default in any config: `docs/signing-keys.md`'s
precedent is that a key file is where the key is and an exported variable is an instruction — and a
default is what reaches production by omission. Nothing this test creates can be mistaken for a real
credential, because it exists only inside one Python process for a few seconds.

**Both halves are asserted.** With the token, a post reaches `keep` and is stored. **Without it, `keep`
does not start** — a service that accepted everything because no token was configured is an open door
that looks like a working deployment, so the refusal is at start-up rather than at the first request.
"""

import json
import secrets
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = _ROOT / "keep" / "migrations" / "001-initial.sql"
_TEMPLATE = _ROOT / "deploy" / "nginx" / "boxscorepuzzle.conf.template"
_NGINX = "nginx:1.27-alpine"
_POSTGRES = "postgres:17-alpine"


def _docker(
    *arguments: str, check: bool = True, timeout: int = 300, stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
    finished = subprocess.run(
        ["docker", *arguments], capture_output=True, text=True, check=False, timeout=timeout, input=stdin
    )
    if check and finished.returncode != 0:
        # ⚠️ `CalledProcessError` prints the command and swallows what the command said, which on a
        # failing `psql` is the one line that names the statement. The message carries it.
        message = f"docker {' '.join(arguments[:3])} failed ({finished.returncode}): {finished.stderr[-400:]}"
        raise AssertionError(message)
    return finished


def _available() -> str | None:
    try:
        finished = _docker("info", "--format", "{{.ServerVersion}}", check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"docker is not runnable here: {error}"
    if finished.returncode != 0:
        return f"docker is installed and not serving: {finished.stderr.strip()[:120]}"
    if not (_ROOT / "deploy" / "keep.Dockerfile").is_file():
        return "deploy/keep.Dockerfile is missing"
    return None


def _free_port() -> int:
    import socket  # noqa: PLC0415 - only the fixture needs it
    from contextlib import closing  # noqa: PLC0415

    with closing(socket.socket()) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _answers(url: str, *, data: bytes | None = None, tries: int = 60) -> tuple[int, str]:
    """Ask until something answers. ⚠️ A **real request**, never an open socket: Docker's forwarder binds
    before the container accepts and then resets what it accepted, which is how the nginx probe failed
    in CI on a server that was seconds from fine (`CLAUDE.md`)."""
    request = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    for _attempt in range(tries):
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8", "replace")
        except (urllib.error.URLError, OSError, TimeoutError):
            if tries == 1:
                # ⚠️ One try means the caller is polling and wants the answer, not a retry loop of its
                # own. Nothing listening is reported as a 502 so a poll can treat it like one.
                return 502, "nothing answered"
            time.sleep(0.25)
    message = f"nothing answered at {url}"
    raise AssertionError(message)


@pytest.fixture(scope="module")
def stack() -> Iterator[tuple[int, str, str, str]]:
    """Postgres, `keep` and `serve`'s nginx on one network, with a token that exists for this run only."""
    why = _available()
    if why is not None:
        pytest.skip(why)

    # ⚠️ 32 characters because `keep` refuses anything shorter, and `token_hex(24)` gives 48 — long
    # enough that the length floor is not what is being tested here.
    token = secrets.token_hex(24)
    suffix = _free_port()
    network, database, keep, edge = (f"bsp-{name}-{suffix}" for name in ("net", "db", "keep", "edge"))
    port = _free_port()

    _docker("network", "create", network)
    try:
        _docker(
            "build",
            "-f",
            str(_ROOT / "deploy" / "keep.Dockerfile"),
            "-t",
            f"bsp-keep-{suffix}",
            str(_ROOT / "keep"),
            timeout=900,
        )
        _docker(
            "run",
            "-d",
            "--name",
            database,
            "--network",
            network,
            "--network-alias",
            "db",
            "-e",
            "POSTGRES_PASSWORD=keep",
            "-e",
            "POSTGRES_DB=keep",
            _POSTGRES,
        )
        # ⚠⚠ **A real query against the real database, not `pg_isready`.** The official image starts a
        # temporary server to run initdb and then **restarts**; `pg_isready` answers yes during that
        # window, so the migration lands in the gap and psql exits 2. Third instance today of asking the
        # transport instead of the protocol — `CLAUDE.md` carries the rule and this is what it looks like
        # when it is not applied.
        for _attempt in range(180):
            probe = _docker("exec", database, "psql", "-U", "postgres", "-d", "keep", "-c", "SELECT 1", check=False)
            if probe.returncode == 0:
                break
            time.sleep(0.5)
        else:
            message = f"postgres never answered a query: {probe.stderr[-200:]}"
            raise AssertionError(message)
        _docker(
            "exec",
            "-i",
            database,
            "psql",
            "-U",
            "postgres",
            "-d",
            "keep",
            "-v",
            "ON_ERROR_STOP=1",
            # ⚠️ The migration arrives on **stdin**, not as `-c`. A multi-statement script with comments
            # through `-c` exited 2 without saying which statement it disliked.
            stdin=_MIGRATION.read_text(encoding="utf-8"),
        )

        _docker(
            "run",
            "-d",
            "--name",
            keep,
            "--network",
            network,
            "--network-alias",
            "keep",
            "-e",
            f"KEEP_SHARED_TOKEN={token}",
            "-e",
            "KEEP_DATABASE_URL=postgresql://postgres:keep@db:5432/keep",
            f"bsp-keep-{suffix}",
        )
        _docker(
            "run",
            "-d",
            "--name",
            edge,
            "--network",
            network,
            "-p",
            f"{port}:8080",
            "-e",
            f"KEEP_SHARED_TOKEN={token}",
            "-e",
            "NGINX_ENVSUBST_FILTER=^KEEP_",
            "-v",
            f"{_TEMPLATE.as_posix()}:/etc/nginx/templates/default.conf.template:ro",
            "-v",
            f"{str(_ROOT).replace(chr(92), '/')}/serve:/srv/serve:ro",
            _NGINX,
        )
        # ⚠⚠⚠ **Waiting for nginx is not waiting for the path this test is about, and that is what the
        # first version did.** nginx answers `/` from a static file the instant it starts; `keep` is
        # still importing psycopg, connecting and checking the schema. The first POST went out into a
        # data layer that was not listening and the edge answered **502** — green in isolation, red in
        # the full run.
        #
        # ⚠️ **Fourth instance today of asking about the near neighbour**, and this one is in the code
        # written to demonstrate the rule. `CLAUDE.md` says knowing the rule does not apply it; this is
        # what that looks like.
        #
        # ⚠️ **It waits on the whole path** — browser to edge to `keep` — because that is what every case
        # below uses. Retrying on 502 **here** is correct and retrying on 502 in an assertion would not
        # be: this is establishing that the stack is up, and those are testing what it does.
        for _attempt in range(240):
            status, _body = _answers(f"http://127.0.0.1:{port}/api/errors", data=b'{"errors": []}', tries=1)
            if status != 502:
                break
            time.sleep(0.5)
        else:
            message = "keep never became reachable through the edge"
            raise AssertionError(message)
        yield port, token, network, f"bsp-keep-{suffix}"
    finally:
        for name in (edge, keep, database):
            _docker("rm", "-f", name, check=False, timeout=120)
        _docker("network", "rm", network, check=False, timeout=120)
        _docker("image", "rm", "-f", f"bsp-keep-{suffix}", check=False, timeout=300)


class TestThePostReachesKeep:
    def test_an_event_is_accepted_through_the_edge(self, stack: tuple[int, str, str, str]) -> None:
        """⚠️ The whole path: browser → `serve` → nginx adds the token → `keep` stores it. Nothing in the
        browser's request carries the secret."""
        port, _token, _network, _image = stack
        event = {
            "event_id": "11111111-1111-4111-8111-111111111111",
            "device_id": "22222222-2222-4222-8222-222222222222",
            "puzzle_id": "0123456789abcdef",
            "calendar_date": "2026-09-02",
            "played_on": "2026-09-02",
            "account_id": None,
            "duration_ms": 600_000,
            "hints": 0,
            "errors": 0,
            "failed_checks": 0,
            "highest_technique": None,
            "solved": True,
            "assisted": False,
        }

        status, body = _answers(f"http://127.0.0.1:{port}/api/events", data=json.dumps({"events": [event]}).encode())

        assert status in {200, 201, 202, 204}, f"the edge answered {status}: {body[:200]}"
        # ⚠️⚠️ **`stored` names the id, and a status alone would not.** A 200 says the edge answered; this
        # says `keep` holds the row. Two different claims, and a proxy is exactly the thing that can
        # satisfy the first without the second.
        assert event["event_id"] in json.loads(body).get("stored", []), f"keep did not store it: {body[:200]}"

    def test_the_browser_never_supplies_the_token(self, stack: tuple[int, str, str, str]) -> None:
        """⚠️⚠️ **The client's own Authorization header is discarded rather than merged.** A browser that
        sent one must not be able to influence what `keep` sees. Sending a wrong one and still being
        accepted is what says the edge decides."""
        port, _token, _network, _image = stack
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/errors",
            data=json.dumps({"errors": []}).encode(),
            method="POST",
        )
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", "Bearer not-the-token-at-all")

        with urllib.request.urlopen(request, timeout=10) as response:
            assert response.status in {200, 201, 202, 204}

    def test_only_post_reaches_the_data_layer(self, stack: tuple[int, str, str, str]) -> None:
        """`keep` answers three routes and a GET on this path is not one. Refused at the edge rather
        than forwarded, so the data layer never sees a request it has no answer for."""
        port, _token, _network, _image = stack

        status, _body = _answers(f"http://127.0.0.1:{port}/api/events")

        assert status == 403, f"a GET on the API path answered {status}"


class TestKeepWithoutATokenDoesNotStart:
    """⚠️⚠️ **The half that is usually missing.** A service that accepted everything because no token was
    configured would be an open door that looks like a working deployment, so the refusal is at
    **start-up**: a misconfiguration is a container that will not come up rather than one that serves.
    """

    def test_it_exits_rather_than_serving(self, stack: tuple[int, str, str, str]) -> None:
        """⚠️⚠️ **Against a database it can reach, and the first version was not.**

        `main()` checks the DSN, connects, and only then asks for the token — so a run pointed at a
        host that does not resolve dies on the connection and never reaches the check. It exited
        non-zero, said nothing about a token, and the assertion passed on the wrong refusal. **A test
        that cannot reach the code it is about is satisfied by any failure at all.**
        """
        _port, _token, network, image = stack

        finished = _docker(
            "run",
            "--rm",
            "--network",
            network,
            "-e",
            "KEEP_DATABASE_URL=postgresql://postgres:keep@db:5432/keep",
            image,
            check=False,
            timeout=180,
        )

        assert finished.returncode != 0, "keep started with no token configured"
        said = finished.stdout + finished.stderr
        assert "KEEP_SHARED_TOKEN" in said, f"it refused for some other reason: {said[-400:]}"
