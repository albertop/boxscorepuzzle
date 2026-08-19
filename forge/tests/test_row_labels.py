"""Which row a label names, and which row a footnote lands in.

⚠️ **Found by a person reading a printed board, not by any check.** A lineup came out carrying `CF-1`,
`CF-2` and `CF-3`. Three centre fielders in one game does not happen, and every identity balanced
anyway — the labels are outside the arithmetic, so all four §22 layers pass a board whose rows are
named wrong.

The label is not decoration. §7 makes it the row's only identity during play, and a footnote is
attributed to a *row*: `SF: 9b` means one specific line, with its own plate appearances and its own
row identity. Send the term to the wrong row and that row stops balancing while the other one does
not — arithmetic broken in a way the column totals cannot reveal, because the term is present, just
in the wrong place.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

from boxscore_forge.boxscore import (
    BatterFootnotes,
    BattingLine,
    Direction,
    LineScore,
    PitchingLine,
    TeamFootnotes,
)
from boxscore_forge.identities import Identity, find_violations

_LOADER = Path(__file__).resolve().parents[2] / "discovery" / "difficulty-metrics"


def _loader() -> object:
    sys.path.insert(0, str(_LOADER))
    spec = importlib.util.spec_from_file_location("loader_measure", _LOADER / "measure.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestThePositionRule:
    """Where he played, not how he arrived — and `PH` only when it is the whole truth."""

    @pytest.mark.parametrize(
        ("appeared_at", "entered_fielding", "entered_as", "started_at", "expected"),
        [
            # ⚠️ **`started_at` used to be missing from this table**, so every "starter" case ran the
            # fallback path and the branch that fixed the two-third-basemen defect was never exercised
            # by the test written for it. The first row is that defect: a man recorded at both 3B and
            # CF whose starting lineup code is 8.
            ("3B", None, None, 8, "CF"),
            ("CF", None, None, 5, "3B"),
            ("?", None, None, 10, "DH"),
            ("DH", None, None, 10, "DH"),
            # A starter's own code wins over anything the flags say.
            ("P", None, None, 2, "C"),
            # The defect as it reached a substitute: recorded at centre, entered in right.
            ("CF", 9, 11, None, "RF"),
            # A pinch hitter who stayed in at centre is a centre fielder.
            ("PH", 8, 11, None, "CF"),
            # The largest group in the 7%: he batted for the designated hitter without taking the slot.
            ("DH", None, 11, None, "PH"),
            ("DH", None, 12, None, "PR"),
            # `PH` is the whole truth here: he came in to bat and left.
            ("?", None, 11, None, "PH"),
            # No substitution row and no lineup code: fall back on what he is recorded at.
            ("CF", None, None, None, "CF"),
            ("?", None, 10, None, "DH"),
        ],
    )
    def test_the_label_names_the_position(
        self,
        appeared_at: str,
        entered_fielding: int | None,
        entered_as: int | None,
        started_at: int | None,
        expected: str,
    ) -> None:
        assert _loader()._position(appeared_at, entered_fielding, entered_as, started_at) == expected

    def test_the_starting_lineup_code_beats_the_recorded_flags(self) -> None:
        # The assertion that would have caught the original defect, stated on its own rather than as
        # one row of a table: the two disagree, and the lineup wins.
        assert _loader()._position("3B", None, None, 8) != _loader()._position("3B", None, None, None)

    def test_the_label_is_the_position_and_nothing_else(self) -> None:
        # ⚠️ The suffix is gone. It existed so a footnote could name a unique row, and the reference
        # moved to the slot, which identifies a row without help. Two CF rows in different slots are
        # two rows reading CF — what a boxscore shows and what actually happened.
        assert _loader()._batting_labels(["CF", "SS", "CF"]) == ("CF", "SS", "CF")

    def test_repeats_are_not_numbered_however_many(self) -> None:
        assert _loader()._batting_labels(["P", "P", "P"]) == ("P", "P", "P")


class TestAFootnoteBelongsToARowAndNotToAPosition:
    """The half that breaks arithmetic rather than trust."""

    def _lineup(self) -> tuple[tuple[BattingLine, ...], tuple[BatterFootnotes, ...]]:
        # Two men at the same position. The substitute made a sacrifice fly; the starter did not.
        starter = BattingLine(plate_appearances=3, at_bats=3, runs=0, hits=1, walks=0, strikeouts=0)
        substitute = BattingLine(plate_appearances=1, at_bats=0, runs=0, hits=0, walks=0, strikeouts=0)
        nothing = BatterFootnotes(hit_by_pitch=0, sacrifice_flies=0, sacrifice_hits=0, catcher_interference=0)
        sacrifice = BatterFootnotes(hit_by_pitch=0, sacrifice_flies=1, sacrifice_hits=0, catcher_interference=0)
        return (starter, substitute), (nothing, sacrifice)

    def test_the_rendered_footnote_names_the_slot_reference(self) -> None:
        # `SF: CF` on a board with two CF rows is unresolvable, and so is `SF: CF-2` once the suffix
        # numbers by position while the indentation groups by slot. The slot reference is neither: it
        # names a row, and it is the same string the slot cell prints.
        references = _loader().slot_references([9, 9])
        _, footnotes = self._lineup()
        carriers = [references[index] for index, note in enumerate(footnotes) if note.sacrifice_flies]

        assert carriers == ["9b"]

    def _board(self, footnotes: tuple[BatterFootnotes, ...], rows: tuple[BattingLine, ...]) -> Direction:
        """Only the row identity is under test, so the rest of the board is the smallest thing that
        lets `find_violations` run. Every other fault is filtered out by the caller."""
        totals = BattingLine(plate_appearances=4, at_bats=3, runs=0, hits=1, walks=0, strikeouts=0)
        return Direction(
            batting=rows,
            batting_totals=totals,
            batter_footnotes=footnotes,
            footnote_totals=BatterFootnotes(
                hit_by_pitch=0, sacrifice_flies=1, sacrifice_hits=0, catcher_interference=0
            ),
            team_footnotes=TeamFootnotes(left_on_base=1),
            pitching=(PitchingLine(outs=3, hits=1, runs=0, earned_runs=0, walks=0, strikeouts=0),),
            pitching_totals=PitchingLine(outs=3, hits=1, runs=0, earned_runs=0, walks=0, strikeouts=0),
            line_score=LineScore(
                offense_by_inning=(0,),
                defense_by_inning=(0,),
                offense_runs=0,
                offense_hits=1,
                offense_errors=0,
                defense_runs=0,
                defense_hits=0,
                defense_errors=0,
            ),
        )

    def test_the_term_balances_in_its_own_row_and_would_break_the_other(self) -> None:
        rows, footnotes = self._lineup()

        good = [
            fault
            for fault in find_violations(self._board(footnotes, rows))
            if fault.identity is Identity.ROW_PLATE_APPEARANCES
        ]

        assert not good

        # ⚠️ The same term, one row up. Every column total is unchanged — the sacrifice fly is still
        # on the board and still sums to one — and both rows now fail their identity. This is what a
        # mislabelled row does, and why the column sums cannot reveal it.
        swapped = [
            fault
            for fault in find_violations(self._board((footnotes[1], footnotes[0]), rows))
            if fault.identity is Identity.ROW_PLATE_APPEARANCES
        ]

        assert len(swapped) == 2


class TestTheSlotReferenceHasOneSource:
    """The slot cell and the footnote apply the same condition, so they call the same function.

    ⚠️ Two places applying one rule is the defect this project spent a day closing — three erasable
    definitions, two copies of the accepted-source list, two docstrings stating opposite rules. A cell
    reading `9b` beside a footnote saying `9c` would be that defect where the player can see it.
    """

    def test_a_slot_with_one_row_carries_no_letter(self) -> None:
        # Never `2a` when there is no `2b`: the letter is the signal that a slot is shared.
        assert _loader().slot_references([1, 2, 3]) == ("1", "2", "3")

    def test_a_shared_slot_letters_every_one_of_its_rows(self) -> None:
        assert _loader().slot_references([1, 2, 2, 3]) == ("1", "2a", "2b", "3")

    def test_it_applies_to_every_slot_not_only_the_pitcher(self) -> None:
        # Slot 9 dominates the examples only because the pitcher is the position most substituted.
        assert _loader().slot_references([5, 5, 9]) == ("5a", "5b", "9")

    def test_three_in_a_slot_keep_counting(self) -> None:
        assert _loader().slot_references([9, 9, 9]) == ("9a", "9b", "9c")

    def test_the_cell_and_the_footnote_are_the_same_string_for_the_same_row(self) -> None:
        """⚠️ **This assigned both names from one expression and was a tautology**: it stayed green if
        either consumer stopped calling `slot_references` at all, which is the only thing it existed to
        prevent. It reads the two real consumers now — the slot cell the table draws and the reference
        the footnote line prints — and requires them to agree.
        """
        import importlib.util  # noqa: PLC0415
        import sys  # noqa: PLC0415
        from types import SimpleNamespace  # noqa: PLC0415

        handsolve = Path(__file__).resolve().parents[2] / "discovery" / "hand-solve"
        for extra in (handsolve, handsolve.parents[0] / "difficulty-metrics"):
            sys.path.insert(0, str(extra))
        spec = importlib.util.spec_from_file_location("build_pack_parity", handsolve / "build_pack.py")
        assert spec is not None and spec.loader is not None
        pack = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pack)

        from boxscore_package.format import Board, LineScore  # noqa: PLC0415

        slots = (9, 9)
        board = Board(
            batting=((1, 1, 0, 0, 0, 0), (1, 1, 0, 0, 0, 0)),
            batting_totals=(2, 2, 0, 0, 0, 0),
            footnotes=((0, 0, 0, 0), (0, 0, 1, 0)),
            footnote_totals=(0, 0, 1, 0),
            left_on_base=1,
            pitching=((3, 0, 0, 0, 0, 0),),
            pitching_totals=(3, 0, 0, 0, 0, 0),
            line_score=LineScore((0,), (0,), 0, 0, 0, 0, 0, 0),
        )
        loaded = SimpleNamespace(
            offense_is_home=True, labels=("P", "P"), pitcher_labels=("SP",), slots=slots, direction=None
        )

        drawn = [str(cell) for cell in pack.board_table(board, loaded, solved=False)._cellvalues[3]]
        printed = pack.footnote_line(board, slots)

        assert drawn[0] == "9b", f"the table drew {drawn[0]!r} for the second row of slot 9"
        assert "SH: 9b" in printed, f"the footnote line printed {printed!r}"

    def test_every_reference_carries_its_slot_number(self) -> None:
        # `9b`, never a bare `b`. The footnote prints the same string the cell does, so finding the
        # row is recognition rather than composing the number from the row above.
        assert all(reference[0].isdigit() for reference in _loader().slot_references([1, 9, 9, 9]))


class TestAFootnoteReferenceNamesExactlyOneRow:
    """The invariant that replaces the retired ambiguity experiment.

    ⚠️ That experiment grouped rows by position label and erased their footnote cells as one ambiguous
    domain. Labels are bare positions now and **42.1% of repeated position labels span more than one
    lineup slot**, so it would have built a domain over men who never replaced each other and reported
    the solver's reaction as footnote ambiguity.

    The live question — whether an unassigned footnote resolves — is measured per slot group elsewhere.
    What belongs here is the construction invariant: **a reference must name one row.** A duplicate is
    a bug in `slot_references`, not a finding about solvers.
    """

    def test_every_reference_is_unique(self) -> None:
        for slots in ([1, 2, 3], [9, 9, 9], [1, 2, 2, 3, 9, 9], [5, 5, 5, 5, 5], list(range(1, 10))):
            references = _loader().slot_references(slots)

            assert len(set(references)) == len(references), f"{slots} produced {references}"

    def test_two_men_at_one_position_in_different_slots_get_different_references(self) -> None:
        # The case the retired experiment would have called ambiguous: same label, different slot.
        labels = _loader()._batting_labels(["CF", "SS", "CF"])
        references = _loader().slot_references([2, 3, 6])

        assert labels[0] == labels[2] == "CF"
        assert references[0] != references[2]
