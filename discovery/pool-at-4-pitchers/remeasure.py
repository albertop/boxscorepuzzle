"""Everything that was measured on the old pool, measured again on the one that ships.

The population has changed three times now — random erasure to chain-targeted, ungated to gated, and
now ≤2 pitchers to ≤4 — and the answer moved every time. Nothing is assumed to transfer.

What this answers:

  ceiling        how far a gated ≤4 board can be erased before it stops being derivable
  families       which combinations are reachable at each chain target, now that cross-team is no
                 longer compulsory (it was 100% at two pitchers, which distinguished nothing)
  bands          the three metrics' spread and independence, target by target
  discrimination where the metrics stop separating boards, which is where the weekly curve should
                 stop rather than at a number anyone picked
  boredom        whether the hardest day quietly readmits what the gate removed — chain ceiling
                 correlates with compressibility and compressibility with zero density, so the
                 hardest target may be selecting the boards the gate exists to exclude

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

from compressibility import proxies  # noqa: E402
from measure import Loaded, load  # noqa: E402

from boxscore_forge.constraints import cell_values, shape_of  # noqa: E402
from boxscore_forge.erasure import ORDERINGS, erasable  # noqa: E402
from boxscore_forge.identities import Family, find_violations  # noqa: E402
from boxscore_forge.solver import Solution, solve  # noqa: E402

TARGETS = (3, 5, 7, 9, 11, 13, 15, 17, 19, 21)
SEEDS = (1, 2, 3)
SAMPLE_PER_DECADE = 6
ORDERING = "row_first"


@dataclass(frozen=True)
class Snapshot:
    erased: int
    chain: int
    search: float | None
    resolution: int | None
    trivial: float | None
    families: tuple[str, ...]


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
        solution: Solution = solve(shape, given)
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
                families=tuple(sorted(family.value for family in solution.families_used)),
            )
        )
    return snapshots


def first_reaching(snapshots: list[Snapshot], target: int) -> Snapshot | None:
    return next((snapshot for snapshot in snapshots if snapshot.chain >= target), None)


def ceiling(runs: list[list[Snapshot]]) -> None:
    print("\n=== HOW FAR A GATED ≤4 BOARD GOES ===")
    finals = [run[-1] for run in runs if run]
    chains = [final.chain for final in finals]
    erased = [final.erased for final in finals]
    print(f"  runs                    : {len(finals)}")
    print(f"  max chain p10/p50/p90   : {_pc(chains, 0.1):.0f} / {_pc(chains, 0.5):.0f} / {_pc(chains, 0.9):.0f}")
    print(f"  cells erased at ceiling : {_pc(erased, 0.5):.0f} (p50)")


def bands(runs: list[list[Snapshot]]) -> None:
    """Where the metrics stop discriminating.

    A metric separates boards while its spread is wide. When the p10 and the p90 meet, every board
    scores alike and the number has stopped saying anything — which is where the weekly curve should
    end, rather than at a number chosen for looking hard.
    """
    print("\n=== BANDS AND WHERE THEY CLOSE ===")
    print(f"{'target':>7}{'reached':>9}{'erased':>8}{'search p10-p90':>18}{'width':>8}"
          f"{'resolution p10-p90':>21}{'width':>8}{'trivial':>9}")
    for target in TARGETS:
        found = [hit for run in runs if (hit := first_reaching(run, target))]
        if not found:
            print(f"{target:>7}{0.0:>8.0f}%")
            continue
        searches = [hit.search for hit in found if hit.search is not None]
        resolutions = [float(hit.resolution) for hit in found if hit.resolution is not None]
        trivials = [hit.trivial for hit in found if hit.trivial is not None]
        if not searches or not resolutions:
            continue
        s_low, s_high = _pc(searches, 0.1), _pc(searches, 0.9)
        r_low, r_high = _pc(resolutions, 0.1), _pc(resolutions, 0.9)
        print(
            f"{target:>7}{100.0 * len(found) / len(runs):>8.0f}%"
            f"{_pc([float(hit.erased) for hit in found], 0.5):>8.0f}"
            f"{s_low:>10.2f}-{s_high:<7.2f}{s_high - s_low:>8.2f}"
            f"{r_low:>13.0f}-{r_high:<7.0f}{r_high - r_low:>8.1f}"
            f"{statistics.fmean(trivials):>9.2f}"
        )
    print("  A width approaching zero means every board scores alike and the metric has stopped")
    print("  separating them. That is the end of the usable range, not a hard board.")


def independence(runs: list[list[Snapshot]]) -> None:
    print("\n=== ARE THE THREE STILL INDEPENDENT ===")
    print(f"{'target':>7}{'n':>6}{'r(chain,search)':>18}{'r(chain,resolution)':>22}{'r(search,resolution)':>23}")
    for target in TARGETS:
        found = [hit for run in runs if (hit := first_reaching(run, target))]
        rows = [
            (float(hit.chain), hit.search, float(hit.resolution))
            for hit in found
            if hit.search is not None and hit.resolution is not None
        ]
        if len(rows) < 20:
            continue
        chains = [row[0] for row in rows]
        searches = [row[1] for row in rows]
        resolutions = [row[2] for row in rows]
        print(
            f"{target:>7}{len(rows):>6}{_pearson(chains, searches):>18.3f}"
            f"{_pearson(chains, resolutions):>22.3f}{_pearson(searches, resolutions):>23.3f}"
        )


def families(runs: list[list[Snapshot]]) -> None:
    print("\n=== FAMILIES REACHABLE AT EACH CHAIN TARGET ===")
    names = [family.value for family in Family]
    print(f"{'target':>7}{'boards':>8}{'all four':>10}" + "".join(f"{name:>16}" for name in names))
    for target in TARGETS:
        found = [hit for run in runs if (hit := first_reaching(run, target))]
        if not found:
            continue
        counter: Counter[str] = Counter()
        for hit in found:
            for family in hit.families:
                counter[family] += 1
        all_four = sum(1 for hit in found if len(hit.families) == len(names))
        shares = "".join(f"{100.0 * counter[name] / len(found):>15.0f}%" for name in names)
        print(f"{target:>7}{len(found):>8}{100.0 * all_four / len(found):>9.0f}%{shares}")

    print("\n  most common combinations, by target:")
    for target in TARGETS:
        found = [hit for run in runs if (hit := first_reaching(run, target))]
        if not found:
            continue
        combinations: Counter[tuple[str, ...]] = Counter(hit.families for hit in found)
        shown = ", ".join(
            f"{'+'.join(name.replace('_identity', '').replace('_sum', '') for name in combo) or 'none'}"
            f" {100.0 * count / len(found):.0f}%"
            for combo, count in combinations.most_common(3)
        )
        print(f"    chain {target:>2}: {shown}")


def boredom(sample: list[Loaded], per_direction: dict[int, list[list[Snapshot]]]) -> None:
    """Does the hardest day readmit the boards the gate removed?

    Chain ceiling correlates with compressibility and compressibility with zero density (§5), so
    selecting for the longest chains may be selecting, quietly, for the emptiest boards that still
    passed the gate.
    """
    print("\n=== DOES THE HARDEST DAY BRING BACK BORING BOARDS ===")
    print(f"{'target':>7}{'reached n':>11}{'zero density reached':>22}{'zero density failed':>21}{'gap':>8}")
    density = {index: proxies(loaded)["zero_density"] for index, loaded in enumerate(sample)}
    for target in TARGETS:
        reached: list[float] = []
        failed: list[float] = []
        for index in per_direction:
            hit = any(first_reaching(run, target) is not None for run in per_direction[index])
            (reached if hit else failed).append(density[index])
        if not reached or not failed:
            continue
        print(
            f"{target:>7}{len(reached):>11}{statistics.fmean(reached):>21.1%}"
            f"{statistics.fmean(failed):>20.1%}{statistics.fmean(reached) - statistics.fmean(failed):>+8.1%}"
        )
    print("  A positive gap means the hardest boards are the emptiest ones the gate let through.")

    ceilings = [
        max((run[-1].chain for run in per_direction[index] if run), default=0) for index in sorted(per_direction)
    ]
    densities = [density[index] for index in sorted(per_direction)]
    print(f"\n  r(zero density, chain ceiling) = {_pearson(densities, [float(c) for c in ceilings]):+.3f}")


def resolution_ceiling(sample: list[Loaded], per_direction: dict[int, list[list[Snapshot]]]) -> None:
    """What an absolute resolution ceiling would quietly throw away.

    Resolution p90 is now a ceiling rather than a target. But it correlates +0.45 with batting rows
    (§31) and modern boards carry more rows, so **an absolute ceiling is a covert batter cap** — and
    a covert batter cap works directly against the pitcher-cap decision, which exists to buy the
    modern era. If the discard skews modern, the ceiling has to scale with row count instead.
    """
    print("\n=== WOULD A RESOLUTION CEILING BE A COVERT BATTER CAP ===")
    at_target: dict[int, tuple[int, int, int]] = {}
    for index, loaded in enumerate(sample):
        hits = [hit for run in per_direction[index] if (hit := first_reaching(run, 11))]
        resolutions = [hit.resolution for hit in hits if hit.resolution is not None]
        if resolutions:
            at_target[index] = (
                int(statistics.median(resolutions)),
                len(loaded.direction.batting),
                (loaded.season // 10) * 10,
            )
    if not at_target:
        return

    print(f"{'batting rows':>13}{'boards':>8}{'resolution p50':>16}")
    by_rows: dict[int, list[int]] = {}
    for resolution, rows, _ in at_target.values():
        by_rows.setdefault(rows, []).append(resolution)
    for rows in sorted(by_rows):
        print(f"{rows:>13}{len(by_rows[rows]):>8}{statistics.median(by_rows[rows]):>16.0f}")

    print(f"\n{'decade':>8}{'boards':>8}{'resolution p50':>16}   discarded by an absolute ceiling of")
    ceilings = (7, 8, 9, 10)
    print(f"{'':>32}" + "".join(f"{ceiling:>9}" for ceiling in ceilings))
    by_decade: dict[int, list[tuple[int, int]]] = {}
    for resolution, rows, decade in at_target.values():
        by_decade.setdefault(decade, []).append((resolution, rows))
    for decade in sorted(by_decade):
        entries = by_decade[decade]
        resolutions = [resolution for resolution, _ in entries]
        cut = "".join(
            f"{100.0 * sum(1 for value in resolutions if value > ceiling) / len(resolutions):>8.0f}%"
            for ceiling in ceilings
        )
        print(f"{decade:>8}{len(entries):>8}{statistics.median(resolutions):>16.0f}   {cut}")

    # The alternative: a ceiling that scales with the rows the board actually has, which is what the
    # +0.45 correlation says the number is partly measuring anyway.
    print("\n  scaled instead of absolute — a ceiling of k x batting rows:")
    print(f"{'k':>8}{'discarded overall':>20}   by decade, worst to best")
    for k in (0.6, 0.7, 0.8):
        cut_by_decade = {
            decade: 100.0 * sum(1 for resolution, rows in entries if resolution > k * rows) / len(entries)
            for decade, entries in by_decade.items()
        }
        overall = 100.0 * sum(
            1 for resolution, rows, _ in at_target.values() if resolution > k * rows
        ) / len(at_target)
        worst = sorted(cut_by_decade.items(), key=lambda pair: -pair[1])[:3]
        print(f"{k:>8.1f}{overall:>19.0f}%   " + ", ".join(f"{decade}s {share:.0f}%" for decade, share in worst))
    print("  A ceiling that discards evenly across decades is not a batter cap in disguise.")


def _pc[T: (int, float)](values: list[T], fraction: float) -> float:
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



def _render(sample: list, folder: str) -> None:
    """Six boards to look at, written before the numbers are printed (see `discovery/render_step`)."""
    sys.path.insert(0, str(_ROOT / "discovery"))
    from render_step import write_examples  # noqa: PLC0415

    out = _ROOT / "discovery" / folder / "look-at-these.html"
    count = write_examples(sample, out)
    print()
    print(f"{count} boards written to {out} — look at them before trusting anything below")


def main() -> None:
    loaded = load(SAMPLE_PER_DECADE, gated=True, max_batters=13, max_pitchers=4)
    sample = [item for item in loaded if not find_violations(item.direction)]
    print(f"{len(sample)} gated directions at ≤13 batters and ≤4 pitchers, ordering {ORDERING!r}")
    print(f"decades: {dict(sorted(Counter((item.season // 10) * 10 for item in sample).items()))}")
    pitchers = Counter(len(item.direction.pitching) for item in sample)
    print(f"pitchers per board: {dict(sorted(pitchers.items()))}")

    per_direction = {index: [trajectory(item, seed) for seed in SEEDS] for index, item in enumerate(sample)}
    runs = [run for runs_for_one in per_direction.values() for run in runs_for_one]

    _render(sample, "pool-at-4-pitchers")
    ceiling(runs)
    bands(runs)
    independence(runs)
    families(runs)
    resolution_ceiling(sample, per_direction)
    boredom(sample, per_direction)


if __name__ == "__main__":
    main()
