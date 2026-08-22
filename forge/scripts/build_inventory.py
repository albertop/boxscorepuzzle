"""Fill the calendar: produce validated puzzles at volume and assign them to dates.

**`docs/beta-0-plan.md` group A, and `docs/calendar.md` is the artefact.** This is the one command the
runbook (A5) will document, and the one that gets re-run whenever the curve or the caps change.

    uv run python scripts/build_inventory.py --measure --directions 60

⚠️⚠️ **Measuring is all it does today, and the assignment half is deliberately absent rather than
stubbed.** A `build()` taking a date range and ignoring it would look like the producer and not be one —
the shape `CLAUDE.md` names as *an incomplete gate looks like a gate and is not one*. The yield decides
how the batch is sized and how long it runs, so it is measured first and the assignment is written
against a number.

⚠️⚠️ **The yield is unknown and everything downstream is sized from it.**
§5's gate keeps roughly 11% of the pool before any of this runs; on top of that the erasure can fail to
reach a target and the publication gate can refuse what it produced. **Nobody has ever run this at
volume**, so the number of directions a five-month calendar costs is not known, and a batch sized from
a guess either stops halfway or spends hours it did not need. Measure, then build.

⚠️ **Every refusal is counted by cause.** A pool that cannot be erased and a board the gate rejects are
different problems with different fixes, and a producer that reports one number cannot tell them apart —
which is why `produce()` returns its cause rather than printing it.

⚠️ **What the assignment half will have to do, stated here so it is not rediscovered:** read
`forge/calendar.json` before it starts, write only dates with no entry (§21's idempotence and its
extends-never-rewrites are the same mechanism), and refuse any game the calendar has already spent (§7)
— the check no package can perform on itself. `boxscore_forge.calendar` already implements all three;
what is missing is the producer that feeds it, and it is missing rather than pretended.
"""

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from boxscore_domain import ZERO_DENSITY_GATE  # noqa: E402
from boxscore_forge.pool import Loaded, load  # noqa: E402
from boxscore_forge.produce import produce  # noqa: E402
from boxscore_package.format import Package  # noqa: E402

NOTE = "daily inventory"

CEILING = 12
"""The hardest stall target to ask a board for, counting down. **Ask the board rather than tell it** —
only about 20% of boards reach 12, so a producer that demanded it would discard four in five."""

FLOOR = 1
"""The easiest target worth producing. A board that reaches nothing from the ceiling down to here has
nothing to offer and is discarded silently (§22): with a pool this size, throwing away 30% costs
nothing."""


def _hardest_target(loaded: Loaded, key: Ed25519PrivateKey, counts: Counter[str]) -> Package | None:
    """The hardest target this board reaches, or nothing — counting the cause of every refusal.

    ⚠️ **Counted per cause, not per board.** One board can fail the erasure at twelve stalls and pass
    the gate at nine; a tally that only recorded the board's final outcome would report the pool as
    healthier than it is and would hide which check is doing the discarding.
    """
    for target in range(CEILING, FLOOR - 1, -1):
        attempt = produce(loaded, target, key, note=NOTE)
        counts[attempt.cause or "published"] += 1
        if attempt.package is not None:
            return attempt.package
    return None


def _say(message: str) -> None:
    """Print and flush.

    ⚠️⚠️ **A long run that says nothing is indistinguishable from a hung one.** Python buffers stdout
    when it is not a terminal, so the first version of this printed *nothing at all* for minutes while
    it worked — and the operator watching it had no way to tell it from a stalled connection. The
    runbook (`docs/beta-0-plan.md` A5.2) requires every step to say what it prints when it is working;
    a step whose success looks like silence is a step nobody can tell failed.
    """
    print(message, flush=True)


def measure(directions: int, key: Ed25519PrivateKey) -> None:
    """How many directions a board costs, and which check spends them.

    ⚠️ **This is a measurement and it prints a number that decides a spend**, so it says where the
    number came from: the sample size, the gate, and the caps in force. A figure without its
    provenance is the shape this project has had to correct twice.
    """
    _say(f"loading {directions} directions, gate {ZERO_DENSITY_GATE}")
    started = time.monotonic()
    sample = load(directions, gated=True, gate=ZERO_DENSITY_GATE)
    loaded_in = time.monotonic() - started
    _say(f"  {len(sample)} directions in {loaded_in:.1f}s ({loaded_in / max(len(sample), 1):.2f}s each)")

    counts: Counter[str] = Counter()
    produced = 0
    started = time.monotonic()
    for item in sample:
        if _hardest_target(item, key, counts) is not None:
            produced += 1
    building = time.monotonic() - started

    _say("")
    _say(f"produced {produced} of {len(sample)} directions ({produced / max(len(sample), 1):.0%})")
    _say(f"  {building:.1f}s building, {building / max(len(sample), 1):.2f}s per direction")
    _say(f"  attempts by outcome: {dict(counts)}")
    if produced:
        each = (loaded_in + building) / produced
        _say(f"  ~{each:.1f}s per published board; 150 boards ~= {each * 150 / 60:.0f} min")
    else:
        _say("  WARNING: nothing was produced, so nothing here sizes a batch")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measure", action="store_true", required=True, help="report the yield")
    parser.add_argument("--directions", type=int, default=60, help="how many directions to sample")
    args = parser.parse_args()

    # ⚠️ **A throwaway key while measuring.** The gate verifies against the key's own public half, so any
    # pair satisfies it — and the real signing key has no business on the path of a measurement (§33).
    # Building for publication will be a different command with a different key.
    measure(args.directions, Ed25519PrivateKey.generate())


if __name__ == "__main__":
    main()
