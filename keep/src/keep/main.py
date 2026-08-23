"""Starting `keep`, and the four ways it refuses to start.

⚠️⚠️ **Every refusal here happens before the first request.** A service that starts and then rejects
everything looks like a client fault; one that will not come up is a deployment fault, and the
difference decides who spends the afternoon looking.

The order is deliberate: **the token first**, because it is the check whose absence is silent, and the
schema second, because a database of the wrong shape is at least visible in a query error.
"""

import os
from wsgiref.simple_server import make_server

from keep.app import Application, create_app
from keep.auth import configured_token
from keep.store import PostgresStore, Store

DSN_VARIABLE = "KEEP_DATABASE_URL"
PORT_VARIABLE = "KEEP_PORT"
DEFAULT_PORT = 8081


def build(store: Store) -> Application:
    """The application, or a refusal. **Both checks run; neither is skippable.**"""
    token = configured_token()
    # ⚠️ **Never migrates.** `data-layer.md` §7: a deploy that alters the database at three in the
    # morning is the one failure on that list a rollback does not undo. This asks and refuses.
    store.require_schema()
    return create_app(store, token)


def main() -> None:  # pragma: no cover - the process entry point; `build` is what is tested
    dsn = os.environ.get(DSN_VARIABLE, "")
    if not dsn:
        message = f"{DSN_VARIABLE} is not set. keep needs a database and does not invent one."
        raise SystemExit(message)

    import psycopg  # noqa: PLC0415 - imported here so the module loads without a driver present

    with psycopg.connect(dsn, autocommit=False) as connection:
        application = build(PostgresStore(connection))
        port = int(os.environ.get(PORT_VARIABLE, DEFAULT_PORT))
        # ⚠️ Bound to every interface **inside the container**, whose port is not published to the host
        # (`data-layer.md` §4). The token is the second line of defence, not the first.
        with make_server("", port, application) as server:
            server.serve_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
