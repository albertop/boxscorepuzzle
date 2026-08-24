"""The two scripts that write a dated pointer must write the same document.

⚠️⚠️ **This exists because they drifted, and the drift was invisible from either file.** `build_inventory`
dates the calendar and `write_reference_puzzles` dates six development boards from a fixed day; their
docstrings say the *dating* is deliberately not shared and that is right. **The field set and the version
are not the dating.** When the pointer gained `next_rotation` and went to `POINTER_SCHEMA` 2, only the
calendar writer was changed -- so the batch the dev server and the browser suite read was a schema-1
document production no longer produces. The countdown could not appear locally, and the browser test
named *the real pointers still read* was reading the wrong real pointer, green the whole time.

**Each file was internally consistent and neither stated the other's half**, which is the shape
`CLAUDE.md` records for the two Dockerfiles and the uid. The repair is the same: the fact lives in two
files, so a guard asserts they agree.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _ROOT / "forge" / "scripts"
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_SCRIPTS))

from boxscore_package.format import POINTER_SCHEMA, next_rotation, pointer  # noqa: E402


def _module(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def writers() -> tuple[ModuleType, ModuleType]:
    return _module("build_inventory"), _module("write_reference_puzzles")


def test_both_writers_spell_the_same_rollover(writers: tuple[ModuleType, ModuleType]) -> None:
    """The one comparison the `publish` copy cannot have, because it is in another tree."""
    builder, reference = writers
    assert builder.ROLLOVER_OFFSET_HOURS == reference.ROLLOVER_OFFSET_HOURS


def test_both_agree_with_the_document_that_states_it(writers: tuple[ModuleType, ModuleType]) -> None:
    """`docs/calendar.md` is where the decision lives; every spelling cites it and must match it."""
    stated = re.search(r"ROLLOVER_OFFSET_HOURS = (-?\d+)", (_ROOT / "docs" / "calendar.md").read_text(encoding="utf-8"))
    assert stated, "docs/calendar.md no longer states ROLLOVER_OFFSET_HOURS, which the trees point at"
    for module in writers:
        assert int(stated[1]) == module.ROLLOVER_OFFSET_HOURS


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

    `serve/ui/phone/daily.js` reads `date`, `puzzle_id` and `next_rotation`; the rotation reads
    `generation`. A body missing one of them would be shared and still wrong.
    """
    body = pointer(day="2026-09-02", puzzle_id="abc123", generation="deadbeef", offset_hours=-8)
    assert set(body) == {"date", "generation", "next_rotation", "puzzle_id", "schema"}
    assert body["schema"] == POINTER_SCHEMA
    assert body["next_rotation"] == "2026-09-03T08:00:00Z"


def test_the_boundary_is_the_next_day_at_minus_the_offset() -> None:
    """⚠️⚠️ **The arithmetic the browser is forbidden to do, checked here where the constant lives.**

    A date is current until the *following* date's boundary, and that lands at `-offset` hours UTC. Off
    by a day and every countdown is 24 hours out; off by a sign and it lands at 16:00 UTC, in the middle
    of the afternoon on the coast the offset was chosen for.
    """
    assert next_rotation("2026-09-02", -8) == "2026-09-03T08:00:00Z"
    assert next_rotation("2026-12-31", -8) == "2027-01-01T08:00:00Z"
    assert next_rotation("2026-02-28", -8) == "2026-03-01T08:00:00Z"
    # A leap year, because February is where a hand-rolled day-add goes wrong.
    assert next_rotation("2028-02-28", -8) == "2028-02-29T08:00:00Z"
    assert next_rotation("2026-09-02", 0) == "2026-09-03T00:00:00Z"
