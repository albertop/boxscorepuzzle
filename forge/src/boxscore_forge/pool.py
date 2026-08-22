"""The pool: which directions exist, and how one is loaded out of Retrosheet.

**Everything the publication path needs to turn a game into a `Direction`** — §32's source rules, §5's
gate and caps, the era windows, the SQL, and the row-to-board mapping with its labels and its printed
boxscore.

⚠️⚠️ **This lived in `discovery/difficulty-metrics/measure.py` until 2026-08-22, and the production
publisher imported it from there.** `write_reference_puzzles.py` did `from measure import Loaded, load`,
so the path that writes signed packages ran through a research script — outside `mypy --strict`, inside
the ratcheted lint tree, and free to be edited by any cleanup in `discovery/`. The deferral was recorded
in the writer with its reason: **moving it is building the inventory pipeline, not renaming a module.**
This is that build (`docs/beta-0-plan.md`, A1).

⚠️ **`measure.py` re-exports every name that moved and 33 discovery scripts are untouched.** That is a
re-export, not a copy — one definition with an alias — and it is deliberate: rewriting 33 import lines
would be a change verified by reading a diff, against scripts that need a database to run. `CLAUDE.md`
is explicit that rewrites across call sites are verified by running.

⚠️ **What did not move: the measurement half.** `survey()`, the erasure trials, the correlations and the
ambiguity sweep stay in `discovery/`, because §5 puts the *pool rule* here and the *research into it*
there. The line is whether the code produces something a package carries.

**Read-only against DGL.** `pyodbc` is imported lazily inside `load()`, so importing this module costs
nothing and needs no driver — which is what lets the suite exercise everything around it with no
database at all.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Any, Final

from boxscore_domain import (
    BATTER_CAP,
    PITCHER_CAP,
    POSTSEASON_SEASON_FLOOR,
    ZERO_DENSITY_GATE,
)
from boxscore_forge.boxscore import (
    BatterFootnotes,
    BattingLine,
    Direction,
    LineScore,
    PitchingLine,
    TeamFootnotes,
)
from boxscore_forge.identities import BATTING_COLUMNS, PITCHING_COLUMNS
from boxscore_package.format import (
    PrintedBatter,
    PrintedBoxscore,
    PrintedPitcher,
    PrintedSide,
)


def _sum[Line](model: type[Line], rows: tuple[object, ...], columns: tuple[str, ...]) -> Line:
    """Total a column across rows into the same model.

       ⚠️ **Generic rather than `-> object`, and that is not decoration.** Under `-> object` the three
       `Direction(...)` arguments it feeds were `object` where `BattingLine`, `BatterFootnotes` and
       `PitchingLine` were expected — three real type errors `discovery/` never saw, because it sits
       outside `mypy --strict`. The annotation was hiding the check rather than passing it.
    ⚠️ **Moved here with `load()`, which is its only
       caller** — it sat in the research half and `load()` reached across for it, so promoting one without
       the other left an undefined name that only ruff saw."""
    return model(**{column: sum(getattr(row, column) for row in rows) for column in columns})


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

POSTSEASON_SOURCE: Final = "EVE"
"""The extension every postseason event file carries. **Verified against the download, not assumed.**

All 121 `events-post` zips hold 403 files and every one is `.EVE` — 1,878 games, no league letter and
no deduced variant. Regular-season files split by league (`.EVA`/`.EVN`/`.EVF`) and carry a deduced
twin (`.EDA`/`.EDN`/`.EDF`); postseason files do neither.

⚠️ Spelled once and interpolated into both the acceptance list and the SQL, because it is the same
fact in two places and this project has shipped the same rule twice before with the copies drifting.
"""

PROVENANCE_SOURCES: Final = ("EVA", "EVN", "EVF")
"""What `dbo.retroGameProvenance` may hold and the pool may accept: American, National, Federal.

An **acceptance** list, not an exclusion list. `EVR` is Negro Leagues — transcribed newspaper box
scores that balance every identity and are still not scored games (§32) — and `ED?` is deduced. Both
are excluded by not appearing here rather than by being named somewhere a future kind could miss.

⚠️⚠️ **`EVE` is deliberately NOT in this tuple, and the first version of the postseason change put it
here.** That version was wrong and an instrument caught it: adding a member to the list the regular
season's `CROSS APPLY` interpolates *widens the predicate that admits every game the pool already
holds*. It was harmless in fact — no provenance row carries `EVE` — and harmless in fact is not the
test. The rule was that the existing pool does not change, and a widened predicate is a change to it
whether or not today's data notices.

**The two lists are separate because they answer different questions.** This one is *what a provenance
row may say*. `ACCEPTED_SOURCES` is *what the publication gate may accept*, which is this plus the
postseason, and the postseason has no provenance row to say anything.
"""

ACCEPTED_SOURCES: Final = (*PROVENANCE_SOURCES, POSTSEASON_SOURCE)
"""Every source the publication gate accepts: the three provenanced kinds, and the postseason.

Derived from `PROVENANCE_SOURCES` rather than spelled again, so a change to what the pool admits
cannot leave the gate behind — the failure this project meets most often is two places that should
agree and nothing checking that they do.
"""

CONNECTION = "DSN=LocalServer;DATABASE=DGL;Encrypt=no;TrustServerCertificate=yes"


PROVENANCE_LITERAL: Final = ", ".join(f"'{source}'" for source in PROVENANCE_SOURCES)
"""§32's provenanced source types as a SQL list. Derived from `PROVENANCE_SOURCES`, never spelled.

⚠️ Built from `PROVENANCE_SOURCES` and **not** from `ACCEPTED_SOURCES`: the SQL this feeds is the
regular season's admission, and the postseason's `EVE` has no business widening it."""

SEASON_WINDOW: Final = (1910, 2029)
"""The seasons the sampler draws from, hoisted out of the decade loop that spelled it.

⚠️ An instrument measuring *the pool* has to apply this too. Retrosheet reaches back to 1871 and
the sampler never touches those games, so a denominator without this window counts boards `load()`
cannot return.
"""


@dataclass(frozen=True)
class Season:
    """Which season's tables a cohort draws from, and how §32 admissibility is established for it.

    ⚠️⚠️ **`admission` is a `CROSS APPLY`, in both seasons, and that is the point rather than a
    coincidence.** The rule this project keeps rediscovering is that *the absence of a check must not
    read as the presence of a passing one*. A `CROSS APPLY` producing no row drops the game; an
    `OUTER APPLY` would admit it with nulls. Adding the postseason by loosening the regular season's
    apply to `OUTER` was the obvious change and would have silently made a regular-season game with a
    missing provenance row admissible — a defect in the half nobody was editing, arriving attached to
    a feature that has nothing to do with it.

    So each season carries its own **positive** admission, and both fail the same way.
    """

    games: str
    daily: str
    substitutions: str
    admission: str
    events: str
    """The play-by-play table this season's first event is read from.

    ⚠️ **A field rather than a constant, for the same reason `admission` is one.** The postseason has
    its own events table, and a shared literal would silently read regular-season rows for a postseason
    game — producing no first event, and so excluding every postseason board. A rule that empties a pool
    is easier to spot than one that mixes two, but neither should be possible."""


REGULAR: Final = Season(
    games="dbo.retroGamesReg",
    daily="dbo.retroDailyReg",
    substitutions="dbo.retroSubstitutionsReg",
    events="dbo.retroEventsReg",
    # ⚠️ Unchanged, and it must stay unchanged: this is what admits every game the pool already holds.
    # Deduced games and Negro Leagues games are out (§32) and both balance every identity, which is why
    # the exclusion is a join rather than a check — nothing downstream can catch a board that is
    # consistent and still wrong. A game with no accepted, non-deduced provenance row produces no row.
    admission=f"""CROSS APPLY (SELECT TOP 1 p.source_type, p.is_deduced FROM dbo.retroGameProvenance p
                 WHERE p.GAME_ID = g.GAME_ID AND p.is_deduced = 0 AND p.source_type IN ({PROVENANCE_LITERAL})
                 ORDER BY p.source_type) AS prov""",  # noqa: S608 — `PROVENANCE_LITERAL`, from a `Final` tuple
)
"""The pool as it has always been. **Nothing about the postseason changes what this admits.**"""

POSTSEASON: Final = Season(
    games="dbo.retroGamesPost",
    daily="dbo.retroDailyPost",
    substitutions="dbo.retroSubstitutionsPost",
    events="dbo.retroEventsPost",
    # There is no provenance table for the postseason and none is needed: every postseason event file
    # is `.EVE`, with no deduced twin and no league letter, so there is nothing to exclude per game.
    # The floor is protection against Retrosheet publishing something later that would need excluding.
    # ⚠️ Still a CROSS APPLY: a game below the floor produces **no row**, exactly as an unprovenanced
    # regular-season game does. The two seasons fail identically, which is the only reason it is safe
    # to have two of them.
    admission=f"""CROSS APPLY (SELECT '{POSTSEASON_SOURCE}' AS source_type, CAST(0 AS bit) AS is_deduced
                 WHERE g.SEASON >= {POSTSEASON_SEASON_FLOOR}) AS prov""",
)
"""The postseason from `POSTSEASON_SEASON_FLOOR`. **Opt-in everywhere** — every caller that does not
ask for it gets `REGULAR`, so adding this changed no existing measurement and no existing board."""


# ⚠️ PLR0913: six keyword arguments, and they are the cohort's six independent axes. The alternative is
# a settings object whose only job is to be unpacked here — one more thing to keep in step with §5.
def eligibility(  # noqa: PLR0913
    *,
    max_batters: int = BATTER_CAP,
    min_pitchers: int = 0,
    max_pitchers: int = PITCHER_CAP,
    gate_clause: str = "",
    seasons: str = "g.SEASON BETWEEN ? AND ?",
    season: Season = REGULAR,
) -> str:
    """**The whole candidate cohort**: the provenance rule, both roster caps, the game-log join, the
    line score requirement, the season window and — when asked for — §5's zero-density gate.

    ⚠️ **Hoisted because sharing part of a cohort is worse than sharing none.** The first repair to
    `footnote-multiplicity` shared `SHAPE_CTE` and the gate and left the game-log join, the
    `VisLineScore` requirement and the season window behind — so the instrument still counted games
    `load()` cannot return, and its report still called that number the production pool. **A fix that
    solves most of a problem reads exactly like one that solves all of it**, which is why the whole
    thing is one string now rather than three shared fragments and a hope.


    ⚠️⚠️ **What reaches this query, and why S608 is answered rather than waived.** Three kinds of value
    are interpolated and they are not equally safe, so they are not treated alike:

    - **`max_batters`, `min_pitchers`, `max_pitchers`** — scalars from a caller. **Checked below.** The
      annotations were the only guard and an annotation is not one.
    - **`gate_clause` and `seasons`** — SQL fragments this module produces (`zero_density_clause`, and a
      literal with `?` placeholders). A caller *can* pass its own, and a caller here is a script in this
      repository reading a local read-only database.
    - **`season.games` / `.daily` / `.substitutions` / `.admission`** — table names and a `CROSS APPLY`.
      **These are SQL by construction**; `Season` exists to hold them, and there are two instances of it
      in this module. Parameterising a table name is not possible in any case.

    ⚠️ **No value on any of these paths comes from a user, a request, or a file.** If that ever stops
    being true — an endpoint, a config file, a CLI argument reaching here — this comment is the thing to
    re-read, because the `noqa` will still be sitting there saying it was fine.
    """
    # ⚠️ Checked before a single fragment is composed, so a bad cap cannot reach a query even in a
    # branch. A roster outside 0..100 is a mistake in the caller whatever it means: the decided pair is
    # 13 and 6, and the widest thing any instrument has varied them to is far inside this.
    for name, value in (("max_batters", max_batters), ("min_pitchers", min_pitchers), ("max_pitchers", max_pitchers)):
        _a_number(name, value, low=0, high=100)
    return f"""FROM {season.games} g
    {season.admission}
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
      -- ⚠️⚠️ **The visiting club batted first, stated by the data rather than inferred.** 49 games in
      -- the regular season have the home club batting the top of the first — neutral-site and
      -- rescheduled games where the designated home team led off. Retrosheet is describing something
      -- real; the board is what cannot represent it.
      --
      -- **Everything about the board assumes the visitor bats first**: the `x` for the half-inning
      -- never played, which side is `AWAY BATTING`, and the outs for a home team that wins without
      -- batting in the ninth. A reversed game is a different object, and 49 of them do not justify a
      -- special case running on every board forever. **This is a construction rule, not data quality.**
      --
      -- ⚠️⚠️ **`EXISTS` over the visitor batting, never `NOT EXISTS` over the 49.** An exclusion list
      -- lets a game with no event rows through — the fail-open shape this project has closed twice, and
      -- the one §32 already states for provenance. Coverage was measured before relying on it:
      -- **100% of games from 1910 to 2029 have a first event**, so nothing is lost by requiring one.
      --
      -- ⚠️ No validation layer can see this. Such a board balances every identity perfectly and is only
      -- wrong about which team is which — the mislabelled-team shape, found by reading a file.
      AND EXISTS (SELECT 1 FROM {season.events} ev
                  WHERE ev.GAME_ID = g.GAME_ID AND ev.EVENT_ID = 1 AND ev.BAT_HOME_ID = 0)
      AND {seasons}
      -- ⚠️ The source rule (§32) is the CROSS APPLY above and is stated **only** there. It is an
      -- acceptance list, never an exclusion list: the form that used to sit here admitted a game with
      -- no provenance row at all, because absence satisfied "not excluded", so a partial import or an
      -- identifier mismatch silently turned "source unknown" into "source approved". Stating it twice
      -- is the defect this file spent a day closing, so the EXISTS that used to be here is gone
      -- rather than kept as a belt — and `Season.admission` is why it stays one place now that there
      -- are two seasons to admit.
      {gate_clause}
    """  # noqa: S608 - see `what reaches this query` in the docstring


def shape_cte(season: Season = REGULAR) -> str:
    """The per-team shape a cohort query needs, over one season's daily table.

    ⚠️ S608 is waived on the return below with a reason rather than silently: the only interpolation is
    `season.daily`, a **table name**, which no database lets you parameterise and which `Season` exists
    to hold. There are two instances of `Season` and both are module constants in this file.
    """
    return f"""    WITH shape AS (
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
      FROM {season.daily} GROUP BY GAME_ID, TEAM_ID)"""  # noqa: S608 — a table name, see the docstring


SHAPE_CTE: Final = shape_cte(REGULAR)
"""The regular season's shape, derived from `shape_cte()` rather than spelled a second time.

⚠️ **Kept as a module constant because eight scripts import it by that name.** When a mechanism grows a
parameter, the callers that were reading the old one do not disappear — this project has already broken
three consumers by removing something only one place wrote. Deriving the constant means there is still
one definition, and nothing that imports `SHAPE_CTE` changed at all.

Roster sizes **and the twelve zero counts §5's gate divides by.**

⚠️ **Hoisted after an instrument reimplemented a partial copy of it.**
`discovery/footnote-multiplicity` computed only the roster counts and applied only the caps, then
printed `gate applied downstream (30%)` while its docstring said the figures were counted against
"the pool the board actually draws from — the zero-density gate, the roster caps and the provenance
rule". The gate was in neither of its queries. It published a prevalence for a cohort it had never
measured, and the number reached five other files before a review caught it.

One predicate, one place. An instrument wanting the pool's cohort takes these two strings.
"""


def _a_number(name: str, value: object, *, low: float, high: float) -> float:
    """Refuse anything that is not a real number in range, **before it reaches a query string.**

    ⚠️⚠️ **These values are interpolated into SQL and the annotations were the only thing guarding
    them.** `gate: float` and `max_batters: int` are hints; nothing enforces them at runtime, and every
    caller is a script. `CLAUDE.md` says validate at the boundary rather than downstream — this is the
    boundary, and downstream is a query the database will run.

    ⚠️ `bool` is rejected explicitly: it is a subclass of `int`, so `isinstance(True, int)` is true and
    `zero_density_clause(True)` would have produced `< True`, which SQL Server accepts.
    """
    if isinstance(value, bool) or not isinstance(value, int | float):
        message = f"{name} must be a number, got {type(value).__name__}: {value!r}"
        raise TypeError(message)
    if not low <= value <= high:
        message = f"{name} must be between {low} and {high}, got {value!r}"
        raise ValueError(message)
    return float(value)


def zero_density_clause(gate: float) -> str:
    """§5's gate as a SQL predicate, over `SHAPE_CTE`'s aliases `o` (offense) and `d` (defense)."""
    # A density is a fraction of cells. Zero would admit nothing and one would admit everything, so both
    # ends are refused rather than silently producing a query with no purpose.
    gate = _a_number("gate", gate, low=0.0, high=1.0)
    # ⚠️ S608 is answered by the line above, not waived: the one interpolated value is a float this
    # function just proved is a float in range. There is no string path into this query.
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

    printed: PrintedBoxscore | None = None
    """**Both clubs' complete boxscore**, for the reveal and for nothing else.

    ⚠️ **It is not part of `direction` and must never become part of it.** `direction` is the board:
    every field in it enters an identity, an erasure and four validation layers. This is display data —
    it feeds no deduction, and putting it in the model would widen what §22 has to verify in order to
    change what a screen looks like.

    `None` when the club could not be named for that season; the loader drops those directions.
    """


FIELDING_CODE: Final = {1: "P", 2: "C", 3: "1B", 4: "2B", 5: "3B", 6: "SS", 7: "LF", 8: "CF", 9: "RF"}
"""Retrosheet's `SUB_FLD_CD`, for the nine positions on the field. 10 is DH, 11 PH, 12 PR."""

DESIGNATED_HITTER: Final = 10
PINCH_HITTER: Final = 11
PINCH_RUNNER: Final = 12
"""Retrosheet's position codes past the nine on the field, which `FIELDING_CODE` covers.

⚠️ Named rather than written as `10`, `11`, `12` in a decision cascade: **the numbers encode Retrosheet's
scheme, not an ordering anybody could re-derive**, and `entered_as == 11` reads as a magic threshold
while `entered_as == PINCH_HITTER` reads as what it is. The distinction matters here because a wrong
label puts a footnote inside the wrong row identity while every column total still balances.
"""

_NOT_A_FIELDING_POSITION: Final = frozenset({"", "?", "DH", "PH", "PR"})


def _position(  # noqa: PLR0911 — a seven-branch decision cascade, and collapsing it would hide the order
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
    if started_at == DESIGNATED_HITTER:
        return "DH"
    if entered_fielding is not None:
        return FIELDING_CODE[entered_fielding]
    if appeared_at not in _NOT_A_FIELDING_POSITION:
        return appeared_at
    if entered_as in (PINCH_HITTER, PINCH_RUNNER):
        return "PH" if entered_as == PINCH_HITTER else "PR"
    if entered_as == DESIGNATED_HITTER:
        return "DH"
    return appeared_at or "?"


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


TEAM_NAME_QUERY: Final = """
SELECT city, nickname FROM dbo.retroTeams
WHERE team = ? AND ? BETWEEN firstSeason AND lastSeason
"""
"""The club's real name, which is what a boxscore is headed with.

⚠️ **The season is part of the key and dropping it is wrong, not merely imprecise.** A three-letter
code is a *franchise slot*, and `retroTeams` carries one row per era: `MIL` is the Braves and then the
Brewers, `WAS` the Senators and then the Nationals. A lookup on the code alone returns whichever row
came first.

⚠️ **Exactly one row or the direction is dropped, and there is no fallback to the code.** Measured
over every team-season the pool can draw: **2,892 of 2,901 resolve to exactly one row, and the nine
that fail resolve to zero** — Negro League and exhibition clubs whose season windows do not cover the
game they appear in. So the ambiguous case does not exist and only the absent one does; falling back
to `SLA` would put the abbreviation back on the one screen schema 5 exists to take it off, and it
would do it silently.
"""

_CITY_SPELLINGS: Final = {"St.Louis": "St. Louis"}
"""⚠️ One club, spelled two ways in one table. `retroTeams` holds both `St. Louis` and `St.Louis`, and
the 1913 Browns get the second. It reads as a typo on a page whose whole job is to look printed.
Corrected by exact match on the known bad spelling rather than by a rule about periods, because
`Ft. Wayne` and `Harrisburg - St. Louis` are correct as they stand and a general rule would touch them.
"""


def team_name(
    connection: object, cache: dict[tuple[str, int], tuple[str, str] | None], code: str, season: int
) -> tuple[str, str] | None:
    """`(city, nickname)`, or nothing when the table cannot name the club for that season."""
    key = (code, season)
    if key not in cache:
        cursor = connection.cursor()  # type: ignore[attr-defined]
        rows = cursor.execute(TEAM_NAME_QUERY, code, season).fetchall()
        found = rows[0] if len(rows) == 1 else None
        cache[key] = None if found is None else (_CITY_SPELLINGS.get(found[0], found[0]), found[1])
    result: tuple[str, str] | None = cache[key]
    return result


# ⚠️ `list[Any]`, not a bare `list` and not a tuple shape: these are pyodbc `Row` objects, indexable and
# attribute-accessible, with no published stub. `Any` says *unknown by construction*; a bare `list` reads
# as an oversight, which is what it was.
def _printed_side(
    code: str, city: str, nickname: str, batting_rows: list[Any], pitching_rows: list[Any]
) -> PrintedSide:
    """One club's half of the printed sheet, from the same rows the board is built from.

    ⚠️ **The same queries and the same helpers, with the team ids swapped.** The defence's batting and
    the offence's pitching are not a second kind of data — they are the other direction of the same
    game, and reading them any other way would be a second definition of *who batted* and *where he
    played*. `_position` and `_pitcher_labels` decide those once, for both clubs.
    """
    return PrintedSide(
        code=code,
        city=city,
        nickname=nickname,
        batting=tuple(
            PrintedBatter(
                name=full_name(r[12], r[13]),
                position=position,
                at_bats=r[2],
                runs=r[3],
                hits=r[4],
                runs_batted_in=r[14],
                walks=r[5],
                strikeouts=r[6],
            )
            for r, position in zip(
                batting_rows,
                _batting_labels([_position(r[11], r[16], r[17], r[19]) for r in batting_rows]),
                strict=True,
            )
        ),
        pitching=tuple(
            PrintedPitcher(
                name=full_name(p[7], p[8]),
                role=role,
                outs=p[0],
                hits=p[1],
                runs=p[2],
                earned_runs=p[3],
                walks=p[4],
                strikeouts=p[5],
            )
            for p, role in zip(pitching_rows, _pitcher_labels([p[6] for p in pitching_rows]), strict=True)
        ),
    )


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


# ⚠️ **`pyodbc` is imported inside the two functions that use it, and that is load-bearing.** It keeps
# this module importable with no ODBC driver present, which is what lets the suite exercise everything
# around `load()` with no database at all — `test_the_writer_passes_its_own_gate.py` depends on it.
def _rows(connection: object, query: str, game_id: str, team_id: str) -> list[Any]:
    """One game-and-team fetch, with the parameters typed as the columns actually are.

    ⚠⚠ **`varchar`, and it is not cosmetic: it is the whole cost of loading.** pyodbc sends every
    Python `str` as `nvarchar`, and `GAME_ID` and `TEAM_ID` are `varchar` in a **SQL** collation
    (`SQL_Latin1_General_CP1_CI_AS`). `nvarchar` wins the precedence, so the conversion lands on the
    *column* — the live plan reads
    `CONVERT_IMPLICIT(nvarchar(12), retroDailyReg.GAME_ID, 0) = [@P1]` — and a SQL collation gets no
    `GetRangeThroughConvert`. The clustered index on `(GAME_ID, IDX)` becomes unusable and every fetch
    **scans all 5,325,173 rows**.

    Measured on the real table, both arms returning the same 12 rows so the comparison is honest:
    **827 ms against 0.1 ms, 6731x.** Times 96 fetches, that is the twenty minutes every discovery run
    paid to load before measuring anything.

    ⚠️ **The first diagnosis was wrong, and the shape of the error is why it is written down.** The
    plan summary showed two full scans of `retroSubstitutionsReg`, an unindexed 1.76M-row table, and
    that was reported as the cause. It is real and worth an index — but it is the smaller half, and a
    summary listing operator *types* is not a plan: the line naming which table each one touched said
    `retroDailyReg` was **scanned**, not sought. **Reading the summary is not reading the plan**, and
    the summary was consistent with a wrong answer.
    """
    import pyodbc  # noqa: PLC0415

    cursor = connection.cursor()  # type: ignore[attr-defined]
    # 12 and 3 are the declared widths of GAME_ID and TEAM_ID. Wrong widths would silently truncate.
    cursor.setinputsizes([(pyodbc.SQL_VARCHAR, 12, 0), (pyodbc.SQL_VARCHAR, 3, 0)])
    rows: list[Any] = cursor.execute(query, game_id, team_id).fetchall()
    return rows


# ⚠️ PLR0913 and PLR0915: eight arguments and fifty-two statements. This is the one function that turns
# rows into a `Direction`, and every argument is a pool axis an instrument varies. Splitting it would put
# the row-to-board mapping in two places, which is the defect this project meets most often — the shape
# complaint is the smaller cost.
def load(  # noqa: PLR0913, PLR0915
    limit: int,
    *,
    gated: bool = True,
    gate: float = ZERO_DENSITY_GATE,
    max_batters: int = BATTER_CAP,
    min_pitchers: int = 0,
    max_pitchers: int = PITCHER_CAP,
    also: tuple[str, ...] = (),
    season: Season = REGULAR,
    window: tuple[int, int] = SEASON_WINDOW,
    rejected: Counter[str] | None = None,
) -> list[Loaded]:
    """Sample directions from the pool, stratified by decade.

    ⚠️⚠️ **Tested against a fake driver, not excluded from coverage — and a blanket pragma was written
    here first.** It looked defensible: this opens a connection, and a test needing a DSN is one CI skips
    and nobody runs. **The line between "needs a server" and "needs rows" is not "touches the database".**

    Most of what is inside is *logic*: the rejection tally, `also`, the deduplication keyed on game **and**
    offensive team, and the row-to-`Direction` mapping. None of it needs a server; it needs rows. Hiding
    it behind an infrastructure excuse would have covered the exact place **the pinch-runner defect
    lived** — a row query and a shape query disagreeing about what counts as having contributed.

    `pyodbc` is imported inside this function, which is what lets a test put a fake in `sys.modules` and
    drive the whole thing off fixed rows. See `tests/test_pool_loading.py`.


    `gated` applies §5's zero-density gate in SQL, which matters more than it sounds: the gate keeps
    only 11% of the pool at 30%, so an ungated sample is nine parts boards that will never ship.

    ⚠️⚠️ **It did nothing at all until 2026-08-21, and the docstring promised the opposite of the
    truth.** (v36-P2-20) `gate_clause` was built unconditionally and `eligibility()` interpolated it
    unconditionally, so **every sample this function has ever returned was gated** — while this
    paragraph said *off by default*, and the signature still says `gated: bool = False`.

    ⚠️ **The damage was to reasoning rather than to data.** No figure is wrong because of it: every
    caller that wanted a gated sample got one. What it produced was a *belief* — a reader of the
    signature concludes that eight call sites omitting the flag measured the unfiltered pool, and they
    did not. **A parameter that lies about what it does is a hazard with no callers at all**, because
    it is read far more often than it is passed.

    Those eight now pass `gated=True` explicitly, which is what they were already getting, so no
    recorded figure moves. Whether each of them *should* have been ungated is a separate question and
    is recorded in `docs/reviews/todo.md` rather than decided here.

    ⚠️⚠️ **The default is `True` since 2026-08-22, and that closes the second half of the same defect.**
    Reading the flag fixed the behaviour and left the hazard: a caller who omits it got the **ungated**
    pool, which is nine parts boards that can never ship, and gets it silently. **An omitted argument
    must not widen the population** — that is the same instinct as failing closed at a boundary, applied
    to a sample.

    Counted before changing it: **37 call sites, every one passing `gated=True`, none passing `False`.**
    So the new default is what everybody already wanted and no figure moves again.

    ⚠️ **Deleting the parameter was the other option and it was not taken.** With one value in the whole
    repository it looks like dead weight, and there is a second way to say the same thing — `gate=1.0`
    admits every board whose zero density is under one, which is all of them but a wholly-zero board.
    Two ways to express *no gate* is the duplication this project meets most often. It stays because
    removing it means editing 37 call sites in scripts that need a database to run, and `CLAUDE.md` is
    explicit that a rewrite across call sites is verified by running and never by reading the diff.
    **Recorded as a deliberate deferral rather than an oversight**, with the count that would justify
    doing it: it costs one afternoon with a DSN, not a decision.

    `min_pitchers` exists to sample an *exact* pitcher count rather than a cap, which is what
    comparing a two-pitcher board against a five-pitcher one requires — under a cap the five-pitcher
    boards would be a handful of outliers inside a sample of two-pitcher ones.

    ⚠️⚠️ **`window` exists so a quota can be sampled rather than hoped for.** The draw is *n per decade*,
    which is flat by construction — and §6 caps pre-1950 boards at 5% of what a player sees. A flat draw
    cannot satisfy a weighted quota except by accident, which is exactly how the first 150-board calendar
    came out **34% pre-1950 against a ceiling of 8**. Two draws with two windows can.

    ⚠️ **`also` names games the sample must contain**, on top of whatever the stratified draw returns.
    It exists for re-measuring a specific board after a scale changes — the one board carrying a human
    verdict, say. Without it a script can only *hope* the draw includes what it wants to compare, and a
    comparison that runs whether or not its subject is present is a check that never fires. Named games
    still face every filter: the caps, the gate and the provenance rule apply to them exactly as they
    apply to the draw, so `also` cannot smuggle in a board the pool would refuse. **A named game that
    does not come back was rejected, and the caller must say so rather than fall silent.**

    ⚠️ **`season` defaults to `REGULAR`, and every existing caller therefore loads exactly what it
    loaded before.** Passing `POSTSEASON` swaps the three source tables and the admission rule
    together — never one of them, which is why they travel as one record. The postseason has no
    provenance table and needs none (every postseason event file is `.EVE`, no deduced twin), so its
    admission is the season floor; a game below it produces no row, the same way an unprovenanced
    regular-season game does.
    """
    import pyodbc  # noqa: PLC0415

    # ⚠️ The flag is read now (v36-P2-20). This was `zero_density_clause(gate)` unconditionally, so
    # `gated` was declared, documented, passed at thirty-three call sites — and never consulted.
    gate_clause = zero_density_clause(gate) if gated else ""
    # Bound before the query so the f-string stays inside the line budget, and so the two queries below
    # cannot drift: `named_query` is built from `query`, and both take this one cohort.
    cohort = eligibility(
        max_batters=max_batters,
        min_pitchers=min_pitchers,
        max_pitchers=max_pitchers,
        gate_clause=gate_clause,
        season=season,
    )
    query = f"""
    {shape_cte(season)}
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
    {cohort}
    -- ⚠️⚠️ **The tiebreaker is what makes the sample repeatable.** (v36-P3-07) `CHECKSUM` is
    -- 32-bit, so ties exist, and SQL Server's order among tied rows is not defined — a `TOP (?)`
    -- draw could in principle return a different sample on the same data on the same day. This
    -- project's rule is that a discovery result which cannot be re-run identically is not
    -- evidence, and every figure in `docs/reviews/` rests on draws from this line.
    ORDER BY ABS(CHECKSUM(g.GAME_ID, o.TEAM_ID)), g.GAME_ID, o.TEAM_ID
    """  # noqa: S608 — composed from `shape_cte` and `eligibility`, which guard their own scalars
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
      (SELECT TOP 1 s.SUB_FLD_CD FROM {season.substitutions} s
       WHERE s.GAME_ID = d.GAME_ID AND s.SUB_ID = d.PLAYER_ID AND s.SUB_FLD_CD BETWEEN 1 AND 9
       ORDER BY s.EVENT_ID) AS entered_fielding,
      (SELECT TOP 1 s.SUB_FLD_CD FROM {season.substitutions} s
       WHERE s.GAME_ID = d.GAME_ID AND s.SUB_ID = d.PLAYER_ID
       ORDER BY s.EVENT_ID) AS entered_as,
      -- The batting-order slot. Always 1 to 9, and every direction has exactly nine distinct ones —
      -- 407,815 of 407,816, the exception being a source error. It was already used to order the
      -- rows; carrying it makes the grouping part of the board rather than a detail of the ORDER BY.
      d.SLOT_CT,
      CASE WHEN (CASE d.SLOT_CT {lineup_bat} END) = d.PLAYER_ID
           THEN (CASE d.SLOT_CT {lineup_fld} END) END AS started_at
    FROM {season.daily} d
    LEFT JOIN {season.games} g ON g.GAME_ID = d.GAME_ID
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
    """  # noqa: S608 — `CONTRIBUTED` and `season.daily`, both module constants
    # Pitchers in order of appearance, which is what SP / RP-1 / RP-2 labels claim to mean.
    # SEQ_CT alone is not that order: in a game without a designated hitter a reliever who enters at
    # another lineup slot carries that slot's sequence, so ordering by it puts a man who finished the
    # game ahead of one who pitched the sixth. The substitution table has the event that put each
    # pitcher in, which is the real order. The starter has no substitution row, and P_GS puts him
    # first regardless.
    pitch_query = f"""
    SELECT d.P_OUT, d.P_H, d.P_R, d.P_ER, d.P_BB, d.P_SO, d.P_GS, m.nickname, m.last, d.P_HR
    FROM {season.daily} d
    -- The Retrosheet master file, keyed by the same identifier the daily rows carry.
    LEFT JOIN dbo.retroMaster m ON m.playerID = d.PLAYER_ID
    LEFT JOIN (SELECT GAME_ID, SUB_ID, MIN(EVENT_ID) AS entered
               FROM {season.substitutions} WHERE SUB_FLD_CD = 1
               GROUP BY GAME_ID, SUB_ID) s
      ON s.GAME_ID = d.GAME_ID AND s.SUB_ID = d.PLAYER_ID
    WHERE d.GAME_ID = ? AND d.TEAM_ID = ? AND d.P_G = 1
    ORDER BY d.P_GS DESC, s.entered, d.SEQ_CT, d.PLAYER_ID
    """  # noqa: S608 — `season.daily` and `season.substitutions`, both module constants

    loaded: list[Loaded] = []
    # ⚠️⚠️ **Accepted from the caller so its decisions are observable.** This was a local `Counter`
    # printed at the end — so a *test* could only see `load()`'s refusals by reading stdout, and three
    # tests written against the empty result passed with the refusals deleted, because **an empty list is
    # what every path returns**.
    #
    # **A function whose decisions are visible only as a printed line cannot be tested for making them.**
    # Passing the tally in costs one optional argument, changes nothing for the 37 existing callers, and
    # hands the batch producer the per-cause number it sizes a run from.
    rejected = Counter() if rejected is None else rejected
    # One lookup per team-season rather than per direction: a stratified draw returns many games from
    # the same club and the table is small.
    team_names: dict[tuple[str, int], tuple[str, str] | None] = {}
    with pyodbc.connect(CONNECTION) as connection:
        cursor = connection.cursor()
        # Stratified by decade on purpose. The pool is not spread evenly across eras, and a sample
        # that lands in one decade would describe that decade's roster habits rather than the board.
        candidates = []
        # ⚠️ `window`, not `SEASON_WINDOW`. The constant is the default and no longer the only option:
        # a **quota** on eras cannot be met by a draw that is flat across all of them (§6's 5% pre-1950),
        # so a caller has to be able to ask each side of 1950 for its own share. Passing the window is
        # what makes *sampling with the quota applied* possible instead of drawing flat and hoping.
        for decade in range(window[0], window[1] + 1, 10):
            candidates += cursor.execute(query, limit, decade, decade + 9).fetchall()
        if also:
            # ⚠️ Keyed by game *and* offensive team, because a game is two directions and they are two
            # different boards. Deduplicating on the game id alone would drop the second direction
            # whenever the draw happened to contain the first — silently halving what was asked for.
            drawn = {(row[0], row[2]) for row in candidates}
            candidates += [
                row for row in cursor.execute(named_query, *also).fetchall() if (row[0], row[2]) not in drawn
            ]
        # ⚠️ `year`, not `season`. This unpacked into `season` and shadowed the `season: Season`
        # parameter that chooses the source tables — two different things under one name inside one
        # function. It broke nothing today only because every query is built before this loop runs, so
        # `season.daily` had already been interpolated; the next line that reached for it after the
        # loop would have found an integer. `g.SEASON` is a calendar year, and calling it that is both
        # the fix and the more accurate name. Found by the discovery ratchet once the ratchet could
        # report at all (v36-P1-01, PLR1704).
        for (
            game_id,
            year,
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
            batting_rows = _rows(connection, rows_query, game_id, offense)
            pitching_rows = _rows(connection, pitch_query, game_id, defense)
            if not batting_rows or not pitching_rows:
                continue
            # ⚠️ **The other direction of the same game, for the reveal only.** The board never sees
            # these rows; the printed sheet at the end of the game does. Same two queries with the team
            # ids swapped, so *who batted* and *where he played* keep one definition across both clubs.
            defense_batting_rows = _rows(connection, rows_query, game_id, defense)
            offense_pitching_rows = _rows(connection, pitch_query, game_id, offense)
            offense_name = team_name(connection, team_names, offense, year)
            defense_name = team_name(connection, team_names, defense, year)
            if not defense_batting_rows or not offense_pitching_rows:
                rejected["the other direction has no rows to print"] += 1
                continue
            if offense_name is None or defense_name is None:
                # Schema 5 heads the reveal with the club's real name and there is no fallback: see
                # `TEAM_NAME_QUERY`. A direction whose club cannot be named is dropped here rather than
                # shipped with an abbreviation on the one screen that exists to remove it.
                rejected["retroTeams cannot name a club for that season"] += 1
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
                    year,
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
                    PrintedBoxscore(
                        offense=_printed_side(offense, *offense_name, batting_rows, offense_pitching_rows),
                        defense=_printed_side(defense, *defense_name, defense_batting_rows, pitching_rows),
                    ),
                )
            )
    if rejected:
        # ⚠️⚠️ **A library printing is the wrong shape, and it is kept for one release on purpose.**
        # `discovery/` was exempt from T201 — a script printing is its interface — and promoting this
        # module into `src/` is what exposed it. Thirty-three callers read this line today, so silencing
        # it now would remove information without replacing it.
        #
        # **A2.2 is where it changes** (`docs/beta-0-plan.md`): the batch producer needs the survival
        # rate as a **number**, not as a line of output, because the five-month batch has to be sized
        # from it. That task replaces this with a returned count, and the callers get it properly.
        print(f"loader rejected {sum(rejected.values())} directions: {dict(rejected)}")  # noqa: T201
    return loaded
