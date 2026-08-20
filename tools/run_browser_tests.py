"""Run the browser suite headless and exit non-zero if anything failed.

The engine's tests run in a real browser because the engine runs in a real browser: the harness
asserts computed styles, element geometry and the cascade, and none of that has an answer outside one.
`serve/tests/index.html` is the same page a person opens; this drives it and reads the result.

⚠️ **It reads `window.__results`, not the page text.** The harness sets `{passed, failures}` at the end
of its run, which is a value rather than a rendering of one — and a driver that scraped the summary
line would be an instrument supplying part of what it measures, which is a shape this project has
already paid for once today.

⚠️⚠️ **It fails closed on every way of not finishing.** A module that throws on import leaves
`__results` undefined and the page otherwise blank; a harness that never runs leaves it undefined too.
Both are reported as failures with whatever the console said, because *the absence of a result must
never read as a passing one* — the same rule as an unverified signature. A driver that timed out and
exited zero would turn a broken client into a green build.

    python tools/run_browser_tests.py [--headed]
"""

import socket
import subprocess
import sys
from contextlib import closing
from pathlib import Path

# ⚠⚠ **The stream is forced to UTF-8, and the same fix was made in `lint_discovery.py` an hour
# earlier and not carried here.** This prints test *names* and failure messages, which come from
# `engine.test.js` and are full of warning signs; Windows gives a redirected stream cp1252, so the
# first real failure this runner reported died on a `UnicodeEncodeError` while printing it — turning
# a named failing test into a traceback. **A tool that prints text it did not write cannot control the
# characters in it.** A rule applied to one file and not to its sibling is the shape this project keeps
# finding; this is that shape, inside the fix for it.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "tools" / "dev_server.py"
READY_TIMEOUT_MS = 120_000
"""Long enough for a cold chromium on a slow runner, short enough to fail rather than hang a job."""


def free_port() -> int:
    """A port the operating system says is free.

    ⚠️ Not a fixed one: the dev container publishes 8137 and a developer running this locally would
    otherwise get a confusing bind error, or worse, silently test *the container's* files instead of
    the working tree.
    """
    with closing(socket.socket()) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError:
        print("playwright is not installed. `uv sync --group dev` in forge/, then `playwright install chromium`.")
        return 2

    port = free_port()
    server = subprocess.Popen(  # noqa: S603
        [sys.executable, str(SERVER), str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    console: list[str] = []
    try:
        with sync_playwright() as play:
            browser = play.chromium.launch(headless="--headed" not in sys.argv)
            page = browser.new_page(viewport={"width": 375, "height": 812})
            # Everything the page says about itself, kept for the failure path. A suite that does not
            # finish is almost always a module that threw, and the message is in here.
            page.on("console", lambda message: console.append(f"  [{message.type}] {message.text}"))
            # ⚠️ A page error is fatal and is recorded as such rather than only logged: the harness
            # cannot finish after one, and waiting the full timeout to say so wastes two minutes of
            # every broken build.
            page.on(
                "pageerror",
                lambda error: (console.append(f"  [pageerror] {error}"), page.evaluate("window.__fatal = 1")),
            )

            page.goto(f"http://127.0.0.1:{port}/tests/index.html", wait_until="domcontentloaded")
            try:
                # ⚠⚠ **Both conditions, and waiting on only one made the fast-fail dead code.** The
                # page-error handler above sets `window.__fatal`, and this waited on `window.__results`
                # alone -- so a module that throws on import still burned the full two minutes before
                # reporting, and the flag looked like a fast path while being a variable nobody read.
                # A half-applied patch, committed without running the failing case. v30-P3-02.
                page.wait_for_function(
                    "window.__results !== undefined || window.__fatal !== undefined",
                    timeout=READY_TIMEOUT_MS,
                )
            except Exception:  # noqa: BLE001
                print("the browser suite never finished — no window.__results after "
                      f"{READY_TIMEOUT_MS // 1000}s. The console said:")
                print("\n".join(console) or "  (nothing)")
                return 1

            if page.evaluate("window.__results === undefined"):
                print("the browser suite died before it could run. The console said:")
                print("\n".join(console) or "  (nothing)")
                return 1

            results = page.evaluate("window.__results")
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)

    failures = results["failures"]
    for failure in failures:
        print(f"FAIL  {failure}")
    print(f"{results['passed']} passed, {len(failures)} failed")
    # ⚠️ A suite that reports zero of everything is a suite that did not collect, not a suite that
    # passed. Same shape as a check that never fires.
    if results["passed"] == 0 and not failures:
        print("the harness collected no tests at all")
        return 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
