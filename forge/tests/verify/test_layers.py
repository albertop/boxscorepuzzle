"""One deliberately broken board per layer, and each caught by the layer that should catch it.

§22's four failure types are distinct — bad data, no solution, multiple solutions, unique but not
derivable — plus the corruption the signing rule exists for. A verifier that rejects everything is
useless in the same way as one that accepts everything, so what is tested is not only *that* a board
is rejected but *which layer* rejected it and *why*.
"""

from collections.abc import Callable

import pytest

from boxscore_package.format import Board, LineScore, Package
from boxscore_package.signing import sign
from boxscore_verify.verify import Fault, Layer, check_derivability, verify

Blank = Callable[[Board, dict[str, list[tuple[int, int]]]], Board]

SECRET = b"a test secret, not the one that signs anything real"


def package(puzzle: Board, source: Board) -> Package:
    return Package(puzzle_id="test", puzzle=puzzle, source=source)


def replacing(board: Board, **changes: object) -> Board:
    """A board with some parts swapped, so a test can state only what it breaks."""
    fields: dict[str, object] = {
        "batting": board.batting,
        "batting_totals": board.batting_totals,
        "footnotes": board.footnotes,
        "footnote_totals": board.footnote_totals,
        "left_on_base": board.left_on_base,
        "pitching": board.pitching,
        "pitching_totals": board.pitching_totals,
        "line_score": board.line_score,
    }
    fields.update(changes)
    return Board(**fields)  # type: ignore[arg-type]


class TestItAcceptsACorrectPuzzle:
    def test_a_derivable_erasure_passes_every_layer(self, board: Board, blank: Blank) -> None:
        # Found by searching this board for an erasure that is unique and needs no guess. Six cells
        # across four batting rows, a pitching cell and a pitching total, so the accepted case is not
        # a board with one blank in it.
        puzzle = blank(
            board,
            {
                "batting": [(2, 0), (7, 4), (1, 1), (4, 3)],
                "pitching": [(1, 4)],
                "pitching_totals": [(0, 2)],
            },
        )

        verdict = verify(package(puzzle, board))

        assert verdict.accepted, verdict.rejection

    def test_a_board_with_nothing_erased_is_still_a_valid_package(self, board: Board) -> None:
        # Degenerate but it must pass: every layer's question has a trivial answer, and a verifier
        # that trips over the easy case cannot be trusted on the hard one.
        assert verify(package(board, board)).accepted


class TestLayerOneCatchesBadData:
    def test_a_boxscore_that_does_not_balance(self, board: Board) -> None:
        # One hit added to a batter and nowhere else. The column sum breaks, and so does the
        # cross-team link to the pitchers who supposedly allowed it.
        rows = list(board.batting)
        rows[3] = (4, 4, 0, 2, 0, 1)
        source = replacing(board, batting=tuple(rows))

        verdict = verify(package(source, source))

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.IDENTITIES
        assert verdict.rejection.fault is Fault.BAD_DATA

    def test_a_line_score_whose_innings_do_not_add_up(self, board: Board) -> None:
        score = board.line_score
        source = replacing(
            board,
            line_score=LineScore(
                offense_by_inning=(0, 1, 0, 0, 1, 0, 0, 0, 0),  # adds to two, and three are claimed
                defense_by_inning=score.defense_by_inning,
                offense_runs=score.offense_runs,
                offense_hits=score.offense_hits,
                offense_errors=score.offense_errors,
                defense_runs=score.defense_runs,
                defense_hits=score.defense_hits,
                defense_errors=score.defense_errors,
            ),
        )

        verdict = verify(package(source, source))

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.IDENTITIES
        assert verdict.rejection.fault is Fault.BAD_DATA

    def test_an_erased_footnote_is_malformed_rather_than_hard(self, board: Board) -> None:
        # §6 gives the footnote line complete and never erased. Without it the row identity does not
        # close, so this is a broken puzzle rather than a difficult one.
        notes = [list(row) for row in board.footnotes]
        notes[0][0] = None
        puzzle = replacing(board, footnotes=tuple(tuple(row) for row in notes))

        verdict = verify(package(puzzle, board))

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.IDENTITIES
        assert verdict.rejection.fault is Fault.MALFORMED


class TestLayerTwoCatchesAmbiguity:
    def test_cells_erased_that_were_not_forced(self, board: Board, blank: Blank) -> None:
        # Two hits cells from the same column. Their sum is fixed and nothing separates them, so the
        # board has several completions and no right answer for the player to find.
        puzzle = blank(board, {"batting": [(0, 3), (1, 3)]})

        verdict = verify(package(puzzle, board))

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.UNIQUENESS
        assert verdict.rejection.fault is Fault.MULTIPLE_SOLUTIONS

    def test_a_board_whose_given_cells_contradict_each_other(self, board: Board, blank: Blank) -> None:
        # The puzzle claims forty hits in the batting total against the eight its pitchers allowed.
        # No completion exists, which is a different failure from having too many.
        puzzle = replacing(
            blank(board, {"batting": [(0, 3)]}),
            batting_totals=(36, 36, 3, 40, 0, 5),
        )

        verdict = verify(package(puzzle, board))

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.UNIQUENESS
        assert verdict.rejection.fault is Fault.NO_SOLUTION


class TestLayerThreeCatchesAnUnreachableBoard:
    def test_it_rejects_a_board_that_cannot_be_reached_without_guessing(self, board: Board, blank: Blank) -> None:
        # Called on its own, which is what §22 means by each layer rejecting independently. This
        # board also has several completions, so `verify` would stop at layer 2 — asking layer 3
        # directly is what shows layer 3 answering its own question.
        puzzle = blank(board, {"batting": [(0, 3), (1, 3)]})

        rejection = check_derivability(package(puzzle, board), None)

        assert rejection is not None
        assert rejection.layer is Layer.DERIVABILITY
        assert rejection.fault is Fault.NOT_DERIVABLE

    @pytest.mark.xfail(
        reason=(
            "No board that is unique AND underivable has been found: about 24,000 random erasures "
            "across 400 generated boards produced none. That is a finding about this constraint "
            "family rather than a gap in the search — see the verifier's README — and the layer "
            "stays regardless, because absence of an example is not a proof."
        ),
        strict=True,
    )
    def test_a_unique_board_that_still_needs_a_guess(self) -> None:
        message = "no such board is known"
        raise AssertionError(message)


class TestLayerFourCatchesACorruptedArtefact:
    def test_a_given_cell_altered_after_generation(self, board: Board) -> None:
        # The nastiest case the first three layers cannot see. Two batters' hits are swapped in the
        # published board: every identity still holds, the board still has exactly one completion,
        # and that completion is a different game from the one the source says it is.
        rows = [list(row) for row in board.batting]
        rows[0][3], rows[8][3] = rows[8][3], rows[0][3]
        puzzle = replacing(board, batting=tuple(tuple(row) for row in rows))

        verdict = verify(package(puzzle, board))

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.END_TO_END
        assert verdict.rejection.fault is Fault.MISMATCH


class TestTheSignatureCatchesCorruptionInTransit:
    def test_a_package_changed_after_signing(self, board: Board, blank: Blank) -> None:
        signed = sign(package(board, board), SECRET)
        tampered = Package(
            puzzle_id=signed.puzzle_id,
            puzzle=blank(board, {"batting": [(0, 3)]}),
            source=signed.source,
            metadata=signed.metadata,
            signature=signed.signature,
        )

        verdict = verify(tampered, secret=SECRET)

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.SIGNATURE
        assert verdict.rejection.fault is Fault.CORRUPTED

    def test_an_unsigned_package_is_refused_when_a_secret_is_expected(self, board: Board) -> None:
        verdict = verify(package(board, board), secret=SECRET)

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.SIGNATURE

    def test_a_signed_package_passes(self, board: Board) -> None:
        assert verify(sign(package(board, board), SECRET), secret=SECRET).accepted
