"""The publication gate runs every check that exists, and refuses when it cannot.

⚠️ **The test that matters here discovers the checks rather than listing them.** A hand-maintained
list of which checks are wired in is the same defect one level up: somebody adds a check, forgets the
registry, and the list still says everything is covered. This walks the modules instead, so a new
`check_*` or `*_faults` that nothing calls fails here.
"""

import dataclasses
import inspect
from dataclasses import replace
from pathlib import Path

import pytest

from boxscore_package.format import BATTING_COLUMNS, LEAKING_METADATA, Board, Package, PrintedBoxscore, Reveal
from boxscore_verify import certify as certification
from boxscore_verify import plausibility
from boxscore_verify.certify import (
    CERTIFICATIONS,
    UNSIGNED,
    Certification,
    Evidence,
    certify_for_publication,
)
from boxscore_verify.expected_id import expected_puzzle_id
from tests.verify.helpers import refs

LOADER = Path(__file__).resolve().parents[3] / "discovery" / "difficulty-metrics" / "measure.py"


GAME = "SLN19680808"
OFFENSE = "CHN"


def good_evidence(board: Board) -> Evidence:
    """Evidence that describes this board and this game, with every field it can be checked on."""
    return Evidence(
        # The board this evidence is about, which is what layer 4 solves back to.
        source=board,
        game_id=GAME,
        offense_team=OFFENSE,
        source_type="EVN",
        is_deduced=False,
        official_hits=board.line_score.offense_hits,
        official_runs=board.line_score.offense_runs,
        official_errors=board.line_score.offense_errors,
        official_defense_runs=board.line_score.defense_runs,
        official_defense_hits=board.line_score.defense_hits,
        official_defense_errors=board.line_score.defense_errors,
        official_at_bats=board.batting_totals[BATTING_COLUMNS.index("at_bats")],
        official_left_on_base=board.left_on_base,
    )


def package_for(board: Board) -> Package:
    from tests.reveals import reveal_for  # noqa: PLC0415

    return Package(
        slot_references=refs(board),
        # The identifier the evidence implies. It used to be an arbitrary string, which is exactly the
        # gap: nothing tied a package to the game its evidence described.
        puzzle_id=expected_puzzle_id(GAME, OFFENSE),
        puzzle=board,
        solution=board,
        labels=tuple("C" for _ in board.batting),
        pitcher_labels=tuple("SP" for _ in board.pitching),
        # Derived from the board, because from schema 5 the reveal restates its numbers and the
        # constructor refuses a package where the two disagree. See `tests/reveals.py` for why that
        # makes this file no evidence about the agreement check.
        reveal=reveal_for(
            board,
            labels=tuple("C" for _ in board.batting),
            pitcher_labels=tuple("SP" for _ in board.pitching),
            offense=OFFENSE,
        ),
        offense_is_home=True,
    )


class TestEveryImplementedCheckIsWiredIn:
    def test_the_registry_holds_every_check_defined_in_the_module(self) -> None:
        defined = {
            name
            for name, value in vars(certification).items()
            if name.startswith("check_") and inspect.isfunction(value)
        }
        registered = {function.__name__ for function in CERTIFICATIONS.values()}

        assert defined == registered, f"defined but not registered: {sorted(defined - registered)}"

    def test_every_plausibility_check_is_reached(self) -> None:
        # Discovered from the plausibility module, not listed here. A new `*_faults` that the gate
        # never calls fails this.
        # Public names only: the private helpers are the parts `faults()` is made of, and requiring
        # the gate to name them would be requiring it to know how plausibility is implemented.
        available = {
            name
            for name, value in vars(plausibility).items()
            if name.endswith("faults") and not name.startswith("_") and inspect.isfunction(value)
        }
        source = Path(certification.__file__).read_text(encoding="utf-8")

        for name in available:
            assert name in source, f"{name} exists and the publication gate never calls it"

    def test_the_gate_names_every_registered_check_when_it_refuses(self, board: Board) -> None:
        # Each refusal is prefixed with the check that produced it, so a batch report says which gate
        # is rejecting rather than only how many.
        # ⚠️⚠️ **This passed `evidence=None`, which returns before any check runs.** (v36-P3-17) So the
        # test named for the prefixing could not produce a prefix even in principle — and it asserted
        # only that a refusal happened, so removing the prefixing from `certify_for_publication` left
        # the suite green. A batch report would then say how many gates rejected and not which.
        #
        # Real evidence, and a package that fails a real check: metadata still naming the game.
        carrying = replace(package_for(board), metadata={"game_id": "BOS191305010"})

        result = certify_for_publication(carrying, evidence=good_evidence(board), secret=UNSIGNED)

        assert not result.publishable
        assert result.refusals, "a refusal with no reasons"
        for refusal in result.refusals:
            assert any(refusal.startswith(f"{name}:") for name in CERTIFICATIONS), (
                f"{refusal!r} is not prefixed by a registered check; a batch report cannot attribute it"
            )

    def test_a_refusal_before_any_check_names_no_check_and_says_so(self, board: Board) -> None:
        """⚠️ The other path, kept apart because it is a different fact. Missing evidence fails closed
        *before* the registry is entered, so its one refusal is deliberately unprefixed — there is no
        check to attribute it to. Asserting it here stops someone 'fixing' the inconsistency by
        prefixing a message that no check produced."""
        result = certify_for_publication(package_for(board), evidence=None, secret=UNSIGNED)

        assert not result.publishable
        assert result.refusals == ("no evidence supplied: provenance and correspondence unknown",)


class TestItFailsClosed:
    def test_no_evidence_is_a_refusal(self, board: Board) -> None:
        # ⚠️ A producer that cannot say where the game came from has not shown it may publish; it has
        # only failed to look.
        result = certify_for_publication(package_for(board), evidence=None, secret=UNSIGNED)

        assert not result.publishable
        assert "no evidence" in result.refusals[0]

    def test_a_deduced_game_is_refused(self, board: Board) -> None:
        evidence = replace(good_evidence(board), source_type="EDN", is_deduced=True)

        result = certify_for_publication(package_for(board), evidence=evidence, secret=UNSIGNED)

        assert any("deduced" in refusal for refusal in result.refusals)

    def test_an_unaccepted_source_is_refused(self, board: Board) -> None:
        evidence = replace(good_evidence(board), source_type="EVR")

        result = certify_for_publication(package_for(board), evidence=evidence, secret=UNSIGNED)

        assert any("EVR" in refusal for refusal in result.refusals)

    def test_disagreeing_with_the_official_total_is_refused(self, board: Board) -> None:
        evidence = replace(good_evidence(board), official_hits=board.line_score.offense_hits + 1)

        result = certify_for_publication(package_for(board), evidence=evidence, secret=UNSIGNED)

        assert any("hits disagree" in refusal for refusal in result.refusals)

    def test_an_implausible_board_is_refused_where_verify_accepts_it(self, board: Board) -> None:
        # ⚠️ The whole reason this boundary exists. A row of noughts breaks no identity, so every
        # layer of §22 accepts it.
        from boxscore_verify.verify import verify  # noqa: PLC0415

        broken = Board(
            batting=((0, 0, 0, 0, 0, 0), *board.batting),
            batting_totals=board.batting_totals,
            footnotes=((0, 0, 0, 0), *board.footnotes),
            footnote_totals=board.footnote_totals,
            left_on_base=board.left_on_base,
            pitching=board.pitching,
            pitching_totals=board.pitching_totals,
            line_score=board.line_score,
        )

        # ⚠⚠ **`verify` used to accept this and no longer does.** The four arithmetic families cannot
        # see a row of noughts; the batting order can, because a phantom row at the top takes the
        # first place with nought appearances while the rest have four, and the cycle forbids it.
        #
        # The gate is still what this test is about, so what it asserts is unchanged: the board does
        # not publish. What changed is that it is now refused twice, by two independent readings.
        # ⚠️ Asserting only "not publishable" would pass even if the gate stopped running and verify
        # did all the work, so both are named.
        assert not verify(package_for(broken), secret=UNSIGNED, source=broken).accepted
        assert not certify_for_publication(
            package_for(broken), evidence=good_evidence(broken), secret=UNSIGNED
        ).publishable

    def test_a_sound_package_is_publishable(self, board: Board) -> None:
        # A gate that refuses everything is as useless as one that refuses nothing.
        result = certify_for_publication(package_for(board), evidence=good_evidence(board), secret=UNSIGNED)

        assert result.publishable, result.refusals


class TestThePrintedBoxscoreIsCorroborated:
    """⚠️⚠️ **v30-P1-02: the gate certified a package whose unshared half was fabricated.**

    Schema 5 gave the reveal both clubs. `check_reveal_agrees` compares the half the board also
    carries; `format.py` said the other half "belongs to `certify_for_publication`", and no such check
    existed — `Evidence` carried no rows and no certification looked at them. The fixture named those
    rows `Not A Real Player`, filled them with zeros, and `test_a_sound_package_is_publishable`
    expected the gate to accept it. It did.

    These are the failing cases. Each one moves a single number in the half no board carries and
    asserts the gate refuses, because a check is worth what its failures prove and every other test
    that touches this fixture now builds a *consistent* half by construction.
    """

    def _reveal(self, board: Board) -> Reveal:
        reveal = package_for(board).reveal
        assert reveal is not None
        return reveal

    def _with(self, board: Board, boxscore: PrintedBoxscore) -> Certification:
        package = dataclasses.replace(
            package_for(board),
            reveal=dataclasses.replace(self._reveal(board), boxscore=boxscore),
        )
        return certify_for_publication(package, evidence=good_evidence(board), secret=UNSIGNED)

    def test_the_defence_scoring_something_else_is_refused(self, board: Board) -> None:
        # The club the board never shows, against a total loaded from a different table.
        box = self._reveal(board).boxscore
        rows = (dataclasses.replace(box.defense.batting[0], runs=box.defense.batting[0].runs + 1),)

        result = self._with(board, dataclasses.replace(box, defense=dataclasses.replace(box.defense, batting=rows)))

        assert not result.publishable
        assert any("defence's batters scored" in refusal for refusal in result.refusals), result.refusals

    def test_the_defence_hitting_something_else_is_refused(self, board: Board) -> None:
        box = self._reveal(board).boxscore
        rows = (dataclasses.replace(box.defense.batting[0], hits=box.defense.batting[0].hits + 2),)

        result = self._with(board, dataclasses.replace(box, defense=dataclasses.replace(box.defense, batting=rows)))

        assert not result.publishable
        assert any("defence's batters hit" in refusal for refusal in result.refusals), result.refusals

    def test_the_offence_staff_allowing_something_else_is_refused(self, board: Board) -> None:
        # ⚠️ The cross-team identity applied to the direction the board does not show: the runs this
        # staff allowed and the runs the other club scored are the same events.
        box = self._reveal(board).boxscore
        rows = (dataclasses.replace(box.offense.pitching[0], runs=box.offense.pitching[0].runs + 1),)

        result = self._with(board, dataclasses.replace(box, offense=dataclasses.replace(box.offense, pitching=rows)))

        assert not result.publishable
        assert any("pitchers allowed, in runs" in refusal for refusal in result.refusals), result.refusals

    def test_an_impossible_number_of_outs_is_refused(self, board: Board) -> None:
        box = self._reveal(board).boxscore
        rows = (dataclasses.replace(box.offense.pitching[0], outs=99),)

        result = self._with(board, dataclasses.replace(box, offense=dataclasses.replace(box.offense, pitching=rows)))

        assert not result.publishable
        assert any("outs across" in refusal for refusal in result.refusals), result.refusals

    def test_a_short_last_inning_is_accepted(self, board: Board) -> None:
        # ⚠️ The negative case, so the bound is a decision rather than an accident. A home side that
        # scores the winning run stops batting, so the staff can be up to three outs short. An equality
        # here would refuse every walk-off ever played.
        box = self._reveal(board).boxscore
        rows = (dataclasses.replace(box.offense.pitching[0], outs=box.offense.pitching[0].outs - 2),)

        result = self._with(board, dataclasses.replace(box, offense=dataclasses.replace(box.offense, pitching=rows)))

        assert result.publishable, result.refusals

    def test_an_empty_grid_is_refused(self, board: Board) -> None:
        box = self._reveal(board).boxscore

        result = self._with(board, dataclasses.replace(box, defense=dataclasses.replace(box.defense, batting=())))

        assert not result.publishable
        assert any("no rows for defense.batting" in refusal for refusal in result.refusals), result.refusals

    def test_the_all_zero_half_that_used_to_publish_is_refused(self, board: Board) -> None:
        # ⚠️ The exact shape the review found: every unshared row present, named, and entirely zero.
        # It passed the gate for the whole life of schema 5, which is one commit, and this is the
        # assertion that it cannot again.
        box = self._reveal(board).boxscore
        zeroed = dataclasses.replace(
            box,
            defense=dataclasses.replace(
                box.defense,
                batting=(dataclasses.replace(box.defense.batting[0], runs=0, hits=0, at_bats=0, runs_batted_in=0),),
            ),
            offense=dataclasses.replace(
                box.offense,
                pitching=(dataclasses.replace(box.offense.pitching[0], outs=0, runs=0, hits=0, earned_runs=0),),
            ),
        )

        result = self._with(board, zeroed)

        assert not result.publishable
        assert len(result.refusals) >= 3, result.refusals


class TestTheGateRefusesAPackageThatNamesTheGame:
    """v36-P2-10. The gate is *the single gate a puzzle passes before it may be published* and it never
    asked whether the metadata still carried the answer.

    ⚠️ The damaging case needs no attacker: a pipeline that forgets `.published()` ships the date and
    the clubs in every file, passes every check, and hands the reveal to anyone with devtools open.
    """

    @pytest.mark.parametrize("key", sorted(LEAKING_METADATA))
    def test_every_leaking_key_is_refused_on_its_own(self, board: Board, key: str) -> None:
        # ⚠️ One case per key rather than one case with all five. The ad-hoc check this replaces looked
        # for `game_id` alone, and `date` or `teams` name the game just as well.
        carrying = replace(package_for(board), metadata={key: "anything"})

        verdict = certify_for_publication(carrying, evidence=good_evidence(board), secret=UNSIGNED)

        assert not verdict.publishable
        assert any(key in refusal for refusal in verdict.refusals), verdict.refusals

    def test_a_published_package_passes(self, board: Board) -> None:
        # The other half: the check must not refuse what the pipeline actually produces. `published()`
        # is what strips them, and its output has to survive its own gate.
        verdict = certify_for_publication(
            package_for(board).published(), evidence=good_evidence(board), secret=UNSIGNED
        )

        assert not any("names the game" in refusal for refusal in verdict.refusals), verdict.refusals


class TestTheDuplicatedSourceListAgrees:
    def test_the_gate_and_the_loader_accept_the_same_sources(self) -> None:
        # §22 forbids the verifier importing from the generator, so the list exists twice on purpose.
        # Two copies of a rule drift — this project has watched it happen — so they are asserted equal
        # rather than trusted.
        # ⚠️ **Imported, not parsed, and the change is the point.** This read the assignment with
        # `ast.literal_eval`, which works only while the loader spells the tuple out. It stopped
        # working the moment the list was derived from another constant — a guard that fails because
        # the *spelling* changed while the rule held is the failure mode this project has recorded
        # twice, and the fix both times was to compare what the code produces.
        from boxscore_forge import pool as measure  # noqa: PLC0415

        assert measure.ACCEPTED_SOURCES == certification.ACCEPTED_SOURCES

    def test_the_pool_sql_is_narrower_than_the_gate(self) -> None:
        """⚠️ **The postseason source must not widen what admits the existing pool.**

        `EVE` belongs to the gate, because a postseason package may be published. It must **not** reach
        the regular season's provenance predicate, which is interpolated from `PROVENANCE_SOURCES`. The
        first version of the postseason change put it in one list serving both, and the regression was
        invisible in the data — no provenance row carries `EVE`, so nothing would have failed. *Harmless
        in fact* is not the test; the rule was that the pool does not change.
        """
        from boxscore_forge import pool as measure  # noqa: PLC0415

        assert "EVE" not in measure.PROVENANCE_SOURCES, "the postseason source reached the regular season's SQL"
        assert "EVE" not in measure.PROVENANCE_LITERAL, "the rendered SQL list carries the postseason source"
        assert set(measure.PROVENANCE_SOURCES) < set(measure.ACCEPTED_SOURCES), "the gate must be the wider of the two"


class TestEvidenceMustBeAboutThisPackage:
    """The gap the gate had: `Evidence` was an unbound assertion by the producer that built the board.

    Nothing in it named a game, and the published package carries no game id by design (§7), so
    evidence from a different game satisfied every check as long as the totals happened to match.
    """

    def test_evidence_for_another_game_is_refused(self, board: Board) -> None:
        # The two games agree on every total the gate used to compare. Only the identifier separates
        # them, which is why the identifier is what the gate recomputes.
        elsewhere = replace(good_evidence(board), game_id="BOS19680808")

        result = certify_for_publication(package_for(board), evidence=elsewhere, secret=UNSIGNED)

        assert not result.publishable
        assert any("describes puzzle" in refusal for refusal in result.refusals)

    def test_evidence_for_the_other_direction_of_the_same_game_is_refused(self, board: Board) -> None:
        # A game yields up to two puzzles and they are different puzzles. The batting team is part of
        # the identifier for exactly this reason.
        other_way = replace(good_evidence(board), offense_team="SLN")

        result = certify_for_publication(package_for(board), evidence=other_way, secret=UNSIGNED)

        assert any("describes puzzle" in refusal for refusal in result.refusals)

    def test_evidence_naming_no_game_is_refused(self, board: Board) -> None:
        # Fail closed rather than raise. An empty game id would hash to a stable value and bind
        # nothing, so it is refused before it is hashed.
        nameless = replace(good_evidence(board), game_id="")

        result = certify_for_publication(package_for(board), evidence=nameless, secret=UNSIGNED)

        assert any("names no game" in refusal for refusal in result.refusals)


class TestTheCompleteLineScoreIsChecked:
    """Every player-visible R/H/E field, each on its own.

    The gate compared two of the six. The other four are signed and shown, so an alteration in any of
    them is a false historical claim that no identity on the board would notice - the defensive hit
    total in particular takes part in nothing.
    """

    def test_each_line_score_field_is_checked_independently(self, board: Board) -> None:
        fields = (
            "official_hits",
            "official_runs",
            "official_errors",
            "official_defense_runs",
            "official_defense_hits",
            "official_defense_errors",
        )
        for field in fields:
            altered = replace(good_evidence(board), **{field: getattr(good_evidence(board), field) + 1})

            result = certify_for_publication(package_for(board), evidence=altered, secret=UNSIGNED)

            assert not result.publishable, f"{field} was not checked"

    def test_at_bats_are_checked_against_the_game_log(self, board: Board) -> None:
        # The only strict correspondence the gate has: the game log is neither of the tables the
        # board is built from. Everything else compares a value against the query that produced it.
        wrong = replace(good_evidence(board), official_at_bats=good_evidence(board).official_at_bats + 1)

        result = certify_for_publication(package_for(board), evidence=wrong, secret=UNSIGNED)

        assert any("at-bats disagree with the game log" in refusal for refusal in result.refusals)

    def test_runners_left_on_base_are_checked_against_the_game_log(self, board: Board) -> None:
        wrong = replace(good_evidence(board), official_left_on_base=(board.left_on_base or 0) + 1)

        result = certify_for_publication(package_for(board), evidence=wrong, secret=UNSIGNED)

        assert any("left on base disagree" in refusal for refusal in result.refusals)

    def test_a_game_with_no_log_row_is_refused_rather_than_waved_through(self, board: Board) -> None:
        # ⚠️ Absence is a refusal. 1.5% of games have no game-log row, concentrated in the 1930s to
        # 1960s, and a game nothing independent corroborates is discarded rather than published on
        # the strength of the checks that happened to run.
        uncorroborated = replace(good_evidence(board), official_at_bats=None, official_left_on_base=None)

        result = certify_for_publication(package_for(board), evidence=uncorroborated, secret=UNSIGNED)

        assert not result.publishable
        assert any("nothing independent corroborates" in refusal for refusal in result.refusals)
