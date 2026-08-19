"""Was opening the footnote cells ever worth anything, once the zeros are excluded?

⚠️ **This is a correction, not a new result.** The measurement that opened these cells reported the
median board going from 5 stalls to 15. It did — the solver deduced every erased footnote value,
correctly, and recorded each as a step. But when `HBP`, `SF`, `SH` and `CI` are all zero for a batter
the row identity is `PA = AB + BB`: those terms contribute nothing *because they did not happen*. On the
reference fixture **35 of 36 footnote cells are zero**. The solver stalled sixteen times filling in
zeros and a person never met one.

It was found by the operator solving a 19-stall board with the footnote line visible and finding it hard
— so the difficulty was there without them. No test could have caught it: the instrument was working and
pointed at the wrong thing.

**On one board, three treatments with the same seeds, the answer was already stark:**

| treatment | candidates | ceiling per seed |
|---|---:|---|
| footnotes fully erasable | 110 | 14, 17, 14 |
| erasable only where non-zero | 75 | 7, 9, 1 |
| footnotes given entirely | 74 | 7, 9, 1 |

The last two are identical. This runs the same comparison across the pool, because one board — and one
whose footnote line is nearly empty — decides nothing.

⚠️ **How the ordering is kept stable, stated at the point of comparison.** The three arms have different
candidate lists. Ordering each separately would let them differ in *trajectory* as well as *treatment*,
which is the confound this project has produced twice and which **has no signature in the output** — it
cannot be caught by reading the numbers afterwards, only prevented here. So one canonical walk is
computed per `(direction, seed)` **over the union**, and each arm takes that same walk **filtered**.

⚠️ **Coverage at fixed targets rather than a searched ceiling.** A ceiling found by scanning assumes a
board that fails at `t` also fails at `t+1`, which nothing here establishes. Coverage is what the
question actually asks and it needs no such assumption.

Read-only against DGL. Run from `forge/`.
"""

import contextlib
import io
import json
import os
import random
import secrets
import statistics
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

NL = chr(10)
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))

from measure import load  # noqa: E402

from boxscore_forge import erasure  # noqa: E402
from boxscore_forge.constraints import (  # noqa: E402
    batting_cell,
    batting_total_cell,
    cell_values,
    footnote_cell,
    pitching_cell,
    pitching_total_cell,
    shape_of,
)
from boxscore_forge.identities import BATTING_COLUMNS, FOOTNOTE_COLUMNS, PITCHING_COLUMNS, find_violations  # noqa: E402

SAMPLE_PER_DECADE = 6
GATE = 0.25
SEEDS = (301, 302)
TARGETS = (5, 8, 11, 15, 19)
"""5 is the figure the old measurement said only 56% of boards reached with footnotes given; the rest
are the ladder's rungs, which are stall counts and therefore inherit the error."""

RESULT_SCHEMA = 1
EXAMPLES = 6
"""How many differing pairs to print. A distribution also produces examples checked by eye."""
ARMS = ("all", "non_zero", "given")


@dataclass(frozen=True, slots=True)
class Row:
    game: str
    seed: int
    target: int
    arm: str
    reached: bool
    blanks: int
    chain: int
    stalls: int
    footnote_blanks: int


def _grid(direction: object) -> list[str]:
    """Everything except the footnote cells, which are what the arms differ on."""
    shape = shape_of(direction)
    cells = [batting_cell(i, c) for i in range(shape.batter_count) for c in BATTING_COLUMNS]
    cells += [batting_total_cell(c) for c in BATTING_COLUMNS]
    cells += [pitching_cell(i, c) for i in range(shape.pitcher_count) for c in PITCHING_COLUMNS]
    cells += [pitching_total_cell(c) for c in PITCHING_COLUMNS]
    return sorted(set(cells) - set(erasure.SCOREBOARD_DUPLICATES))


def _footnotes(direction: object) -> list[str]:
    shape = shape_of(direction)
    return [footnote_cell(i, c) for i in range(shape.batter_count) for c in FOOTNOTE_COLUMNS]


def _candidates(direction: object, arm: str) -> set[str]:
    values = cell_values(direction)
    cells = set(_grid(direction))
    if arm == "all":
        return cells | set(_footnotes(direction))
    if arm == "non_zero":
        return cells | {name for name in _footnotes(direction) if values[name] != 0}
    return cells


def walks(direction: object, seed: int) -> dict[str, list[str]]:
    """One canonical order over the union, filtered per arm.

    ⚠️ **Extracted so a test can call it.** It lived inside `_measure`, tangled with `erase`, so the only
    way to check it was to re-implement the filtering in the test — which then passed while the
    instrument reordered each arm separately. A guard that rebuilds what it is guarding is testing
    itself, and this project has produced that nine times now.
    """
    union = sorted(set(_grid(direction)) | set(_footnotes(direction)))
    order = erasure.ORDERINGS[erasure.DEFAULT_ORDERING](union, direction, random.Random(seed))  # noqa: S311
    return {arm: [cell for cell in order if cell in _candidates(direction, arm)] for arm in ARMS}


def _measure(direction: object, game: str, seed: int, erase: object = None) -> list[Row]:
    """`erase` is injectable so a test can drive the row-building without a real board."""
    erase = erase or erasure.erase
    by_arm = walks(direction, seed)

    rows: list[Row] = []
    for arm in ARMS:
        walk = by_arm[arm]
        original_erasable, original_orderings = erasure.erasable, dict(erasure.ORDERINGS)
        erasure.erasable = lambda _direction, _cells=walk: list(_cells)
        erasure.ORDERINGS = dict(original_orderings)
        erasure.ORDERINGS[erasure.DEFAULT_ORDERING] = lambda cells, _direction, _rng: list(cells)
        try:
            for target in TARGETS:
                puzzle = erase(direction, target_stalls=target, seed=seed)
                rows.append(
                    Row(
                        game=game,
                        seed=seed,
                        target=target,
                        arm=arm,
                        reached=puzzle is not None,
                        blanks=len(puzzle.erased) if puzzle else 0,
                        chain=puzzle.solution.chain_length if puzzle else 0,
                        stalls=puzzle.solution.stalls if puzzle else 0,
                        footnote_blanks=len([c for c in puzzle.erased if c.startswith("footnotes")]) if puzzle else 0,
                    )
                )
        finally:
            erasure.erasable, erasure.ORDERINGS = original_erasable, original_orderings
    return rows


LABEL = {"all": "footnotes fully erasable", "non_zero": "erasable if non-zero", "given": "footnotes given"}


def report(rows: list[Row]) -> None:
    trials = {(r.game, r.seed) for r in rows}
    print("=== COVERAGE: SHARE OF BOARD-AND-SEED TRIALS THAT REACH EACH TARGET ===")
    print("  the question the 5-versus-15 figure was really answering")
    print(f"{'target':>8}" + "".join(f"{LABEL[a]:>28}" for a in ARMS))
    for target in TARGETS:
        cells = []
        for arm in ARMS:
            at = [r for r in rows if r.target == target and r.arm == arm]
            reached = sum(r.reached for r in at)
            cells.append(f"{reached}/{len(at)} = {reached / len(at):.0%}" if at else "-")
        print(f"{target:>8}" + "".join(f"{c:>28}" for c in cells))

    print("")
    print("=== ⚠️ THE ONE THAT SETTLES IT: NON-ZERO AGAINST GIVEN, PAIR BY PAIR ===")
    print("  if these two are the same, opening the footnote cells buys nothing and they go back to given")
    same = differ = 0
    examples = []
    for game, seed in sorted(trials):
        for target in TARGETS:
            here = [r for r in rows if r.game == game and r.seed == seed and r.target == target]
            a = next((r for r in here if r.arm == "non_zero"), None)
            b = next((r for r in here if r.arm == "given"), None)
            if a is None or b is None:
                continue
            if (a.reached, a.stalls, a.chain, a.blanks) == (b.reached, b.stalls, b.chain, b.blanks):
                same += 1
            else:
                differ += 1
                if len(examples) < EXAMPLES:
                    examples.append(
                        f"  {game} seed {seed} target {target}: "
                        f"non-zero {a.reached} {a.stalls}st {a.blanks}b  vs  given {b.reached} {b.stalls}st {b.blanks}b"
                    )
    total = same + differ
    print(f"  identical on every field: {same}/{total} = {same / total:.0%}" if total else "  no pairs")
    print(f"  differing:                {differ}/{total} = {differ / total:.0%}" if total else "")
    for line in examples:
        print(line)

    print("")
    print("=== WHAT A REACHED BOARD LOOKS LIKE, PER ARM ===")
    print(f"{'arm':>28}{'reached':>10}{'median blanks':>16}{'median chain':>15}{'median footnote blanks':>24}")
    for arm in ARMS:
        got = [r for r in rows if r.arm == arm and r.reached]
        if not got:
            print(f"{LABEL[arm]:>28}{0:>10}{'-':>16}{'-':>15}{'-':>24}")
            continue
        print(
            f"{LABEL[arm]:>28}{len(got):>10}"
            f"{statistics.median([r.blanks for r in got]):>16g}"
            f"{statistics.median([r.chain for r in got]):>15g}"
            f"{statistics.median([r.footnote_blanks for r in got]):>24g}"
        )

    print("")
    print("=== A HANDFUL OF TRIALS, RENDERED RATHER THAN SUMMARISED ===")
    for game, seed in sorted(trials)[:4]:
        for arm in ARMS:
            got = [r for r in rows if r.game == game and r.seed == seed and r.arm == arm and r.reached]
            highest = max((r.target for r in got), default=0)
            print(f"  {game} seed {seed} {LABEL[arm]:>28}: highest target reached {highest}")


def _git(*arguments: str) -> str:
    try:
        return subprocess.run(  # noqa: S603
            ["git", "-C", str(_ROOT), *arguments],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return "unknown"


def provenance(directions: int, rows: int) -> str:
    dirty = _git("status", "--porcelain", "--untracked-files=all")
    return NL.join(
        [
            "=== WHAT PRODUCED THIS ===",
            f"  result schema      {RESULT_SCHEMA}",
            f"  revision           {_git('rev-parse', '--short', 'HEAD')}",
            f"  tree               {'clean' if dirty == '' else f'{len(dirty.splitlines())} files dirty'}",
            f"  sample             {directions} directions, {SAMPLE_PER_DECADE} per decade, gate {GATE:.0%}",
            f"  seeds              {SEEDS}; targets {TARGETS}; arms {ARMS}",
            f"  rows               {rows}",
            "  ordering           one canonical walk per (direction, seed) over the union, filtered per",
            "                     arm, so every shared cell keeps its relative position",
            "  coverage           measured at fixed targets, not searched, so no monotonicity is assumed",
            "COMPLETE",
        ]
    )


def main() -> None:
    sample = [
        item
        for item in load(SAMPLE_PER_DECADE, gated=True, gate=GATE, max_batters=13, max_pitchers=4)
        if not find_violations(item.direction)
    ]
    if not sample:
        message = f"no directions survived the {GATE:.0%} gate"
        raise SystemExit(message)
    print(f"{len(sample)} gated directions", flush=True)

    rows: list[Row] = []
    for number, item in enumerate(sample, start=1):
        for seed in SEEDS:
            rows.extend(_measure(item.direction, item.game_id, seed))
        if number % 10 == 0:
            print(f"  {number}/{len(sample)} boards, {len(rows)} rows", flush=True)

    # ⚠️ The rows reach disk before anything is formatted. An earlier instrument measured seventy-two
    # boards and died in its own stamp, losing every one; compute is expensive and formatting is fragile.
    raw = _HERE / "rows.json"
    raw.write_text(json.dumps([asdict(r) for r in rows], indent=1, sort_keys=True), encoding="utf-8", newline=NL)
    print(f"{len(rows)} rows saved to {raw}", flush=True)

    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        report(rows)
        print("")
        print(provenance(len(sample), len(rows)))
    text = captured.getvalue()
    print(text)
    out = _HERE / "results.txt"
    pending = out.with_name(f"{out.name}.pending-{os.getpid()}-{secrets.token_hex(4)}")
    try:
        pending.write_text(text, encoding="utf-8")
        pending.replace(out)
    finally:
        pending.unlink(missing_ok=True)
    print(f"written to {out}")


if __name__ == "__main__":
    main()
