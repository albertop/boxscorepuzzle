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
import threading
from collections import deque
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
READY_TIMEOUT_MS = 900_000
"""Long enough for a cold chromium on a slow runner, short enough to fail rather than hang a job.

⚠⚠ **Raised from 120s on 2026-08-23, because it fired on a suite that was passing.** E1 added tests
and the run crossed two minutes on this laptop; the runner then reported *the browser suite never
finished* with an empty console — which reads exactly like a module that failed to load, and sent the
diagnosis in the wrong direction until the page was opened by hand and found to be **1 failed, 282
passed**.

⚠️ **A timeout that fires on a healthy run is worse than a long one**, because its message names a
different fault. The suite grows; this is sized for a slow CI runner with room, not for the current
count, so it does not need raising again every time a test is added."""


LOG_LINES_KEPT = 200
"""How much of the server's log the teardown can show. The failure path prints twenty; the rest is
headroom for reading a little further back when twenty is not enough."""


def _drain(server: "subprocess.Popen[str]", log: "deque[str]") -> None:
    """Read the server's output forever, so its pipe cannot fill. See the note where the thread starts.

    ⚠️ **Failures here are swallowed on purpose.** This is a diagnostic reader on a daemon thread; an
    exception raised in it after the process is terminated would print a traceback that belongs to the
    teardown rather than to the run, on top of whatever the run was actually reporting.
    """
    stream = server.stdout
    if stream is None:  # pragma: no cover - `stdout=PIPE` above guarantees it
        return
    try:
        for line in stream:
            log.append(line.rstrip())
    except (ValueError, OSError):  # pragma: no cover - the stream closing under a terminate()
        return


def free_port() -> int:
    """A port the operating system says is free.

    ⚠️ Not a fixed one: the dev container publishes 8137 and a developer running this locally would
    otherwise get a confusing bind error, or worse, silently test *the container's* files instead of
    the working tree.
    """
    with closing(socket.socket()) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _stop(server: "subprocess.Popen[str]", log: "deque[str]", *, explain: bool) -> None:
    """Shut the development server down and, when something went wrong, say what it said.

    ⚠️ **The wait used to be a bare `server.wait(timeout=10)` inside the `finally`.** A
    `TimeoutExpired` raised there **replaces whatever exception was already travelling** — the
    runner losing the diagnosis on its way to reporting one. v36-P3-11.

    ⚠️ `explain` rather than always: the server's log on a green run is noise, and noise is how a
    report stops being read.
    """
    server.terminate()
    try:
        server.wait(timeout=10)
    except subprocess.TimeoutExpired:
        server.kill()
        log.append("the development server did not stop; killed")
    # ⚠️ From the deque the reader thread filled, never from `communicate()`. Reading the pipe here was
    # the deadlock: it is the one place that cannot help, because by now the run it would have
    # explained has already failed.
    if explain and log:
        print("the development server said:")
        for line in list(log)[-20:]:
            print(f"  {line}")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError:
        print("playwright is not installed. `uv sync --group dev` in forge/, then `playwright install chromium`.")
        return 2

    port = free_port()
    # ⚠️⚠️ **The server's own diagnostics are kept, not discarded.** (v36-P3-11) Both streams went to
    # `DEVNULL`, so a port stolen between `free_port()` and here, or a crash inside `dev_server.py`,
    # presented as a bare `net::ERR_CONNECTION_REFUSED` with the one explanation thrown away. Every
    # path already failed closed; what was missing was any way to find out why.
    server = subprocess.Popen(  # noqa: S603
        [sys.executable, str(SERVER), str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    # ⚠️⚠️⚠️ **The pipe is drained continuously, and not draining it was a deadlock that took a day to
    # find.** The server writes one line per request. A `PIPE` nobody reads fills its operating-system
    # buffer — 64 KB on Windows, about a thousand of these lines — and the *server* then blocks inside
    # `write()` on its next request and stops answering. The browser waits forever for a response, the
    # suite never finishes, and `communicate()` in the teardown reads the pipe only after the run it
    # just killed.
    #
    # **The symptoms were a perfect disguise.** It looked like a defect in whichever test happened to
    # be running at the thousandth request, so it *moved* when tests were added or removed; it did not
    # reproduce in an ordinary browser, whose server was writing to a terminal; and every isolated
    # probe passed, because a hundred requests never fill a buffer. `docs/reviews/todo.md` records the
    # whole chase, and the wrong conclusion it nearly reached: that the suite needed splitting across
    # two pages. **That would have moved the ceiling, not raised the floor** — the next thousand
    # requests would have hit the same wall.
    #
    # ⚠️ **Discarding the output is not the fix and was the previous defect** (v36-P3-11): both streams
    # went to `DEVNULL`, so a stolen port or a crash inside `dev_server.py` presented as a bare
    # `ERR_CONNECTION_REFUSED` with the one explanation thrown away. Keeping it *and* reading it is
    # what neither version did.
    #
    # ⚠️ A bounded deque rather than a list: the teardown prints the last twenty lines, so an unbounded
    # one would hold a hundred thousand strings to throw away all but twenty.
    log: deque[str] = deque(maxlen=LOG_LINES_KEPT)
    reader = threading.Thread(target=_drain, args=(server, log), daemon=True)
    reader.start()
    console: list[str] = []
    # ⚠️ Set before every failing exit and read in the `finally`. The server's own log is
    # diagnosis: printing it on a green run is noise, and noise is how a report stops being read.
    trouble = False
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
            except Exception:
                trouble = True
                print("the browser suite never finished — no window.__results after "
                      f"{READY_TIMEOUT_MS // 1000}s. The console said:")
                print("\n".join(console) or "  (nothing)")
                # ⚠️⚠️ **Where it stopped, because *it did not finish* names no test.** On 2026-08-23
                # this reported a silent timeout on a suite that ran to completion in an ordinary
                # browser, and with an empty console the message reads exactly like a module that
                # failed to load — which sent the diagnosis in the wrong direction for an hour. The
                # page renders a line per test; the last of them is the one that hung, and printing it
                # is the difference between a diagnosis and a bisect.
                # ⚠⚠ **Every one of these is guarded, because a wedged page makes `page.evaluate` block
                # with no timeout of its own.** The first version was not, and on a page whose JavaScript
                # thread never yielded the *reporter* hung -- so a fifteen-minute timeout produced no
                # output at all and looked like a run that was still going. **An instrument that can hang
                # on the failure it exists to describe is worse than no instrument**, because it removes
                # the timeout's own signal.
                for what, expression in (
                    ("still running", "window.__running"),
                    (
                        "rendered, last first",
                        (
                            "document.body.innerText.split(String.fromCharCode(10))"
                            ".map(s => s.trim()).filter(Boolean).slice(-6).reverse()"
                        ),
                    ),
                ):
                    try:
                        print(f"  {what}: {page.evaluate(expression, timeout=10_000)}")
                    except Exception:
                        print(f"  {what}: the page did not answer, so its JavaScript thread is blocked")
                return 1

            if page.evaluate("window.__results === undefined"):
                trouble = True
                print("the browser suite died before it could run. The console said:")
                print("\n".join(console) or "  (nothing)")
                return 1

            results = page.evaluate("window.__results")
            # ⚠️ **A page error after the results are set is still a page error.** (v36-P3-11) The
            # docstring calls one fatal; the check happened only while waiting, so an exception thrown
            # during teardown — or by anything the suite kicked off and did not await — was collected
            # into `console` and then ignored, and the run reported the passes it had.
            if page.evaluate("window.__fatal === 1"):
                trouble = True
                print("the page raised after the suite finished. The console said:")
                print("\n".join(console) or "  (nothing)")
                browser.close()
                return 1
            browser.close()
    except BaseException:
        # A crash on the way out is exactly when the server's log is worth having.
        trouble = True
        raise
    finally:
        _stop(server, log, explain=trouble)

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
