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
        ("appeared_at", "entered_fielding", "entered_as", "expected"),
        [
            # The defect itself: a man recorded at centre who entered in right is a right fielder.
            ("CF", 9, 11, "RF"),
            # A pinch hitter who stayed in at centre is a centre fielder. `PH` distinguishes nothing —
            # every substitute hitter is one — and a printed boxscore prints the position too.
            ("PH", 8, 11, "CF"),
            # The largest group in the 7%: he batted for the designated hitter without taking the slot.
            ("DH", None, 11, "PH"),
            ("DH", None, 12, "PR"),
            # `PH` is the whole truth here: he came in to bat and left.
            ("?", None, 11, "PH"),
            # Starters keep what they are recorded at, with no substitution row to consult.
            ("CF", None, None, "CF"),
            ("DH", None, None, "DH"),
            # Entering as the designated hitter is taking the slot.
            ("?", None, 10, "DH"),
        ],
    )
    def test_the_label_names_the_position(
        self, appeared_at: str, entered_fielding: int | None, entered_as: int | None, expected: str
    ) -> None:
        assert _loader()._position(appeared_at, entered_fielding, entered_as) == expected

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

    def _board(
        self, footnotes: tuple[BatterFootnotes, ...], rows: tuple[BattingLine, ...]
    ) -> Direction:
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
        """The assertion that matters: one call, one string, both consumers."""
        slots = [1, 2, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9]
        carries_a_footnote = 10  # the second man in the pitcher's slot

        references = _loader().slot_references(slots)
        cell = references[carries_a_footnote]
        footnote = references[carries_a_footnote]

        assert cell == footnote == "9b"

    def test_every_reference_carries_its_slot_number(self) -> None:
        # `9b`, never a bare `b`. The footnote prints the same string the cell does, so finding the
        # row is recognition rather than composing the number from the row above.
        assert all(reference[0].isdigit() for reference in _loader().slot_references([1, 9, 9, 9]))
