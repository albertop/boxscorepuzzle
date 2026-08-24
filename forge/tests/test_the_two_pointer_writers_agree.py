"""The two scripts that write a dated pointer must write the same document.

⚠️⚠️ **This exists because they drifted, and the drift was invisible from either file.** `build_inventory`
dates the calendar and `write_reference_puzzles` dates six development boards from a fixed day; their
docstrings say the *dating* is deliberately not shared and that is right. **The field set and the version
are not the dating.** A field added to one writer left the other producing a different document -- and
the second one is the batch the dev server and the browser suite read, so the browser test named *the
real pointers still read* was reading a document production no longer produces, green the whole time.

**Each file was internally consistent and neither stated the other's half**, which is the shape
`CLAUDE.md` records for the two Dockerfiles and the uid. The repair is the same: the fact lives in two
files, so it lives in neither -- `boxscore_package.format.pointer` builds the body and both call it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _ROOT / "forge" / "scripts"
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_SCRIPTS))

from boxscore_package.format import POINTER_SCHEMA, pointer  # noqa: E402


def _module(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def writers() -> tuple[ModuleType, ModuleType]:
    return _module("build_inventory"), _module("write_reference_puzzles")


def test_neither_writer_spells_the_pointer_body_itself() -> None:
    """⚠️ **The guard that would have caught it.** A writer building the dict inline is a second field set.

    Seen red by putting the literal back in `write_reference_puzzles`: it names the file and the key.
    """
    for name in ("build_inventory", "write_reference_puzzles"):
        source = (_SCRIPTS / f"{name}.py").read_text(encoding="utf-8")
        assert '"puzzle_id":' not in source, (
            f"{name}.py spells a pointer field itself; the body belongs to boxscore_package.format.pointer"
        )


def test_the_body_carries_every_field_a_pointer_needs() -> None:
    """⚠️ And the other half: a helper both writers call is only worth having if it is complete.

    `serve/ui/phone/daily.js` reads `date` and `puzzle_id`; the rotation reads `generation`. A body
    missing one of them would be shared and still wrong.
    """
    body = pointer(day="2026-09-02", puzzle_id="abc123", generation="deadbeef")
    assert set(body) == {"date", "generation", "puzzle_id", "schema"}
    assert body["schema"] == POINTER_SCHEMA
