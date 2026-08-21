"""The printed sheet and the board must agree, and this is the file that proves the check can fail.

⚠️⚠️ **Schema 5 duplicates data on purpose.** `reveal.boxscore.offense.batting` restates every batting
column the board carries except `PA`, and `reveal.boxscore.defense.pitching` restates the whole pitching
line — two places holding one set of facts, which is the shape of every serious defect this project has
found. What makes it safe is `check_reveal_agrees`, and a guard is only worth what a *failing* case
proves.

⚠️ **Every other test that builds a reveal uses `tests/reveals.py`, which derives the shared half from
the board — so none of them can fail this way and none of them is evidence about it.** Here the two
halves are built apart, deliberately, one field at a time.

⚠️ **And it is asserted on the constructor, not on `from_json`.** `from_json` calls the constructor, so
a test that only mutated documents would leave the in-memory path unproven — and the in-memory path is
the one the forge uses to build every package it signs. Schema 4's own docstring records that exact
asymmetry going wrong once already: a rule living only at the parse boundary let this type emit a
document its own reader refused.
"""

import dataclasses
import json
from pathlib import Path

import pytest

from boxscore_package.format import (
    SCHEMA_VERSION,
    Board,
    Package,
    PackageError,
    PrintedBoxscore,
    Reveal,
    read,
)
from tests.reveals import reveal_for


def a_package(board: Board, boxscore: PrintedBoxscore | None = None) -> Package:
    """A valid schema-5 package over the fixture board, with the printed sheet optionally tampered with."""
    labels = tuple("C" for _ in board.batting)
    roles = tuple("SP" for _ in board.pitching)
    reveal = reveal_for(board, labels=labels, pitcher_labels=roles)
    if boxscore is not None:
        reveal = dataclasses.replace(reveal, boxscore=boxscore)
    return Package(
        puzzle_id="0123456789abcdef",
        puzzle=board,
        solution=board,
        labels=labels,
        pitcher_labels=roles,
        slot_references=tuple(str(index + 1) for index in range(len(board.batting))),
        offense_is_home=True,
        reveal=reveal,
    )


def _rebuilt(board: Board, reveal: Reveal) -> Package:
    """The same package with a different reveal — so the constructor is what judges it."""
    return Package(
        puzzle_id="0123456789abcdef",
        puzzle=board,
        solution=board,
        labels=tuple("C" for _ in board.batting),
        pitcher_labels=tuple("SP" for _ in board.pitching),
        slot_references=tuple(str(index + 1) for index in range(len(board.batting))),
        offense_is_home=True,
        reveal=reveal,
    )


def _tamper(reveal: Reveal, side: str, grid: str, index: int, **fields: object) -> PrintedBoxscore:
    """Change one cell of the printed sheet and leave everything else alone."""
    box = reveal.boxscore
    half = getattr(box, side)
    rows = list(getattr(half, grid))
    rows[index] = dataclasses.replace(rows[index], **fields)
    return dataclasses.replace(box, **{side: dataclasses.replace(half, **{grid: tuple(rows)})})


class TestTheSheetCannotDisagreeWithTheBoard:
    def test_the_untampered_package_is_accepted(self, board: Board) -> None:
        # ⚠️ The control. Without it every assertion below could be passing because the fixture is
        # broken in some unrelated way, and a guard that refuses everything is not a guard.
        assert a_package(board).reveal is not None

    @pytest.mark.parametrize("column", ["at_bats", "runs", "hits", "walks", "strikeouts"])
    def test_a_batting_cell_that_disagrees_is_refused(self, board: Board, column: str) -> None:
        # Every shared column separately: a check that happens to compare only the first would pass a
        # parametrised test that only ever looked at the first.
        original = a_package(board).reveal
        assert original is not None
        current = getattr(original.boxscore.offense.batting[0], column)

        with pytest.raises(PackageError, match=f"offense.batting\\[0\\].{column}"):
            a_package(board, _tamper(original, "offense", "batting", 0, **{column: current + 1}))

    @pytest.mark.parametrize("column", ["outs", "hits", "runs", "earned_runs", "walks", "strikeouts"])
    def test_a_pitching_cell_that_disagrees_is_refused(self, board: Board, column: str) -> None:
        original = a_package(board).reveal
        assert original is not None
        current = getattr(original.boxscore.defense.pitching[0], column)

        with pytest.raises(PackageError, match=f"defense.pitching\\[0\\].{column}"):
            a_package(board, _tamper(original, "defense", "pitching", 0, **{column: current + 1}))

    def test_runs_batted_in_is_not_compared_because_no_board_carries_it(self, board: Board) -> None:
        # ⚠️ The negative case, stated so the check's *scope* is a decision rather than an accident.
        # `RBI` is the one column the printed sheet has and the board does not, which is why it is
        # worth printing — and it follows that nothing here can check it. A future reader tempted to
        # "complete" the comparison finds out here that there is nothing to complete it against.
        original = a_package(board).reveal
        assert original is not None

        tampered = _tamper(original, "offense", "batting", 0, runs_batted_in=99)

        assert a_package(board, tampered).reveal is not None

    def test_a_name_that_disagrees_with_the_reveal_is_refused(self, board: Board) -> None:
        original = a_package(board).reveal
        assert original is not None

        with pytest.raises(PackageError, match=r"offense.batting\[0\].name"):
            a_package(board, _tamper(original, "offense", "batting", 0, name="Someone Else"))

    def test_a_position_that_disagrees_with_the_label_is_refused(self, board: Board) -> None:
        # ⚠️ A mislabelled row is the defect that broke arithmetic while every total still balanced —
        # a footnote attributed to the wrong man. The label lives in two places from schema 5, so the
        # two are compared.
        original = a_package(board).reveal
        assert original is not None

        with pytest.raises(PackageError, match=r"offense.batting\[0\].position"):
            a_package(board, _tamper(original, "offense", "batting", 0, position="1B"))

    def test_a_club_code_that_disagrees_with_the_reveal_is_refused(self, board: Board) -> None:
        original = a_package(board).reveal
        assert original is not None
        box = original.boxscore

        with pytest.raises(PackageError, match="boxscore names"):
            a_package(
                board,
                dataclasses.replace(box, offense=dataclasses.replace(box.offense, code="ZZZ")),
            )

    def test_a_sheet_with_the_wrong_number_of_rows_is_refused(self, board: Board) -> None:
        original = a_package(board).reveal
        assert original is not None
        box = original.boxscore
        short = dataclasses.replace(box.offense, batting=box.offense.batting[:-1])

        with pytest.raises(PackageError, match="rows and the board has"):
            a_package(board, dataclasses.replace(box, offense=short))


class TestTheConstructorHoldsWhatPlausibilityUsedToClaim:
    """⚠️⚠️ Five checks in `reveal_faults` could not fire, because these refusals run first.

    They asked whether the reveal names every batter, names every pitcher, carries a placeholder team
    code, gives both clubs the same code, or reveals an empty name — **and `Package.__post_init__`
    calls `check_reveal_agrees`, which refuses every one of those packages before any plausibility
    layer sees them.** `Reveal.boxscore` is a required field, so there is always something to compare
    against.

    **One predicate, two places, and the stricter copy ran first.** The weaker set was deleted rather
    than marked unreachable, and this class is where the guarantee now lives — case by case, so the
    comment in `plausibility.py` saying so is exactly true rather than approximately.
    """

    def test_a_reveal_that_names_too_few_batters_is_refused(self, board: Board) -> None:
        reveal = a_package(board).reveal
        assert reveal is not None

        with pytest.raises(PackageError, match="names"):
            _rebuilt(board, dataclasses.replace(reveal, batter_names=reveal.batter_names[:-1]))

    def test_a_reveal_that_names_too_few_pitchers_is_refused(self, board: Board) -> None:
        reveal = a_package(board).reveal
        assert reveal is not None

        with pytest.raises(PackageError, match="names"):
            _rebuilt(board, dataclasses.replace(reveal, pitcher_names=reveal.pitcher_names[:-1]))

    @pytest.mark.parametrize("placeholder", ["TBD", "OPP", "???"])
    def test_a_placeholder_club_code_is_refused(self, board: Board, placeholder: str) -> None:
        """These would reach a player as the name of the club they beat."""
        reveal = a_package(board).reveal
        assert reveal is not None

        with pytest.raises(PackageError, match="reveal names"):
            _rebuilt(board, dataclasses.replace(reveal, offense_team=placeholder))

    def test_both_clubs_carrying_one_code_is_refused(self, board: Board) -> None:
        reveal = a_package(board).reveal
        assert reveal is not None

        with pytest.raises(PackageError, match="reveal names"):
            _rebuilt(board, dataclasses.replace(reveal, defense_team=reveal.offense_team))

    def test_a_blank_player_name_is_refused(self, board: Board) -> None:
        reveal = a_package(board).reveal
        assert reveal is not None

        with pytest.raises(PackageError, match="name"):
            _rebuilt(board, dataclasses.replace(reveal, batter_names=("", *reveal.batter_names[1:])))


class TestTheClubHasToBeNamed:
    @pytest.mark.parametrize("field", ["code", "city", "nickname"])
    def test_a_blank_name_is_refused_at_the_parse_boundary(self, board: Board, field: str) -> None:
        # ⚠️ Through `from_json`, because this one is a *parse* rule: the constructor takes objects that
        # are already typed and a blank string is only reachable from a document. There is deliberately
        # no fallback to the three-letter code — see `PrintedSide`.
        document = a_package(board).as_json()
        document["reveal"]["boxscore"]["offense"][field] = "   "

        with pytest.raises(PackageError, match=f"offense.{field} is blank"):
            Package.from_json(document)

    def test_a_missing_boxscore_is_refused(self, board: Board) -> None:
        document = a_package(board).as_json()
        del document["reveal"]["boxscore"]

        with pytest.raises(PackageError, match="boxscore"):
            Package.from_json(document)


class TestTheVersionMeansWhatItSays:
    def test_a_published_schema_four_file_is_refused_rather_than_read(self, tmp_path: Path) -> None:
        """⚠️ **The test that makes this a new version rather than a tightening of the old one.**

        Schema 4's docstring set the rule and the test for it: a change is a tightening only if no
        artefact changes status. Here every version-4 file changes status — it stops being readable —
        which is exactly the case that must not reuse a number. Asserted rather than argued, because
        the argument is the same one that was made, correctly, to tighten version 4 in place.
        """
        root = Path(__file__).resolve().parents[3]
        manifest = json.loads((root / "serve" / "data" / "puzzles" / "manifest.json").read_text(encoding="utf-8"))
        current = root / "serve" / "data" / "puzzles" / manifest["generation"] / f"{manifest['puzzles'][0]}.json"
        document = json.loads(current.read_text(encoding="utf-8"))
        assert document["schema"] == SCHEMA_VERSION, "the published set is not what this code writes"

        # The same file as a version-4 document: the reveal loses its sheet and the version says 4.
        del document["reveal"]["boxscore"]
        document["schema"] = SCHEMA_VERSION - 1
        stale = tmp_path / "v4.json"
        stale.write_text(json.dumps(document), encoding="utf-8")

        with pytest.raises(PackageError):
            read(stale)
