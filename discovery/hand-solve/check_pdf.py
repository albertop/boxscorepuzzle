"""Does the printed page say what it should and nothing it should not?

⚠️ **The previous version of this check decompressed 0 of 50 streams and reported "no leaks".** Both
of its answers happened to be true, which is worse than being wrong: a check that cannot read its
input and says "clean" is the absence of a check reading as the presence of a passing one, which
CLAUDE.md names outright.

It matters more on this pack than on any before it, because there is now **one number that must be on
the page** — the 1-6 difficulty scale — and **several that must not**: the stall count, the chain
length, the era, the teams, the game identifier. A check that cannot tell those apart is worse than
none, because it would bless a pack that anchors every rating it collects.

So it fails closed. If a page cannot be decompressed, that is an error and not a pass.

Run from anywhere: `python check_pdf.py boards.pdf key.csv`
"""

import base64
import csv
import re
import sys
import zlib
from pathlib import Path

REQUIRED = ("How hard was it?", "How many times did you have to stop", "PA = AB + BB")
"""What every page must carry. The scale, the stall question, and the formula strip."""

FORBIDDEN_WORDS = ("chain", "stall", "target", "uncertified", "certified", "difficulty:")
"""Words that would name the difficulty on a page that must not name it."""


def pages(path: Path) -> list[str]:
    """Every content stream, decoded. Raises rather than skipping what it cannot read.

    ⚠️ **The filters are stacked and that is why the first version read nothing.** reportlab
    writes `/Filter [ /ASCII85Decode /FlateDecode ]`, so a stream must be un-base85ed *before*
    it is inflated. Trying zlib alone failed on every one of them, and the check said clean.
    """
    raw = path.read_bytes()
    streams = re.findall(rb"stream[\r\n]{1,2}(.*?)endstream", raw, re.S)
    if not streams:
        message = f"{path.name}: found no content streams at all, so nothing was checked"
        raise SystemExit(message)
    text: list[str] = []
    unreadable: list[str] = []
    for index, stream in enumerate(streams):
        body = stream.strip()
        try:
            text.append(zlib.decompress(base64.a85decode(body, adobe=True)).decode("latin-1"))
        except (zlib.error, ValueError) as error:
            try:
                text.append(zlib.decompress(body).decode("latin-1"))
            except zlib.error:
                unreadable.append(f"stream {index}: {error}")
    if unreadable:
        # Fail closed. A stream that cannot be read might be the one carrying the leak.
        message = f"{path.name}: {len(unreadable)} of {len(streams)} unreadable - " + unreadable[0]
        raise SystemExit(message)
    return text


def shown(page: str) -> str:
    """The text a reader sees, pulled out of the PDF drawing operators."""
    return " ".join(match.decode("latin-1") if isinstance(match, bytes) else match for match in re.findall(r"\((?:[^()\\]|\\.)*\)", page))


def check(pdf: Path, key: Path | None) -> None:
    found = pages(pdf)
    board_pages = [page for page in found if "Board " in shown(page)]
    if not board_pages:
        message = f"{pdf.name}: decompressed {len(found)} streams and none of them is a board page"
        raise SystemExit(message)
    print(f"{pdf.name}: {len(found)} streams read, {len(board_pages)} board pages")

    problems: list[str] = []
    for index, page in enumerate(board_pages, start=1):
        visible = shown(page)
        for phrase in REQUIRED:
            if phrase not in visible:
                problems.append(f"page {index} is missing {phrase!r}")
        lowered = visible.lower()
        for word in FORBIDDEN_WORDS:
            if word in lowered:
                problems.append(f"page {index} names {word!r}, which anchors the rating")
        if re.search(r"\b(19|20)\d{2}\b", visible):
            problems.append(f"page {index} shows a year, which gives away the era")

    if key is not None and key.exists():
        # The key must hold what the page must not, or the afternoon cannot be read afterwards.
        with key.open(encoding="utf-8") as handle:
            columns = next(csv.reader(handle))
        for column in ("stalls", "board"):
            if column not in columns:
                problems.append(f"the key has no {column!r} column, so the ratings cannot be compared")

    if problems:
        raise SystemExit("\n".join(problems))
    print(f"every page carries {len(REQUIRED)} required items and names no difficulty")


def main() -> None:
    if len(sys.argv) < 2:
        message = "usage: check_pdf.py boards.pdf [key.csv]"
        raise SystemExit(message)
    check(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else None)


if __name__ == "__main__":
    main()
