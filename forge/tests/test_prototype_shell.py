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
