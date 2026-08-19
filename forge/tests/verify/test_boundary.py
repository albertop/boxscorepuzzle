"""The boundary rejects malformed input; the signature refuses to be skipped by accident.

Both guard the same shape of defect, which CLAUDE.md names outright: **the absence of a check reading
as the presence of a passing one.** Parsing that accepts anything and dies three layers later, and a
verifier that reports success when its secret is missing, are the same mistake wearing two hats.
"""

import inspect
import json
from dataclasses import fields
from pathlib import Path

import pytest

from boxscore_forge.boxscore import BatterFootnotes, BattingLine, PitchingLine
from boxscore_package.format import (
    BATTING_COLUMNS,
    FOOTNOTE_COLUMNS,
    PITCHING_COLUMNS,
    Board,
    Package,
    PackageError,
    read,
)
from boxscore_verify.verify import UNSIGNED, verify


def refs(board: object) -> tuple[str, ...]:
    """One slot reference per batting row — the shape a package must carry since schema 2.

    A helper rather than the expression inline: it appears in every fixture, and the property being
    fixed is *one per row*, which a name states and a comprehension buries.
    """
    return tuple(str(index + 1) for index in range(len(board.batting)))  # type: ignore[attr-defined]


def written(tmp_path: Path, board: Board, **changes: object) -> Path:
    document = Package(puzzle_id="000000000000000f", puzzle=board, solution=board,
        slot_references=refs(board)).as_json()
    for key, value in changes.items():
        section, _, field = key.partition("__")
        if field:
            document[section][field] = value
        else:
            document[section] = value
    path = tmp_path / "package.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


class TestTheFormatRefusesMalformedBoards:
    def test_a_row_of_the_wrong_width(self, tmp_path: Path, board: Board) -> None:
        # Five columns where six are expected. Without this check it becomes an IndexError or a
        # silently short row, somewhere inside the arithmetic.
        rows = [list(row) for row in board.batting]
        rows[0] = rows[0][:5]

        with pytest.raises(PackageError, match="expected 6"):
            read(written(tmp_path, board, puzzle__batting=rows))

    def test_a_cell_that_is_not_a_number(self, tmp_path: Path, board: Board) -> None:
        # Deliberately the wrong type — that is the test. The row is typed loosely here so the
        # checker does not object to input the parser is supposed to object to.
        rows: list[list[object]] = [list(row) for row in board.batting]
        rows[0][0] = "four"

        with pytest.raises(PackageError, match="expected a whole number or null"):
            read(written(tmp_path, board, puzzle__batting=rows))

    def test_a_boolean_is_not_a_number_even_though_python_thinks_so(self, tmp_path: Path, board: Board) -> None:
        # `isinstance(True, int)` is True in Python, so this needs saying explicitly or `true` in
        # the JSON becomes a 1 on the board.
        rows: list[list[object]] = [list(row) for row in board.batting]
        rows[0][0] = True

        with pytest.raises(PackageError, match="expected a whole number or null"):
            read(written(tmp_path, board, puzzle__batting=rows))

    def test_a_batting_section_that_is_not_a_list(self, tmp_path: Path, board: Board) -> None:
        with pytest.raises(PackageError, match="expected a list of rows"):
            read(written(tmp_path, board, puzzle__batting={"rows": 9}))

    def test_a_footnote_line_with_a_hole_in_it(self, tmp_path: Path, board: Board) -> None:
        # §6 gives the footnote totals complete and never erased, so a null there is malformed
        # rather than difficult, and saying so at the boundary is cheaper than deducing it later.
        with pytest.raises(PackageError, match="never erased"):
            read(written(tmp_path, board, puzzle__footnote_totals=[0, None, 0, 0]))

    def test_footnote_rows_that_do_not_match_the_lineup(self, tmp_path: Path, board: Board) -> None:
        with pytest.raises(PackageError, match="footnote rows against"):
            read(written(tmp_path, board, puzzle__footnotes=[[0, 0, 0, 0]] * 3))

    def test_a_line_score_missing_a_field(self, tmp_path: Path, board: Board) -> None:
        score = board.line_score.as_json()
        del score["offense_hits"]

        with pytest.raises(PackageError, match="missing offense_hits"):
            read(written(tmp_path, board, puzzle__line_score=score))

    def test_metadata_that_is_not_an_object(self, tmp_path: Path, board: Board) -> None:
        # Seam C3 keeps metadata loose on purpose, but a list here breaks every reader of it.
        with pytest.raises(PackageError, match="metadata is list"):
            read(written(tmp_path, board, metadata=[1, 2, 3]))

    def test_a_well_formed_package_still_reads(self, tmp_path: Path, board: Board) -> None:
        # A boundary check that rejects valid input is worse than none, so this is the other half.
        assert read(written(tmp_path, board)).puzzle == board


class TestTheSignatureCannotBeSkippedByAccident:
    def test_a_missing_secret_raises_rather_than_passing(self, board: Board) -> None:
        # ⚠️ The finding. A publish path whose secret is unset would previously verify nothing and
        # report a pass — misconfiguration reading as success.
        with pytest.raises(ValueError, match="pass UNSIGNED"):
            verify(Package(puzzle_id="000000000000000f", puzzle=board, solution=board,
                slot_references=refs(board)), secret=None)

    def test_there_is_no_default_to_forget(self) -> None:
        parameter = inspect.signature(verify).parameters["secret"]

        assert parameter.default is inspect.Parameter.empty
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY

    def test_skipping_it_deliberately_is_allowed(self, board: Board) -> None:
        assert verify(Package(puzzle_id="000000000000000f", puzzle=board, solution=board,
            slot_references=refs(board)), secret=UNSIGNED).accepted


class TestTheTwoSidesUseTheSameVocabulary:
    def test_the_footnote_columns_match_the_model_field_names(self) -> None:
        """The schema and the model must name the same concept the same way.

        They did not: the model called the fourth footnote term `reached_on_interference` and the
        package called it `catcher_interference`. Nothing broke, because the adapter writes
        positionally — which is exactly what makes it worth a test. A future reader taking the column
        by name would have displayed or validated the wrong concept, and the tuple order would have
        kept agreeing with itself.
        """
        assert tuple(f.name for f in fields(BatterFootnotes)) == FOOTNOTE_COLUMNS
        assert tuple(f.name for f in fields(BattingLine)) == BATTING_COLUMNS
        assert tuple(f.name for f in fields(PitchingLine)) == PITCHING_COLUMNS


class TestTheRemainingMalformedShapes:
    def test_a_board_that_is_not_an_object(self, tmp_path: Path, board: Board) -> None:
        with pytest.raises(PackageError, match="expected an object"):
            read(written(tmp_path, board, puzzle=[1, 2, 3]))

    def test_a_line_score_that_is_not_an_object(self, tmp_path: Path, board: Board) -> None:
        with pytest.raises(PackageError, match="expected an object"):
            read(written(tmp_path, board, puzzle__line_score="nine innings"))

    def test_innings_that_are_not_a_list(self, tmp_path: Path, board: Board) -> None:
        score = board.line_score.as_json()
        score["offense_by_inning"] = "000100200"

        with pytest.raises(PackageError, match="expected a list of innings"):
            read(written(tmp_path, board, puzzle__line_score=score))

    def test_an_inning_that_is_not_a_number(self, tmp_path: Path, board: Board) -> None:
        score = board.line_score.as_json()
        score["offense_by_inning"] = [0, "x", 0, 0, 1, 0, 0, 1, 0]

        with pytest.raises(PackageError, match="expected a whole number"):
            read(written(tmp_path, board, puzzle__line_score=score))

    def test_a_totals_row_that_is_not_a_list(self, tmp_path: Path, board: Board) -> None:
        with pytest.raises(PackageError, match="expected a list of 6 values"):
            read(written(tmp_path, board, puzzle__batting_totals=36))

    def test_left_on_base_that_is_not_a_number(self, tmp_path: Path, board: Board) -> None:
        with pytest.raises(PackageError, match="expected a whole number"):
            read(written(tmp_path, board, puzzle__left_on_base="six"))


class TestTheEnvelopeIsCheckedToo:
    """The board was validated at the boundary and the envelope around it was not.

    ⚠️ **Tested against `Package.from_json` directly, not only through `read`.** `read` guarded the
    root object and the method did not, so the method was safe only when entered through one
    particular door — which is not a boundary, it is a habit.
    """

    def _document(self, board: Board) -> dict[str, object]:
        return Package(puzzle_id="000000000000000f", puzzle=board, solution=board,
            slot_references=refs(board)).as_json()

    @pytest.mark.parametrize("root", [[], "a package", 7, None, True])
    def test_a_root_that_is_not_an_object_is_refused(self, root: object) -> None:
        # `raw.get` on a list raised AttributeError three frames later. A malformed file must produce
        # a controlled rejection, not an uncontrolled crash.
        with pytest.raises(PackageError, match="expected an object"):
            Package.from_json(root)

    def test_a_boolean_schema_is_refused(self, board: Board) -> None:
        # ⚠️ `True == 1` in Python, so `schema != SCHEMA_VERSION` accepted `"schema": true` and read
        # the file as a version 1 package.
        document = self._document(board)
        document["schema"] = True

        with pytest.raises(PackageError, match="schema True"):
            Package.from_json(document)

    @pytest.mark.parametrize("bad", ["p", "", "0123456789ABCDEF", "0123456789abcde", "../../etc/passwd", 1, None])
    def test_an_identifier_that_is_not_the_contract_shape_is_refused(self, board: Board, bad: object) -> None:
        # Sixteen lower-case hex characters, as the format document states. The identifier reaches
        # filenames and will reach URLs, so a path-like value is the case that matters most.
        document = self._document(board)
        document["puzzle_id"] = bad

        with pytest.raises(PackageError, match="puzzle_id is"):
            Package.from_json(document)

    def test_the_contract_shape_is_accepted(self, board: Board) -> None:
        # The other half. A pattern that refuses everything would pass every test above.
        assert Package.from_json(self._document(board)).puzzle_id == "000000000000000f"

    @pytest.mark.parametrize("bad", ["", "not-hex", "0" * 63, "0" * 65, 1, []])
    def test_a_signature_that_is_not_an_hmac_is_refused(self, board: Board, bad: object) -> None:
        # A signature of the wrong type used to reach `hmac.compare_digest`, which raises on bytes it
        # cannot handle — the verifier crashing on a malformed file instead of rejecting it.
        document = self._document(board)
        document["signature"] = bad

        with pytest.raises(PackageError, match="signature is"):
            Package.from_json(document)

    def test_an_absent_signature_is_still_allowed(self, board: Board) -> None:
        # Absence is not malformation: a package may be unsigned, and the gate is what decides
        # whether an unsigned one may be published.
        document = self._document(board)
        document.pop("signature", None)

        assert Package.from_json(document).signature is None

    def test_a_real_identifier_satisfies_the_pattern(self) -> None:
        # The link between the two sides. The forge produces the identifier and the format states its
        # shape; without this they are two claims about the same string with nothing joining them.
        from boxscore_forge.identity import puzzle_id  # noqa: PLC0415
        from boxscore_package.format import PUZZLE_ID  # noqa: PLC0415

        assert PUZZLE_ID.fullmatch(puzzle_id("SLN19131005", "CHN"))
