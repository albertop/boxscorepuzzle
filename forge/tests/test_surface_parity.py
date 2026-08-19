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


def _parsed(line: str) -> dict[str, set[str]]:
    """`SF: 3   SH: 2, 9b   LOB: 9` into `{"SF": {"3"}, "SH": {"2", "9b"}}`.

    ⚠️ **The assertions here used to be substring tests**, which rejected `LABEL: reference` and passed
    `LABEL: other, reference` — a leak in any position but the first survived. And the positive check
    asserted only that a label appeared, so any reference under it satisfied it. Parsing into an exact
    mapping is what makes both directions checkable.
    """
    parsed: dict[str, set[str]] = {}
    for part in line.split("   "):
        if ":" not in part:
            continue
        label, _, rest = part.partition(":")
        if label.strip() == "LOB":
            continue
        parsed[label.strip()] = {token.strip() for token in rest.split(",") if token.strip()}
    return parsed


def _expected(board: Board, slots: "list[int]", pack: object) -> dict[str, set[str]]:
    """What the line must say, derived from the puzzle rather than from the line."""
    references = pack.slot_references(slots)
    wanted: dict[str, set[str]] = {}
    for column, name in enumerate(FOOTNOTE_COLUMNS):
        label = dict(pack.FOOTNOTE_LABELS)[name]
        carriers = {
            references[index] if value else "?"
            for index, row in enumerate(board.footnotes)
            for c, value in enumerate(row)
            if c == column and (value is None or value)
        }
        if carriers:
            wanted[label] = carriers
    return wanted


class TestTheFootnoteLineCannotDisagreeWithTheBoard:
    """⚠️ **This class guarded a defect that no longer has a way to occur, and it said so itself.**

    It existed because the printed pack drew its footnote line from the *complete* board while the
    player was graded on the erased one — a printed board easier than the board that was graded
    (`v05-P1-02`). Its own non-vacuity assertion — *footnote cells have to have been erased for this to
    test anything* — started failing the moment the footnote line went back to given, which is the guard
    doing its job rather than a regression.

    **The defect is now structural rather than guarded**: with the terms given, the erased board and the
    complete board carry the same footnote values, so the two lines cannot differ. What is asserted here
    is that premise, because it is the thing that would have to break first.
    """

    def test_no_footnote_cell_is_ever_erased(self, cubs_at_braves_1968: Direction) -> None:
        _board, _source, erased = _erased_board(cubs_at_braves_1968)

        assert not [cell for cell in erased if cell.startswith("footnotes[")], (
            "a footnote cell was erased; the parity guard below is no longer structural and has to return"
        )

    def test_the_line_is_the_same_from_the_puzzle_and_from_the_solution(self, cubs_at_braves_1968: Direction) -> None:
        pack = _pack()
        board, source, _erased = _erased_board(cubs_at_braves_1968)
        slots = list(range(1, len(board.batting) + 1))

        assert _parsed(pack.footnote_line(board, slots)) == _parsed(pack.footnote_line(source, slots))

    def test_the_line_still_carries_the_live_terms(self, cubs_at_braves_1968: Direction) -> None:
        # A line that printed nothing would satisfy both tests above.
        pack = _pack()
        board, _source, _erased = _erased_board(cubs_at_braves_1968)
        slots = list(range(1, len(board.batting) + 1))

        assert _parsed(pack.footnote_line(board, slots)), "the footnote line prints nothing at all"


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
            (index, column) for index, row in enumerate(board.batting) for column, v in enumerate(row) if v is None
        ]
        # ⚠️ The docstring claimed every erased cell and the test read only the batting rows. The
        # pitching section is erasable too, and an erased value revealed there is the same defect.
        # header, section, the batting rows, the batting totals, the pitching section, its header.
        pitching_first = 2 + len(board.batting) + 3
        pitching_blanks = [
            (index, column) for index, row in enumerate(board.pitching) for column, v in enumerate(row) if v is None
        ]
        for index, column in pitching_blanks:
            assert drawn[pitching_first + index][2 + column] == "", f"pitching[{index}][{column}] drew a value"

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
            (index, column) for index, row in enumerate(board.batting) for column, v in enumerate(row) if v is None
        ]

        drawn = self._drawn(source, cubs_at_braves_1968)

        for index, column in blanks:
            assert drawn[2 + index][2 + column] == str(source.batting[index][column])


class TestTheGuardCanFire:
    """A parity test that cannot fail is worth nothing, and this project has shipped two of those today."""

    def test_the_erased_board_and_the_source_still_differ_where_erasure_happens(
        self, cubs_at_braves_1968: Direction
    ) -> None:
        """⚠️ The footnote half of this guard can no longer fire, and that is not the same as it passing.

        The defect was a page drawn from the *source* beside a grid drawn from the *erased* board. With
        the footnote terms given, the two footnote lines are equal by construction, so a fire test on
        them would assert a difference that cannot exist — a check that never fires, which is what this
        class exists to prevent. That half is asserted as a premise in the class above.

        What is asserted here is the premise the surviving half rests on: **the grid still differs**, so
        a parity check over it is still capable of failing. Comparing the rendered tables directly would
        need a `Loaded` these tests do not build, and fabricating one to reach a stronger-looking
        assertion is how a guard starts testing its own scaffolding.
        """
        board, source, erased = _erased_board(cubs_at_braves_1968)

        assert erased, "nothing was erased at all"
        assert board.batting != source.batting, "the erased board and the source are the same grid"
