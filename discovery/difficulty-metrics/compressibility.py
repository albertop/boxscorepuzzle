"""How far a single boxscore can be compressed — the ceiling for this direction, not an average.

Section 31 measured what random erasure does across many boards, which compares boards to each
other under the same treatment. This asks a different question: given *this* boxscore, what is the
most that can be taken away while it stays uniquely solvable without backtracking. That is what
orders one candidate direction against another, and it is section 5's quality metric.

The two must not be conflated. A direction that survives a lot of random erasure is not necessarily
one that can be compressed far, and it is compressibility that decides whether a boxscore is worth
publishing at all.

Search strategy, stated rather than assumed
-------------------------------------------
Finding the true maximum is a combinatorial search nobody can afford across a pool. What runs here
is **randomised greedy with restarts**: from the full board, repeatedly pick a still-given cell at
random, erase it, and keep it erased if the board still solves completely; stop when no remaining
cell can be removed. That yields a *maximal* set — one that cannot be extended — not a *maximum*
one. Restarts explore different orders and the best is kept.

So every number here is a **lower bound** on true compressibility. Chosen because it is the cheapest
search that gives a defensible floor, and because a floor is what a quality filter needs: a direction
that clears the bar on a lower bound clears it.

Read-only against DGL. Run from `forge/`.
"""

import random
import statistics
import time
from collections import Counter

from measure import Loaded, erasable_cells, load  # noqa: F401

from boxscore_forge.constraints import cell_values, shape_of
from boxscore_forge.errors import ContradictionError
from boxscore_forge.identities import find_violations
from boxscore_forge.solver import solve

PER_DECADE = 10
RESTARTS = 5
SEED = 20260818


def ceiling(loaded: Loaded, rng: random.Random) -> tuple[int, int, float, float, float]:
    """Best maximal erasure found: cells, raw chain, weighted chain, trivial share, seconds."""
    started = time.perf_counter()
    shape = shape_of(loaded.direction)
    values = cell_values(loaded.direction)
    candidates = erasable_cells(loaded.direction)
    best_cells, best_chain, best_weighted, best_trivial = 0, 0, 0.0, 0.0

    for _ in range(RESTARTS):
        order = candidates[:]
        rng.shuffle(order)
        erased: set[str] = set()
        chain, weighted, trivial = 0, 0.0, 0.0
        for cell in order:
            trial = erased | {cell}
            puzzle = {k: v for k, v in values.items() if k not in trial}
            try:
                solution = solve(shape, puzzle)
            except ContradictionError:
                continue
            if solution.is_complete:
                erased = trial
                chain = solution.chain_length
                weighted = solution.weighted_chain_length
                trivial = solution.trivial_share or 0.0
        if len(erased) > best_cells:
            best_cells, best_chain, best_weighted, best_trivial = len(erased), chain, weighted, trivial

    return best_cells, best_chain, best_weighted, best_trivial, time.perf_counter() - started


def at_fixed_erasure(loaded: Loaded, counts: tuple[int, ...], rng: random.Random) -> dict[int, float | None]:
    """Weighted chain at the *same* cell count on every board.

    Comparing boards at their own ceilings confounds difficulty with volume: a board that compresses
    further has more steps and so a longer weighted chain whatever each step costs. Holding the cell
    count fixed removes that, at the price of only working where random erasure still solves.

    Returns None where no random erasure of that size solved, which is a fact about the board and
    must not be reported as a zero.
    """
    shape = shape_of(loaded.direction)
    values = cell_values(loaded.direction)
    candidates = erasable_cells(loaded.direction)
    result: dict[int, float | None] = {}
    for count in counts:
        scores = []
        for _ in range(12):
            erased = rng.sample(candidates, min(count, len(candidates)))
            try:
                solution = solve(shape, {k: v for k, v in values.items() if k not in erased})
            except ContradictionError:
                continue
            if solution.is_complete:
                scores.append(solution.weighted_chain_length)
        result[count] = statistics.median(scores) if scores else None
    return result


def proxies(loaded: Loaded) -> dict[str, float]:
    """The cheap screens section 5 assumes can stand in for compressibility, never yet validated."""
    values = cell_values(loaded.direction)
    grid = [values[cell] for cell in erasable_cells(loaded.direction)]
    innings = loaded.direction.line_score.offense_by_inning
    return {
        "zero_density": sum(1 for value in grid if value == 0) / len(grid),
        "digit_range": sum(1 for value in grid if value > 3) / len(grid),
        "line_score_variety": len({runs for runs in innings}) / max(len(innings), 1),
        "scoring_innings": sum(1 for runs in innings if runs) / max(len(innings), 1),
    }


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or statistics.pstdev(xs) == 0 or statistics.pstdev(ys) == 0:
        return float("nan")
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / len(xs)
    return covariance / (statistics.pstdev(xs) * statistics.pstdev(ys))


def main() -> None:
    rng = random.Random(SEED)
    sample = [item for item in load(PER_DECADE) if not find_violations(item.direction)]
    print(f"{len(sample)} directions, {RESTARTS} restarts each, greedy maximal search")
    print(f"decades: {dict(sorted(Counter((i.season // 10) * 10 for i in sample).items()))}\n")

    rows = []
    for index, loaded in enumerate(sample, start=1):
        cells, chain, weighted, trivial, seconds = ceiling(loaded, rng)
        below = at_fixed_erasure(loaded, (6, 10), rng)
        rows.append((loaded, cells, chain, seconds, proxies(loaded), weighted, trivial, below))
        print(
            f"  [{index:>3}/{len(sample)}] {loaded.game_id} {loaded.season}: "
            f"{cells}/{len(erasable_cells(loaded.direction))} cells, chain {chain}, "
            f"weighted {weighted:.1f}, trivial {trivial:.0%}, {seconds:.1f}s",
            flush=True,
        )

    erasable = [len(erasable_cells(loaded.direction)) for loaded, *_ in rows]
    shares = [100.0 * cells / total for (_, cells, *_), total in zip(rows, erasable, strict=True)]
    chains = [row[2] for row in rows]
    seconds = [row[3] for row in rows]

    print("=== HOW FAR A BOXSCORE COMPRESSES (share of the grid removable) ===")
    ordered = sorted(shares)
    for label, value in (
        ("min", ordered[0]),
        ("p10", ordered[len(ordered) // 10]),
        ("p50", statistics.median(ordered)),
        ("p90", ordered[9 * len(ordered) // 10]),
        ("max", ordered[-1]),
    ):
        print(f"  {label:>4}: {value:5.1f}%")
    print(f"  mean cells erased: {statistics.fmean([row[1] for row in rows]):.1f} of {statistics.fmean(erasable):.0f}")

    print("\n=== BY DECADE ===")
    by_decade: dict[int, list[float]] = {}
    for (loaded, cells, *_), total in zip(rows, erasable, strict=True):
        by_decade.setdefault((loaded.season // 10) * 10, []).append(100.0 * cells / total)
    for decade, values in sorted(by_decade.items()):
        print(f"  {decade}: median {statistics.median(values):5.1f}%   n={len(values)}")

    print("\n=== CHAIN LENGTH ACHIEVED AT THE CEILING ===")
    histogram = Counter(chains)
    for length, count in sorted(histogram.items()):
        print(f"  chain {length:>2}: {count:>3} directions ({100.0 * count / len(chains):.0f}%)")
    print(f"  correlation, compressibility vs chain at the ceiling: r = {_pearson(shares, [float(c) for c in chains]):+.3f}")

    print("\n=== DO THE CHEAP SCREENS PREDICT IT ===")
    for name in ("zero_density", "digit_range", "line_score_variety", "scoring_innings"):
        column = [row[4][name] for row in rows]
        print(f"  {name:<19} r = {_pearson(shares, column):+.3f}")

    weighted = [row[5] for row in rows]
    trivial = [row[6] for row in rows]

    print("\n=== WEIGHTED CHAIN LENGTH AT THE CEILING ===")
    ordered_weighted = sorted(weighted)
    for label, value in (
        ("min", ordered_weighted[0]),
        ("p10", ordered_weighted[len(ordered_weighted) // 10]),
        ("p50", statistics.median(ordered_weighted)),
        ("p90", ordered_weighted[9 * len(ordered_weighted) // 10]),
        ("max", ordered_weighted[-1]),
    ):
        print(f"  {label:>4}: {value:7.1f}")
    print(f"  share of steps that were trivial: median {statistics.median(trivial):.0%}")

    # Volume-controlled: cost per cell removed, and the same cell count on every board.
    intensity = [row[5] / max(row[1], 1) for row in rows]
    print(f"  cost per cell removed: median {statistics.median(intensity):.2f}")
    for count in (6, 10):
        column = [row[7][count] for row in rows if row[7][count] is not None]
        print(f"  at {count:>2} cells on every board: median {statistics.median(column):6.1f} (n={len(column)})")

    print("\n=== DOES THE WEIGHTING ADD ANYTHING ===")
    print(f"  weighted vs raw chain length     r = {_pearson(weighted, [float(c) for c in chains]):+.3f}")
    print(f"  weighted vs compressibility      r = {_pearson(weighted, shares):+.3f}")
    print("  (a very high correlation with raw chain means the weighting changed nothing)")

    print("\n=== THE TEST THAT MATTERS: DOES IT STILL REWARD BOREDOM ===")
    print("  three readings of weighted chain: at each board's ceiling, per cell removed, and at a")
    print("  fixed ten cells on every board. Only the last two hold volume constant.")
    at_ten = [(row[4], row[7][10]) for row in rows if row[7][10] is not None]
    for name in ("zero_density", "digit_range", "line_score_variety", "scoring_innings"):
        column = [row[4][name] for row in rows]
        print(
            f"  {name:<19} compressibility {_pearson(shares, column):+.3f}   "
            f"ceiling {_pearson(weighted, column):+.3f}   "
            f"per-cell {_pearson(intensity, column):+.3f}   "
            f"at-10 {_pearson([p[name] for p, _ in at_ten], [w for _, w in at_ten]):+.3f}"
        )

    print("\n=== DOES IT SEPARATE BOARDS RAW CHAIN CALLS EQUAL ===")
    grouped: dict[int, list[float]] = {}
    for row in rows:
        grouped.setdefault(row[2], []).append(row[5])
    for chain_length, values in sorted(grouped.items()):
        if len(values) < 3:
            continue
        spread = max(values) - min(values)
        print(
            f"  raw chain {chain_length:>2} ({len(values):>2} boards): weighted "
            f"{min(values):6.1f} to {max(values):6.1f}, spread {spread:5.1f}, median {statistics.median(values):6.1f}"
        )

    print("\n=== SEARCH COST ===")
    print(f"  per direction: mean {statistics.fmean(seconds):.2f}s, max {max(seconds):.2f}s")
    print(f"  extrapolated over 55,024 directions: {statistics.fmean(seconds) * 55024 / 3600:.1f} hours")
    print("  weighted chain is computed from the same walk, so it adds no search cost of its own")


if __name__ == "__main__":
    main()
