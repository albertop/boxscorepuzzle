"""What actually separates an easy board from a hard one.

Survival — whether propagation finishes at all — says a board is solvable, not how hard it was.
This measures the shape of the solution path instead, over real directions loaded from DGL:

  chain length      how many steps had to wait for the one before them
  frontier width    how many moves were available at each step; a width of one means the player
                    had to scan the whole board to find the only move there was
  families          which of the four kinds of reasoning the path actually needed

Plus two things specific to this board: how often a footnote term is load-bearing, and whether a
footnote whose row is ambiguous ever generates real work or always collapses on its own.

The question is whether these separate into bands or collapse into one pile. Bands make the weekly
difficulty curve a pool query; no bands means a different lever is needed. Thresholds are not set
here — those come from real solving times, not from anyone's estimate.

Read-only against DGL. Run from `forge/` so the package is importable.
"""

import random
import statistics
import sys
from collections import Counter
from collections.abc import Sequence
from string import ascii_lowercase
from dataclasses import dataclass
from typing import Final

sys.path.insert(0, str(__file__).rsplit("discovery", 1)[0] + "forge/src")

from boxscore_forge.boxscore import (  # noqa: E402
    BatterFootnotes,
    BattingLine,
    Direction,
    LineScore,
    PitchingLine,
    TeamFootnotes,
)
from boxscore_forge.constraints import (  # noqa: E402
    cell_values,
    shape_of,
)
from boxscore_forge.erasure import erasable  # noqa: E402
from boxscore_forge.errors import ContradictionError  # noqa: E402
from boxscore_forge.identities import (  # noqa: E402
    BATTING_COLUMNS,
    PITCHING_COLUMNS,
    find_violations,
)
from boxscore_forge.solver import Solution, solve  # noqa: E402
from boxscore_domain import BATTER_CAP, PITCHER_CAP, ZERO_DENSITY_GATE  # noqa: E402

CONTRIBUTED = (
    "B_G = 1 AND (B_PA > 0 OR B_R > 0 OR B_H > 0 OR B_BB > 0"
    " OR B_SO > 0 OR B_HP > 0 OR B_SF > 0 OR B_SH > 0 OR B_XI > 0)"
)
"""Which rows belong on the board, in one place because two copies of it drifted apart in a day.

`B_G = 1` means a player appeared, not that he batted: 18.8% of those rows have no plate appearance
and 83% of them also pitched. But a plate appearance is not the test either — a pinch runner scores
without ever batting, and dropping him takes his run with him. **The invariant is that the row
contributed something.**

⚠️ It has to be the *same* predicate in the shape query and the row query. When the shape counted
contributors and the rows loaded only batters, a game could pass the roster cap on a row count that
the loaded board did not have.
"""

ACCEPTED_SOURCES: Final = ("EVA", "EVN", "EVF")
"""The event-file kinds a puzzle may come from: American, National, Federal.

An **acceptance** list, not an exclusion list. `EVR` is Negro Leagues — transcribed newspaper box
scores that balance every identity and are still not scored games (§32) — and `ED?` is deduced. Both
are excluded by not appearing here rather than by being named somewhere a future kind could miss.
"""

CONNECTION = "DSN=LocalServer;DATABASE=DGL;Encrypt=no;TrustServerCertificate=yes"
ERASURE_COUNTS = (2, 4, 6, 8, 10, 12)
TRIALS_PER_COUNT = 15
AMBIGUITY_TRIALS = 20
TAIL_TRIM = 3
SEED = 20260817


SHAPE_CTE: Final = f"""    WITH shape AS (
      SELECT GAME_ID, TEAM_ID,
             -- Only rows that actually batted. See the note on the batting query below.
             SUM(CASE WHEN {CONTRIBUTED} THEN 1 ELSE 0 END) AS batters,
             SUM(CASE WHEN P_G=1 THEN 1 ELSE 0 END) AS pitchers,
             SUM(CASE WHEN {CONTRIBUTED} THEN
               CASE WHEN B_PA=0 THEN 1 ELSE 0 END + CASE WHEN B_AB=0 THEN 1 ELSE 0 END +
               CASE WHEN B_R=0 THEN 1 ELSE 0 END + CASE WHEN B_H=0 THEN 1 ELSE 0 END +
               CASE WHEN B_BB=0 THEN 1 ELSE 0 END + CASE WHEN B_SO=0 THEN 1 ELSE 0 END
               ELSE 0 END) AS batting_zeros,
             SUM(CASE WHEN P_G=1 THEN
               CASE WHEN P_OUT=0 THEN 1 ELSE 0 END + CASE WHEN P_H=0 THEN 1 ELSE 0 END +
               CASE WHEN P_R=0 THEN 1 ELSE 0 END + CASE WHEN P_ER=0 THEN 1 ELSE 0 END +
               CASE WHEN P_BB=0 THEN 1 ELSE 0 END + CASE WHEN P_SO=0 THEN 1 ELSE 0 END
               ELSE 0 END) AS pitching_zeros,
             SUM(CASE WHEN {CONTRIBUTED} THEN B_PA ELSE 0 END) AS t_pa,
             SUM(CASE WHEN {CONTRIBUTED} THEN B_AB ELSE 0 END) AS t_ab,
             SUM(CASE WHEN {CONTRIBUTED} THEN B_R ELSE 0 END) AS t_r,
             SUM(CASE WHEN {CONTRIBUTED} THEN B_H ELSE 0 END) AS t_h,
             SUM(CASE WHEN {CONTRIBUTED} THEN B_BB ELSE 0 END) AS t_bb,
             SUM(CASE WHEN {CONTRIBUTED} THEN B_SO ELSE 0 END) AS t_so,
             SUM(CASE WHEN P_G=1 THEN P_OUT ELSE 0 END) AS t_out,
             SUM(CASE WHEN P_G=1 THEN P_H ELSE 0 END) AS t_ph,
             SUM(CASE WHEN P_G=1 THEN P_R ELSE 0 END) AS t_pr,
             SUM(CASE WHEN P_G=1 THEN P_ER ELSE 0 END) AS t_per,
             SUM(CASE WHEN P_G=1 THEN P_BB ELSE 0 END) AS t_pbb,
             SUM(CASE WHEN P_G=1 THEN P_SO ELSE 0 END) AS t_pso
      FROM dbo.retroDailyReg GROUP BY GAME_ID, TEAM_ID)"""
"""The per-team shape every cohort query needs: roster sizes **and the twelve zero counts §5's
gate divides by.**

⚠️ **Hoisted after an instrument reimplemented a partial copy of it.**
`discovery/footnote-multiplicity` computed only the roster counts and applied only the caps, then
printed `gate applied downstream (30%)` while its docstring said the figures were counted against
"the pool the board actually draws from — the zero-density gate, the roster caps and the provenance
rule". The gate was in neither of its queries. It published a prevalence for a cohort it had never
measured, and the number reached five other files before a review caught it.

One predicate, one place. An instrument wanting the pool's cohort takes these two strings.
"""


def zero_density_clause(gate: float) -> str:
    """§5's gate as a SQL predicate, over `SHAPE_CTE`'s aliases `o` (offense) and `d` (defense)."""
    return f"""
      AND CAST(o.batting_zeros + d.pitching_zeros
        + CASE WHEN o.t_pa=0 THEN 1 ELSE 0 END + CASE WHEN o.t_ab=0 THEN 1 ELSE 0 END
        + CASE WHEN o.t_r=0 THEN 1 ELSE 0 END + CASE WHEN o.t_h=0 THEN 1 ELSE 0 END
        + CASE WHEN o.t_bb=0 THEN 1 ELSE 0 END + CASE WHEN o.t_so=0 THEN 1 ELSE 0 END
        + CASE WHEN d.t_out=0 THEN 1 ELSE 0 END + CASE WHEN d.t_ph=0 THEN 1 ELSE 0 END
        + CASE WHEN d.t_pr=0 THEN 1 ELSE 0 END + CASE WHEN d.t_per=0 THEN 1 ELSE 0 END
        + CASE WHEN d.t_pbb=0 THEN 1 ELSE 0 END + CASE WHEN d.t_pso=0 THEN 1 ELSE 0 END AS float)
        / (6.0 * (o.batters + 1) + 6.0 * (d.pitchers + 1)) < {gate}
    """


def full_name(nickname: str | None, last: str | None) -> str:
    """A player's name for the final reveal (§7): **the name he was known by, plus the surname.**

    ⚠️ **`nickname`, never `first`.** In `retroMaster` the `first` column is the full legal given name
    — `Henry Louis` for Hank Aaron, `Fausto Andres` for Andy Abad — and `nickname` is what the man was
    called. A reveal built from `first` prints a name no boxscore, no broadcast and no player ever used.

    ⚠️ **A surname alone is a real answer, not a failure.** 113 of the players the pool contains have
    neither a nickname nor a given name on record; their Retrosheet identifiers carry `u` in the fifth
    position, which is that file's mark for *first name unknown*, and every one of them appears in two
    to five rows — one-game men from the early era. `Pitts` is what is known about him, and `Pitts` is
    what gets printed.

    ⚠️ **What the old code lost was different, and worse.** `f"{first} {last}".strip() or "Unknown"`
    handled a missing given name correctly — it produced the surname. The fallback fired only when
    *both* were empty, which happened when the player had **no row in `regPeople` at all**: 316 of the
    20,019 players in the pool. Those were published as `Unknown`, losing the surname too, and the
    placeholder-name check could not see it because `Unknown` is not blank.

    An empty result is left empty on purpose: `plausibility.faults` rejects a blank reveal name, and
    that check only means something if this function does not paper over the case.
    """
    return f"{(nickname or '').strip()} {(last or '').strip()}".strip()


@dataclass(frozen=True, slots=True)
class Loaded:
    game_id: str
    season: int
    direction: Direction
    labels: tuple[str, ...]
    offense_is_home: bool
    names: tuple[str, ...]
    """The batters' full names, **composed once here** (§7).

    ⚠️ **This was a `(first, last)` pair and two consumers joined it differently** — the reference
    writer with `.strip() or "Unknown"`, the prototype builder with neither. One rule, two places, and
    they disagreed about a player with no given name on record. The loader composes it now and nothing
    downstream reassembles it.
    """
    pitcher_labels: tuple[str, ...] = ()
    offense_team: str = ""
    """The club that batted. ⚠️ **Not** `game_id[:3]`, which is the *home* club and coincides only
    when the home side is the one batting. Taken from the same query as the roster, so the code and
    the names cannot disagree."""

    defense_team: str = ""
    pitcher_names: tuple[str, ...] = ()
    source_type: str = ""
    """Carried so the publication gate can be given evidence rather than assuming it."""

    official_hits: int = 0
    official_runs: int = 0

    is_deduced: bool = False
    """The provenance row's own flag. §32 excludes deduced event files, and the writer used to derive
    this from the source type's spelling — two places encoding one rule, which is this project's
    named failure shape."""

    official_at_bats: int | None = None
    official_left_on_base: int | None = None
    """From `retroGameLogs`, which is neither of the tables the board is built from.

    Everything else the gate can compare comes from `retroGamesReg`, the same query that fills the
    line score, so comparing those checks a value against itself — it catches corruption between
    loading and packaging and cannot catch a board that never happened. These two can. `None` means
    the game log has no row, which is 1.5% of games and concentrated in the 1930s to 1960s."""

    slots: tuple[int, ...] = ()
    """The batting-order slot of each row, in the same order as `direction.batting`.

    Rows sharing a slot are the men who followed one another in it, and that is a real relationship
    the board was discarding: their plate appearances sum against the same slot, and a footnote left
    unassigned falls to one of them by elimination. Position labels do not carry it — **42.1% of
    repeated position labels span more than one slot**, so two `CF` rows are usually two men who never
    replaced each other.
    """

    batter_rbi: tuple[int, ...] = ()
    """Runs batted in and home runs, per row and in lineup order, carried alongside `direction`
    rather than inside it.

    They are **candidate** columns (§6): the board ships six, and whether either earns a seventh is a
    measurement rather than a decision. Putting them in `BattingLine` would add them to every identity,
    every erasure and every package before that measurement exists, so they travel next to the model
    and `discovery/rbi-and-hr` assembles the wider rows it needs.
    """

    batter_home_runs: tuple[int, ...] = ()
    pitcher_home_runs: tuple[int, ...] = ()
    """Home runs charged to each pitcher. The offense's total and this one are the same events, which
    is the cross-team link a home-run column would add."""


FIELDING_CODE: Final = {1: "P", 2: "C", 3: "1B", 4: "2B", 5: "3B", 6: "SS", 7: "LF", 8: "CF", 9: "RF"}
"""Retrosheet's `SUB_FLD_CD`, for the nine positions on the field. 10 is DH, 11 PH, 12 PR."""

_NOT_A_FIELDING_POSITION: Final = frozenset({"", "?", "DH", "PH", "PR"})


def _position(
    appeared_at: str, entered_fielding: int | None, entered_as: int | None, started_at: int | None = None
) -> str:
    """Where the man played, not how he arrived.

    **The label has a deductive function rather than a biographical one.** It is what tells the player
    which row an `SF: SS` belongs to and what to expect from that line. `PH` distinguishes nothing —
    every substitute hitter is one — while a fielding position places him in the order and on the
    field. A printed boxscore does the same thing: when a pinch hitter stays in, it prints his
    fielding position too.

    So: **the position he entered the field at if there was one, then any position he is recorded at,
    and `PH` or `PR` only when he never occupied one** — there they are the whole truth rather than a
    provenance tag. `DH` loses to `PH` for the man who came in to bat for the designated hitter without
    taking the slot, which was the largest single group in the 7% of rows this rule corrects.

    ⚠️ **Getting this wrong is not cosmetic.** A footnote is attributed to a *row*, and a mislabelled
    row puts an `SF` inside the wrong row identity while the column totals still balance — arithmetic
    broken in a way no §22 layer can see.
    """
    # ⚠️ **The position of entry, and a starter enters in the starting lineup.** "Where he played"
    # was underspecified: a man who played two positions has no single answer, so the `CASE` over the
    # `F_*_G` flags fell back on a fixed priority and produced a board with two third basemen and no
    # starting centre fielder. This is one rule with two sources rather than two rules.
    if started_at in FIELDING_CODE:
        return FIELDING_CODE[started_at]
    if started_at == 10:
        return "DH"
    if entered_fielding is not None:
        return FIELDING_CODE[entered_fielding]
    if appeared_at not in _NOT_A_FIELDING_POSITION:
        return appeared_at
    if entered_as in (11, 12):
        return "PH" if entered_as == 11 else "PR"
    if entered_as == 10:
        return "DH"
    return appeared_at or "?"


def slot_references(slots: Sequence[int]) -> tuple[str, ...]:
    """The reference for each row: `9` when its slot holds one row, `9a`/`9b`/`9c` when it is shared.

    ⚠️ **One function, and both callers use it.** The slot cell and the footnote line apply the same
    condition — *is this slot shared* — and two places applying one condition is the defect this
    project has spent the day closing. The cell prints what this returns and the footnote prints what
    this returns, so `SH: 9b` and the cell reading `9b` cannot drift into disagreeing.

    The letter appears **only** where a slot is shared, which makes it the signal that a substitution
    happened rather than decoration on every row: nine rows numbered 1 to 9, with letters exactly where
    somebody was replaced. Never `2a` when there is no `2b`.

    Every reference carries the slot number, never a bare letter. The footnote says `9b`, so a cell
    saying `9b` makes finding the row a recognition rather than a composition — and leaves no second
    representation of the same thing to go stale.

    This applies to every slot, not only the ninth. A substituted left fielder gives `5a` and `5b`; the
    pitcher's slot dominates the examples only because it is the position most often substituted.
    """
    shared = {slot for slot in slots if list(slots).count(slot) > 1}
    seen: Counter[int] = Counter()
    references: list[str] = []
    for slot in slots:
        seen[slot] += 1
        references.append(f"{slot}{ascii_lowercase[seen[slot] - 1]}" if slot in shared else str(slot))
    return tuple(references)


def _batting_labels(positions: list[str]) -> tuple[str, ...]:
    """The label is the position, and nothing else.

    ⚠️ **The suffix is gone.** It existed for one reason — a footnote had to name a unique row — and the
    reference moved to the slot, which identifies a row without help. Two `CF` rows in different slots
    are now two rows reading `CF`, which is what a boxscore shows and what actually happened.

    Keeping it would have cost more than width. The suffix numbered by order of appearance of a
    *position* while the indentation groups by *slot*, and those are different partitions: a reader met
    a suffixed row that replaced nobody beside an unsuffixed row that did. Every attempt to fix that
    asked which row deserved the number, when the question was whether the number belonged on a row.

    Kept as a function rather than inlined: the batting section's pitchers are `P` here and `SP`/`RP-n`
    in the pitching section, which shows the *opposing* team, and one symbol naming two men on two
    teams is a mistake this is the natural place to prevent.
    """
    return tuple(positions)


def _pitcher_labels(started: list[int]) -> tuple[str, ...]:
    """SP for the starter, RP-1 onwards for relievers in the order they appeared.

    Not only clarity — it is information the board can be reasoned with. A starter is where the long
    innings are and a third reliever is where they are not, so a fan can bound the IP column before
    touching an equation, which is exactly what a puzzle built for baseball fans should allow.

    Never a bare `P` for the starter: the pitcher who batted also appears as `P` in the batting
    section, and the same label meaning two things in two sections is worse than no label.
    """
    labels: list[str] = []
    relievers = 0
    for is_starter in started:
        if is_starter:
            labels.append("SP")
        else:
            relievers += 1
            labels.append(f"RP-{relievers}")
    return tuple(labels)


def _parse_line_score(text: str) -> tuple[int, ...]:
    """Retrosheet writes a ten-run inning as `(10)`; everything else is one digit per inning."""
    innings: list[int] = []
    index = 0
    while index < len(text):
        if text[index] == "(":
            close = text.index(")", index)
            innings.append(int(text[index + 1 : close]))
            index = close + 1
        elif text[index].isdigit():
            innings.append(int(text[index]))
            index += 1
        else:
            index += 1
    return tuple(innings)


def load(
    limit: int,
    *,
    gated: bool = False,
    gate: float = ZERO_DENSITY_GATE,
    max_batters: int = BATTER_CAP,
    min_pitchers: int = 0,
    max_pitchers: int = PITCHER_CAP,
    also: tuple[str, ...] = (),
) -> list[Loaded]:
    """Sample directions from the pool, stratified by decade.

    `gated` applies §5's zero-density gate in SQL, which matters more than it sounds: the gate keeps
    only 11% of the pool at 30%, so an ungated sample is nine parts boards that will never ship. Off
    by default so that measurements taken before the gate existed stay comparable to themselves.

    `min_pitchers` exists to sample an *exact* pitcher count rather than a cap, which is what
    comparing a two-pitcher board against a five-pitcher one requires — under a cap the five-pitcher
    boards would be a handful of outliers inside a sample of two-pitcher ones.

    ⚠️ **`also` names games the sample must contain**, on top of whatever the stratified draw returns.
    It exists for re-measuring a specific board after a scale changes — the one board carrying a human
    verdict, say. Without it a script can only *hope* the draw includes what it wants to compare, and a
    comparison that runs whether or not its subject is present is a check that never fires. Named games
    still face every filter: the caps, the gate and the provenance rule apply to them exactly as they
    apply to the draw, so `also` cannot smuggle in a board the pool would refuse. **A named game that
    does not come back was rejected, and the caller must say so rather than fall silent.**
    """
    import pyodbc  # noqa: PLC0415

    gate_clause = zero_density_clause(gate)
    accepted = ", ".join(f"'{source}'" for source in ACCEPTED_SOURCES)
    query = f"""
    {SHAPE_CTE}
    SELECT TOP (?) g.GAME_ID, g.SEASON, o.TEAM_ID, d.TEAM_ID,
           CASE WHEN o.TEAM_ID = g.HOME_TEAM_ID THEN 1 ELSE 0 END AS offense_is_home,
           CASE WHEN o.TEAM_ID = g.HOME_TEAM_ID THEN g.HOME_LOB_CT ELSE g.AWAY_LOB_CT END AS lob,
           l.VisLineScore, l.HomeLineScore,
           CASE WHEN o.TEAM_ID = g.HOME_TEAM_ID THEN g.HOME_ERR_CT ELSE g.AWAY_ERR_CT END AS offense_errors,
           CASE WHEN o.TEAM_ID = g.HOME_TEAM_ID THEN g.AWAY_ERR_CT ELSE g.HOME_ERR_CT END AS defense_errors,
           CASE WHEN o.TEAM_ID = g.HOME_TEAM_ID THEN g.AWAY_HITS_CT ELSE g.HOME_HITS_CT END AS defense_hits,
           -- ⚠️ Loaded rather than summed. The line score's offensive hit total used to be
           -- `sum(line.hits for line in batting)` — an anchor manufactured from the very rows it is
           -- meant to verify, so an omitted batter, a duplicate, or a join fan-out satisfied every
           -- hit identity while the board no longer matched the historical boxscore. This comes from
           -- the game table, which is a different file from the daily one the rows come from.
           CASE WHEN o.TEAM_ID = g.HOME_TEAM_ID THEN g.HOME_HITS_CT ELSE g.AWAY_HITS_CT END AS offense_hits,
           -- Same rule, found by the test written for the hits: the runs totals were summed from the
           -- inning array the verifier then checks them against, so that identity could not fail.
           CASE WHEN o.TEAM_ID = g.HOME_TEAM_ID THEN l.HomeRunsScore ELSE l.VisRunsScored END AS offense_runs,
           CASE WHEN o.TEAM_ID = g.HOME_TEAM_ID THEN l.VisRunsScored ELSE l.HomeRunsScore END AS defense_runs,
           -- Evidence for the publication gate. It has no database and must not grow one (§22), so
           -- the producer carries what it knows and the gate refuses when it is missing.
           -- ⚠️ **One row, chosen once, and both fields come from it.** These were two independent
           -- `TOP 1` subqueries with no `ORDER BY` and no acceptance predicate, while eligibility used
           -- `EXISTS` over the accepted sources — three places, one rule, and the projection was not
           -- bound to the row that qualified. Every game has exactly one provenance row today (0 of
           -- 203,908 with more), so it cannot fire, which is the reason to fix it rather than close
           -- it: a check that cannot fire is indistinguishable from one that is broken, and "one row
           -- per game" is an invariant nobody asserts.
           prov.source_type,
           -- The provenance row's own flag, not a guess from the source name.
           prov.is_deduced,
           -- ⚠️ retroGameLogs is a different table from both retroDailyReg and retroGamesReg, which
           -- is the whole point: at-bats and runners left on base can be compared against the board
           -- without the comparison being a value checked against itself.
           (SELECT CASE WHEN o.TEAM_ID = g.HOME_TEAM_ID THEN l.HomeAB ELSE l.VisAB END
            FROM dbo.retroGameLogs l WHERE l.GAME_ID = g.GAME_ID) AS official_at_bats,
           (SELECT CASE WHEN o.TEAM_ID = g.HOME_TEAM_ID THEN l.HomeLOB ELSE l.VisLOB END
            FROM dbo.retroGameLogs l WHERE l.GAME_ID = g.GAME_ID) AS official_left_on_base
    FROM dbo.retroGamesReg g
    CROSS APPLY (SELECT TOP 1 p.source_type, p.is_deduced FROM dbo.retroGameProvenance p
                 WHERE p.GAME_ID = g.GAME_ID AND p.is_deduced = 0 AND p.source_type IN ({accepted})
                 ORDER BY p.source_type) AS prov
    JOIN shape o ON o.GAME_ID = g.GAME_ID
    JOIN shape d ON d.GAME_ID = g.GAME_ID AND d.TEAM_ID <> o.TEAM_ID
    JOIN dbo.retroGameLogs l ON l.GAME_ID = g.GAME_ID
    -- Caps are arguments so an instrument can vary them, but the defaults are the decided pair and
    -- they are **imported rather than spelled**: ≤13 batters and ≤6 pitchers (§5, §6). Written as
    -- literals here they were also literals at twenty-five call sites, which is how ≤4 outlived the
    -- measurement supporting it. Anything measured under ≤2 or ≤4 pitchers describes a board that is
    -- no longer being built.
    WHERE o.batters <= {max_batters} AND d.pitchers BETWEEN {min_pitchers} AND {max_pitchers}
      AND l.VisLineScore IS NOT NULL
      AND g.SEASON BETWEEN ? AND ?
      -- Deduced games and Negro Leagues games are out of the pool (§32). Both balance every
      -- identity, which is why the exclusion has to be a join rather than a check: nothing
      -- downstream can catch a board that is consistent and still wrong.
      -- ⚠️ EXISTS over an acceptance list, never NOT EXISTS over an exclusion list. The previous
      -- form admitted a game with **no provenance row at all**: absence satisfied "not excluded", so
      -- a partial import, a new season or an identifier mismatch silently turned "source unknown"
      -- into "source approved". Completeness of the provenance table was an unstated precondition.
      -- The acceptance rule lives in the CROSS APPLY above: a game with no accepted, non-deduced
      -- provenance row produces no row at all. Stating it twice is the defect this file spent the day
      -- closing, so the EXISTS that used to sit here is gone rather than kept as a belt.
      {gate_clause if gated else ""}
    ORDER BY ABS(CHECKSUM(g.GAME_ID, o.TEAM_ID))
    """
    # The same SELECT with the sampling replaced by a name list. Built from the query above rather
    # than written out, so the caps, the gate and the provenance join cannot drift between the two:
    # one predicate, one place. `TOP (?)` becomes a large literal because the IN list already bounds it.
    named_query = query.replace("SELECT TOP (?)", "SELECT TOP 999", 1).replace(
        "AND g.SEASON BETWEEN ? AND ?", f"AND g.GAME_ID IN ({', '.join('?' * len(also))})", 1
    )
    # The starting lineup, which is where a *starter* entered. `retroGamesReg` carries nine
    # BAT_ID/FLD_CD pairs per side; the code counts only when the row's player is the man the lineup
    # names in that slot, so a substitute cannot inherit his predecessor's position.
    lineup_bat = " ".join(
        f"WHEN {n} THEN CASE WHEN g.HOME_TEAM_ID = d.TEAM_ID THEN g.HOME_LINEUP{n}_BAT_ID"
        f" ELSE g.AWAY_LINEUP{n}_BAT_ID END"
        for n in range(1, 10)
    )
    lineup_fld = " ".join(
        f"WHEN {n} THEN CASE WHEN g.HOME_TEAM_ID = d.TEAM_ID THEN g.HOME_LINEUP{n}_FLD_CD"
        f" ELSE g.AWAY_LINEUP{n}_FLD_CD END"
        for n in range(1, 10)
    )
    rows_query = f"""
    SELECT d.PLAYER_ID, d.B_PA, d.B_AB, d.B_R, d.B_H, d.B_BB, d.B_SO, d.B_HP, d.B_SF, d.B_SH, d.B_XI,
      CASE WHEN d.F_P_G=1 THEN 'P' WHEN d.F_C_G=1 THEN 'C' WHEN d.F_1B_G=1 THEN '1B'
           WHEN d.F_2B_G=1 THEN '2B' WHEN d.F_3B_G=1 THEN '3B' WHEN d.F_SS_G=1 THEN 'SS'
           WHEN d.F_LF_G=1 THEN 'LF' WHEN d.F_CF_G=1 THEN 'CF' WHEN d.F_RF_G=1 THEN 'RF'
           WHEN d.B_G_DH=1 THEN 'DH' WHEN d.B_G_PH=1 THEN 'PH' WHEN d.B_G_PR=1 THEN 'PR'
           ELSE '?' END AS label,
      m.nickname, m.last, d.B_RBI, d.B_HR,
      -- ⚠️ The position a substitute *entered at*. The F_*_G flags above mean "appeared here at some
      -- point", and the CASE picks by a fixed priority, so a pinch hitter who later took centre came
      -- out as CF and three men who each spent an inning there became CF-1, CF-2, CF-3. A lineup with
      -- three centre fielders is not a thing that happens, and no identity on the board can see it.
      (SELECT TOP 1 s.SUB_FLD_CD FROM dbo.retroSubstitutionsReg s
       WHERE s.GAME_ID = d.GAME_ID AND s.SUB_ID = d.PLAYER_ID AND s.SUB_FLD_CD BETWEEN 1 AND 9
       ORDER BY s.EVENT_ID) AS entered_fielding,
      (SELECT TOP 1 s.SUB_FLD_CD FROM dbo.retroSubstitutionsReg s
       WHERE s.GAME_ID = d.GAME_ID AND s.SUB_ID = d.PLAYER_ID
       ORDER BY s.EVENT_ID) AS entered_as,
      -- The batting-order slot. Always 1 to 9, and every direction has exactly nine distinct ones —
      -- 407,815 of 407,816, the exception being a source error. It was already used to order the
      -- rows; carrying it makes the grouping part of the board rather than a detail of the ORDER BY.
      d.SLOT_CT,
      CASE WHEN (CASE d.SLOT_CT {lineup_bat} END) = d.PLAYER_ID
           THEN (CASE d.SLOT_CT {lineup_fld} END) END AS started_at
    FROM dbo.retroDailyReg d
    LEFT JOIN dbo.retroGamesReg g ON g.GAME_ID = d.GAME_ID
    -- The Retrosheet master file, keyed by the same identifier the daily rows carry.
    LEFT JOIN dbo.retroMaster m ON m.playerID = d.PLAYER_ID
    -- B_G = 1 marks a player as having appeared, not as having batted: 18.8% of those rows have no
    -- plate appearance at all, and 83% of those also pitched — the designated-hitter era's pitchers,
    -- who are on the card and never come up. They belong on no board. Each one is six cells of nought
    -- that count against the roster cap and inflate zero density.
    --
    -- It also fixes the lineup order. Those rows carry SLOT_CT = 0, and **not one row in slot zero
    -- has ever batted**, so the slot is the marker for "did not bat" — ordering by it put the
    -- pitchers at the top of the card and pushed the leadoff hitter to third.
    WHERE d.GAME_ID = ? AND d.TEAM_ID = ? AND {CONTRIBUTED.replace("B_", "d.B_")}
    ORDER BY d.SLOT_CT, d.SEQ_CT
    """
    # Pitchers in order of appearance, which is what SP / RP-1 / RP-2 labels claim to mean.
    # SEQ_CT alone is not that order: in a game without a designated hitter a reliever who enters at
    # another lineup slot carries that slot's sequence, so ordering by it puts a man who finished the
    # game ahead of one who pitched the sixth. The substitution table has the event that put each
    # pitcher in, which is the real order. The starter has no substitution row, and P_GS puts him
    # first regardless.
    pitch_query = """
    SELECT d.P_OUT, d.P_H, d.P_R, d.P_ER, d.P_BB, d.P_SO, d.P_GS, m.nickname, m.last, d.P_HR
    FROM dbo.retroDailyReg d
    -- The Retrosheet master file, keyed by the same identifier the daily rows carry.
    LEFT JOIN dbo.retroMaster m ON m.playerID = d.PLAYER_ID
    LEFT JOIN (SELECT GAME_ID, SUB_ID, MIN(EVENT_ID) AS entered
               FROM dbo.retroSubstitutionsReg WHERE SUB_FLD_CD = 1
               GROUP BY GAME_ID, SUB_ID) s
      ON s.GAME_ID = d.GAME_ID AND s.SUB_ID = d.PLAYER_ID
    WHERE d.GAME_ID = ? AND d.TEAM_ID = ? AND d.P_G = 1
    ORDER BY d.P_GS DESC, s.entered, d.SEQ_CT, d.PLAYER_ID
    """

    loaded: list[Loaded] = []
    rejected: Counter[str] = Counter()
    with pyodbc.connect(CONNECTION) as connection:
        cursor = connection.cursor()
        # Stratified by decade on purpose. The pool is not spread evenly across eras, and a sample
        # that lands in one decade would describe that decade's roster habits rather than the board.
        candidates = []
        for decade in range(1910, 2030, 10):
            candidates += cursor.execute(query, limit, decade, decade + 9).fetchall()
        if also:
            # ⚠️ Keyed by game *and* offensive team, because a game is two directions and they are two
            # different boards. Deduplicating on the game id alone would drop the second direction
            # whenever the draw happened to contain the first — silently halving what was asked for.
            drawn = {(row[0], row[2]) for row in candidates}
            candidates += [
                row for row in cursor.execute(named_query, *also).fetchall() if (row[0], row[2]) not in drawn
            ]
        for (
            game_id,
            season,
            offense,
            defense,
            is_home,
            lob,
            vis,
            home,
            offense_errors,
            defense_errors,
            defense_hits,
            offense_hits,
            offense_runs,
            defense_runs,
            source_type,
            is_deduced,
            official_at_bats,
            official_left_on_base,
        ) in candidates:
            batting_rows = connection.cursor().execute(rows_query, game_id, offense).fetchall()
            pitching_rows = connection.cursor().execute(pitch_query, game_id, defense).fetchall()
            if not batting_rows or not pitching_rows:
                continue
            batting = tuple(
                BattingLine(plate_appearances=r[1], at_bats=r[2], runs=r[3], hits=r[4], walks=r[5], strikeouts=r[6])
                for r in batting_rows
            )
            footnotes = tuple(
                BatterFootnotes(
                    hit_by_pitch=r[7], sacrifice_flies=r[8], sacrifice_hits=r[9], catcher_interference=r[10]
                )
                for r in batting_rows
            )
            pitching = tuple(
                PitchingLine(outs=p[0], hits=p[1], runs=p[2], earned_runs=p[3], walks=p[4], strikeouts=p[5])
                for p in pitching_rows
            )
            offense_innings = _parse_line_score(home if is_home else vis)
            defense_innings = _parse_line_score(vis if is_home else home)
            direction = Direction(
                batting=batting,
                batting_totals=_sum(BattingLine, batting, BATTING_COLUMNS),
                batter_footnotes=footnotes,
                footnote_totals=_sum(
                    BatterFootnotes,
                    footnotes,
                    ("hit_by_pitch", "sacrifice_flies", "sacrifice_hits", "catcher_interference"),
                ),
                team_footnotes=TeamFootnotes(left_on_base=lob),
                pitching=pitching,
                pitching_totals=_sum(PitchingLine, pitching, PITCHING_COLUMNS),
                line_score=LineScore(
                    offense_by_inning=offense_innings,
                    defense_by_inning=defense_innings,
                    offense_runs=offense_runs,
                    offense_hits=offense_hits,
                    offense_errors=offense_errors,
                    defense_runs=defense_runs,
                    defense_hits=defense_hits,
                    defense_errors=defense_errors,
                ),
            )
            # The anchor and the rows have to agree, and this is the one place that can tell.
            # A direction where they do not is internally consistent and does not correspond to the
            # game, which is precisely what an independent source exists to catch.
            if offense_hits is None or offense_hits != sum(line.hits for line in batting):
                rejected["offensive hits disagree with the game table"] += 1
                continue
            if offense_runs is None or offense_runs != sum(offense_innings):
                rejected["offensive runs disagree with the line score"] += 1
                continue
            if defense_runs is None or defense_runs != sum(defense_innings):
                rejected["defensive runs disagree with the line score"] += 1
                continue
            loaded.append(
                Loaded(
                    game_id,
                    season,
                    direction,
                    _batting_labels([_position(r[11], r[16], r[17], r[19]) for r in batting_rows]),
                    bool(is_home),
                    tuple(full_name(r[12], r[13]) for r in batting_rows),
                    _pitcher_labels([p[6] for p in pitching_rows]),
                    offense,
                    defense,
                    tuple(full_name(p[7], p[8]) for p in pitching_rows),
                    source_type or "",
                    offense_hits,
                    offense_runs,
                    bool(is_deduced),
                    official_at_bats,
                    official_left_on_base,
                    tuple(r[18] for r in batting_rows),
                    tuple(r[14] for r in batting_rows),
                    tuple(r[15] for r in batting_rows),
                    tuple(p[9] for p in pitching_rows),
                )
            )
    if rejected:
        print(f"loader rejected {sum(rejected.values())} directions: {dict(rejected)}")
    return loaded


def _sum(model: type, rows: tuple[object, ...], columns: tuple[str, ...]) -> object:
    return model(**{column: sum(getattr(row, column) for row in rows) for column in columns})


def leaned_on_a_footnote(direction: Direction, solution: Solution) -> bool:
    """Whether the solution used a row identity on a row that actually carries a footnote.

    A player has to notice the footnote is there before that row's identity is usable, and nine rows
    in ten have nothing in it. That is a difficulty signal distinct from how many cells are blank.

    Checked against the row rather than against what the deduction leaned on, because a footnote is
    always given: it is never deduced, so it never shows up as a dependency.
    """
    carrying = {
        index
        for index, footnotes in enumerate(direction.batter_footnotes)
        if footnotes.hit_by_pitch
        or footnotes.sacrifice_flies
        or footnotes.sacrifice_hits
        or footnotes.catcher_interference
    }
    return any(
        deduction.from_identity == "row_plate_appearances"
        and deduction.cell.startswith("batting[")
        and int(deduction.cell.split("[")[1].split("]")[0]) in carrying
        for deduction in solution.deductions
    )


def survey(sample: list[Loaded]) -> None:
    rng = random.Random(SEED)
    print("\n=== SOLUTION SHAPE BY ERASURE COUNT ===")
    print("erased  solved%  chain p50/p90/max   frontier min p50   mean frontier   footnote-needed%")
    rows_for_correlation: list[tuple[int, int, int]] = []

    bottleneck_counts: dict[int, Counter[int]] = {}
    attempts_per_puzzle: dict[int, float] = {}

    for count in ERASURE_COUNTS:
        chains: list[int] = []
        narrow_widths: list[int] = []
        mean_widths: list[float] = []
        bottlenecks: Counter[int] = Counter()
        family_sets: Counter[tuple[str, ...]] = Counter()
        solved = trials = footnote_needed = 0
        for loaded in sample:
            cells = erasable(loaded.direction)
            values = cell_values(loaded.direction)
            for _ in range(TRIALS_PER_COUNT):
                trials += 1
                erased = rng.sample(cells, count)
                puzzle = {k: v for k, v in values.items() if k not in erased}
                try:
                    solution = solve(shape_of(loaded.direction), puzzle)
                except ContradictionError:
                    continue
                if not solution.is_complete:
                    continue
                solved += 1
                chains.append(solution.chain_length)
                if solution.narrowest_frontier is not None:
                    narrow_widths.append(solution.narrowest_frontier)
                if solution.mean_frontier is not None:
                    mean_widths.append(solution.mean_frontier)
                if len(solution.deductions) > TAIL_TRIM:
                    # How often the board pinched, not just whether it ever did. One width-one step
                    # and six of them are very different solves and the minimum calls both "one".
                    bottlenecks[sum(1 for d in solution.deductions[:-TAIL_TRIM] if d.frontier == 1)] += 1
                family_sets[tuple(sorted(f.value for f in solution.families_used))] += 1
                if leaned_on_a_footnote(loaded.direction, solution):
                    footnote_needed += 1
                # Only boards long enough to have a frontier at all. Substituting a zero for the
                # ones that do not would put a fabricated value into the correlation.
                if solution.narrowest_frontier is not None:
                    rows_for_correlation.append((count, solution.chain_length, solution.narrowest_frontier))

        if not chains:
            print(f"{count:>6}  {0.0:>6.1f}%  no complete solutions")
            continue
        print(
            f"{count:>6}  {100.0 * solved / trials:>6.1f}%  "
            f"{_q(chains, 0.5):>5.0f}/{_q(chains, 0.9):>3.0f}/{max(chains):>3}   "
            f"{_q(narrow_widths, 0.0) if narrow_widths else 0:>11.0f} {_q(narrow_widths, 0.5) if narrow_widths else 0:>5.0f}   "
            f"{statistics.fmean(mean_widths) if mean_widths else 0:>13.2f}   "
            f"{100.0 * footnote_needed / max(solved, 1):>15.1f}%"
        )
        print(f"          families: {_top_families(family_sets)}")
        bottleneck_counts[count] = bottlenecks
        attempts_per_puzzle[count] = trials / max(solved, 1)

    _bottleneck_table(bottleneck_counts)
    _pool_cost(attempts_per_puzzle)
    _correlations(rows_for_correlation)
    _frontier_tail(sample, rng)


def _bottleneck_table(counts: dict[int, Counter[int]]) -> None:
    print("\n=== HOW OFTEN A BOARD PINCHES TO ONE MOVE (3-step tail trimmed) ===")
    print("erased   0     1     2     3    4+   mean")
    for erased, histogram in counts.items():
        total = sum(histogram.values()) or 1
        buckets = [100.0 * histogram[n] / total for n in range(4)]
        buckets.append(100.0 * sum(v for k, v in histogram.items() if k >= 4) / total)
        mean = sum(k * v for k, v in histogram.items()) / total
        print(f"{erased:>6}  " + "  ".join(f"{b:4.0f}%" for b in buckets) + f"  {mean:5.2f}")


def _pool_cost(attempts: dict[int, float]) -> None:
    print("\n=== WHAT EACH DIFFICULTY LEVEL COSTS THE POOL ===")
    print("  erased   attempts per valid puzzle")
    for erased, cost in attempts.items():
        print(f"  {erased:>6}   {cost:>6.2f}")
    print("\n  Illustration only — the mapping from weekday to erasure count is not decided.")
    print("  Taking one day each at 2, 4, 6, 8, 10 and 12 cells, a seven-day week with two easy days:")
    weekly = 2 * attempts[2] + attempts[4] + attempts[6] + attempts[8] + attempts[10] + attempts[12]
    print(f"    directions consumed per week : {weekly:.1f}")
    print(f"    per year                     : {weekly * 52:.0f}")
    print(f"    years of calendar from 55,024: {55024 / (weekly * 52):.1f}")


def _q(values: list[int], fraction: float) -> float:
    ordered = sorted(values)
    if fraction == 0.0:
        return float(ordered[0])
    return float(ordered[min(int(fraction * len(ordered)), len(ordered) - 1)])


def _top_families(counter: Counter[tuple[str, ...]]) -> str:
    total = sum(counter.values())
    return ", ".join(f"{'+'.join(k) or 'none'} {100.0 * v / total:.0f}%" for k, v in counter.most_common(4))


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or statistics.pstdev(xs) == 0 or statistics.pstdev(ys) == 0:
        return float("nan")
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / len(xs)
    return covariance / (statistics.pstdev(xs) * statistics.pstdev(ys))


def _correlations(rows: list[tuple[int, int, int]]) -> None:
    print("\n=== DO THE METRICS MOVE TOGETHER ===")
    erased = [float(r[0]) for r in rows]
    chain = [float(r[1]) for r in rows]
    frontier = [float(r[2]) for r in rows]
    print(f"  erasure count vs chain length   r = {_pearson(erased, chain):+.3f}")
    print(f"  erasure count vs frontier width r = {_pearson(erased, frontier):+.3f}")
    print(f"  chain length  vs frontier width r = {_pearson(chain, frontier):+.3f}")
    print("  (near +/-1 means one variable with three names; near 0 means independent levers)")


def _frontier_tail(sample: list[Loaded], rng: random.Random) -> None:
    """Whether the frontier distribution spikes at one because solutions narrow by exhaustion."""
    print("\n=== FRONTIER DISTRIBUTION, BY HOW MUCH OF THE TAIL IS TRIMMED ===")
    for trim in (1, 2, 3):
        widths: Counter[int] = Counter()
        for loaded in sample[:60]:
            cells = erasable(loaded.direction)
            values = cell_values(loaded.direction)
            for _ in range(TRIALS_PER_COUNT):
                erased = rng.sample(cells, 8)
                try:
                    solution = solve(shape_of(loaded.direction), {k: v for k, v in values.items() if k not in erased})
                except ContradictionError:
                    continue
                if not solution.is_complete or len(solution.deductions) <= trim:
                    continue
                widths[min(d.frontier for d in solution.deductions[:-trim])] += 1
        total = sum(widths.values()) or 1
        shape = ", ".join(f"{width}:{100.0 * count / total:.0f}%" for width, count in sorted(widths.items())[:6])
        print(f"  trimming {trim} step(s): {shape}")


def ambiguity(sample: list[Loaded], rng: random.Random) -> None:
    """⚠️ **Retired: this measured duplicate positions, not ambiguous footnote references.**

    It grouped rows by `loaded.labels` and erased the group's footnote cells as one ambiguous domain.
    That was sound while labels carried a suffix and a repeated label meant a shared lineup slot. It is
    not sound now: labels are bare positions, and **42.1% of repeated position labels span more than
    one slot**, so two `CF` rows are usually two men who never replaced each other. The experiment
    would build an artificial domain over unrelated rows and report the solver's reaction as footnote
    ambiguity — plausible percentages for a case the board does not contain.

    Its docstring described the opposite implementation, predicting no groups would be found. Left as a
    named refusal rather than deleted, so a reader who remembers it finds out why instead of finding
    nothing. The live question — whether an unassigned footnote resolves — belongs to
    `discovery/footnote-groups`, which groups by **slot** and reports per group size and term count.
    """
    del sample, rng
    message = "ambiguity() grouped by position label and no longer measures ambiguity; see discovery/footnote-groups"
    raise RuntimeError(message)


def main() -> None:
    sample = load(35)
    balanced = [item for item in sample if not find_violations(item.direction)]
    print(f"loaded {len(sample)} directions, {len(balanced)} balance every identity")
    by_decade = Counter((item.season // 10) * 10 for item in balanced)
    print(f"decades: {dict(sorted(by_decade.items()))}")
    survey(balanced)


if __name__ == "__main__":
    main()
