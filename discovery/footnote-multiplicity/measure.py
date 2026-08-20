"""How often one batter carries the same footnote term twice in one game.

⚠️ **This decides a correctness question, not a formatting one.** The footnote line prints `SH: 2`,
which reads as *a sacrifice in slot 2* — the number is a slot reference and the count is absent
entirely. If a row can carry two of the same term, the player cannot tell one from two, and the row
identity `PA = AB + BB + HBP + SF + SH + CI` has no other route to the value. **Boards like that are
unsolvable today**, and nothing in the four validation layers can see it: every total still balances,
because the arithmetic is right and only the presentation is lossy.

So the question is not *is the format nicer with a count*. It is **does the case occur**, and if it
does, every board containing one is broken.

Counted per **row**, not per slot: `slot_references()` gives each batting row its own reference (`9a`,
`9b`), so attribution is already row-level. A slot holding a starter and a substitute with one sacrifice
each is two rows with one apiece and is not this case.

⚠️ **Counted against the pool the board actually draws from**, because a rate over rows nobody will
ever see is not the rate that matters. That means §5's zero-density gate, the roster caps and the
provenance rule — and the first version of this file **said exactly that while applying only the caps.**
It printed `gate applied downstream` and imported the gate constant to put in a label. The figures it
published described a cohort it had never measured, and they reached five other files before a review
compared its CTE with the loader's.

The cohort is not reimplemented here any more. `SHAPE_CTE` and `zero_density_clause()` come from the
loader, so the measurement and the generator cannot describe different pools.

Read-only against DGL. Run from `forge/`.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))
sys.path.insert(0, str(_ROOT / "forge" / "src"))

from measure import ACCEPTED_SOURCES, CONNECTION, CONTRIBUTED, SHAPE_CTE, zero_density_clause  # noqa: E402

from boxscore_domain import BATTER_CAP, PITCHER_CAP, ZERO_DENSITY_GATE  # noqa: E402

TERMS = {"hit_by_pitch": "B_HP", "sacrifice_flies": "B_SF", "sacrifice_hits": "B_SH", "catcher_interference": "B_XI"}


def main() -> None:
    import pyodbc  # noqa: PLC0415

    accepted = ", ".join(f"'{source}'" for source in ACCEPTED_SOURCES)
    # The offensive side of an admissible direction: a team whose roster fits and whose game is one the
    # pool accepts. The zero-density half of the gate needs both sides, so it is applied as a join on
    # the shape table exactly as `load()` does.
    query = f"""
    {SHAPE_CTE},
    admissible AS (
      SELECT o.GAME_ID, o.TEAM_ID
      FROM shape o
      JOIN shape d ON d.GAME_ID = o.GAME_ID AND d.TEAM_ID <> o.TEAM_ID
      JOIN dbo.retroGamesReg g ON g.GAME_ID = o.GAME_ID
      CROSS APPLY (SELECT TOP 1 p.source_type FROM dbo.retroGameProvenance p
                   WHERE p.GAME_ID = g.GAME_ID AND p.is_deduced = 0 AND p.source_type IN ({accepted})
                   ORDER BY p.source_type) AS prov
      WHERE o.batters <= {BATTER_CAP} AND d.pitchers <= {PITCHER_CAP}
        {zero_density_clause(ZERO_DENSITY_GATE)})
    SELECT COUNT(*) AS rows_total,
           COUNT(DISTINCT a.GAME_ID) AS games,
           {", ".join(f"SUM(CASE WHEN d.{col} > 1 THEN 1 ELSE 0 END) AS many_{name}" for name, col in TERMS.items())},
           {", ".join(f"SUM(CASE WHEN d.{col} > 0 THEN 1 ELSE 0 END) AS any_{name}" for name, col in TERMS.items())},
           {", ".join(f"MAX(d.{col}) AS max_{name}" for name, col in TERMS.items())},
           SUM(CASE WHEN {" OR ".join(f"d.{col} > 1" for col in TERMS.values())} THEN 1 ELSE 0 END) AS affected_rows
    FROM admissible a
    JOIN dbo.retroDailyReg d ON d.GAME_ID = a.GAME_ID AND d.TEAM_ID = a.TEAM_ID
    WHERE {CONTRIBUTED.replace("B_", "d.B_")}
    """  # noqa: S608 - every interpolation is a module constant; nothing here is reachable from input

    with pyodbc.connect(CONNECTION) as connection:
        row = connection.cursor().execute(query).fetchone()

    columns = [description[0] for description in connection.cursor().execute(query).description]
    found = dict(zip(columns, row, strict=True))
    rows_total = found["rows_total"]
    if not rows_total:
        message = "no admissible batting rows at all; the filters in this script are wrong"
        raise SystemExit(message)

    print(f"caps {BATTER_CAP} batters / {PITCHER_CAP} pitchers, zero-density gate {ZERO_DENSITY_GATE:.0%} APPLIED")
    print(f"{rows_total:,} batting rows across {found['games']:,} admissible games")
    print("")
    print("term                  rows with >1   share of all rows   share of rows carrying the term   max")
    for name in TERMS:
        many, carrying, top = found[f"many_{name}"], found[f"any_{name}"], found[f"max_{name}"]
        of_carrying = f"{100.0 * many / carrying:.2f}%" if carrying else "n/a"
        print(f"  {name:<20} {many:>10,}   {100.0 * many / rows_total:>16.4f}%   {of_carrying:>31}   {top:>3}")
    print("")
    # ⚠️ **One OR, not a sum of the per-term counts.** Summing them counted a row carrying two
    # different repeated terms twice, so the numerator could exceed the number of rows it described.
    affected = found["affected_rows"]
    print(f"rows that cannot be read from the current format: {affected:,} of {rows_total:,}")
    print(f"   {100.0 * affected / rows_total:.4f}% of admissible batting rows")

    # ⚠️ **The denominator that decides.** One unreadable row breaks the whole board, so the rate per
    # row understates the damage by the number of rows on a board. A per-row figure would have made
    # this look like a rounding error; the per-direction figure is what the pool actually loses.
    per_board = f"""
    {SHAPE_CTE},
    admissible AS (
      SELECT o.GAME_ID, o.TEAM_ID, g.SEASON
      FROM shape o
      JOIN shape d ON d.GAME_ID = o.GAME_ID AND d.TEAM_ID <> o.TEAM_ID
      JOIN dbo.retroGamesReg g ON g.GAME_ID = o.GAME_ID
      CROSS APPLY (SELECT TOP 1 p.source_type FROM dbo.retroGameProvenance p
                   WHERE p.GAME_ID = g.GAME_ID AND p.is_deduced = 0 AND p.source_type IN ({accepted})
                   ORDER BY p.source_type) AS prov
      WHERE o.batters <= {BATTER_CAP} AND d.pitchers <= {PITCHER_CAP}
        {zero_density_clause(ZERO_DENSITY_GATE)})
    SELECT (a.SEASON/10)*10 AS decade, COUNT(*) AS directions,
           SUM(CASE WHEN x.affected > 0 THEN 1 ELSE 0 END) AS broken
    FROM admissible a
    CROSS APPLY (SELECT SUM(CASE WHEN d.B_HP>1 OR d.B_SF>1 OR d.B_SH>1 OR d.B_XI>1 THEN 1 ELSE 0 END) AS affected
                 FROM dbo.retroDailyReg d
                 WHERE d.GAME_ID = a.GAME_ID AND d.TEAM_ID = a.TEAM_ID
                   AND {CONTRIBUTED.replace("B_", "d.B_")}) AS x
    GROUP BY (a.SEASON/10)*10 ORDER BY decade
    """  # noqa: S608 - same: domain constants and the accepted-source list
    with pyodbc.connect(CONNECTION) as connection:
        decades = connection.cursor().execute(per_board).fetchall()

    directions = sum(row.directions for row in decades)
    broken = sum(row.broken for row in decades)
    print("")
    print("=== DIRECTIONS CARRYING AT LEAST ONE UNREADABLE ROW ===")
    print(f"{broken:,} of {directions:,} admissible directions — {100.0 * broken / directions:.2f}%")
    print("")
    print("decade   directions      broken     share")
    for row in decades:
        share = 100.0 * row.broken / row.directions
        print(f"  {row.decade:<6} {row.directions:>10,}  {row.broken:>10,}   {share:>6.2f}%")
    print("")
    print("NOTE: one unreadable row makes the whole board unsolvable. The player cannot tell one")
    print("  occurrence from two, and the row identity has no other route to the value. Every total still")
    print("  balances, which is why no validation layer sees it.")


if __name__ == "__main__":
    main()
