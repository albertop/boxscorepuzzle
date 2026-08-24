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
import re
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
        named = _pointer(pointer)
        if named is None:
            faults.append(f"{TODAY} is not a readable pointer")
        else:
            when, puzzle_id = named
            if when != today.isoformat():
                # The job that did not run. It leaves yesterday's board in place, which players notice
                # within hours -- and this notices it first.
                faults.append(f"{TODAY} names {when} and today is {today.isoformat()}; the rotation has not run")
            # ⚠⚠ **The pointer is followed, and until v40-P1-01 it was not.** The date was read and the
            # `puzzle_id` beside it was ignored, so **an empty public directory was healthy** as long as
            # a current-dated pointer survived: the package ceiling is an *at most*, and zero satisfies
            # it. F3 exists precisely for `serve` being up with no inventory (`docs/data-layer.md`), and
            # that was the one state it could not see.
            #
            # ⚠️ **This is the shape the register keeps recording**: a check whose two halves were each
            # true -- at most two packages, the date is today -- and whose conjunction still admitted the
            # outage. Nothing was broken; the question was never asked.
            if puzzle_id is None:
                faults.append(f"{TODAY} names no puzzle")
            elif not (public / f"{puzzle_id}.json").is_file():
                faults.append(f"{TODAY} names {puzzle_id} and {puzzle_id}.json is not public; today's game is a 404")

    # ⚠️ **Yesterday is checked the same way and its absence is not a fault.** The calendar's first
    # day has no yesterday, and §9's two-day window is a ceiling rather than a quota -- but a pointer
    # that *exists* and names a file that does not is the same outage one day older.
    if (public / YESTERDAY).is_file():
        named = _pointer(public / YESTERDAY)
        if named is None:
            faults.append(f"{YESTERDAY} is not a readable pointer")
        elif named[1] is None or not (public / f"{named[1]}.json").is_file():
            faults.append(f"{YESTERDAY} names {named[1]} and no such package is public")

    faults.extend(_the_client_can_read_what_is_public(public, packages))

    return Verdict(healthy=not faults, faults=tuple(faults))


def _the_client_can_read_what_is_public(public: Path, packages: list[str]) -> list[str]:
    """⚠️⚠️ **Can the browser that is deployed beside these files actually parse them?**

    **This is the one deployment failure the other checks cannot see, and it is the seventeen-inning
    shape at deployment scale.** Every question above is about the *set* -- how many, which date, does
    the named file exist -- and all four pass on a directory of perfectly-formed packages the client
    refuses at its first boundary. A package schema is a contract between two trees that share no code
    and no deployment cycle (§33), so **each holds its own `READABLE` and nothing compared them**: the
    forge's is `boxscore_package.format.READABLE`, the client's is a literal in `engine/package.js`, and
    they are in different images that are pushed separately.

    On 2026-08-24 the two were 6 and 5. The site was fine -- both deployed halves were 5 -- and the
    repository had moved to 6 in both, so **the only way to be broken was to push one image and not the
    other**, in either order. Nothing asserted it. It held because the operator did it carefully, which
    is not a property of the system.

    ⚠️⚠️ **It is decidable here and nowhere else**, which is why it lives in the health verdict rather
    than in a test. A test in `forge` cannot see what is deployed and a test in `serve` cannot either;
    **the served root holds both halves at once**, and this runs against the served root.

    ⚠️ **A missing reader is a fault, not a skip.** `serve` not being there at all is a deployment that
    published packages into a directory nobody serves -- and *the absence of the evidence must not read
    as the evidence*.
    """
    reader = public.parents[1] / "engine" / "package.js" if len(public.parents) > 1 else None
    if reader is None or not reader.is_file():
        return [f"{reader} is not there; the packages are public and no client is deployed beside them"]

    readable = re.search(r"const READABLE = \[([\d,\s]*)\]", reader.read_text(encoding="utf-8"))
    if readable is None or not readable[1].strip():
        # ⚠️ The literal moved or was emptied. **Refused rather than assumed**: a check that cannot find
        # its subject reports on nothing, and `nginx -t` approving a config it was never given is the
        # register's own instance of believing that answer.
        return [f"{reader.name} declares no READABLE versions; this check cannot say what the client reads"]

    accepted = {int(one) for one in readable[1].split(",") if one.strip()}
    faults = []
    for name in packages:
        try:
            schema = json.loads((public / f"{name}.json").read_text(encoding="utf-8")).get("schema")
        except (OSError, ValueError):
            faults.append(f"{name}.json is public and is not readable JSON")
            continue
        if schema not in accepted:
            # The whole point, and the message names both sides: which way round the mismatch is decides
            # which image is behind, and that is the difference between a diagnosis and a bisect.
            faults.append(
                f"{name}.json is schema {schema} and the deployed client reads {sorted(accepted)}; "
                f"every board is a controlled rejection"
            )
    return faults


def _pointer(pointer: Path) -> tuple[str, str | None] | None:
    """The date and puzzle id a pointer names, or `None` if it cannot be read at all.

    ⚠️ **One parse, two facts.** These were two reads of the same file in two places, which is the
    same document being described twice -- and the second description was the one that never got
    written. An unreadable pointer and a pointer with no `puzzle_id` are different faults, so the
    missing id comes back as `None` inside a tuple rather than collapsing into the outer one.
    """
    try:
        loaded = json.loads(pointer.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(loaded, dict):
        return None
    when = loaded.get("date")
    if not isinstance(when, str):
        return None
    puzzle_id = loaded.get("puzzle_id")
    return when, puzzle_id if isinstance(puzzle_id, str) else None
