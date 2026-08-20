"""The PA-column buckets must put each step where its technique says, and nowhere else.

⚠️⚠️ **This is the guard the reviewer asked for, and its absence is why two numbers survived.** The
figures on the eleven gained directions are technique counts, and the whole experiment turns on one
distinction: reading a total and dividing by nine is the **cheapest** move on the board, and cornering
a cell through inequalities is the **most expensive**. `arms.py::_pa_techniques` exists to keep them
apart.

**It got that backwards once.** Its own docstring records the version that counted anything which was
not `BOUNDING` as propagation — so the cyclic step would have been filed as reasoning, which is the
precise inversion of what the experiment measures. It was fixed, and nothing was written to stop it
coming back.

⚠️ **The shape of the test is the point: a solution containing no lineup step must report zero in the
lineup bucket, and a solution containing one must report it there and nowhere else.** A count computed
by subtracting one technique from a total passes the first and fails the second, which is exactly how
`_steps()` in `confirm.py` came to call every non-division deduction *causal*.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parents[2] / "discovery" / "batting-order"
sys.path.insert(0, str(_HERE))

from arms import _pa_techniques  # noqa: E402

from boxscore_forge.solver import Technique  # noqa: E402

PA = "batting[0].plate_appearances"
OTHER_PA = "batting[1].plate_appearances"
NOT_PA = "batting[0].hits"


@dataclass(frozen=True)
class Step:
    """The two fields the bucketing reads. Built here rather than solved for, so the input is exactly
    what the assertion is about — a real solve would also have to be *arranged* to contain each case,
    which is a second thing to get wrong."""

    cell: str
    technique: Technique


def buckets(*steps: Step, erased: set[str] | None = None) -> tuple[int, int, int]:
    @dataclass(frozen=True)
    class Solution:
        deductions: tuple[Step, ...]

    return _pa_techniques(Solution(steps), erased if erased is not None else {PA, OTHER_PA, NOT_PA})


class TestEachStepLandsWhereItsTechniqueSays:
    def test_an_all_propagation_solution_reports_no_lineup_steps(self) -> None:
        """⚠️ The reviewer's test. A count that subtracts one technique from a total also passes this,
        which is why the case below is the one that matters."""
        counted = buckets(
            Step(PA, Technique.PROPAGATION),
            Step(OTHER_PA, Technique.PROPAGATION),
        )

        assert counted[0] == 0, f"a solution with no cyclic step reported lineup work: {counted}"
        assert counted == (0, 2, 0)

    def test_a_lineup_step_lands_in_the_lineup_bucket_and_nowhere_else(self) -> None:
        """⚠️⚠️ **The case a subtraction cannot pass.** Filing the cyclic step anywhere but `lineup`
        turns the cheapest move on the board into the most expensive, in the one number that decides
        whether the constraint is worth adopting."""
        counted = buckets(Step(PA, Technique.LINEUP_ARITHMETIC))

        assert counted == (1, 0, 0), f"the cyclic step was not filed as lineup work: {counted}"

    def test_a_bounded_cell_is_not_counted_as_propagation(self) -> None:
        # The inversion the docstring records: every deduction reached through an inequality *is*
        # BOUNDING, and an `else` branch swallows it.
        counted = buckets(Step(PA, Technique.BOUNDING))

        assert counted == (0, 0, 1), f"a cornered cell was filed as propagation: {counted}"

    @pytest.mark.parametrize("technique", list(Technique))
    def test_no_technique_is_counted_twice(self, technique: Technique) -> None:
        # Three buckets over one step must sum to one, whatever the technique. A rule added later that
        # matches two branches would inflate the denominator silently.
        assert sum(buckets(Step(PA, technique))) == 1, f"{technique} was counted more than once"


class TestOnlyErasedPaCellsCount:
    def test_a_cell_outside_the_pa_column_is_ignored(self) -> None:
        # The buckets are about the PA column, because that is the column the constraint speaks about.
        assert buckets(Step(NOT_PA, Technique.LINEUP_ARITHMETIC)) == (0, 0, 0)

    def test_a_pa_cell_that_was_never_erased_is_ignored(self) -> None:
        # ⚠️ A given cell is not a deduction the board bought; counting it would credit the constraint
        # with cells the player was handed.
        assert buckets(Step(PA, Technique.LINEUP_ARITHMETIC), erased=set()) == (0, 0, 0)
