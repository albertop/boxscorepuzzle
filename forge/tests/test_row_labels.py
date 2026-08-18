"""Which row a label names, and which row a footnote lands in.

⚠️ **Found by a person reading a printed board, not by any check.** A lineup came out carrying `CF-1`,
`CF-2` and `CF-3`. Three centre fielders in one game does not happen, and every identity balanced
anyway — the labels are outside the arithmetic, so all four §22 layers pass a board whose rows are
named wrong.

The label is not decoration. §7 makes it the row's only identity during play, and a footnote is
attributed to a *row*: `SF: CF-2` means one specific line, with its own plate appearances and its own
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

    def test_a_repeated_position_is_suffixed_in_order_of_appearance(self) -> None:
        # Suffixing is what keeps a footnote resolvable when two men really did share a position.
        assert _loader()._batting_labels(["CF", "SS", "CF"]) == ("CF-1", "SS", "CF-2")

    def test_a_position_held_by_one_man_is_not_suffixed(self) -> None:
        assert _loader()._batting_labels(["CF", "SS"]) == ("CF", "SS")


class TestAFootnoteBelongsToARowAndNotToAPosition:
    """The half that breaks arithmetic rather than trust."""

    def _lineup(self) -> tuple[tuple[BattingLine, ...], tuple[BatterFootnotes, ...]]:
        # Two men at the same position. The substitute made a sacrifice fly; the starter did not.
        starter = BattingLine(plate_appearances=3, at_bats=3, runs=0, hits=1, walks=0, strikeouts=0)
        substitute = BattingLine(plate_appearances=1, at_bats=0, runs=0, hits=0, walks=0, strikeouts=0)
        nothing = BatterFootnotes(hit_by_pitch=0, sacrifice_flies=0, sacrifice_hits=0, catcher_interference=0)
        sacrifice = BatterFootnotes(hit_by_pitch=0, sacrifice_flies=1, sacrifice_hits=0, catcher_interference=0)
        return (starter, substitute), (nothing, sacrifice)

    def test_the_rendered_footnote_names_the_suffixed_label(self) -> None:
        # `SF: CF` on a board where the rows are CF-1 and CF-2 is unresolvable: the player cannot tell
        # which line the term belongs to, and the row identity is what needs it.
        labels = _loader()._batting_labels(["CF", "CF"])
        _, footnotes = self._lineup()
        carriers = [labels[index] for index, note in enumerate(footnotes) if note.sacrifice_flies]

        assert carriers == ["CF-2"]

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
