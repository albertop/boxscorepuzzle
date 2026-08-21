"""One deliberately broken board per layer, and each caught by the layer that should catch it.

§22's four failure types are distinct — bad data, no solution, multiple solutions, unique but not
derivable — plus the corruption the signing rule exists for. A verifier that rejects everything is
useless in the same way as one that accepts everything, so what is tested is not only *that* a board
is rejected but *which layer* rejected it and *why*.
"""

from collections.abc import Callable

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from boxscore_package.format import Board, LineScore, Package, PackageError
from boxscore_package.signing import sign
from boxscore_verify.verify import UNSIGNED, Fault, Layer, check_derivability, verify

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


def package(puzzle: Board, source: Board) -> Package:
    return Package(
        labels=("C",) * len(puzzle.batting),
        pitcher_labels=("C",) * len(puzzle.pitching),
        puzzle_id="000000000000001f",
        puzzle=puzzle,
        solution=source,
        slot_references=refs(puzzle),
        offense_is_home=True,
    )


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

        verdict = verify(package(puzzle, board), secret=UNSIGNED, source=board)

        assert verdict.accepted, verdict.rejection

    def test_a_board_with_nothing_erased_is_still_a_valid_package(self, board: Board) -> None:
        # Degenerate but it must pass: every layer's question has a trivial answer, and a verifier
        # that trips over the easy case cannot be trusted on the hard one.
        assert verify(package(board, board), secret=UNSIGNED, source=board).accepted


class TestLayerOneCatchesBadData:
    def test_a_boxscore_that_does_not_balance(self, board: Board) -> None:
        # One hit added to a batter and nowhere else. The column sum breaks, and so does the
        # cross-team link to the pitchers who supposedly allowed it.
        rows = list(board.batting)
        rows[3] = (4, 4, 0, 2, 0, 1)
        source = replacing(board, batting=tuple(rows))

        verdict = verify(package(source, source), secret=UNSIGNED, source=source)

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

        verdict = verify(package(source, source), secret=UNSIGNED, source=source)

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.IDENTITIES
        assert verdict.rejection.fault is Fault.BAD_DATA

    def test_an_erased_footnote_total_never_reaches_a_layer_at_all(self, board: Board) -> None:
        """⚠️ **The rule moved from this layer to the format, and the test moved with it.**

        Erasing the totals row leaves the row identity with two unknowns and no way to separate them,
        which is a broken puzzle rather than a difficult one. Layer 1 used to say so. `check_profile`
        now refuses it on construction *and* on parsing, so no package can carry the fault and the
        layer's branch for it could never fire — which this project treats as broken rather than free.

        Asserting the earlier refusal is the stronger statement: a fault caught by the type cannot
        reach a verifier that might have been skipped.
        """
        puzzle = replacing(board, footnote_totals=(None, *board.footnote_totals[1:]))

        with pytest.raises(PackageError, match="footnote_totals has a blank"):
            package(puzzle, board)


class TestLayerTwoCatchesAmbiguity:
    def test_cells_erased_that_were_not_forced(self, board: Board, blank: Blank) -> None:
        # Two hits cells from the same column. Their sum is fixed and nothing separates them, so the
        # board has several completions and no right answer for the player to find.
        puzzle = blank(board, {"batting": [(0, 3), (1, 3)]})

        verdict = verify(package(puzzle, board), secret=UNSIGNED, source=board)

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.UNIQUENESS
        assert verdict.rejection.fault is Fault.MULTIPLE_SOLUTIONS

    def test_givens_that_contradict_the_answer_never_reach_a_layer(self, board: Board, blank: Blank) -> None:
        """⚠️⚠️ **Refused at the format boundary, before any layer runs.** (v36-P2-08)

        This built forty hits into the puzzle's batting total and left the original solution beside it,
        then asserted layer 2 found no completion. A package whose givens disagree with its own answer
        cannot be constructed now — in either runtime — because that board is unwinnable and the player
        has no way to discover it.
        """
        contradicting = replacing(blank(board, {"batting": [(0, 3)]}), batting_totals=(36, 36, 3, 40, 0, 5))

        with pytest.raises(PackageError, match="the solution says"):
            package(contradicting, board)

    def test_an_impossible_board_is_caught_by_layer_one_rather_than_layer_two(
        self, board: Board, blank: Blank
    ) -> None:
        """⚠️ **And putting the contradiction in both halves moves it one layer earlier, not later.**

        With the givens forced to match the solution, the only way to express *forty hits against eight
        allowed* is a solution that says so — and a solution that says so fails the identities. Layer 1
        answers it, with the columns it is off by.

        ⚠️⚠️ **This is the consequence worth naming: `Fault.NO_SOLUTION` at layer 2 is now unreachable
        through the type.** If every given equals the solution and the solution satisfies the
        identities, the solution *is* a completion — so "no completion exists" cannot arise from a
        well-formed package that passed layer 1. Layer 2's real work is `MULTIPLE`, which
        `test_cells_erased_that_were_not_forced` covers. Recorded in `todo.md`; whether the
        now-unreachable branch stays as defence in depth is an operator decision, not a test's.
        """
        impossible = replacing(board, batting_totals=(36, 36, 3, 40, 0, 5))
        puzzle = blank(impossible, {"batting": [(0, 3)]})

        verdict = verify(package(puzzle, impossible), secret=UNSIGNED, source=impossible)

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.IDENTITIES
        assert verdict.rejection.fault is Fault.BAD_DATA
        assert "hits" in verdict.rejection.detail, "the rejection does not say which column is wrong"


class TestLayerThreeCatchesAnUnreachableBoard:
    def test_it_rejects_a_board_that_cannot_be_reached_without_guessing(self, board: Board, blank: Blank) -> None:
        # Called on its own, which is what §22 means by each layer rejecting independently. This
        # board also has several completions, so `verify` would stop at layer 2 — asking layer 3
        # directly is what shows layer 3 answering its own question.
        puzzle = blank(board, {"batting": [(0, 3), (1, 3)]})

        rejection = check_derivability(package(puzzle, board), UNSIGNED, board)

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
    def test_two_batters_hits_swapped_after_generation(self, board: Board) -> None:
        """⚠️⚠️ **§22's worked example, and until this landed it passed.**

        Two batters' hits are swapped in the published artefact. Every identity still holds, the board
        still has exactly one completion, and that completion is **a different game from the one the
        source says it is** — which is precisely the case §22 names to justify a fourth layer existing
        at all.

        It passed because `check_end_to_end` compared the solved board against `package.solution`: the
        answer the same producer wrote in the same pass. A corrupted artefact carries the swap in both
        halves, so the file agreed with itself and all four layers agreed with the file. **Four layers
        that consult one answer are one layer.**

        Now the source is the original boxscore and comes in from outside the package.
        """
        rows = [list(row) for row in board.batting]
        rows[0][3], rows[8][3] = rows[8][3], rows[0][3]
        corrupted = replacing(board, batting=tuple(tuple(row) for row in rows))

        # Both halves swapped, which is what an altered artefact looks like: the puzzle gives what the
        # solution claims, so nothing before layer 4 has anything to object to.
        verdict = verify(package(corrupted, corrupted), secret=UNSIGNED, source=board)

        assert verdict.rejection is not None, "the swapped board passed every layer"
        assert verdict.rejection.layer is Layer.END_TO_END
        assert verdict.rejection.fault is Fault.MISMATCH
        # The detail names the cell and both values, because an operator reading a discard needs to
        # know which board is wrong rather than that one of them is.
        assert "bat[0].hits" in verdict.rejection.detail, verdict.rejection.detail
        assert "2 cells" in verdict.rejection.detail, "a swap moves two cells and the count should say so"

    def test_the_same_swap_passes_when_the_source_is_the_packages_own_copy(self, board: Board) -> None:
        """⚠️⚠️ **The old behaviour, kept as a test so the regression cannot return quietly.**

        Handing layer 4 the package's own solution is exactly what it used to do, and this asserts that
        doing so accepts the corrupted artefact above. It is the difference the change bought, stated as
        a fact rather than as a claim in a docstring — and it is why `source` has no default.
        """
        rows = [list(row) for row in board.batting]
        rows[0][3], rows[8][3] = rows[8][3], rows[0][3]
        corrupted = replacing(board, batting=tuple(tuple(row) for row in rows))

        verdict = verify(package(corrupted, corrupted), secret=UNSIGNED, source=corrupted)

        assert verdict.accepted, "the corrupted board no longer passes even against its own copy"

    def test_a_missing_source_raises_rather_than_falling_back(self, board: Board) -> None:
        """⚠️ **The absence of the comparison must not read as the comparison passing.** The same rule
        `secret` follows: `None` is in the signature so that it can be refused, not defaulted."""
        with pytest.raises(ValueError, match="no source boxscore"):
            verify(package(board, board), secret=UNSIGNED, source=None)

    def test_a_given_cell_that_contradicts_the_solution_never_reaches_a_layer(self, board: Board) -> None:
        """The other half of the same corruption: swapped in the puzzle only.

        ⚠️ Refused at the format boundary since v36-P2-08, before any layer runs, and **in both
        runtimes** — the client verifies no signature by design, so that refusal is the only thing
        between a tampered static file and a day nobody can win.
        """
        rows = [list(row) for row in board.batting]
        rows[0][3], rows[8][3] = rows[8][3], rows[0][3]
        altered = replacing(board, batting=tuple(tuple(row) for row in rows))

        with pytest.raises(PackageError, match="the solution says"):
            package(altered, board)


class TestTheSignatureCatchesCorruptionInTransit:
    def test_a_package_changed_after_signing(self, board: Board, blank: Blank) -> None:
        signed = sign(package(board, board), SECRET)
        tampered = Package(
            labels=("C",) * len(blank(board, {"batting": [(0, 3)]}).batting),
            pitcher_labels=("C",) * len(blank(board, {"batting": [(0, 3)]}).pitching),
            puzzle_id=signed.puzzle_id,
            puzzle=blank(board, {"batting": [(0, 3)]}),
            solution=signed.solution,
            metadata=signed.metadata,
            signature=signed.signature,
            slot_references=refs(blank(board, {"batting": [(0, 3)]})),
            offense_is_home=True,
        )

        verdict = verify(tampered, secret=PUBLIC, source=board)

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.SIGNATURE
        assert verdict.rejection.fault is Fault.CORRUPTED

    def test_an_unsigned_package_is_refused_when_a_secret_is_expected(self, board: Board) -> None:
        verdict = verify(package(board, board), secret=PUBLIC, source=board)

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.SIGNATURE

    def test_a_signed_package_passes(self, board: Board) -> None:
        assert verify(sign(package(board, board), SECRET), secret=PUBLIC, source=board).accepted
