"""`keep`'s three routes, as a WSGI application.

**`docs/keep-api.md` is the contract.** This is thin on purpose: everything worth getting right is in
`store.py`, `auth.py` and `reading.py`, and this file is the part that turns a request into a call.

⚠️⚠️ **Plain WSGI and no framework, and that is a decision rather than an omission.** The service has
three routes, no templating, no sessions, no ORM and no async workload — it writes rows and answers a
health check. §23 asks for availability from **having fewer pieces rather than bigger ones**, and a
framework here would add two dependencies to save perhaps forty lines.

**What would reverse it:** authentication flows, a real API surface for the archive and metrics, or
anything needing content negotiation. `keep` gains all three in beta 3, and swapping this file for a
framework then is a contained change **because the parts that matter do not import it.**

⚠️ **Every response is JSON, including refusals.** A caller that gets HTML when it expected JSON reports
a parse error, which is the least useful description available of what went wrong.
"""

import json
from collections.abc import Callable, Iterable
from typing import Any

from keep.auth import accepted, presented
from keep.reading import MalformedError, read_batch, read_error, read_event
from keep.store import Store

_MAX_BODY = 1_000_000
"""A megabyte. A queue draining after a week offline is a few hundred events at roughly 300 bytes each;
this is far past that and far short of anything that costs memory.

⚠️ **A cap exists at all because an unbounded read is a way to take the service down** with one request
from inside the network — which is exactly the trust level the shared token assumes and does not prove."""


def _reply(start: Callable[..., Any], status: str, body: dict[str, Any]) -> list[bytes]:
    payload = json.dumps(body).encode("utf-8")
    start(status, [("Content-Type", "application/json"), ("Content-Length", str(len(payload)))])
    return [payload]


Application = Callable[[dict[str, Any], Callable[..., Any]], Iterable[bytes]]
"""What WSGI asks for. ⚠️ Named rather than spelled at both ends: `main.build` returns one and this makes
one, and two spellings of a callable signature drift the moment either changes."""


def create_app(store: Store, token: str) -> Application:
    """The application, given a store and the token it accepts.

    ⚠️ **Both are arguments rather than read here.** `auth.configured_token()` refuses at *startup*; a
    token this file read per request would turn a misconfiguration into a running service that rejects
    everybody, which looks like an outage in the client rather than an error in the deployment.
    """

    def application(  # noqa: PLR0911 - one return per outcome, and collapsing them hides which
        environ: dict[str, Any], start_response: Callable[..., Any]
    ) -> Iterable[bytes]:
        path = environ.get("PATH_INFO", "")
        method = environ.get("REQUEST_METHOD", "GET")

        if path == "/health" and method == "GET":
            # ⚠️ **No token on health.** Uptime Kuma reaches it through `serve`'s proxy and holds no
            # secret; requiring one would mean the monitor carries a credential whose only use is
            # asking whether the service is up. It says status and nothing else, so there is nothing
            # to protect: a public endpoint naming the host it cannot reach hands out more than it needs.
            try:
                store.alive()
            except Exception:
                return _reply(start_response, "503 Service Unavailable", {"status": "unavailable"})
            return _reply(start_response, "200 OK", {"status": "ok"})

        if not accepted(presented(environ.get("HTTP_AUTHORIZATION")), token):
            # ⚠️ One answer for a missing header, a malformed one and a wrong token. Distinguishing them
            # tells a caller how close it is.
            return _reply(start_response, "401 Unauthorized", {"error": "unauthorized"})

        if method != "POST" or path not in {"/events", "/errors"}:
            return _reply(start_response, "404 Not Found", {"error": "no such route"})

        try:
            length = min(int(environ.get("CONTENT_LENGTH") or 0), _MAX_BODY)
            body = json.loads(environ["wsgi.input"].read(length) or b"null")
        except (ValueError, KeyError) as broken:
            return _reply(start_response, "400 Bad Request", {"error": f"unreadable body: {broken}"})

        try:
            if path == "/events":
                stored = store.store_events(read_batch(body, "events", read_event))
            else:
                stored = store.store_errors(read_batch(body, "errors", read_error))
        except MalformedError as refusal:
            # ⚠️ The field name travels to the caller. A 400 saying *invalid request* leaves the fix to
            # guesswork, and the caller here is a client the operator also wrote.
            return _reply(start_response, "400 Bad Request", {"error": str(refusal)})

        # ⚠️ **The ids, not a count** (`keep-api.md`). A count says how many landed and not which, so a
        # partial success would force the client to re-send everything — reintroducing the duplication
        # the id exists to prevent.
        return _reply(start_response, "200 OK", {"stored": stored})

    return application
