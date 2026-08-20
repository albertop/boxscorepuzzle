"""Does the batting order determine every plate-appearance count from the team total?

**The hypothesis.** The order is cyclic and cannot be skipped, so if a game ends with slot 5 batting
last, slots 1 to 5 have come up one more time than slots 6 to 9. Three claims, in increasing strength:

  weak       PA(N+1) <= PA(N) for every N from 1 to 8 — it never rises going down the order
  strong     exactly one step down, of exactly one, and never two steps
  determined given the team's PA total, the whole per-slot distribution follows from the cycle

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

from measure import (  # noqa: E402
    ACCEPTED_LITERAL,
    CONNECTION,
    CONTRIBUTED,
    SEASON_WINDOW,
    SHAPE_CTE,
    eligibility,
)

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


def _rows(cursor: object, provenance: str = "") -> list:
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
    cohort = eligibility(seasons=f"g.SEASON BETWEEN {SEASON_WINDOW[0]} AND {SEASON_WINDOW[1]}")
    if provenance:
        original = f"AND p.is_deduced = 0 AND p.source_type IN ({ACCEPTED_LITERAL})"
        # Not an `assert`: `python -O` removes assertions, and the failure this guards is an arm that
        # silently measures the pool while claiming to measure an excluded population.
        if original not in cohort:
            message = "the provenance rule moved; this arm would silently measure the pool instead"
            raise SystemExit(message)
        cohort = cohort.replace(original, provenance)
    slot_sums = ", ".join(f"SUM(CASE WHEN r.SLOT_CT = {n} THEN r.B_PA ELSE 0 END) AS s{n}" for n in range(1, SLOTS + 1))
    query = f"""
    {SHAPE_CTE},
    admissible AS (
      SELECT g.GAME_ID, o.TEAM_ID, g.SEASON, g.INN_CT, g.METHOD_RECORD_CD,
             CASE WHEN o.TEAM_ID = g.HOME_TEAM_ID THEN 1 ELSE 0 END AS offense_is_home,
             prov.source_type
      {cohort})
    SELECT a.GAME_ID, a.TEAM_ID, a.SEASON, a.INN_CT, a.METHOD_RECORD_CD, a.offense_is_home,
           a.source_type, {slot_sums}
    FROM admissible a
    JOIN dbo.retroDailyReg r ON r.GAME_ID = a.GAME_ID AND r.TEAM_ID = a.TEAM_ID
    WHERE r.SLOT_CT BETWEEN 1 AND {SLOTS}
    GROUP BY a.GAME_ID, a.TEAM_ID, a.SEASON, a.INN_CT, a.METHOD_RECORD_CD, a.offense_is_home, a.source_type
    """  # noqa: S608 - every interpolation is a module constant or a loop index
    return cursor.execute(query).fetchall()


def _report(name: str, rows: list) -> Counter:
    kinds: Counter = Counter()
    exceptions: list = []
    extra_innings = walkoff_side = 0

    for row in rows:
        slots = tuple(row[7 : 7 + SLOTS])
        broken = faults(slots)
        if row.INN_CT and row.INN_CT > SLOTS:
            extra_innings += 1
        if row.offense_is_home:
            walkoff_side += 1
        if broken:
            kinds[", ".join(broken)] += 1
            exceptions.append((row, slots, broken))

    total = len(rows)
    clean = total - len(exceptions)
    print("")
    print(f"=== {name} ===")
    if not total:
        # ⚠️ Says which of the two it is. "No rows" from a cohort that cannot exist is a different fact
        # from "no rows" out of a cohort that should have had some, and one report cannot mean both.
        print("  NO DIRECTIONS AT ALL. Either this population is empty in the database, or this arm's")
        print("  predicate cannot match anything. Both are silence; only the first is a result.")
        return kinds
    print(f"  {total:,} directions, {extra_innings:,} in extra innings, {walkoff_side:,} batting last")
    print(f"  hold all three claims: {clean:,} ({100.0 * clean / total:.4f}%)")
    print(f"  exceptions:            {len(exceptions):,} ({100.0 * len(exceptions) / total:.4f}%)")
    for kind, count in kinds.most_common():
        print(f"     {count:>7,}  {kind}")

    if not exceptions:
        return kinds
    print("")
    print(f"  --- exceptions, {min(EXAMPLES, len(exceptions))} of {len(exceptions):,} listed ---")
    print(f"  {'game':<14} {'yr':<5} {'inn':<4} {'m':<2} {'home':<5} {'source':<22} slots -> predicted")
    for row, slots, broken in exceptions[:EXAMPLES]:
        shown = "".join(f"{value:>3}" for value in slots)
        expect = "".join(f"{value:>3}" for value in predicted(sum(slots)))
        print(
            f"  {row.GAME_ID:<14} {row.SEASON:<5} {row.INN_CT or 0:<4} {row.METHOD_RECORD_CD or 0:<2} "
            f"{'yes' if row.offense_is_home else 'no':<5} {(row.source_type or '')[:22]:<22} "
            f"{shown}  ->{expect}   [{'; '.join(broken)}]"
        )
    if len(exceptions) > EXAMPLES:
        print(f"  ({len(exceptions) - EXAMPLES:,} further exceptions not listed; the counts above are complete)")

    # ⚠️ Where the exceptions cluster is the thing that separates a rule of baseball from a data defect.
    print("")
    print("  --- where the exceptions are ---")
    for label, key in (
        ("by decade", lambda r: (r.SEASON // 10) * 10),
        ("by source", lambda r: r.source_type),
        ("by method record", lambda r: r.METHOD_RECORD_CD),
        ("extra innings", lambda r: bool(r.INN_CT and r.INN_CT > SLOTS)),
        ("batting last", lambda r: bool(r.offense_is_home)),
    ):
        spread = Counter(key(row) for row, _, _ in exceptions)
        whole = Counter(key(row) for row in rows)
        parts = ", ".join(
            f"{value}: {count:,}/{whole[value]:,} ({100.0 * count / whole[value]:.2f}%)"
            for value, count in sorted(spread.items(), key=lambda item: str(item[0]))
        )
        print(f"    {label:<18} {parts}")
    return kinds


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


def _what_it_buys(cursor: object) -> None:
    """What the constraint would be worth, without implementing anything.

    ⚠️ **The payoff is cut by substitutions, and this is the same trap the hypothesis itself carries.**
    The constraint determines PA per *slot*. The board has a row per *player*. A slot occupied by one man
    all game has its row's PA fully determined by the team total; a slot shared by a starter and a
    substitute gets only their **sum**, which is a weaker statement about two cells rather than a value
    for either.

    So the honest measure of what it buys is not "nine cells": it is **how many batting rows are alone in
    their slot**. Measured, not estimated, and measured before anything is built.
    """
    cohort = eligibility(seasons=f"g.SEASON BETWEEN {SEASON_WINDOW[0]} AND {SEASON_WINDOW[1]}")
    rows = cursor.execute(f"""
    {SHAPE_CTE},
    admissible AS (SELECT g.GAME_ID, o.TEAM_ID {cohort}),
    occupancy AS (
      SELECT a.GAME_ID, a.TEAM_ID, r.SLOT_CT, COUNT(*) AS men
      FROM admissible a
      JOIN dbo.retroDailyReg r ON r.GAME_ID = a.GAME_ID AND r.TEAM_ID = a.TEAM_ID
      WHERE r.SLOT_CT BETWEEN 1 AND {SLOTS} AND {CONTRIBUTED.replace("B_", "r.B_")}
      GROUP BY a.GAME_ID, a.TEAM_ID, r.SLOT_CT)
    SELECT men, COUNT(*) AS slots, SUM(men) AS rows_in_them
    FROM occupancy GROUP BY men ORDER BY men
    """).fetchall()  # noqa: S608 - module constants only

    print("")
    print("=== WHAT IT WOULD BUY, IF THE POOL RULE MADE IT EXACT ===")
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
        pool = _rows(cursor, "")
        _report("THE POOL - accepted, non-deduced sources", pool)

        # ⚠️ Measured separately and never mixed in. A violation among an excluded population
        # **confirms the exclusion** rather than refuting the hypothesis, so pooling them would make the
        # rule look weaker than it is and pooling them silently would be worse.
        for label, rule in (
            (
                "DEDUCED FILES - excluded by S32. Reconstructions, so a violation here confirms the rule",
                "AND p.is_deduced = 1 AND p.source_type IN ('EDA', 'EDN', 'EDF')",
            ),
        ):
            _report(label, _rows(cursor, rule))

        _negro_leagues(cursor)
        _what_it_buys(cursor)

    print("")
    print("NOTE: nothing is implemented from this. The solver does not have the constraint and does not")
    print("  get it until the operator decides. A rule true 99.9% of the time is not a constraint, it is")
    print("  a trap: the solver would deduce a wrong value on the exceptional board and no identity")
    print("  check could see it. If it holds only mostly, the answer is a pool rule, not a weaker rule.")


if __name__ == "__main__":
    main()
