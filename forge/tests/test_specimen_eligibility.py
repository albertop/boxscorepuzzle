"""The specimen classifier must refuse a direction whose rendered comparison does not exist.

⚠️⚠️ **v27-P3-16: `False` meant two different things and both landed in the contrast pool.** The
classifier asked `any(pa_by_lineup > 0 for ... if reached)`. That is false when the treatment reached
the target using no lineup arithmetic — a genuine contrast, which is the thing the pool is for — and
equally false when the treatment **never reached the target**, which is not an observation at all. The
second kind could be selected as the promised contrast, and `_specimen_pages()` would write
`arm on_total_erasable never reached 5 stalls` where a board was supposed to be, while the summary
announced a complete two-positive/one-contrast set.

Tested here rather than left to the sweep for the same reason `test_hand_solve_pack.py` exists: the
specimen file is the eye-check the adoption decision rests on, and **a sample that quietly replaces a
board with an absence message is an eye-check on one population presented as an eye-check on two.**

⚠️ The distinction is a measured zero against an absent observation. This project has met that one
before under another name — a null result read off medians without the per-item count.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "discovery" / "batting-order"))

from arms import BASELINE, SPECIMEN_ARMS, SPECIMEN_TARGET, Row, _classify_specimen

TREATED = next(arm for arm in SPECIMEN_ARMS if arm != BASELINE)


def _row(arm: str, *, reached: bool, lineup: int, target: int = SPECIMEN_TARGET) -> Row:
    return Row(
        game="TST190001010",
        offense="TST",
        season=1900,
        seed=1,
        arm=arm,
        target=target,
        reached=reached,
        blanks=10,
        pa_blanks=3,
        stalls=5,
        chain=20,
        families="row_identity",
        pa_by_lineup=lineup,
        pa_by_propagation=2,
        pa_by_bounding=1,
        walk_max_stalls=5,
    )


def _specimens(*arms: str) -> dict[tuple[str, int], object]:
    """A specimen map containing a page for each named arm at the specimen target."""
    return {(arm, SPECIMEN_TARGET): ("given", "solution") for arm in arms}


class TestEligibilityComesBeforeComposition:
    def test_a_treatment_that_never_reached_the_target_is_in_neither_pool(self) -> None:
        # ⚠️ The exact defect. Zero lineup steps because the arm produced nothing, not because it
        # produced a clean board. Before the fix this returned the contrast pool.
        measured = [
            _row(BASELINE, reached=True, lineup=0),
            _row(TREATED, reached=False, lineup=0),
        ]

        assert _classify_specimen(measured, _specimens(BASELINE)) is None

    def test_a_baseline_that_never_reached_the_target_is_in_neither_pool(self) -> None:
        # The other half of the page. A comparison missing its baseline is still a missing comparison.
        measured = [
            _row(BASELINE, reached=False, lineup=0),
            _row(TREATED, reached=True, lineup=0),
        ]

        assert _classify_specimen(measured, _specimens(TREATED)) is None

    def test_a_reached_treatment_with_no_lineup_steps_is_the_genuine_contrast(self) -> None:
        """⚠️ The case that must still be accepted, or the fix would close the pool entirely.

        Without this, a classifier that returned `None` for everything would pass the two tests above
        and the contrast pool would simply never fill — a guard that fixes a defect by removing the
        feature.
        """
        measured = [
            _row(BASELINE, reached=True, lineup=0),
            _row(TREATED, reached=True, lineup=0),
        ]

        assert _classify_specimen(measured, _specimens(*SPECIMEN_ARMS)) == "negative"

    def test_a_reached_treatment_using_lineup_arithmetic_is_positive(self) -> None:
        measured = [
            _row(BASELINE, reached=True, lineup=0),
            _row(TREATED, reached=True, lineup=4),
        ]

        assert _classify_specimen(measured, _specimens(*SPECIMEN_ARMS)) == "positive"

    @pytest.mark.parametrize("present", [(), (BASELINE,), (TREATED,)])
    def test_a_missing_specimen_page_disqualifies_whatever_the_rows_say(self, present: tuple[str, ...]) -> None:
        """⚠️ The rows and the specimen map can disagree, and the page is what the reader sees.

        A row may say `reached` while no specimen was retained for that arm at this target. The
        promised artifact is the rendered page, so **the page's existence is the eligibility test** —
        not a field that merely implies it.
        """
        measured = [
            _row(BASELINE, reached=True, lineup=0),
            _row(TREATED, reached=True, lineup=4),
        ]

        assert _classify_specimen(measured, _specimens(*present)) is None

    def test_a_row_at_another_target_cannot_qualify_a_direction(self) -> None:
        # ⚠️ The classifier is about one target. A treatment reaching 3 says nothing about the page
        # drawn at 5, and counting it would be the pooled-population defect one level down.
        measured = [
            _row(BASELINE, reached=True, lineup=0),
            _row(TREATED, reached=True, lineup=4, target=SPECIMEN_TARGET - 1),
        ]

        assert _classify_specimen(measured, _specimens(*SPECIMEN_ARMS)) is None
