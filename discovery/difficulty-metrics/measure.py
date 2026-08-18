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
    batting_cell,
    batting_total_cell,
    cell_values,
    footnote_cell,
    pitching_cell,
    pitching_total_cell,
    shape_of,
)
from boxscore_forge.errors import ContradictionError  # noqa: E402
from boxscore_forge.identities import (  # noqa: E402
    BATTING_COLUMNS,
    PITCHING_COLUMNS,
    Family,
    find_violations,
)
from boxscore_forge.solver import Solution, solve  # noqa: E402

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


@dataclass(frozen=True)
class Loaded:
    game_id: str
    season: int
    direction: Direction
    labels: tuple[str, ...]
    offense_is_home: bool
    names: tuple[tuple[str, str], ...]
    pitcher_labels: tuple[str, ...] = ()
    offense_team: str = ""
    """The club that batted. ⚠️ **Not** `game_id[:3]`, which is the *home* club and coincides only
    when the home side is the one batting. Taken from the same query as the roster, so the code and
    the names cannot disagree."""

    defense_team: str = ""
    pitcher_names: tuple[tuple[str, str], ...] = ()


def _batting_labels(positions: list[str]) -> tuple[str, ...]:
    """Position labels, with any repeat suffixed by order of appearance: `LF-1`, `LF-2`.

    43% of gated boards have two rows sharing a label and 10% have one where a row also carries a
    footnote — which is when `SF: LF` stops naming a row and the identity for both becomes unusable.
    Suffixing removes that at the source, so the erasure no longer has to avoid patterns that leave
    the attribution unresolved.

    It is also a better label rather than a patch: `LF-2` says a substitution happened at that
    position, which is real information the boxscore already contains and the bare label threw away.

    Labels used once stay bare — the common row should not carry a suffix that distinguishes nothing.
    Four characters, inside the seven §7 fixed.

    Note the batting section's pitchers become `P-1`, `P-2` and **not** `SP`/`RP-n`. Those belong to
    the pitching section, which shows the *opposing* team's pitchers: the same symbol in both
    sections would name two different men on two different teams.
    """
    repeated = {label for label in positions if positions.count(label) > 1}
    seen: Counter[str] = Counter()
    labels: list[str] = []
    for label in positions:
        if label in repeated:
            seen[label] += 1
            labels.append(f"{label}-{seen[label]}")
        else:
            labels.append(label)
    return tuple(labels)


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
    gate: float = 0.30,
    max_batters: int = 13,
    min_pitchers: int = 0,
    max_pitchers: int = 4,
) -> list[Loaded]:
    """Sample directions from the pool, stratified by decade.

    `gated` applies §5's zero-density gate in SQL, which matters more than it sounds: the gate keeps
    only 11% of the pool at 30%, so an ungated sample is nine parts boards that will never ship. Off
    by default so that measurements taken before the gate existed stay comparable to themselves.

    `min_pitchers` exists to sample an *exact* pitcher count rather than a cap, which is what
    comparing a two-pitcher board against a five-pitcher one requires — under a cap the five-pitcher
    boards would be a handful of outliers inside a sample of two-pitcher ones.
    """
    import pyodbc  # noqa: PLC0415

    gate_clause = f"""
      AND CAST(o.batting_zeros + d.pitching_zeros
        + CASE WHEN o.t_pa=0 THEN 1 ELSE 0 END + CASE WHEN o.t_ab=0 THEN 1 ELSE 0 END
        + CASE WHEN o.t_r=0 THEN 1 ELSE 0 END + CASE WHEN o.t_h=0 THEN 1 ELSE 0 END
        + CASE WHEN o.t_bb=0 THEN 1 ELSE 0 END + CASE WHEN o.t_so=0 THEN 1 ELSE 0 END
        + CASE WHEN d.t_out=0 THEN 1 ELSE 0 END + CASE WHEN d.t_ph=0 THEN 1 ELSE 0 END
        + CASE WHEN d.t_pr=0 THEN 1 ELSE 0 END + CASE WHEN d.t_per=0 THEN 1 ELSE 0 END
        + CASE WHEN d.t_pbb=0 THEN 1 ELSE 0 END + CASE WHEN d.t_pso=0 THEN 1 ELSE 0 END AS float)
        / (6.0 * (o.batters + 1) + 6.0 * (d.pitchers + 1)) < {gate}
    """
    accepted = ", ".join(f"'{source}'" for source in ACCEPTED_SOURCES)
    query = f"""
    WITH shape AS (
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
      FROM dbo.retroDailyReg GROUP BY GAME_ID, TEAM_ID)
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
           CASE WHEN o.TEAM_ID = g.HOME_TEAM_ID THEN l.VisRunsScored ELSE l.HomeRunsScore END AS defense_runs
    FROM dbo.retroGamesReg g
    JOIN shape o ON o.GAME_ID = g.GAME_ID
    JOIN shape d ON d.GAME_ID = g.GAME_ID AND d.TEAM_ID <> o.TEAM_ID
    JOIN dbo.retroGameLogs l ON l.GAME_ID = g.GAME_ID
    -- Caps are arguments, not constants, and the defaults are the decided pair: ≤13 batters and
    -- ≤4 pitchers (§5, §6). Anything measured under ≤2 pitchers describes a board that is no longer
    -- being built — the pitcher cap changed after its screen-cost justification turned out to have
    -- been retired by the working-set measurement without anyone revisiting it.
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
      AND EXISTS (SELECT 1 FROM dbo.retroGameProvenance p
                  WHERE p.GAME_ID = g.GAME_ID AND p.is_deduced = 0
                    AND p.source_type IN ({accepted}))
      {gate_clause if gated else ""}
    ORDER BY ABS(CHECKSUM(g.GAME_ID, o.TEAM_ID))
    """
    rows_query = f"""
    SELECT d.PLAYER_ID, d.B_PA, d.B_AB, d.B_R, d.B_H, d.B_BB, d.B_SO, d.B_HP, d.B_SF, d.B_SH, d.B_XI,
      CASE WHEN d.F_P_G=1 THEN 'P' WHEN d.F_C_G=1 THEN 'C' WHEN d.F_1B_G=1 THEN '1B'
           WHEN d.F_2B_G=1 THEN '2B' WHEN d.F_3B_G=1 THEN '3B' WHEN d.F_SS_G=1 THEN 'SS'
           WHEN d.F_LF_G=1 THEN 'LF' WHEN d.F_CF_G=1 THEN 'CF' WHEN d.F_RF_G=1 THEN 'RF'
           WHEN d.B_G_DH=1 THEN 'DH' WHEN d.B_G_PH=1 THEN 'PH' WHEN d.B_G_PR=1 THEN 'PR'
           ELSE '?' END AS label,
      p.name_first, p.name_last
    FROM dbo.retroDailyReg d
    LEFT JOIN dbo.regPeople p ON p.key_retro = d.PLAYER_ID
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
    SELECT d.P_OUT, d.P_H, d.P_R, d.P_ER, d.P_BB, d.P_SO, d.P_GS, p.name_first, p.name_last
    FROM dbo.retroDailyReg d
    LEFT JOIN dbo.regPeople p ON p.key_retro = d.PLAYER_ID
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
                BatterFootnotes(hit_by_pitch=r[7], sacrifice_flies=r[8], sacrifice_hits=r[9], catcher_interference=r[10])
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
                    _batting_labels([r[11] for r in batting_rows]),
                    bool(is_home),
                    tuple((r[12] or "", r[13] or "") for r in batting_rows),
                    _pitcher_labels([p[6] for p in pitching_rows]),
                    offense,
                    defense,
                    tuple((p[7] or "", p[8] or "") for p in pitching_rows),
                )
            )
    if rejected:
        print(f"loader rejected {sum(rejected.values())} directions: {dict(rejected)}")
    return loaded


def _sum(model: type, rows: tuple[object, ...], columns: tuple[str, ...]) -> object:
    return model(**{column: sum(getattr(row, column) for row in rows) for column in columns})


def erasable_cells(direction: Direction) -> list[str]:
    """The grid, and only the grid. The line score is the anchor and the footnotes are given."""
    shape = shape_of(direction)
    cells = [batting_cell(i, c) for i in range(shape.batter_count) for c in BATTING_COLUMNS]
    cells += [batting_total_cell(c) for c in BATTING_COLUMNS]
    cells += [pitching_cell(i, c) for i in range(shape.pitcher_count) for c in PITCHING_COLUMNS]
    cells += [pitching_total_cell(c) for c in PITCHING_COLUMNS]
    return sorted(cells)


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
            cells = erasable_cells(loaded.direction)
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
                    bottlenecks[
                        sum(1 for d in solution.deductions[:-TAIL_TRIM] if d.frontier == 1)
                    ] += 1
                family_sets[tuple(sorted(f.value for f in solution.families_used))] += 1
                if leaned_on_a_footnote(loaded.direction, solution):
                    footnote_needed += 1
                # Only boards long enough to have a frontier at all. Substituting a zero for the
                # ones that do not would put a fabricated value into the correlation.
                if solution.narrowest_frontier is not None:
                    rows_for_correlation.append(
                        (count, solution.chain_length, solution.narrowest_frontier)
                    )

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
            cells = erasable_cells(loaded.direction)
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
    """Footnotes whose row cannot be told apart, modelled by leaving both candidate cells unknown.

    Measured on top of a real erasure rather than on an otherwise complete board. With everything
    else given there is no rest of the board to be held up, so "the ambiguity never mattered" would
    be unmeasurable by construction.

    ⚠️ **Kept as a record; it now measures a case that no longer exists.** The ambiguity came from two
    batting rows sharing a position label, and labels are disambiguated at the source since
    `_batting_labels` — `LF-1` and `LF-2` rather than two `LF` rows. Run against a current sample this
    finds no groups at all, which is the result rather than a bug. The erasure constraint it implied
    is not needed (§5).
    """
    print("\n=== AMBIGUOUS FOOTNOTE ATTRIBUTION ===")
    never_mattered = had_to_be_resolved = non_unique = boards = 0
    families_when_it_mattered: Counter[str] = Counter()
    stuck_share: list[float] = []
    per_pattern: Counter[str] = Counter()

    for loaded in sample:
        groups: dict[str, list[int]] = {}
        for index, label in enumerate(loaded.labels):
            groups.setdefault(label, []).append(index)
        values = cell_values(loaded.direction)
        for indexes in groups.values():
            if len(indexes) < 2:
                continue
            ambiguous = [
                footnote_cell(i, column)
                for i in indexes
                for column in ("hit_by_pitch", "sacrifice_flies", "sacrifice_hits", "catcher_interference")
                if any(values[footnote_cell(j, column)] for j in indexes)
            ]
            if not ambiguous:
                continue
            boards += 1
            # Many erasure patterns, not one. Whether the ambiguity resolves depends on which cells
            # are blank, so a single pattern cannot tell a bad direction from a bad erasure.
            outcomes: Counter[str] = Counter()
            for _ in range(AMBIGUITY_TRIALS):
                grid = rng.sample(erasable_cells(loaded.direction), 6)
                puzzle = {k: v for k, v in values.items() if k not in ambiguous and k not in grid}
                try:
                    solution = solve(shape_of(loaded.direction), puzzle)
                except ContradictionError:
                    outcomes["stuck"] += 1
                    per_pattern["stuck"] += 1
                    continue
                if not solution.is_complete:
                    outcomes["stuck"] += 1
                    per_pattern["stuck"] += 1
                    continue
                settled = {deduction.cell for deduction in solution.deductions} & set(ambiguous)
                depended = any(
                    deduction.cell not in ambiguous and deduction.depends_on & settled
                    for deduction in solution.deductions
                )
                outcomes["mattered" if depended else "irrelevant"] += 1
                per_pattern[("mattered" if depended else "irrelevant")] += 1
                if depended:
                    for family in solution.families_used:
                        families_when_it_mattered[family.value] += 1

            if outcomes["stuck"] == AMBIGUITY_TRIALS:
                non_unique += 1
            elif outcomes["mattered"]:
                had_to_be_resolved += 1
            else:
                never_mattered += 1
            stuck_share.append(outcomes["stuck"] / AMBIGUITY_TRIALS)

    print(f"  ambiguous groups carrying a footnote      : {boards}")
    print(f"  never mattered under any erasure tried    : {never_mattered}")
    print(f"  mattered under at least one erasure       : {had_to_be_resolved}")
    print(f"  stuck under EVERY erasure tried           : {non_unique}")
    if stuck_share:
        print(f"  mean share of erasure patterns that stick: {statistics.fmean(stuck_share):.1%}")
        print(f"  groups that never stick at all           : {sum(1 for s in stuck_share if s == 0)}")
    total_patterns = sum(per_pattern.values()) or 1
    print("\n  per erasure pattern, not per group:")
    for outcome in ("irrelevant", "mattered", "stuck"):
        print(f"    {outcome:<11}: {per_pattern[outcome]:>5}  ({100.0 * per_pattern[outcome] / total_patterns:.1f}%)")
    if families_when_it_mattered:
        print(f"  families used when it mattered            : {dict(families_when_it_mattered)}")


def main() -> None:
    sample = load(35)
    balanced = [item for item in sample if not find_violations(item.direction)]
    print(f"loaded {len(sample)} directions, {len(balanced)} balance every identity")
    by_decade = Counter((item.season // 10) * 10 for item in balanced)
    print(f"decades: {dict(sorted(by_decade.items()))}")
    survey(balanced)
    ambiguity(balanced, random.Random(SEED + 1))


if __name__ == "__main__":
    main()
