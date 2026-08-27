"""The rotation as a command. **This is what the daily job runs.**

    python -m publish --inventory <private> --public <served>

⚠️⚠️ **It existed only as a function until 2026-08-23, and a job that cannot be invoked is not a job.**
F3 schedules this; E1 uses it to build the development tree. Both need an entry point, and writing two —
a cron line here, a script there — is the two-places defect on the one step that enforces the access
model.

⚠️ **`--date` is for reproducing a day, not for choosing one.** Without it the rotation asks
`serving_date()`, which is the whole point: the day is decided server-side, by this, once. With it a
development tree can be built to a fixed date so a committed tree does not go stale in a way that reads
as a defect. **It is not a way to publish the future** — the inventory only holds pointers the forge
wrote, and `rotate` refuses a date with no pointer.
"""

import argparse
from datetime import date
from pathlib import Path

from publish.health import DEFAULT_CLIENT, inspect, readable_versions
from publish.rotate import RotationError, rotate, serving_date


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish today's and yesterday's puzzles, and remove the rest.")
    parser.add_argument("--inventory", required=True, type=Path, help="the private inventory of generations")
    parser.add_argument("--public", required=True, type=Path, help="the served root")
    parser.add_argument("--date", default="", help="the serving date, ISO; default is the one the clock gives")
    # ⚠️ v42-P2-01. This used to be derived from `--public`, which only worked in a checkout: in
    # production the volume is at `/srv/public` and the derived path was `/engine/package.js`.
    parser.add_argument(
        "--client",
        default=DEFAULT_CLIENT,
        help="the deployed engine/package.js, as a URL or a path; default is the site on the backend network",
    )
    arguments = parser.parse_args()

    when = date.fromisoformat(arguments.date) if arguments.date else serving_date()

    # ⚠️⚠️ **Asked before rotating, so the answer can still stop it.** v42-P2-02. `inspect()` below asks
    # the same question of the same client and reports; this one refuses. `None` — an unreachable client,
    # a literal that has moved — publishes and lets the verdict speak, which is what this did for both
    # cases before today.
    readable = readable_versions(arguments.client)
    try:
        rotation = rotate(arguments.inventory, arguments.public, when, readable)
    except RotationError as error:
        # ⚠️ A refusal is the message and a non-zero exit, never a traceback: this runs unattended and
        # the operator reads a log line. `docs/beta-0-plan.md` A5.2 requires every step to say what it
        # prints when it works, so a failure has to be legible in the same place.
        message = f"rotation refused: {error}"
        raise SystemExit(message) from error

    print(f"rotated {arguments.public} to {when.isoformat()}", flush=True)
    print(f"  published: {', '.join(rotation.published)}", flush=True)
    print(f"  public now: {', '.join(rotation.kept)}", flush=True)
    print(f"  retired: {', '.join(rotation.retired) or 'nothing'}", flush=True)

    # ⚠️⚠️ **The verdict is read here rather than left for monitoring.** The rotation writing files and
    # the public path being correct are different claims: a pointer naming a package that is not there
    # is a 404 on the only game the product has, and it is the state F3 exists for. Asking immediately
    # turns it into an exit code the job's own log carries, instead of a red dashboard nobody is
    # looking at yet.
    verdict = inspect(arguments.public, when, arguments.client)
    if not verdict.healthy:
        message = "rotation finished and the public path is not healthy: " + "; ".join(verdict.faults)
        raise SystemExit(message)
    print("  health: green", flush=True)


if __name__ == "__main__":  # pragma: no cover - the module's own entry, exercised by running it
    main()
