"""`load(gated=...)` decides whether §5's gate is in the query. It did not, for a long time.

⚠️⚠️ **The defect was a parameter that lied, and it produced no wrong number at all.** (v36-P2-20)
`load()` built `gate_clause = zero_density_clause(gate)` unconditionally and `eligibility()`
interpolated it unconditionally, so **every sample it ever returned was gated** — while its docstring
said *off by default* and its signature said `gated: bool = False`. Thirty-three call sites passed
`gated=True` and got what they asked for; eight omitted it and got the same thing.

**So no figure was wrong. What was wrong was what the code said about the figures** — and that is the
more expensive kind, because a signature is read far more often than it is passed. Reasoning from it
produces confident, specific, wrong conclusions about which measurements describe which population,
and there is no number anywhere that contradicts them.

⚠️ These tests read the **rendered SQL** rather than calling the database. `eligibility()` is a pure
string builder, which is the whole reason it can be checked here at all; a test needing the connection
would run nowhere but the laptop.
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_METRICS = _ROOT / "discovery" / "difficulty-metrics"
if str(_METRICS) not in sys.path:
    sys.path.insert(0, str(_METRICS))

from measure import eligibility, zero_density_clause  # noqa: E402

from boxscore_domain import ZERO_DENSITY_GATE  # noqa: E402

_MARKER = "batting_zeros"
"""A fragment that appears only in the gate's predicate, so its presence is the gate's presence."""


class TestTheClauseIsWhatItClaims:
    def test_the_gate_predicate_names_the_gate_it_was_given(self) -> None:
        assert str(ZERO_DENSITY_GATE) in zero_density_clause(ZERO_DENSITY_GATE)
        assert _MARKER in zero_density_clause(ZERO_DENSITY_GATE)

    def test_eligibility_carries_the_clause_it_is_handed(self) -> None:
        assert _MARKER in eligibility(gate_clause=zero_density_clause(ZERO_DENSITY_GATE))

    def test_eligibility_without_a_clause_has_no_gate_in_it(self) -> None:
        """⚠️ The half that can fail. A builder that always emitted the predicate would satisfy the
        test above and be exactly the defect this file is about."""
        assert _MARKER not in eligibility()


class TestLoadReadsTheFlag:
    """⚠️⚠️ Read off `load`'s source, and that is a compromise stated rather than hidden.

    The behavioural test is `load(gated=False)` against a database, which exists on one machine. What
    can run anywhere is that the one line deciding this is conditional — and the defect was precisely
    that it was not. `CLAUDE.md` records that a regular expression over code cannot tell a name from
    the tail of another name, so this matches the whole statement rather than a fragment of it.
    """

    @staticmethod
    def _source() -> str:
        return (_METRICS / "measure.py").read_text(encoding="utf-8")

    def test_the_gate_clause_is_conditional_on_the_flag(self) -> None:
        source = self._source()

        assert 'gate_clause = zero_density_clause(gate) if gated else ""' in source, (
            "load() builds the gate predicate unconditionally again: `gated` is decoration and every "
            "sample is gated whatever the caller asked for (v36-P2-20)"
        )

    def test_no_caller_leaves_the_flag_to_the_default(self) -> None:
        """⚠️⚠️ The default is `False` and every caller wants `True`, which is a trap left armed.

        Eight call sites omitted the flag while it did nothing, so they were gated; the moment it
        started working they would have silently become ungated — **a fix turning eight correct
        measurements into wrong ones, with nothing to notice.** They name it now. Until the default is
        reconsidered, omitting it is forbidden here rather than left to whoever reads the signature.
        """
        import ast  # noqa: PLC0415

        offenders: list[str] = []
        for path in [
            *sorted((_ROOT / "discovery").rglob("*.py")),
            _ROOT / "forge" / "scripts" / "write_reference_puzzles.py",
        ]:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "load"):
                    continue
                if not any(keyword.arg == "gated" for keyword in node.keywords):
                    offenders.append(f"{path.relative_to(_ROOT)}:{node.lineno}")

        assert not offenders, (
            f"load() called without saying whether the pool is gated, at {offenders}. The default is "
            f"`False` and every instrument in this tree wants `True`."
        )

    def test_the_finder_sees_a_call_that_omits_it(self) -> None:
        """⚠️ Positive control. *No offenders* from a finder that finds nothing is not a result, and
        this project has produced that eight times."""
        import ast  # noqa: PLC0415

        tree = ast.parse("sample = load(35)")
        found = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "load"
            and not any(keyword.arg == "gated" for keyword in node.keywords)
        ]

        assert len(found) == 1


@pytest.mark.parametrize("gate", [0.25, ZERO_DENSITY_GATE])
def test_a_stricter_gate_and_a_looser_one_render_different_sql(gate: float) -> None:
    """The number reaches the query. Two gates that rendered identically would make the whole
    0.25-versus-0.30 distinction unobservable, which is the thing being annotated everywhere else."""
    assert f"< {gate}" in zero_density_clause(gate)
