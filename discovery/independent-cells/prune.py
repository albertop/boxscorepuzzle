"""Pruning the filler, and re-asking which ordering causes it.

**The finding this answers.** A chain-5 board carries fourteen blanks and nine of them depend on
nothing that was deduced — 59% of the filling needs no ordering. It is not a tail of bad boards, it
is the median, and it barely improves with chain length. There is no threshold to set; there is an
erasure rule producing filler systematically.

**Pruning.** Erase to the target as now, then hand each blank back as *given* while the chain still
holds. That keeps the path the chain needed and drops only the filling, without the greedy trap of
permanently discarding a cell that would have let a later one lengthen the chain.

Two things pruning should also catch, measured separately because they are different:

  independent    resolves from an equation already holding everything else; no ordering at all
  dead-end       depends on something earlier, but nothing depends on it — dependent by the letter
                 and contributing nothing to the chain

**And the ordering question, re-opened.** `row_first` was chosen on *fewest trivial steps*, before
this metric existed — and trivial steps and independent cells were then shown to have zero overlap.
The totals row is one row, so a row-spreading erasure gives it one blank and moves on, leaving every
other column with its total given and every blank in it a subtraction against a known number. That is
a hypothesis about the mechanism, and it is checkable: the four orderings are compared here against
the metric that matters rather than the one that happened to exist.

Read-only against DGL. Run from `forge/`.
"""

import random
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))
sys.path.insert(0, str(_ROOT / "discovery" / "pitcher-cap"))

from measure import Loaded, load  # noqa: E402
from render_boards import page, render  # noqa: E402

from boxscore_forge.constraints import cell_values, shape_of  # noqa: E402
from boxscore_forge.erasure import ORDERINGS, erasable  # noqa: E402
from boxscore_forge.identities import find_violations  # noqa: E402
from boxscore_forge.solver import Solution, solve  # noqa: E402

TARGETS = (6, 8, 10)
GATE = 0.25
SEEDS = (1, 2)
SAMPLE_PER_DECADE = 5


@dataclass(frozen=True)
class Result:
    ordering: str
    target: int
    chain: int
    erased: int
    independent: int
    dead_end: int
    pruned_erased: int
    pruned_independent: int
    reached: bool
    families: frozenset[str]
    pruned_families: frozenset[str]
    pitching_blanks: int
    pruned_pitching_blanks: int
    pruned_pitcher_row_blanks: int

    @property
    def share(self) -> float:
        return self.independent / self.erased if self.erased else 0.0

    @property
    def pruned_share(self) -> float:
        return self.pruned_independent / self.pruned_erased if self.pruned_erased else 0.0


def independent_cells(solution: Solution) -> set[str]:
    """Cells that fell out of an equation already holding everything else."""
    recovered = {step.cell for step in solution.deductions}
    return {step.cell for step in solution.deductions if not (step.depends_on & recovered)}


def dead_end_cells(solution: Solution) -> set[str]:
    """Depends on something earlier, and nothing depends on it.

    Dependent by the letter of the definition and contributing nothing to the chain: the end of a
    branch the player walks and then abandons.
    """
    recovered = {step.cell for step in solution.deductions}
    leaned_on: set[str] = set()
    for step in solution.deductions:
        leaned_on |= step.depends_on & recovered
    return {step.cell for step in solution.deductions if (step.depends_on & recovered) and step.cell not in leaned_on}


def prune(shape: object, values: dict[str, int], erased: set[str], target: int) -> set[str]:
    """Hand blanks back as given, keeping what the chain **and the families** need.

    ⚠️ **Unconstrained pruning degenerates the board.** Pitching cells and totals cells resolve against
    given numbers, so they look independent and are handed back first — and the minimum it converges
    on is a batting-only puzzle with a complete boxscore decorating it. With both totals rows given
    the equation linking them has no unknowns: it is true and useless, and the player never has a
    reason to look at the pitching section at all. §3 calls that cross "the part without which the
    puzzle degenerates into row arithmetic", and this is exactly that degeneration, systematically.

    So a blank that is the last remaining reason to use a family is not filler, however independent
    it looks. Coverage is preserved the same way chain length already was.
    """
    kept = set(erased)
    start = solve(shape, {name: value for name, value in values.items() if name not in kept})  # type: ignore[arg-type]
    required = frozenset(family.value for family in start.families_used)
    while True:
        given = {name: value for name, value in values.items() if name not in kept}
        solution = solve(shape, given)  # type: ignore[arg-type]
        candidates = sorted(independent_cells(solution) | dead_end_cells(solution))
        removed = False
        for cell in candidates:
            trial = kept - {cell}
            if not trial:
                continue
            attempt = solve(shape, {name: value for name, value in values.items() if name not in trial})  # type: ignore[arg-type]
            covers = frozenset(family.value for family in attempt.families_used) >= required
            # At least one blank in the pitching section, so the section is part of the puzzle
            # rather than decoration. Family coverage does not give this: cross-team can be
            # exercised entirely through a batting-side cell while the pitching half is complete,
            # and a quarter of easy boards ended that way.
            keeps_pitching = any(c.startswith(("pitching[", "pitching_totals")) for c in trial)
            if attempt.is_complete and attempt.chain_length >= target and covers and keeps_pitching:
                kept = trial
                removed = True
                break
        if not removed:
            return kept


def run(loaded: Loaded, ordering: str, seed: int) -> list[Result]:
    direction = loaded.direction
    shape = shape_of(direction)
    values = cell_values(direction)
    rng = random.Random(seed)  # noqa: S311
    candidates = ORDERINGS[ordering](erasable(direction), direction, rng)

    found: list[Result] = []
    wanted = list(TARGETS)
    erased: set[str] = set()
    for cell in candidates:
        trial = erased | {cell}
        given = {name: value for name, value in values.items() if name not in trial}
        solution = solve(shape, given)
        if not solution.is_complete:
            continue
        erased = trial
        while wanted and solution.chain_length >= wanted[0]:
            target = wanted.pop(0)
            kept = prune(shape, values, set(erased), target)
            after = solve(shape, {name: value for name, value in values.items() if name not in kept})
            found.append(
                Result(
                    ordering=ordering,
                    target=target,
                    chain=solution.chain_length,
                    erased=len(erased),
                    independent=len(independent_cells(solution)),
                    dead_end=len(dead_end_cells(solution)),
                    pruned_erased=len(kept),
                    pruned_independent=len(independent_cells(after)),
                    reached=after.chain_length >= target,
                    families=frozenset(f.value for f in solution.families_used),
                    pruned_families=frozenset(f.value for f in after.families_used),
                    pitching_blanks=sum(1 for c in erased if c.startswith(("pitching[", "pitching_totals"))),
                    pruned_pitching_blanks=sum(1 for c in kept if c.startswith(("pitching[", "pitching_totals"))),
                    pruned_pitcher_row_blanks=sum(1 for c in kept if c.startswith("pitching[")),
                )
            )
        if not wanted:
            break
    return found


def report(results: list[Result]) -> None:
    print("\n=== THE FOUR ORDERINGS AGAINST THE METRIC THAT MATTERS ===")
    print("row_first was chosen on fewest trivial steps, before this existed.")
    print(f"{'ordering':>13}{'target':>8}{'blanks':>8}{'independent':>13}{'share':>8}{'dead-end':>10}{'per step':>10}")
    for ordering in sorted(ORDERINGS):
        for target in TARGETS:
            group = [r for r in results if r.ordering == ordering and r.target == target]
            if not group:
                continue
            print(
                f"{ordering:>13}{target:>8}"
                f"{statistics.median([r.erased for r in group]):>8.0f}"
                f"{statistics.median([r.independent for r in group]):>13.0f}"
                f"{statistics.fmean([r.share for r in group]):>8.0%}"
                f"{statistics.median([r.dead_end for r in group]):>10.0f}"
                f"{statistics.fmean([r.erased / max(r.chain, 1) for r in group]):>10.2f}"
            )
        print()


def report_pruning(results: list[Result]) -> None:
    print("=== WHAT PRUNING REMOVES ===")
    print(
        f"{'target':>8}{'before':>9}{'after':>8}{'removed':>10}{'share before':>15}{'share after':>14}{'still reaches':>15}"
    )
    for target in TARGETS:
        group = [r for r in results if r.target == target]
        if not group:
            continue
        before = statistics.median([r.erased for r in group])
        after = statistics.median([r.pruned_erased for r in group])
        print(
            f"{target:>8}{before:>9.0f}{after:>8.0f}{before - after:>10.0f}"
            f"{statistics.fmean([r.share for r in group]):>15.0%}"
            f"{statistics.fmean([r.pruned_share for r in group]):>14.0%}"
            f"{statistics.fmean([1.0 if r.reached else 0.0 for r in group]):>15.0%}"
        )
    print("  Pruning cannot cost pool: the board reached the target before pruning began.")
    print("")
    print("=== FAMILY COVERAGE, AND WHETHER PITCHING STAYS IN THE PUZZLE ===")
    heads = f"{'target':>8}{'families before':>18}{'after':>8}{'lost any':>10}{'pitch blanks':>15}{'after':>8}{'none left':>11}"
    print(heads)
    for target in TARGETS:
        group = [r for r in results if r.target == target]
        if not group:
            continue
        lost = sum(1 for r in group if not r.pruned_families >= r.families)
        empty = sum(1 for r in group if r.pruned_pitching_blanks == 0)
        print(
            f"{target:>8}{statistics.fmean([len(r.families) for r in group]):>18.2f}"
            f"{statistics.fmean([len(r.pruned_families) for r in group]):>8.2f}"
            f"{lost:>10}"
            f"{statistics.median([r.pitching_blanks for r in group]):>15.0f}"
            f"{statistics.median([r.pruned_pitching_blanks for r in group]):>8.0f}"
            f"{empty:>11}"
        )
    print("  none left counts boards whose pitching section became decoration.")
    print("")
    print("=== IS THE FORCED PITCHING BLANK ITSELF FILLER ===")
    print("  A pitching cell resolved against given totals is independent, so the constraint could")
    print("  reintroduce what pruning removes. Pruning only hands blanks back, and the retained one")
    print("  comes from a set that already reached the target - confirmed rather than assumed:")
    for target in TARGETS:
        group = [r for r in results if r.target == target and r.pruned_pitching_blanks]
        if not group:
            continue
        share = statistics.fmean([r.pruned_independent / max(r.pruned_erased, 1) for r in group])
        print(f"    chain {target:>2}: {len(group)} boards keep a pitching blank, independent share {share:.0%}")
    print("")
    print("=== FAMILY DISTRIBUTION ON PRUNED BOARDS ===")
    print("  The ceiling was lowered to 11 on pre-pruning saturation. A pruned board is a different")
    print("  object, so the question is open again.")
    heads = f"{'target':>8}{'boards':>8}{'all four':>10}{'three':>8}{'two':>7}{'blanks':>8}"
    print(heads)
    for target in TARGETS:
        group = [r for r in results if r.target == target]
        if not group:
            continue
        four = sum(1 for r in group if len(r.pruned_families) == 4) / len(group)
        three = sum(1 for r in group if len(r.pruned_families) == 3) / len(group)
        two = sum(1 for r in group if len(r.pruned_families) <= 2) / len(group)
        print(
            f"{target:>8}{len(group):>8}{four:>9.0%}{three:>8.0%}{two:>7.0%}"
            f"{statistics.median([r.pruned_erased for r in group]):>8.0f}"
        )


def render_comparison(sample: list[Loaded]) -> None:
    """Pruned boards at each candidate rung, so the floor can be chosen by looking.

    The pruned-against-unpruned comparison is settled; this one asks how 6, 8 and 10 read against
    each other. **A blank ratio comes with it**, because nine blanks in sixty-eight cells is 13% and
    that may read as a filled boxscore with a few typos rather than as a puzzle.
    """
    boards: list[dict[str, object]] = []
    ratios: dict[int, list[float]] = {}
    for target in TARGETS:
        drawn = 0
        for loaded in sample:
            if drawn >= 4:
                break
            shape = shape_of(loaded.direction)
            values = cell_values(loaded.direction)
            rng = random.Random(3)  # noqa: S311
            erased: set[str] = set()
            reached = False
            for cell in ORDERINGS["row_first"](erasable(loaded.direction), loaded.direction, rng):
                trial = erased | {cell}
                solution = solve(shape, {n: v for n, v in values.items() if n not in trial})
                if not solution.is_complete:
                    continue
                erased = trial
                if solution.chain_length >= target:
                    reached = True
                    break
            if not reached:
                continue
            kept = prune(shape, values, set(erased), target)
            cells = len(erasable(loaded.direction))
            ratio = len(kept) / cells
            ratios.setdefault(target, []).append(ratio)
            boards.append(
                render(
                    loaded,
                    SimpleNamespace(erased=frozenset(kept)),
                    f"CHAIN {target} - {len(kept)} blanks of {cells} cells ({ratio:.0%})",
                )
            )
            drawn += 1

    out = _ROOT / "discovery" / "independent-cells" / "the-three-rungs.html"
    out.write_text(
        page(
            boards,
            title="Chain 6, 8 and 10 - pruned, side by side",
            intro="Four pruned boards at each candidate rung, in order. Every blank is necessary: the "
            "chain needs it, or a family would be lost, or the pitching section would become "
            "decoration. The question is which rung reads as a puzzle rather than as a filled "
            "boxscore with a few gaps.",
        ),
        encoding="utf-8",
    )
    print(f"{len(boards)} boards written to {out}")
    print("")
    print("=== HOW MUCH OF THE BOARD IS BLANK, BY RUNG ===")
    for target in sorted(ratios):
        values_here = ratios[target]
        print(
            f"  chain {target:>2}: {statistics.fmean(values_here):.0%} blank"
            f"  ({statistics.median([r for r in values_here]):.0%} median, {len(values_here)} boards)"
        )
    print("  A sudoku runs about 60% empty. Nobody is copying that, but 13% may read as a")
    print("  completed boxscore with a few typos rather than as a puzzle.")


def report_pitching_location(results: list[Result]) -> None:
    """Does the retained pitching blank land in the totals row or in a pitcher line?

    A blank in the totals row satisfies the constraint and does make the section participate, but
    weakly: completing it is one addition over the pitcher lines. A blank *inside* a pitcher line
    forces the cross-team route instead, which is the participation that was wanted.
    """
    print("")
    print("=== WHERE THE RETAINED PITCHING BLANK LANDS ===")
    heads = f"{'target':>8}{'boards':>8}{'in a pitcher row':>19}{'totals only':>14}"
    print(heads)
    for target in TARGETS:
        group = [r for r in results if r.target == target and r.pruned_pitching_blanks]
        if not group:
            continue
        in_row = sum(1 for r in group if r.pruned_pitcher_row_blanks)
        print(f"{target:>8}{len(group):>8}{in_row / len(group):>18.0%}{1 - in_row / len(group):>13.0%}")
    print("  If it is nearly always the totals row, the constraint should ask for a pitcher row.")


def main() -> None:
    loaded = load(SAMPLE_PER_DECADE, gated=True, gate=GATE, max_batters=13, max_pitchers=4)
    sample = [item for item in loaded if not find_violations(item.direction)]
    print(f"{len(sample)} gated directions, gate {GATE:.0%}")
    print(f"decades: {dict(sorted(Counter((item.season // 10) * 10 for item in sample).items()))}")

    render_comparison(sample)
    results = [
        result
        for item in sample
        for ordering in sorted(ORDERINGS)
        for seed in SEEDS
        for result in run(item, ordering, seed)
    ]
    print(f"{len(results)} measured boards")
    report(results)
    report_pruning(results)
    report_pitching_location(results)


if __name__ == "__main__":
    main()
