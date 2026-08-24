"""The development server answers every route it declares, and `/p/<id>` keeps its id.

⚠️⚠️ **These two rules exist twice and only one copy is checked here.** `tools/dev_server.py` is the
laptop's implementation; F writes the same set again as an nginx server block, and **nothing compares
them.** That is the project's oldest defect — two places that should say the same thing — and it is
recorded rather than solved: the declaration in `dev_server.py` is what F must copy from, and this file
asserts the declaration against the running server so at least one side cannot drift silently.

⚠️ **A real server, not a call to `do_GET`.** The route table is a property of what the browser gets
back, and a handler driven in-process would pass with the socket layer, the redirect status and the
path rewrite all wrong. The browser suite starts this same server the same way.
"""

import http.client
import importlib.util
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SERVER = _ROOT / "tools" / "dev_server.py"


def _module() -> object:
    """`dev_server` loaded by path. It is a script in `tools/`, not an installed module, and §33 keeps
    it out of every package — so the declaration is read the way the runner reads the file."""
    spec = importlib.util.spec_from_file_location("dev_server_routes", _SERVER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _free_port() -> int:
    with closing(socket.socket()) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.fixture(scope="module")
def server() -> Iterator[int]:
    """The real server on a free port, stopped afterwards whatever the tests did."""
    port = _free_port()
    process = subprocess.Popen(  # noqa: S603 - a fixed script path, no shell, no user input
        [sys.executable, str(_SERVER), str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                with closing(socket.create_connection(("127.0.0.1", port), timeout=0.5)):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            message = f"the development server never answered on {port}"
            raise AssertionError(message)
        yield port
    finally:
        process.terminate()
        process.wait(timeout=10)


def _get(port: int, path: str) -> tuple[int, str, bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, response.headers.get("Location", ""), response.read()
    finally:
        connection.close()


class TestEveryDeclaredRedirectAnswers:
    """⚠️ Driven from the declaration, so adding a route without exercising it is not possible: a new
    entry in `REDIRECTS` becomes a new case here on the next run."""

    def test_the_declaration_is_not_empty(self) -> None:
        # ⚠️ A parameterised sweep over an empty mapping passes and says nothing. This is the check on
        # the check, and the project has recorded that shape often enough to write it by default.
        assert _module().REDIRECTS, "no redirects are declared, so the sweep below proves nothing"

    def test_each_one_redirects_where_it_says(self, server: int) -> None:
        for path, where in _module().REDIRECTS.items():
            status, location, _body = _get(server, path)
            assert status == 302, f"{path} answered {status}, not a redirect"
            assert location == where, f"{path} went to {location}, not {where}"

    def test_the_test_mode_route_reaches_today_carrying_the_mode(self, server: int) -> None:
        """⚠️ It goes through `/today` rather than straight to the board, and that is not a detour: the
        board takes its id from the path and the server does not know today's id — only the pointer
        does."""
        status, location, _body = _get(server, "/t/fill")

        assert status == 302
        assert location == f"{_module().REDIRECTS['/today']}?test=fill"

    def test_an_unknown_mode_is_forwarded_rather_than_listed(self, server: int) -> None:
        """`testmode.js` owns which modes exist. A list here would be a second copy of that decision."""
        _status, location, _body = _get(server, "/t/not-a-mode")

        assert location.endswith("?test=not-a-mode")


class TestTheBoardRouteIsARewrite:
    """⚠️⚠️ `/p/<id>` is canonical (C6), so it must stay in the address bar. A redirect to `play.html`
    would take the id away and leave the loader with nothing to ask for."""

    def test_it_serves_the_board_page_with_a_200(self, server: int) -> None:
        status, _location, body = _get(server, "/p/0ed0aad8886544ca")

        assert status == 200, f"the board route answered {status}"
        assert b"main.js" in body, "the board route did not serve the board page"

    def test_the_page_is_the_same_one_the_direct_address_serves(self, server: int) -> None:
        """⚠️ Byte equality, because *serves a board page* is satisfied by serving a **different** one.
        The rewrite has one job and this is the assertion that it did that job rather than a similar."""
        _status, _location, rewritten = _get(server, "/p/0ed0aad8886544ca")
        _status, _location, direct = _get(server, _module().BOARD)

        assert rewritten == direct

    def test_a_missing_file_is_still_a_404(self, server: int) -> None:
        """⚠️ The rewrite must not swallow everything under `/p/`. It catches the board prefix; anything
        the tree genuinely does not hold still answers honestly."""
        status, _location, _body = _get(server, "/ui/phone/not-a-file.js")

        assert status == 404


class TestNothingIsCached:
    """The whole reason this server exists rather than `python -m http.server`."""

    def test_every_response_says_do_not_keep_this(self, server: int) -> None:
        connection = http.client.HTTPConnection("127.0.0.1", server, timeout=10)
        try:
            connection.request("GET", _module().BOARD)
            response = connection.getresponse()
            response.read()
            assert "no-store" in response.headers.get("Cache-Control", "")
        finally:
            connection.close()
