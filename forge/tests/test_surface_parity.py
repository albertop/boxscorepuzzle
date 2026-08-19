"""Every erased cell is blank on the page, and its value appears nowhere in the generated text.

⚠️ **The board a person reads must be the board that was graded.** The per-batter footnote cells are
erasable, and the printed footnote line took its values from the complete source while the grid beside
it drew the erased puzzle — so a value removed for grading was handed back on the page, and the key
recorded stalls the reader never had to work for.

The earlier repair fixed `Direction → Board`. This guards `Board → the artifact a human reads`, which
is one boundary further out and was not covered by it.

**Both directions are asserted.** A renderer that printed nothing at all would satisfy "no erased value
appears"; one that printed everything would satisfy "every given value appears". Neither alone is the
property.
"""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

from boxscore_forge.boxscore import Direction
from boxscore_forge.erasure import erase
from boxscore_forge.publish import to_board
from boxscore_package.format import FOOTNOTE_COLUMNS, Board

_HANDSOLVE = Path(__file__).resolve().parents[2] / "discovery" / "hand-solve"


def _pack() -> object:
    for extra in (_HANDSOLVE, _HANDSOLVE.parents[0] / "difficulty-metrics"):
        sys.path.insert(0, str(extra))
    spec = importlib.util.spec_from_file_location("build_pack_surface", _HANDSOLVE / "build_pack.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _erased_board(direction: Direction) -> tuple[Board, Board, frozenset[str]]:
    puzzle = erase(direction, target_stalls=8, seed=11)
    assert puzzle is not None
    return to_board(direction, puzzle.erased), to_board(direction, None), puzzle.erased


class TestTheFootnoteLineShowsTheErasedBoard:
    def test_an_erased_footnote_is_not_printed_and_leaves_a_placeholder(self, cubs_at_braves_1968: Direction) -> None:
        pack = _pack()
        board, source, erased = _erased_board(cubs_at_braves_1968)
        slots = list(range(1, len(board.batting) + 1))
        erased_footnotes = [cell for cell in erased if cell.startswith("footnotes[")]
        # Non-vacuous: the fixture has to have lost footnote cells for this to test anything.
        assert erased_footnotes

        line = pack.footnote_line(board, slots)
        complete = pack.footnote_line(source, slots)

        assert line != complete, "the erased board printed the same footnote line as the source"
        for index, row in enumerate(board.footnotes):
            for column, value in enumerate(row):
                if value is None and source.footnotes[index][column]:
                    reference = pack.slot_references(slots)[index]
                    label = dict(pack.FOOTNOTE_LABELS)[FOOTNOTE_COLUMNS[column]]
                    assert f"{label}: {reference}" not in line, f"{label} for row {index} was handed back"
        assert "?" in line

    def test_a_given_footnote_is_still_printed(self, cubs_at_braves_1968: Direction) -> None:
        # The other direction. A line that printed nothing would pass the test above.
        pack = _pack()
        board, _, _ = _erased_board(cubs_at_braves_1968)
        slots = list(range(1, len(board.batting) + 1))

        line = pack.footnote_line(board, slots)

        carried = [
            (index, column)
            for index, row in enumerate(board.footnotes)
            for column, value in enumerate(row)
            if value
        ]
        for index, column in carried:
            label = dict(pack.FOOTNOTE_LABELS)[FOOTNOTE_COLUMNS[column]]
            assert label in line, f"{label} was carried on row {index} and is not on the page"

    def test_left_on_base_and_the_totals_stay_visible(self, cubs_at_braves_1968: Direction) -> None:
        # §6: the footnote *totals* row and LOB are given, and they are what close the row identity.
        pack = _pack()
        board, _, _ = _erased_board(cubs_at_braves_1968)

        assert f"LOB: {board.left_on_base}" in pack.footnote_line(board, list(range(1, len(board.batting) + 1)))


class TestTheGridShowsTheErasedBoard:
    """⚠️ The first version of this computed the drawn string from the same value it then asserted on —
    a tautology, and the third one written in a day. It calls the renderer now and reads what the table
    actually holds."""

    def _drawn(self, board: Board, direction: Direction) -> list[list[str]]:
        pack = _pack()
        loaded = SimpleNamespace(
            offense_is_home=True,
            labels=tuple("C" for _ in board.batting),
            pitcher_labels=tuple("SP" for _ in board.pitching),
            slots=tuple(range(1, len(board.batting) + 1)),
            direction=direction,
        )
        return [[str(cell) for cell in row] for row in pack.board_table(board, loaded, solved=False)._cellvalues]

    def test_every_erased_cell_draws_nothing_and_every_given_one_draws_its_value(
        self, cubs_at_braves_1968: Direction
    ) -> None:
        board, _, _ = _erased_board(cubs_at_braves_1968)
        drawn = self._drawn(board, cubs_at_braves_1968)
        flat = " ".join(cell for row in drawn for cell in row)
        blanks = [
            (index, column)
            for index, row in enumerate(board.batting)
            for column, v in enumerate(row)
            if v is None
        ]

        assert blanks, "nothing was erased in the batting grid; the test would pass vacuously"
        # The batting rows start after the column header and the section band, and carry the slot
        # reference and the label before the data.
        for index, column in blanks:
            assert drawn[2 + index][2 + column] == "", f"batting[{index}][{column}] was erased and drew a value"
        for index, row in enumerate(board.batting):
            for column, value in enumerate(row):
                if value is not None:
                    assert drawn[2 + index][2 + column] == str(value)
        assert flat.strip(), "the table drew nothing at all, which would satisfy every assertion above"

    def test_the_solution_table_draws_what_the_puzzle_hides(self, cubs_at_braves_1968: Direction) -> None:
        # The other direction, and the one that proves the blanks are the renderer's doing rather than
        # the board's: the same renderer on the complete board fills the same cells.
        board, source, _ = _erased_board(cubs_at_braves_1968)
        blanks = [
            (index, column)
            for index, row in enumerate(board.batting)
            for column, v in enumerate(row)
            if v is None
        ]

        drawn = self._drawn(source, cubs_at_braves_1968)

        for index, column in blanks:
            assert drawn[2 + index][2 + column] == str(source.batting[index][column])


class TestTheGuardCanFire:
    """A parity test that cannot fail is worth nothing, and this project has shipped two of those today."""

    def test_it_rejects_a_page_built_from_the_complete_board(self, cubs_at_braves_1968: Direction) -> None:
        pack = _pack()
        board, source, _ = _erased_board(cubs_at_braves_1968)
        slots = list(range(1, len(board.batting) + 1))

        # The defect exactly: the footnote line rendered from the source beside an erased grid.
        from_the_source = pack.footnote_line(source, slots)

        assert "?" not in from_the_source
        assert from_the_source != pack.footnote_line(board, slots)
