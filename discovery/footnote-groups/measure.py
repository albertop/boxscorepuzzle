"""Is an unassigned footnote resolvable? Three separate questions, per group size and term count.

⚠️ **Stall count says how often a player has to think. It does not say whether the thing to think
about can be resolved.** Different problems, and only the second can leave a board underivable, which
§22 forbids.

⚠️ **This instrument has been wrong three times, in three different ways, and each fault made a number
look like a finding.** They are worth stating because the shape recurs rather than the bug:

  **A metric that could not vary.** Blockage hid the group and left every other cell given, so every
  deduction was a hidden cell and nothing could depend on them. It read `0%` on every board and was
  reported as *the assignment never blocks the rest of the board*.

  **A metric that could not fire where it mattered.** The counterfactual's baseline removed every cell
  in `erased`, and footnote cells **are** erasable — so when the sampled erasure had already hidden the
  group, baseline and treatment were the same board. Blockage was forced false on exactly the published
  states the question is about.

  **Denominators that did not match their questions.** Derivability counted ambiguous groups as
  failures, unmeasured trials counted as negatives, and which population a table used was decided by
  the *title string* of its heading.

What follows from that is the shape of this file: the measurements are pure functions in `metrics.py`
so a test can call the production predicate, and each row of the report carries its own eligibility
rule as a callable rather than inferring one from display copy.

Read-only against DGL. Run from `forge/`.
"""

import contextlib
import hashlib
import io
import os
import secrets
import subprocess
import sys
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))

from measure import Loaded, load  # noqa: E402
from metrics import completions, derivable, stops_progress, uses_the_group  # noqa: E402

from boxscore_forge.constraints import cell_values, footnote_cell, shape_of  # noqa: E402
from boxscore_forge.erasure import erase  # noqa: E402
from boxscore_forge.identities import FOOTNOTE_COLUMNS, find_violations  # noqa: E402
from boxscore_forge.publish import to_board  # noqa: E402

SAMPLE_PER_DECADE = 20
GATE = 0.25
SEEDS = (907, 908, 909)
"""⚠️ **One erasure per board is one sample, not a rate.** Whether a group gates progress depends on
which cells are blank, and the erasure decides that. Third instance of that shape, after the stall
ceiling from one greedy path and open-against-given from one ordering — and the first corrected before
the number had been believed rather than after.

**Only blockage needs them.** Completions and derivability are read off the complete board with the
group hidden, so they cannot move with the seed."""

TARGET_STALLS = 8
COLUMNS = (0, 1, 2, 3, "4+")
RESULT_SCHEMA = 3
"""1 could not vary, 2 could not fire where it mattered. A reader of an old file needs to know which."""


@dataclass(frozen=True)
class Group:
    """One slot group on one board. Every field is a separate question."""

    rows: int
    terms: int
    completions: int
    derivable: bool
    trials: int
    """Erasures that reached the target. Zero means **unmeasured**, which is not the same as negative:
    a board that resists erasure is not a random draw, so counting it as a negative biases the rate
    downward and selectively."""

    stopped: int
    used: int


@dataclass(frozen=True)
class Coverage:
    """Run-level accounting, which is not the same as the group-trial denominator.

    ⚠️ **`erase` is called once per direction and seed, before the direction becomes slot groups.**
    Reporting `len(groups) * len(SEEDS)` as *erasures attempted* counted group-erasure evaluations,
    and summing `group.trials` reported one successful erasure once per group on its board — so a
    direction with nine groups claimed nine successes for one call. The repeated count is the right
    denominator for a per-group per-erasure rate and the wrong measure of how often the eraser worked.
    """

    directions: int = 0
    attempted: int = 0
    reached: int = 0

    def plus(self, attempted: int, reached: int) -> "Coverage":
        return Coverage(self.directions + 1, self.attempted + attempted, self.reached + reached)


def groups_in(loaded: Loaded) -> tuple[list[Group], int]:
    direction = loaded.direction
    shape, values = shape_of(direction), cell_values(direction)
    by_slot: dict[int, list[int]] = defaultdict(list)
    for index, slot in enumerate(loaded.slots):
        by_slot[slot].append(index)

    drawn = [erase(direction, target_stalls=TARGET_STALLS, seed=seed) for seed in SEEDS]
    erasures = [puzzle.erased for puzzle in drawn if puzzle is not None]

    found: list[Group] = []
    for indexes in by_slot.values():
        terms = sum(
            getattr(direction.batter_footnotes[index], column) for index in indexes for column in FOOTNOTE_COLUMNS
        )
        hidden = frozenset(footnote_cell(index, column) for index in indexes for column in FOOTNOTE_COLUMNS)
        found.append(
            Group(
                rows=len(indexes),
                terms=terms,
                completions=completions(to_board(direction, hidden)),
                derivable=derivable(shape, values, hidden),
                trials=len(erasures),
                stopped=sum(stops_progress(shape, values, erased, hidden) for erased in erasures),
                used=sum(uses_the_group(shape, values, erased, hidden) for erased in erasures),
            )
        )
    return found, len(erasures)


@dataclass(frozen=True)
class Row:
    """One question: which groups it is about, and what it counts.

    ⚠️ **Eligibility is a callable, not a string test on the heading.** It used to be inferred from
    whether the title began with `DERIVABLE` or `HIDING`, so renaming a heading silently restored the
    unconditional denominator. Display copy deciding statistics is the same defect as formatting
    deciding a domain rule, which this project has already had three times.
    """

    title: str
    note: str
    eligible: Callable[[Group], bool]
    numerator: Callable[[Group], int]
    denominator: Callable[[Group], int]


ROWS = (
    Row(
        "EXACTLY ONE COMPLETION",
        "is the assignment ambiguous at all — a property of the board, not of a technique",
        lambda _: True,
        lambda group: int(group.completions == 1),
        lambda _: 1,
    ),
    Row(
        "DERIVABLE, AMONG THOSE WITH ONE COMPLETION",
        "conditional: ambiguous groups are not failures of the solver and are not counted as such",
        lambda group: group.completions == 1,
        lambda group: int(group.derivable),
        lambda _: 1,
    ),
    Row(
        "TRIALS WHERE HIDING IT STOPPED OUTSIDE PROGRESS",
        "per trial, not per group: exposure varies because not every seed reaches the target",
        lambda group: group.trials > 0,
        lambda group: group.stopped,
        lambda group: group.trials,
    ),
    Row(
        "TRIALS WHERE SOME OUTSIDE DEDUCTION USED IT",
        "a weaker claim than blocking, on the same denominator so the two can be compared",
        lambda group: group.trials > 0,
        lambda group: group.used,
        lambda group: group.trials,
    ),
)


def _cohort(cells: dict, rows: int, terms: object) -> list[Group]:
    if terms == "4+":
        return [g for key, here in cells.items() if key[0] == rows and key[1] >= 4 for g in here]  # noqa: PLR2004
    return cells.get((rows, terms), [])


def report(groups: list[Group], coverage: "Coverage") -> None:
    cells: dict[tuple[int, int], list[Group]] = defaultdict(list)
    for group in groups:
        cells[(group.rows, group.terms)].append(group)
    seen = sorted({group.rows for group in groups})
    header = f"{'rows':>5}" + "".join(f"{f'{t} terms' if t != 1 else '1 term':>18}" for t in COLUMNS)

    for row in ROWS:
        print("")
        print(f"=== {row.title} ===")
        print(f"  {row.note}")
        print(header)
        for rows in seen:
            line = f"{rows:>5}"
            for terms in COLUMNS:
                here = [g for g in _cohort(cells, rows, terms) if row.eligible(g)]
                over = sum(row.denominator(g) for g in here)
                under = sum(row.numerator(g) for g in here)
                line += f"{f'{under / over:.0%} [{under}/{over}]' if over else '-':>18}"
            print(line)

    print("")
    print("=== COVERAGE, SO THE DENOMINATORS CAN BE READ ===")
    print(f"  erasures: {coverage.attempted} attempted over {coverage.directions} directions, "
          f"{coverage.reached} reached {TARGET_STALLS} stalls")
    print(f"  group-erasure trials: {sum(g.trials for g in groups)} — the blockage denominator, which")
    print("    repeats each successful erasure once per group on its board and is not an eraser count")
    print(f"  groups with no successful erasure: {sum(1 for g in groups if g.trials == 0)} — excluded")
    print(f"  ambiguous groups (more than one completion): {sum(1 for g in groups if g.completions > 1)}")
    print(f"  {len(groups)} slot groups from {coverage.directions} directions")

    print("")
    print("=== THE CONTROL, AT A FIXED TERM COUNT ===")
    print("  One row with two terms is not ambiguous at all. Comparing `>= 2` against `>= 2` mixed")
    print("  populations of different composition, so a difference could be volume or assignment.")
    for terms in (2, 3):
        one, two = _cohort(cells, 1, terms), _cohort(cells, 2, terms)
        if one and two:
            print(
                f"  {terms} terms: one row {sum(g.completions == 1 for g in one) / len(one):.0%} unique "
                f"[{len(one)}], two rows {sum(g.completions == 1 for g in two) / len(two):.0%} [{len(two)}]"
            )
        else:
            print(f"  {terms} terms: one row [{len(one)}], two rows [{len(two)}] — too few to compare")


def _git(*arguments: str) -> str:
    """Git output, or `unknown`. `unknown` is not publishable — see `main`."""
    try:
        return subprocess.run(  # noqa: S603
            ["git", "-C", str(_ROOT), *arguments],  # noqa: S607
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def source_hashes() -> str:
    """A digest of the code that actually decides, so a revision is not the only identity.

    A commit says what was committed. These say what ran — including files git has never heard of,
    which is the gap `--dirty` leaves open.
    """
    digest = hashlib.sha256()
    for path in sorted((_HERE / "measure.py", _HERE / "metrics.py")):
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def provenance(coverage: "Coverage", groups: int, trials: int) -> str:
    """What produced this file, including whether the tree was clean.

    ⚠️ **A commit alone does not identify the code that ran.** The version this replaces read
    `.git/HEAD` and a loose ref, which is wrong for a packed ref or a worktree, and said nothing about
    uncommitted edits — so an edited instrument was labelled with the previous commit. `git describe`
    through the repository answers all three, and `--dirty` is the part that matters.
    """
    described = _git("describe", "--always", "--dirty=+uncommitted")
    # ⚠️ **`--dirty` does not see untracked files.** An untracked `metrics.py` or query helper changes
    # the result while the revision reads clean, which is the failure this stamp exists to prevent.
    untracked = _git("status", "--porcelain", "--untracked-files=all")
    if untracked and untracked != "unknown":
        described = f"{described} +untracked({len(untracked.splitlines())} files)"
    return "\n".join(
        [
            "=== WHAT PRODUCED THIS ===",
            f"  result schema      {RESULT_SCHEMA}   (1 could not vary; 2 could not fire where it mattered)",
            f"  revision           {described}",
            f"  instrument         sha256 {source_hashes()}   (measure.py and metrics.py as they ran)",
            f"  sample             {coverage.directions} directions, {SAMPLE_PER_DECADE} per decade, gate {GATE:.0%}",
            f"  erasures           {SEEDS} per direction; {coverage.reached} of {coverage.attempted} reached "
        f"{TARGET_STALLS} stalls",
        f"  group trials       {trials}   (each successful erasure once per group on its board)",
            f"  groups             {groups}",
            "  blockage           counterfactual, per trial; the baseline restores the group whatever",
            "                     the erasure did to it, so the only difference is the assignment",
            "  derivability       conditional on exactly one completion",
            "COMPLETE",
        ]
    )


def main() -> None:
    out = Path(sys.argv[sys.argv.index("--output") + 1]) if "--output" in sys.argv else _HERE / "results.txt"
    sample = [
        item
        for item in load(SAMPLE_PER_DECADE, gated=True, gate=GATE, max_batters=13, max_pitchers=4)
        if not find_violations(item.direction)
    ]
    if not sample:
        raise SystemExit(f"no directions survived the {GATE:.0%} gate")
    print(f"{len(sample)} gated directions", flush=True)

    groups: list[Group] = []
    coverage = Coverage()
    for number, item in enumerate(sample, start=1):
        found, reached = groups_in(item)
        groups.extend(found)
        coverage = coverage.plus(len(SEEDS), reached)
        if number % 20 == 0:
            print(f"  {number}/{len(sample)} boards, {len(groups)} groups", flush=True)
    if not groups:
        raise SystemExit("no slot groups were produced; the sample carried no lineups")

    # ⚠️ The instrument owns its artifact. Shell redirection leaves a partial file at the canonical
    # path when a run is interrupted, and a partial file with no completion marker still occupies the
    # name a decision gets read from. Written aside and replaced, with `COMPLETE` as the last line.
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        report(groups, coverage)
        print("")
        print(provenance(coverage, len(groups), sum(group.trials for group in groups)))
    text = captured.getvalue()
    if "revision           unknown" in text:
        # Fail closed. A result that cannot say what produced it is worse than no result, because it
        # occupies the name a decision gets read from.
        message = "git could not identify the revision; refusing to publish a result with no provenance"
        raise SystemExit(message)
    print(text)
    # ⚠️ **A fixed staging name is not a single-writer contract.** An atomic final rename protects the
    # destination and not the preparation: two overlapping runs sharing `results.txt.pending` can
    # truncate each other, or one can move the other's bytes into the canonical path. This is the same
    # class already removed from the reference publisher, and a long run makes a duplicate launch
    # operationally plausible rather than a timing curiosity.
    pending = out.with_name(f"{out.name}.pending-{os.getpid()}-{secrets.token_hex(4)}")
    try:
        pending.write_text(text, encoding="utf-8")
        pending.replace(out)
    finally:
        pending.unlink(missing_ok=True)
    print(f"written to {out}")


if __name__ == "__main__":
    main()
