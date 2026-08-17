"""The same four tables, measured where puzzles will actually be published.

Everything so far was measured at each board's compressibility ceiling, and that saturates by
construction: a board pushed to its limit has a maximally hard step somewhere, so every board scores
the same and nothing separates. No puzzle ever ships at its ceiling.

Here the boards are erased to a target chain length instead — which is what the generator will do —
and the metrics are read there. Because chain length is then fixed by construction, any spread left
inside a target group *is* separation, with no need to bucket afterwards.

Read-only against DGL. Run from `forge/`.
"""

import random
import statistics
from collections import Counter

from compressibility import chain_targeted, families_of, proxies
from measure import load

from boxscore_forge.identities import find_violations

TARGETS = (5, 10, 20)
SEED = 20260820


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or statistics.pstdev(xs) == 0 or statistics.pstdev(ys) == 0:
        return float("nan")
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / len(xs)
    return covariance / (statistics.pstdev(xs) * statistics.pstdev(ys))


def _spread(label: str, series: list[float]) -> str:
    ordered = sorted(series)
    return (
        f"  {label:<16} min {ordered[0]:5.2f}  p10 {ordered[len(ordered) // 10]:5.2f}  "
        f"p50 {statistics.median(ordered):5.2f}  p90 {ordered[9 * len(ordered) // 10]:5.2f}  "
        f"max {ordered[-1]:5.2f}   spread {ordered[-1] - ordered[0]:5.2f}"
    )


def main() -> None:
    rng = random.Random(SEED)
    sample = [item for item in load(10) if not find_violations(item.direction)]
    print(f"{len(sample)} directions, erased to a target chain rather than to the ceiling\n")

    for target in TARGETS:
        rows = []
        for loaded in sample:
            solution = chain_targeted(loaded, target, rng)
            if solution is None or solution.hardest_search is None:
                continue
            rows.append((loaded, solution, proxies(loaded)))
        if len(rows) < 10:
            print(f"=== CHAIN TARGET {target}: only {len(rows)} boards reached it, skipping ===\n")
            continue

        search = [row[1].hardest_search or 0.0 for row in rows]
        search_p90 = [row[1].ninetieth_percentile_search or 0.0 for row in rows]
        resolution = [float(row[1].hardest_resolution or 0) for row in rows]
        resolution_p90 = [float(row[1].ninetieth_percentile_resolution or 0) for row in rows]
        chains = [float(row[1].chain_length) for row in rows]
        zeros = [row[2]["zero_density"] for row in rows]

        print(f"=== CHAIN TARGET {target}  (n={len(rows)}, chain actually reached: "
              f"p50 {statistics.median(chains):.0f}, range {min(chains):.0f}-{max(chains):.0f}) ===")
        print(_spread("search max", search))
        print(_spread("search p90", search_p90))
        print(_spread("resolution max", resolution))
        print(_spread("resolution p90", resolution_p90))
        print("  the spread column is the separation: chain is fixed here, so anything left is real")
        print(f"\n  vs zero density   search {_pearson(search, zeros):+.3f}   "
              f"search p90 {_pearson(search_p90, zeros):+.3f}   "
              f"resolution p90 {_pearson(resolution_p90, zeros):+.3f}")
        print(f"  vs chain length   search {_pearson(search, chains):+.3f}   "
              f"resolution p90 {_pearson(resolution_p90, chains):+.3f}")
        print(f"  the two components against each other   r = {_pearson(search, resolution_p90):+.3f}")

        families: Counter[str] = Counter(families_of(row[1]) for row in rows)
        total = sum(families.values())
        print(f"  families: {', '.join(f'{k} {100.0 * v / total:.0f}%' for k, v in families.most_common(5))}\n")


if __name__ == "__main__":
    main()
