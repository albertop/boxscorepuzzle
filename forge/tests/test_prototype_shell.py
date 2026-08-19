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

        found = sorted(set(re.findall(r">([A-Z0-9]{1,3}-\d)<", path.read_text(encoding="utf-8"))))

        assert not found, f"{path.name} renders suffixed labels {found}; labels are bare positions"

    def test_the_archived_one_would_be_rejected(self) -> None:
        # The can-it-fire case, and it is a real file rather than a fixture: the page that prompted
        # this check must still fail it, or the check is matching nothing.
        import re  # noqa: PLC0415

        archived = _PROTOTYPES[0].parent / "archive" / "substitute-grouping-sample.html"
        assert archived.exists(), "the archived prototype moved; this guard is no longer proven to fire"
        found = sorted(set(re.findall(r">([A-Z0-9]{1,3}-\d)<", archived.read_text(encoding="utf-8"))))

        assert found, "the archived page no longer contains what this check looks for"
        assert "HISTORICAL" in archived.read_text(encoding="utf-8")
