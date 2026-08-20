"""The batting order is adopted, and these are the invariants that survived the fence coming down.

⚠️⚠️ **This file used to assert the opposite of what it asserts now, and that is the point of keeping
it rather than deleting it.** While the constraint was experimental it held three guards: nothing may
import the fallback, no module may reach both it and certification, and the verifier must contain no
lineup step. All three were true, all three were checked by reverting, and **all three are now false by
decision** — the operator adopted the constraint, production builds through the fallback, and the
verifier has the step it needs to certify those boards.

A guard that outlives its decision fails honest changes, so those three are gone. What replaces them
is not weaker: it is the set of things that must hold **because** it is adopted.

⚠️ **And one of them existed only by accident.** The old import-graph guard walked `forge/src` and the
production generator lives in `forge/scripts`, so a script bridging the experiment to certification
would never have been seen. The fence was intact in the half of the tree it looked at. That is
recorded here because it is the reason to state a boundary as *what the code must do* rather than as
*what it must not import*.
"""

import ast
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
GAME = "SLN19680808"
OFFENSE = "CHN"
"""The game the shared fixture is, so the evidence and the identifier describe the same one. The gate
checks that they agree — an arbitrary id with matching evidence is the gap it exists to close."""

FALLBACK = "boxscore_forge.lineup_fallback"
"""⚠️ Named for what it is, not for what it was. This constant was `EXPERIMENTAL` while the module was,
and kept the name for a commit after production started calling it — v29-P3-01. An identifier that
describes a retired state is a statement about the code, and it was the wrong one."""


def _modules(*roots: pathlib.Path) -> dict[str, ast.Module]:
    """Every first-party module under the given roots, parsed once.

    ⚠️ `scripts/` as well as `src/`, because the production generator lives there and the guard this
    replaces did not look at it.
    """
    found: dict[str, ast.Module] = {}
    for root in roots:
        for path in root.rglob("*.py"):
            dotted = ".".join(path.relative_to(root).with_suffix("").parts).removesuffix(".__init__")
            found[dotted] = ast.parse(path.read_text(encoding="utf-8"))
    return found


def _calls(tree: ast.Module, name: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", None)) == name
    ]


class TestProductionGoesThroughTheFallbackRatherThanAroundIt:
    """⚠️⚠️ The conditional retry is the whole design, and calling `erase` directly bypasses it.

    On the walks measured, turning the constraint on everywhere converted a median of eight steps per
    board into *read the total, divide by nine, write it down* — 244 such cells. The retry exists so
    boards that reach their target without the constraint never pay that. A producer that calls
    `erase()` itself gets the old behaviour if it omits slots, and the everywhere-on behaviour if it
    passes them. **Neither is the adopted design**, and both look correct in a diff.
    """

    def test_the_reference_generator_builds_through_the_fallback(self) -> None:
        tree = _modules(SCRIPTS)["write_reference_puzzles"]

        assert _calls(tree, "erase_with_lineup_fallback"), "the generator no longer uses the retry"
        assert not _calls(tree, "erase"), "the generator calls erase() directly, bypassing the retry"

    def test_no_module_outside_the_fallback_passes_slots_to_erase(self) -> None:
        """⚠️ The other way round it: turning the constraint on for every board.

        `erase(..., slots=lineup)` is the everywhere-on configuration, which is the one the measurement
        rejected. Only the fallback may pass it, and only after the plain attempt has failed.
        """
        offenders: list[str] = []
        for name, tree in _modules(SRC, SCRIPTS).items():
            if name == FALLBACK:
                continue
            for call in _calls(tree, "erase"):
                if any(keyword.arg == "slots" for keyword in call.keywords) or len(call.args) > 1:
                    offenders.append(f"{name}:{call.lineno}")

        assert not offenders, f"the constraint is switched on for every board at {offenders}"

    def test_the_finder_sees_the_one_call_that_is_allowed_to_pass_slots(self) -> None:
        # ⚠️ Positive control. "No offenders" from a finder that finds nothing is not a result.
        tree = _modules(SRC)[FALLBACK]
        with_slots = [
            call for call in _calls(tree, "erase") if any(keyword.arg == "slots" for keyword in call.keywords)
        ]

        assert with_slots, "the finder cannot see the fallback's own call, so it would find nothing"


class TestTheVerifierCanActuallyCertifyTheseBoards:
    """⚠️⚠️ The gate that used to keep them unpublishable is now the thing that lets them publish.

    While the step did not exist, layer 3 refused any board leaning on the cyclic order — which is what
    made the experiment safe, and also what made every figure measured before it describe boards that
    could not ship. Now it exists, so what has to hold is that it is *reachable*: present in the
    verifier, and actually consulted by the layer.
    """

    def test_the_verifier_has_a_value_producing_lineup_step(self) -> None:
        from boxscore_verify.reason import lineup_values  # noqa: PLC0415

        # It produces a value rather than a bound: nine places, thirty-nine appearances, so the first
        # three bat five times. A step that only narrowed would return nothing here.
        from boxscore_verify.rules import batting_total  # noqa: PLC0415

        found = lineup_values(tuple(range(1, 10)), {batting_total("plate_appearances"): 39})

        assert len(found) == 9
        assert sorted(found.values()) == [4, 4, 4, 4, 4, 4, 5, 5, 5]

    @pytest.mark.parametrize("layer", ["check_derivability", "derivable_in_view"])
    def test_both_derivability_layers_read_the_lineup(self, layer: str) -> None:
        """⚠️ Present is not the same as consulted.

        `relations()` took a `slots` argument for a day while every call site passed nothing, so the
        family was dead code that read as a working constraint. This reads the call sites.
        """
        source = (SRC / "boxscore_verify" / "verify.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        body = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == layer)
        text = ast.unparse(body)

        assert "slots_of(package)" in text, f"{layer} never reads the lineup off the package"
        assert "slots" in text, f"{layer} does not pass the lineup on"


class TestAFallbackBoardActuallyPublishes:
    """⚠️⚠️ Adoption as an observable outcome, not as the presence of imports and calls.

    Everything else in this file reads the source: does the generator call the retry, does the verifier
    have the step, do the layers read the lineup. **All of that was true while a fallback board could
    not publish at all**, because layers 2 and 4 built their relations without the slots and searched a
    weaker system than the one that erased the cells. A board unique *because of* the batting order was
    seen as ambiguous and discarded at layer 2 — before the new derivability step ever ran.

    ⚠️ **And nothing was red.** The reference writer fills its slots with whatever boards it finds, so a
    run where the adopted branch published nothing looks exactly like a run where it published. That is
    the shape of every check in this project that turned out to be watching the wrong thing.

    So this test takes the one path that matters: a board the plain erasure **cannot** reach, produced
    by the fallback, through the arithmetic layers **and the publication gate**.

    ⚠️ Not "all five layers": this run is unsigned, so the signature layer is deliberately skipped and
    the phrase would claim something the test does not check.
    """

    SLOTS = (1, 2, 3, 4, 5, 6, 7, 8, 9)
    """The shared fixture is nine rows, one per place, with no substitution."""

    SEED = 1
    FALLBACK_TARGET = 4
    """⚠️ Found by probing this fixture, not guessed: at four stalls with seed one the plain erasure
    misses and the fallback reaches. Targets 8 and above are `unreachable` even with the constraint, so
    a test pinned there would assert nothing about publication."""
    """⚠️ Pinned, not searched. A test that hunts for the first target the plain path misses will
    silently move to a different case when the erasure changes, and then it is exercising something
    nobody chose. Asserted below, so if this board stops needing the fallback here the test says so
    rather than quietly testing the plain path."""

    @staticmethod
    def _evidence(package: object) -> object:
        """Independent corroboration, in the shape the gate requires.

        ⚠️ Taken from the solution board's line score, which §6 gives complete and never erases — so it
        is *given* rather than derived from the rows it corroborates. In production these come from the
        game log, which is a different table from the one the board is built from; here the point is
        that the gate runs at all, not that it catches a fabricated total.
        """
        from boxscore_package.format import BATTING_COLUMNS  # noqa: PLC0415
        from boxscore_verify.certify import Evidence  # noqa: PLC0415

        board = package.solution
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

    def test_the_fixture_is_a_lineup_the_pool_rule_accepts(self, cubs_at_braves_1968: object) -> None:
        """⚠️ Before anything else: a fixture the pool rule would reject cannot test adoption.

        A real 1968 boxscore, and its places bat 5 5 5 4 4 4 4 4 4 — thirty-nine appearances dealt round
        the order, which is what the cycle predicts. **Used rather than fabricated** so the test is
        about a board that happened, and stated first so a later failure is never ambiguous about
        whether the fixture or the adoption is at fault.
        """
        from boxscore_forge.identities import find_violations  # noqa: PLC0415

        assert find_violations(cubs_at_braves_1968, self.SLOTS) == ()

    def test_a_fallback_board_reaches_the_publication_gate(self, cubs_at_braves_1968: object) -> None:
        """The sequence: plain misses, the fallback reaches, and that exact package publishes.

        ⚠⚠ **This skipped when no fallback board appeared, and called `verify()` rather than the gate.**
        Both are the same defect wearing different clothes — v29-P2-02. A skip is a *successful* suite
        outcome, so the regression v29-P2-01 described could return without the suite going red: the
        adopted branch produces nothing certifiable and the test reports a skip. And production
        publishes through `certify_for_publication()`, which adds plausibility and independent
        evidence, so a defect in either refuses every fallback board while a `verify()` assertion stays
        green.

        **A missing fallback board is a failed precondition, never a skip**, and the boundary asserted
        is the one the production writer actually calls.
        """
        from boxscore_forge.erasure import erase  # noqa: PLC0415
        from boxscore_forge.lineup_fallback import erase_with_lineup_fallback  # noqa: PLC0415
        from boxscore_forge.publish import to_board  # noqa: PLC0415
        from boxscore_package.format import Package  # noqa: PLC0415
        from boxscore_verify.certify import certify_for_publication  # noqa: PLC0415
        from boxscore_verify.verify import UNSIGNED, verify  # noqa: PLC0415

        direction, slots = cubs_at_braves_1968, self.SLOTS
        target = self.FALLBACK_TARGET

        # ⚠️ Pinned rather than searched. A test that hunts for a target where the plain path misses
        # will quietly pick a different one when the erasure changes, and then it is testing a case
        # nobody chose. If this board stops needing the fallback here, that is a finding.
        assert erase(direction, target_stalls=target, seed=self.SEED) is None, (
            f"the plain path now reaches {target} stalls on this board; the fixture no longer exercises the fallback"
        )
        puzzle, reason = erase_with_lineup_fallback(direction, slots, target_stalls=target, seed=self.SEED)

        assert reason == "fallback", f"expected a fallback board, got {reason!r}"
        assert puzzle is not None

        # ⚠️ Built the way production builds it, not the way a fixture is convenient. The gate refused
        # the first version for two reasons that are entirely correct — an arbitrary `puzzle_id` that
        # no evidence implies, and a missing reveal — and a test that worked around those by not
        # calling the gate is exactly what v29-P2-02 was about.
        from boxscore_verify.expected_id import expected_puzzle_id  # noqa: PLC0415
        from tests.reveals import reveal_for  # noqa: PLC0415

        package = Package(
            puzzle_id=expected_puzzle_id(GAME, OFFENSE),
            puzzle=to_board(direction, puzzle.erased),
            solution=to_board(direction, None),
            labels=("C",) * len(direction.batting),
            pitcher_labels=("SP",) * len(direction.pitching),
            slot_references=tuple(str(slot) for slot in slots),
            reveal=reveal_for(
                to_board(direction, None),
                labels=("C",) * len(direction.batting),
                pitcher_labels=("SP",) * len(direction.pitching),
                offense=OFFENSE,
            ),
            offense_is_home=True,
        )

        # Per-layer attribution first, because "the gate refused it" does not say which layer.
        verdict = verify(package, secret=UNSIGNED)
        assert verdict.accepted, f"the arithmetic layers refused a fallback board: {verdict.rejection}"

        # ⚠⚠ And then the boundary production calls. Passing the layers is not publishing.
        result = certify_for_publication(package, evidence=self._evidence(package), secret=UNSIGNED)

        assert result.publishable, f"a fallback board did not reach publication: {result.refusals}"
