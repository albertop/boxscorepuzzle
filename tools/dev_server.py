"""A static server for `serve/` that never lets the browser cache anything.

⚠️ **Written because the cache made "did my change land?" unanswerable, twice.** The six reference
packages were regenerated, the manifest was rewritten to name the new generation, and the browser went
on serving the old manifest *and* the old JavaScript modules — so a correct client refused the packages
as the wrong schema and the failure looked like a code defect. `docs/serve-brief.md` §6 already records
the earlier instance: a prototype reported as *not rendering* that was the cache.

`python -m http.server` sends `Last-Modified` and lets the browser decide, which is the wrong default for
a tree being edited every few seconds. This sends `Cache-Control: no-store` on everything, so what the
page runs is what is on disk. **Development only** — production caching is nginx's job and is the
opposite shape: `<generation>/<id>.json` is immutable and cached hard, while `manifest.json` is a pointer
and is never cached.

⚠️ **Lives in `tools/`, not in `serve/`.** Deployment ships `serve/` only, so a development server
sitting inside it would travel to the VPS. That is the same reasoning as `forge/` never shipping: the
boundary is what the directory means, not what the file is called.

    python tools/dev_server.py [port]
"""

import re
import socket
import sys
from dataclasses import dataclass
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1] / "serve"
BOARD = "/ui/phone/play.html"
LANDING = "/ui/phone/index.html"
TODAY = "/ui/phone/today.html"
TUTORIAL = "/ui/phone/tutorial.html"
PORT = 8137

PRODUCTION = "production"
DEVELOPMENT = "development"
"""Which environment a route belongs to. **⚠️⚠️ The tag is the whole of what makes a comparison
possible.**

nginx must implement **everything tagged production and nothing tagged development**. That is not
equality, and a test that checked only the first half would pass an nginx that also answered
`/t/<mode>` — a development affordance reachable by players, which is the thing tagging exists to
prevent. `serve/nginx/boxscorepuzzle.conf` is the other implementation and
`forge/tests/test_nginx_serves_what_is_declared.py` asserts both halves against this table.

⚠️ **One table rather than two lists.** Two lists is exactly the defect the comparison exists to close:
they agree until somebody edits one."""


@dataclass(frozen=True, slots=True)
class Route:
    """One address, what it answers with, and where it belongs.

    `answer` is the **status** the URL contract requires (`docs/serve-brief.md`, v36-P3-48). A rewrite
    answers 200 with the page's own body and leaves the address in the bar; a redirect answers 302.
    """

    path: str
    answer: int
    target: str
    environment: str
    prefix: bool = False


ROUTES = (
    # ⚠️⚠️ **200 by rewrite, not 302, and this was a redirect until 2026-08-24.** v36-P3-48: *a redirect
    # makes the canonical homepage a second URL*. The dev server was teaching the shape the production
    # contract forbids, on the address every visit lands at (`docs/serve-flow.md` §1).
    Route("/", 200, LANDING, PRODUCTION),
    # ⚠️ Also a rewrite now. C6 says `/today` redirects and it still does — **from the page**, since E1
    # built it as a static page rather than a server redirect: §23 keeps a process off the play path.
    Route("/today", 200, TODAY, PRODUCTION),
    # C6's canonical board URL. The id stays in the address, so the page can read it.
    Route("/p/", 200, BOARD, PRODUCTION, prefix=True),
    # ⚠️⚠️ **The tutorial had no URL at all until 2026-08-24.** `docs/serve-flow.md` §1b makes it
    # reachable from the landing page at any time, and the landing linked `tutorial.html` — which from
    # `/` is `/tutorial.html`, a 404. **A page the product documents as reachable, unreachable.**
    Route("/tutorial", 200, TUTORIAL, PRODUCTION),
    # ⚠️ **Development.** A handset shortcut: one tap to today's board without typing an id. It is a
    # redirect on purpose — it has no page of its own — and nginx must not answer it.
    Route("/p", 302, "/today", DEVELOPMENT),
    # ⚠️ **Development, and the reason tagging is not decoration.** `/t/<mode>` reaches the board with a
    # development mode. Answering it in production hands players `?test=solved`.
    Route("/t/", 302, TODAY, DEVELOPMENT, prefix=True),
)
"""Every address this server answers specially. **Declared once so both implementations are checked
against the same table.**"""

BOARD_PATTERN = re.compile(r"^/p/([0-9a-f]+)/?$")
"""⚠️⚠️ **Anchored, and a bare `startswith("/p/")` left the canonical route serving a blank page.**

The board page names its assets, and under a prefix rewrite `/p/<id>` + `main.js` is `/p/main.js` —
which `startswith` answered with **`play.html` itself**, so the browser was handed HTML where it asked
for a module and refused it on MIME. `#app` empty, no stylesheet, nothing on screen.

**Both halves were wrong and both are fixed**: the pages name their assets absolutely now, and this
matches only what `daily.js`'s `idInPath` matches. A pattern that swallows everything under a prefix is
the same shape as a soft-404 — every wrong address answering 200 with something that is not what was
asked for."""


class NoCache(SimpleHTTPRequestHandler):
    """Every response says *do not keep this*, including 304-eligible ones.

    ⚠️ `no-store` rather than `no-cache`: the second still permits a stored copy revalidated by
    `If-Modified-Since`, and a revalidation the server answers with 304 is exactly how a stale module
    survives an edit whose mtime resolution the filesystem rounded.
    """

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    protocol_version = "HTTP/1.1"
    """⚠⚠ **Keep-alive, and HTTP/1.0 without it hung the headless browser suite.**

    `BaseHTTPRequestHandler` defaults to 1.0, so every response closed its connection and every fetch
    opened a new one. An ordinary browser hides that behind its cache; the headless suite caches nothing
    and made a fresh TCP connection for each of several hundred requests, and somewhere past the last
    test the next one simply never completed. **It moved when tests were added or removed**, which is
    the signature of a limit rather than a defect in any one test -- and it cost an afternoon of
    bisecting because it looked like whichever test happened to be standing on the line.

    ⚠️ **`Content-Length` is mandatory on every response now**, including the redirects below: under
    1.1 a client keeps the connection open waiting for a body it was not told the length of.
    `SimpleHTTPRequestHandler` already sends one for files.
    """

    def _redirect(self, where: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", where)
        # ⚠️ Zero, said out loud. Under HTTP/1.1 a bodyless response with no length is a connection the
        # client holds open forever -- the same hang this class was just fixed for, one layer up.
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        # ⚠⚠ **Short addresses, because typing a URL on a phone is the actual cost.** The pages live
        # under `/ui/phone/`, which is fine to type on a laptop and miserable on a handset — and the
        # whole point of the test mode is checking a change on the device it was designed for.
        #
        # ⚠️⚠️ **These are the routes F has to write again, in nginx, and nothing checks that the two
        # agree.** `REDIRECTS` and the board rewrite below are the whole set; an nginx server block is a
        # second implementation of them and the project's oldest defect is two places that should say
        # the same thing and do not. `forge/tests/test_dev_server_routes.py` asserts *this* side against
        # the declaration — it cannot see the other one. **F must copy from the declaration rather than
        # from memory**, and this paragraph is here so F finds the problem rather than rediscovering it.
        #
        # ⚠️ **And this server can never reach a player.** It is `tools/`, which deployment does not
        # ship — the same boundary that keeps `forge/` off the VPS.
        for route in ROUTES:
            if route.prefix:
                continue
            if self.path == route.path:
                if route.answer == 302:  # noqa: PLR2004 - the status is the subject
                    self._redirect(route.target)
                else:
                    self.path = route.target
                break
        if self.path.startswith("/t/"):
            mode = self.path[len("/t/"):].strip("/")
            # Through `/today`, which then carries the mode into `/p/<id>`. Routing straight to the
            # board is no longer possible: the board takes its id from the path and this does not know
            # what today's is — only the pointer does.
            self._redirect(f"{TODAY}?test={quote(mode, safe='')}")
            return
        if BOARD_PATTERN.match(self.path):
            # ⚠️⚠️ **A rewrite, not a redirect: `/p/<id>` is canonical (C6) and must stay in the bar.**
            # The page reads its own id from `location.pathname`, so redirecting to `play.html` would
            # take the id away and leave the loader with nothing to ask for. nginx does this with
            # `try_files $uri /ui/phone/play.html`; here it is one assignment.
            self.path = BOARD

        # ⚠️ **The validators are dropped before the parent sees them.** `no-store` tells the browser
        # not to keep a copy; it does not stop one it already has from being revalidated, and a 304
        # answered against a stale copy is how the old module survived a reload. Removing the
        # conditional headers forces a full body every time, which is what a dev server is for.
        for validator in ("If-Modified-Since", "If-None-Match"):
            if validator in self.headers:
                del self.headers[validator]
        super().do_GET()

    def log_message(self, fmt: str, *args: object) -> None:
        # One line per request, without the date noise, so a missing fetch is visible at a glance.
        sys.stderr.write(f"  {fmt % args}\n")


def _reachable_at(port: int) -> list[str]:
    """Every address this server can be opened at, so the one to type into a phone is on screen.

    ⚠️ **Printed rather than left to be worked out.** The whole point of binding every interface is a
    second device, and `http://localhost` is the one address that is useless from one. The laptop's
    address on the wireless network is what a phone needs, it changes with the network, so nothing can
    hard-code it and a person should not have to go looking.

    ⚠⚠ **And inside a container it refuses to guess, because the first version guessed wrong.** The
    probe below asks the operating system which interface it would use, and in a container the answer
    is the container's own bridge address on the container's own port — it printed
    `http://172.20.0.2:8080/...`, which no phone can reach and which reads exactly like an address that
    works. The host's address and the published port are facts the container does not have and cannot
    obtain, so it says that instead of inventing one. **The same shape as the text dump that supplied
    its own padding: an instrument reporting on its own environment rather than the one that matters.**
    """
    addresses = [f"http://localhost:{port}/"]
    if Path("/.dockerenv").exists():
        addresses.append(
            "from a phone: the host's own address on the network, at the port compose publishes "
            "-- this container cannot see either of them"
        )
        return addresses
    try:
        # A UDP socket to an address that is never contacted: it makes the OS choose a source
        # interface, which is the one a phone on the same network would reach. No packet is sent.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("10.255.255.255", 1))
            addresses.append(
                f"http://{probe.getsockname()[0]}:{port}/   <- from a phone; "
                "/p for the board, /t/fill, /t/solved, /t/reset"
            )
    except OSError:
        addresses.append("(no network address found: this laptop is not on a network)")
    return addresses


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    if not ROOT.is_dir():
        message = f"{ROOT} is not a directory"
        raise SystemExit(message)
    handler = partial(NoCache, directory=str(ROOT))
    print(f"serving {ROOT} on http://localhost:{port} with caching off", flush=True)
    for address in _reachable_at(port):
        print(f"  {address}", flush=True)
    # ⚠⚠ **`ThreadingHTTPServer`, and the plain one was a real outage.** `HTTPServer` handles one
    # request at a time, so a single connection left open blocks every other client permanently — the
    # server reports `Up 26 minutes`, its log shows requests it served, and nothing new is answered.
    # That happened: one `Established` and one `CloseWait` socket on 8137 and a dead server.
    #
    # It stopped being tolerable the moment a **second device** was the point. A laptop browser and a
    # phone on the same server is exactly the case one thread cannot serve, and the failure looks like
    # the phone being unable to reach the laptop rather than like a server defect.
    ThreadingHTTPServer(("0.0.0.0", port), handler).serve_forever()  # noqa: S104


if __name__ == "__main__":
    main()
