"""Weighting the four families, and finding the floor under Monday.

**Part 1 — weights.** This project already does four of sudoku's five grading steps: generate
complete, erase, prove uniqueness, solve with a logical solver recording what it used. The fifth is
missing. Sudoku scores a naked single at 1 and an X-Wing at 15 and classifies primarily by the
*hardest technique required*; here a column sum and the global identity count the same, and they are
plainly not equally hard. `PA = Outs + R + LOB` is the one §8 leaves for last because nobody knows it.

Two derivations, reported side by side rather than merged, because **a disagreement between them is
information about whether the tutorial order reflects real difficulty**:

  tutorial       position in §8's teaching sequence, which is already a claim about relative difficulty
  co-occurrence  what else is true of the boards that require a family — if the global identity only
                 turns up on boards the existing metrics call hard, that is evidence about its weight

Then the test that matters: **does it add anything.** If it tracks chain length or zero density
closely it is a new name for an old number, and this project has carried one metric too long before
because building it took work.

**Part 2 — the easy end**, which has no floor at all. Monday is "chain 5" and nothing else: a length,
with no statement about content. The easy extreme is the worse one — an impossible board produces a
complaint, a trivial one produces a silent cancellation — and every mechanism here points the other
way.

  floor A, by symptom   trivial-step share and search cost, and the boards high on one and low on the other
  floor B, by content   a board requiring nothing beyond column sums has nothing in it, whatever its chain

Do they catch the same boards? If they largely do it is one thing with two names, and B wins: "must
require the row identity" is clearer to state and to apply than a percentile on trivial steps.

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

from compressibility import proxies  # noqa: E402
from measure import Loaded, load  # noqa: E402

from boxscore_forge.constraints import cell_values, shape_of  # noqa: E402
from boxscore_forge.erasure import ORDERINGS, erasable  # noqa: E402
from boxscore_forge.identities import FAMILY_OF, Family, find_violations  # noqa: E402
from boxscore_forge.solver import solve  # noqa: E402

TARGETS = (5, 7, 9, 11)
EASY = (5, 7)
GATE = 0.25
SEEDS = (1, 2)
SAMPLE_PER_DECADE = 8
ORDERING = "row_first"

TUTORIAL_ORDER = (Family.COLUMN_SUM, Family.ROW_IDENTITY, Family.CROSS_TEAM, Family.GLOBAL_IDENTITY)
"""§8 teaches them in this order, and a teaching order is already a claim about relative difficulty."""

TUTORIAL_WEIGHTS = {family: position + 1 for position, family in enumerate(TUTORIAL_ORDER)}


@dataclass(frozen=True)
class Scored:
    target: int
    chain: int
    search: float | None
    resolution: int | None
    trivial: float
    zero_density: float
    families: frozenset[str]
    per_family: dict[str, int]
    bounding: int
    steps: int

    def hardest(self, weights: dict[Family, float]) -> float:
        """Sudoku's primary classifier: the hardest thing the board made the solver do."""
        present = [weights[family] for family in TUTORIAL_ORDER if family.value in self.families]
        return max(present) if present else 0.0

    def weighted_total(self, weights: dict[Family, float]) -> float:
        """The secondary number: the whole path, not only its peak."""
        return sum(weights[family] * self.per_family.get(family.value, 0) for family in TUTORIAL_ORDER)


def score(loaded: Loaded, seed: int) -> list[Scored]:
    direction = loaded.direction
    shape = shape_of(direction)
    values = cell_values(direction)
    rng = random.Random(seed)  # noqa: S311
    candidates = ORDERINGS[ORDERING](erasable(direction), direction, rng)
    density = proxies(loaded)["zero_density"]

    found: list[Scored] = []
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
            per_family: Counter[str] = Counter()
            for step in solution.deductions:
                if step.from_identity is not None:
                    per_family[FAMILY_OF[step.from_identity].value] += 1
            found.append(
                Scored(
                    target=target,
                    chain=solution.chain_length,
                    search=solution.ninetieth_percentile_search,
                    resolution=solution.ninetieth_percentile_resolution,
                    trivial=solution.trivial_share or 0.0,
                    zero_density=density,
                    families=frozenset(family.value for family in solution.families_used),
                    per_family=dict(per_family),
                    bounding=solution.bounding_steps,
                    steps=len(solution.deductions),
                )
            )
        if not wanted:
            break
    return found


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or statistics.pstdev(xs) == 0 or statistics.pstdev(ys) == 0:
        return float("nan")
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / len(xs)
    return covariance / (statistics.pstdev(xs) * statistics.pstdev(ys))


def co_occurrence_weights(boards: list[Scored]) -> dict[Family, float]:
    """What else is true of a board that needs this family — derived rather than chosen.

    The mean chain length of the boards requiring each family, scaled so the easiest sits at 1. If a
    family only appears on long solves, that is evidence it is hard, and evidence the tutorial order
    did not supply.
    """
    means: dict[Family, float] = {}
    for family in TUTORIAL_ORDER:
        chains = [float(board.chain) for board in boards if family.value in board.families]
        means[family] = statistics.fmean(chains) if chains else 0.0
    floor = min((value for value in means.values() if value), default=1.0) or 1.0
    return {family: round(value / floor, 2) for family, value in means.items()}


def report_weights(boards: list[Scored]) -> dict[Family, float]:
    derived = co_occurrence_weights(boards)
    print("\n=== TWO DERIVATIONS OF THE FAMILY WEIGHTS ===")
    print(f"{'family':>18}{'tutorial':>10}{'co-occurrence':>16}{'boards requiring it':>22}")
    for family in TUTORIAL_ORDER:
        requiring = sum(1 for board in boards if family.value in board.families)
        print(f"{family.value:>18}{TUTORIAL_WEIGHTS[family]:>10}{derived[family]:>16.2f}{requiring:>22}")
    agreement = _pearson(
        [float(TUTORIAL_WEIGHTS[family]) for family in TUTORIAL_ORDER],
        [derived[family] for family in TUTORIAL_ORDER],
    )
    print(f"\n  agreement between the two orderings: r = {agreement:+.3f}")
    print("  A disagreement says the tutorial order may not reflect real difficulty.")

    with_bounding = [board for board in boards if board.bounding]
    if with_bounding:
        share = statistics.fmean([board.bounding / max(board.steps, 1) for board in with_bounding])
        without = [float(board.chain) for board in boards if not board.bounding]
        print(f"\n  bounding: on {len(with_bounding)} of {len(boards)} boards, {share:.1%} of steps when used")
        if without:
            print(
                f"  chain {statistics.fmean([float(b.chain) for b in with_bounding]):.1f} with bounding "
                f"against {statistics.fmean(without):.1f} without"
            )
        print("  Proposal: a multiplier on the board's score rather than a fifth family weight —")
        print("  bounding can apply to any family, so scoring it as one of them double-counts.")
    return derived


def report_value(boards: list[Scored], derived: dict[Family, float]) -> None:
    print("\n=== DOES THE SCORE ADD ANYTHING ===")
    print(f"{'against':>20}{'hardest (tutorial)':>20}{'weighted (tutorial)':>21}{'weighted (derived)':>20}")
    hardest = [board.hardest(TUTORIAL_WEIGHTS) for board in boards]
    weighted = [board.weighted_total(TUTORIAL_WEIGHTS) for board in boards]
    weighted_derived = [board.weighted_total(derived) for board in boards]
    for name, values in (
        ("chain length", [float(b.chain) for b in boards]),
        ("search cost p90", [b.search if b.search is not None else 0.0 for b in boards]),
        ("resolution p90", [float(b.resolution or 0) for b in boards]),
        ("zero density", [b.zero_density for b in boards]),
        ("trivial share", [b.trivial for b in boards]),
    ):
        print(
            f"{name:>20}{_pearson(hardest, values):>20.3f}"
            f"{_pearson(weighted, values):>21.3f}{_pearson(weighted_derived, values):>20.3f}"
        )
    print("  A tight correlation with chain or zero density means it renames something already had.")

    print("\n=== DOES IT SEPARATE BOARDS THAT CHAIN LENGTH CALLS EQUIVALENT ===")
    print(f"{'chain':>7}{'boards':>8}{'distinct hardest':>18}{'weighted p10-p90':>20}")
    by_chain: dict[int, list[Scored]] = {}
    for board in boards:
        by_chain.setdefault(board.chain, []).append(board)
    for chain in sorted(by_chain):
        group = by_chain[chain]
        if len(group) < 10:
            continue
        values = sorted(board.weighted_total(TUTORIAL_WEIGHTS) for board in group)
        distinct = len({board.hardest(TUTORIAL_WEIGHTS) for board in group})
        span = f"{values[len(values) // 10]:.0f}-{values[9 * len(values) // 10]:.0f}"
        print(f"{chain:>7}{len(group):>8}{distinct:>18}{span:>20}")


def report_floors(boards: list[Scored]) -> None:
    easy = [board for board in boards if board.target in EASY]
    if not easy:
        return
    print(f"\n=== THE EASY END: {len(easy)} BOARDS AT CHAIN TARGETS {EASY} ===")
    trivial = sorted(board.trivial for board in easy)
    searches = sorted(board.search for board in easy if board.search is not None)
    print(
        f"  trivial share  p10 {trivial[len(trivial) // 10]:.2f}  p50 {statistics.median(trivial):.2f}"
        f"  p90 {trivial[9 * len(trivial) // 10]:.2f}  max {trivial[-1]:.2f}"
    )
    if searches:
        print(
            f"  search cost    p10 {searches[len(searches) // 10]:.2f}  p50 {statistics.median(searches):.2f}"
            f"  p90 {searches[9 * len(searches) // 10]:.2f}"
        )

    print("\n  FLOOR A, by symptom — high trivial and low search together:")
    print(f"{'trivial >=':>12}{'search <=':>11}{'boards':>9}{'share':>9}")
    failing_a: set[int] = set()
    for trivial_floor in (0.25, 0.35, 0.45):
        for search_floor in (0.40, 0.50, 0.60):
            caught = {
                index
                for index, board in enumerate(easy)
                if board.trivial >= trivial_floor
                and (board.search if board.search is not None else 1.0) <= search_floor
            }
            print(f"{trivial_floor:>12.2f}{search_floor:>11.2f}{len(caught):>9}{len(caught) / len(easy):>9.1%}")
            if (trivial_floor, search_floor) == (0.35, 0.50):
                failing_a = caught

    print("\n  FLOOR B, by content — what the board actually required:")
    only_columns = {i for i, b in enumerate(easy) if b.families <= {Family.COLUMN_SUM.value}}
    no_row = {i for i, b in enumerate(easy) if Family.ROW_IDENTITY.value not in b.families}
    print(f"    nothing beyond column sums        : {len(only_columns):>5}  ({len(only_columns) / len(easy):.1%})")
    print(f"    does not require the row identity : {len(no_row):>5}  ({len(no_row) / len(easy):.1%})")

    print("\n=== DO THE TWO FLOORS CATCH THE SAME BOARDS ===")
    print(f"  floor A (trivial >= 0.35 and search <= 0.50): {len(failing_a)}")
    print(f"  floor B (does not require the row identity) : {len(no_row)}")
    print(f"  both                                        : {len(failing_a & no_row)}")
    print(f"  only A                                      : {len(failing_a - no_row)}")
    print(f"  only B                                      : {len(no_row - failing_a)}")
    print("  Largely coinciding means one thing with two names, and B is the clearer statement.")


def render_easy(sample: list[Loaded]) -> None:
    from render_step import write_examples  # noqa: PLC0415

    out = _ROOT / "discovery" / "difficulty-weights" / "the-easy-end.html"
    count = write_examples(sample, out, target_chain=5, note=" - chain 5, the easy end")
    print(f"\n{count} boards from the easy end written to {out}")
    print("Look before trusting anything above: where does a gentle Monday stop being a puzzle?")


def main() -> None:
    loaded = load(SAMPLE_PER_DECADE, gated=True, gate=GATE)
    sample = [item for item in loaded if not find_violations(item.direction)]
    print(f"{len(sample)} gated directions, gate {GATE:.0%}, ordering {ORDERING!r}")
    print(f"decades: {dict(sorted(Counter((item.season // 10) * 10 for item in sample).items()))}")

    boards = [scored for item in sample for seed in SEEDS for scored in score(item, seed)]
    print(f"{len(boards)} scored boards across chain targets {TARGETS}")

    render_easy(sample)
    derived = report_weights(boards)
    report_value(boards, derived)
    report_floors(boards)


if __name__ == "__main__":
    main()
