"""Does the batting order determine every plate-appearance count from the team total?

**The hypothesis.** The order is cyclic and cannot be skipped, so if a game ends with slot 5 batting
last, slots 1 to 5 have come up one more time than slots 6 to 9. Three claims, in increasing strength:

  weak       PA(N+1) <= PA(N) for every N from 1 to 8 — it never rises going down the order
  strong     **at most one** cut point, and where there is one it drops by exactly one
  determined given the team's PA total, the whole per-slot distribution follows from the cycle

⚠️ **"At most one", not "exactly one", and the difference is not pedantry.** A total divisible by nine
is a whole number of complete turns, so every slot holds the same value and there is **no** cut point —
`4 4 4 4 4 4 4 4 4` is the cleanest possible case and the literal wording called it a violation. The
prose said one thing and `faults()` did another; the predicate was right and the sentence was wrong,
which is the harder direction to notice because the numbers looked correct.

If the third holds, **the total determines every individual value**: 38 plate appearances is four full
turns of nine plus two, so slots 1 and 2 have 5 and the rest have 4. The solver does not have this
constraint and it is strong — `PA` is the column that ties the row identity together.

⚠️ **PA is per SLOT, never per player.** A slot is the sum of everyone who occupied it, starters and
substitutes together; a slot holding three pitchers has one figure. Measured per player the hypothesis
is false immediately, because a substitute obviously bats fewer times than the man he replaced. `SLOT_CT`
is what groups them.

⚠️ **The whole pool, not a sample.** This is a structural claim about baseball, and **one counterexample
matters more than a rate**. A 99.9% rate with 200 exceptions is a different answer from 100%: a
constraint that is true almost always is not a constraint, it is a trap — the solver would deduce a
value that is wrong on the exceptional board, and §22's guarantee would break in a way no identity check
could catch. If it holds only mostly, the answer is a **pool rule** that excludes the failures, never a
weaker constraint.

⚠️ **The exceptions are the finding.** They are listed rather than aggregated, with the game, the season,
the actual distribution and the provenance source type, because a rate cannot tell a data defect from a
rule of baseball.

Read-only against DGL. Run from `forge/`.
"""

import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))
sys.path.insert(0, str(_ROOT / "forge" / "src"))

# ⚠️ `ZERO_DENSITY_GATE` comes from `boxscore_domain`, which is where it is decided — it used to be
# imported from `measure`, which only had it because `measure` imported it too. A domain constant
# reached through a research module is a third place for a value §5 defines once, and it broke the day
# `measure` stopped needing it for itself (2026-08-22, the pool moving to `boxscore_forge.pool`).
from measure import (  # noqa: E402
    CONNECTION,
    CONTRIBUTED,
    PROVENANCE_LITERAL,
    SEASON_WINDOW,
    SHAPE_CTE,
    eligibility,
    zero_density_clause,
)

from boxscore_domain import ZERO_DENSITY_GATE  # noqa: E402


def candidates(*, gated: bool, provenance: str = "") -> str:
    """The candidate population, with §5's zero-density gate applied or deliberately not.

    ⚠️ **The first run of this script applied no gate at all** and reported 371,802 directions — the
    ungated population — while the decision it was written to support is about the **100,226** the
    generator actually ships from. That is the same defect this project had just fixed twice in
    `footnote-multiplicity`, in a script written by the same hand hours later: *a research denominator
    and the generator have to mean the same thing.*

    Both are reported now, and the difference between them is the point rather than an accident:

    - **gated** is the production pool. **The pool rule is decided from this one.**
    - **ungated** is a wider population for the structural claim — more evidence about baseball, and
      **not** evidence about what ships. Labelled, never mixed.
    """
    built = eligibility(
        seasons=f"g.SEASON BETWEEN {SEASON_WINDOW[0]} AND {SEASON_WINDOW[1]}",
        gate_clause=zero_density_clause(ZERO_DENSITY_GATE) if gated else "",
    )
    if provenance:
        # ⚠️⚠️ **`PROVENANCE_LITERAL`, and the rename is the point rather than a detail.** The postseason
        # work split one list in two: `PROVENANCE_SOURCES` is what a `dbo.retroGameProvenance` row may
        # say and is what `eligibility()` interpolates; `ACCEPTED_SOURCES` is the wider set the
        # publication gate accepts, because the postseason has no provenance row and is admitted by a
        # season floor instead. The anchor below has to be built from what the SQL actually contains.
        #
        # ⚠️ This file imported the old name and **died with `ImportError` before printing anything** —
        # so the guard immediately below, which exists to catch exactly "the provenance rule moved",
        # never got the chance to fire. A check that cannot be reached is not a weaker check; it is
        # absent, and the pool rule was decided from this instrument. v36-P2-03.
        original = f"AND p.is_deduced = 0 AND p.source_type IN ({PROVENANCE_LITERAL})"
        # Not an `assert`: `python -O` removes assertions, and the failure this guards is an arm that
        # silently measures the pool while claiming to measure an excluded population.
        if original not in built:
            message = "the provenance rule moved; this arm would silently measure the pool instead"
            raise SystemExit(message)
        built = built.replace(original, provenance)
    return built


SLOTS = 9
EXAMPLES = 25
"""How many exceptions of each kind to print in full. The counts are complete; this bounds the listing.

⚠️ Whatever is dropped is **stated in the output**. A report that silently truncates reads as one that
found that many.
"""


def predicted(total: int) -> tuple[int, ...]:
    """What the cycle says the nine slots hold, given the team's plate-appearance total.

    Four full turns and two over means slots 1 and 2 bat five times and the rest four.
    """
    base, over = divmod(total, SLOTS)
    return tuple(base + 1 if slot <= over else base for slot in range(1, SLOTS + 1))


def faults(slots: tuple[int, ...]) -> list[str]:
    """Which of the three claims this direction breaks."""
    found = []
    if any(slots[i + 1] > slots[i] for i in range(SLOTS - 1)):
        found.append("rises")
    steps = [slots[i] - slots[i + 1] for i in range(SLOTS - 1)]
    if any(step > 1 for step in steps):
        found.append("drops more than one")
    if sum(1 for step in steps if step != 0) > 1:
        found.append("more than one cut point")
    if slots != predicted(sum(slots)):
        found.append("not determined by the total")
    return found


def _rows(cursor: object, *, gated: bool, provenance: str = "") -> list:
    """One row per direction: the nine slot totals, and what is needed to explain an exception.

    ⚠️ `r` for the daily rows, because `eligibility()` already binds `d` to the *defensive* team's shape.
    An alias collision here would have silently summed the wrong side.

    ⚠️ **`provenance` replaces the whole rule, flag and source list together.** The first version swapped
    only `is_deduced = 0` for `= 1` and returned nothing — and the report said *the filters in this script
    are wrong*, which was a broken arm describing itself as a broken script. Deduced files are excluded
    **twice**: by the flag and by their source type, which is `EDA`/`EDN`/`EDF` rather than `EVA`/`EVN`/
    `EVF`. Asking for a deduced game with an accepted source type is asking for the empty set, and an arm
    that cannot return a row is not a null result.
    """
    built = candidates(gated=gated, provenance=provenance)
    slot_sums = ", ".join(f"SUM(CASE WHEN r.SLOT_CT = {n} THEN r.B_PA ELSE 0 END) AS s{n}" for n in range(1, SLOTS + 1))
    query = f"""
    {SHAPE_CTE},
    admissible AS (
      SELECT g.GAME_ID, o.TEAM_ID, g.SEASON, g.INN_CT, g.METHOD_RECORD_CD,
             CASE WHEN o.TEAM_ID = g.HOME_TEAM_ID THEN 1 ELSE 0 END AS offense_is_home,
             -- ⚠️ **Which side actually made the game's last plate appearance**, which is not the same
             -- as which side is at home. When the home team leads after the top of the ninth they do
             -- not bat at all, and Retrosheet marks that half-inning `x` at the end of the home line
             -- score. So home batted last exactly when their line score does *not* end in `x`.
             --
             -- The first version of this script read `offense_is_home` and called it "batting last".
             -- The split it reported was the home/away split, which is near enough 50/50 to look like
             -- an answer. **A name is not the thing** — the fourth instance of that class here.
             CASE WHEN (CASE WHEN o.TEAM_ID = g.HOME_TEAM_ID THEN 1 ELSE 0 END)
                       <> (CASE WHEN RIGHT(l.HomeLineScore, 1) = 'x' THEN 1 ELSE 0 END)
                  THEN 1 ELSE 0 END AS batted_last,
             prov.source_type
      {built})
    SELECT a.GAME_ID, a.TEAM_ID, a.SEASON, a.INN_CT, a.METHOD_RECORD_CD, a.offense_is_home,
           a.batted_last, a.source_type, {slot_sums}
    FROM admissible a
    JOIN dbo.retroDailyReg r ON r.GAME_ID = a.GAME_ID AND r.TEAM_ID = a.TEAM_ID
    WHERE r.SLOT_CT BETWEEN 1 AND {SLOTS}
    GROUP BY a.GAME_ID, a.TEAM_ID, a.SEASON, a.INN_CT, a.METHOD_RECORD_CD, a.offense_is_home,
             a.batted_last, a.source_type
    """  # noqa: S608 - every interpolation is a module constant or a loop index
    return cursor.execute(query).fetchall()


def _report(name: str, rows: list) -> tuple[Counter, list]:
    kinds: Counter = Counter()
    exceptions: list = []
    extra_innings = last_up = 0

    for row in rows:
        slots = tuple(row[8 : 8 + SLOTS])
        broken = faults(slots)
        if row.INN_CT and row.INN_CT > SLOTS:
            extra_innings += 1
        if row.batted_last:
            last_up += 1
        if broken:
            kinds[", ".join(broken)] += 1
            exceptions.append((row, slots, broken))

    broken_keys = [(row.GAME_ID, row.TEAM_ID) for row, _, _ in exceptions]
    total = len(rows)
    clean = total - len(exceptions)
    print("")
    print(f"=== {name} ===")
    if not total:
        # ⚠️ Says which of the two it is. "No rows" from a cohort that cannot exist is a different fact
        # from "no rows" out of a cohort that should have had some, and one report cannot mean both.
        print("  NO DIRECTIONS AT ALL. Either this population is empty in the database, or this arm's")
        print("  predicate cannot match anything. Both are silence; only the first is a result.")
        return kinds, broken_keys
    print(f"  {total:,} directions, {extra_innings:,} in extra innings, {last_up:,} batted last")
    print(f"  hold all three claims: {clean:,} ({100.0 * clean / total:.4f}%)")
    print(f"  exceptions:            {len(exceptions):,} ({100.0 * len(exceptions) / total:.4f}%)")
    for kind, count in kinds.most_common():
        print(f"     {count:>7,}  {kind}")

    if not exceptions:
        return kinds, broken_keys
    print("")
    print(f"  --- exceptions, {min(EXAMPLES, len(exceptions))} of {len(exceptions):,} listed ---")
    print(f"  {'game':<14} {'yr':<5} {'inn':<4} {'m':<2} {'last':<5} {'source':<22} slots -> predicted")
    for row, slots, broken in exceptions[:EXAMPLES]:
        shown = "".join(f"{value:>3}" for value in slots)
        expect = "".join(f"{value:>3}" for value in predicted(sum(slots)))
        print(
            f"  {row.GAME_ID:<14} {row.SEASON:<5} {row.INN_CT or 0:<4} {row.METHOD_RECORD_CD or 0:<2} "
            f"{'yes' if row.batted_last else 'no':<5} {(row.source_type or '')[:22]:<22} "
            f"{shown}  ->{expect}   [{'; '.join(broken)}]"
        )
    if len(exceptions) > EXAMPLES:
        print(f"  ({len(exceptions) - EXAMPLES:,} further exceptions not listed; the counts above are complete)")

    # ⚠️ Where the exceptions cluster is the thing that separates a rule of baseball from a data defect.
    print("")
    print("  --- where the exceptions are (every category, including those with none) ---")
    for label, key in (
        ("by decade", lambda r: (r.SEASON // 10) * 10),
        ("by source", lambda r: r.source_type),
        ("by method record", lambda r: r.METHOD_RECORD_CD),
        ("extra innings", lambda r: bool(r.INN_CT and r.INN_CT > SLOTS)),
        ("home offense", lambda r: bool(r.offense_is_home)),
        ("batted last", lambda r: bool(r.batted_last)),
    ):
        spread = Counter(key(row) for row, _, _ in exceptions)
        whole = Counter(key(row) for row in rows)
        # ⚠️ **Over the whole population, not over the exceptions.** This iterated `spread`, so a
        # category with **no** exceptions disappeared from the table entirely — and this table exists
        # for exactly one purpose, to say whether failures cluster. Every one of the five is a
        # non-extra-innings direction, so the honest line is `True: 0/6,276` beside `False: 5/93,950`;
        # what printed was the second alone, which reads as a neutral partial split rather than as the
        # one-sided result it is. **The absence of a reading is not a reading of absence**, and here it
        # suppressed the strongest clustering evidence in the report.
        parts = ", ".join(
            f"{value}: {spread[value]:,}/{whole[value]:,} ({100.0 * spread[value] / whole[value]:.2f}%)"
            for value in sorted(whole, key=str)
        )
        print(f"    {label:<18} {parts}")
    return kinds, broken_keys


def _negro_leagues(cursor: object) -> None:
    """Why the Negro Leagues arm is empty, said as a result rather than left as silence.

    ⚠️ **They are excluded twice and only one of the two is §32.** The source rule removes `EVR`, and so
    does the game-log join — independently, and more completely. An arm reporting "no rows" cannot tell
    a population that is empty from a predicate that cannot match, so it asks.
    """
    row = cursor.execute("""
    SELECT COUNT(*) AS games, SUM(has_log) AS with_a_game_log
    FROM (
      SELECT CASE WHEN l.GAME_ID IS NULL THEN 0 ELSE 1 END AS has_log
      FROM dbo.retroGamesReg g
      JOIN dbo.retroGameProvenance p ON p.GAME_ID = g.GAME_ID
      LEFT JOIN dbo.retroGameLogs l ON l.GAME_ID = g.GAME_ID
      WHERE p.source_type = 'EVR') AS seen
    """).fetchone()
    print("")
    print("=== NEGRO LEAGUES (EVR) - why that arm is empty ===")
    print(f"  {row.games:,} games, {row.with_a_game_log:,} of them with a game-log row.")
    print("  So the hypothesis cannot be tested on them, and the reason is not S32's source rule: they")
    print("  carry no retroGameLogs row at all, which is the join the pool needs for its independent")
    print("  cross-check. Two exclusions for one population, and the game log is the stricter of them.")


def _what_it_buys(cursor: object, broken: list) -> None:
    """What the constraint would be worth, without implementing anything.

    ⚠️ **The payoff is cut by substitutions, and this is the same trap the hypothesis itself carries.**
    The constraint determines PA per *slot*. The board has a row per *player*. A slot occupied by one man
    all game has its row's PA fully determined by the team total; a slot shared by a starter and a
    substitute gets only their **sum**, which is a weaker statement about two cells rather than a value
    for either.

    So the honest measure of what it buys is not "nine cells": it is **how many batting rows are alone in
    their slot**. Measured, not estimated, and measured before anything is built.
    """
    # ⚠️ **The post-rule cohort, because that is what the heading claims.** This measured the gated
    # cohort while calling itself the payoff "if the pool rule made it exact" — the five directions the
    # rule removes were still in the denominator. The difference is tiny today and that is not the
    # point: the number is named for a population it did not measure, and exception growth would widen
    # the gap silently. Derived from the run rather than hard-coded, so the two cannot drift apart.
    # ⚠️⚠️ **Parameters, and the `noqa` below used to say these were module constants.** (v36-P2-11)
    #
    # `broken` is rows returned by the previous query — database content — and it was being formatted
    # straight into the predicate as quoted literals. `docs/python-conventions.md` is absolute about
    # this: *parameterized queries only, ever, including in throwaway scripts*. A `GAME_ID` carrying an
    # apostrophe would at minimum break the query.
    #
    # The practical exposure is small: a local, read-only database this project loads itself. **The
    # real cost was the false justification**, sitting in the one place a reader or the lint ratchet
    # would look to decide whether the suppression was earned. A suppression that misdescribes what it
    # is suppressing is worse than none, because it answers the question nobody then asks.
    #
    # Placeholders are generated from the *length* of `broken` — that count is genuinely a program
    # value — and the identifiers travel as bound parameters.
    excluded = " AND NOT (" + " OR ".join(["(a.GAME_ID = ? AND a.TEAM_ID = ?)"] * len(broken)) + ")" if broken else ""
    exclusions = [value for pair in broken for value in pair]
    # ⚠️ **No suppression, and that is the point of the change.** This carried an S608 waiver claiming
    # *module constants only* while interpolating database rows — a false justification sitting exactly
    # where a reader or the ratchet would look to decide whether the waiver was earned. The identifiers
    # are bound parameters now; the S608 that remains is ruff seeing an f-string build a query, the
    # same as the five sites in `difficulty-metrics/measure.py`, and it is counted in the baseline
    # rather than argued away. v36-P2-11.
    #
    # ⚠️ The old waiver is described rather than quoted, because **ruff reads a directive spelled inside
    # a comment as a directive** and reported the quotation itself as an unused one.
    rows = cursor.execute(
        f"""
    {SHAPE_CTE},
    admissible AS (SELECT g.GAME_ID, o.TEAM_ID {candidates(gated=True)}),
    occupancy AS (
      SELECT a.GAME_ID, a.TEAM_ID, r.SLOT_CT, COUNT(*) AS men
      FROM admissible a
      JOIN dbo.retroDailyReg r ON r.GAME_ID = a.GAME_ID AND r.TEAM_ID = a.TEAM_ID
      WHERE r.SLOT_CT BETWEEN 1 AND {SLOTS} AND {CONTRIBUTED.replace("B_", "r.B_")}{excluded}
      GROUP BY a.GAME_ID, a.TEAM_ID, r.SLOT_CT)
    SELECT men, COUNT(*) AS slots, SUM(men) AS rows_in_them
    FROM occupancy GROUP BY men ORDER BY men
    """,
        # ⚠️ The only values from the database. Everything else interpolated above is a module constant
        # or a count, which is what the suppression now honestly covers.
        *exclusions,
    ).fetchall()

    print("")
    print(f"=== WHAT IT WOULD BUY (production pool, gated, {len(broken)} rule-excluded directions removed) ===")
    total_slots = sum(row.slots for row in rows)
    total_rows = sum(row.rows_in_them for row in rows)
    if not total_slots:
        print("  no slots at all; this query is wrong")
        return
    alone = next((row for row in rows if row.men == 1), None)
    print("  men in a slot   slots            batting rows in them")
    for row in rows:
        share = 100.0 * row.slots / total_slots
        print(f"     {row.men:<12} {row.slots:>10,} ({share:>5.2f}%)  {row.rows_in_them:>10,}")
    if alone is not None:
        share = 100.0 * alone.rows_in_them / total_rows
        print("")
        print(f"  {alone.rows_in_them:,} of {total_rows:,} batting rows ({share:.1f}%) are alone in their slot.")
        print("  For those, the team's PA total would determine the cell outright. For the rest the")
        print("  constraint gives the SUM of the rows sharing a slot, which constrains two cells without")
        print("  fixing either - still useful to a solver, and not the same thing.")
    print("")
    print("  NOTE: this is what the constraint DETERMINES, not how many cells could then be erased.")
    print("  Those are different numbers and the second one needs the solver to have the constraint,")
    print("  which is exactly what is not being built yet.")


def main() -> None:
    import pyodbc  # noqa: PLC0415

    with pyodbc.connect(CONNECTION) as connection:
        cursor = connection.cursor()
        print("THE HYPOTHESIS: the batting order is cyclic, so the team's PA total determines every slot.")
        print("Measured over the whole admissible pool, not a sample. One counterexample outweighs a rate.")
        _, broken = _report(
            "THE PRODUCTION POOL - caps, provenance, game log, season window, and S5's zero-density gate."
            " THE POOL RULE IS DECIDED FROM THIS ONE",
            _rows(cursor, gated=True),
        )
        # ⚠️ Wider, and labelled as not-the-pool. More evidence about baseball; none about what ships.
        _report(
            "UNGATED - the same rules WITHOUT the zero-density gate. NOT the production pool: structural evidence only",
            _rows(cursor, gated=False),
        )

        # ⚠️ Measured separately and never mixed in. A violation among an excluded population
        # **confirms the exclusion** rather than refuting the hypothesis, so pooling them would make the
        # rule look weaker than it is and pooling them silently would be worse.
        for label, rule in (
            (
                "DEDUCED FILES - excluded by S32. Reconstructions, so a violation here confirms the rule",
                "AND p.is_deduced = 1 AND p.source_type IN ('EDA', 'EDN', 'EDF')",
            ),
        ):
            _report(label, _rows(cursor, gated=True, provenance=rule))

        _negro_leagues(cursor)
        _what_it_buys(cursor, broken)

    print("")
    print("NOTE: nothing is implemented from this. The solver does not have the constraint and does not")
    print("  get it until the operator decides. A rule true 99.9% of the time is not a constraint, it is")
    print("  a trap: the solver would deduce a wrong value on the exceptional board and no identity")
    print("  check could see it. If it holds only mostly, the answer is a pool rule, not a weaker rule.")


if __name__ == "__main__":
    main()
