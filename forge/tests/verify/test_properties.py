"""Properties, because the identities are invariants and invariants are what property tests are for.

`docs/python-conventions.md` calls this the highest-value testing investment for validation code, and
the reason is visible here: a boxscore has to satisfy a dozen equations at once, and the boards that
break a verifier are the ones nobody thinks to write down — the batter with no plate appearances, the
game with a single pitcher, the team that scored nothing.

Boards are **built to satisfy §3** rather than sampled from anywhere, so a failure means the verifier
disagrees with the design document, which is the only thing it is supposed to agree with.
"""

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from hypothesis import given
from hypothesis import strategies as st

from boxscore_package.format import Board, LineScore, Package
from boxscore_package.signing import SignatureError, sign
from boxscore_package.signing import verify as verify_signature
from boxscore_verify.reason import derive, solutions
from boxscore_verify.rules import all_cells, relations, values_of
from boxscore_verify.verify import UNSIGNED, Fault, Layer, verify

_KEY = Ed25519PrivateKey.generate()
SECRET = _KEY
"""⚠️ **A key pair, not a shared secret.** The forge signs with the private half and `serve` verifies
with the public one, which is the property a MAC cannot express: every verifier of an HMAC is also a
signer, so the verification key on the VPS *was* the signing authority (§33). Generated per run — a
test key checked into the repository is a key anybody can sign with."""

PUBLIC = _KEY.public_key()


def _split(draw: st.DrawFn, total: int, parts: int) -> list[int]:
    """Break a total into `parts` non-negative pieces, so pitching lines add up by construction."""
    cuts = sorted(draw(st.lists(st.integers(0, total), min_size=parts - 1, max_size=parts - 1)))
    edges = [0, *cuts, total]
    return [edges[index + 1] - edges[index] for index in range(parts)]


@st.composite
def boards(draw: st.DrawFn) -> Board:
    batters = draw(st.integers(9, 13))
    batting: list[list[int]] = []
    notes: list[list[int]] = []
    for _ in range(batters):
        at_bats = draw(st.integers(0, 5))
        walks = draw(st.integers(0, 2))
        hbp, sf, sh, ci = (draw(st.integers(0, 1)) for _ in range(4))
        plate = at_bats + walks + hbp + sf + sh + ci
        hits = draw(st.integers(0, at_bats))
        strikeouts = draw(st.integers(0, at_bats))
        runs = draw(st.integers(0, plate))
        batting.append([plate, at_bats, runs, hits, walks, strikeouts])
        notes.append([hbp, sf, sh, ci])

    totals = [sum(row[index] for row in batting) for index in range(6)]
    note_totals = [sum(row[index] for row in notes) for index in range(4)]

    # PA = Outs + R + LOB, so choosing one of the two fixes the other. Nothing else can be free here.
    left_on_base = draw(st.integers(0, max(totals[0] - totals[2], 0)))
    outs = totals[0] - totals[2] - left_on_base

    pitchers = draw(st.integers(1, 4))
    runs_split = _split(draw, totals[2], pitchers)
    columns: list[list[int]] = [
        _split(draw, outs, pitchers),
        _split(draw, totals[3], pitchers),
        runs_split,
        [draw(st.integers(0, runs_split[index])) for index in range(pitchers)],
        _split(draw, totals[4], pitchers),
        _split(draw, totals[5], pitchers),
    ]
    pitching = [[columns[column][index] for column in range(6)] for index in range(pitchers)]
    pitching_totals = [sum(row[index] for row in pitching) for index in range(6)]

    innings = [0] * 9
    for _ in range(totals[2]):
        innings[draw(st.integers(0, 8))] += 1

    return Board(
        batting=tuple(tuple(row) for row in batting),
        batting_totals=tuple(totals),
        footnotes=tuple(tuple(row) for row in notes),
        footnote_totals=tuple(note_totals),
        left_on_base=left_on_base,
        pitching=tuple(tuple(row) for row in pitching),
        pitching_totals=tuple(pitching_totals),
        line_score=LineScore(
            offense_by_inning=tuple(innings),
            defense_by_inning=(0,) * 9,
            offense_runs=totals[2],
            offense_hits=totals[3],
            offense_errors=0,
            defense_runs=0,
            defense_hits=0,
            defense_errors=0,
        ),
    )


def _package(puzzle: Board, source: Board) -> Package:
    return Package(puzzle_id="property", puzzle=puzzle, solution=source)


class TestABoardBuiltFromTheIdentitiesSatisfiesThem:
    @given(board=boards())
    def test_it_passes_every_layer(self, board: Board) -> None:
        verdict = verify(_package(board, board), secret=UNSIGNED)

        assert verdict.accepted, verdict.rejection

    @given(board=boards(), index=st.integers(0, 10_000))
    def test_changing_one_cell_anywhere_breaks_it(self, board: Board, index: int) -> None:
        # Every cell sits in at least one equality — that is what makes the board a system rather
        # than a table — so moving any one of them by one must be visible to layer 1.
        cells = all_cells(board)
        target = cells[index % len(cells)]
        broken = dict(values_of(board))
        broken[target] += 1

        faults = [
            relation
            for relation in relations(board)
            if relation.equality
            and sum(coefficient * broken[cell] for cell, coefficient in relation.terms) != relation.constant
        ]

        assert faults, f"moving {target} by one broke nothing"


class TestSolvingAgreesWithItself:
    @given(board=boards())
    def test_a_complete_board_has_exactly_itself_as_a_solution(self, board: Board) -> None:
        found = solutions(relations(board), all_cells(board), values_of(board), limit=2)

        assert len(found) == 1
        assert found[0] == values_of(board)

    @given(board=boards())
    def test_deriving_a_complete_board_changes_nothing(self, board: Board) -> None:
        reached = derive(relations(board), all_cells(board), values_of(board))

        assert reached.is_complete
        assert reached.values == values_of(board)

    @given(board=boards(), index=st.integers(0, 10_000))
    def test_erasing_a_single_cell_leaves_a_puzzle_that_is_unique_and_derivable(self, board: Board, index: int) -> None:
        # One blank is always forced: the cell sits in an equation whose every other term is given,
        # which is a subtraction. If this ever fails, either the relations are wrong or a cell has
        # escaped the system entirely.
        cells = all_cells(board)
        target = cells[index % len(cells)]
        given_cells = {cell: value for cell, value in values_of(board).items() if cell != target}

        found = solutions(relations(board), cells, given_cells, limit=2)
        reached = derive(relations(board), cells, given_cells)

        assert len(found) == 1
        assert reached.is_complete
        assert reached.values[target] == values_of(board)[target]


class TestTheSignatureTracksTheContent:
    @given(board=boards())
    def test_signing_then_verifying_round_trips(self, board: Board) -> None:
        verify_signature(sign(_package(board, board), SECRET), PUBLIC)

    @given(board=boards(), index=st.integers(0, 10_000))
    def test_any_change_to_the_published_half_breaks_the_signature(self, board: Board, index: int) -> None:
        signed = sign(_package(board, board), SECRET)
        # The board is complete, so the None branch never runs; it is here to keep the row typed as
        # integers rather than as the format's `int | None`.
        rows = [[0 if value is None else value for value in row] for row in board.batting]
        row = index % len(rows)
        rows[row][0] += 1
        tampered = Package(
            puzzle_id=signed.puzzle_id,
            puzzle=Board(
                batting=tuple(tuple(entry) for entry in rows),
                batting_totals=board.batting_totals,
                footnotes=board.footnotes,
                footnote_totals=board.footnote_totals,
                left_on_base=board.left_on_base,
                pitching=board.pitching,
                pitching_totals=board.pitching_totals,
                line_score=board.line_score,
            ),
            solution=signed.solution,
            metadata=signed.metadata,
            signature=signed.signature,
        )

        with pytest.raises(SignatureError):
            verify_signature(tampered, PUBLIC)

    @given(board=boards())
    def test_the_signature_survives_the_publishing_step(self, board: Board) -> None:
        # The receiver holds only the published half, so the signature has to check there or it is
        # unverifiable at the one place it matters. What publishing removes is the leaking metadata,
        # and the signature is taken over the published shape so removing it changes nothing.
        signed = sign(_package(board, board), SECRET)

        verify_signature(signed.published(), PUBLIC)

    @given(board=boards())
    def test_altering_the_solution_breaks_the_signature(self, board: Board) -> None:
        # ⚠️ New, and the reason the signing payload changed. The solution now travels with the
        # puzzle (§23), so a corrupted transfer could alter the answer a player is shown at the end.
        # Anything that travels is signed.
        signed = sign(_package(board, board), SECRET)
        rows = [list(row) for row in board.batting]
        rows[0][3] = (rows[0][3] or 0) + 1
        altered = Package(
            puzzle_id=signed.puzzle_id,
            puzzle=signed.puzzle,
            solution=Board(
                batting=tuple(tuple(entry) for entry in rows),
                batting_totals=board.batting_totals,
                footnotes=board.footnotes,
                footnote_totals=board.footnote_totals,
                left_on_base=board.left_on_base,
                pitching=board.pitching,
                pitching_totals=board.pitching_totals,
                line_score=board.line_score,
            ),
            signature=signed.signature,
        )

        with pytest.raises(SignatureError):
            verify_signature(altered, PUBLIC)


class TestRejectionsAreAttributed:
    @given(board=boards())
    def test_an_unsigned_package_is_a_signature_failure_not_a_puzzle_failure(self, board: Board) -> None:
        verdict = verify(_package(board, board), secret=PUBLIC)

        assert verdict.rejection is not None
        assert verdict.rejection.layer is Layer.SIGNATURE
        assert verdict.rejection.fault is Fault.CORRUPTED
