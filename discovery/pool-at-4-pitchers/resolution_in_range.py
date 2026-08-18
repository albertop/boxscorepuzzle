"""Is a resolution ceiling still solving a problem, now that the week tops out at 13?

The ceiling was proposed to stop long arithmetic — a step that combines eleven known numbers is
addition, not deduction. But those steps were seen on boards near the ceiling, and after §31's
rescaling those boards are not published: the week runs from chain 5 to chain 13.

So the question is no longer "what should the ceiling be" but "is there anything left to cap". If
resolution p90 rarely reaches 10 inside 5-13, the ceiling solves a problem that no longer exists and
dropping it avoids the decade skew it would have carried — an absolute ceiling of 7 discards 50-67%
of post-1970 boards against 0-17% of the 1950s, and a ceiling scaled by row count inverts that skew
instead of removing it.

Cheaper than the full re-measurement on purpose: the walk stops at chain 13 rather than continuing to
the compressibility ceiling, which is where most of the cost was.

Read-only against DGL. Run from `forge/`.
"""

import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))

import random  # noqa: E402

from measure import Loaded, load  # noqa: E402

from boxscore_forge.constraints import cell_values, shape_of  # noqa: E402
from boxscore_forge.erasure import ORDERINGS, erasable  # noqa: E402
from boxscore_forge.identities import find_violations  # noqa: E402
from boxscore_forge.solver import solve  # noqa: E402

TARGETS = (5, 7, 9, 11, 13)
PUBLISHABLE_TOP = 13
SEEDS = (1, 2, 3)
SAMPLE_PER_DECADE = 12
ORDERING = "row_first"


@dataclass(frozen=True)
class Snapshot:
    chain: int
    resolution: int | None
    rows: int
    decade: int


def trajectory(loaded: Loaded, seed: int) -> list[Snapshot]:
    """Walk only as far as the week goes. Everything above 13 is off the calendar now."""
    direction = loaded.direction
    shape = shape_of(direction)
    values = cell_values(direction)
    rng = random.Random(seed)  # noqa: S311
    candidates = ORDERINGS[ORDERING](erasable(direction), direction, rng)

    snapshots: list[Snapshot] = []
    erased: set[str] = set()
    for cell in candidates:
        trial = erased | {cell}
        given = {name: value for name, value in values.items() if name not in trial}
        solution = solve(shape, given)
        if not solution.is_complete:
            continue
        erased = trial
        snapshots.append(
            Snapshot(
                chain=solution.chain_length,
                resolution=solution.ninetieth_percentile_resolution,
                rows=len(direction.batting),
                decade=(loaded.season // 10) * 10,
            )
        )
        if solution.chain_length >= PUBLISHABLE_TOP:
            break
    return snapshots


def first_reaching(snapshots: list[Snapshot], target: int) -> Snapshot | None:
    return next((snapshot for snapshot in snapshots if snapshot.chain >= target), None)


def distribution(runs: list[list[Snapshot]]) -> None:
    print("\n=== RESOLUTION p90 INSIDE THE PUBLISHABLE RANGE ===")
    print(f"{'target':>7}{'n':>6}{'p10':>6}{'p50':>6}{'p90':>6}{'max':>6}"
          f"{'>= 9':>8}{'>= 10':>8}{'>= 11':>8}")
    for target in TARGETS:
        found = [
            hit.resolution for run in runs if (hit := first_reaching(run, target)) and hit.resolution is not None
        ]
        if not found:
            continue
        print(
            f"{target:>7}{len(found):>6}{_pc(found, 0.1):>6.0f}{_pc(found, 0.5):>6.0f}"
            f"{_pc(found, 0.9):>6.0f}{max(found):>6}"
            f"{100.0 * sum(1 for value in found if value >= 9) / len(found):>7.0f}%"
            f"{100.0 * sum(1 for value in found if value >= 10) / len(found):>7.0f}%"
            f"{100.0 * sum(1 for value in found if value >= 11) / len(found):>7.0f}%"
        )
    print("  If the tail is thin here, the ceiling has nothing left to cap.")


def by_rows_and_decade(runs: list[list[Snapshot]]) -> None:
    print("\n=== AT THE HARDEST PUBLISHED TARGET (13), WHO CARRIES THE TAIL ===")
    found = [hit for run in runs if (hit := first_reaching(run, PUBLISHABLE_TOP)) and hit.resolution is not None]
    if not found:
        return
    print(f"{'batting rows':>13}{'boards':>8}{'resolution p50':>16}{'p90':>6}{'>= 10':>8}")
    by_rows: dict[int, list[int]] = {}
    for hit in found:
        by_rows.setdefault(hit.rows, []).append(hit.resolution or 0)
    for rows in sorted(by_rows):
        values = by_rows[rows]
        print(
            f"{rows:>13}{len(values):>8}{statistics.median(values):>16.0f}{_pc(values, 0.9):>6.0f}"
            f"{100.0 * sum(1 for value in values if value >= 10) / len(values):>7.0f}%"
        )

    print(f"\n{'decade':>8}{'boards':>8}{'resolution p50':>16}{'>= 10':>8}")
    by_decade: dict[int, list[int]] = {}
    for hit in found:
        by_decade.setdefault(hit.decade, []).append(hit.resolution or 0)
    for decade in sorted(by_decade):
        values = by_decade[decade]
        print(
            f"{decade:>8}{len(values):>8}{statistics.median(values):>16.0f}"
            f"{100.0 * sum(1 for value in values if value >= 10) / len(values):>7.0f}%"
        )


def _pc(values: list[int], fraction: float) -> float:
    ordered = sorted(values)
    return float(ordered[min(int(fraction * len(ordered)), len(ordered) - 1)])


def main() -> None:
    loaded = load(SAMPLE_PER_DECADE, gated=True, max_batters=13, max_pitchers=4)
    sample = [item for item in loaded if not find_violations(item.direction)]
    print(f"{len(sample)} gated directions at ≤13 batters and ≤4 pitchers, walking only to chain {PUBLISHABLE_TOP}")
    print(f"decades: {dict(sorted(Counter((item.season // 10) * 10 for item in sample).items()))}")
    print(f"batting rows: {dict(sorted(Counter(len(item.direction.batting) for item in sample).items()))}")

    runs = [trajectory(item, seed) for item in sample for seed in SEEDS]
    distribution(runs)
    by_rows_and_decade(runs)


if __name__ == "__main__":
    main()
