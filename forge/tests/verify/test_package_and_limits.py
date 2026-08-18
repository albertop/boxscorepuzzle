"""The file format, and what the verifier does when it cannot answer.

Two things that are easy to leave untested and expensive to get wrong. A package that round-trips
through disk incorrectly corrupts the artefact §33 says must survive an interrupted transfer; and a
verifier that quietly gives up when a search runs long is worse than one that says so, because a
silent give-up is indistinguishable from a pass.
"""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from boxscore_package import format as package_format
from boxscore_package.format import Board, Package, PackageError, read, write
from boxscore_package.signing import sign
from boxscore_package.signing import verify as verify_signature
from boxscore_verify import reason
from boxscore_verify.reason import UndecidedError, solutions
from boxscore_verify.rules import all_cells, relations, values_of
from boxscore_verify.verify import Fault, Layer, Verdict, tally, verify

Blank = Callable[[Board, dict[str, list[tuple[int, int]]]], Board]
SECRET = b"a test secret"


class TestTheFormatSurvivesDisk:
    def test_a_package_round_trips(self, tmp_path: Path, board: Board) -> None:
        original = sign(Package(puzzle_id="round-trip", puzzle=board, source=board, metadata={"season": 1968}), SECRET)
        path = tmp_path / "puzzle.json"

        write(path, original)
        restored = read(path)

        assert restored == original
        verify_signature(restored, SECRET)

    def test_the_published_half_leaves_the_answer_behind(self, board: Board) -> None:
        # The source boxscore is the answer key. Everything that travels goes through `published`,
        # and if it ever starts carrying the source the puzzle ships with its own solution.
        full = Package(puzzle_id="p", puzzle=board, source=board)

        assert full.published().source is None
        assert "source" not in full.published().as_json()

    def test_a_signature_written_over_the_full_package_still_checks_on_the_published_half(
        self, tmp_path: Path, board: Board
    ) -> None:
        signed = sign(Package(puzzle_id="p", puzzle=board, source=board), SECRET)
        path = tmp_path / "published.json"

        write(path, signed.published())

        verify_signature(read(path), SECRET)

    def test_it_refuses_a_schema_it_does_not_know(self, tmp_path: Path, board: Board) -> None:
        # A future schema must fail loudly rather than be read with today's assumptions, which is
        # the whole point of seam C2's versioning.
        path = tmp_path / "future.json"
        document = Package(puzzle_id="p", puzzle=board).as_json()
        document["schema"] = package_format.SCHEMA_VERSION + 1
        path.write_text(json.dumps(document), encoding="utf-8")

        with pytest.raises(PackageError, match="schema"):
            read(path)

    def test_it_refuses_a_file_that_is_not_json(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.json"
        path.write_text("{ this is not json", encoding="utf-8")

        with pytest.raises(PackageError, match="not valid JSON"):
            read(path)

    def test_it_refuses_json_that_is_not_a_package(self, tmp_path: Path) -> None:
        path = tmp_path / "list.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")

        with pytest.raises(PackageError, match="does not hold a puzzle package"):
            read(path)

    def test_it_refuses_a_package_with_fields_missing(self, tmp_path: Path) -> None:
        path = tmp_path / "partial.json"
        path.write_text(json.dumps({"schema": package_format.SCHEMA_VERSION, "puzzle_id": "p"}), encoding="utf-8")

        with pytest.raises(PackageError, match="missing or malformed"):
            read(path)


class TestItSaysWhenItCannotAnswer:
    def test_exhausting_the_search_budget_is_not_a_pass(
        self, board: Board, blank: Blank, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Squeezed to a handful of steps so the limit is reached on a small board. What matters is
        # that running out raises rather than returning "no other solution found".
        monkeypatch.setattr(reason, "NODE_BUDGET", 3)
        puzzle = blank(board, {"batting": [(0, 3), (1, 3), (2, 3), (3, 3), (4, 3)]})

        with pytest.raises(UndecidedError, match="not a pass"):
            solutions(relations(puzzle), all_cells(puzzle), values_of(puzzle), limit=2)

    def test_an_undecided_search_is_reported_as_a_rejection(
        self, board: Board, blank: Blank, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(reason, "NODE_BUDGET", 3)
        puzzle = blank(board, {"batting": [(0, 3), (1, 3), (2, 3), (3, 3), (4, 3)]})

        verdict = verify(Package(puzzle_id="p", puzzle=puzzle, source=board))

        assert verdict.rejection is not None
        assert verdict.rejection.fault is Fault.UNDECIDED

    def test_a_solution_touching_the_modelling_cap_is_refused(
        self, board: Board, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The cap is an assumption, not something §3 states. A result that leans on it is a result
        # the verifier has no right to report as fact.
        monkeypatch.setattr(reason, "CELL_CAP", 4)

        with pytest.raises(UndecidedError, match="modelling cap"):
            solutions(relations(board), all_cells(board), values_of(board), limit=1)


class TestMalformedPackages:
    def test_a_package_with_no_source_cannot_be_verified(self, board: Board) -> None:
        verdict = verify(Package(puzzle_id="p", puzzle=board))

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.IDENTITIES
        assert verdict.rejection.fault is Fault.MALFORMED

    def test_a_source_with_a_hole_in_it_is_malformed(self, board: Board, blank: Blank) -> None:
        # The source is the original boxscore, so a gap in it means the pipeline lost something
        # rather than that the puzzle is hard.
        holed = blank(board, {"batting": [(0, 3)]})

        verdict = verify(Package(puzzle_id="p", puzzle=board, source=holed))

        assert verdict.rejection is not None
        assert verdict.rejection.fault is Fault.MALFORMED

    def test_a_puzzle_of_a_different_shape_from_its_source(self, board: Board) -> None:
        shorter = package_format.Board(
            batting=board.batting[:8],
            batting_totals=board.batting_totals,
            footnotes=board.footnotes[:8],
            footnote_totals=board.footnote_totals,
            left_on_base=board.left_on_base,
            pitching=board.pitching,
            pitching_totals=board.pitching_totals,
            line_score=board.line_score,
        )

        verdict = verify(Package(puzzle_id="p", puzzle=shorter, source=board))

        assert verdict.rejection is not None
        assert verdict.rejection.fault is Fault.MALFORMED
        assert "batting rows" in verdict.rejection.detail

    def test_an_erased_left_on_base_is_malformed(self, board: Board) -> None:
        # Without LOB the global identity cannot be expressed at all (§6), so the board is not a
        # harder puzzle — it is a puzzle missing one of its four families.
        without = package_format.Board(
            batting=board.batting,
            batting_totals=board.batting_totals,
            footnotes=board.footnotes,
            footnote_totals=board.footnote_totals,
            left_on_base=None,
            pitching=board.pitching,
            pitching_totals=board.pitching_totals,
            line_score=board.line_score,
        )

        verdict = verify(Package(puzzle_id="p", puzzle=without, source=board))

        assert verdict.rejection is not None
        assert verdict.rejection.fault is Fault.MALFORMED
        assert "left on base" in verdict.rejection.detail

    def test_a_line_score_that_disagrees_with_the_source(self, board: Board) -> None:
        score = board.line_score
        elsewhere = package_format.Board(
            batting=board.batting,
            batting_totals=board.batting_totals,
            footnotes=board.footnotes,
            footnote_totals=board.footnote_totals,
            left_on_base=board.left_on_base,
            pitching=board.pitching,
            pitching_totals=board.pitching_totals,
            line_score=package_format.LineScore(
                offense_by_inning=score.offense_by_inning,
                defense_by_inning=score.defense_by_inning,
                offense_runs=score.offense_runs,
                offense_hits=score.offense_hits,
                offense_errors=score.offense_errors,
                defense_runs=score.defense_runs,
                defense_hits=score.defense_hits,
                defense_errors=score.defense_errors + 1,
            ),
        )

        verdict = verify(Package(puzzle_id="p", puzzle=elsewhere, source=board))

        assert verdict.rejection is not None
        assert verdict.rejection.fault is Fault.MALFORMED
        assert "line score" in verdict.rejection.detail

    def test_a_negative_inning_is_bad_data(self, board: Board) -> None:
        score = board.line_score
        broken = package_format.Board(
            batting=board.batting,
            batting_totals=board.batting_totals,
            footnotes=board.footnotes,
            footnote_totals=board.footnote_totals,
            left_on_base=board.left_on_base,
            pitching=board.pitching,
            pitching_totals=board.pitching_totals,
            line_score=package_format.LineScore(
                offense_by_inning=(-1, 2, 0, 0, 1, 0, 0, 1, 0),
                defense_by_inning=score.defense_by_inning,
                offense_runs=score.offense_runs,
                offense_hits=score.offense_hits,
                offense_errors=score.offense_errors,
                defense_runs=score.defense_runs,
                defense_hits=score.defense_hits,
                defense_errors=score.defense_errors,
            ),
        )

        verdict = verify(Package(puzzle_id="p", puzzle=broken, source=broken))

        assert verdict.rejection is not None
        assert verdict.rejection.fault is Fault.BAD_DATA
        assert "negative" in verdict.rejection.detail


class TestTheTally:
    def test_it_counts_acceptances_and_names_what_rejected(self, board: Board, blank: Blank) -> None:
        # The distribution is what says whether the generator is behaving, so it has to distinguish
        # layers rather than only count failures.
        verdicts = [
            verify(Package(puzzle_id="a", puzzle=board, source=board)),
            verify(Package(puzzle_id="b", puzzle=blank(board, {"batting": [(0, 3), (1, 3)]}), source=board)),
            verify(Package(puzzle_id="c", puzzle=board)),
        ]

        counts = tally(verdicts)

        assert counts["accepted"] == 1
        assert counts["uniqueness:multiple_solutions"] == 1
        assert counts["identities:malformed"] == 1

    def test_an_empty_batch_still_reports_an_accepted_count(self) -> None:
        assert tally([]) == {"accepted": 0}

    def test_a_verdict_knows_whether_it_passed(self) -> None:
        assert Verdict(puzzle_id="p").accepted
