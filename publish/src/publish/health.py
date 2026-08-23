"""Whether the public path is in the state the access model requires.

⚠️⚠️ **The rotation is a moving part whose failure is silent, and this is what makes it loud**
(`docs/calendar.md`). Two different failures, and they need two different questions:

| failure | what it looks like | the question that catches it |
|---|---|---|
| the delete did not happen | today and yesterday are both correct | **how many packages are public** |
| the job did not run at all | exactly two packages, both stale | **which date does `today.json` name** |

**Neither question catches the other's failure**, which is why both are asked. A count alone passes a
job that has not run since Tuesday; a date alone passes a directory quietly accumulating a year.

⚠️ **This returns a verdict rather than serving it.** The endpoint that exposes it is F3, and the
`serve` side is not built — a function is what can exist and be tested today, and F wires it.
"""

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from publish.rotate import MANIFEST, TODAY, YESTERDAY

PUBLIC_LIMIT = 2
"""How many packages may be on the public path. **Today's and yesterday's** (`docs/calendar.md`).

⚠️ **Yesterday is a rollover boundary, not a second grace day**: somebody who starts at eleven at night
would otherwise lose their board at the rollover. **Two days is not an archive**, so it does not compete
with what §9 sells — and a third day is the archive leaking one day at a time."""


@dataclass(frozen=True, slots=True)
class Verdict:
    """Healthy, or a list of what is wrong. ⚠️ **Faults are named**, because *unhealthy* with no reason
    is a check somebody mutes within a week."""

    healthy: bool
    faults: tuple[str, ...]


def inspect(public: Path, today: date) -> Verdict:
    """Is the public path what the access model says it must be?

    ⚠️ `today` is an argument for the same reason it is in `rotate()`: a check that asks the machine what
    day it is can only be tested against the day the suite runs.
    """
    faults: list[str] = []

    if not public.is_dir():
        return Verdict(healthy=False, faults=(f"{public} is not a directory; nothing is being served",))

    packages = sorted(found.stem for found in public.glob("*.json") if found.name not in {MANIFEST, TODAY, YESTERDAY})
    if len(packages) > PUBLIC_LIMIT:
        # ⚠️ The names are reported, not just the count. *Three packages* sends the operator looking; a
        # third id tells them which run failed and when.
        faults.append(f"{len(packages)} packages are public and at most {PUBLIC_LIMIT} may be: {packages}")

    pointer = public / TODAY
    if not pointer.is_file():
        faults.append(f"{TODAY} is missing; nothing names the day's puzzle")
    else:
        named = _date_named_by(pointer)
        if named is None:
            faults.append(f"{TODAY} carries no readable date")
        elif named != today.isoformat():
            # The job that did not run. It leaves yesterday's board in place, which players notice
            # within hours -- and this notices it first.
            faults.append(f"{TODAY} names {named} and today is {today.isoformat()}; the rotation has not run")

    return Verdict(healthy=not faults, faults=tuple(faults))


def _date_named_by(pointer: Path) -> str | None:
    try:
        loaded = json.loads(pointer.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(loaded, dict):
        return None
    named = loaded.get("date")
    return named if isinstance(named, str) else None
