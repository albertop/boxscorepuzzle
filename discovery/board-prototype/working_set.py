"""How far apart are the rows a single step needs?

Rows visible at once is the wrong unit for a deduction puzzle, because the totals are pinned and so
never scroll away. What binds instead is whether the rows a step depends on can be held together.
A step needing batting row 2 and batting row 9 forces the player to carry numbers in their head if
both cannot be on screen; a step needing one row and the pinned totals does not care how long the
board is.

Measured per step: the span in rows between the furthest-apart rows the step's equation touches,
ignoring totals because those are always visible. And alongside it, how many *non-zero* numbers lie
in that span — scanning past eight zeros to find two numbers is not the same load as combining ten.

Read-only against DGL. Run from `forge/`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bootstrap import bootstrap

bootstrap()

import random
import statistics
from collections import Counter

from compressibility import chain_targeted
from measure import load

from boxscore_forge.constraints import equations, shape_of
from boxscore_forge.identities import FAMILY_OF, find_violations

TARGETS = (5, 10, 20)
SEED = 20260823


def row_index(cell: str) -> int | None:
    """The row a cell sits in, or None for a totals row, the line score or a team footnote."""
    for prefix in ("batting[", "pitching[", "footnotes["):
        if cell.startswith(prefix):
            return int(cell.split("[", 1)[1].split("]", 1)[0])
    return None


def main() -> None:
    rng = random.Random(SEED)
    sample = [item for item in load(10) if not find_violations(item.direction)]
    print(f"{len(sample)} directions\n")

    for target in TARGETS:
        spans: Counter[int] = Counter()
        by_family: dict[str, list[int]] = {}
        live_numbers: list[int] = []
        for loaded in sample:
            solution = chain_targeted(loaded, target, rng)
            if solution is None:
                continue
            system = {id(e): e for e in equations(shape_of(loaded.direction))}
            del system
            for step in solution.deductions:
                if step.from_identity is None:
                    continue
                equation = next(
                    (
                        e
                        for e in equations(shape_of(loaded.direction))
                        if e.origin == step.from_identity and any(t.cell == step.cell for t in e.terms)
                    ),
                    None,
                )
                if equation is None:
                    continue
                rows = [r for r in (row_index(t.cell) for t in equation.terms) if r is not None]
                span = (max(rows) - min(rows) + 1) if rows else 0
                spans[span] += 1
                family = FAMILY_OF[step.from_identity].value
                by_family.setdefault(family, []).append(span)
                if step.known_terms_combined is not None:
                    live_numbers.append(step.known_terms_combined)

        total = sum(spans.values()) or 1
        print(f"=== chain target {target}  (n={total} steps) ===")
        print("  rows a step must hold together (totals excluded, they are pinned):")
        for span, count in sorted(spans.items()):
            bar = "#" * round(40 * count / total)
            print(f"   {span:>2} rows: {100.0 * count / total:5.1f}%  {bar}")
        within = sum(count for span, count in spans.items() if span <= 5)
        print(f"  within a five-row window: {100.0 * within / total:.1f}%")
        for family, values in sorted(by_family.items()):
            print(f"    {family:<16} median span {statistics.median(values):.0f}, n={len(values)}")
        if live_numbers:
            print(
                f"  non-zero numbers actually combined: median {statistics.median(live_numbers):.0f}, "
                f"p90 {sorted(live_numbers)[9 * len(live_numbers) // 10]}"
            )
        print()


if __name__ == "__main__":
    main()
