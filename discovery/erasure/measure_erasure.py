"""What the erasure algorithm actually produces, before any of it is treated as decided.

Four orderings exist in `erasure.py` because three of them are guesses. This measures them against
the three metrics that describe a solution path — chain length, search cost and resolution p90 —
over real directions loaded from DGL, and answers the open questions with data:

  ordering    does round-robin across columns, across rows, or mirrored pairing beat random
  symmetry    does the mirrored ordering produce symmetric boards, and does symmetry cost anything
  targeting   does aiming at chain alone leave search cost and resolution free to vary, or are they
              already determined by chain, in which case targeting them adds a knob that does nothing
  cost        how many directions a level consumes, per ordering

One pass per (direction, ordering, seed) rather than one per target. `erase` is prefix-greedy and
deterministic, so a single run that snapshots every accepted state contains the answer for every
target at once; `check_equivalence` proves that against the real function rather than assuming it.

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

from boxscore_forge.boxscore import Direction  # noqa: E402
from boxscore_forge.constraints import cell_values, shape_of  # noqa: E402
from boxscore_forge.erasure import ORDERINGS, erase, erasable  # noqa: E402
from boxscore_forge.identities import find_violations  # noqa: E402
from boxscore_forge.solver import solve  # noqa: E402

TARGETS = (5, 8, 11, 14, 17, 20)
SEEDS = (1, 2, 3)
SEED = 20260817
SAMPLE_PER_DECADE = 6


@dataclass(frozen=True)
class Snapshot:
    """One accepted erasure state: what came out, and what the path looked like afterwards."""

    erased: frozenset[str]
    chain: int
    search: float | None
    resolution: int | None
    trivial: float | None
    families: int


def trajectory(direction: Direction, ordering: str, seed: int) -> list[Snapshot]:
    """Replay `erase` and keep every accepted state instead of only the one that hits the target.

    This duplicates the loop from `erasure.erase` on purpose — it is a measuring instrument, not a
    second implementation to be kept. `check_equivalence` is what keeps it honest.
    """
    shape = shape_of(direction)
    values = cell_values(direction)
    rng = random.Random(seed)  # noqa: S311
    candidates = ORDERINGS[ordering](erasable(direction), direction, rng)

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
                erased=frozenset(erased),
                chain=solution.chain_length,
                search=solution.ninetieth_percentile_search,
                resolution=solution.ninetieth_percentile_resolution,
                trivial=solution.trivial_share,
                families=len(solution.families_used),
            )
        )
    return snapshots


def first_reaching(snapshots: list[Snapshot], target: int) -> Snapshot | None:
    """What `erase(target_chain=target)` would have returned, or nothing if the board cannot."""
    return next((snapshot for snapshot in snapshots if snapshot.chain >= target), None)


def check_equivalence(sample: list[Loaded]) -> None:
    """The trajectory shortcut has to agree with the function it stands in for, or it measures air."""
    mismatches = 0
    for loaded in sample[:5]:
        for ordering in sorted(ORDERINGS):
            snapshots = trajectory(loaded.direction, ordering, 1)
            for target in TARGETS:
                expected = erase(loaded.direction, target_chain=target, seed=1, ordering=ordering)
                found = first_reaching(snapshots, target)
                if (expected is None) != (found is None):
                    mismatches += 1
                elif expected is not None and found is not None and expected.erased != found.erased:
                    mismatches += 1
    print(f"trajectory vs erase(): {mismatches} mismatches across 5 directions x 4 orderings x {len(TARGETS)} targets")


def by_ordering(sample: list[Loaded]) -> dict[str, list[list[Snapshot]]]:
    runs: dict[str, list[list[Snapshot]]] = {name: [] for name in sorted(ORDERINGS)}
    for loaded in sample:
        for ordering in sorted(ORDERINGS):
            for seed in SEEDS:
                runs[ordering].append(trajectory(loaded.direction, ordering, seed))
    return runs


def ordering_table(runs: dict[str, list[list[Snapshot]]]) -> None:
    print("\n=== EACH ORDERING AGAINST EACH TARGET ===")
    print("A run that never reaches the target is a discard, not a failure (§22).")
    print(
        f"{'ordering':<13}{'target':>7}{'reached':>9}{'erased p50':>12}{'chain p50':>11}"
        f"{'search p50':>12}{'resolution p50':>16}{'trivial p50':>13}"
    )
    for ordering in sorted(ORDERINGS):
        for target in TARGETS:
            hits = [first_reaching(run, target) for run in runs[ordering]]
            found = [hit for hit in hits if hit is not None]
            if not found:
                print(f"{ordering:<13}{target:>7}{0.0:>8.0f}%")
                continue
            searches = [hit.search for hit in found if hit.search is not None]
            resolutions = [hit.resolution for hit in found if hit.resolution is not None]
            print(
                f"{ordering:<13}{target:>7}{100.0 * len(found) / len(hits):>8.0f}%"
                f"{_median([len(hit.erased) for hit in found]):>12.0f}"
                f"{_median([hit.chain for hit in found]):>11.0f}"
                f"{(_median(searches) if searches else float('nan')):>12.2f}"
                f"{(_median(resolutions) if resolutions else float('nan')):>16.0f}"
                f"{_median([hit.trivial for hit in found if hit.trivial is not None]):>13.2f}"
            )
        print()


def ceiling_table(runs: dict[str, list[list[Snapshot]]]) -> None:
    """How far each ordering can push a board before it stops being derivable."""
    print("=== HOW FAR EACH ORDERING CAN GO ON THE SAME BOARDS ===")
    print(f"{'ordering':<13}{'max chain p50':>15}{'max chain p90':>15}{'cells erased p50':>18}")
    for ordering in sorted(ORDERINGS):
        finals = [run[-1] for run in runs[ordering] if run]
        print(
            f"{ordering:<13}{_median([f.chain for f in finals]):>15.0f}"
            f"{_percentile([f.chain for f in finals], 0.9):>15.0f}"
            f"{_median([len(f.erased) for f in finals]):>18.0f}"
        )


def symmetry_table(runs: dict[str, list[list[Snapshot]]], sample: list[Loaded]) -> None:
    """Whether mirrored erasure is actually symmetric, and whether the symmetry costs anything.

    Symmetry is measured as the share of erased batting cells whose mirror cell is also erased. The
    random ordering gives the baseline a coincidence produces, which is what any claim of symmetry
    has to beat.
    """
    print("\n=== IS THE MIRRORED ORDERING ACTUALLY SYMMETRIC ===")
    rows_by_run: list[int] = []
    for loaded in sample:
        rows_by_run += [len(loaded.direction.batting)] * len(SEEDS)
    print(f"{'ordering':<13}{'mirror-pair share at target 11':>32}")
    for ordering in sorted(ORDERINGS):
        shares: list[float] = []
        for run, rows in zip(runs[ordering], rows_by_run, strict=True):
            hit = first_reaching(run, 11)
            if hit is None:
                continue
            batting = [cell for cell in hit.erased if cell.startswith("batting[")]
            if not batting:
                continue
            paired = sum(1 for cell in batting if _mirror_of(cell, rows) in hit.erased)
            shares.append(paired / len(batting))
        print(f"{ordering:<13}{(statistics.fmean(shares) if shares else float('nan')):>31.1%}")


def _mirror_of(cell: str, rows: int) -> str:
    index = int(cell.split("[", 1)[1].split("]", 1)[0])
    return cell.replace(f"batting[{index}]", f"batting[{rows - 1 - index}]", 1)


def targeting(runs: dict[str, list[list[Snapshot]]]) -> None:
    """Whether search cost and resolution are free to vary once chain is fixed.

    If a fixed chain pins them, targeting all three is a knob wired to nothing and the algorithm
    should keep its single objective. If they spread, the second question is whether a stricter
    stopping condition can actually reach a joint target and what it costs the pool.
    """
    print("\n=== WITH CHAIN FIXED, HOW MUCH ROOM IS LEFT IN THE OTHER TWO ===")
    print(
        f"{'target':>7}{'n':>7}{'search p10-p90':>18}{'resolution p10-p90':>22}{'r(chain,search)':>18}"
        f"{'r(chain,res)':>15}"
    )
    for target in TARGETS:
        found = [hit for ordering in runs for run in runs[ordering] if (hit := first_reaching(run, target))]
        searches = [(hit.chain, hit.search) for hit in found if hit.search is not None]
        resolutions = [(hit.chain, float(hit.resolution)) for hit in found if hit.resolution is not None]
        if not searches or not resolutions:
            continue
        s_values = [value for _, value in searches]
        r_values = [value for _, value in resolutions]
        print(
            f"{target:>7}{len(found):>7}"
            f"{_percentile(s_values, 0.1):>10.2f}-{_percentile(s_values, 0.9):<7.2f}"
            f"{_percentile(r_values, 0.1):>14.0f}-{_percentile(r_values, 0.9):<7.0f}"
            f"{_pearson([float(c) for c, _ in searches], s_values):>18.3f}"
            f"{_pearson([float(c) for c, _ in resolutions], r_values):>15.3f}"
        )
    print("  (a wide band with r near zero means the second and third metrics are separate levers)")

    print("\n=== WHAT A JOINT TARGET WOULD COST ===")
    print("  chain >= 11 alone, versus chain >= 11 with search and resolution above their medians")
    all_runs = [run for ordering in runs for run in runs[ordering]]
    single = [hit for run in all_runs if (hit := first_reaching(run, 11))]
    searches = sorted(hit.search for hit in single if hit.search is not None)
    resolutions = sorted(hit.resolution for hit in single if hit.resolution is not None)
    if not searches or not resolutions:
        return
    search_floor = _median(searches)
    resolution_floor = _median(resolutions)
    joint = 0
    for run in all_runs:
        for snapshot in run:
            if (
                snapshot.chain >= 11
                and snapshot.search is not None
                and snapshot.search >= search_floor
                and snapshot.resolution is not None
                and snapshot.resolution >= resolution_floor
            ):
                joint += 1
                break
    print(f"  runs reaching chain 11                     : {len(single)}/{len(all_runs)}")
    print(
        f"  runs also reaching search >= {search_floor:.2f} and res >= {resolution_floor:.0f}: {joint}/{len(all_runs)}"
    )
    print(f"  pool cost multiplier of the joint target   : {len(single) / max(joint, 1):.2f}x")


def _median[T: (int, float)](values: list[T]) -> float:
    return float(statistics.median(values)) if values else float("nan")


def _percentile[T: (int, float)](values: list[T], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    return float(ordered[min(int(fraction * len(ordered)), len(ordered) - 1)])


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or statistics.pstdev(xs) == 0 or statistics.pstdev(ys) == 0:
        return float("nan")
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / len(xs)
    return covariance / (statistics.pstdev(xs) * statistics.pstdev(ys))


def main() -> None:
    # Gated on purpose. The gate keeps 11% of the pool, so an ungated sample is nine parts boards
    # that will never ship, and how they respond to erasure describes a product nobody will play.
    sample = load(SAMPLE_PER_DECADE, gated=True)
    balanced = [item for item in sample if not find_violations(item.direction)]
    print(f"loaded {len(sample)} directions, {len(balanced)} balance every identity")
    print(f"decades: {dict(sorted(Counter((item.season // 10) * 10 for item in balanced).items()))}")
    check_equivalence(balanced)
    runs = by_ordering(balanced)
    ordering_table(runs)
    ceiling_table(runs)
    symmetry_table(runs, balanced)
    targeting(runs)


if __name__ == "__main__":
    main()
