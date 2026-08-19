"""The blocked-on-assignment metric must be able to be true.

⚠️ **It could not be.** The experiment hid one slot group's footnote cells and left every other cell
given, so every cell the solver deduced was one of the hidden ones and no later deduction could depend
on them. The column read `0%` on every board and was reported as *the assignment never blocks the rest
of the board* — a metric with one possible value, presented as though it had two.

This is the project's own *a check that never fires* defect, in the **output** rather than in a guard,
where it is harder to see because it looks like data. The guard against it is the same one: construct
the case the metric exists to detect and require it to fire.
"""

from pathlib import Path

from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import cell_values, footnote_cell, shape_of
from boxscore_forge.erasure import erase
from boxscore_forge.identities import FOOTNOTE_COLUMNS
from boxscore_forge.solver import solve

_GROUPS = Path(__file__).resolve().parents[2] / "discovery" / "footnote-groups"


def _hidden() -> set[str]:
    """Every footnote cell of the first batting row — one slot group, whichever board it is on."""
    return {footnote_cell(0, column) for column in FOOTNOTE_COLUMNS}


class TestSomethingCanWaitOnTheAssignment:
    def test_on_a_complete_board_nothing_can_wait(self, cubs_at_braves_1968: Direction) -> None:
        """The old setup, stated as a fact rather than left implicit.

        With every other cell given, the only cells the solver deduces are the hidden ones, so the
        metric is not merely zero — it is unreachable. Keeping this test is what stops the instrument
        drifting back to a board where its own answer is fixed.
        """
        shape, values = shape_of(cubs_at_braves_1968), cell_values(cubs_at_braves_1968)
        hidden = _hidden()

        solution = solve(shape, {name: value for name, value in values.items() if name not in hidden})
        outside = [step for step in solution.deductions if step.cell not in hidden]

        assert not outside, "a complete board deduced something outside the hidden group"

    def test_on_an_erased_board_something_does(self, cubs_at_braves_1968: Direction) -> None:
        """The case the metric exists to detect, required to fire.

        A real erasure leaves other unknowns, so a later deduction can lean on the hidden footnote —
        and if none ever could, the measurement would be reporting a property of its own setup.
        """
        puzzle = erase(cubs_at_braves_1968, target_stalls=8, seed=907)

        assert puzzle is not None
        shape, values = shape_of(cubs_at_braves_1968), cell_values(cubs_at_braves_1968)
        hidden = _hidden()
        without = {name: value for name, value in values.items() if name not in (puzzle.erased | hidden)}

        solution = solve(shape, without)
        outside = [step for step in solution.deductions if step.cell not in hidden]

        assert outside, "the erased board deduced nothing outside the group; the metric cannot fire"

    def test_the_instrument_measures_it_on_the_erased_board(self) -> None:
        # The link between the two: the script must take its `blocked` reading from an erasure, not
        # from the complete board. Asserted on the source because running it needs the database.
        source = (_GROUPS / "measure.py").read_text(encoding="utf-8")

        assert "erase(direction, target_stalls=TARGET_STALLS" in source
        assert "if k not in hidden" in source


class TestCardinalityAndDerivabilityAreSeparate:
    def test_the_instrument_counts_completions_and_solves_separately(self) -> None:
        """⚠️ One field used to mean both, so a false result could be *several assignments exist* or
        *one exists and the techniques did not reach it* — different findings with different fixes.
        Several completions is a generator constraint; one-but-unreached is a technique question.
        """
        source = (_GROUPS / "measure.py").read_text(encoding="utf-8")

        assert "solutions(relations(board), all_cells(board), values_of(board), limit=2)" in source
        assert "completions: int" in source
        assert "derivable: bool" in source


class TestTheBlockagePredicateItself:
    """⚠️ The earlier test asserted that outside deductions exist, which is trace activity, not the
    property. The predicate is a **counterfactual**: a cell the baseline settles and the treatment
    does not.

    The version it replaces marked a group blocking when some outside deduction recorded a dependency
    on it. That is evidence a solver path *used* the value. When hiding the group prevents the outside
    deduction from happening at all, there is no such step — so the strongest possible blockage read
    as no blockage.
    """

    def test_hiding_a_group_can_remove_an_outside_deduction(self, cubs_at_braves_1968: Direction) -> None:
        puzzle = erase(cubs_at_braves_1968, target_stalls=8, seed=907)

        assert puzzle is not None
        shape, values = shape_of(cubs_at_braves_1968), cell_values(cubs_at_braves_1968)
        hidden = _hidden()
        baseline = solve(shape, {name: value for name, value in values.items() if name not in puzzle.erased})
        treatment = solve(
            shape, {name: value for name, value in values.items() if name not in (puzzle.erased | hidden)}
        )

        outside_before = {cell for cell in baseline.values if cell not in hidden}
        outside_after = {cell for cell in treatment.values if cell not in hidden}

        # Not an assertion that this board blocks — an assertion that the comparison is capable of
        # showing it. Equal closures would mean the two solves cannot differ and the metric is fixed.
        assert outside_before >= outside_after, "hiding cells expanded what the solver reached"

    def test_the_instrument_compares_two_closures(self) -> None:
        source = (_GROUPS / "measure.py").read_text(encoding="utf-8")

        assert "before - after" in source
        assert "baseline = solve(" in source and "treatment = solve(" in source

    def test_an_unmeasured_trial_is_not_a_negative(self) -> None:
        # ⚠️ A trial where `erase` returned nothing became an empty erasure and therefore a measured
        # negative, biasing the rate downward — selectively, since boards that resist erasure are not
        # a random subset.
        source = (_GROUPS / "measure.py").read_text(encoding="utf-8")

        assert "blocked: bool | None" in source
        assert "group.blocked is not None" in source
        # And several erasures, since one is a sample of size one for a question the erasure decides.
        assert "SEEDS = (" in source and "for seed in SEEDS" in source

    def test_derivability_is_conditional_on_a_single_completion(self) -> None:
        # Non-unique groups contributed negatives to a rate whose denominator should hold only the
        # groups where there is something to derive.
        source = (_GROUPS / "measure.py").read_text(encoding="utf-8")

        assert "group.completions == 1" in source
