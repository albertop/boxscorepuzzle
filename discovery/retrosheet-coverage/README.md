# Retrosheet coverage funnel

Resolves the first open data item in design §36: whether the pool is large enough for the design to
stand on real data, before any generator code is written.

Run date: 2026-08-17. Source: `DGL` on `LocalServer`, Retrosheet regular season 1910–2025.

Counted by **direction**, not by game. A direction is one team's offense against the opposing team's
pitching. A game yields up to two, and can qualify in one direction while failing in the other (§5).

## Result

| Step | Directions | Kept |
|---|---:|---:|
| 0. Regular-season games with an event file (203,908 games) | 407,816 | — |
| 1. Minus deduced games (3,465 games) | 400,886 | 98.3% |
| 2. Minus rosters that do not fit the board (≤10 batters on offense, ≤3 pitchers on defense) | 65,522 | 16.3% |
| 3. Minus directions with a Retrosheet/official discrepancy in a board stat | 55,024 | 84.0% |

**The design holds.** The threshold for proceeding was ~100k directions, and for loosening filters
~2k. The result is 65,522 (55,024 under the stricter reading), which is the same order of magnitude
as the go-ahead figure and more than an order of magnitude above the alarm figure.

Step 2 is where almost everything is lost, and the batter cap does the work: only 18.5% of
directions use ≤10 batters, while 66.9% use ≤3 pitchers.

Of 203,908 games, 10,555 yield both directions, 44,412 yield one, and 148,941 yield none.

## Decade distribution

| Decade | After deduced | After roster | After discrepancy |
|---|---:|---:|---:|
| 1910 | 26,218 | 13,782 | 9,893 |
| 1920 | 23,700 | 10,471 | 7,054 |
| 1930 | 24,970 | 10,551 | 9,111 |
| 1940 | 23,500 | 9,122 | 8,000 |
| 1950 | 23,914 | 5,490 | 5,027 |
| 1960 | 31,844 | 5,120 | 4,987 |
| 1970 | 39,610 | 5,059 | 5,025 |
| 1980 | 40,674 | 2,874 | 2,874 |
| 1990 | 43,188 | 1,549 | 1,549 |
| 2000 | 48,582 | 900 | 900 |
| 2010 | 48,594 | 538 | 538 |
| 2020 | 26,092 | 66 | 66 |

Two figures worth isolating from the table: the pool sits 62% in 1910–1949 against 30% in 1950–1985,
and the 2020s contribute 66 directions against 13,782 from the 1910s. **Both are properties of the
provisional caps, not of the data** — see the next section.

## Pool size as a function of the caps

The funnel above bakes in ≤10 batters and ≤3 pitchers, which §6 marks as unvalidated estimates. This
table removes that assumption, so the pool size can be read off once a browser prototype produces
the real row ceiling. Non-deduced directions, no discrepancy filter.

Directions surviving, by cap pair:

| batters \ pitchers | ≤1 | ≤2 | ≤3 | ≤4 | ≤5 |
|---|---:|---:|---:|---:|---:|
| **≤9** | 14,972 | 28,886 | 36,648 | 39,361 | 39,907 |
| **≤10** | 25,425 | 49,645 | **65,522** | 72,288 | 73,943 |
| **≤11** | 40,555 | 76,008 | 101,493 | 113,747 | 117,125 |
| **≤12** | 55,130 | 103,304 | 141,400 | 162,091 | 168,559 |
| **≤13** | 67,887 | 128,766 | 181,748 | 214,233 | 225,981 |
| **≤14** | 76,880 | 148,815 | 215,691 | 261,242 | 279,983 |

The height budget constrains both sections together, so total data rows is the figure that maps onto
a measured row ceiling:

| Total rows ≤ | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Directions | 14,972 | 39,339 | 72,537 | 109,173 | 148,858 | 189,845 | 231,524 | 271,264 | 307,206 |

### The era skew tracks the row budget

| Decade | rows ≤11 | rows ≤13 | rows ≤15 | rows ≤17 |
|---|---:|---:|---:|---:|
| 1910 | 10,801 | 19,679 | 24,088 | 25,700 |
| 1920 | 7,483 | 15,444 | 20,271 | 22,527 |
| 1930 | 6,992 | 15,727 | 21,177 | 23,750 |
| 1940 | 5,880 | 13,561 | 18,853 | 21,571 |
| 1950 | 2,720 | 9,158 | 15,477 | 19,880 |
| 1960 | 1,896 | 9,334 | 18,300 | 24,949 |
| 1970 | 1,991 | 11,079 | 22,289 | 30,730 |
| 1980 | 871 | 7,399 | 18,354 | 28,636 |
| 1990 | 397 | 3,896 | 12,544 | 23,961 |
| 2000 | 196 | 2,332 | 9,607 | 22,710 |
| 2010 | 94 | 1,363 | 7,017 | 19,211 |
| 2020 | 18 | 201 | 1,868 | 7,639 |

At a budget of 11 rows, 1910–1949 holds 79% of the pool. At 17 rows it holds 34.5% and the
distribution is close to flat, with the 1970s the single largest decade. The skew is a consequence
of how tight the board is, not a property of Retrosheet's coverage.

## Where the conclusions live

**This document reports measurements only.** What the numbers mean for the product — whether the
pool is large enough, what the era skew implies for the calendar and the progressive reveal, and
what gets measured next — is decided in `docs/design-boxscore-puzzle.md` §5, §6, and §36. Read those,
not this file, for the current position. Keeping the interpretation in one place is deliberate: a
second copy drifts.

## Caveats

- **This is an upper bound, not the pool.** The remaining §5 quality filters — compressibility, zero
  density, line score variety, digit range — have not run, and compressibility is the expensive one
  that decides whether a boxscore is a puzzle at all. Expect a substantial further cut.
- **The discrepancy filter only covers 1898–1986.** `retroDiscrepancies` stops there, so the
  identical `after_roster` and `after_discrepancy` figures from 1987 on mean "not measured", not
  "clean".
- **Batters are counted as `B_G = 1`** in `retroDailyReg`, which includes pinch runners who never
  batted. That matches what a boxscore prints, so it matches what the board must show, but it is a
  choice worth revisiting if the board ends up omitting them.
- **117 duplicate `(GAME_ID, PLAYER_ID)` pairs** exist in `retroDailyReg` out of 5,325,173 rows.
  Immaterial at this scale; worth a look before the generator trusts that key as unique.

## Deduced games — how they were identified

Retrosheet ships deduced play-by-play as `.EDA` / `.EDN` / `.EDF` files inside the same
`<season>eve.zip` as the good `.EVA` / `.EVN` / `.EVF` ones. The DGL loader concatenates every
`<season>*.E??` file into one `<season>.EVE` before running the Chadwick tools, so **the database
contains deduced games with no marker distinguishing them.** 105 such files, 3,465 games, all
between 1910 and 1968.

The zips are the only surviving record of that distinction, so `extract_deduced_game_ids.ps1` reads
the `.ED?` entries directly. `retroDiscrepancies` does not answer this question — it records
per-player differences against official totals, which is a different failure mode.

**The exclusion list this script produces is a stopgap.** The pipeline fix is a provenance column on
the game table, decided in §32 — a regenerated list is a second source of truth that can drift.
Once provenance is recorded at load time, this script is only needed to backfill it.

## Reproducing

```powershell
./extract_deduced_game_ids.ps1
./coverage_funnel.ps1
./cap_sensitivity.ps1
```

Sources, table-by-table provenance, and how the deduced list was obtained: `data-sources.md`.
