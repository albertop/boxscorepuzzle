"""Properties the identity system must hold, rather than cases someone thought to write down.

The example-based tests confirm that each identity fires when broken in the way its author had in
mind. What they cannot show is that the set of identities has no blind spot — a column nobody
wired up, a footnote nobody checks. That is what the perturbation property below is for, and it is
the reason these tests enumerate the model's fields from `dataclasses.fields` instead of from the
lists inside `identities`. Reading the implementation's own idea of which columns exist would
inherit exactly the blind spot being looked for.
"""

import dataclasses
from collections.abc import Iterator

from hypothesis import given, settings
from hypothesis import strategies as st

from boxscore_forge.boxscore import BattingLine, Direction, Footnotes, LineScore, PitchingLine
from boxscore_forge.identities import find_violations
from tests.strategies import valid_directions

# Errors are printed because a line score has an E column, and the defense's hit total belongs to a
# team whose offense is not on the board. Nothing deduces from either, so moving them must not
# reject a boxscore. Listing them here makes that a decision under test rather than an oversight.
INERT_FIELDS = frozenset(
    {
        "line_score.offense_errors",
        "line_score.defense_errors",
        "line_score.defense_hits",
    }
)


def _int_field_names(model: type) -> tuple[str, ...]:
    return tuple(field.name for field in dataclasses.fields(model) if field.type in (int, "int"))


def _batting_perturbations(direction: Direction, delta: int) -> Iterator[tuple[str, Direction]]:
    for index, line in enumerate(direction.batting):
        for field in _int_field_names(BattingLine):
            rows = list(direction.batting)
            rows[index] = dataclasses.replace(line, **{field: getattr(line, field) + delta})
            yield f"batting[{index}].{field}", dataclasses.replace(direction, batting=tuple(rows))

    for field in _int_field_names(BattingLine):
        totals = direction.batting_totals
        moved = dataclasses.replace(totals, **{field: getattr(totals, field) + delta})
        yield f"batting_totals.{field}", dataclasses.replace(direction, batting_totals=moved)


def _pitching_perturbations(direction: Direction, delta: int) -> Iterator[tuple[str, Direction]]:
    for index, line in enumerate(direction.pitching):
        for field in _int_field_names(PitchingLine):
            rows = list(direction.pitching)
            rows[index] = dataclasses.replace(line, **{field: getattr(line, field) + delta})
            yield f"pitching[{index}].{field}", dataclasses.replace(direction, pitching=tuple(rows))

    for field in _int_field_names(PitchingLine):
        totals = direction.pitching_totals
        moved = dataclasses.replace(totals, **{field: getattr(totals, field) + delta})
        yield f"pitching_totals.{field}", dataclasses.replace(direction, pitching_totals=moved)


def _footnote_perturbations(direction: Direction, delta: int) -> Iterator[tuple[str, Direction]]:
    for field in _int_field_names(Footnotes):
        footnotes = direction.footnotes
        moved = dataclasses.replace(footnotes, **{field: getattr(footnotes, field) + delta})
        yield f"footnotes.{field}", dataclasses.replace(direction, footnotes=moved)


def _line_score_perturbations(direction: Direction, delta: int) -> Iterator[tuple[str, Direction]]:
    line_score = direction.line_score
    for field in _int_field_names(LineScore):
        moved = dataclasses.replace(line_score, **{field: getattr(line_score, field) + delta})
        yield f"line_score.{field}", dataclasses.replace(direction, line_score=moved)

    for index in range(len(line_score.offense_by_inning)):
        moved = dataclasses.replace(line_score, offense_by_inning=_move(line_score.offense_by_inning, index, delta))
        yield f"line_score.offense_by_inning[{index}]", dataclasses.replace(direction, line_score=moved)

    for index in range(len(line_score.defense_by_inning)):
        moved = dataclasses.replace(line_score, defense_by_inning=_move(line_score.defense_by_inning, index, delta))
        yield f"line_score.defense_by_inning[{index}]", dataclasses.replace(direction, line_score=moved)


def _move(innings: tuple[int, ...], index: int, delta: int) -> tuple[int, ...]:
    mutated = list(innings)
    mutated[index] += delta
    return tuple(mutated)


def _perturbations(direction: Direction, delta: int) -> Iterator[tuple[str, Direction]]:
    yield from _batting_perturbations(direction, delta)
    yield from _pitching_perturbations(direction, delta)
    yield from _footnote_perturbations(direction, delta)
    yield from _line_score_perturbations(direction, delta)


class TestBalancedBoxscoresAreAccepted:
    @given(valid_directions())
    def test_accepts_any_boxscore_built_to_balance(self, direction: Direction) -> None:
        assert find_violations(direction) == ()


class TestEveryParticipatingValueIsChecked:
    @given(valid_directions(), st.sampled_from([-1, 1]))
    @settings(max_examples=50)
    def test_moving_any_participating_value_breaks_an_identity(self, direction: Direction, delta: int) -> None:
        # If this fails, a value on the board takes part in no identity — which means the solver has
        # a cell it can never deduce and the generator has one it can erase without consequence.
        unchecked = [
            path
            for path, perturbed in _perturbations(direction, delta)
            if path not in INERT_FIELDS and find_violations(perturbed) == ()
        ]

        assert unchecked == []

    @given(valid_directions())
    @settings(max_examples=50)
    def test_moving_a_deliberately_unused_value_changes_nothing(self, direction: Direction) -> None:
        # Only upward: taking an unused value below zero is still caught by non-negativity, which
        # is correct and not what this property is about.
        wrongly_rejected = [
            path
            for path, perturbed in _perturbations(direction, 1)
            if path in INERT_FIELDS and find_violations(perturbed)
        ]

        assert wrongly_rejected == []

    @given(valid_directions())
    def test_the_inert_list_names_fields_that_exist(self, direction: Direction) -> None:
        # Guards against a renamed column quietly turning an exemption into a dead string, which
        # would leave the field unexercised by the property above with nothing to show for it.
        paths = {path for path, _ in _perturbations(direction, 1)}

        assert paths >= INERT_FIELDS


class TestOrderIndependence:
    @given(valid_directions(), st.data())
    def test_batting_order_does_not_affect_validity(self, direction: Direction, data: st.DataObject) -> None:
        # The identities are sums, so the board may reorder or relabel rows without changing
        # whether the boxscore balances. The progressive reveal depends on rows being addressable
        # independently of the order they were dealt in.
        reordered = data.draw(st.permutations(direction.batting))

        assert find_violations(dataclasses.replace(direction, batting=tuple(reordered))) == ()
