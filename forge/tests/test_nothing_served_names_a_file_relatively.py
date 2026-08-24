"""No served page names an asset relatively, and no route constant is a filename.

⚠️⚠️ **This covers two instances and NOT the class.** The class — a test asserting a property that is
necessary but not sufficient, and true in the broken state — **is not mechanically detectable**:
catching it requires knowing what the test meant to assert, and that is intent. `CLAUDE.md` records it
as a finding rather than as a gap. **This file is not that check and must not be read as closing it.**

What it does close is the pair that actually happened, both of which *are* decidable:

- **`play.html` named `main.js`.** Served at `/p/<id>`, that resolves to `/p/main.js` — answered with
  the page itself by a prefix rewrite, so the browser got HTML where it asked for a module, refused it
  on MIME, and drew a blank screen on the canonical URL.
- **`ROUTES` held `play.html`, `index.html`, `tutorial.html`.** Linked from `/`, those resolve to
  `/play.html` and `/tutorial.html`: **both landing buttons dead**, on the address every visit lands at.

⚠️ **Proved to fire before being believed** — with the filenames restored,
`test_nginx_serves_what_is_declared.py` reports *the client links to play.html and nginx answers 400*
and the second case here goes red. A guard that has never been seen red is indistinguishable from one
that cannot be.
"""

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PHONE = _ROOT / "serve" / "ui" / "phone"

_NAMED = re.compile(r'(?:href|src)="(?!/|https?:|#|data:)([^"]+)"')
"""An asset named by a page. Absolute, protocol and fragment references are somebody else's problem and
are correct by construction: what this looks for is a **bare relative** name, which resolves against
whichever address served the page."""


def _pages() -> list[Path]:
    found = sorted(_PHONE.glob("*.html"))
    assert found, f"no pages under {_PHONE}; this file would sweep nothing"
    return found


@pytest.mark.parametrize("page", _pages(), ids=lambda path: path.name)
def test_a_page_names_its_assets_absolutely(page: Path) -> None:
    """⚠️ Per page rather than over all of them, so a failure names the file rather than the set."""
    relative = _NAMED.findall(page.read_text(encoding="utf-8"))

    assert not relative, (
        f"{page.name} names {relative} relatively. A page served at more than one address cannot: "
        f"from /p/<id> those resolve under /p/, which is not where they are."
    )


def test_the_sweep_can_see_a_relative_name() -> None:
    """⚠️⚠️ **The check on the check.** A regular expression that stopped matching would leave every case
    above passing over an empty list, which is a guard that cannot fire — the shape this project records
    most. This gives it the exact string that was wrong and requires it to be caught."""
    assert _NAMED.findall('<script type="module" src="main.js"></script>') == ["main.js"]
    assert _NAMED.findall('<link rel="stylesheet" href="/ui/phone/tokens.css">') == []


def test_no_route_constant_is_a_filename() -> None:
    """`ROUTES` in `daily.js` is what the pages link to, and filenames there are dead links.

    ⚠️ Read out of the source rather than imported: this is a Python suite and the constant lives in a
    browser module. The parse failing is a failure — `assert found is not None` — because a silent
    reshape would leave this asserting nothing.
    """
    source = (_PHONE / "daily.js").read_text(encoding="utf-8")
    found = re.search(r"export const ROUTES = \{([^}]*)\}", source)
    assert found is not None, "ROUTES is not where this expects it; the shape changed and the guard is blind"

    urls = re.findall(r'"([^"]+)"', found.group(1))
    assert urls, "ROUTES parsed to nothing, so this proves nothing"
    for url in urls:
        assert url.startswith("/"), f"ROUTES names {url}, which resolves against whatever page links it"
        assert not url.endswith(".html"), f"ROUTES names {url}: an implementation path, not a canonical URL"
