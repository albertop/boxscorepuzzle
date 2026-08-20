"""What the batting-order constraint is worth, and what has to be controlled for it to be worth it.

⚠️ **The correction this instrument exists to settle.** An earlier reading said the constraint determines
the whole PA column and called that the payoff. **Determining cells is filler, not difficulty.** If the
team's PA total is given, the player computes nine slots from one number — four turns and a remainder —
and types nine cells without thinking.

**With the total erased it works the other way.** Each slot bounds the next and the player has to chain,
and it bounds **in both directions**: knowing slots 3 and 6 puts 4 and 5 between them without fixing
either. That restricts without determining, which is what produces a stall.

**So the rule is good and what needs controlling is the total.** Three arms, and the one that answers the
question is `off` against `on_total_erasable`:

  off                today's solver
  on_total_given     constraint on, the PA total never erased
  on_total_erasable  constraint on, the PA total erasable like any other cell

The middle arm exists so the choice about the total is **visible rather than assumed**.

⚠️ **One canonical walk, filtered per arm.** The arms must differ in *treatment* and not in *trajectory*.
Ordering each arm's own candidate list separately would vary two things at once, and the report would read
exactly as clean as an honest one — a confound has no signature in the output and can only be prevented
here, while the instrument is being built.

⚠️ **The pool rule is applied.** 5 directions in 100,226 break the cycle; a constraint true 99.995% of the
time is a trap rather than a weaker rule, so the exceptions are excluded rather than tolerated. Measuring
without the rule would be measuring a constraint nobody would ship.

Read-only against DGL. Run from `forge/`.
"""

import random
import statistics
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))
sys.path.insert(0, str(_ROOT / "discovery" / "sample-boards"))
sys.path.insert(0, str(_ROOT / "forge" / "src"))

import json  # noqa: E402

from measure import Loaded, load  # noqa: E402
from render import render, render_path  # noqa: E402

from boxscore_forge.boxscore import Direction  # noqa: E402
from boxscore_forge.constraints import batting_total_cell, cell_values, shape_of  # noqa: E402
from boxscore_forge.erasure import DEFAULT_ORDERING, ORDERINGS, erasable  # noqa: E402
from boxscore_forge.identities import find_violations  # noqa: E402
from boxscore_forge.solver import Solution, Technique, solve  # noqa: E402

ARMS = ("off", "on_total_given", "on_total_erasable")
TARGETS = (3, 4, 5, 6, 8)
SAMPLE_PER_DECADE = 4
GATE = 0.30
SEEDS = (1, 2, 3)
PA_TOTAL = batting_total_cell("plate_appearances")
PA_COLUMN = ".plate_appearances"
SLOTS = 9
SPECIMEN_BOARDS = 3
SPECIMEN_TARGET = 5
SPECIMEN_ARMS = ("off", "on_total_erasable")
SPECIMEN_RULE = "⚠️ chosen for lineup arithmetic, plus one contrast board that uses none"
BASELINE = "off"
NEWLINE = chr(10)
PAGE_BREAK = NEWLINE * 2 + "=" * 100 + NEWLINE * 2


@dataclass(frozen=True, slots=True)
class Row:
    """One direction, one seed, one arm, one target."""

    game: str
    # ⚠️ **`offense` and `seed`, because without them the rows cannot be paired.** `Row` said it was
    # one direction, one seed, one arm and one target, and stored neither the seed nor the side. Three
    # seeds run per direction, so ambiguity was guaranteed rather than unlucky — and if both directions
    # of one game entered the sample their rows were indistinguishable. The expensive artifact could
    # not answer the one question it exists for: what did the three arms do on *this* walk.
    offense: str
    season: int
    seed: int
    arm: str
    target: int
    reached: bool
    blanks: int
    pa_blanks: int
    stalls: int
    chain: int
    families: str
    pa_by_lineup: int
    pa_by_propagation: int
    pa_by_bounding: int
    # ⚠⚠ **v27-P2-11: the ceiling table could not see a ceiling.** Every other field is a snapshot
    # at the *first crossing* of a configured target, and `_ceiling()` was taking maxima over those
    # snapshots after `_pairs()` had already dropped every walk only one arm reached — which is
    # exactly the population a ceiling difference lives in. A walk that ran to 8 under the treatment
    # and stopped at 6 under the baseline contributed neither number, so the table could report equal
    # ceilings while censoring the gains it exists to summarise.
    #
    # This is the terminal maximum over the whole accepted walk, recorded independently of whether any
    # target was reached. `None` means the row came from an artifact written before this field existed;
    # the table says so rather than quietly reverting to the censored answer.
    walk_max_stalls: int | None = None


def predicted(total: int) -> tuple[int, ...]:
    base, over = divmod(total, SLOTS)
    return tuple(base + 1 if slot <= over else base for slot in range(1, SLOTS + 1))


def obeys_the_cycle(loaded: Loaded) -> bool:
    """The pool rule, applied here so the constraint is exact on everything measured.

    ⚠️ Five directions in 100,226 break it. Measuring without this would be measuring a constraint the
    generator would never be allowed to use.
    """
    per_slot: dict[int, int] = {}
    for row, slot in zip(loaded.direction.batting, loaded.slots, strict=True):
        per_slot[slot] = per_slot.get(slot, 0) + row.plate_appearances
    ordered = tuple(value for _, value in sorted(per_slot.items()))
    return len(ordered) == SLOTS and ordered == predicted(sum(ordered))


def _canonical(direction: Direction, seed: int) -> list[str]:
    """The one walk every arm follows, in the generator's own default ordering."""
    rng = random.Random(seed)  # noqa: S311
    return list(ORDERINGS[DEFAULT_ORDERING](erasable(direction), direction, rng))


def _offered(arm: str, walk: list[str]) -> list[str]:
    """The same walk, filtered. ⚠️ Filtered, never re-ordered: that is the whole confound control."""
    if arm == "on_total_given":
        return [cell for cell in walk if cell != PA_TOTAL]
    return list(walk)


def _pa_techniques(solution: Solution, erased: set[str]) -> tuple[int, int, int]:
    """How the erased PA cells were reached: filler, arithmetic, or reasoning.

    ⚠️⚠️ **Three buckets, because two put the answer in the wrong one.** This counted anything that was
    not `BOUNDING` as propagation — and every deduction reached through an inequality *is* `BOUNDING`,
    so the cyclic step would have been recorded as reasoning. That is the precise inversion of the
    distinction this experiment exists to draw: reading one number and dividing by nine is the cheapest
    move on the board, and it would have been counted as the most expensive.

    `LINEUP_ARITHMETIC` is now its own technique, so the total-visible arm can be seen for what it is.
    """
    lineup = propagation = bounding = 0
    for step in solution.deductions:
        if step.cell not in erased or not step.cell.endswith(PA_COLUMN):
            continue
        if step.technique is Technique.LINEUP_ARITHMETIC:
            lineup += 1
        elif step.technique is Technique.BOUNDING:
            bounding += 1
        else:
            propagation += 1
    return lineup, propagation, bounding


def _stalls(solution: Solution) -> int:
    count = 0
    previous = False
    for step in solution.deductions:
        bounding = step.technique is Technique.BOUNDING
        count += bounding and not previous
        previous = bounding
    return count


def _measure(loaded: Loaded, seed: int) -> tuple[list[Row], dict[tuple[str, int], tuple[dict[str, int], Solution]]]:
    """The rows, and the boards they were read off.

    ⚠️ **The specimens are returned rather than rebuilt.** Every number below is a summary of a board
    nobody has looked at, and this project has never once caught a serious defect by reading a
    statistic. Re-walking the erasure to produce examples would be a second copy of the rule and would
    render a board other than the one measured — so the walk hands them over.
    """
    direction = loaded.direction
    values = cell_values(direction)
    walk = _canonical(direction, seed)
    without = shape_of(direction)
    with_order = shape_of(direction, tuple(loaded.slots))

    rows: list[Row] = []
    specimens: dict[tuple[str, int], tuple[dict[str, int], Solution]] = {}
    for arm in ARMS:
        shape = without if arm == "off" else with_order
        offered = _offered(arm, walk)
        erased: set[str] = set()
        best: dict[int, Solution] = {}
        best_erased: dict[int, set[str]] = {}
        # The whole walk's high-water mark, not a snapshot at a target. See `Row.walk_max_stalls`.
        walk_max = 0
        for cell in offered:
            trial = erased | {cell}
            solution = solve(shape, {name: value for name, value in values.items() if name not in trial})
            if not solution.is_complete:
                continue
            erased = trial
            reached = _stalls(solution)
            walk_max = max(walk_max, reached)
            for target in TARGETS:
                if reached >= target and target not in best:
                    best[target] = solution
                    best_erased[target] = set(erased)

        for target in TARGETS:
            solution = best.get(target)
            got = best_erased.get(target, set())
            if solution is not None:
                specimens[arm, target] = ({n: v for n, v in values.items() if n not in got}, solution)
            lineup, propagation, bounding = _pa_techniques(solution, got) if solution else (0, 0, 0)
            rows.append(
                Row(
                    game=loaded.game_id,
                    offense=loaded.offense_team,
                    season=loaded.season,
                    seed=seed,
                    arm=arm,
                    target=target,
                    # ⚠️ A target no arm reached is a row, not a missing row. Dropping it would summarise
                    # the survivors and call the difference a null.
                    reached=solution is not None,
                    blanks=len(got),
                    pa_blanks=sum(1 for cell in got if cell.endswith(PA_COLUMN)),
                    stalls=_stalls(solution) if solution else 0,
                    chain=solution.chain_length if solution else 0,
                    families=",".join(sorted(family.value for family in solution.families_used)) if solution else "",
                    pa_by_lineup=lineup,
                    pa_by_propagation=propagation,
                    pa_by_bounding=bounding,
                    walk_max_stalls=walk_max,
                )
            )
    return rows, specimens


def _classify_specimen(measured: list[Row], specimens: dict[tuple[str, int], object]) -> str | None:
    """Which pool this direction belongs to, or `None` when it belongs to neither.

    ⚠️⚠️ **v27-P3-16: `False` meant two different things and both went into the contrast pool.**
    The classifier read `any(pa_by_lineup > 0 for ... if reached)`. That is false when the treatment
    reached the target using no lineup arithmetic — a genuine contrast — and equally false when the
    treatment **never reached the target at all**, which is not an observation. The second kind could
    be picked as the promised contrast, and `_specimen_pages()` would write
    `arm on_total_erasable never reached 5 stalls` where a board was supposed to be, while the summary
    announced a complete two-positive/one-contrast set.

    **Eligibility comes before composition.** A direction is classified only when *both* rendered arms
    produced a specimen at the target, so the promised comparison is known to exist before anything
    decides what kind of comparison it is. A measured zero and an absent observation are not the same
    value, and pooling them is the null-result defect wearing a different hat.
    """
    drawn = [arm for arm in SPECIMEN_ARMS if arm != BASELINE]
    if any((arm, SPECIMEN_TARGET) not in specimens for arm in SPECIMEN_ARMS):
        return None
    reached = [row for row in measured if row.arm in drawn and row.target == SPECIMEN_TARGET and row.reached]
    if not reached:
        return None
    return "positive" if any(row.pa_by_lineup > 0 for row in reached) else "negative"


def _choose_specimens(
    positive: list[tuple[Loaded, dict]], negative: list[tuple[Loaded, dict]]
) -> list[tuple[Loaded, dict]]:
    """Fill the declared composition from two pools, or refuse to write a page.

    ⚠⚠ **A postcondition, not a comment.** `SPECIMEN_RULE` says the set is boards using lineup
    arithmetic *plus one contrast that uses none*, and the previous selector could satisfy neither half
    while still printing the rule. If a pool cannot supply its share this **raises**: a specimen file
    that silently lost its contrast is an eye-check on one population presented as an eye-check on two,
    and the reader has no way to tell.

    Deterministic by draw order within each pool, so a rerun on the same sample renders the same
    boards.
    """
    wanted_contrast = 1
    wanted_positive = SPECIMEN_BOARDS - wanted_contrast
    if len(positive) < wanted_positive or len(negative) < wanted_contrast:
        message = (
            f"the specimen rule needs {wanted_positive} boards using lineup arithmetic and "
            f"{wanted_contrast} that does not; the sample offered {len(positive)} and {len(negative)}. "
            f"Widen the sample or change SPECIMEN_BOARDS -- do not write a page that misstates its rule."
        )
        raise SystemExit(message)
    return positive[:wanted_positive] + negative[:wanted_contrast]


def _specimen_pages(loaded: Loaded, specimens: dict[tuple[str, int], tuple[dict[str, int], Solution]]) -> list[str]:
    """The same board under both arms, drawn with the board's own renderer.

    ⚠⚠ **Rendered, not described.** Every serious defect this project has found was found by printing
    something and reading it, and the one that survived several reviews was a *working* instrument
    pointed at the wrong thing — a metric counting steps the player experiences as typing zeros. No
    number distinguishes that case from an honest one. These pages exist to answer what no column can:
    **when the erased PA cells go up, what does the player actually do?**

    `show_slots` is on, because a chain across slots is the thing being judged and the slot is not on
    the player's board. It is a flag on the real renderer, never a second one.
    """
    pages: list[str] = []
    for arm in SPECIMEN_ARMS:
        found = specimens.get((arm, SPECIMEN_TARGET))
        if found is None:
            pages.append(f"  {loaded.game_id} {loaded.offense_team}: arm {arm} never reached {SPECIMEN_TARGET} stalls")
            continue
        given, solution = found
        blank = sum(1 for cell in cell_values(loaded.direction) if cell not in given and cell.endswith(PA_COLUMN))
        title = f"arm {arm} - target {SPECIMEN_TARGET} stalls - {blank} of the PA column erased"
        pages.append(render(loaded, given, title=title, show_slots=True) + NEWLINE * 2 + render_path(solution))
    return pages


def _median(values: list[int]) -> float:
    return statistics.median(values) if values else 0.0


def _key(row: Row) -> tuple[str, str, int]:
    """One walk: a direction and a seed. `target` is not in the key; it selects the table."""
    return (row.game, row.offense, row.seed)


def _pairs(rows: list[Row], arm: str, target: int) -> list[tuple[Row, Row]]:
    """The walks `arm` and the baseline **both** reached at this target, paired.

    ⚠⚠ **v27-P2-10: `Row` was made pairable and the report did not pair.** Each table selected
    reached rows per arm independently, and *reachability is changed by the treatment* — so the arms
    contributed different directions, different seeds and different target mixtures to figures printed
    side by side. A walk that reaches 8 stalls only under `on_total_erasable` put its blanks into that
    arm's median with no counterpart in `off`. Any difference could then be **which trials survived**
    rather than the constraint, and the artifact already held the fields needed to remove it.

    Coverage stays unpaired, because failing to reach *is* its outcome. Everything else is a treatment
    effect and is measured only on walks both arms completed.
    """
    baseline = {_key(row): row for row in rows if row.arm == BASELINE and row.target == target and row.reached}
    treated = {_key(row): row for row in rows if row.arm == arm and row.target == target and row.reached}
    return [(baseline[key], treated[key]) for key in sorted(baseline.keys() & treated.keys())]


def _moved(deltas: list[int]) -> str:
    """How many items moved, which way, and by how much.

    ⚠️ **The per-item count, not only the median.** "Nothing moved" read off a median is not a null
    result: two walks moving in opposite directions leave every summary statistic untouched. A
    comparison that cannot say how many individual items changed is not a comparison.
    """
    if not deltas:
        return f"{'no pairs':>30}"
    up = sum(1 for delta in deltas if delta > 0)
    down = sum(1 for delta in deltas if delta < 0)
    return f"{f'{_median(deltas):+.1f} ({up} up, {down} dn, {len(deltas) - up - down} =)':>30}"


def _coverage(rows: list[Row]) -> None:
    print("")
    print("=== COVERAGE: SHARE OF WALKS REACHING EACH TARGET (unpaired, on purpose) ===")
    print("  Failing to reach a target IS this table's outcome, so it is the one table that must not be")
    print("  restricted to walks both arms completed. Every table below it is paired.")
    print(f"  {'target':<8}" + "".join(f"{arm:>20}" for arm in ARMS))
    for target in TARGETS:
        line = f"  {target:<8}"
        for arm in ARMS:
            here = [row for row in rows if row.arm == arm and row.target == target]
            got = sum(1 for row in here if row.reached)
            line += f"{f'{got}/{len(here)} ({100.0 * got / max(len(here), 1):.0f}%)':>20}"
        print(line)


def _blanks(rows: list[Row], arm: str) -> None:
    print("")
    print(f"  --- blanks, paired ({arm} minus {BASELINE}) ---")
    print(f"  {'target':<8}{'pairs':>7}{'blanks delta':>30}{'PA blanks delta':>30}")
    for target in TARGETS:
        pairs = _pairs(rows, arm, target)
        blanks = [treated.blanks - base.blanks for base, treated in pairs]
        pa_blanks = [treated.pa_blanks - base.pa_blanks for base, treated in pairs]
        print(f"  {target:<8}{len(pairs):>7}{_moved(blanks)}{_moved(pa_blanks)}")


def _techniques(rows: list[Row], arm: str) -> None:
    print("")
    print("  --- how the erased PA cells were reached, on those same pairs ---")
    print("  lineup = read the total, divide by nine, write it down. Filler: the cheapest move there is.")
    print("  bounding = the cell was cornered by the board. That is the reasoning the constraint may buy.")
    print(f"  {'target':<8}{'pairs':>7}{BASELINE + ' l/p/b':>24}{arm + ' l/p/b':>24}{'bounding share':>20}")
    for target in TARGETS:
        pairs = _pairs(rows, arm, target)
        if not pairs:
            print(f"  {target:<8}{0:>7}{'no pairs':>24}")
            continue
        sides = [
            (
                sum(pair[index].pa_by_lineup for pair in pairs),
                sum(pair[index].pa_by_propagation for pair in pairs),
                sum(pair[index].pa_by_bounding for pair in pairs),
            )
            for index in (0, 1)
        ]
        shares = [
            f"{100.0 * bound / (line + prop + bound):.1f}%" if (line + prop + bound) else "n/a"
            for line, prop, bound in sides
        ]
        cells = "".join(f"{f'{line}/{prop}/{bound}':>24}" for line, prop, bound in sides)
        print(f"  {target:<8}{len(pairs):>7}{cells}{f'{shares[0]} -> {shares[1]}':>20}")


def _families(rows: list[Row], arm: str) -> None:
    print("")
    print("  --- families needed, on those same pairs (share of paired walks) ---")
    for target in TARGETS:
        pairs = _pairs(rows, arm, target)
        if not pairs:
            continue
        line = f"  {target:<8}{len(pairs):>7}   "
        for index, label in ((0, BASELINE), (1, arm)):
            counted: Counter = Counter()
            for pair in pairs:
                for family in pair[index].families.split(","):
                    if family:
                        counted[family] += 1
            shown = " ".join(f"{name[:6]} {100.0 * count / len(pairs):.0f}%" for name, count in sorted(counted.items()))
            line += f"{label}: {shown}   "
        print(line)


def _ceiling(rows: list[Row], arm: str) -> None:
    """The stall ceiling per walk, from the terminal maximum — **not from target snapshots**.

    ⚠⚠ **v27-P2-11: the previous version could not see a ceiling difference.** It was built from
    `_pairs()`, which keeps only walks *both* arms reached at the same target. A walk that ran to 8
    under the treatment and stopped at 6 under the baseline was dropped entirely — and that is
    precisely the population a ceiling gain lives in. The persisted run has 73 treated target-8
    reaches against 53 baseline ones, so at least twenty walks could never influence the table
    summarising exactly that. It could report equal ceilings while censoring the difference.

    Paired by walk, never by target success: the pairing key is the direction and the seed, and both
    arms contribute their high-water mark whether or not they reached anything. Aggregated to
    direction only after the walk-level delta, because a direction is three walks and averaging them
    before differencing hides which walk moved.
    """
    paired: dict[tuple[str, str, int], list[int]] = {}
    censored = 0
    for arm_name, index in ((BASELINE, 0), (arm, 1)):
        for row in rows:
            if row.arm != arm_name:
                continue
            if row.walk_max_stalls is None:
                censored += 1
                continue
            here = paired.setdefault(_key(row), [0, 0])
            here[index] = max(here[index], row.walk_max_stalls)

    print("")
    print("  --- stall ceiling, the terminal maximum of each walk (paired by direction and seed) ---")
    if censored:
        # ⚠️ Fail loud rather than silently reverting to the censored answer. An artifact written
        # before `walk_max_stalls` existed cannot answer this question, and saying so is the whole
        # point of the finding that produced this field.
        print(f"  NOT ANSWERABLE: {censored} rows predate walk_max_stalls. Re-run to get this table.")
        return

    deltas = [values[1] - values[0] for values in paired.values()]
    print(
        f"  {len(paired)} walks   {BASELINE} median {_median([v[0] for v in paired.values()]):.0f}"
        f"   {arm} median {_median([v[1] for v in paired.values()]):.0f}"
        f"   paired delta {_moved(deltas).strip()}"
    )
    by_direction: dict[tuple[str, str], list[int]] = {}
    for (game, offense, _seed), values in paired.items():
        by_direction.setdefault((game, offense), []).append(values[1] - values[0])
    moved = sum(1 for per_walk in by_direction.values() if any(delta != 0 for delta in per_walk))
    print(f"  {moved} of {len(by_direction)} directions have at least one walk whose ceiling moved")


def _report(rows: list[Row]) -> None:
    _coverage(rows)
    for arm in ARMS:
        if arm == BASELINE:
            continue
        print("")
        print(f"=== {arm.upper()} AGAINST {BASELINE.upper()}, PAIRED BY DIRECTION AND SEED ===")
        _blanks(rows, arm)
        _techniques(rows, arm)
        _families(rows, arm)
        _ceiling(rows, arm)


def report_only() -> None:
    """Re-read `arms.json` and print the tables again, without re-measuring anything.

    ⚠️ The rows are the expensive half and they are written before any formatting, precisely so a
    defect in the *report* costs a second of reading rather than an afternoon of solving. v27-P2-10 was
    exactly that defect, and this is why the run that hit it did not have to be repeated.
    """
    saved = json.loads((_HERE / "arms.json").read_text(encoding="utf-8"))
    rows = [Row(**row) for row in saved]
    print(f"re-reporting {len(rows)} rows from arms.json - nothing was re-measured")
    _report(rows)


def main() -> None:
    sample = [
        item
        for item in load(SAMPLE_PER_DECADE, gated=True, gate=GATE)
        if not find_violations(item.direction) and obeys_the_cycle(item)
    ]
    if not sample:
        message = "no directions survived the gate and the cycle rule; the filters here are wrong"
        raise SystemExit(message)
    print(f"{len(sample)} directions x {len(SEEDS)} seeds x {len(ARMS)} arms, targets {TARGETS}")
    print("One canonical walk per (direction, seed), FILTERED per arm - never re-ordered.")

    rows: list[Row] = []
    # ⚠⚠ **v27-P3-12: two pools, filled without a quota, and the quota applied afterwards.** The
    # previous version accepted `uses_lineup or not contrast` as boards arrived, so three
    # lineup-positive boards in a row filled the quota and the contrast could never enter — while the
    # summary still printed `SPECIMEN_RULE`, which promises one. The composition depended on draw
    # order, and the artifact happening to contain a contrast was luck. Collect both pools to the end
    # of the sample, choose after measuring, and **assert the composition rather than describe it**.
    positive: list[tuple[Loaded, dict]] = []
    negative: list[tuple[Loaded, dict]] = []
    for number, loaded in enumerate(sample, start=1):
        for seed in SEEDS:
            measured, specimens = _measure(loaded, seed)
            rows.extend(measured)
            # ⚠⚠ **Chosen for what is being judged, not by draw order.** The first run rendered the
            # first three boards and all three happened to use no lineup arithmetic at all — an
            # eye-check on boards where the treatment does nothing, while 73% of reached walks in the
            # same run used it. A sample meant to show a phenomenon has to contain it. One board that
            # uses none is kept deliberately, so the contrast is visible rather than assumed.
            if seed == SEEDS[0]:
                pool = _classify_specimen(measured, specimens)
                if pool is not None:
                    (positive if pool == "positive" else negative).append((loaded, specimens))
        if number % 5 == 0:
            print(f"  {number}/{len(sample)} measured", flush=True)

    chosen = _choose_specimens(positive, negative)
    pages = [page for loaded, specimens in chosen for page in _specimen_pages(loaded, specimens)]
    # ⚠️ Written before the report, and meant to be read before the report is believed.
    # ⚠️ A page break the internal blank lines cannot imitate: joining on two newlines made the
    # boundary between one board and the next identical to the one between a board and its own
    # solution path, so the file could not be split back into pages by eye or by code.
    (_HERE / "specimens.txt").write_text(PAGE_BREAK.join(pages), encoding="utf-8", newline=NEWLINE)
    print(f"wrote {len(pages)} rendered boards to specimens.txt - READ THESE BEFORE TRUSTING THE NUMBERS")
    print(f"  {SPECIMEN_BOARDS - 1} using lineup arithmetic and 1 contrast ({SPECIMEN_RULE})")

    # Persisted before formatting: the rows are the expensive half and everything below can fail.
    (_HERE / "arms.json").write_text(
        json.dumps([asdict(row) for row in rows], indent=1, sort_keys=True), encoding="utf-8", newline="\n"
    )
    print(f"wrote {len(rows)} rows to arms.json before formatting anything")
    _report(rows)

    print("")
    print("NOTE: the comparison that answers the question is `off` against `on_total_erasable`.")
    print("  `on_total_given` is there so the choice about the total is visible rather than assumed:")
    print("  with the total given the nine slots follow from one number and the player types filler.")
    print("")
    print("NOT MEASURED HERE: whether these boards pass the verifier's layer 3. The constraint is in the")
    print("  generator's solver and in the verifier's RELATIONS, but the verifier has no twin of the")
    print("  lineup step - its solver narrows intervals, which cannot reach the cyclic distribution. So")
    print("  a board leaning on the constraint would be refused as underivable. Said rather than left")
    print("  implied: no number below is a claim about derivability.")


if __name__ == "__main__":
    # ⚠️ `--report-only` re-reads the persisted rows. It exists because a report can be wrong while the
    # measurement is fine, and re-solving 48 directions to fix a formatting decision is how a chain of
    # measurements starts.
    if "--report-only" in sys.argv[1:]:
        report_only()
    else:
        main()
