"""`frozen=True` freezes the binding, not the value — so these three freeze the value too. (v36-P3-05)

⚠️⚠️ **The defect this guards is action at a distance on a result that carries its own proof.** A
`Puzzle` holds `given` *and* the `Solution` proving that board can be reasoned through; a `Solution`
holds `values` *and* the `deductions` recording how those numbers were reached. Mutating the mapping
leaves the pair in one object describing two different boards, with every difficulty figure already
computed from it silently about the one that no longer exists.

**Nothing mutates them today**, which is exactly when a guard is cheap to add and worth adding: the
convention defaults to frozen against this, and `format.py` already refuses a `list` where a tuple is
meant, one field over from `Package.metadata`.

⚠️ The verifier's copy of the idiom is deliberate duplication under §22 — a helper shared with the
generator would make the two sides agree by construction, which is the property layer 3 exists to test
rather than to assume.
"""

import pytest

from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import cell_values, shape_of
from boxscore_forge.erasure import Puzzle, erase
from boxscore_forge.solver import Solution, solve
from boxscore_verify.reason import Derivation


class TestAResultRefusesToBeEdited:
    def test_a_solution_does_not_hand_out_a_writable_mapping(self, cubs_at_braves_1968: Direction) -> None:
        solution = solve(shape_of(cubs_at_braves_1968), cell_values(cubs_at_braves_1968))
        cell = next(iter(solution.values))

        with pytest.raises(TypeError):
            solution.values[cell] = 99  # type: ignore[index]

    def test_a_puzzle_does_not_hand_out_a_writable_mapping(self, cubs_at_braves_1968: Direction) -> None:
        puzzle = erase(cubs_at_braves_1968, target_stalls=2, seed=1)

        assert puzzle is not None, "the fixture no longer reaches two stalls; pick another target"
        with pytest.raises(TypeError):
            puzzle.given[next(iter(puzzle.given))] = 99  # type: ignore[index]

    def test_a_derivation_does_not_hand_out_a_writable_mapping(self) -> None:
        derivation = Derivation(values={"bat[0].hits": 1}, unresolved=())

        with pytest.raises(TypeError):
            derivation.values["bat[0].hits"] = 99  # type: ignore[index]


class TestTheFreezeCopiesRatherThanWrapping:
    """⚠️⚠️ Without this, the freeze is a window onto something that can still change.

    `MappingProxyType(d)` over a dict the caller still holds is read-only *through the proxy* and
    fully writable through `d` — the original defect with one more step. The copy is the fix; these
    say so, because a reviewer removing the `dict()` would see every test above stay green.
    """

    def test_a_solution_is_unaffected_by_edits_to_the_dict_it_was_built_from(self) -> None:
        """⚠️ Constructed directly, and the first version of this test could not fail.

        It went through `solve()`, which builds its own `values` dict internally — so the dict the
        test held was never the one stored, and removing the copy from `__post_init__` left the test
        green while the other two went red. **A guard is checked by asking what change it would let
        through**, not by rereading what it asserts.
        """
        values = {"bat[0].hits": 1}
        solution = Solution(values=values, deductions=(), unsolved=frozenset())

        values["bat[0].hits"] = 99

        assert solution.values["bat[0].hits"] == 1

    def test_a_puzzle_is_unaffected_by_edits_to_the_dict_it_was_built_from(
        self, cubs_at_braves_1968: Direction
    ) -> None:
        given = dict(cell_values(cubs_at_braves_1968))
        cell = next(iter(given))
        shape = shape_of(cubs_at_braves_1968)
        puzzle = Puzzle(shape=shape, given=given, erased=frozenset(), solution=solve(shape, given))
        before = puzzle.given[cell]

        given[cell] = 99

        assert puzzle.given[cell] == before

    def test_a_derivation_is_unaffected_by_edits_to_the_dict_it_was_built_from(self) -> None:
        values = {"bat[0].hits": 1}
        derivation = Derivation(values=values, unresolved=())

        values["bat[0].hits"] = 99

        assert derivation.values["bat[0].hits"] == 1
