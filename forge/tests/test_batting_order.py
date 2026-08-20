"""The lineup is a cycle nobody can skip, so a slot never bats fewer times than the one after it.

⚠️ **Per SLOT, never per player.** A slot is every man who occupied it, starters and substitutes
together. Stated per row the claim is false immediately — a substitute bats fewer times than the man he
replaced — and it is false in a way that still balances every identity, which is the dangerous kind.

⚠️ **Off unless asked for.** Both implementations take the slots and emit nothing without them. A default
of one row per slot would be wrong on every board carrying a substitution and wrong *silently*, so
absence means *no constraint* rather than *a guessed one*.

⚠️ **Two implementations on purpose (§22).** The generator has one and the verifier has another, written
from the rule rather than from each other. If they were one function a mistake in it would pass
validation by being present on both sides. What they share is the sentence at the top of this file — and
the last test here is the one that makes that sharing answerable.
"""

import pytest

from boxscore_forge.constraints import BoardShape, batting_cell, inequalities
from boxscore_forge.identities import Identity
from boxscore_package.format import Board, LineScore
from boxscore_verify.rules import relations

_SHAPE = {"batter_count": 9, "pitcher_count": 2, "offense_innings": 9, "defense_innings": 9}


def _generator(slots: tuple[int, ...], batters: int = 9) -> list:
    shape = BoardShape(**{**_SHAPE, "batter_count": batters}, slots=slots)
    return [rule for rule in inequalities(shape) if rule.origin is Identity.BATTING_ORDER]


def _board(batters: int) -> Board:
    return Board(
        batting=((0,) * 6,) * batters,
        batting_totals=(0,) * 6,
        footnotes=((0,) * 4,) * batters,
        footnote_totals=(0,) * 4,
        left_on_base=0,
        pitching=((0,) * 6,),
        pitching_totals=(0,) * 6,
        line_score=LineScore((0,), (0,), 0, 0, 0, 0, 0, 0),
    )


def _verifier(slots: tuple[int, ...], batters: int = 9) -> list:
    return [rule for rule in relations(_board(batters), slots) if rule.origin.startswith("PA(slot")]


class TestItIsOffUnlessAskedFor:
    def test_the_generator_emits_nothing_without_slots(self) -> None:
        assert _generator(()) == []

    def test_the_verifier_emits_nothing_without_slots(self) -> None:
        assert _verifier(()) == []

    def test_and_something_with_them_so_the_test_above_is_not_vacuous(self) -> None:
        slots = (1, 2, 3, 4, 5, 6, 7, 8, 9)

        assert len(_generator(slots)) == 8
        assert len(_verifier(slots)) == 8


class TestOneRelationPerAdjacentPairOfSlots:
    def test_nine_distinct_slots_give_eight_relations(self) -> None:
        assert len(_generator((1, 2, 3, 4, 5, 6, 7, 8, 9))) == 8

    def test_a_shared_slot_is_one_term_of_several_cells(self) -> None:
        """⚠️ The whole hypothesis, expressed. Three men in slot 9 are **one** figure, not three."""
        rules = _generator((1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9), batters=11)
        last = rules[-1]
        negative = {term.cell for term in last.terms if term.coefficient < 0}

        assert len(rules) == 8, "eleven rows in nine slots still make eight adjacent pairs"
        assert negative == {batting_cell(index, "plate_appearances") for index in (8, 9, 10)}

    def test_it_only_ever_speaks_about_plate_appearances(self) -> None:
        # Every other column is unaffected by the order: a slot that bats more does not thereby walk
        # more. Asserted because a copy-and-paste into another column would still balance.
        for rule in _generator((1, 2, 3, 4, 5, 6, 7, 8, 9)):
            assert all(term.cell.endswith(".plate_appearances") for term in rule.terms)

    def test_a_slot_count_that_does_not_match_the_rows_is_refused(self) -> None:
        # Both sides. A mismatch means the caller has the wrong lineup, and applying it to whatever rows
        # happen to be there would emit relations about the wrong batters.
        with pytest.raises(ValueError, match="slots against"):
            _generator((1, 2, 3), batters=9)
        with pytest.raises(ValueError, match="slots against"):
            _verifier((1, 2, 3), batters=9)


class TestTheRelationHoldsAndFailsWhereItShould:
    @staticmethod
    def _satisfied(rule: object, values: dict[str, int]) -> bool:
        return sum(term.coefficient * values[term.cell] for term in rule.terms) >= 0

    def _values(self, per_slot: tuple[int, ...]) -> dict[str, int]:
        return {batting_cell(index, "plate_appearances"): value for index, value in enumerate(per_slot)}

    def test_a_cyclic_distribution_satisfies_every_relation(self) -> None:
        # 38 plate appearances: four turns of nine and two over, so slots 1 and 2 bat five times.
        values = self._values((5, 5, 4, 4, 4, 4, 4, 4, 4))

        assert all(self._satisfied(rule, values) for rule in _generator(tuple(range(1, 10))))

    def test_a_flat_distribution_satisfies_them_too(self) -> None:
        """⚠️ A total divisible by nine is whole turns and **no** cut point at all.

        The relation is *at most one* step down, not exactly one, and this is the case that separates
        those two readings. Getting it wrong would reject the cleanest board there is.
        """
        values = self._values((4,) * 9)

        assert all(self._satisfied(rule, values) for rule in _generator(tuple(range(1, 10))))

    def test_a_rise_going_down_the_order_breaks_it(self) -> None:
        values = self._values((4, 5, 4, 4, 4, 4, 4, 4, 4))

        assert not all(self._satisfied(rule, values) for rule in _generator(tuple(range(1, 10))))

    def test_the_relation_is_about_the_slot_sum_and_not_the_row(self) -> None:
        """The case a per-row reading gets wrong, and it is the ordinary case rather than a corner.

        Slot 9 is a starter with 1 and a substitute with 3. Per row, `1` looks like a fall from slot 8's
        `4` and `3` looks fine; as a slot it is 4 and the order holds.
        """
        rules = _generator((1, 2, 3, 4, 5, 6, 7, 8, 9, 9), batters=10)
        values = self._values((4, 4, 4, 4, 4, 4, 4, 4, 1, 3))

        assert all(self._satisfied(rule, values) for rule in rules)


class TestTheTwoImplementationsAgree:
    """⚠️ §22 keeps them apart; this keeps them answerable to one rule.

    ⚠️ **They are compared by row index, not by cell name.** The two use different naming grammars on
    purpose — `batting[0].plate_appearances` against `bat[0].plate_appearances` — because `format.py`
    fixes the column *order* and nothing else, so each side names cells however it likes internally. A
    test comparing names would have been comparing spellings and would fail on a rename that changed
    nothing. What must match is **which rows each relation is about**, and in which group.

    The sign convention is each side's own business too, and the last test here records that they differ.
    """

    @staticmethod
    def _rows(cells: object) -> frozenset[int]:
        import re  # noqa: PLC0415

        return frozenset(int(re.search(r"\[(\d+)\]", cell).group(1)) for cell in cells)

    @pytest.mark.parametrize(
        "slots",
        [
            (1, 2, 3, 4, 5, 6, 7, 8, 9),
            (1, 2, 3, 4, 5, 6, 7, 8, 9, 9),
            (1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9),
            (1, 2, 3, 4, 5, 5, 6, 7, 8, 9),
        ],
        ids=["nine clean", "one substitution", "two shared slots", "a shared slot in the middle"],
    )
    def test_both_sides_constrain_the_same_cells(self, slots: tuple[int, ...]) -> None:
        batters = len(slots)
        ours = [
            (self._rows(t.cell for t in rule.terms if t.coefficient > 0),
             self._rows(t.cell for t in rule.terms if t.coefficient < 0))
            for rule in _generator(slots, batters)
        ]
        theirs = [
            (self._rows(c for c, k in rule.terms if k < 0),
             self._rows(c for c, k in rule.terms if k > 0))
            for rule in _verifier(slots, batters)
        ]

        assert ours, "the generator emitted nothing, so this proves nothing"
        assert ours == theirs

    def test_they_disagree_about_direction_deliberately(self) -> None:
        # Recorded rather than papered over: the generator writes `earlier - later >= 0` and the
        # verifier writes `later - earlier <= 0`. Same claim, each in its own file's convention, and a
        # test that demanded identical signs would be pushing them toward being one implementation.
        slots = (1, 2, 3, 4, 5, 6, 7, 8, 9)
        first = _generator(slots)[0]
        theirs = _verifier(slots)[0]
        ours_positive = self._rows(term.cell for term in first.terms if term.coefficient > 0)
        theirs_positive = self._rows(cell for cell, coefficient in theirs.terms if coefficient > 0)

        assert ours_positive != theirs_positive
