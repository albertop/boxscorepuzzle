"""The format half must not be able to reach the signing half.

⚠️ **The split holds today by habit, not by contract.** `format.py` imports nothing from `signing.py`
and nothing from `cryptography`, and `__init__.py` is a docstring, so importing the format pulls in
neither. Nothing fails if that stops being true — and a rule with no check is the defect this project
has recorded more often than any other.

§33's property is that **whoever verifies cannot sign**, and `docs/serve-brief.md` adds the second
reason the split matters: `format.py` is what gets re-expressed in the client's language, so a verifier
sitting inside it is a verifier copied into the browser by accident.

These assert the closure by **importing in a fresh interpreter and looking at what arrived**, rather
than by reading the source for import statements — a grep would miss a deferred import inside a
function, which is exactly how the dependency would return.
"""

import subprocess
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"

FORBIDDEN = ("boxscore_package.signing", "cryptography", "nacl")


def _modules_after(statement: str) -> set[str]:
    """Every module loaded in a fresh interpreter after `statement`."""
    program = (
        "import sys"
        + chr(10)
        + f"sys.path.insert(0, {str(_SRC)!r})"
        + chr(10)
        + statement
        + chr(10)
        + "print(chr(10).join(sorted(sys.modules)))"
    )
    # The program is built in this file from a literal statement; nothing here comes from outside.
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", program], capture_output=True, text=True, encoding="utf-8", check=True
    )
    return set(result.stdout.split())


@pytest.mark.parametrize("statement", ["import boxscore_package", "import boxscore_package.format"])
def test_the_format_side_loads_no_verifier(statement: str) -> None:
    loaded = _modules_after(statement)

    reached = sorted(name for name in loaded for banned in FORBIDDEN if name == banned or name.startswith(banned + "."))

    assert not reached, f"{statement} pulled in {reached}; the format half must not reach the signing half"


def test_the_signing_side_does_reach_the_format() -> None:
    """The direction that is allowed, asserted so the test above cannot pass by nothing importing at all.

    A guard that forbids everything is indistinguishable from a guard that runs against an empty module.
    """
    loaded = _modules_after("import boxscore_package.signing")

    assert "boxscore_package.format" in loaded
    assert "cryptography.hazmat.primitives.asymmetric.ed25519" in loaded


def test_the_package_root_is_inert() -> None:
    # `__init__.py` re-exporting either half would defeat the split for every consumer at once, and the
    # cost of noticing is one import.
    loaded = _modules_after("import boxscore_package")

    assert "boxscore_package.format" not in loaded, "the root drags the format in; a consumer cannot opt out"
    assert "boxscore_package.signing" not in loaded, "the root drags the verifier in"
