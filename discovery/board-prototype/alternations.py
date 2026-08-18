"""How often does a solution cross between the batting and pitching halves of the board?

This decides whether the pitching section can scroll away. If a typical path crosses two or three
times, scrolling costs the player almost nothing and the 191 pixels a permanently visible pitching
panel occupies are better spent on batting rows. If it crosses a dozen times, the scrolling is worse
than the pixels.

Counted over solution paths the solver already produces, at the chain targets the calendar will use.

Read-only against DGL. Run from `forge/`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bootstrap import bootstrap  # noqa: E402

bootstrap()

import random
import statistics
from collections import Counter

from compressibility import chain_targeted
from measure import load

from boxscore_forge.identities import find_violations
from boxscore_forge.solver import Solution

TARGETS = (5, 10, 20)
SEED = 20260822


def section(cell: str) -> str | None:
    """Which half of the board a cell sits in. The line score and team footnotes are the anchor and
    scroll with nothing, so they count as neither."""
    if cell.startswith(("batting", "footnotes[", "footnote_totals")):
        return "batting"
    if cell.startswith("pitching"):
        return "pitching"
    return None


def alternations(solution: Solution) -> int:
    visited = [s for s in (section(d.cell) for d in solution.deductions) if s is not None]
    return sum(1 for before, after in zip(visited, visited[1:], strict=False) if before != after)


def main() -> None:
    rng = random.Random(SEED)
    sample = [item for item in load(10) if not find_violations(item.direction)]
    print(f"{len(sample)} directions\n")

    for target in TARGETS:
        counts: list[int] = []
        pitching_steps: list[float] = []
        for loaded in sample:
            solution = chain_targeted(loaded, target, rng)
            if solution is None or not solution.deductions:
                continue
            counts.append(alternations(solution))
            in_pitching = sum(1 for d in solution.deductions if section(d.cell) == "pitching")
            pitching_steps.append(in_pitching / len(solution.deductions))
        if not counts:
            continue
        histogram = Counter(counts)
        ordered = sorted(counts)
        print(f"=== chain target {target}  (n={len(counts)}) ===")
        print(
            f"  crossings between the halves: min {ordered[0]}  p50 {statistics.median(ordered):.0f}  "
            f"p90 {ordered[9 * len(ordered) // 10]}  max {ordered[-1]}"
        )
        print("  " + ", ".join(f"{k}x:{100.0 * v / len(counts):.0f}%" for k, v in sorted(histogram.items())[:8]))
        print(f"  share of steps landing in the pitching half: median {statistics.median(pitching_steps):.0%}\n")


if __name__ == "__main__":
    main()