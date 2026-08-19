"""Footnotes open against footnotes given, paired per board, on the canonical erasable list.

⚠️ **The number that decided this has the most reason of any to be wrong.** Opening the per-batter
footnote cells was justified by a median stall count going from 5 to 15. That came from
`stall-targeted`, which was the script carrying the duplicated candidate list — and **the duplication
was precisely of the footnote cells**. Their buckets held every entry twice and spent half their
round-robin turns erasing nothing, so the instrument treated footnotes differently from everything
else while measuring the effect of opening footnotes. The bias runs in the direction that inflates the
gap: at the real rate, 15 could be much lower.

Today's regeneration does not settle it. It re-ran with footnotes open and confirmed 100% coverage at
targets 5 to 12, but it never isolated open against given. **The comparison has never been repeated on
the canonical list.**

**Paired per direction**, because a difference between medians cannot say whether every board moved a
little or a few moved a lot, and the two answers point at different decisions.

The two configurations differ by a filter and not by a second list: `erasable()` is the one definition
(v03-P1-02), and *given* is that list with the footnote cells removed.

Read-only against DGL. Run from `forge/`.
"""

import random
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))

from measure import Loaded, load  # noqa: E402

from boxscore_forge.constraints import cell_values, shape_of  # noqa: E402
from boxscore_forge.erasure import DEFAULT_ORDERING, ORDERINGS, erasable  # noqa: E402
from boxscore_forge.identities import find_violations  # noqa: E402
from boxscore_forge.solver import Solution, Technique, solve  # noqa: E402

SAMPLE_PER_DECADE = 4
GATE = 0.25
SEED = 831
TARGETS = tuple(range(5, 13))


@dataclass(frozen=True)
class Walk:
    ceiling: int
    blanks_at: dict[int, int]
    erasable: int


def stalls_in(solution: Solution) -> int:
    count, previous = 0, False
    for step in solution.deductions:
        bounding = step.technique is Technique.BOUNDING
        count += bounding and not previous
        previous = bounding
    return count


def walk(loaded: Loaded, *, footnotes_open: bool) -> Walk | None:
    """Erase as far as the board allows, recording the ceiling and where each target was first met."""
    direction = loaded.direction
    cells = [cell for cell in erasable(direction) if footnotes_open or not cell.startswith("footnotes[")]
    shape, values = shape_of(direction), cell_values(direction)
    candidates = ORDERINGS[DEFAULT_ORDERING](cells, direction, random.Random(SEED))  # noqa: S311

    erased: set[str] = set()
    blanks_at: dict[int, int] = {}
    ceiling = 0
    for cell in candidates:
        trial = erased | {cell}
        solution = solve(shape, {name: value for name, value in values.items() if name not in trial})
        if not solution.is_complete:
            continue
        erased = trial
        stalls = stalls_in(solution)
        ceiling = max(ceiling, stalls)
        for target in TARGETS:
            if stalls >= target and target not in blanks_at:
                blanks_at[target] = len(erased)
    return Walk(ceiling=ceiling, blanks_at=blanks_at, erasable=len(candidates)) if ceiling else None


def report(pairs: list[tuple[str, Walk, Walk]]) -> None:
    print("")
    print("=== STALL CEILING, PAIRED PER BOARD ===")
    opened = [pair[1].ceiling for pair in pairs]
    given = [pair[2].ceiling for pair in pairs]
    print(f"{'':<14}{'open':>8}{'given':>8}")
    for name, get in (("median", statistics.median), ("mean", statistics.fmean), ("max", max), ("min", min)):
        print(f"{name:<14}{get(opened):>8.1f}{get(given):>8.1f}")
    deltas = [a - b for a, b in zip(opened, given, strict=True)]
    print(f"{'median delta':<14}{statistics.median(deltas):>8.1f}  (per board, not a difference of medians)")
    print(f"boards where open is higher: {sum(d > 0 for d in deltas)}/{len(deltas)}, "
          f"equal: {sum(d == 0 for d in deltas)}, lower: {sum(d < 0 for d in deltas)}")
    print(f"erasable cells: open {pairs[0][1].erasable}, given {pairs[0][2].erasable} on the first board")

    print("")
    print("=== COVERAGE AND BLANKS AT EACH TARGET ===")
    print(f"{'stalls':>7}{'open %':>9}{'given %':>9}{'open p50':>10}{'given p50':>11}")
    for target in TARGETS:
        o = [pair[1].blanks_at[target] for pair in pairs if target in pair[1].blanks_at]
        g = [pair[2].blanks_at[target] for pair in pairs if target in pair[2].blanks_at]
        print(f"{target:>7}{len(o) / len(pairs):>9.0%}{len(g) / len(pairs):>9.0%}"
              f"{statistics.median(o) if o else float('nan'):>10.0f}"
              f"{statistics.median(g) if g else float('nan'):>11.0f}")

    print("")
    print("=== DOES 5-AGAINST-15 REPRODUCE? ===")
    print(f"  the claim: median ceiling 5 with footnotes given, 15 with them open")
    print(f"  measured:  median ceiling {statistics.median(given):.0f} given, {statistics.median(opened):.0f} open")
    print(f"  coverage at 5 stalls: {sum(1 for p in pairs if 5 in p[2].blanks_at) / len(pairs):.0%} given "
          f"(the claim said 56%), {sum(1 for p in pairs if 5 in p[1].blanks_at) / len(pairs):.0%} open")


def main() -> None:
    sample = [item for item in load(SAMPLE_PER_DECADE, gated=True, gate=GATE, max_batters=13, max_pitchers=4)
              if not find_violations(item.direction)]
    if not sample:
        raise SystemExit(f"no directions survived the {GATE:.0%} gate")
    print(f"{len(sample)} gated directions, each walked twice on the same ordering and seed", flush=True)
    print(f"decades: {dict(sorted(Counter((i.season // 10) * 10 for i in sample).items()))}", flush=True)

    pairs: list[tuple[str, Walk, Walk]] = []
    for number, item in enumerate(sample, start=1):
        opened, given = walk(item, footnotes_open=True), walk(item, footnotes_open=False)
        if opened and given:
            pairs.append((item.game_id, opened, given))
        if number % 10 == 0:
            print(f"  {number}/{len(sample)} paired", flush=True)
    if not pairs:
        raise SystemExit("no board produced a derivable erasure in both configurations")
    report(pairs)
    print(f"\n({len(pairs)} boards in both configurations)")


if __name__ == "__main__":
    main()
