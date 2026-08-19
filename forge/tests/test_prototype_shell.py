"""A prototype that claims to judge the board at 375px has to fit in 375px.

⚠️ **Each of these needed about 405.** A 375px content-box section plus borders, inside a body with
14px of padding on each side. On a real phone that is horizontal overflow or a page the browser
shrinks — and a nominal 44px cell then renders below the touch target the prototype exists to
validate. With no viewport meta a mobile browser lays out at its wider default and scales everything
down, which breaks the same assumption more quietly.

The width budget in §6 is the whole reason these pages exist. A page that cannot honour it is not
evidence about the board; it is evidence about itself.
"""

from pathlib import Path

import pytest

_PROTOTYPES = sorted((Path(__file__).resolve().parents[2] / "discovery" / "board-prototype").glob("*-sample.html"))


def _found() -> list[Path]:
    assert _PROTOTYPES, "no prototypes found; the path in this test is wrong"
    return _PROTOTYPES


class TestEveryPrototypeIsAMobilePage:
    @pytest.mark.parametrize("path", _found(), ids=lambda path: path.name)
    def test_it_has_a_document_shell(self, path: Path) -> None:
        assert path.read_text(encoding="utf-8").lstrip().startswith("<!doctype html>")

    @pytest.mark.parametrize("path", _found(), ids=lambda path: path.name)
    def test_it_declares_the_viewport(self, path: Path) -> None:
        # Without this a mobile browser uses its wider default layout viewport and scales the page,
        # so every pixel measurement the prototype is making becomes a different number.
        assert "width=device-width" in path.read_text(encoding="utf-8")

    @pytest.mark.parametrize("path", _found(), ids=lambda path: path.name)
    def test_its_boxes_include_their_own_borders(self, path: Path) -> None:
        # The 375px claim was for content, and the borders sat outside it.
        assert "box-sizing:border-box" in path.read_text(encoding="utf-8")

    @pytest.mark.parametrize("path", _found(), ids=lambda path: path.name)
    def test_the_page_cannot_scroll_sideways(self, path: Path) -> None:
        assert "overflow-x:hidden" in path.read_text(encoding="utf-8")

    def test_the_check_can_fire(self, tmp_path: Path) -> None:
        # A guard over a directory that finds nothing is indistinguishable from one that cannot look.
        bare = tmp_path / "bare-sample.html"
        bare.write_text("<style>section{width:375px}</style><section>board</section>", encoding="utf-8")

        assert not bare.read_text(encoding="utf-8").lstrip().startswith("<!doctype html>")
        assert "width=device-width" not in bare.read_text(encoding="utf-8")


SUFFIXED = r">([A-Z0-9]{1,3}-\d+)<"
r"""⚠️ This was `-\d`, a single digit, so `P-10` and `PH-12` passed a guard meant to reject every
numbered label — and those are within the shape of the old convention, most likely in exactly the long
substitution-heavy games where the grouping matters. One historical file cannot define the adversarial
space, so the can-it-fire case is synthetic and carries both widths."""


class TestActivePrototypesUseTheCurrentVisualLanguage:
    """A prototype judged side by side must not show a convention the product dropped.

    ⚠️ `substitute-grouping-sample.html` rendered `PH-4`, `3B-2`, `P-3` after the suffix was removed,
    and nothing on the page said so. A note in conversation is not a guard: someone evaluating grouping
    or spacing would have been comparing against a visual language that no longer exists, and could
    copy it back into a renderer. It is archived now, behind a banner, outside this glob.

    Shell checks cannot catch this — the page was perfectly well formed. **This is a domain check.**
    """

    @pytest.mark.parametrize("path", _found(), ids=lambda path: path.name)
    def test_no_active_prototype_shows_a_suffixed_position(self, path: Path) -> None:
        import re  # noqa: PLC0415

        found = sorted(set(re.findall(SUFFIXED, path.read_text(encoding="utf-8"))))

        assert not found, f"{path.name} renders suffixed labels {found}; labels are bare positions"

    def test_it_rejects_a_two_digit_suffix(self) -> None:
        # The gap: a single-digit pattern is green on the numbers a long game actually produces.
        import re  # noqa: PLC0415

        page = "<td>PH-2</td><td>P-10</td><td>PH-12</td><td>CF</td>"

        assert sorted(set(re.findall(SUFFIXED, page))) == ["P-10", "PH-12", "PH-2"]

    def test_it_accepts_a_page_with_bare_positions(self) -> None:
        # A pattern that matched everything would satisfy the two tests above.
        import re  # noqa: PLC0415

        assert not re.findall(SUFFIXED, "<td>CF</td><td>SS</td><td>P</td><td>9b</td>")

    def test_the_archived_one_would_be_rejected(self) -> None:
        # The can-it-fire case, and it is a real file rather than a fixture: the page that prompted
        # this check must still fail it, or the check is matching nothing.
        import re  # noqa: PLC0415

        archived = _PROTOTYPES[0].parent / "archive" / "substitute-grouping-sample.html"
        assert archived.exists(), "the archived prototype moved; this guard is no longer proven to fire"
        found = sorted(set(re.findall(SUFFIXED, archived.read_text(encoding="utf-8"))))

        assert found, "the archived page no longer contains what this check looks for"
        assert "HISTORICAL" in archived.read_text(encoding="utf-8")
