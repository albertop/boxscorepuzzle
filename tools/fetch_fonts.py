"""Download both candidate faces, subset to the characters this board actually renders.

⚠️ **Self-hosted, never linked.** §23 requires the day's puzzle to be playable with the backend down,
and a webfont fetched from a third party is a dependency in the play path — a board that falls back to
a different face is a board whose columns no longer line up, which is the one thing a grid of numbers
cannot survive.

⚠️ **The character set is derived, not typed.** It is read out of `serve/engine/strings.js` and the
labels the packages actually carry, plus the digits and the slot-reference grammar. A hand-written list
is a second copy of the catalogue, and it goes stale the first time a string is added — which shows up
as one glyph in the fallback face, in a grid where a different width is exactly what breaks.
"""

import json
import pathlib
import re
import string
import urllib.parse
import urllib.request

OUT = pathlib.Path("serve/ui/fonts")
OUT.mkdir(parents=True, exist_ok=True)
AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

FAMILIES = {
    # ⚠️ The plain name. Pre-encoding it as `Roboto+Condensed` and then handing that to `urlencode`
    # turns the `+` into `%2B`, so the request asks for a family literally called "Roboto+Condensed"
    # and Google answers 400. One encoding, in one place.
    #
    # ⚠️ Roboto Condensed was the other candidate and lost on the character the instruction named:
    # it draws `1` as a bare stem with an angled flag and no foot. Checked on screen rather than
    # argued — all three weights had loaded and the digit's advance differed from the fallback's, so
    # the bare `1` is the face's design and not a webfont that failed to arrive.
    "plex-condensed": "IBM Plex Sans Condensed",
}
WEIGHTS = (400, 600, 700)


def characters() -> str:
    used = set(string.digits)
    # Every user-facing string in the catalogue.
    catalogue = pathlib.Path("serve/engine/strings.js").read_text(encoding="utf-8")
    used.update("".join(re.findall(r':\s*"([^"]*)"', catalogue)))
    # Every label and slot reference the real packages carry.
    for path in pathlib.Path("serve/data/puzzles").rglob("*.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if "labels" not in raw:
            continue
        for value in raw["labels"] + raw["pitcher_labels"] + raw["slot_references"]:
            used.update(value)
    # The grammar, not just today's instances: any position abbreviation is upper case, a shared slot
    # takes a lower-case suffix, and the footnote line multiplies with ×.
    used.update(string.ascii_uppercase + string.ascii_lowercase + " :,.#?×+-()")
    return "".join(sorted(used))


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": AGENT})  # noqa: S310
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return response.read()


text = characters()
print(f"{len(text)} characters: {text!r}")

rules = []
for slug, family in FAMILIES.items():
    for weight in WEIGHTS:
        query = urllib.parse.urlencode({"family": f"{family}:wght@{weight}", "text": text, "display": "block"})
        css = get(f"https://fonts.googleapis.com/css2?{query}").decode("utf-8")
        # ⚠️ No `.woff2` extension to anchor on: a subset response points at `/l/font?kit=...`, and a
        # pattern that required the suffix matched nothing and blew up on `None`. The format is in the
        # `format('woff2')` that follows, which is what to assert on.
        found = re.search(r"url\((https://[^)]+)\)\s*format\('woff2'\)", css)
        assert found is not None, f"no woff2 in the response for {family} {weight}: {css[:200]}"
        url = found.group(1)
        name = f"{slug}-{weight}.woff2"
        (OUT / name).write_bytes(get(url))
        rules.append(
            f"@font-face {{{chr(10)}"
            f"  font-family: '{family}';{chr(10)}"
            f"  font-style: normal;{chr(10)}"
            f"  font-weight: {weight};{chr(10)}"
            # `block`, not `swap`: a moment of invisible text beats a board that lays out in the
            # fallback's metrics and then jumps. The files are local and a few kilobytes, so it is short.
            f"  font-display: block;{chr(10)}"
            f"  src: url('../fonts/{name}') format('woff2');{chr(10)}"
            f"}}{chr(10)}"
        )
        print(f"  {name}  {(OUT / name).stat().st_size / 1024:.1f} KB")

header = (
    "/* Both faces are SIL Open Font License 1.1, which permits redistribution with the site — checked"
    + chr(10)
    + "   before shipping, because this product charges money and a licence that forbids that forbids"
    + chr(10)
    + "   launch. Subset by `tools/fetch_fonts.py` to the characters the catalogue and the packages use."
    + chr(10)
    + "   Served from here and never linked: see the note in board.css. */"
    + chr(10)
    + chr(10)
)
pathlib.Path("serve/ui/phone/fonts.css").write_text(header + chr(10).join(rules), encoding="utf-8", newline=chr(10))
print(f"total {sum(f.stat().st_size for f in OUT.glob('*.woff2')) / 1024:.1f} KB")
