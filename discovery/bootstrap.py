"""How a discovery script finds the project, in one place.

Two rules from CLAUDE.md, both learned the hard way:

**Reproducible from the script alone.** No script may depend on the caller's working directory or an
ambient `PYTHONPATH`. A discovery result that cannot be re-run identically is not evidence, and half
of these scripts used to import `measure` only because they happened to be launched from `forge/`.

**Fail with an explanation, not an `IndexError`.** These are decision tools. When a gate, an era
window, or a data change empties a sample, the script must say which filters were applied and what it
needed — not crash on `pool[6]` three lines later.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
"""The repository root, computed from this file rather than from wherever python was started."""


def bootstrap() -> Path:
    """Put the forge package and the shared discovery helpers on the path. Idempotent."""
    for path in (ROOT / "forge" / "src", ROOT / "discovery" / "difficulty-metrics", ROOT / "discovery"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    return ROOT


def require(sample: list, minimum: int, what: str, filters: str) -> list:
    """Refuse to continue on a sample too small to mean anything, and say why.

    `what` names the thing being measured and `filters` names what was applied to get here, because
    "IndexError: list index out of range" tells the operator nothing about which gate emptied it.
    """
    if len(sample) < minimum:
        message = (
            f"{what} needs at least {minimum} directions and has {len(sample)}. "
            f"Filters applied: {filters}. Loosen one of them or widen the sample."
        )
        raise SystemExit(message)
    return sample
