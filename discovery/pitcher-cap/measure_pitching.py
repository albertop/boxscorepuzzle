"""Does the puzzle get worse as the pitching section grows?

The ≤2 pitcher cap was defended on screen cost, and that argument is retired: the working-set
measurement showed scrolling does not bind, which is what let the batter cap go from 10 to 13. It was
never applied to pitchers. Under §5's new 5% pre-1950 calendar quota the cap is expensive — ≤2 leaves
5.3 years of calendar against 18.6 at ≤4 — so the question is whether raising it costs puzzle.

The hypothesis to test, stated by the operator as a guess rather than a finding: **a pitching line
crosses the offense only through totals, so three or four pitching rows give nearly the same
constraints as two, and the board gets longer without getting better.** If that is right it shows up
as falling constraint density per row, more trivial steps, and fewer steps that touch the pitching
section at all.

Boards are sampled at an *exact* pitcher count rather than under a cap, because under a cap the
five-pitcher boards would be a handful of outliers inside a sample of two-pitcher ones.

**The confound, named up front: pitcher count and era are the same variable.** A two-pitcher game is
usually old and a five-pitcher game is usually modern, so any difference between them is partly a
difference between 1925 and 2005. Every table below is repeated on a 1970-2009 window where all four
counts genuinely coexist.

Read-only against DGL. Run from `forge/` so the package is importable.
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

from boxscore_forge.constraints import (  # noqa: E402
    cell_values,
    equations,
    independent_cycles,
    shape_of,
)
from boxscore_forge.erasure import ORDERINGS, erasable  # noqa: E402
from boxscore_forge.identities import Family, find_violations  # noqa: E402
from boxscore_forge.solver import Solution, solve  # noqa: E402

PITCHER_COUNTS = (2, 3, 4, 5)
TARGETS = (5, 8, 11, 14)
SEEDS = (1, 2)
SAMPLE_PER_DECADE = 5
ORDERING = "row_first"
ERA_WINDOW = (1970, 2009)


@dataclass(frozen=True)
class Snapshot:
    erased: int
    chain: int
    search: float | None
    resolution: int | None
    trivial: float | None
    pitching_share: float
    families: tuple[str, ...]


def _pitching_share(solution: Solution) -> float:
    """How much of the solution path actually goes through the pitching section."""
    if not solution.deductions:
        return 0.0
    touched = sum(1 for step in solution.deductions if step.cell.startswith(("pitching[", "pitching_totals")))
    return touched / len(solution.deductions)


def trajectory(loaded: Loaded, seed: int) -> list[Snapshot]:
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
                erased=len(erased),
                chain=solution.chain_length,
                search=solution.ninetieth_percentile_search,
                resolution=solution.ninetieth_percentile_resolution,
                trivial=solution.trivial_share,
                pitching_share=_pitching_share(solution),
                families=tuple(sorted(family.value for family in solution.families_used)),
            )
        )
    return snapshots


def first_reaching(snapshots: list[Snapshot], target: int) -> Snapshot | None:
    return next((snapshot for snapshot in snapshots if snapshot.chain >= target), None)


def structure(sample: dict[int, list[Loaded]]) -> None:
    """Constraints per row, before any erasure. The hypothesis is structural, so test it structurally.

    If a pitching row participated as richly as a batting row, equations per row would hold steady as
    pitchers are added. If pitching rows are nearly free riders, it falls.
    """
    print("\n=== CONSTRAINT DENSITY, STRUCTURAL ===")
    print(f"{'pitchers':>9}{'boards':>8}{'rows':>7}{'equations':>11}{'per row':>9}{'cycles':>8}{'cycles/row':>12}")
    for count in PITCHER_COUNTS:
        rows_seen: list[int] = []
        per_row: list[float] = []
        cycles_per_row: list[float] = []
        cycle_counts: list[int] = []
        equation_counts: list[int] = []
        for loaded in sample[count]:
            shape = shape_of(loaded.direction)
            rows = shape.batter_count + shape.pitcher_count
            system = equations(shape)
            cycles = independent_cycles(shape)
            rows_seen.append(rows)
            equation_counts.append(len(system))
            per_row.append(len(system) / rows)
            cycle_counts.append(cycles)
            cycles_per_row.append(cycles / rows)
        if not rows_seen:
            continue
        print(
            f"{count:>9}{len(rows_seen):>8}{statistics.fmean(rows_seen):>7.1f}"
            f"{statistics.fmean(equation_counts):>11.1f}{statistics.fmean(per_row):>9.2f}"
            f"{statistics.fmean(cycle_counts):>8.1f}{statistics.fmean(cycles_per_row):>12.2f}"
        )


def quality(sample: dict[int, list[Loaded]], runs: dict[int, list[list[Snapshot]]], label: str) -> None:
    print(f"\n=== SOLUTION QUALITY BY PITCHER COUNT — {label} ===")
    print(f"{'pitchers':>9}{'runs':>6}{'ceiling p50':>13}{'target':>8}{'reached':>9}"
          f"{'erased':>8}{'search':>8}{'res':>6}{'trivial':>9}{'pitching steps':>16}")
    for count in PITCHER_COUNTS:
        trajectories = runs[count]
        if not trajectories:
            continue
        ceiling = _median([run[-1].chain for run in trajectories if run])
        for target in TARGETS:
            hits = [first_reaching(run, target) for run in trajectories]
            found = [hit for hit in hits if hit is not None]
            if not found:
                print(f"{count:>9}{len(trajectories):>6}{ceiling:>13.0f}{target:>8}{0.0:>8.0f}%")
                continue
            searches = [hit.search for hit in found if hit.search is not None]
            resolutions = [hit.resolution for hit in found if hit.resolution is not None]
            trivials = [hit.trivial for hit in found if hit.trivial is not None]
            print(
                f"{count:>9}{len(trajectories):>6}{ceiling:>13.0f}{target:>8}"
                f"{100.0 * len(found) / len(hits):>8.0f}%"
                f"{_median([hit.erased for hit in found]):>8.0f}"
                f"{(_median(searches) if searches else float('nan')):>8.2f}"
                f"{(_median(resolutions) if resolutions else float('nan')):>6.0f}"
                f"{(_median(trivials) if trivials else float('nan')):>9.2f}"
                f"{statistics.fmean([hit.pitching_share for hit in found]):>15.1%}"
            )
        print()
    print(f"  sample sizes: {({count: len(sample[count]) for count in PITCHER_COUNTS})}")


def families(runs: dict[int, list[list[Snapshot]]], label: str) -> None:
    """Does the cross-team family get exercised more or less as the pitching section grows?

    Cross-team is the family that ties the two halves of the board together, so if extra pitching
    rows were dead weight this is where it would show.
    """
    print(f"\n=== FAMILIES REQUIRED AT A CHAIN TARGET OF 11 — {label} ===")
    # Read off the enum, never off hand-written strings. The first version of this table looked up
    # "global" against a family whose value is "global_identity" and reported it as never used.
    names = [family.value for family in Family]
    header = "".join(f"{name:>16}" for name in names)
    print(f"{'pitchers':>9}{'boards':>8}{'all four':>10}{header}")
    for count in PITCHER_COUNTS:
        found = [hit for run in runs[count] if (hit := first_reaching(run, 11))]
        if not found:
            continue
        counter: Counter[str] = Counter()
        for hit in found:
            for family in hit.families:
                counter[family] += 1
        total = len(found)
        all_four = sum(1 for hit in found if len(hit.families) == len(names))
        shares = "".join(f"{100.0 * counter[name] / total:>15.0f}%" for name in names)
        print(f"{count:>9}{total:>8}{100.0 * all_four / total:>9.0f}%{shares}")


def _median[T: (int, float)](values: list[T]) -> float:
    return float(statistics.median(values)) if values else float("nan")


def main() -> None:
    sample: dict[int, list[Loaded]] = {}
    for count in PITCHER_COUNTS:
        loaded = load(SAMPLE_PER_DECADE, gated=True, min_pitchers=count, max_pitchers=count)
        sample[count] = [item for item in loaded if not find_violations(item.direction)]
        decades = Counter((item.season // 10) * 10 for item in sample[count])
        print(f"{count} pitchers: {len(sample[count])} directions, decades {dict(sorted(decades.items()))}")

    structure(sample)

    runs = {
        count: [trajectory(loaded, seed) for loaded in sample[count] for seed in SEEDS] for count in PITCHER_COUNTS
    }
    quality(sample, runs, "all eras")
    families(runs, "all eras")

    # The same thing with era held roughly still, because pitcher count and era are the same
    # variable in this data and a difference between them would otherwise be unattributable.
    windowed_sample = {
        count: [item for item in sample[count] if ERA_WINDOW[0] <= item.season <= ERA_WINDOW[1]]
        for count in PITCHER_COUNTS
    }
    windowed_runs = {
        count: [trajectory(loaded, seed) for loaded in windowed_sample[count] for seed in SEEDS]
        for count in PITCHER_COUNTS
    }
    quality(windowed_sample, windowed_runs, f"{ERA_WINDOW[0]}-{ERA_WINDOW[1]} only")
    families(windowed_runs, f"{ERA_WINDOW[0]}-{ERA_WINDOW[1]} only")


if __name__ == "__main__":
    main()
