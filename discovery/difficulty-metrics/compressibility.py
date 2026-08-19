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

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bootstrap import bootstrap  # noqa: E402

bootstrap()

import random
import statistics
import time
from collections import Counter

from measure import Loaded, load  # noqa: F401

from boxscore_forge.constraints import cell_values, shape_of
from boxscore_forge.erasure import erasable
from boxscore_forge.errors import ContradictionError
from boxscore_forge.identities import find_violations
from boxscore_forge.solver import Solution, solve

PER_DECADE = 10
RESTARTS = 5
SEED = 20260818


def ceiling(loaded: Loaded, rng: random.Random) -> tuple[int, Solution | None, float]:
    """Best maximal erasure found, the solution it produced, and seconds spent."""
    started = time.perf_counter()
    shape = shape_of(loaded.direction)
    values = cell_values(loaded.direction)
    candidates = erasable(loaded.direction)
    best_cells, best_solution = 0, None

    for _ in range(RESTARTS):
        order = candidates[:]
        rng.shuffle(order)
        erased: set[str] = set()
        found = None
        for cell in order:
            trial = erased | {cell}
            puzzle = {k: v for k, v in values.items() if k not in trial}
            try:
                solution = solve(shape, puzzle)
            except ContradictionError:
                continue
            if solution.is_complete:
                erased, found = trial, solution
        if len(erased) > best_cells:
            best_cells, best_solution = len(erased), found

    return best_cells, best_solution, time.perf_counter() - started


def chain_targeted(loaded: Loaded, target: int, rng: random.Random) -> Solution | None:
    """Erase greedily until the solve is `target` steps deep — the planned difficulty control.

    Family variety was measured under random erasure at fixed cell counts. If the generator instead
    aims at a chain length, the variety it produces may be different, and the calendar's character
    axis depends on which is true.
    """
    shape = shape_of(loaded.direction)
    values = cell_values(loaded.direction)
    order = erasable(loaded.direction)
    rng.shuffle(order)

    erased: set[str] = set()
    best: Solution | None = None
    for cell in order:
        trial = erased | {cell}
        try:
            solution = solve(shape, {k: v for k, v in values.items() if k not in trial})
        except ContradictionError:
            continue
        if not solution.is_complete:
            continue
        erased, best = trial, solution
        if solution.chain_length >= target:
            break
    return best


def families_of(solution: Solution) -> str:
    short = {"column_sum": "col", "row_identity": "row", "cross_team": "cross", "global_identity": "global"}
    return "+".join(short[f.value] for f in sorted(solution.families_used, key=lambda f: f.value))


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
    candidates = erasable(loaded.direction)
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
    grid = [values[cell] for cell in erasable(loaded.direction)]
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
    targeted: dict[int, Counter[str]] = {5: Counter(), 10: Counter(), 20: Counter()}
    trivial_costs: list[float] = []
    real_costs: list[float] = []

    for index, loaded in enumerate(sample, start=1):
        cells, solution, seconds = ceiling(loaded, rng)
        if solution is None:
            continue
        for target, counter in targeted.items():
            aimed = chain_targeted(loaded, target, rng)
            if aimed is not None:
                counter[families_of(aimed)] += 1
        for step in solution.deductions:
            if step.search_cost is None:
                continue
            (trivial_costs if step.is_trivial else real_costs).append(step.search_cost)
        rows.append((loaded, cells, solution, seconds, proxies(loaded)))
        print(
            f"  [{index:>3}/{len(sample)}] {loaded.game_id} {loaded.season}: "
            f"{cells}/{len(erasable(loaded.direction))} cells, chain {solution.chain_length}, "
            f"search {solution.hardest_search or 0:.2f}, res {solution.hardest_resolution or 0}, "
            f"trivial {solution.trivial_share or 0:.0%}, "
            f"{families_of(solution)}, {seconds:.1f}s",
            flush=True,
        )

    erasable_counts = [len(erasable(loaded.direction)) for loaded, *_ in rows]
    shares = [100.0 * cells / total for (_, cells, *_), total in zip(rows, erasable_counts, strict=True)]
    chains = [row[2].chain_length for row in rows]
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
    print(
        f"  mean cells erased: {statistics.fmean([row[1] for row in rows]):.1f} of {statistics.fmean(erasable_counts):.0f}"
    )

    print("\n=== BY DECADE ===")
    by_decade: dict[int, list[float]] = {}
    for (loaded, cells, *_), total in zip(rows, erasable_counts, strict=True):
        by_decade.setdefault((loaded.season // 10) * 10, []).append(100.0 * cells / total)
    for decade, values in sorted(by_decade.items()):
        print(f"  {decade}: median {statistics.median(values):5.1f}%   n={len(values)}")

    print("\n=== CHAIN LENGTH ACHIEVED AT THE CEILING ===")
    ordered_chains = sorted(chains)
    print(
        f"  min {ordered_chains[0]}  p50 {statistics.median(ordered_chains):.0f}  "
        f"p90 {ordered_chains[9 * len(ordered_chains) // 10]}  max {ordered_chains[-1]}"
    )
    print(f"  compressibility vs chain at the ceiling: r = {_pearson(shares, [float(c) for c in chains]):+.3f}")

    search = [row[2].hardest_search or 0.0 for row in rows]
    resolution = [float(row[2].hardest_resolution or 0) for row in rows]
    search_p90 = [row[2].ninetieth_percentile_search or 0.0 for row in rows]
    resolution_p90 = [float(row[2].ninetieth_percentile_resolution or 0) for row in rows]
    trivial = [row[2].trivial_share or 0.0 for row in rows]

    print("\n=== ⚠️ IS THERE A CHARACTER AXIS AT ALL ===")
    print("  Which equation families a solution actually needed. If nearly every board needs the")
    print("  same combination, the calendar cannot vary character and section 31 loses a dimension.")
    at_ceiling: Counter[str] = Counter(families_of(row[2]) for row in rows)
    for label, counter in (("at the ceiling", at_ceiling), *((f"chain target {t}", c) for t, c in targeted.items())):
        total = sum(counter.values()) or 1
        shown = ", ".join(f"{k} {100.0 * v / total:.0f}%" for k, v in counter.most_common(5))
        print(f"  {label:<16} (n={total:>3}): {shown}")

    print("\n=== THE TWO COMPONENTS AT THE CEILING ===")
    for label, series in (
        ("search max", search),
        ("search p90", search_p90),
        ("resolution max", resolution),
        ("resolution p90", resolution_p90),
    ):
        ordered = sorted(series)
        print(
            f"  {label:<15} min {ordered[0]:5.2f}  p10 {ordered[len(ordered) // 10]:5.2f}  "
            f"p50 {statistics.median(ordered):5.2f}  p90 {ordered[9 * len(ordered) // 10]:5.2f}  "
            f"max {ordered[-1]:5.2f}"
        )
    print(f"  share of steps that were trivial: median {statistics.median(trivial):.0%}")
    print(f"\n  ARE THE TWO COMPONENTS INDEPENDENT OF EACH OTHER?  r = {_pearson(search, resolution):+.3f}")
    print("  (near zero means three numbers rather than two, which is the better outcome)")

    print("\n=== THE FALSIFICATION TEST: DOES EITHER STILL REWARD BOREDOM ===")
    print("  flat or negative against zero density means the component works")
    for name in ("zero_density", "digit_range", "line_score_variety", "scoring_innings"):
        column = [row[4][name] for row in rows]
        print(
            f"  {name:<19} compressibility {_pearson(shares, column):+.3f}   "
            f"search {_pearson(search, column):+.3f}   resolution {_pearson(resolution, column):+.3f}"
        )

    print("\n=== ARE THEY INDEPENDENT OF EFFORT ===")
    floats = [float(c) for c in chains]
    print(f"  search     vs raw chain length   r = {_pearson(search, floats):+.3f}")
    print(f"  resolution vs raw chain length   r = {_pearson(resolution, floats):+.3f}")
    print(f"  search     vs compressibility    r = {_pearson(search, shares):+.3f}")
    print(f"  resolution vs compressibility    r = {_pearson(resolution, shares):+.3f}")

    print("\n=== DOES EITHER SEPARATE BOARDS RAW CHAIN CALLS EQUAL ===")
    grouped: dict[int, list[tuple[float, float]]] = {}
    for row in rows:
        grouped.setdefault(row[2].chain_length, []).append(
            (row[2].hardest_search or 0.0, float(row[2].hardest_resolution or 0))
        )
    for chain_length, pairs in sorted(grouped.items()):
        if len(pairs) < 3:
            continue
        searches = [p[0] for p in pairs]
        resolutions = [p[1] for p in pairs]
        print(
            f"  chain {chain_length:>2} ({len(pairs):>2} boards): "
            f"search {min(searches):.2f}-{max(searches):.2f} (spread {max(searches) - min(searches):.2f})   "
            f"resolution {min(resolutions):.0f}-{max(resolutions):.0f} (spread {max(resolutions) - min(resolutions):.0f})"
        )

    print("\n=== SATURDAY'S LEVER: DOES BOARD CHARACTER SEPARATE THE SOLVE ===")
    print("  if the family axis is dead at high difficulty, the variation must come from the")
    print("  boxscore itself. These are properties of the direction, fixed before any erasure.")
    character = {
        "pitching_rows": [float(len(row[0].direction.pitching)) for row in rows],
        "batting_rows": [float(len(row[0].direction.batting)) for row in rows],
        "live_footnotes": [
            float(
                sum(
                    1
                    for f in row[0].direction.batter_footnotes
                    if f.hit_by_pitch or f.sacrifice_flies or f.sacrifice_hits or f.catcher_interference
                )
            )
            for row in rows
        ],
        "total_runs": [float(row[0].direction.batting_totals.runs) for row in rows],
        "zero_density": [row[4]["zero_density"] for row in rows],
    }
    for name, column in character.items():
        print(
            f"  {name:<16} search {_pearson(search, column):+.3f}   "
            f"resolution {_pearson(resolution, column):+.3f}   chain {_pearson(floats, column):+.3f}"
        )

    print("\n  by pitching rows, holding nothing else:")
    by_pitchers: dict[int, list[tuple[float, float, int]]] = {}
    for row in rows:
        by_pitchers.setdefault(len(row[0].direction.pitching), []).append(
            (row[2].hardest_search or 0.0, float(row[2].hardest_resolution or 0), row[2].chain_length)
        )
    for count, triples in sorted(by_pitchers.items()):
        print(
            f"    {count} pitcher(s), n={len(triples):>3}: search {statistics.median([t[0] for t in triples]):.2f}   "
            f"resolution {statistics.median([t[1] for t in triples]):.0f}   "
            f"chain {statistics.median([t[2] for t in triples]):.0f}"
        )

    print("\n=== IS THE TRIVIAL DISCOUNT THROWING AWAY SEARCH EFFORT ===")
    print("  a step can be trivial to resolve and still expensive to find")
    for label, costs in (("trivial steps", trivial_costs), ("real steps", real_costs)):
        if not costs:
            continue
        ordered = sorted(costs)
        print(
            f"  {label:<14} n={len(costs):>5}  mean {statistics.fmean(costs):5.1f}  "
            f"p50 {statistics.median(ordered):5.1f}  p90 {ordered[9 * len(ordered) // 10]:5.1f}  "
            f"max {ordered[-1]:5.1f}"
        )
    # ⚠️ **These thresholds used to be 5, 10 and 20 against a metric that runs 0 to 1.** Every answer
    # was 0.0% whatever the data said, so the section could neither support nor refute the claim it
    # exists to test. `search_cost` is a *share* of the scanned board that led nowhere — it was a raw
    # count in an earlier solver and the numbers outlived the change.
    #
    # Compared against the real steps' own distribution now, which is the only comparison that means
    # anything: a trivial step above the real steps' median took more looking for than half of the
    # work the discount keeps.
    if trivial_costs and real_costs:
        reference = sorted(real_costs)
        for name, mark in (("median", reference[len(reference) // 2]), ("p90", reference[9 * len(reference) // 10])):
            share = sum(1 for cost in trivial_costs if cost >= mark) / len(trivial_costs)
            print(f"  trivial steps at or above the real steps' {name} ({mark:.2f}): {share:.1%}")
        print("  search_cost is a share of the scanned board that led nowhere, so it lies in [0, 1].")

    print("\n=== SEARCH COST ===")
    print(f"  per direction: mean {statistics.fmean(seconds):.2f}s, max {max(seconds):.2f}s")
    print(f"  extrapolated over 55,024 directions: {statistics.fmean(seconds) * 55024 / 3600:.1f} hours")
    print("  weighted chain is computed from the same walk, so it adds no search cost of its own")


if __name__ == "__main__":
    main()
