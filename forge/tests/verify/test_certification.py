"""The publication gate runs every check that exists, and refuses when it cannot.

⚠️ **The test that matters here discovers the checks rather than listing them.** A hand-maintained
list of which checks are wired in is the same defect one level up: somebody adds a check, forgets the
registry, and the list still says everything is covered. This walks the modules instead, so a new
`check_*` or `*_faults` that nothing calls fails here.
"""

import ast
import inspect
from pathlib import Path

from boxscore_package.format import Board, Package
from boxscore_verify import certify as certification
from boxscore_verify import plausibility
from boxscore_verify.certify import (
    CERTIFICATIONS,
    UNSIGNED,
    Evidence,
    certify_for_publication,
)

LOADER = Path(__file__).resolve().parents[3] / "discovery" / "difficulty-metrics" / "measure.py"


def good_evidence(board: Board) -> Evidence:
    return Evidence(
        source_type="EVN",
        is_deduced=False,
        official_hits=board.line_score.offense_hits,
        official_runs=board.line_score.offense_runs,
    )


def package_for(board: Board) -> Package:
    from boxscore_package.format import Reveal  # noqa: PLC0415

    return Package(
        puzzle_id="certify",
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
        evidence = Evidence(
            source_type="EDN",
            is_deduced=True,
            official_hits=board.line_score.offense_hits,
            official_runs=board.line_score.offense_runs,
        )

        result = certify_for_publication(package_for(board), evidence=evidence, secret=UNSIGNED)

        assert any("deduced" in refusal for refusal in result.refusals)

    def test_an_unaccepted_source_is_refused(self, board: Board) -> None:
        evidence = Evidence(
            source_type="EVR",
            is_deduced=False,
            official_hits=board.line_score.offense_hits,
            official_runs=board.line_score.offense_runs,
        )

        result = certify_for_publication(package_for(board), evidence=evidence, secret=UNSIGNED)

        assert any("EVR" in refusal for refusal in result.refusals)

    def test_disagreeing_with_the_official_total_is_refused(self, board: Board) -> None:
        evidence = Evidence(
            source_type="EVN",
            is_deduced=False,
            official_hits=board.line_score.offense_hits + 1,
            official_runs=board.line_score.offense_runs,
        )

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
