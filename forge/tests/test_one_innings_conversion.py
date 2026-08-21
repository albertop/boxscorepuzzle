"""Outs become innings in one place, and every surface asks it for the notation it wants.

⚠️⚠️ **Five copies of the formula existed outside tests, and they had already drifted in front of the
player.** The board printed `4` and the reveal printed `9.0` for the same kind of value, in one
product, on two screens a player sees minutes apart. Neither was wrong about its own surface — a grid
where the keypad offers `.1` and `.2` writes `4`, and a printed boxscore writes `9.0` — but the
notation was being decided by whichever formula the file happened to contain.

**The fix is one function with the notation as a parameter, not one notation everywhere.**
`boxscore_package.innings` converts; `Innings.PRINTED` and `Innings.BOARD` name what to write. The two
docstrings that used to defend opposite rules are two documented format choices now.

This is the same family of guard as `test_no_label_formatting_decisions.py` and
`test_constants_are_not_copied.py`: **the rule is enforced where it can be checked rather than
remembered.** The copies drifted on their own, so remembering was already shown not to work.

⚠️ **The JavaScript half of this rule lives in `serve/tests/engine.test.js`**, because `serve/` shares
no code with `forge/` (§33) and carries its own mirror of the conversion. Neither guard can see the
other's tree; both are named here so the next reader knows there are two.
"""

import ast
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_TREES = (_ROOT / "forge" / "src", _ROOT / "forge" / "scripts", _ROOT / "discovery")

_DEFINITION = "innings.py"
"""The one file allowed to hold the arithmetic. Everything else calls `to_display`."""


def _sources() -> list[Path]:
    found = [
        path
        for tree in _TREES
        for path in tree.rglob("*.py")
        if "_not_in_use" not in path.parts and "__pycache__" not in path.parts
    ]
    assert found, "the scan found no Python at all, which means it is searching the wrong place"
    return found


def _converts_outs_to_innings(tree: ast.AST) -> list[int]:
    """Lines doing the outs-to-innings arithmetic themselves.

    ⚠️ **The shape, not a spelling.** What every copy had in common was dividing something by three and
    taking the remainder of the same thing by three — `f"{outs // 3}.{outs % 3}"` in four of them and
    `Math.floor(outs / 3)` with `outs % 3` in the fifth. A scan for the literal f-string would have
    missed a rewrite that kept the defect, so this asks for the *pair of operations against 3* in one
    statement, which is what a conversion is and what an unrelated `% 3` is not.

    ⚠️ **`divmod(outs, 3)` is not caught and does not need to be**: it is a single operation, and the
    one place entitled to perform it is exempt by filename. A copy written with `divmod` would be a
    genuine miss — recorded here rather than papered over, because a guard's blind spots belong beside
    it. The JavaScript side has no `divmod`, which is where the drift actually happened.
    """
    offences: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.stmt):
            continue
        floor: set[str] = set()
        remainder: set[str] = set()
        for inner in ast.walk(node):
            if not isinstance(inner, ast.BinOp) or not isinstance(inner.right, ast.Constant):
                continue
            if inner.right.value != 3:
                continue
            subject = ast.dump(inner.left)
            if isinstance(inner.op, ast.FloorDiv | ast.Div):
                floor.add(subject)
            elif isinstance(inner.op, ast.Mod):
                remainder.add(subject)
        if floor & remainder:
            offences.append(node.lineno)
    return offences


class TestOneConversionAndTwoNotations:
    @pytest.mark.parametrize("path", _sources(), ids=lambda path: path.name)
    def test_no_file_converts_outs_to_innings_itself(self, path: Path) -> None:
        offences = _converts_outs_to_innings(ast.parse(path.read_text(encoding="utf-8")))

        assert not offences or path.name == _DEFINITION, (
            f"{path.name}:{offences} turns outs into innings itself. "
            f"Call `to_display(outs, Innings.BOARD)` or `Innings.PRINTED` — five copies of this "
            f"formula drifted into two notations on screen at once."
        )

    def test_the_check_can_fire(self) -> None:
        """⚠️ **A guard that cannot fail cannot be told from one that is broken**, and this is the exact
        expression four of the five copies used."""
        reintroduced = ast.parse('cells[0] = f"{line.outs // 3}.{line.outs % 3}"')

        assert _converts_outs_to_innings(reintroduced) == [1]

    def test_the_check_spares_what_it_must(self) -> None:
        """⚠️ **The half that matters**, because every version of a scan that was wrong in this project
        was wrong by matching too much. A remainder against three is ordinary arithmetic; what marks a
        conversion is *both* operations on the same subject in one statement."""
        for innocent in (
            "if outs % 3:\n    pass",
            "whole = outs // 3",
            "keys[9 + (value % 3)].click()",
            "share = division / total",
            "thirds = other % 3\nwhole = outs // 3",
        ):
            assert _converts_outs_to_innings(ast.parse(innocent)) == [], innocent

    def test_the_two_notations_differ_only_where_a_whole_inning_is(self) -> None:
        """The conversion itself, so this file fails if the parameter stops meaning anything."""
        from boxscore_package.innings import Innings, from_display, to_display  # noqa: PLC0415

        assert to_display(12, Innings.PRINTED) == "4.0"
        assert to_display(12, Innings.BOARD) == "4"
        # A partial inning is written the same way by both: the trailing digit is the information.
        assert to_display(13, Innings.PRINTED) == to_display(13, Innings.BOARD) == "4.1"
        # ⚠️ And both parse. The client's parser refused `.0` — the very string this side emits.
        for outs in range(0, 61):
            for notation in Innings:
                assert from_display(to_display(outs, notation)) == outs

    def test_the_default_is_the_one_the_hand_solve_pack_receives(self) -> None:
        """⚠️⚠️ **The pack is §22's launch gate and must not move while it is being solved.**

        `build_pack.py` calls `to_display(outs)` with no notation, and this asserts that the parameter's
        default keeps its output byte-identical. If the default ever changes, the pack's boards change
        underneath a printed answer key — and that failure is silent in the one measurement no test can
        make.
        """
        from boxscore_package.innings import to_display  # noqa: PLC0415

        assert to_display(27) == "9.0", "the hand-solve pack's notation moved"

        pack = (_ROOT / "discovery" / "hand-solve" / "build_pack.py").read_text(encoding="utf-8")
        assert "to_display(line[0])" in pack, "the pack no longer takes the default; re-check its fidelity"
