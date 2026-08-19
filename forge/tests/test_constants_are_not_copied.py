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
