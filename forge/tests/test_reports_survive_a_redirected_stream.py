"""Nothing a script prints may be un-encodable in cp1252.

⚠️ **Third occurrence, and the second one written by the same hand that had just recorded the rule.**
Every long discovery run on this machine is redirected to a file, Windows gives a redirected stream
cp1252, and `print("\N{WARNING SIGN} ...")` raises `UnicodeEncodeError` at the moment the report is
produced — **after the compute, before the numbers reach anyone**. The first time cost a run. The
second was caught by review inside a file whose own comment, thirty lines above, explained the hazard
in full. The third was a brand-new script written an hour after that correction, and it killed the
report of a measurement that had just finished.

A comment is not stopping this. **A rule this project keeps re-breaking is a rule that has to be
checkable rather than remembered**, which is the same conclusion the label-formatting guard and the
copied-constants guard reached.

⚠️ **Only `print` arguments, and only literals.** The scope is deliberately narrow: source files may
carry any character in comments, docstrings and identifiers, and they do — this file included. What
cannot survive the trip is a character on its way to a redirected stdout. A guard covering the whole
file would fire on every warning sign in every docstring, which is a check that fires on everything and
carries no information.

**The fix is never to weaken the encoding**: it is to write the report in plain text, because a report
that dies on its own decoration loses the compute that produced it.
"""

import ast
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_TREES = (_ROOT / "discovery", _ROOT / "forge" / "scripts", _ROOT / "tools")
_ENCODING = "cp1252"


def _sources() -> list[Path]:
    found = [path for tree in _TREES for path in tree.rglob("*.py") if "_not_in_use" not in path.parts]
    assert found, "no sources found; the paths in this test are wrong"
    return found


def _unprintable(tree: ast.AST) -> list[tuple[int, str]]:
    """Lines whose `print` carries a literal cp1252 cannot encode.

    Reaches inside f-strings: `f"\N{WARNING SIGN} {count} boards"` is a `JoinedStr` whose literal parts
    are `Constant` nodes, and the warning sign is in one of them. The interpolated values are not
    checked — they are data, and a datum that cannot encode is a different problem with a different
    fix.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "print":
            continue
        for argument in node.args:
            pieces = argument.values if isinstance(argument, ast.JoinedStr) else [argument]
            for piece in pieces:
                if not (isinstance(piece, ast.Constant) and isinstance(piece.value, str)):
                    continue
                try:
                    piece.value.encode(_ENCODING)
                except UnicodeEncodeError as refused:
                    offending = piece.value[refused.start : refused.end]
                    found.append((node.lineno, offending))
    return sorted(set(found))


class TestNoReportDiesOnItsOwnDecoration:
    @pytest.mark.parametrize("path", _sources(), ids=lambda path: path.name)
    def test_everything_this_file_prints_survives_a_redirected_stream(self, path: Path) -> None:
        offences = _unprintable(ast.parse(path.read_text(encoding="utf-8")))

        assert not offences, (
            f"{path.name} prints {offences}, which {_ENCODING} cannot encode. A redirected run on "
            f"Windows raises UnicodeEncodeError here and loses the compute that produced the report. "
            f"Write it in plain text."
        )

    def test_the_check_fires_on_a_warning_sign(self) -> None:
        # ⚠️ The exact line that killed the footnote-multiplicity report, an hour after the same defect
        # was corrected in the ceiling pack. A guard that cannot fail is indistinguishable from one that
        # is broken.
        offending = ast.parse('print("\N{WARNING SIGN} One unreadable row makes the board unsolvable")')

        assert _unprintable(offending) == [(1, "\N{WARNING SIGN}")]

    def test_the_check_reaches_inside_an_f_string(self) -> None:
        # The shape most report lines actually take, and the one a naive scan of `ast.Constant`
        # arguments would miss entirely.
        offending = ast.parse('print(f"\N{WARNING SIGN} {count} of {total} boards")')

        assert _unprintable(offending) == [(1, "\N{WARNING SIGN}")]

    def test_the_check_ignores_a_warning_sign_that_is_not_printed(self) -> None:
        """⚠️ The half that decides whether this guard is worth keeping.

        Docstrings, comments and non-`print` strings carry these characters everywhere in this project
        and are perfectly safe — they never reach a stream. A guard that fired on them would fire on
        almost every file, and a check that fires on everything carries no information.
        """
        innocent = ast.parse('"""\N{WARNING SIGN} A docstring."""\nmessage = "\N{WARNING SIGN} not printed"')

        assert _unprintable(innocent) == []

    def test_plain_text_passes(self) -> None:
        assert _unprintable(ast.parse('print("NOTE: one unreadable row makes the board unsolvable")')) == []
