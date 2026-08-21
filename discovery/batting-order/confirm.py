"""Does the adoption hold on boards that can actually publish?

⚠️⚠️ **Everything that decided this was measured while no such board existed.** `boxscore_verify` had
no value-producing lineup step, so layer 3 refused anything leaning on the cyclic order. The technique
counts and the no-filler share describe **what the generator produces**, not what can ship. The step
exists now; this is the re-run.

⚠⚠ **Two of the figures that used to be quoted here were wrong and are corrected in
`batting-order-reversal.md`**: there is no reproducible *47*, and the no-filler share is **eight** of
eleven rather than nine — the table it came from listed eight zeros. The instrument that produced the
buckets is sound; the sentences about it were not.

⚠️⚠️ **PRE-REGISTERED, and this is the second version of the pre-registration.** The first was
committed and the run was stopped before it wrote a single row — `confirm.json` never existed and no
figure was ever seen. **Rewriting it is therefore correcting an instrument, not adjusting a reading**,
and that distinction is the only thing that makes a rewrite legitimate at all.

## ⚠️⚠️ Why the first version could not have overturned anything (v29-P1-01)

It compared `plain` against `fallback` and made `gained - lost` the headline, with *anything at or
below zero overturns the adoption*.

**`lost` was impossible by construction.** `erase_with_lineup_fallback` makes the identical plain call
first and returns that exact puzzle when it succeeds, so **every direction covered by `plain` is
covered by `fallback`**. `plain - fallback` is structurally empty. The criterion described as able to
overturn the decision was wired to one treatment that *contains* the other, and the per-seed table did
not repair it, because the containment holds for every seed independently.

**A pre-registered criterion that cannot be violated is not a criterion.** It is the
check-that-never-fires defect, built into the arm rather than the threshold — inside a file whose own
docstring said it existed to stop exactly that.

## The two questions, separated — they were one before, which is what let the containment hide

  **A. What does the constraint cost and buy as a treatment?**
     `plain` against `on`: the constraint applied to every board, `erase(..., slots=slots)`, same seed
     and target. **Neither arm contains the other, so `lost` is real and can be positive.**

  **B. What does the product gain from the adopted design?**
     `plain` against `fallback`. **Monotone by design** — the fallback tries plain first, so it can
     only add. `lost` is meaningless here and is not reported as though it were a finding.

## What would confirm the adoption, fixed before any number is seen

  1. **Coverage.** Arm B adds directions at the hard end that plain cannot reach and that pass the
     publication gate. **Zero added overturns it** — the whole case is that the constraint reaches
     boards nothing else does.
  2. **Cost.** In arm A, `lost` does not swamp `gained` at the hard end, per seed. **If switching the
     constraint on loses more than it gains, the conditional design is doing the work and the
     constraint itself is not.**
  3. **Filler.** On the **gained cohort only** — `target == 8`, `arm == "fallback"`,
     `reason == "fallback"`, publishable, direction in the paired gained set — division steps are a
     small share of the solve. The earlier claim was nine of eleven with none at all. **A majority
     carrying filler overturns it.**

     ⚠️ **The denominator is every other deduction, not deductions the constraint caused.** It was
     called `causal` and that asserted the one thing this run was meant to settle. The share is a real
     measure of how much of the solve is read-the-total-divide-by-nine, which is what the criterion
     asks; it is not evidence that the remaining steps used the cyclic order. v30-P1-01.

⚠️ **What would NOT count:** a favourable figure drawn from a wider cohort than the criterion names —
other targets, other seeds, common boards, or fallback rows whose wrapper returned the plain result.
Those carry zero division *by construction* and dilute the very share being tested. That was
v29-P2-04, which is why the cohort above is spelled out field by field.

## ⚠️ Certification means the publication gate, not the arithmetic verifier

The first version called `verify()` and stored the answer in a field named `certified`. Production
publishes through `certify_for_publication()`, which also applies plausibility and independent
evidence. A board can pass every arithmetic layer and be refused for roster plausibility or a
disagreeing official total, so coverage built on `verify()` is a number about the verifier while
claiming to be one about the product (v29-P2-03).

Both are recorded under names that cannot be confused: `verified` for the arithmetic layers,
`publishable` for the gate. ⚠️ Signatures are deliberately skipped — this is an unsigned discovery run
— so **"passes the gate" here never means "authentic"**, and the phrase *all five layers* is not used.

Read-only against DGL. Run from anywhere.
"""

import json
import statistics
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parents[1] / "discovery"))
sys.path.insert(0, str(_HERE.parents[1] / "forge" / "scripts"))
from bootstrap import bootstrap  # noqa: E402

bootstrap()

from measure import Loaded, load  # noqa: E402
from write_reference_puzzles import reveal_for  # noqa: E402

from boxscore_domain import ZERO_DENSITY_GATE  # noqa: E402
from boxscore_forge.erasure import erase  # noqa: E402
from boxscore_forge.identities import find_violations  # noqa: E402
from boxscore_forge.identity import puzzle_id  # noqa: E402
from boxscore_forge.lineup_fallback import erase_with_lineup_fallback  # noqa: E402
from boxscore_forge.publish import (  # noqa: E402
    slot_references,
    to_board,
)
from boxscore_forge.solver import Technique  # noqa: E402
from boxscore_package.format import Package  # noqa: E402
from boxscore_verify.certify import Evidence, certify_for_publication  # noqa: E402
from boxscore_verify.verify import UNSIGNED, verify  # noqa: E402

TARGETS = (3, 4, 5, 6, 8)
SEEDS = (1, 2, 3)
SAMPLE_PER_DECADE = 4
"""The same draw as `arms.py`, so the figures are comparable to the ones being tested."""

HARD = 8
"""The target the case rests on. Named, so the cohort below cannot quietly become a different one."""

ARMS = ("plain", "on", "fallback")
"""⚠️ `on` is the trade-off arm and `fallback` is the product arm. Reporting them as one comparison is
what made `lost` impossible last time."""


@dataclass(frozen=True, slots=True)
class Row:
    """One direction, one seed, one target, one arm."""

    game: str
    offense: str
    season: int
    seed: int
    target: int
    arm: str
    reached: bool
    verified: bool
    """The arithmetic layers accepted it. **Not** the same as publishable."""
    publishable: bool
    """⚠️ The publication gate accepted it: plausibility and independent evidence as well."""
    refused_by: str
    blanks: int
    stalls: int
    chain: int
    division: int
    other_steps: int
    reason: str
    """`plain`, `on`, `fallback`, `discarded_filler` or `unreachable` — which path produced this."""


def _evidence(loaded: Loaded, board: object) -> Evidence:
    """The same independent corroboration the production writer supplies.

    ⚠️ `official_at_bats` and `official_left_on_base` come from the loader's game-log join rather than
    from the board, which is the whole point of the evidence layer: a total summed from the rows it is
    meant to verify cannot fail. The error and defensive columns are not on `Loaded`, so they are taken
    from the line score — which §6 gives complete and never erases, so they are given rather than
    derived.
    """
    return Evidence(
        # The board as the loader read it from the database, which is what layer 4 solves back to.
        source=to_board(loaded.direction, None),
        game_id=loaded.game_id,
        offense_team=loaded.offense_team,
        source_type=loaded.source_type,
        is_deduced=loaded.is_deduced,
        official_hits=loaded.official_hits,
        official_runs=loaded.official_runs,
        official_errors=board.line_score.offense_errors,
        official_defense_runs=board.line_score.defense_runs,
        official_defense_hits=board.line_score.defense_hits,
        official_defense_errors=board.line_score.defense_errors,
        official_at_bats=loaded.official_at_bats,
        official_left_on_base=loaded.official_left_on_base,
    )


def _package(loaded: Loaded, erased: frozenset[str] | None) -> Package:
    """The package production would build, **including its reveal** (v29-P1-02).

    ⚠⚠ **Without the reveal the gate refuses every row, and the criterion reads that as a verdict.**
    `certify_for_publication` requires a complete reveal — §23 puts the answer in the file — so a
    measurement package missing one is `publishable=False` for a reason that has nothing to do with the
    treatment. `_covered()` counts only publishable rows, and criterion 1 says **zero added overturns
    the adoption**. The instrument would have rejected the mechanism without measuring it.

    ⚠️ **The end-to-end test had already hit this and been fixed**, and the fix was not carried here.
    A lesson learned in one file at 15:40 and not applied in the next is the shape this project keeps
    meeting; the pre-flight check below exists so the next one costs a second rather than an afternoon.

    `reveal_for` is imported from the production writer rather than reassembled, so there is one place
    that knows what a reveal is made of.
    """
    return Package(
        puzzle_id=puzzle_id(loaded.game_id, loaded.offense_team),
        puzzle=to_board(loaded.direction, erased),
        solution=to_board(loaded.direction, None),
        labels=loaded.labels,
        pitcher_labels=loaded.pitcher_labels,
        slot_references=slot_references(loaded.slots),
        reveal=reveal_for(loaded),
        offense_is_home=loaded.offense_is_home,
    )


def _preflight(loaded: Loaded) -> None:
    """Prove the instrument can produce a publishable board **before** spending the run on it.

    ⚠⚠ **The check that would have caught v29-P1-02 in a second.** An unerased board is the easiest
    case there is: nothing is blank, so no treatment, no erasure and no solver is involved. If *that*
    cannot pass the gate, the failure is in how this file assembles a package — and every row the run
    produces would carry it, reported as though the constraint had failed.

    ⚠️ Raises rather than warns. A measurement that knows its instrument is broken and runs anyway is
    worse than one that never ran, because it produces numbers.
    """
    package = _package(loaded, None)
    verdict = verify(package, secret=UNSIGNED, source=package.solution)
    if not verdict.accepted:
        message = f"pre-flight: an unerased board fails the arithmetic layers: {verdict.rejection}"
        raise SystemExit(message)
    gate = certify_for_publication(package, evidence=_evidence(loaded, package.solution), secret=UNSIGNED)
    if not gate.publishable:
        message = (
            "pre-flight: an unerased board does not reach publication, so nothing this run measures "
            f"could. The instrument is at fault, not the treatment: {gate.refusals}"
        )
        raise SystemExit(message)
    print(f"pre-flight: an unerased {loaded.game_id} board passes the gate, so the package is complete")


def _steps(solution: object) -> tuple[int, int]:
    """Division filler, and **every other deduction** — which is not the same as a causal one.

    ⚠⚠ **The second number was called `causal` and it is not.** It is `len(deductions) - division`:
    ordinary column sums, row propagation, cross-team and global-identity deductions and bounding
    steps, whether or not the batting order contributed anything to them. Subtracting division from
    the total establishes nothing about causation, and the name asserted the one thing the adoption
    measurement was supposed to settle — whether the constraint *resolves* cells or merely permits
    more erasure while unrelated equations resolve them. v30-P1-01.

    **What the ratio still means, and it is worth keeping.** Division steps as a share of the whole
    solution is a real measure of *filler*: how much of the player's work is read-the-total-divide-by-
    nine. That is what the pre-registered criterion asked for and it is what this reports. The
    denominator is simply "the rest of the solve" rather than "deductions the constraint enabled".

    ⚠️ **A causal number needs a counterfactual and this instrument does not have one.** It would mean
    solving the identical erasure with and without the mechanism and counting what disappears — and
    bounding carries no originating identity, so a dependency graph could not attribute it. Until that
    exists, nothing here may be reported as causal, and `_report_filler` no longer does.
    """
    division = sum(1 for step in solution.deductions if step.technique is Technique.LINEUP_ARITHMETIC)
    return division, len(solution.deductions) - division


def _erase_for(arm: str, loaded: Loaded, slots: tuple[int, ...], target: int, seed: int) -> tuple:
    """The three arms, kept apart so none contains another by accident."""
    if arm == "plain":
        produced = erase(loaded.direction, target_stalls=target, seed=seed)
        return produced, ("plain" if produced else "unreachable")
    if arm == "on":
        # The constraint applied to every board. Not the adopted design -- the arm that says what the
        # adopted design is avoiding.
        produced = erase(loaded.direction, target_stalls=target, seed=seed, slots=slots)
        return produced, ("on" if produced else "unreachable")
    return erase_with_lineup_fallback(loaded.direction, slots, target_stalls=target, seed=seed)


def _measure(loaded: Loaded, seed: int) -> list[Row]:
    rows: list[Row] = []
    slots = tuple(loaded.slots)
    for target in TARGETS:
        for arm in ARMS:
            puzzle, reason = _erase_for(arm, loaded, slots, target, seed)
            common = {
                "game": loaded.game_id,
                "offense": loaded.offense_team,
                "season": loaded.season,
                "seed": seed,
                "target": target,
                "arm": arm,
                "reason": reason,
            }
            if puzzle is None:
                rows.append(
                    Row(
                        **common,
                        reached=False,
                        verified=False,
                        publishable=False,
                        refused_by="",
                        blanks=0,
                        stalls=0,
                        chain=0,
                        division=0,
                        other_steps=0,
                    )
                )
                continue
            package = _package(loaded, puzzle.erased)
            verdict = verify(package, secret=UNSIGNED, source=package.solution)
            # ⚠️⚠️ The gate production calls, not the arithmetic verifier alone.
            gate = certify_for_publication(package, evidence=_evidence(loaded, package.solution), secret=UNSIGNED)
            division, other_steps = _steps(puzzle.solution)
            refused = "" if gate.publishable else "; ".join(str(item) for item in gate.refusals)[:80]
            rows.append(
                Row(
                    **common,
                    reached=True,
                    verified=verdict.accepted,
                    publishable=gate.publishable,
                    refused_by=refused,
                    blanks=len(puzzle.erased),
                    stalls=puzzle.solution.stalls,
                    chain=puzzle.solution.chain_length,
                    division=division,
                    other_steps=other_steps,
                )
            )
    return rows


def _covered(rows: list[Row], arm: str, target: int, seed: int | None = None) -> set[tuple[str, str]]:
    """Directions covered: reached AND through the publication gate. One definition, used everywhere."""
    return {
        (row.game, row.offense)
        for row in rows
        if row.arm == arm and row.target == target and row.publishable and (seed is None or row.seed == seed)
    }


def _report_coverage(rows: list[Row], directions: set) -> None:
    print("")
    print("=== B. PRODUCT COVERAGE: plain against the adopted fallback ===")
    print("  Monotone by design: the fallback tries plain first, so it can only add.")
    print("  'lost' is meaningless here and is not reported as one.")
    print(f"  {'target':>7}{'plain':>12}{'fallback':>12}{'added':>8}")
    for target in TARGETS:
        plain = _covered(rows, "plain", target)
        fallback = _covered(rows, "fallback", target)
        print(
            f"  {target:>7}{f'{len(plain)}/{len(directions)}':>12}"
            f"{f'{len(fallback)}/{len(directions)}':>12}{len(fallback - plain):>8}"
        )


def _report_tradeoff(rows: list[Row]) -> None:
    print("")
    print("=== A. TREATMENT TRADE-OFF: plain against the constraint on every board ===")
    print("  Neither arm contains the other, so 'lost' is real and can be positive.")
    print(f"  {'target':>7}{'seed':>6}{'plain':>7}{'on':>5}{'gained':>8}{'lost':>6}")
    for target in TARGETS:
        for seed in SEEDS:
            plain = _covered(rows, "plain", target, seed)
            switched = _covered(rows, "on", target, seed)
            print(
                f"  {target:>7}{seed:>6}{len(plain):>7}{len(switched):>5}"
                f"{len(switched - plain):>8}{len(plain - switched):>6}"
            )


DECISION_UNIT = "direction"
"""⚠⚠ **One unit, fixed before the run, and it is the direction** (v29-P2-05).

The claim being tested is *nine of eleven **directions** carried no division filler*, and the follow-up
was asked for per direction. An earlier version identified gains per direction and then counted per
**direction-seed row**, so a direction that succeeded under all three seeds cast three votes and one
that succeeded under a single seed cast one. **That weighting can reverse the majority without the set
of useful directions changing at all** — an adoption decided by how often a seed happened to work.

The seed rows are still printed, because a reduction nobody can see is a reduction nobody can check.
They are evidence; the direction is the unit.
"""

SEED_FOR_DECISION = min(SEEDS)
"""Which seed represents a direction when several qualify.

⚠️ **Chosen before any outcome is read, and by a rule that cannot see one.** Taking the best, the
worst, or the one with least filler would be choosing the observation after seeing it, which is the
move that produced the reversal this whole file exists to avoid.
"""


def _gained_cohort(rows: list[Row]) -> list[Row]:
    """⚠⚠ The criterion's rows, spelled out field by field so the cohort cannot widen unnoticed.

    v29-P2-04: an earlier version summed every certified row at every target and seed, including common
    boards and fallback rows whose wrapper returned the plain result. **Those carry zero division by
    construction** and dilute the very share being tested.
    """
    gained = _covered(rows, "fallback", HARD) - _covered(rows, "plain", HARD)
    return [
        row
        for row in rows
        if row.target == HARD
        and row.arm == "fallback"
        and row.reason == "fallback"
        and row.publishable
        and (row.game, row.offense) in gained
    ]


def _one_per_direction(cohort: list[Row]) -> list[Row]:
    """Reduce the seed rows to one observation per gained direction, deterministically.

    The lowest qualifying seed, which is fixed by `SEED_FOR_DECISION` and does not depend on what the
    row says. A direction with no row at that seed falls back to its lowest available one — stated
    here rather than left implicit, because "the lowest that exists" is still a rule chosen in advance.
    """
    by_direction: dict[tuple[str, str], list[Row]] = {}
    for row in cohort:
        by_direction.setdefault((row.game, row.offense), []).append(row)
    chosen = []
    for rows_here in by_direction.values():
        preferred = [row for row in rows_here if row.seed == SEED_FOR_DECISION]
        chosen.append(min(preferred or rows_here, key=lambda row: row.seed))
    return sorted(chosen, key=lambda row: (row.game, row.offense))


def _report_filler(rows: list[Row]) -> None:
    cohort = _gained_cohort(rows)
    decided = _one_per_direction(cohort)
    print("")
    print(f"=== C. FILLER, gained cohort only: target {HARD}, fallback path, publishable ===")
    print(f"  unit: one {DECISION_UNIT}, represented by seed {SEED_FOR_DECISION} where it qualifies")
    print(f"  {len(cohort)} qualifying rows reduce to {len(decided)} directions, against 11 before")
    if not decided:
        print("  NOTHING IN THE COHORT. The adoption's own criterion has no evidence either way.")
        return

    print("")
    print("  every qualifying row, so the reduction can be checked rather than trusted:")
    header = f"  {'':<3}{'game':<14}{'off':<5}{'seed':>5}{'stalls':>7}{'chain':>7}"
    print(header + f"{'blanks':>7}{'division':>9}{'other':>7}")
    counted = {(row.game, row.offense, row.seed) for row in decided}
    for row in sorted(cohort, key=lambda item: (item.game, item.offense, item.seed)):
        mark = "->" if (row.game, row.offense, row.seed) in counted else "  "
        print(
            f"  {mark:<3}{row.game:<14}{row.offense:<5}{row.seed:>5}{row.stalls:>7}{row.chain:>7}"
            f"{row.blanks:>7}{row.division:>9}{row.other_steps:>7}"
        )

    division = sum(row.division for row in decided)
    other_steps = sum(row.other_steps for row in decided)
    clean = sum(1 for row in decided if row.division == 0)
    share = division / max(other_steps + division, 1)
    print("")
    print(
        f"  over {len(decided)} directions: {division} division steps in {other_steps + division} "
        f"deductions ({share:.1%} filler)"
    )
    print("  NOTE the other steps are every non-division deduction, NOT deductions the constraint")
    print("       caused. A causal count needs a counterfactual solve; see _steps().")
    print(f"  {clean} of {len(decided)} directions carry no division filler at all, against 9 of 11 before")


def _report_gate(rows: list[Row]) -> None:
    print("")
    print("=== THE PUBLICATION GATE AGAINST THE ARITHMETIC VERIFIER ===")
    print("  Two different questions, so two fields. A board can pass every arithmetic layer and be")
    print("  refused for plausibility or a disagreeing official total.")
    for arm in ARMS:
        produced = [row for row in rows if row.arm == arm and row.reached]
        if not produced:
            continue
        verified = sum(1 for row in produced if row.verified)
        publishable = sum(1 for row in produced if row.publishable)
        print(f"  {arm:<10}{len(produced):>5} produced, {verified:>4} verified, {publishable:>4} publishable")
        gap = Counter(row.refused_by for row in produced if row.verified and not row.publishable)
        for refusal, count in gap.most_common(3):
            print(f"       {count:>4}  verified but refused by the gate: {refusal}")


def report(rows: list[Row]) -> None:
    directions = {(row.game, row.offense) for row in rows}
    print("")
    print(f"{len(directions)} directions x {len(SEEDS)} seeds x {len(TARGETS)} targets x {len(ARMS)} arms")
    _report_coverage(rows, directions)
    _report_tradeoff(rows)
    _report_filler(rows)
    _report_gate(rows)

    print("")
    print("=== STALL CEILING AND BLANKS, publishable boards only ===")
    for arm in ARMS:
        publishable = [row for row in rows if row.arm == arm and row.publishable]
        if not publishable:
            print(f"  {arm:<10}nothing publishable")
            continue
        ceilings = [
            max(item.stalls for item in publishable if (item.game, item.offense) == board)
            for board in {(item.game, item.offense) for item in publishable}
        ]
        print(
            f"  {arm:<10}ceiling median {statistics.median(ceilings):.0f}, max {max(ceilings)}; "
            f"blanks median {statistics.median([item.blanks for item in publishable]):.0f}"
        )


RENAMED_FIELDS = {"causal": "other_steps"}
"""Fields whose *name* changed after a run was recorded. The values did not.

⚠⚠ **The recorded artefact is not rewritten to match a rename, and that is the point.**
`confirm.json` is 2,160 rows produced by the run that decided the adoption; it is the evidence, and
evidence edited to agree with later code is no longer evidence of anything. v30-P1-01 renamed `causal`
to `other_steps` because the old name asserted causation the number does not establish — a correction to
the *claim*, not to the measurement — so the file keeps the key it was written with and the reader
knows both names.

⚠️ **This is a rename shim and must never become a value shim.** A missing field, a changed unit or a
value that needs adjusting is a different run, and the honest answer to those is to re-run rather than
to translate on the way in.
"""


def _migrate(row: dict) -> dict:
    return {RENAMED_FIELDS.get(name, name): value for name, value in row.items()}


def main() -> None:
    # ⚠️ The pool rule applied with the slots, which is the whole point: without them
    # `find_violations` skips the batting-order check and the cohort would include the 35.
    sample = [
        item
        for item in load(SAMPLE_PER_DECADE, gated=True, gate=ZERO_DENSITY_GATE)
        if not find_violations(item.direction, tuple(item.slots))
    ]
    if not sample:
        message = "no directions survived the gate and the pool rule; the filters here are wrong"
        raise SystemExit(message)
    print(f"{len(sample)} directions through the gate and the batting-order pool rule")
    # ⚠️ Before the expensive half, not after: the point is to fail in a second rather than in an hour.
    _preflight(sample[0])

    rows: list[Row] = []
    for number, loaded in enumerate(sample, start=1):
        for seed in SEEDS:
            rows.extend(_measure(loaded, seed))
        if number % 5 == 0:
            print(f"  {number}/{len(sample)} measured", flush=True)

    # Persisted before formatting: the rows are the expensive half and everything below can fail.
    (_HERE / "confirm.json").write_text(
        json.dumps([asdict(row) for row in rows], indent=1, sort_keys=True), encoding="utf-8", newline="\n"
    )
    print(f"wrote {len(rows)} rows to confirm.json before formatting anything")
    report(rows)


if __name__ == "__main__":
    if "--report-only" in sys.argv[1:]:
        report([Row(**_migrate(row)) for row in json.loads((_HERE / "confirm.json").read_text(encoding="utf-8"))])
    else:
        main()
