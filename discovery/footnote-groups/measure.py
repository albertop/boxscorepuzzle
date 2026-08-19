"""Is an unassigned footnote resolvable? Three separate questions, per group size and term count.

⚠️ **Stall count says how often a player has to think. It does not say whether the thing to think
about can be resolved.** Those are different problems and only the second can leave a board
underivable, which §22 forbids.

⚠️ **The first version of this could not observe two of the three things it reported**, and one of its
numbers was read as a finding before that was noticed. Both faults are worth stating, because the shape
recurs:

  `had_to_resolve` was **structurally impossible.** It hid one slot group's footnote cells and left
  every other cell given, so every cell the solver deduced was one of the hidden ones and no later
  deduction could depend on them. The column read `0%` everywhere and was reported as *the assignment
  never blocks the rest of the board* — a metric with one possible value, presented as though it had
  two. It is measured on a **real erased puzzle** now, where other unknowns exist to wait on it.

  `unique` **conflated two questions.** It was true when the restricted human solver finished *and*
  reproduced the hidden values, so false meant either several assignments exist or one exists and
  propagation-plus-bounding did not reach it. Those are different findings with different fixes:
  several assignments is a generator constraint, one-but-underivable is a technique or a hint. They are
  two axes here — **completions** counted by the verifier's enumerator at `limit=2`, and **derivability**
  by the restricted solver.

**Nothing is aggregated.** If solvability falls with group size or term count, *where* it falls is the
finding, and "three or more" destroys it. The one-row cells are the control at a **fixed** term count:
one row with two terms is not ambiguous at all, so if those resolve and two-row two-term groups do not,
the difficulty is the assignment rather than carrying several terms.

Read-only against DGL. Run from `forge/`.
"""

import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))

from measure import Loaded, load  # noqa: E402

from boxscore_forge.constraints import cell_values, footnote_cell, shape_of  # noqa: E402
from boxscore_forge.erasure import erase  # noqa: E402
from boxscore_forge.identities import FOOTNOTE_COLUMNS, find_violations  # noqa: E402
from boxscore_forge.publish import to_board  # noqa: E402
from boxscore_forge.solver import solve  # noqa: E402
from boxscore_verify.reason import solutions  # noqa: E402
from boxscore_verify.rules import all_cells, relations, values_of  # noqa: E402

SAMPLE_PER_DECADE = 20
GATE = 0.25
SEEDS = (907, 908, 909)
"""⚠️ **One erasure per board is one sample, not a rate.** Whether a group gates progress depends
on which cells are blank, and the erasure decides that — so a single seed makes every board
contribute one observation while the report presents a population share.

Third instance of this shape today: the stall ceiling from one greedy path, and open-against-given
from one ordering. Both were corrected by searching several and reporting the spread. This is the
same correction applied **before** the run rather than after the number had been believed.

**Only blockage needs it.** Completions and derivability are measured on the complete board with
the group hidden, no erasure involved, so they cannot move with the seed."""

TARGET_STALLS = 8
COLUMNS = (0, 1, 2, 3, "4+")


@dataclass(frozen=True)
class Group:
    """One slot group on one board, with the three questions kept apart."""

    rows: int
    terms: int
    completions: int
    """How many ways the board can be completed with the group's footnotes unknown, counted to 2.
    One is unique; two means the assignment is genuinely ambiguous and no technique can fix it."""

    derivable: bool
    trials: int = 0
    stopped: int = 0
    """Whether the restricted human solver reaches the values. Only meaningful when there is exactly
    one completion — otherwise there is nothing to reach."""

    blocked: bool | None
    """Whether hiding the assignment **stops** outside progress. `None` when the trial could not be
    measured because no erasure reached the target.

    ⚠️ **Counterfactual, not observed dependency.** The first version marked a group blocking when some
    deduction outside it recorded a dependency on it. That is evidence one solver path *used* the
    value, not that the board had to wait: when hiding the group prevents an outside deduction
    entirely, no such step exists and the metric said `False` — a false negative for the strongest
    possible blockage. It compares two closures now, the same puzzle with the group available and with
    it additionally hidden, and blockage is an outside cell the baseline reaches and the treatment
    does not.

    ⚠️ **And `None` is not `False`.** A trial where `erase` returned nothing used to become an empty
    erasure and therefore a measured negative, which biases the rate downward — selectively, since
    boards that resist erasure are not a random subset."""

    used: bool
    """Whether any outside deduction leaned on the group. Kept as its own reading rather than folded
    into blockage: using a value and needing it are different claims."""


def _hidden_cells(indexes: list[int]) -> set[str]:
    return {footnote_cell(index, column) for index in indexes for column in FOOTNOTE_COLUMNS}


def groups_in(loaded: Loaded) -> list[Group]:
    direction = loaded.direction
    shape, values = shape_of(direction), cell_values(direction)
    by_slot: dict[int, list[int]] = defaultdict(list)
    for index, slot in enumerate(loaded.slots):
        by_slot[slot].append(index)

    # ⚠️ A real erasure, so `blocked` has other unknowns to be waited on by. Without it that metric
    # cannot be true, which is exactly how it came to read 0% everywhere.
    drawn = [erase(direction, target_stalls=TARGET_STALLS, seed=seed) for seed in SEEDS]
    erasures = [puzzle.erased for puzzle in drawn if puzzle is not None]

    found: list[Group] = []
    for indexes in by_slot.values():
        terms = sum(
            getattr(direction.batter_footnotes[index], column) for index in indexes for column in FOOTNOTE_COLUMNS
        )
        hidden = _hidden_cells(indexes)

        # Axis one: how many completions exist at all. The verifier's enumerator, not the solver —
        # cardinality is a property of the board and derivability is a property of a technique.
        board = to_board(direction, frozenset(hidden))
        completions = len(solutions(relations(board), all_cells(board), values_of(board), limit=2))

        # Axis two: whether the restricted solver reaches them.
        solution = solve(shape, {name: value for name, value in values.items() if name not in hidden})
        derivable = solution.is_complete and all(solution.values.get(cell) == values[cell] for cell in hidden)

        # Axis three: the counterfactual. What the board reaches with the assignment available,
        # against what it reaches without it. A cell the baseline settles and the treatment does not
        # is progress the group was gating.
        blocked: bool | None = None
        used = False
        stopped = 0
        for erased in erasures:
            given = {name: value for name, value in values.items() if name not in erased}
            baseline = solve(shape, given)
            treatment = solve(shape, {k: v for k, v in given.items() if k not in hidden})
            before = {cell for cell in baseline.values if cell not in hidden}
            after = {cell for cell in treatment.values if cell not in hidden}
            stopped += bool(before - after)
            used = used or any(
                hidden & step.depends_on for step in treatment.deductions if step.cell not in hidden
            )
        if erasures:
            # ⚠️ **Any** erasure that stops progress makes the group a gate, not a majority of them.
            # A board a player can meet is a board that can be dealt, so the question is whether an
            # unfair one exists, not whether it is typical. `trials` and `stopped` carry the spread.
            blocked = stopped > 0

        found.append(
            Group(
                rows=len(indexes),
                terms=terms,
                completions=completions,
                derivable=derivable,
                blocked=blocked,
                used=used,
                trials=len(erasures),
                stopped=stopped,
            )
        )
    return found


def _label(terms: object) -> str:
    return f"{terms} terms" if terms != 1 else "1 term"


def _cohort(cells: dict, rows: int, terms: object) -> list[Group]:
    if terms == "4+":
        return [g for key, here in cells.items() if key[0] == rows and key[1] >= 4 for g in here]  # noqa: PLR2004
    return cells.get((rows, terms), [])


def _eligible(title: str, group: Group) -> bool:
    """Which groups belong in a question's denominator."""
    if title.startswith("DERIVABLE"):
        return group.completions == 1
    if title.startswith("HIDING"):
        return group.blocked is not None
    return True


def report(groups: list[Group], boards: int) -> None:
    cells: dict[tuple[int, int], list[Group]] = defaultdict(list)
    for group in groups:
        cells[(group.rows, group.terms)].append(group)
    rows_seen = sorted({group.rows for group in groups})
    header = f"{'rows':>5}" + "".join(f"{_label(t):>16}" for t in COLUMNS)

    for title, note, measure in (
        ("EXACTLY ONE COMPLETION", "the board's own answer: is the assignment ambiguous at all",
         lambda g: g.completions == 1),
        ("DERIVABLE, AMONG THOSE WITH ONE COMPLETION",
         "conditional: the denominator is the unique groups, not every group",
         lambda g: g.derivable),
        ("HIDING IT STOPS OUTSIDE PROGRESS", "counterfactual, and unmeasured trials are excluded",
         lambda g: g.blocked),
        ("SOME OUTSIDE DEDUCTION USED IT", "a weaker claim than blocking, kept separate on purpose",
         lambda g: g.used),
    ):
        print("")
        print(f"=== {title} ===")
        print(f"  {note}")
        print(header)
        for rows in rows_seen:
            line = f"{rows:>5}"
            for terms in COLUMNS:
                # ⚠️ Each question keeps only the population it is about: derivability is conditional
                # on a single completion, and blockage excludes trials that could not be measured.
                # The old table used every group as the denominator for all three.
                here = [g for g in _cohort(cells, rows, terms) if _eligible(title, g)]
                line += f"{f'{sum(1 for g in here if measure(g)) / len(here):.0%} [{len(here)}]' if here else '-':>16}"
            print(line)

    print("")
    print("=== AMBIGUOUS RATHER THAN MERELY HARD ===")
    print("  More than one completion is a generator constraint; one completion the solver misses is a")
    print("  technique question. The old instrument called both 'not uniquely solvable'.")
    many = [g for g in groups if g.completions > 1]
    missed = [g for g in groups if g.completions == 1 and not g.derivable]
    print(f"  several completions: {len(many)}   one completion the solver did not reach: {len(missed)}")
    for group in sorted(many, key=lambda g: (-g.rows, -g.terms))[:6]:
        print(f"    {group.rows} rows, {group.terms} terms")

    print("")
    print("=== THE CONTROL, AT A FIXED TERM COUNT ===")
    for terms in (2, 3):
        one = _cohort(cells, 1, terms)
        two = _cohort(cells, 2, terms)
        if one and two:
            print(f"  {terms} terms: one row {sum(g.completions == 1 for g in one) / len(one):.0%} unique "
                  f"[{len(one)}], two rows {sum(g.completions == 1 for g in two) / len(two):.0%} [{len(two)}]")
        else:
            print(f"  {terms} terms: one row [{len(one)}], two rows [{len(two)}] — too few to compare")
    print(f"\n({len(groups)} slot groups from {boards} boards)")


def stamp(boards: int, groups: int) -> str:
    """What produced this file, in the file.

    ⚠️ **A results file with no provenance cannot be told from a stale one.** The version this
    replaced left an output on disk from an instrument whose blockage metric could not vary;
    nothing inside it said so, and nothing inside a good run would have said that either.
    """
    revision = "unknown"
    head = _ROOT / ".git" / "HEAD"
    if head.exists():
        ref = head.read_text(encoding="utf-8").strip()
        target = _ROOT / ".git" / ref.removeprefix("ref: ") if ref.startswith("ref:") else None
        revision = target.read_text(encoding="utf-8").strip()[:12] if target and target.exists() else ref[:12]
    lines = [
        "=== WHAT PRODUCED THIS ===",
        "  result schema      2   (1 was the instrument whose blockage metric could not vary)",
        f"  revision           {revision}",
        f"  sample             {boards} directions, {SAMPLE_PER_DECADE} per decade, gate {GATE:.0%}",
        f"  erasure seeds      {SEEDS} at {TARGET_STALLS} stalls",
        f"  groups             {groups}",
        "  blockage           counterfactual, any erasure that stops outside progress",
        "  derivability       conditional on exactly one completion",
    ]
    return chr(10).join(lines)

def main() -> None:
    sample = [
        item
        for item in load(SAMPLE_PER_DECADE, gated=True, gate=GATE, max_batters=13, max_pitchers=4)
        if not find_violations(item.direction)
    ]
    if not sample:
        raise SystemExit(f"no directions survived the {GATE:.0%} gate")
    print(f"{len(sample)} gated directions", flush=True)

    groups: list[Group] = []
    for number, item in enumerate(sample, start=1):
        groups.extend(groups_in(item))
        if number % 20 == 0:
            print(f"  {number}/{len(sample)} boards, {len(groups)} groups", flush=True)
    if not groups:
        raise SystemExit("no slot groups were produced; the sample carried no lineups")
    report(groups, len(sample))
    print("")
    print(stamp(len(sample), len(groups)))


if __name__ == "__main__":
    main()
