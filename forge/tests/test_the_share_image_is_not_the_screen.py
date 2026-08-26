"""The share image is the phone board, whatever screen it was made on.

⚠️⚠️ **The share is the only growth mechanism the product has, and G3 was closed by hand.** The image was
sent from a real phone through WhatsApp, iMessage and X and arrived intact. **A wide layout would expire
that verification with nothing saying so** -- `share-image.js` draws with `board.js`'s renderers and
inlines `board.css` whole, by design, because a second copy of the board for the image is a definition
that drifts from the first.

⚠️⚠️ **The failure is not that the image gets wider. It is that height and content come from different
rules**, and that was measured on 2026-08-26 rather than deduced. `shareImage` lays the sheet out in the
REAL document to measure it, then draws it inside an SVG, which is a **separate document with its own
375px viewport**. With a probe `@media (min-width: 800px)` in `board.css` and the page at 1440:

| | phone 375 | desktop 1440 |
|---|---|---|
| matched in the page | no | **yes** |
| matched inside the SVG | no | **no** |
| height of the produced PNG | 1864 | **2872** |
| ink across the row at 75% of the height | 710 px | **0 px** |

The boxscore drawn small at the top with blank paper below -- and it does not look broken, because
`.share-sheet`'s background stretches, so the empty part is white rather than transparent.

⚠️ **This compares the produced image, never a constant.** Asserting that `WIDTH` is 375 is the
bytes-versus-works distinction that shipped a blank page: `/p/<id>` served the right bytes and did not
work. Two viewports, one hash, and the hash is what the player receives.

⚠️ **Byte equality was confirmed before this depended on it**: four rasterisations, two at each viewport,
all `866d1fb1...` at 127466 bytes. If that ever stops holding, the fallback is (width, height, hash) --
**height alone catches the failure that matters.**
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SERVER = _ROOT / "tools" / "dev_server.py"

_PHONE = {"width": 375, "height": 812}
"""§6's board. Every number in `board.css` comes from this width."""

_DESKTOP = {"width": 1440, "height": 900}
"""Wide enough that any plausible breakpoint has fired. The point is that the image does not notice."""

_MADE_THE_IMAGE = """
async () => {
  const { shareImage } = await import("/ui/phone/share-image.js");
  const { readPackage } = await import("/engine/package.js");
  const { createGame } = await import("/engine/game.js");
  const pointer = await (await fetch("/data/puzzles/today.json")).json();
  const raw = await (await fetch(`/data/puzzles/${pointer.puzzle_id}.json`)).json();
  const puzzle = readPackage(raw);
  // ⚠️ `random` fixed: the masking picks which answers to blur, and an unseeded draw would make every
  // comparison fail for a reason that is not the one under test.
  const blob = await shareImage(puzzle, createGame(puzzle), { random: () => 0.5 });
  const buffer = await blob.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return {
    bytes: buffer.byteLength,
    sha: Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join(""),
  };
}
"""


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.fixture(scope="module")
def served(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """`serve/` over HTTP, with the server's own output kept and read.

    ⚠️⚠️ **`stdout` goes to a FILE, not to a pipe.** The server writes a line per request; into a pipe
    nobody drains, the 64 KB buffer fills and the **server** blocks inside `write()` -- v37-P1-01, the
    afternoon that presented as a test-count budget and was a plumbing fault. Discarding it was the
    defect before that (v36-P3-11), where a stolen port became a bare `ERR_CONNECTION_REFUSED` with the
    explanation thrown away. **Keeping it and reading it is what neither version did.**
    """
    pytest.importorskip("playwright.sync_api", reason="playwright is not installed in this environment")

    port = _free_port()
    log = tmp_path_factory.mktemp("share-image") / "dev-server.log"
    with log.open("w", encoding="utf-8") as sink:
        server = subprocess.Popen(  # noqa: S603
            [sys.executable, str(_SERVER), str(port)],
            stdout=sink,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        )
        try:
            base = f"http://127.0.0.1:{port}/"
            for _ in range(120):
                try:
                    # ⚠️ A real request to the thing the caller needs, not a socket connect: a bound port
                    # says the listener exists and nothing about whether it answers.
                    urllib.request.urlopen(base, timeout=1).read()
                    break
                except (OSError, urllib.error.URLError):
                    time.sleep(0.25)
            else:
                pytest.fail(f"the dev server never answered on {port}:\n{log.read_text(encoding='utf-8')[-800:]}")
            yield base
        finally:
            server.terminate()
            server.wait(timeout=20)


def _image(browser: object, base: str, viewport: dict[str, int]) -> dict[str, object]:
    """One share image, made at `viewport`. ⚠️ One per context: two big canvases at once killed the driver."""
    context = browser.new_context(viewport=viewport)  # type: ignore[attr-defined]
    try:
        page = context.new_page()
        page.goto(base, wait_until="load")
        return dict(page.evaluate(_MADE_THE_IMAGE))
    finally:
        context.close()


def test_the_share_image_is_identical_at_every_viewport(served: str) -> None:
    """⚠️ Seen red by adding `@media (min-width: 800px) { .grid td.cell { height: 80px } }` to `board.css`.

    The hashes differ and the desktop image is a third taller. That is the whole finding, as a failure.
    """
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    with sync_playwright() as play:
        browser = play.chromium.launch()
        try:
            phone = _image(browser, served, _PHONE)
            desktop = _image(browser, served, _DESKTOP)
        finally:
            browser.close()

    # ⚠️ The subject was there. A page that failed to build an image would otherwise compare two nothings
    # and agree -- the empty-result shape this repository records as reading like a finding.
    assert int(phone["bytes"]) > 2000, f"the phone image is {phone['bytes']} bytes, too small to be a board"

    assert phone["sha"] == desktop["sha"], (
        f"the share image differs by screen: {_PHONE['width']}px gave {phone['bytes']} bytes "
        f"({str(phone['sha'])[:16]}) and {_DESKTOP['width']}px gave {desktop['bytes']} bytes "
        f"({str(desktop['sha'])[:16]}). A wide layout has reached the sheet -- see wide.js, and use "
        f"#app.wide rather than a media query."
    )


_MEASURED_THE_BOARD = """
() => {
  const app = document.querySelector("#app") ?? document.querySelector(".landing");
  const board = document.querySelector(".grid") ?? document.querySelector(".linescore table");
  return {
    app: app ? Math.round(app.getBoundingClientRect().width) : null,
    board: board ? Math.round(board.getBoundingClientRect().width) : null,
    document: document.documentElement.clientWidth,
    scrolls_sideways: document.documentElement.scrollWidth > document.documentElement.clientWidth,
  };
}
"""


def test_the_board_does_not_stretch_at_a_desktop_viewport(served: str) -> None:
    """⚠️⚠️ **Section 6: the board is identical on all screens. Desktop gets more whitespace, not more content.**

    `docs/beta-0.md` measured this once by hand at 1400x900 and found it correct -- and recorded that
    **nothing guarded it**, with the width spelled by hand in three stylesheets. This is the guard, and it
    reads the RENDERED box rather than the stylesheet: asserting a token says 375 is the
    bytes-versus-works distinction that shipped a blank page.

    ⚠️ Seen red by setting `--board-width: 900px`, which is also what A's token replaced.
    """
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    with sync_playwright() as play:
        browser = play.chromium.launch()
        try:
            measured = {}
            for label, viewport in (("phone", _PHONE), ("desktop", _DESKTOP)):
                context = browser.new_context(viewport=viewport)
                try:
                    page = context.new_page()
                    page.goto(f"{served}today", wait_until="load")
                    page.wait_for_selector(".grid", timeout=20_000)
                    measured[label] = dict(page.evaluate(_MEASURED_THE_BOARD))
                finally:
                    context.close()
        finally:
            browser.close()

    # The subject was there: a page that drew no board would agree with itself about nothing.
    assert measured["phone"]["board"], f"no board rendered at {_PHONE['width']}px"

    assert measured["desktop"]["app"] == measured["phone"]["app"], (
        f"the board stretched: {measured['phone']['app']}px at {_PHONE['width']} and "
        f"{measured['desktop']['app']}px at {_DESKTOP['width']}. Section 6 gives desktop whitespace, "
        f"not width."
    )
    assert measured["desktop"]["board"] == measured["phone"]["board"], (
        f"the grid itself differs: {measured['phone']['board']}px against {measured['desktop']['board']}px"
    )
    # ⚠️ And it must not have bought that by overflowing. A board that keeps its width while the document
    # scrolls sideways is a board that does not fit, which is the failure this is meant to prevent.
    assert not measured["desktop"]["scrolls_sideways"], "the desktop page scrolls sideways"
