"""No logical decision in this project may be made by inspecting a label's formatting.

⚠️ **Three places did, and all three failed together.** The row-label suffix was a presentation
convention that quietly became the source of truth for three decisions: whether to indent a row,
whether a board carries a substitution, and which board the reference writer should pick. Each asked
`"-" in label`. Each was really asking a question about the **lineup slot**. They agreed while the
suffix existed and broke in the same commit when it was removed — one of them silently, until a pack
refused to build.

Nobody declared the suffix a contract. It became one by habit, which is the half of the pattern that
is easy to miss: a mechanism kept past its problem does not only constrain what comes after it, it
becomes a hidden dependency of what comes after it. **When a mechanism is removed, look for who was
reading it, not only who was writing it.**

This is the same kind of guard as the one that rejects a duplicated candidate list: the rule is
enforced where it can be checked rather than remembered.
"""

import ast
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_TREES = (_ROOT / "forge" / "src", _ROOT / "forge" / "scripts", _ROOT / "discovery")

# The renderers may look at a label — drawing one is their job. Everything else must ask the data.
#
# ⚠️ **By path, never by basename.** (v36-P3-18) A set of names checked against `path.name`
# exempts *any* file so called anywhere in scope, and `docs/python-conventions.md` states the rule
# the sibling constants guard already follows. An exemption that matches a filename is one a new
# directory can claim by accident.
_MAY_FORMAT = {_ROOT / "discovery" / "pitcher-cap" / "render_boards.py"}


def _sources() -> list[Path]:
    found = [path for tree in _TREES for path in tree.rglob("*.py") if "_not_in_use" not in path.parts]
    assert found, "no sources found; the paths in this test are wrong"
    return found


def _label_formatting_tests(tree: ast.AST) -> list[int]:
    """Lines asking whether a punctuation mark appears in something whose name mentions a label.

    ⚠️ **The soft edge, recorded rather than left for someone to find.** (v36-P3-18) This matches
    the `"<punct>" in label` shape and nothing else. `label.split("-")`, `label.endswith("-1")` and
    `label.count("-")` are realistic reintroductions it cannot see — the same decision in different
    syntax. The sibling constants guard documents its own narrowness; this one did not, and **an
    undocumented blind spot in a guard reads as coverage**.

    Widening it is a change to make when one of those shapes appears: a matcher firing on
    `"-" in name` for any `name` would flag ordinary string work across the tree, and a check that
    cries wolf gets switched off — worse than a narrow one that holds.
    """
    offences: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) or not any(isinstance(op, ast.In) for op in node.ops):
            continue
        left = node.left
        if not (isinstance(left, ast.Constant) and isinstance(left.value, str) and not left.value.isalnum()):
            continue
        for right in node.comparators:
            name = right.id if isinstance(right, ast.Name) else getattr(right, "attr", "")
            if "label" in name.lower():
                offences.append(node.lineno)
    return offences


class TestNoDecisionReadsALabelsFormatting:
    @pytest.mark.parametrize("path", _sources(), ids=lambda path: path.name)
    def test_the_file_asks_the_data_and_not_the_label(self, path: Path) -> None:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offences = _label_formatting_tests(tree)

        assert not offences or path in _MAY_FORMAT, (
            f"{path.name}:{offences} decides something by inspecting a label's formatting. "
            f"Ask the lineup slot — a label is drawn, not interrogated."
        )

    def test_the_check_can_fire(self) -> None:
        # A guard that cannot fail is indistinguishable from one that is broken. This is the exact
        # expression the three broken call sites used.
        offending = ast.parse('has_substitution = any("-" in label for label in loaded.labels)')

        assert _label_formatting_tests(offending) == [1]
