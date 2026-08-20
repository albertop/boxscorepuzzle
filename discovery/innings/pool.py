"""How many innings the pool's games actually run to, and what the long ones are worth as puzzles.

The operator solved a twelve-inning game on paper and it was a good puzzle. The question that raises is
where the line score stops fitting — and **the cap cannot be set from the screen alone**, because the
games it would exclude may be the ones that work best.

⚠️ **Broken down per inning count, never as one "extra innings" bucket.** If games of thirteen or more
are four in the whole pool the cap goes wherever and costs nothing; if they are thousands it is a real
trade. One bucket cannot tell those apart, and a decision was going to be made on it.

⚠️ **The same cohort `load()` returns.** `eligibility()` carries the provenance rule, both roster caps,
the game-log join, the line-score requirement and the season window in one string, because a cohort
shared in part is worse than one shared not at all — an earlier instrument kept three fragments and a
hope, and counted games production cannot return.

Read-only against DGL. Run from anywhere.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bootstrap import bootstrap

ROOT = bootstrap()

from collections import Counter  # noqa: E402

import pyodbc  # noqa: E402
from measure import (  # noqa: E402
    CONNECTION,
    SEASON_WINDOW,
    SHAPE_CTE,
    _parse_line_score,
    eligibility,
    zero_density_clause,
)

GATE = 0.30
"""§5's decided pool gate. The question is about boards that would ship, so the gate is applied."""

ALWAYS_SHOW_TO = 12
"""Print every rung up to here even when empty, then skip empty ones.

⚠️ Twelve because that is the length the operator solved and liked, so a zero at 12 is a *result* and
must be visible. Above it an empty rung carries no information and only pads the table."""


def _predicate(clause: str) -> str:
    """The gate as a boolean expression rather than a WHERE fragment.

    ⚠️ `zero_density_clause` returns a fragment that begins `AND`, for pasting into a WHERE. Reusing
    it inside `CASE WHEN` needs that prefix gone — and `lstrip("AND ")` does **not** do it: lstrip
    takes a character *set*, and the fragment starts with a newline, so it removed nothing and produced
    `CASE WHEN AND CAST(...)`. Named and asserted rather than done inline, because the failure was a
    silent no-op that only SQL Server noticed.
    """
    stripped = clause.strip()
    if not stripped.startswith("AND "):
        message = f"the gate clause no longer begins with AND: {stripped[:40]!r}"
        raise SystemExit(message)
    return stripped[len("AND ") :]


def counts() -> tuple[Counter[int], Counter[int]]:
    """Directions by inning count, gated and ungated.

    ⚠️ Both, because the gate removes shutouts and low-scoring games, and a long game is more likely to
    be low-scoring per inning. Reporting only the gated number would understate how much baseball this
    is; reporting only the ungated one would overstate what the cap costs the product.
    """
    gated: Counter[int] = Counter()
    ungated: Counter[int] = Counter()
    query = f"""
    {SHAPE_CTE}
    SELECT l.VisLineScore, l.HomeLineScore, {{gate}} AS passes_gate
    {eligibility(seasons="g.SEASON BETWEEN ? AND ?")}
    """
    with pyodbc.connect(CONNECTION) as connection:
        cursor = connection.cursor()
        rows = cursor.execute(
            query.replace("{gate}", f"CASE WHEN {_predicate(zero_density_clause(GATE))} THEN 1 ELSE 0 END"),
            *SEASON_WINDOW,
        ).fetchall()
    for vis, home, passes in rows:
        # One game is two directions and both sides see the same line score, so each game contributes
        # twice — the pool is counted by direction everywhere else and this must match.
        innings = max(len(_parse_line_score(vis)), len(_parse_line_score(home)))
        ungated[innings] += 2
        if passes:
            gated[innings] += 2
    return gated, ungated


def report(gated: Counter[int], ungated: Counter[int]) -> None:
    total_gated = sum(gated.values())
    total_ungated = sum(ungated.values())
    print(f"{total_ungated:,} directions in the cohort, {total_gated:,} through the {GATE:.0%} gate")
    print("")
    print(f"  {'innings':>8}{'gated':>12}{'share':>9}{'cumulative loss above':>24}")
    longest = max(ungated)
    running = 0
    for innings in range(9, longest + 1):
        here = gated[innings]
        if here == 0 and innings > ALWAYS_SHOW_TO:
            continue
        share = here / total_gated if total_gated else 0
        above = sum(count for (count,) in [(gated[n],) for n in range(innings + 1, longest + 1)])
        running += here
        print(f"  {innings:>8}{here:>12,}{share:>8.2%}{f'{above:,} ({above / total_gated:.2%})':>24}")
    print("")
    print(f"  the longest game in the cohort runs {longest} innings")


def main() -> None:
    gated, ungated = counts()
    report(gated, ungated)


if __name__ == "__main__":
    main()
