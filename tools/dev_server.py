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

import sys
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "serve"
PORT = 8137


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

    def do_GET(self) -> None:
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


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    if not ROOT.is_dir():
        message = f"{ROOT} is not a directory"
        raise SystemExit(message)
    handler = partial(NoCache, directory=str(ROOT))
    print(f"serving {ROOT} on http://localhost:{port} with caching off", flush=True)
    HTTPServer(("0.0.0.0", port), handler).serve_forever()  # noqa: S104


if __name__ == "__main__":
    main()
