"""A decided value may be spelled in one place. Anywhere else it is a literal, and literals drift.

⚠️ **One definition was not enough on its own, and this project has the receipt.** The erasable set was
given a single definition and the copies were not removed by that act — nothing stopped them existing,
so they went on existing. The pitcher cap is the same story told slower: `≤4` was a decision recorded
in `CLAUDE.md`, in `§5`, in `§6`, and spelled as an argument at twenty-five call sites. When the
measurement behind it turned out to be invalid, the number was in twenty-six places and the reason was
in none of them.

**So the rule is enforced where it can be checked rather than remembered.** Same family as the guard
rejecting a decision made by inspecting a label's formatting, and for the same reason: a convention
nobody can violate accidentally is worth more than a convention everybody agrees with.

⚠️⚠️ **What this guard cannot see, stated here so its passing is not read as more than it is: it
catches duplication, never divergence.**

It fires on a file spelling `6` where it could import `PITCHER_CAP` — the *same* number for the same
knob, written twice. It is structurally blind to a *different* number for the same knob, and that is
the shape the reference writer carried for weeks: `GATE = 0.25` standing beside a decided
`ZERO_DENSITY_GATE = 0.30`, deciding which boards `serve` was built against (v36-P3-36). No literal
was copied, so nothing here fired, and there was nothing wrong with the check.

**The two failures are not variants of each other.** A copy is findable because both places hold the
same token, which is what makes an AST match possible at all. A divergence holds a token that appears
nowhere else — the only thing tying `0.25` to `ZERO_DENSITY_GATE` is that both are the zero-density
gate, and that is a fact about meaning, not about syntax. **No extension of this guard reaches it**;
what reaches it is the convention that a value shaping the product carries its reason, its measurement
and its `PROVISIONAL` marker beside it, because a bare `GATE = 0.25` with none of the three is visible
to a reader even when the number it disagrees with is in another file.

⚠️ **So a green run here means no constant was copied. It does not mean no constant has drifted**, and
the drift is the one that changed what shipped.

⚠️ **This checks the caps, not every number in `boxscore_domain`.** A guard that fires on every
occurrence of `5` or `3` in the source tree would be noise, and a check that fires on everything carries
no information — exactly like one that never fires. The caps are the values with a history of being
copied, they are compared against row counts in a recognisable shape, and that shape is what makes them
findable without matching arithmetic that happens to use the same digit.
"""

import ast
from pathlib import Path

import pytest

from boxscore_domain import BATTER_CAP, PITCHER_CAP

_ROOT = Path(__file__).resolve().parents[2]
_TREES = (_ROOT / "forge" / "src", _ROOT / "forge" / "scripts", _ROOT / "forge" / "tests", _ROOT / "discovery")

_CAPS = {BATTER_CAP: "BATTER_CAP", PITCHER_CAP: "PITCHER_CAP"}

_GATE_NAMES = ("gate",)
"""Names that mean *the zero-density gate* wherever they appear — as a binding or as a keyword.

⚠️⚠️ **This is why the gate is catchable and the general divergence problem is not.** The blind spot
recorded above holds for a number standing alone: nothing in the syntax ties a bare `0.25` to
`ZERO_DENSITY_GATE`. The gate escapes it for one reason only — **every place that sets it names it** —
`GATE = 0.25`, `load(..., gate=0.25)`, `zero_density_clause(0.30)`. The name is the token both sides
share, so the match is possible again.

⚠️ **So this fires on any float in those positions, not only on `0.25`.** A cap is copied by repeating
the same digit; the gate was broken by writing a *different* one. Restricting the guard to the values
seen so far would rebuild exactly the blind spot it is here to close — and a correct copy is still a
copy, so `GATE = 0.30` fails too.
"""

_GATE_CALLS = ("zero_density_clause",)
"""Calls whose first positional argument is the gate."""

_MAY_SPELL_THEM = {
    # The definition itself. **By path, not by basename** — exempting `__init__.py` would exempt every
    # package in the tree, which is a hole the size of the guard.
    Path("forge/src/boxscore_domain/__init__.py"),
    # This file spells both caps in its own fixtures, which is what proves the check can fire.
    Path("forge/tests/test_constants_are_not_copied.py"),
    # ⚠️ Instruments whose *recorded results* were measured at a different cap. Rewriting their
    # arguments would make a published number unreproducible and quietly reattribute it to a board
    # family it never measured. They keep their literal, and the literal is now the documentation of
    # what they measured.
    Path("discovery/pool-at-4-pitchers/remeasure.py"),
    Path("discovery/pool-at-4-pitchers/resolution_in_range.py"),
    Path("discovery/pitcher-cap/measure_pitching.py"),
    Path("discovery/pitcher-cap/render_boards.py"),
}


_MAY_SPELL_THE_GATE = {
    # The two definitions: the decided gate and its one named deviation.
    Path("forge/src/boxscore_domain/__init__.py"),
    # This file spells it in its own fixtures, which is what proves the check can fire.
    Path("forge/tests/test_constants_are_not_copied.py"),
}


def _sources() -> list[Path]:
    found = [path for tree in _TREES for path in tree.rglob("*.py") if "_not_in_use" not in path.parts]
    assert found, "no sources found; the paths in this test are wrong"
    return found


def _copied_caps(tree: ast.AST) -> list[tuple[int, str]]:
    """Lines spelling a cap as a literal in a shape that means *the cap*.

    Two shapes, which is what every real copy has looked like:

      `max_pitchers=4`   — a keyword argument named for the cap
      `len(rows) <= 13`  — an **ordering** comparison against a length

    ⚠️ **Both require the literal to be doing the cap's job**, not merely to be the same digit. A guard
    matching every bare `6` would fire on innings, on column counts and on outs, and would be switched
    off within a week — a check that fires on everything carries no information, exactly like one that
    never fires.

    ⚠️ **Ordering, not equality, and that line was drawn after the guard's own test caught it.** The
    first version matched any comparison, and `if len(row) != 6:` — the column count, which is six and
    is not the pitcher cap — was structurally identical to `len(board.pitching) <= 6`. A cap is a bound
    and is always asked with `<`, `<=`, `>` or `>=`; a width is asked with `==` or `!=`. That is the
    difference the guard reads, and it is stated here because it is the guard's one soft edge.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg and node.arg.endswith(("batters", "pitchers")):
            value = node.value
            if isinstance(value, ast.Constant) and value.value in _CAPS:
                found.append((value.lineno, _CAPS[value.value]))
        if isinstance(node, ast.Compare):
            sides = [node.left, *node.comparators]
            lengths = [
                side
                for side in sides
                if isinstance(side, ast.Call) and isinstance(side.func, ast.Name) and side.func.id == "len"
            ]
            ordered = any(isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)) for op in node.ops)
            constants = [side for side in sides if isinstance(side, ast.Constant) and side.value in _CAPS]
            if ordered and lengths and constants:
                found.append((constants[0].lineno, _CAPS[constants[0].value]))
    return sorted(set(found))


def _copied_gate(tree: ast.AST) -> list[int]:
    """Lines spelling §5's zero-density gate as a float literal in a shape that means *the gate*.

    Four shapes, which is every way this project has written it:

      `GATE = 0.25`                    — bound to a name meaning the gate
      `load(..., gate=0.30)`           — passed as the keyword that names it
      `def load(*, gate=0.25)`         — a default that quietly decides for every caller
      `zero_density_clause(0.25)`      — the one call whose first argument is the gate

    ⚠️ **Floats only.** A bare `0.25` bound to anything else is somebody's ratio and is none of this
    guard's business; a check firing on every float in the tree would be switched off within a week.
    """
    found = [
        node.value.lineno
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and _is_float(node.value) and _binds_the_gate(node)
    ]
    found += [
        node.value.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.keyword) and node.arg in _GATE_NAMES and _is_float(node.value)
    ]
    found += [
        default.lineno for node in ast.walk(tree) if isinstance(node, ast.arguments) for default in _gate_defaults(node)
    ]
    found += [
        node.args[0].lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _GATE_CALLS
        and node.args
        and _is_float(node.args[0])
    ]
    return sorted(set(found))


def _is_float(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, float)


def _binds_the_gate(node: ast.Assign | ast.AnnAssign) -> bool:
    """Whether this assignment's target is a name meaning the gate — `GATE`, `POOL_GATE`, `gate`."""
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return any(
        isinstance(target, ast.Name) and target.id.lower().removesuffix("_gate") in ("", *_GATE_NAMES)
        for target in targets
    )


def _gate_defaults(node: ast.arguments) -> list[ast.expr]:
    """Float defaults sitting on a parameter named for the gate.

    ⚠️ Defaults are right-aligned against the positional parameters, and keyword-only defaults are a
    separate list that lines up one-to-one. Getting the alignment wrong here would silently attribute a
    default to the wrong parameter, which is a guard that reports the wrong line — worse than one that
    reports nothing.
    """
    positional = [*node.posonlyargs, *node.args]
    aligned: list[tuple[ast.arg, ast.expr | None]] = [
        *zip(positional, [None] * (len(positional) - len(node.defaults)) + list(node.defaults), strict=True),
        *zip(node.kwonlyargs, node.kw_defaults, strict=True),
    ]
    return [
        default
        for argument, default in aligned
        if argument.arg in _GATE_NAMES and default is not None and _is_float(default)
    ]


class TestNoFileSpellsTheGateItCouldImport:
    """⚠️⚠️ Added once the gate was centralised, because until then it had nothing to catch.

    Seventeen instruments in `discovery/` wrote the gate by hand — **fourteen at `0.25` against a
    decided `ZERO_DENSITY_GATE` of `0.30`**, none of them saying why, and the difference decided which
    boards every one of their figures described. Two of those figures were recorded in `todo.md` as an
    unexplained disagreement between correct instruments; they were on opposite sides of this split.

    They read the constant now, so a re-introduced literal is a copy again — and a copy is the shape
    this file can see.
    """

    @pytest.mark.parametrize("path", _sources(), ids=lambda path: path.name)
    def test_the_file_imports_the_gate_instead_of_spelling_it(self, path: Path) -> None:
        offences = _copied_gate(ast.parse(path.read_text(encoding="utf-8")))

        assert not offences or path.relative_to(_ROOT) in _MAY_SPELL_THE_GATE, (
            f"{path.name} spells the zero-density gate as a literal at lines {offences}. "
            f"Import `ZERO_DENSITY_GATE` from `boxscore_domain`, or — if the deviation is intended — "
            f"give it a name and a reason there, as `HAND_SOLVE_ZERO_DENSITY_GATE` does."
        )

    def test_the_check_fires_on_a_module_level_binding(self) -> None:
        # ⚠️ The exact line that stood in fourteen instruments.
        assert _copied_gate(ast.parse("GATE = 0.25")) == [1]

    def test_the_check_fires_on_a_correct_copy_too(self) -> None:
        """⚠️ The half that makes this about divergence rather than duplication.

        `0.30` agrees with the constants module today. It is still a second place the number is
        written, which is how `0.25` came to exist beside it in the first place.
        """
        assert _copied_gate(ast.parse("GATE = 0.30")) == [1]

    def test_the_check_fires_on_a_keyword_argument(self) -> None:
        assert _copied_gate(ast.parse("sample = load(4, gated=True, gate=0.25)")) == [1]

    def test_the_check_fires_on_a_default_that_decides_for_every_caller(self) -> None:
        """The worst shape of the four: it sets the gate for callers that never mention one."""
        assert _copied_gate(ast.parse("def load(count, *, gated=False, gate=0.25):\n    pass")) == [1]

    def test_the_check_fires_on_the_sql_clause_builder(self) -> None:
        assert _copied_gate(ast.parse("clause = zero_density_clause(0.30)")) == [1]

    def test_the_check_accepts_the_constant_everywhere_it_accepts_a_literal(self) -> None:
        """⚠️ The fixed version of each shape above, so the guard is not simply refusing the position."""
        clean = ast.parse(
            "\n".join(
                (
                    "GATE = ZERO_DENSITY_GATE",
                    "sample = load(4, gated=True, gate=ZERO_DENSITY_GATE)",
                    "clause = zero_density_clause(ZERO_DENSITY_GATE)",
                    "STRICT = HAND_SOLVE_ZERO_DENSITY_GATE",
                )
            )
        )

        assert _copied_gate(clean) == []

    def test_the_check_ignores_a_float_doing_another_job(self) -> None:
        """⚠️ The half that decides whether this guard survives contact with the tree.

        Real lines from `discovery/`. `0.25` and `0.30` are ordinary numbers in a codebase full of
        proportions, and a guard firing on all of them carries no information — the same outcome as
        never firing.
        """
        innocent = ast.parse(
            "\n".join(
                (
                    "_PERCENTILE = 0.9",
                    "share = 0.25",
                    "threshold = 0.30",
                    "found = correlate(xs, ys, tolerance=0.25)",
                    # An integer in the gate's own position: a count, not a proportion.
                    "sample = load(4, gate=1)",
                )
            )
        )

        assert _copied_gate(innocent) == []


class TestNoFileSpellsACapItCouldImport:
    @pytest.mark.parametrize("path", _sources(), ids=lambda path: path.name)
    def test_the_file_imports_the_cap_instead_of_spelling_it(self, path: Path) -> None:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offences = _copied_caps(tree)

        assert not offences or path.relative_to(_ROOT) in _MAY_SPELL_THEM, (
            f"{path.name} spells a roster cap as a literal at {offences}. "
            f"Import it from `boxscore_domain` — the value moved once already and left twenty-six copies."
        )

    def test_the_check_fires_on_a_keyword_argument(self) -> None:
        # ⚠️ The exact expression that stood at twenty-five call sites before the cap moved. A guard
        # that cannot fail is indistinguishable from one that is broken.
        offending = ast.parse("sample = load(6, gated=True, max_batters=13, max_pitchers=6)")

        assert _copied_caps(offending) == [(1, "BATTER_CAP"), (1, "PITCHER_CAP")]

    def test_the_check_fires_on_a_length_comparison(self) -> None:
        # The other shape a copy takes: asserting a board respects a cap, with the cap written out.
        offending = ast.parse("assert len(board.pitching) <= 6")

        assert _copied_caps(offending) == [(1, "PITCHER_CAP")]

    def test_the_check_ignores_the_same_digit_doing_another_job(self) -> None:
        """⚠️ The half that decides whether this guard survives.

        A check firing on every `6` in the tree carries no information and gets deleted or ignored,
        which is the same outcome as never firing. These are real lines from the source trees where the
        digit is not a cap.
        """
        innocent = ast.parse(
            "\n".join(
                (
                    "outs = innings * 3",
                    # The column count. Six, like the pitcher cap, and asked with `!=` because it is a
                    # width rather than a bound. This is the line that shaped the rule above.
                    "if len(row) != 6:",
                    "    pass",
                    "found = solve(shape, given, max_solutions=13)",
                )
            )
        )

        assert _copied_caps(innocent) == []
