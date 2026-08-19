"""The publication gate runs every check that exists, and refuses when it cannot.

⚠️ **The test that matters here discovers the checks rather than listing them.** A hand-maintained
list of which checks are wired in is the same defect one level up: somebody adds a check, forgets the
registry, and the list still says everything is covered. This walks the modules instead, so a new
`check_*` or `*_faults` that nothing calls fails here.
"""

import ast
import inspect
from dataclasses import replace
from pathlib import Path

from boxscore_package.format import BATTING_COLUMNS, Board, Package
from boxscore_verify import certify as certification
from boxscore_verify import plausibility
from boxscore_verify.certify import (
    CERTIFICATIONS,
    UNSIGNED,
    Evidence,
    certify_for_publication,
)
from boxscore_verify.expected_id import expected_puzzle_id

LOADER = Path(__file__).resolve().parents[3] / "discovery" / "difficulty-metrics" / "measure.py"


GAME = "SLN19680808"
OFFENSE = "CHN"



def refs(board: object) -> tuple[str, ...]:
    """One slot reference per batting row — the shape a package must carry since schema 2.

    A helper rather than the expression inline: it appears in every fixture, and the property being
    fixed is *one per row*, which a name states and a comprehension buries.
    """
    return tuple(str(index + 1) for index in range(len(board.batting)))  # type: ignore[attr-defined]


def good_evidence(board: Board) -> Evidence:
    """Evidence that describes this board and this game, with every field it can be checked on."""
    return Evidence(
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
    from boxscore_package.format import Reveal  # noqa: PLC0415

    return Package(
        slot_references=refs(board),
        # The identifier the evidence implies. It used to be an arbitrary string, which is exactly the
        # gap: nothing tied a package to the game its evidence described.
        puzzle_id=expected_puzzle_id(GAME, OFFENSE),
        puzzle=board,
        solution=board,
        labels=tuple("C" for _ in board.batting),
        pitcher_labels=tuple("SP" for _ in board.pitching),
        reveal=Reveal(
            batter_names=tuple("A Batter" for _ in board.batting),
            pitcher_names=tuple("A Pitcher" for _ in board.pitching),
            offense_team="AAA",
            defense_team="BBB",
            played_on="1968-08-08",
        ),
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
        result = certify_for_publication(package_for(board), evidence=None, secret=UNSIGNED)

        assert not result.publishable


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

        assert verify(package_for(broken), secret=UNSIGNED).accepted
        assert not certify_for_publication(
            package_for(broken), evidence=good_evidence(broken), secret=UNSIGNED
        ).publishable

    def test_a_sound_package_is_publishable(self, board: Board) -> None:
        # A gate that refuses everything is as useless as one that refuses nothing.
        result = certify_for_publication(package_for(board), evidence=good_evidence(board), secret=UNSIGNED)

        assert result.publishable, result.refusals


class TestTheDuplicatedSourceListAgrees:
    def test_the_gate_and_the_loader_accept_the_same_sources(self) -> None:
        # §22 forbids the verifier importing from the generator, so the list exists twice on purpose.
        # Two copies of a rule drift — this project has watched it happen — so they are asserted equal
        # rather than trusted.
        tree = ast.parse(LOADER.read_text(encoding="utf-8"))
        loader_sources = next(
            tuple(ast.literal_eval(node.value))  # type: ignore[arg-type]
            for node in tree.body
            if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "ACCEPTED_SOURCES"
        )

        assert loader_sources == certification.ACCEPTED_SOURCES


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
