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
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from boxscore_package import format as package_format
from boxscore_package.format import Board, Package, PackageError, read, write
from boxscore_package.signing import sign
from boxscore_package.signing import verify as verify_signature
from boxscore_verify import reason
from boxscore_verify.reason import UndecidedError, solutions
from boxscore_verify.rules import all_cells, relations, values_of
from boxscore_verify.verify import UNSIGNED, Fault, Layer, Verdict, tally, verify

Blank = Callable[[Board, dict[str, list[tuple[int, int]]]], Board]
_KEY = Ed25519PrivateKey.generate()
SECRET = _KEY
"""⚠️ **A key pair, not a shared secret.** The forge signs with the private half and `serve` verifies
with the public one, which is the property a MAC cannot express: every verifier of an HMAC is also a
signer, so the verification key on the VPS *was* the signing authority (§33). Generated per run — a
test key checked into the repository is a key anybody can sign with."""

PUBLIC = _KEY.public_key()


def refs(board: object) -> tuple[str, ...]:
    """One slot reference per batting row, in the shape the format actually allows.

    ⚠️ **This produced `"10"`, `"11"`… and those are not references.** A lineup has nine slots; a
    thirteen-row board carries thirteen references drawn from those nine, and what distinguishes rows
    inside a slot is the letter. The helper invented a tenth slot, and only the stricter constructor
    noticed — the fixtures had been carrying impossible values.
    """
    from string import ascii_lowercase  # noqa: PLC0415

    return tuple(
        str(index + 1) if index < 9 else f"9{ascii_lowercase[index - 9]}"
        for index in range(len(board.batting))  # type: ignore[attr-defined]
    )


class TestTheFormatSurvivesDisk:
    def test_a_package_round_trips(self, tmp_path: Path, board: Board) -> None:
        original = sign(
            Package(
                labels=("C",) * len(board.batting),
                pitcher_labels=("C",) * len(board.pitching),
                puzzle_id="000000000000002f",
                puzzle=board,
                solution=board,
                metadata={"season": 1968},
                slot_references=refs(board),
                offense_is_home=True,
            ),
            SECRET,
        )
        path = tmp_path / "puzzle.json"

        write(path, original)
        restored = read(path)

        assert restored == original
        verify_signature(restored, PUBLIC)

    def test_the_published_half_keeps_the_answer_and_drops_what_would_spoil_it(self, board: Board) -> None:
        # ⚠️ This reverses an earlier promise, on purpose. The published half used to strip the
        # solution as an answer key; §23 requires the game to work with the backend down, so the
        # client cannot fetch a name when a row completes and the solution has to be in the file.
        # §9 accepts that devtools can read it. What travels loses instead the metadata that would
        # hand over the mystery — an opaque puzzle id beside a `game_id` protects nothing.
        full = Package(
            labels=("C",) * len(board.batting),
            pitcher_labels=("C",) * len(board.pitching),
            puzzle_id="000000000000000f",
            puzzle=board,
            solution=board,
            metadata={"game_id": "ATL196808080", "chain_target": 9},
            slot_references=refs(board),
            offense_is_home=True,
        )

        published = full.published()

        assert published.solution == board
        assert "game_id" not in published.as_json()["metadata"]
        assert published.as_json()["metadata"]["chain_target"] == 9

    def test_a_signature_written_over_the_full_package_still_checks_on_the_published_half(
        self, tmp_path: Path, board: Board
    ) -> None:
        signed = sign(
            Package(
                labels=("C",) * len(board.batting),
                pitcher_labels=("C",) * len(board.pitching),
                puzzle_id="000000000000000f",
                puzzle=board,
                solution=board,
                slot_references=refs(board),
                offense_is_home=True,
            ),
            SECRET,
        )
        path = tmp_path / "published.json"

        write(path, signed.published())

        verify_signature(read(path), PUBLIC)

    def test_it_refuses_a_schema_it_does_not_know(self, tmp_path: Path, board: Board) -> None:
        # A future schema must fail loudly rather than be read with today's assumptions, which is
        # the whole point of seam C2's versioning.
        path = tmp_path / "future.json"
        document = Package(
            labels=("C",) * len(board.batting),
            pitcher_labels=("C",) * len(board.pitching),
            puzzle_id="000000000000000f",
            puzzle=board,
            slot_references=refs(board),
            offense_is_home=True,
        ).as_json()
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
        # A contract-shaped id on purpose: the point of this test is the missing board, and an id the
        # envelope would reject on its own would refuse the file before the board was ever looked at.
        path.write_text(
            json.dumps({"schema": package_format.SCHEMA_VERSION, "puzzle_id": "000000000000000f"}),
            encoding="utf-8",
        )

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

        verdict = verify(
            Package(
                labels=("C",) * len(puzzle.batting),
                pitcher_labels=("C",) * len(puzzle.pitching),
                puzzle_id="000000000000000f",
                puzzle=puzzle,
                solution=board,
                slot_references=refs(puzzle),
                offense_is_home=True,
            ),
            secret=UNSIGNED,
        )

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
        verdict = verify(
            Package(
                labels=("C",) * len(board.batting),
                pitcher_labels=("C",) * len(board.pitching),
                puzzle_id="000000000000000f",
                puzzle=board,
                slot_references=refs(board),
                offense_is_home=True,
            ),
            secret=UNSIGNED,
        )

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.IDENTITIES
        assert verdict.rejection.fault is Fault.MALFORMED

    def test_a_source_with_a_hole_in_it_is_malformed(self, board: Board, blank: Blank) -> None:
        # The source is the original boxscore, so a gap in it means the pipeline lost something
        # rather than that the puzzle is hard.
        holed = blank(board, {"batting": [(0, 3)]})

        verdict = verify(
            Package(
                labels=("C",) * len(board.batting),
                pitcher_labels=("C",) * len(board.pitching),
                puzzle_id="000000000000000f",
                puzzle=board,
                solution=holed,
                slot_references=refs(board),
                offense_is_home=True,
            ),
            secret=UNSIGNED,
        )

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

        verdict = verify(
            Package(
                labels=("C",) * len(shorter.batting),
                pitcher_labels=("C",) * len(shorter.pitching),
                puzzle_id="000000000000000f",
                puzzle=shorter,
                solution=board,
                slot_references=refs(shorter),
                offense_is_home=True,
            ),
            secret=UNSIGNED,
        )

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

        verdict = verify(
            Package(
                labels=("C",) * len(without.batting),
                pitcher_labels=("C",) * len(without.pitching),
                puzzle_id="000000000000000f",
                puzzle=without,
                solution=board,
                slot_references=refs(without),
                offense_is_home=True,
            ),
            secret=UNSIGNED,
        )

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

        verdict = verify(
            Package(
                labels=("C",) * len(elsewhere.batting),
                pitcher_labels=("C",) * len(elsewhere.pitching),
                puzzle_id="000000000000000f",
                puzzle=elsewhere,
                solution=board,
                slot_references=refs(elsewhere),
                offense_is_home=True,
            ),
            secret=UNSIGNED,
        )

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

        verdict = verify(
            Package(
                labels=("C",) * len(broken.batting),
                pitcher_labels=("C",) * len(broken.pitching),
                puzzle_id="000000000000000f",
                puzzle=broken,
                solution=broken,
                slot_references=refs(broken),
                offense_is_home=True,
            ),
            secret=UNSIGNED,
        )

        assert verdict.rejection is not None
        assert verdict.rejection.fault is Fault.BAD_DATA
        assert "negative" in verdict.rejection.detail


class TestTheTally:
    def test_it_counts_acceptances_and_names_what_rejected(self, board: Board, blank: Blank) -> None:
        # The distribution is what says whether the generator is behaving, so it has to distinguish
        # layers rather than only count failures.
        verdicts = [
            verify(
                Package(
                    labels=("C",) * len(board.batting),
                    pitcher_labels=("C",) * len(board.pitching),
                    puzzle_id="000000000000000a",
                    puzzle=board,
                    solution=board,
                    slot_references=refs(board),
                    offense_is_home=True,
                ),
                secret=UNSIGNED,
            ),
            verify(
                Package(
                    labels=("C",) * len(blank(board, {"batting": [(0, 3), (1, 3)]}).batting),
                    pitcher_labels=("C",) * len(blank(board, {"batting": [(0, 3), (1, 3)]}).pitching),
                    puzzle_id="000000000000000b",
                    puzzle=blank(board, {"batting": [(0, 3), (1, 3)]}),
                    solution=board,
                    slot_references=refs(blank(board, {"batting": [(0, 3), (1, 3)]})),
                    offense_is_home=True,
                ),
                secret=UNSIGNED,
            ),
            verify(
                Package(
                    labels=("C",) * len(board.batting),
                    pitcher_labels=("C",) * len(board.pitching),
                    puzzle_id="000000000000000c",
                    puzzle=board,
                    slot_references=refs(board),
                    offense_is_home=True,
                ),
                secret=UNSIGNED,
            ),
        ]

        counts = tally(verdicts)

        assert counts["accepted"] == 1
        assert counts["uniqueness:multiple_solutions"] == 1
        assert counts["identities:malformed"] == 1

    def test_an_empty_batch_still_reports_an_accepted_count(self) -> None:
        assert tally([]) == {"accepted": 0}

    def test_a_verdict_knows_whether_it_passed(self) -> None:
        assert Verdict(puzzle_id="000000000000000f").accepted
