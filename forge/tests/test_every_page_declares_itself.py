"""Every served page carries the tags a crawler and a link preview read, and they match the catalogue.

⚠️⚠️ **The urgent half is the preview, not the search result.** `navigator.share` sends the image and a
URL together, and WhatsApp, X and iMessage fetch that URL server-side to build a card. With no
`og:title`, `og:description` or `og:image` the card is a bare domain — so every share sent was carrying a
verified image beside an empty link. G3 proved the image survives the trip; nothing had looked at the
other half of the same message.

⚠️⚠️ **These tags are STATIC in the markup, and that is the whole point.** `serve/ui/phone/head.js`
sets the same strings at runtime and its own docstring names the gap it cannot close: *a crawler that
does not execute JavaScript sees no title and no description.* A scraper is exactly that crawler.

⚠️ **Which reintroduces the defect `applyHead` was written to remove** — the title lived in three HTML
files and the catalogue, four copies of one user-facing string, and C11 is mandatory from day one. It is
two places again and **this file is the something that checks they agree**. The catalogue stays the
source; the markup is a copy with a guard over it, which is the trade this project accepts when the
copy cannot be avoided.

⚠️ Parsed rather than grepped. A `<title>` inside an HTML comment is not a title, and a test that counts
substrings cannot tell the difference -- which it had to, because one of these files documents its own
history in a comment.
"""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PAGES = _ROOT / "serve" / "ui" / "phone"
_CATALOGUE = _ROOT / "serve" / "engine" / "strings.js"

SITE = "https://boxscorepuzzle.com"

REQUIRED_META = ("description", "twitter:card", "twitter:title", "twitter:description", "twitter:image")
REQUIRED_OG = ("og:type", "og:title", "og:description", "og:url", "og:image", "og:image:width", "og:image:height")

NOINDEXED = {"play.html", "today.html"}
"""The two pages that must not be indexed, and the reason is a constraint rather than a difficulty.

§7 keeps the teams and the date out of the URL, which is why a puzzle id is opaque; §9 sells the archive,
which is why only today's and yesterday's packages are on a public path at all. **An indexed `/p/<id>` is
a permanent, crawlable address for a puzzle meant to be one day old and then sold.** `/today` is a
redirect with no content of its own, so an indexed one is a search result leading to a page nobody wrote.
"""


class _Head(HTMLParser):
    """Title, metas and links out of a real parse."""

    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._in_title = False
        self.meta: dict[str, str] = {}
        self.links: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: (value or "") for name, value in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = values.get("name") or values.get("property")
            if key:
                self.meta[key] = values.get("content", "")
        elif tag == "link":
            rel = values.get("rel", "")
            if rel:
                self.links[rel] = values.get("href", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def _head(page: Path) -> _Head:
    parser = _Head()
    parser.feed(page.read_text(encoding="utf-8"))
    return parser


def _catalogue(key: str) -> str:
    """The catalogue's value. ⚠️ Raises rather than defaulting: an empty string would compare equal to a
    page that declares nothing, so the check would pass on the state it exists to catch."""
    needle = f'"{key}":'
    for line in _CATALOGUE.read_text(encoding="utf-8").split("\n"):
        stripped = line.strip()
        if stripped.startswith(needle):
            return json.loads(stripped[len(needle) :].strip().rstrip(","))
    message = f"{key} is not in the catalogue"
    raise AssertionError(message)


def _served() -> list[Path]:
    """The pages nginx answers with. Found by shape, not by a list kept here."""
    return sorted(_PAGES.glob("*.html"))


def test_the_sweep_finds_pages_to_check() -> None:
    """⚠️⚠️ A check over an empty set passes forever, and this project built one an hour after writing
    that down. Assert the subject is there before judging it."""
    pages = _served()
    assert pages, f"no .html under {_PAGES}; every test below would pass over nothing"
    assert len(pages) >= 4, f"expected the four shipped pages, found {[p.name for p in pages]}"


@pytest.mark.parametrize("page", _served(), ids=lambda p: p.name)
def test_the_page_has_a_title_and_a_description(page: Path) -> None:
    head = _head(page)
    assert head.title.strip(), f"{page.name} ships no title; a search result then shows whatever Google infers"
    assert head.meta.get("description", "").strip(), f"{page.name} ships no description"


@pytest.mark.parametrize("page", _served(), ids=lambda p: p.name)
def test_the_page_declares_a_canonical_address(page: Path) -> None:
    """⚠️ `www` 301s to the apex at the edge, and this is the same statement inside the document. Two
    mechanisms for one fact, and the redirect is the one that acts -- this is what a scraper reads when
    it has already followed one."""
    canonical = _head(page).links.get("canonical", "")
    assert canonical.startswith(SITE), f"{page.name} declares canonical {canonical!r}"


@pytest.mark.parametrize("page", _served(), ids=lambda p: p.name)
def test_the_page_carries_a_link_preview(page: Path) -> None:
    """The half G3 did not test: the URL that travels beside the verified image."""
    head = _head(page)
    for key in REQUIRED_OG + REQUIRED_META:
        assert head.meta.get(key, "").strip(), f"{page.name} is missing {key}"
    assert head.meta["og:image"] == f"{SITE}/og-image.png"
    assert head.meta["og:image"] == head.meta["twitter:image"], "two previews of one page"


@pytest.mark.parametrize("page", _served(), ids=lambda p: p.name)
def test_the_declared_strings_are_the_catalogue_s(page: Path) -> None:
    """⚠️⚠️ **The guard that lets the markup hold a copy at all.** Without it this is four HTML files and
    a catalogue spelling one user-facing string, which is the C11 defect `applyHead` was written to
    remove."""
    head = _head(page)
    expected = {
        "index.html": _catalogue("page.landing.title"),
        "tutorial.html": _catalogue("page.tutorial.title"),
    }.get(page.name, _catalogue("page.landing.title"))

    assert head.title.strip() == expected, f"{page.name} titles itself outside the catalogue"
    assert head.meta["og:title"] == head.title.strip(), "the preview and the tab disagree about the page"
    assert head.meta["twitter:title"] == head.title.strip()
    assert head.meta["og:description"] == head.meta["description"]


@pytest.mark.parametrize("page", _served(), ids=lambda p: p.name)
def test_only_the_two_addresses_that_must_not_be_indexed_are_noindexed(page: Path) -> None:
    """⚠️ Both directions. A missing `noindex` puts a sold archive on a crawlable URL; a stray one takes
    the landing page out of the index, which is the whole funnel."""
    robots = _head(page).meta.get("robots", "")
    if page.name in NOINDEXED:
        assert "noindex" in robots, f"{page.name} would be indexed; see this module's NOINDEXED"
    else:
        assert "noindex" not in robots, f"{page.name} is noindexed and it is the indexable site"


def test_robots_and_the_sitemap_agree_with_the_pages() -> None:
    """⚠️ `robots.txt` disallows paths that also carry `noindex`, and the duplication is deliberate: a
    crawler that never fetches a page never reads its meta robots."""
    robots = (_ROOT / "serve" / "robots.txt").read_text(encoding="utf-8")
    sitemap = (_ROOT / "serve" / "sitemap.xml").read_text(encoding="utf-8")

    assert "Disallow: /p/" in robots, "a puzzle URL would be crawled before its markup said not to"
    assert f"Sitemap: {SITE}/sitemap.xml" in robots

    listed = set(re.findall(r"<loc>([^<]+)</loc>", sitemap))
    assert listed == {f"{SITE}/", f"{SITE}/tutorial"}, f"the sitemap lists {sorted(listed)}"
    # ⚠️ The addresses, not the file. The first version searched the whole text and failed on the
    # sitemap's own comment explaining why `/p/` is absent -- a check that cannot tell a URL from a
    # sentence about URLs.
    assert not any("/p/" in address for address in listed), "a puzzle has no permanent public address"


def test_the_preview_image_and_the_marks_exist_and_are_not_empty() -> None:
    """⚠️⚠️ Size-checked, because this is exactly how the favicon failed. A `--` inside an XML comment
    made the SVG unparseable, the write reported success, and the rasteriser turned Chromium's error
    page into a 98-byte icon. **The file existing said nothing.**"""
    for name, floor in (
        ("og-image.png", 10_000),
        ("favicon.svg", 200),
        ("favicon.ico", 200),
        ("apple-touch-icon.png", 500),
    ):
        asset = _ROOT / "serve" / name
        assert asset.is_file(), f"{name} is missing and every page links to it"
        assert asset.stat().st_size > floor, f"{name} is {asset.stat().st_size} bytes, which is not a {name}"
