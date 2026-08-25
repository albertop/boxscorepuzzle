"""The real server block, over the real `serve/`, against the two tables that declare what it must do.

⚠️⚠️ **This is the check the route work has been owing since E1.** `tools/dev_server.py` and an nginx
server block are two implementations of one route set, and until now nothing compared them — the
project's oldest defect, recorded in `do_GET` and left standing because there was no nginx to compare
against. There is one now.

**Two declarations, and neither is restated here:**

  * `tools/dev_server.py`'s `ROUTES`, each tagged `production` or `development`
  * the cache table in `docs/calendar.md`, whose first column is a URL for exactly this reason

⚠️⚠️ **Both halves of the tag are asserted.** Everything tagged production must answer, and **nothing
tagged development may.** A test checking only the first half passes an nginx that also serves
`/t/<mode>` — a development affordance reachable by players, handing them `?test=solved`, which is the
thing tagging exists to prevent.

⚠️ **It needs Docker and says so when there is none.** A skip that reads like a pass is the shape this
project keeps closing.
"""

import http.client
import importlib.util
import re
import secrets
import socket
import subprocess
import time
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

from tests.conftest import DOCKER_PREFIX, nginx_base_image, nginx_environment_flags

_ROOT = Path(__file__).resolve().parents[2]
_CONF = _ROOT / "deploy" / "nginx" / "boxscorepuzzle.conf.template"
_CALENDAR = _ROOT / "docs" / "calendar.md"
_IMAGE = nginx_base_image()
"""⚠️ Read from `deploy/serve.Dockerfile`, never spelled. This was `nginx:1.27-alpine` while the
Dockerfile had moved to 1.30.4 -- a suite green about a config running on a different nginx than
the one shipped."""
_CONTAINER_PORT = 8080


def _dev_server() -> object:
    """`tools/dev_server.py` loaded by path — it is a script, not an installed module (§33)."""
    spec = importlib.util.spec_from_file_location("dev_server_for_nginx", _ROOT / "tools" / "dev_server.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cache_table() -> list[tuple[str, str]]:
    """`(url, cache-control)` from `docs/calendar.md`, parsed rather than restated.

    ⚠️⚠️ **An empty parse is a failure, not an empty sweep.** A table that moved or was reformatted would
    otherwise leave every case below iterating over nothing and reporting green — a check that cannot
    fire, which this project has recorded often enough to write the guard by default.
    """
    text = _CALENDAR.read_text(encoding="utf-8")
    start = text.find("| URL | `Cache-Control` | why |")
    assert start != -1, f"no cache table in {_CALENDAR.name}; it moved or was renamed"
    rows: list[tuple[str, str]] = []
    for line in text[start:].splitlines()[2:]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        url, rule = cells[0].strip("`"), cells[1].strip("`")
        rows.append((url, rule))
    assert rows, "the cache table parsed to nothing"
    return rows


def _free_port() -> int:
    with closing(socket.socket()) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _docker() -> str | None:
    """Why Docker cannot be used, or `None` if it can."""
    try:
        finished = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"docker is not runnable here: {error}"
    if finished.returncode != 0:
        return f"docker is installed and not serving: {finished.stderr.strip()[:120]}"
    return None


def _serve(conf: Path) -> Iterator[int]:
    """nginx in a container over `serve/` and one config, torn down whatever happened."""
    port = _free_port()
    name = f"{DOCKER_PREFIX}-nginx-{port}"
    # ⚠️ `-w` gives the Windows path Docker needs; on Linux `Path.as_posix()` is already right.
    root = str(_ROOT).replace("\\", "/")
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            name,
            "-p",
            f"{port}:{_CONTAINER_PORT}",
            "-v",
            f"{root}/serve:/srv/serve:ro",
            # ⚠⚠ **Mounted as a TEMPLATE, which is how it is deployed.** The config carries
            # `${KEEP_SHARED_TOKEN}` and the nginx image substitutes it at start; mounting it straight
            # into `conf.d/` would leave the placeholder in place and test a config that never runs.
            #
            # ⚠️ **A throwaway token, because a config that names one must have one to be valid** — not
            # because anything here authenticates. It exists inside this process for a few seconds.
            "-e",
            f"KEEP_SHARED_TOKEN={secrets.token_hex(24)}",
            *nginx_environment_flags(),
            "-v",
            f"{conf.as_posix()}:/etc/nginx/templates/default.conf.template:ro",
            _IMAGE,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=180,
    )
    try:
        # ⚠⚠ **A real request, and a socket connecting is not one.** The first version waited for
        # `create_connection` to succeed — which it does the moment **Docker's** port forwarder binds,
        # before nginx inside the container is accepting anything. The forwarder then accepts the TCP
        # connection and resets it, so the first case failed with `ConnectionResetError` on a server that
        # was seconds from being fine.
        #
        # ⚠️ **It passed on the laptop and failed in CI**, because a warm image starts in a blink and a
        # cold runner does not. That is what CI buys and it is the second time today an instrument
        # answered the near neighbour of its question: *is the port open* instead of *does nginx answer*.
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                get(port, "/")
                break
            except (OSError, http.client.HTTPException):
                time.sleep(0.2)
        else:
            message = f"nginx never answered an HTTP request on {port} within 60s"
            raise AssertionError(message)
        yield port
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False, timeout=60)


@pytest.fixture(scope="module")
def nginx() -> Iterator[int]:
    why = _docker()
    if why is not None:
        pytest.skip(why)
    yield from _serve(_CONF)


def get(port: int, path: str) -> tuple[int, str, bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, response.headers.get("Cache-Control", ""), response.read()
    finally:
        connection.close()


def published_id(port: int) -> str:
    """A puzzle id the public manifest actually names. ⚠️ Never a literal: the id is derived from the
    game and a regeneration renames it, which broke a whole vector file the first time it happened."""
    import json  # noqa: PLC0415 - only this helper needs it

    _status, _header, body = get(port, "/data/puzzles/manifest.json")
    ids = json.loads(body)["puzzles"]
    assert ids, "the public manifest names no puzzles"
    return str(ids[0])


class TestTheProductionRoutesAnswer:
    def test_the_declaration_holds_routes_of_both_kinds(self, nginx: int) -> None:
        """⚠️ The check on the checks. A sweep over a table with no development routes would assert the
        second half against nothing and report green."""
        routes = _dev_server().ROUTES
        kinds = {route.environment for route in routes}

        assert kinds == {"production", "development"}, f"the route table is all one kind: {kinds}"

    def test_every_production_route_answers_what_it_declares(self, nginx: int) -> None:
        for route in _dev_server().ROUTES:
            if route.environment != "production":
                continue
            # A prefix route needs a real id after it; an exact one is its own address.
            path = f"{route.path}{published_id(nginx)}" if route.prefix else route.path
            status, _header, body = get(nginx, path)

            assert status == route.answer, f"{path} answered {status}, and the contract says {route.answer}"
            assert body, f"{path} answered {status} with an empty body"

    def test_the_board_route_serves_the_board_page(self, nginx: int) -> None:
        """⚠️⚠️ **Not byte equality against `play.html`, which is the assertion that missed a blank page.**
        `/p/<id>` matched the file exactly while the page could not load a single asset: relative paths
        resolved under `/p/`, and the prefix rewrite answered them with the HTML itself, so the browser
        refused the module on MIME. **The bytes were right and the page was dead.**

        So this asks for what the page *names* as well: the modules and stylesheets it references have to
        be reachable from the address the player is at.
        """
        page = get(nginx, f"/p/{published_id(nginx)}")[2].decode("utf-8")
        named = re.findall(r'(?:src|href)="([^"]+\.(?:js|css))"', page)

        assert named, "the board page names no modules or stylesheets, so this proves nothing"
        for asset in named:
            status, _header, body = get(nginx, asset)
            assert status == 200, f"the board page names {asset}, which answers {status}"
            assert not body.lstrip().startswith(b"<"), f"{asset} answered with markup, which a module cannot be"

    def test_every_url_the_client_links_to_answers(self, nginx: int) -> None:
        """⚠⚠ **`ROUTES` in `daily.js` is what the pages actually link to, and both were dead.**

        They were filenames — `play.html`, `tutorial.html` — which from `/` resolve to `/play.html` and
        `/tutorial.html`, neither of which is a route. **The entire way into the game, on the address
        every visit lands at.** The browser test that checked them fetched `../ui/phone/${file}`,
        supplying the directory whose absence was the defect.

        ⚠️ So this asks the **server**, from the root, exactly as a click does.
        """
        source = (_ROOT / "serve" / "ui" / "phone" / "daily.js").read_text(encoding="utf-8")
        found = re.search(r"export const ROUTES = \{([^}]*)\}", source)
        assert found is not None, "ROUTES is not where this expects it; the shape changed"
        urls = re.findall(r'"([^"]+)"', found.group(1))

        assert urls, "ROUTES parsed to nothing, so this proves nothing"
        for url in urls:
            status, _header, body = get(nginx, url)
            assert status == 200, f"the client links to {url} and nginx answers {status}"
            assert body, f"{url} answered 200 with an empty body"


class TestTheDevelopmentRoutesDoNot:
    """⚠️⚠️ **The half a route test usually forgets.** Everything tagged development must be unreachable:
    `/t/<mode>` reaches the board with a development mode, and answering it in production hands a player
    `?test=solved`."""

    def test_no_development_route_answers(self, nginx: int) -> None:
        for route in _dev_server().ROUTES:
            if route.environment != "development":
                continue
            path = f"{route.path}fill" if route.prefix else route.path
            status, _header, _body = get(nginx, path)

            assert status == 404, f"{path} is tagged development and nginx answered {status}"

    def test_implementation_paths_are_not_reachable(self, nginx: int) -> None:
        """v36-P3-48: they are where the files happen to live today, and two URLs for one page is
        duplicate content indexed permanently."""
        for path in ("/ui/phone/index.html", "/ui/phone/play.html", "/ui/phone/today.html"):
            status, _header, _body = get(nginx, path)

            assert status == 404, f"{path} is reachable as an alternate and answered {status}"

    def test_an_unknown_board_id_is_the_servers_404(self, nginx: int) -> None:
        """⚠️ Not a substitution (v36-P3-45). The absence of the requested puzzle must not read as the
        presence of another, and at the server that means a 404 rather than another board's page."""
        status, _header, _body = get(nginx, "/p/deadbeefdeadbeef/and/more")

        assert status == 404


class TestTheCacheTable:
    def test_every_row_is_served_with_the_rule_it_declares(self, nginx: int) -> None:
        for url, rule in cache_table():
            path = url.replace("<id>", published_id(nginx))
            status, header, _body = get(nginx, path)

            assert status == 200, f"{path} is in the cache table and answered {status}"
            assert header == rule, f"{path} was served `{header}` and the table says `{rule}`"

    def test_the_package_is_the_only_thing_that_caches(self, nginx: int) -> None:
        """⚠️⚠️ **The property behind the table, asserted separately from the table.** A package cannot
        change; everything else can. If a second row ever gains a `max-age`, that is a decision and this
        turns red rather than letting it through because the table was edited in the same commit."""
        caching = [url for url, rule in cache_table() if "max-age" in rule]

        assert caching == ["/data/puzzles/<id>.json"], f"something other than a package caches: {caching}"
