"""The third weak board: mostly free filling.

A chain-5 board carries fifteen to twenty blanks. Chain 5 means five *dependent* steps, so ten to
fifteen of those blanks fall out of an equation that already has everything else in it. The player
fills thirteen holes on autopilot, meets five that require something, and finishes — and what they
remember of Monday is having done arithmetic.

**Neither existing floor sees it.** Floor A counts *trivial* steps, and a subtraction of two known
numbers is not trivial by that definition even though it needs no ordering. Floor B asks which
families are required, and a board can require three families and still be thirteen independent
subtractions plus five chained ones.

So the measure is different from both: **what share of the erased cells depend on no other erased
cell.** The solver already records that — it is where chain length comes from.

Then the question that decides what to do about it: **is the same chain reachable with far fewer
blanks?** `dense` erases the same way but keeps a cell only when it lengthens the chain, so the board
gets the same thinking with none of the filling. If that works, the fix is the erasure rule rather
than a floor.

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
sys.path.insert(0, str(_ROOT / "discovery" / "pitcher-cap"))
sys.path.insert(0, str(_ROOT / "discovery"))

from measure import Loaded, load  # noqa: E402

from boxscore_forge.constraints import cell_values, shape_of  # noqa: E402
from boxscore_forge.erasure import ORDERINGS, erasable  # noqa: E402
from boxscore_forge.identities import Family, find_violations  # noqa: E402
from boxscore_forge.solver import Solution, solve  # noqa: E402

TARGETS = (5, 7, 9, 11)
GATE = 0.25
SEEDS = (1, 2)
SAMPLE_PER_DECADE = 6
ORDERING = "row_first"


@dataclass(frozen=True, slots=True)
class Shape:
    target: int
    chain: int
    erased: int
    independent: int
    trivial: float
    search: float | None
    families: frozenset[str]

    @property
    def independent_share(self) -> float:
        return self.independent / self.erased if self.erased else 0.0

    @property
    def blanks_per_step(self) -> float:
        return self.erased / self.chain if self.chain else 0.0


def independent_count(solution: Solution) -> int:
    """Cells that fell out of an equation already holding everything else.

    A recovered cell is *dependent* when at least one cell it leaned on was itself recovered. If
    every term it needed was given, nothing had to happen first — the player could have filled it at
    any moment, in any order.
    """
    recovered = {step.cell for step in solution.deductions}
    return sum(1 for step in solution.deductions if not (step.depends_on & recovered))


def measure(loaded: Loaded, seed: int, *, dense: bool) -> list[Shape]:
    """Walk the erasure and snapshot at each target.

    With `dense`, a cell is kept only when it lengthens the chain. Everything else is filling: it
    adds a blank the player must resolve and nothing that has to wait for anything.
    """
    direction = loaded.direction
    shape = shape_of(direction)
    values = cell_values(direction)
    rng = random.Random(seed)  # noqa: S311
    candidates = ORDERINGS[ORDERING](erasable(direction), direction, rng)

    found: list[Shape] = []
    wanted = list(TARGETS)
    erased: set[str] = set()
    best_chain = 0
    for cell in candidates:
        trial = erased | {cell}
        given = {name: value for name, value in values.items() if name not in trial}
        solution = solve(shape, given)
        if not solution.is_complete:
            continue
        if dense and solution.chain_length <= best_chain:
            continue
        erased = trial
        best_chain = max(best_chain, solution.chain_length)
        while wanted and solution.chain_length >= wanted[0]:
            found.append(
                Shape(
                    target=wanted.pop(0),
                    chain=solution.chain_length,
                    erased=len(erased),
                    independent=independent_count(solution),
                    trivial=solution.trivial_share or 0.0,
                    search=solution.ninetieth_percentile_search,
                    families=frozenset(family.value for family in solution.families_used),
                )
            )
        if not wanted:
            break
    return found


def _percentiles(values: list[float]) -> str:
    ordered = sorted(values)
    if not ordered:
        return "no data"
    return (
        f"p10 {ordered[len(ordered) // 10]:.2f}  p50 {statistics.median(ordered):.2f}"
        f"  p90 {ordered[9 * len(ordered) // 10]:.2f}  max {ordered[-1]:.2f}"
    )


def report(boards: list[Shape], label: str) -> None:
    print(f"\n=== {label.upper()} ===")
    print(f"{'target':>7}{'boards':>8}{'chain':>7}{'erased':>8}{'independent':>13}{'share':>8}{'per step':>10}")
    by_target: dict[int, list[Shape]] = {}
    for board in boards:
        by_target.setdefault(board.target, []).append(board)
    for target in sorted(by_target):
        group = by_target[target]
        print(
            f"{target:>7}{len(group):>8}"
            f"{statistics.median([b.chain for b in group]):>7.0f}"
            f"{statistics.median([b.erased for b in group]):>8.0f}"
            f"{statistics.median([b.independent for b in group]):>13.0f}"
            f"{statistics.fmean([b.independent_share for b in group]):>8.0%}"
            f"{statistics.fmean([b.blanks_per_step for b in group]):>10.2f}"
        )
    for target in sorted(by_target):
        shares = [board.independent_share for board in by_target[target]]
        print(f"  chain {target:>2} independent share: {_percentiles(shares)}")


def overlap(boards: list[Shape]) -> None:
    """Is this a third defect, or the first two wearing a hat?"""
    easy = [board for board in boards if board.target in (5, 7)]
    if not easy:
        return
    print("\n=== IS IT A THIRD DEFECT, OR THE OTHER TWO AGAIN ===")
    diluted = {i for i, b in enumerate(easy) if b.independent_share >= 0.70}
    floor_a = {
        i for i, b in enumerate(easy) if b.trivial >= 0.35 and (b.search if b.search is not None else 1.0) <= 0.50
    }
    floor_b = {i for i, b in enumerate(easy) if Family.ROW_IDENTITY.value not in b.families}
    print(f"  mostly free filling (>= 70% independent): {len(diluted)} of {len(easy)}")
    print(f"  floor A (trivial and low search)        : {len(floor_a)}")
    print(f"  floor B (no row identity)               : {len(floor_b)}")
    print(f"  diluted and A                           : {len(diluted & floor_a)}")
    print(f"  diluted and B                           : {len(diluted & floor_b)}")
    print("  No overlap means three separate defects, and all three floors apply.")


def compare(sample: list[Loaded]) -> None:
    loose = [shape for item in sample for seed in SEEDS for shape in measure(item, seed, dense=False)]
    dense = [shape for item in sample for seed in SEEDS for shape in measure(item, seed, dense=True)]
    report(loose, "as erased today")
    report(dense, "keeping only cells that lengthen the chain")
    overlap(loose)

    print("\n=== WHAT DENSE ERASURE COSTS AND BUYS ===")
    print(f"{'target':>7}{'reached, loose':>16}{'reached, dense':>16}{'blanks loose':>14}{'blanks dense':>14}")
    per_run = len(sample) * len(SEEDS)
    for target in TARGETS:
        loose_at = [b for b in loose if b.target == target]
        dense_at = [b for b in dense if b.target == target]
        if not loose_at or not dense_at:
            continue
        print(
            f"{target:>7}{len(loose_at) / per_run:>15.0%}{len(dense_at) / per_run:>16.0%}"
            f"{statistics.median([b.erased for b in loose_at]):>14.0f}"
            f"{statistics.median([b.erased for b in dense_at]):>14.0f}"
        )
    print("  A reach that holds means the same thinking is available with a fraction of the filling.")


def render(sample: list[Loaded]) -> None:
    """The comparison that answers it: same target, half the blanks, side by side."""
    from render_step import write_examples  # noqa: PLC0415

    out = _ROOT / "discovery" / "independent-cells" / "dense-against-loose.html"
    count = write_examples(sample, out, target_chain=5, note=" - chain 5 as erased today")
    print(f"\n{count} boards written to {out}")


def main() -> None:
    loaded = load(SAMPLE_PER_DECADE, gated=True, gate=GATE)
    sample = [item for item in loaded if not find_violations(item.direction)]
    print(f"{len(sample)} gated directions, gate {GATE:.0%}, ordering {ORDERING!r}")
    print(f"decades: {dict(sorted(Counter((item.season // 10) * 10 for item in sample).items()))}")
    render(sample)
    compare(sample)


if __name__ == "__main__":
    main()
