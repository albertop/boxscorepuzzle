"""Does a door work where a thermometer did not?

Several rounds went into scoring how boring a board is. But the zero-heavy board that started it was
not a measurement problem — a shutout where the player writes nine zeros is simply not worth
publishing. That does not need an index, it needs a gate: too many zeros, out of the pool.

This tests whether that is sufficient. If the filtered pool keeps its variety of chain length and
family combination while losing the shutouts, the metric work can stop.

The threshold is read off the distribution rather than guessed. Read-only against DGL, run from
`forge/`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bootstrap import bootstrap  # noqa: E402

bootstrap()

import random
import statistics
from collections import Counter

from compressibility import chain_targeted, families_of, proxies
from measure import load

from boxscore_forge.identities import find_violations

TARGETS = (5, 10, 20)
CANDIDATE_THRESHOLDS = (0.25, 0.30, 0.35, 0.40, 0.45)
SEED = 20260821


def main() -> None:
    rng = random.Random(SEED)
    sample = [item for item in load(25) if not find_violations(item.direction)]
    density = {id(item): proxies(item)["zero_density"] for item in sample}
    print(f"{len(sample)} directions\n")

    print("=== HOW MUCH OF A BOARD IS NOUGHT ===")
    ordered = sorted(density.values())
    for label, value in (
        ("min", ordered[0]),
        ("p10", ordered[len(ordered) // 10]),
        ("p25", ordered[len(ordered) // 4]),
        ("p50", statistics.median(ordered)),
        ("p75", ordered[3 * len(ordered) // 4]),
        ("p90", ordered[9 * len(ordered) // 10]),
        ("max", ordered[-1]),
    ):
        print(f"  {label:>4}: {value:.1%}")

    print("\n=== WHAT EACH THRESHOLD COSTS ===")
    print("  674 directions a year are needed, against 55,024 surviving the funnel")
    for threshold in CANDIDATE_THRESHOLDS:
        kept = sum(1 for value in density.values() if value < threshold)
        share = kept / len(sample)
        print(
            f"  below {threshold:.0%}: keeps {share:5.1%} of the pool "
            f"(~{int(55024 * share):>6,} directions, {55024 * share / 674:5.1f} years of calendar)"
        )

    print("\n=== DOES THE FILTERED POOL KEEP ITS VARIETY ===")
    for target in TARGETS:
        solved = []
        for loaded in sample:
            solution = chain_targeted(loaded, target, rng)
            if solution is not None:
                solved.append((loaded, solution))
        if len(solved) < 20:
            continue
        print(f"\n  chain target {target}:")
        for label, subset in (
            ("full pool  ", solved),
            ("below 35%  ", [s for s in solved if density[id(s[0])] < 0.35]),
            ("below 30%  ", [s for s in solved if density[id(s[0])] < 0.30]),
        ):
            if not subset:
                continue
            families: Counter[str] = Counter(families_of(solution) for _, solution in subset)
            total = sum(families.values())
            chains = [solution.chain_length for _, solution in subset]
            shown = ", ".join(f"{k} {100.0 * v / total:.0f}%" for k, v in families.most_common(3))
            print(
                f"    {label} n={len(subset):>3}  chain p50 {statistics.median(chains):.0f} "
                f"({min(chains)}-{max(chains)})   {shown}"
            )

    print("\n=== WHAT THE GATE THROWS OUT ===")
    for threshold in (0.30, 0.35):
        excluded = [item for item in sample if density[id(item)] >= threshold]
        if not excluded:
            continue
        runs = [item.direction.batting_totals.runs for item in excluded]
        hits = [item.direction.batting_totals.hits for item in excluded]
        shutouts = sum(1 for value in runs if value == 0)
        print(
            f"  at {threshold:.0%}: {len(excluded)} boards, median {statistics.median(runs):.0f} runs "
            f"and {statistics.median(hits):.0f} hits, {shutouts} of them shutouts"
        )
    kept = [item for item in sample if density[id(item)] < 0.30]
    if kept:
        runs = [item.direction.batting_totals.runs for item in kept]
        print(
            f"  kept below 30%: median {statistics.median(runs):.0f} runs, "
            f"{sum(1 for value in runs if value == 0)} shutouts"
        )


if __name__ == "__main__":
    main()
