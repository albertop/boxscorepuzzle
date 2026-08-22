"""Every name any script imports from `measure` still resolves after the loader moved.

⚠️⚠️ **The pool moved to `boxscore_forge.pool` on 2026-08-22 and `measure` became a re-export**
(`docs/beta-0-plan.md`, A1). Thirty-odd discovery scripts say `from measure import ...` and none of
them changed — which is the cheap outcome and also the dangerous one, because **nothing in the suite
runs those scripts.** Most need a DSN, so a name dropped from the re-export list breaks them at import
time, months later, on the one afternoon somebody is measuring something.

**This is the check that makes the shim's promise true rather than intended.** It parses every
`from measure import ...` in the repository and asserts the name is actually there. A name removed
from the re-export goes red here instead of in six months.

✔ **It caught something on its first run, which is the only reason to believe it.** `ruff check --fix`
had removed `ZERO_DENSITY_GATE` from `measure.py` — correctly, since the half that stayed no longer used
it — and `discovery/batting-order/measure.py` imported it *through* `measure`. A formatter tidying one
file broke another, silently, in a tree the suite does not execute. The fix was to take the constant
from `boxscore_domain`, where §5 decides it, rather than through a research module.

⚠️ **It reads imports rather than running scripts on purpose.** `CLAUDE.md` says rewrites across call
sites are verified by running, never by reading a diff — and the reason the shim exists is that these
call sites *cannot* be run here. So the guarantee is narrowed honestly: this proves the **names**
resolve, and it does not prove a script produces what it used to. Nothing in a repository without a
database can prove the second.
"""

import ast
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))

import measure  # noqa: E402

from boxscore_forge import pool  # noqa: E402


def imported_names() -> dict[str, set[str]]:
    """Every `from measure import ...` in the tree, by file."""
    found: dict[str, set[str]] = {}
    for path in sorted(_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts or ".venv" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - not a Python file we own
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "measure":
                found.setdefault(str(path.relative_to(_ROOT)), set()).update(alias.name for alias in node.names)
    return found


class TestTheReExportCoversItsCallers:
    def test_every_imported_name_resolves(self) -> None:
        missing = {
            file: sorted(name for name in names if not hasattr(measure, name))
            for file, names in imported_names().items()
        }
        broken = {file: names for file, names in missing.items() if names}

        assert not broken, (
            f"the re-export in discovery/difficulty-metrics/measure.py dropped names that scripts "
            f"still import, and none of those scripts run in this suite:\n"
            f"{chr(10).join(f'  {file}: {names}' for file, names in sorted(broken.items()))}"
        )

    def test_the_scan_finds_the_callers_it_is_named_for(self) -> None:
        # ⚠️ A scan over zero files agrees with itself. This project has shipped that twice — a guard
        # whose match was empty, reporting a real-looking zero. The tree has thirty-odd of these
        # imports; if it ever has under ten, the scan broke rather than the tree changing.
        found = imported_names()

        assert len(found) >= 10, f"only {len(found)} files import from measure, so this scan is broken"
        assert any("discovery" in file for file in found), "no discovery script was scanned"

    @pytest.mark.parametrize("name", ["Loaded", "load", "CONNECTION", "eligibility", "_parse_line_score"])
    def test_the_names_are_the_promoted_ones_and_not_new_definitions(self, name: str) -> None:
        # ⚠️ **A re-export, not a copy — asserted rather than assumed.** If `measure` ever redefines one
        # of these instead of importing it, the tree quietly gains a second definition of the pool rule,
        # which is this project's most-met defect. Every one must be the object `boxscore_forge.pool`
        # holds, by identity.
        assert getattr(measure, name) is getattr(pool, name), (
            f"measure.{name} is not boxscore_forge.pool.{name} — the shim has become a copy"
        )
