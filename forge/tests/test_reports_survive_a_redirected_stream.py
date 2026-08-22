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

⚠️⚠️ **Fourth occurrence, 2026-08-22, and the first this guard could not see.** `build_inventory.py`
passed `description=__doc__` to `argparse`, whose `--help` writes that docstring to stdout — so a module
docstring carrying warning signs became a report on its way to a redirected stream, without a single
`print` involved. **The guard was reading the wrong verb.** It covers argparse now: help text must be
plain, and a docstring is never help text.

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


class TestHelpTextIsAlsoAReportOnItsWayToAStream:
    """⚠️ `argparse` prints, and it was outside the scan above because it is not spelled `print`.

    The scope stays narrow for the same reason: what is checked is the text argparse will *write*, not
    the file it lives in. A docstring may carry anything; the moment it becomes `description=` it stops
    being a docstring and becomes output.
    """

    def test_no_script_hands_argparse_its_module_docstring(self) -> None:
        offenders: list[str] = []
        for path in _sources():
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                    continue
                if node.func.attr != "ArgumentParser":
                    continue
                for keyword in node.keywords:
                    if isinstance(keyword.value, ast.Name) and keyword.value.id == "__doc__":
                        offenders.append(f"{path.relative_to(_ROOT)}:{node.lineno} {keyword.arg}=__doc__")

        assert not offenders, (
            "argparse writes help to stdout and a module docstring may carry anything; a redirected "
            f"stream on Windows is {_ENCODING}. Write a plain description instead: {offenders}"
        )

    def test_every_argparse_string_survives_the_encoding(self) -> None:
        # The general form: any literal handed to argparse is text it may print. `help=` strings are the
        # ones most likely to grow a warning sign later, and nothing else would catch it.
        offenders: list[str] = []
        for path in _sources():
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                    continue
                if node.func.attr not in {"ArgumentParser", "add_argument"}:
                    continue
                for keyword in node.keywords:
                    if not (isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str)):
                        continue
                    try:
                        keyword.value.value.encode(_ENCODING)
                    except UnicodeEncodeError:
                        offenders.append(f"{path.relative_to(_ROOT)}:{node.lineno} {keyword.arg}=")

        assert not offenders, f"argparse text that cannot reach a redirected stream: {offenders}"

    def test_the_scan_would_catch_the_defect_it_was_written_for(self) -> None:
        # ⚠️ A scan that finds nothing is indistinguishable from one that is broken. This asserts the
        # matcher fires on the exact source that raised, rather than on a hand-made example.
        lines = ["import argparse", 'p = argparse.ArgumentParser(description="\N{WARNING SIGN} x")']
        broken = ast.parse("\n".join(lines))
        found = [
            keyword.arg
            for node in ast.walk(broken)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            for keyword in node.keywords
            if isinstance(keyword.value, ast.Constant) and _cannot_encode(keyword.value.value)
        ]

        assert found == ["description"], "the argparse scan no longer recognises its own defect"


def _cannot_encode(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        value.encode(_ENCODING)
    except UnicodeEncodeError:
        return True
    return False
