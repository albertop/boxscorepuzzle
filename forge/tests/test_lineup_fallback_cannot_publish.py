"""The experimental batting-order fallback must not be reachable from anything that publishes.

⚠️⚠️ **This is the whole safety property of the experiment.** The operator's instruction was explicit:
build the conditional retry, keep publication disabled, do not write the verifier's lineup step. Those
three together mean a fallback board **cannot** ship — but "cannot" has to be a check, not an
intention.

⚠️⚠️ **The first version of this file had two guards that could not fail, and a mutation sweep that
agreed with them.**

- `test_production_erasure_still_passes_no_batting_order` scanned `erasure.py` for `shape_of` calls
  carrying a **keyword** named `slots`. The real call is `shape_of(direction, slots)` — *positional* —
  so the assertion was never able to be false. Worse, the mutation used to "verify" it changed that
  call to `slots=slots`, which is the one change the guard can see and **not the change that matters**.
  Checking a guard against the mutation it happens to catch is not checking it. (v27-P2-14)
- The publication check walked imports **outward** from `certify_for_publication`. Real wiring points
  the other way: a producer imports the fallback *and* imports certification. That bridge leaves
  certification's own import set untouched, so the guard stayed green through the exact mistake it
  named. (v27-P2-15)

Both are replaced below. The direction of the graph walk is now the direction a forbidden call path
actually takes, and the production check reads callers of `erase()` across the whole source tree
rather than one file's internals.
"""

import ast
import pathlib

import pytest

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
EXPERIMENTAL = "boxscore_forge.lineup_fallback"
CERTIFICATION = "boxscore_verify.certify"
FIRST_PARTY = ("boxscore_forge", "boxscore_verify", "boxscore_package", "boxscore_domain")


def _modules() -> dict[str, ast.Module]:
    """Every first-party module, parsed once, keyed by dotted name."""
    found: dict[str, ast.Module] = {}
    for path in SRC.rglob("*.py"):
        dotted = ".".join(path.relative_to(SRC).with_suffix("").parts)
        dotted = dotted.removesuffix(".__init__")
        found[dotted] = ast.parse(path.read_text(encoding="utf-8"))
    return found


def _imports(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def _closure(start: str, graph: dict[str, set[str]]) -> set[str]:
    """Everything `start` depends on, transitively. One hop is not enough for a two-hop mistake."""
    seen: set[str] = set()
    queue = [start]
    while queue:
        module = queue.pop()
        if module in seen or not module.startswith(FIRST_PARTY):
            continue
        seen.add(module)
        queue.extend(graph.get(module, set()))
    return seen


@pytest.fixture(scope="module")
def graph() -> dict[str, set[str]]:
    return {name: _imports(tree) for name, tree in _modules().items()}


class TestNoModuleBridgesTheExperimentToPublication:
    """⚠️ The direction the forbidden path actually takes.

    Nothing certification imports will ever reach the experiment — certification does not call
    producers, producers call it. The mistake to catch is a **third module** that reaches both: it
    builds a board with the fallback and hands it to `certify_for_publication`. Walking outward from
    certification is blind to that by construction, which is how the previous version stayed green.
    """

    def test_the_walker_can_see_both_endpoints(self, graph: dict[str, set[str]]) -> None:
        # ⚠️ A guard that cannot find its subjects passes by being blind. Prove both endpoints are
        # visible before trusting a result that says nothing reaches them.
        assert EXPERIMENTAL in graph, "the experimental module is not in the parsed tree"
        assert CERTIFICATION in graph, "the certification module is not in the parsed tree"
        assert "boxscore_forge.erasure" in _closure(EXPERIMENTAL, graph), "the closure is not following imports"

    def test_no_first_party_module_reaches_both(self, graph: dict[str, set[str]]) -> None:
        bridges = {
            name
            for name in graph
            if name != EXPERIMENTAL and EXPERIMENTAL in _closure(name, graph) and CERTIFICATION in _closure(name, graph)
        }

        assert not bridges, (
            f"{sorted(bridges)} can reach both the experimental fallback and certification, so a "
            f"board built by the fallback can be handed to a verifier that cannot replay its lineup "
            f"step -- see docs/reviews/batting-order-reversal.md"
        )

    def test_nothing_at_all_imports_the_experiment_yet(self, graph: dict[str, set[str]]) -> None:
        """The stronger statement while it is still true, so losing it is visible.

        ⚠️ This is deliberately stricter than the property that matters. When research code legitimately
        imports the fallback, this test fails and gets deleted **on purpose** — leaving the bridge test
        above as the real fence. A guard that quietly stops being strict is worse than one that breaks.
        """
        importers = {name for name, imports in graph.items() if EXPERIMENTAL in imports}

        assert not importers, f"{sorted(importers)} now import the experiment; the bridge test is the fence"


class TestProductionNeverEnablesTheBattingOrder:
    def test_no_call_to_erase_outside_the_experiment_passes_slots(self) -> None:
        """⚠️ Callers of `erase()`, across the whole tree — not one file's internal forwarding.

        The previous version read `shape_of` calls inside `erasure.py` and looked for a keyword that
        the real call does not use. It could not fail. This reads every first-party call to `erase`
        and refuses `slots` anywhere except the module that is allowed to pass it.
        """
        offenders: list[str] = []
        for name, tree in _modules().items():
            if name == EXPERIMENTAL:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                called = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", None)
                if called != "erase":
                    continue
                if any(keyword.arg == "slots" for keyword in node.keywords) or len(node.args) > 1:
                    offenders.append(f"{name}:{node.lineno}")

        assert not offenders, f"production calls erase() with a batting order at {offenders}"

    def test_the_guard_sees_the_one_call_that_is_allowed_to_pass_slots(self) -> None:
        """⚠️ Prove the finder finds `erase` calls at all, or "no offenders" means nothing.

        The experimental module is excluded from the check above; here it is the positive control.
        """
        tree = _modules()[EXPERIMENTAL]
        with_slots = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and getattr(node.func, "id", None) == "erase"
            and any(keyword.arg == "slots" for keyword in node.keywords)
        ]

        assert with_slots, "the finder cannot see the one call that does pass slots, so it finds nothing"


class TestTheVerifierStillHasNoLineupMove:
    """⚠️ The gate is that layer 3 cannot replay a `batting_order` step, so fallback boards are refused.

    If someone writes that move, this test fails — **on purpose**. It is not asserting the move is bad;
    it is asserting that adding it is a decision, taken deliberately, rather than something that
    happens on the way to something else and quietly opens publication to an unconfirmed experiment.
    """

    def test_no_value_producing_lineup_step_exists_in_the_verifier(self) -> None:
        verify_source = "".join(path.read_text(encoding="utf-8") for path in (SRC / "boxscore_verify").glob("*.py"))

        assert "LINEUP_ARITHMETIC" not in verify_source, (
            "the verifier gained a lineup move; fallback boards can now pass layer 3, so the "
            "experiment is no longer fenced off from publication -- see "
            "docs/reviews/batting-order-reversal.md before removing this test"
        )
