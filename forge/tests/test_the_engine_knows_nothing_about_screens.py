"""`serve/engine/` does not know what a screen is.

⚠️⚠️ **This is `serve-brief.md`'s central claim, and beta 1 is the one milestone that could have made it
false.** *One puzzle and three interfaces, a core that knows nothing about screens.* Beta 0 built the
first interface and the core under it, so the claim was unfalsifiable until a second interface arrived.

**It survived.** Both beta 1 commits touch `engine/` in zero lines, and the reason is concrete rather
than lucky: `game.js` already exposed `enter`, `clear`, `blanks` and `cells`, and `grow` in `board.js`
already concatenated and capped at two digits for the keypad. **Everything deciding what a key means
already lived in `ui/phone/`**, so the keyboard had nothing to ask the engine for.

⚠️⚠️ **The seam is clean TODAY, which is what makes this the cheapest moment to fence it.** After the
first viewport query lands in `engine/`, this test cannot be added without first removing it — and by
then somebody has a reason for it being there.

## ⚠️⚠️ What this can and cannot see

**It is a list of terms, and a list misses the next one somebody invents.** That is the hand-maintained
shape this repository met four times on 2026-08-26 alone: three `.gitignore` lines, `keep`'s teardown
table list, `PAGES` in the C11 guard, `PLAYER_MODULES` at five of fifteen. **This is one more of them,
and saying so is worth more than letting it read as the class being closed.**

**What it covers:** the vocabulary a screen is described with — viewport and window dimensions, media
queries and `matchMedia`, pointer and touch capability, device pixel ratio, orientation, and the layout
words a core has no business knowing. Anything an engine module would plausibly reach for *first*.

**What it cannot cover:** a screen concern expressed in terms it does not know. `engine/` could take a
`columns` count from a caller, or a boolean named `compact`, and nothing here would notice — because
*being about a screen* is a property of intent, not of the text. **That residual is the same one
`CLAUDE.md` records for the near-neighbour class**, and it is not closed by any list.

⚠️ It is also not `DOM-free`: `store.js` reaches for `localStorage`, `device.js` for `crypto`,
`clock.js` for `document` visibility, `report.js` for `window.onerror`. Those are **platform**, not
**screen**, and forbidding them would be a different and wrong rule.

⚠️ **And it reads code, not comments** -- see `_code`. The first version read both and four legitimate
comments turned it red, one of which had predicted this milestone correctly.

⚠️ **One line is exempt and it is marked where it lives**, not listed here -- see `MARKER`. `report.js`
records the viewport into a client error report, which is recording what the screen was rather than
deciding because of it, and no list of terms can tell those apart.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_ENGINE = _ROOT / "serve" / "engine"

_SCREEN_TERMS = (
    # How wide, how tall, and where the edges are.
    "innerWidth",
    "innerHeight",
    "outerWidth",
    "outerHeight",
    "clientWidth",
    "clientHeight",
    "offsetWidth",
    "offsetHeight",
    "getBoundingClientRect",
    "screen.width",
    "screen.height",
    # Asking the screen a question directly.
    "matchMedia",
    "@media",
    "prefers-color-scheme",
    "min-width",
    "max-width",
    "devicePixelRatio",
    "orientation",
    # What kind of input the hardware has. `ui/` may ask; the engine may not.
    "pointer: fine",
    "pointer: coarse",
    "any-pointer",
    "hover:",
    "maxTouchPoints",
    # The words this product uses for its own layouts.
    "desktop",
    "mobile",
    "tablet",
    "breakpoint",
    "viewport",
)
"""The vocabulary a screen is described with. ⚠️ A list, with the residual named in the module docstring."""

MARKER = "screen: recorded, not decided"
"""What exempts a line, written **at the line** rather than in a list here.

⚠️⚠️ **There is exactly one, and the distinction it draws is the real rule.** `report.js` puts
`innerWidth x innerHeight` into a client error report: a rendering fault is unreproducible without
knowing how big the window was, and `client_errors` has the column. **Recording what the screen was is
not deciding because of it**, and this test's list of terms cannot tell those apart.

⚠️ **Exempting by filename would have been the hand-maintained shape again** -- a list in the test that
nobody reading `report.js` would ever see. At the line, the exemption is read by whoever reads the code,
and adding one means writing the sentence next to what it excuses.

⚠️ **It is not a silencer.** A marker on a line that *branches* on the screen would be a lie, and no test
can catch that -- which is the same residual the module docstring names. What it buys is that the lie has
to be written down.
"""


def _sources() -> list[Path]:
    return sorted(path for path in _ENGINE.glob("*.js") if path.is_file())


def _code(text: str) -> list[tuple[int, str]]:
    """The lines that are code, numbered. **Comment lines are dropped, and the first version kept them.**

    ⚠️⚠️ **That version said comments were read *deliberately* — a line reasoning about desktop inside the
    engine is the decision arriving — and its first run refuted it.** Four legitimate comments fired:
    `clock.js` explaining that a session *survives on a desktop and vanishes on the device the board was
    designed for*; `game.js` noting that *tablet and desktop are planned*; and one that had **anticipated
    this milestone correctly** — *the phone has no keyboard traversal yet; that arrives with desktop*.

    **Forbidding those is forbidding the engine to explain why it is screen-agnostic**, which is the
    opposite of what this guard is for. A comment about desktop is reasoning; code touching a viewport is
    the defect.

    ⚠️ Whole comment lines only, never truncating at an inline `//`: chopping a code line at the first
    slash would silently hide anything after it, including a term this is looking for.
    """
    lines = []
    inside = False
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if inside:
            if "*/" in stripped:
                inside = False
            continue
        if stripped.startswith("/*"):
            inside = "*/" not in stripped
            continue
        if stripped.startswith(("//", "*")):
            continue
        lines.append((number, line))
    return lines


def test_the_sweep_finds_engine_modules_to_check() -> None:
    """⚠️ A check over an empty set passes for ever. This asserts the subject exists before judging it.

    A renamed directory or a changed glob would otherwise make this file report a clean seam about
    nothing at all -- which is the empty-result shape recorded in `CLAUDE.md` as reading like a finding.
    """
    found = _sources()

    assert len(found) > 5, f"only {len(found)} modules under {_ENGINE}; this would pass over almost nothing"
    assert any(path.name == "game.js" for path in found), "game.js is missing; the glob is looking elsewhere"


def test_no_engine_module_asks_about_the_screen() -> None:
    """⚠️ Seen red by putting `if (window.innerWidth > 800)` into `game.js`: it names the file and the term.

    The message says which module and which word, because *something in the engine mentions screens* is
    not actionable and *`game.js:212` says `innerWidth`* is.
    """
    offenders = []
    for path in _sources():
        for number, line in _code(path.read_text(encoding="utf-8")):
            if MARKER in line:
                continue
            for term in _SCREEN_TERMS:
                if re.search(rf"(?<![\w-]){re.escape(term)}", line):
                    offenders.append(f"{path.name}:{number} says {term!r}")

    assert not offenders, (
        "serve/engine/ has learnt about screens, which is serve-brief.md's central claim failing: "
        + "; ".join(offenders[:6])
        + ". If a screen genuinely belongs in the core, that is a decision to write down in the brief, "
        "not a term to slip past this test."
    )
