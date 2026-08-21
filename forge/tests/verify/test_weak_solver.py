"""Layer 3b: the solver that reads one relation at a time.

It exists because layer 3 is stronger than a person — interval propagation to a fixed point across
forty-odd simultaneous relations — so a board can pass layer 3 and still be underivable by hand. This
is the other end of that bracket, and the fifty-board hand-solve decides which end a player sits at.

Untested code deciding a product question is worse than no code, so what is pinned here is the
*difference* between the two solvers, not merely that this one runs.
"""

from collections.abc import Callable

import pytest

from boxscore_package.format import Board, Package
from boxscore_verify.reason import derive, derive_in_view
from boxscore_verify.rules import all_cells, relations, values_of
from boxscore_verify.verify import derivable_in_view
from tests.verify.helpers import refs

Blank = Callable[[Board, dict[str, list[tuple[int, int]]]], Board]


def weakly(board: Board, **kwargs: bool) -> object:
    return derive_in_view(relations(board), all_cells(board), values_of(board), **kwargs)


class TestItSolvesWhatAnyoneCould:
    def test_a_complete_board_needs_no_work(self, board: Board) -> None:
        reached = weakly(board)

        assert reached.is_complete  # type: ignore[attr-defined]
        assert reached.values == values_of(board)  # type: ignore[attr-defined]

    def test_one_blank_is_a_subtraction(self, board: Board, blank: Blank) -> None:
        # An equation with a single unknown is what anybody does first, and it is the whole of the
        # weak solver's propagation step.
        puzzle = blank(board, {"batting": [(3, 3)]})

        reached = weakly(puzzle)

        assert reached.is_complete  # type: ignore[attr-defined]
        assert reached.values["bat[3].hits"] == 1  # type: ignore[attr-defined]

    def test_a_realistic_erasure_still_goes_through(self, board: Board, blank: Blank) -> None:
        puzzle = blank(board, {"batting": [(2, 0), (7, 4), (1, 1), (4, 3)], "pitching": [(1, 4)]})

        assert weakly(puzzle).is_complete  # type: ignore[attr-defined]


class TestItIsWeakerThanLayerThree:
    def test_bounding_can_be_switched_off_entirely(self, board: Board, blank: Blank) -> None:
        # With bounding off it is pure subtraction: an equality with exactly one unknown, nothing
        # else. That is the floor of what "no guessing" can possibly mean.
        puzzle = blank(board, {"batting": [(0, 3)]})

        assert weakly(puzzle, allow_bounding=False).is_complete  # type: ignore[attr-defined]

    def test_it_never_claims_more_than_the_strong_solver(self, board: Board, blank: Blank) -> None:
        # The bracket has to hold in the right direction. If the weak solver ever resolved a cell the
        # strong one could not, one of them would be wrong, and this is the cheapest place to notice.
        puzzle = blank(board, {"batting": [(0, 3), (1, 3), (2, 2), (5, 1)], "pitching_totals": [(0, 1)]})

        strong = derive(relations(puzzle), all_cells(puzzle), values_of(puzzle))
        weak = weakly(puzzle)

        assert set(weak.values) <= set(strong.values)  # type: ignore[attr-defined]
        for cell, value in weak.values.items():  # type: ignore[attr-defined]
            assert strong.values[cell] == value

    def test_it_reports_what_it_could_not_reach(self, board: Board, blank: Blank) -> None:
        # Two cells in one column with nothing to separate them: no single relation settles either,
        # so the weak solver stops and says so rather than guessing.
        puzzle = blank(board, {"batting": [(0, 3), (1, 3)]})

        reached = weakly(puzzle)

        assert not reached.is_complete  # type: ignore[attr-defined]
        assert "bat[0].hits" in reached.unresolved  # type: ignore[attr-defined]


class TestTheReportedProperty:
    def test_a_derivable_board_certifies(self, board: Board, blank: Blank) -> None:
        puzzle = blank(board, {"batting": [(3, 3)]})

        assert derivable_in_view(
            Package(
                labels=("C",) * len(puzzle.batting),
                pitcher_labels=("C",) * len(puzzle.pitching),
                puzzle_id="000000000000000f",
                puzzle=puzzle,
                solution=board,
                slot_references=refs(puzzle),
                offense_is_home=True,
            )
        )

    def test_an_ambiguous_board_does_not(self, board: Board, blank: Blank) -> None:
        puzzle = blank(board, {"batting": [(0, 3), (1, 3)]})

        assert not derivable_in_view(
            Package(
                labels=("C",) * len(puzzle.batting),
                pitcher_labels=("C",) * len(puzzle.pitching),
                puzzle_id="000000000000000f",
                puzzle=puzzle,
                solution=board,
                slot_references=refs(puzzle),
                offense_is_home=True,
            )
        )


class TestAnInequalityBoundsOneSideOnly:
    """⚠️⚠️ v28-P2-01: the weak solver invented exact values out of one-sided relations.

    `_bound_one_relation()` computed both ends of a finite window for every relation, then — for an
    inequality — reset `low` to zero and **left `high` alone**. That is right only when the target's
    coefficient is positive, where `c*x + rest <= k` really does cap `x` from above. With a *negative*
    coefficient the same relation is a **lower** bound and says nothing about how large the cell can
    be, so keeping the equality-derived `high` collapses an open range onto one fabricated number.

    `narrow()`, in the same module, has always had the rule right: positive coefficients tighten only
    the upper side, negative ones only the lower, and the opposite side exists only for an equality.
    **One rule, two implementations, and they disagreed** — the failure this project keeps meeting.

    What it cost: `derive_in_view()` could report a board human-derivable after writing in values the
    relations do not determine, and the values could be wrong. Layer 3b is report-only, so no invalid
    package shipped — but every recorded 3b pass/fail count was produced by this predicate, including
    the ones a decision about promoting 3b to a gate would rest on.
    """

    @staticmethod
    def _derive(relation: object, given: dict[str, int], cells: tuple[str, ...]) -> object:
        return derive_in_view((relation,), cells, given, allow_bounding=True)

    def test_a_lower_bound_does_not_become_an_exact_value(self) -> None:
        # `H - AB <= 0` is `AB >= H`. With H = 0 every non-negative AB satisfies it, so AB is unknown.
        from boxscore_verify.rules import Relation  # noqa: PLC0415

        relation = Relation(
            terms=(("h", 1), ("ab", -1)),
            constant=0,
            origin="H - AB <= 0",
            equality=False,
        )
        result = self._derive(relation, {"h": 0}, ("h", "ab"))

        assert "ab" not in result.values, (
            f"the weak solver invented at_bats = {result.values.get('ab')} from a lower bound; "
            f"a real row with H = 0 and AB = 4 satisfies this relation"
        )
        assert "ab" in result.unresolved

    def test_an_upper_bound_still_resolves_when_it_pins_the_cell(self) -> None:
        """The other half: the fix must not disable the bounding step it corrects.

        ⚠️ Without this, returning `False` from every inequality would pass the test above and quietly
        remove layer 3b's only reasoning move — a fix that works by deleting the feature.
        """
        from boxscore_verify.rules import Relation  # noqa: PLC0415

        # `AB + BB <= 0` with BB known to be 0 forces AB = 0 from above, and zero is the floor.
        relation = Relation(
            terms=(("ab", 1), ("bb", 1)),
            constant=0,
            origin="AB + BB <= 0",
            equality=False,
        )
        result = self._derive(relation, {"bb": 0}, ("ab", "bb"))

        assert result.values.get("ab") == 0, "the bounding step stopped resolving a genuine upper bound"

    @pytest.mark.parametrize(
        "erasure",
        [
            {"batting": [(0, 3)]},
            {"batting": [(0, 1), (0, 3)]},
            {"batting": [(1, 2), (1, 3), (2, 3)]},
            {"batting": [(0, 3), (1, 3), (2, 2), (5, 1)], "pitching_totals": [(0, 1)]},
            {"batting": [(3, 1), (4, 1), (5, 1), (6, 1)]},
            {"batting": [(0, 2), (0, 3), (1, 2), (1, 3)]},
            {"pitching": [(0, 1), (0, 2)]},
            {"batting": [(7, 3), (8, 3)], "batting_totals": [(0, 3)]},
        ],
    )
    def test_no_erasure_makes_the_two_solvers_disagree(self, board: Board, blank: Blank, erasure: dict) -> None:
        """⚠️⚠️ **The agreement test existed and did not fire.**

        `test_it_never_claims_more_than_the_strong_solver` asserts exactly this property, on **one**
        erasure. That erasure never produced a blank cell whose only relation was a negative-coefficient
        inequality, so the defect sat underneath a test written to catch it. A single fixture is a
        sample of one, and a sample of one is how a predicate stays wrong through a passing suite.

        Varied erasures, each asserting the weak solver writes nothing the strong solver contradicts.
        """
        puzzle = blank(board, {key: [tuple(cell) for cell in cells] for key, cells in erasure.items()})
        strong = derive(relations(puzzle), all_cells(puzzle), values_of(puzzle))
        weak = weakly(puzzle)

        wrong = {
            cell: (value, strong.values[cell])
            for cell, value in weak.values.items()  # type: ignore[attr-defined]
            if cell in strong.values and strong.values[cell] != value
        }
        assert not wrong, f"the weak solver contradicts the strong one at {wrong}"
        assert set(weak.values) <= set(strong.values), (  # type: ignore[attr-defined]
            "the weak solver resolved a cell the strong solver could not"
        )
