"""Shared fixtures for the rotation and health suites.

⚠️⚠️ **These were helper functions in `test_rotation.py` and `test_health.py` imported them by module
path.** That works under `python -m pytest`, which puts the working directory on `sys.path`, and fails
under plain `pytest`, which does not — so every local run passed and **the pre-push hook, which runs
`uv run pytest`, refused the push with `ModuleNotFoundError: No module named 'tests'`.**

**The instrument and the gate were not the same command**, which is the finding rather than the import:
thirty-three passing tests were reported from an environment the gate does not use. Fixtures need no
import at all, so the shape cannot come back.
"""

import json
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

import pytest

FIRST = date(2026, 9, 1)
"""The first date every fixture builds from. A fixed date, never `today`: a suite that reads the clock
can only be run on the day it was written."""


PACKAGE_SCHEMA = 6
"""The package version these fixtures write. **A number, not `format.SCHEMA_VERSION`** -- §33 forbids
`publish` importing from `forge`, and the point of the check that reads it is that the two trees do not
share this value."""


def deploy_client(root: Path, *, readable: int = PACKAGE_SCHEMA) -> Path:
    """Put a `serve` tree beside the public path, and answer with the path packages are served from.

    ⚠️⚠️ **The layout is the subject of a check, so the fixture has to have the layout.** `health.inspect`
    asks whether the browser deployed beside the packages can parse them -- which is only decidable
    because the served root holds both. A fixture that put the public path anywhere convenient made that
    question unanswerable, and the first version of the check reported *no client is deployed* on nine
    healthy tests.
    """
    (root / "engine").mkdir(parents=True, exist_ok=True)
    reader = "const READABLE = [" + str(readable) + "];" + chr(10)
    (root / "engine" / "package.js").write_text(reader, encoding="utf-8")
    public = root / "data" / "puzzles"
    public.parent.mkdir(parents=True, exist_ok=True)
    return public


def build_inventory(root: Path, days: int, *, generation: str = "gen1", start: date = FIRST) -> Path:
    """A private inventory shaped exactly as `build_inventory.py` writes one: packages at the top of a
    generation directory, signed per-date pointers under `days/`."""
    inventory = root / "inventory"
    where = inventory / generation
    (where / "days").mkdir(parents=True, exist_ok=True)
    for offset in range(days):
        when = start + timedelta(days=offset)
        puzzle_id = f"p{when.isoformat().replace('-', '')}"
        # ⚠️ A `schema` on every package, because `health.inspect` compares it against what the client
        # deployed beside them says it reads. A fixture package without one is a document no client
        # could accept, and a check over it would be measuring the fixture.
        (where / f"{puzzle_id}.json").write_text(
            json.dumps({"puzzle_id": puzzle_id, "schema": PACKAGE_SCHEMA}), encoding="utf-8"
        )
        pointer = {
            "date": when.isoformat(),
            "generation": generation,
            "puzzle_id": puzzle_id,
            "schema": 1,
            "signature": "0" * 128,
        }
        (where / "days" / f"{when.isoformat()}.json").write_text(json.dumps(pointer), encoding="utf-8")
    return inventory


@pytest.fixture
def inventory() -> Callable[..., Path]:
    """Build a private inventory. Handed in rather than imported, so no test module depends on another."""
    return build_inventory
