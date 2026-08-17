# Data sources used by the coverage measurements

Where every number in `README.md` comes from. Two independent origins: the `DGL` SQL Server
database, and the raw Retrosheet zips on disk. The second exists because one fact the puzzle pool
depends on — which games are deduced — is destroyed before the data reaches the database.

Nothing here writes. All database work is `SELECT` plus session-scoped temp tables.

---

## A term that was wrong for a while

Reaching base on catcher's interference is abbreviated **`CI`**. Early in the design conversation it
was written `XI` and adopted without checking; that is not baseball notation and it propagated through
the code and the documents before anyone verified it. Renamed everywhere, with no alias left behind.

**Retrosheet's own column is `B_XI`** and stays as it is — that is their name for it, not ours, and
the loader must match the database. Anywhere `XI` appears in a query against `dbo.retroDailyReg` it is
correct; anywhere it appears as our label for the quantity, it was not.

---

## 1. The DGL database

**Connection:** ODBC `DSN=LocalServer`, database `DGL`, on the operator's laptop. The DSN and
database name were taken from `apps/team_matchups/config/settings.yaml`, which names `DGL` as its
`source` connection.

**Loaded by:** `DGLv2/retrosheet/scripts/*.ps1` — a numbered pipeline that downloads from
retrosheet.org, runs the Chadwick command-line tools over the event files, and bulk-inserts the CSV
output. That script folder is the reproducible loader §33 identifies as the thing that must be
backed up, since the processed database itself is not.

### Tables used

| Table | Chadwick origin | Granularity | Rows | Span |
|---|---|---|---|---|
| `dbo.retroGamesReg` | `cwgame` | one row per regular-season game | 203,908 | 1910–2025 |
| `dbo.retroDailyReg` | `cwdaily` | one row per player per game | 5,325,173 | 1910–2025 |
| `dbo.retroDiscrepancies` | Retrosheet discrepancies file | one row per player/game/stat difference | 138,189 | 1898–1986 |

**`retroGamesReg`** supplies the game universe, `SEASON` for the decade breakdown, and the game
identifier everything else joins on. It also carries the line score totals (`AWAY_SCORE_CT`,
`AWAY_HITS_CT`, `AWAY_LOB_CT` and their home equivalents) and both starting lineups with fielding
position codes — which is what the progressive reveal will need for its position labels (§7),
though this measurement did not use them.

**`retroDailyReg`** supplies the roster shape. Batters per team-game are counted as rows with
`B_G = 1`, pitchers as rows with `P_G = 1`. It carries every column the board needs — `B_AB`,
`B_R`, `B_H`, `B_RBI`, `B_BB`, `B_SO` for batting and `P_OUT`, `P_H`, `P_R`, `P_ER`, `P_BB`,
`P_SO` for pitching — plus `B_PA` and the components of the batter identity (`B_HP`, `B_SH`,
`B_SF`). Innings pitched are stored as `P_OUT`, an integer count of outs, which is exactly the
representation `python-conventions.md` requires for discrete domain quantities.

**`retroDiscrepancies`** is Retrosheet's record of where its own values differ from the official
ones, per player, per game, per stat. Columns `retrosheetValue` and `officialValue` hold the two
sides; `type` is `O` (offense), `P` (pitching), or `D` (defense); `statType` names the stat. It is
the closest thing in the database to failure type 1 of §22 — "the historical boxscore does not
balance at source" — so the funnel uses it as a filter on the board's own columns.

### What was verified about these tables

- Every one of the 203,908 games in `retroGamesReg` has rows in `retroDailyReg`. No orphans.
- Every game in `retroDailyReg` has exactly two distinct `TEAM_ID` values. No malformed games.
- **117 duplicate `(GAME_ID, PLAYER_ID)` pairs** exist in `retroDailyReg` out of 5,325,173 rows.
  Immaterial for counting roster size, but that key cannot be assumed unique.
- `retroDiscrepancies` has 17,835 rows with no `gameId` — season-level discrepancies, which the
  funnel ignores because it filters per game. Its 138,189 rows cover 44,465 distinct games.

### Tables deliberately not used

- **`dbo.retroEventsReg`** — the play-by-play. The funnel needs boxscore lines, not events, and
  `retroDailyReg` already carries them in aggregated form.
- **`retroGamesAS` / `retroGamesPost` and their daily counterparts** — all-star and postseason. The
  pool is regular season.
- **The fielding columns of `retroDailyReg`** (`F_*_PO`, `F_*_A`) — §32 records that Retrosheet
  proofs defensive stats far less closely, and the board does not use them anyway.

### Observation, not a decision

The design pipeline (`CLAUDE.md`) is written as `Retrosheet event files → cwbox → quality filter`.
`retroDailyReg` is `cwdaily` output already in SQL, and it carries every column the board needs. So
the roster-shape and quality-filter stages may not need to invoke `cwbox` at all — though the
generator will still need a real boxscore structure, and layer 4 of §22 requires end-to-end
verification against something independent. Worth deciding deliberately rather than by default.

---

## 2. The deduced games, and why the database cannot answer for them

§32 requires excluding games built from deduced event files: they are reconstructions from partial
information, and reconstructions are where boxscores that do not balance appear.

**The database cannot distinguish them.** Retrosheet ships deduced play-by-play as `.EDA` / `.EDN` /
`.EDF` files packaged inside the same `<season>eve.zip` as the good `.EVA` / `.EVN` / `.EVF` ones.
`DGLv2/retrosheet/scripts/01_download_events.ps1` concatenates every `<season>*.E??` file into a
single `<season>.EVE` before the Chadwick tools run:

```powershell
$filter = "" + $season + "*.E??"
...
(Get-Content -Path (...) -Filter $filter -Exclude $outFile) ... | Out-File ...<season>.EVE
```

That wildcard matches `.ED?` as well as `.EV?`. By the time the rows reach `retroGamesReg` the file
of origin is gone, and deduced games sit in the table with nothing marking them.

`retroDiscrepancies` does not answer the question either. It records per-player differences against
official totals — a different failure mode, and one that peaks in the same early decades, which
makes it superficially plausible and wrong.

### Where the distinction still exists

Only in the downloaded zips, at `DGLv2/retrosheet/downloads/zip/events-reg/`. A census of every
entry across all season zips:

| Extension | Files | What it is |
|---|---:|---|
| `.EVA` | 1,283 | American League event files |
| `.EVN` | 1,279 | National League event files |
| `.EVF` | 16 | Federal League event files |
| `.EVR` | 36 | Other league event files |
| `.EDA` | 49 | **Deduced**, American League |
| `.EDN` | 54 | **Deduced**, National League |
| `.EDF` | 2 | **Deduced**, Federal League |
| `.ROS` | 2,578 | Season rosters |
| *(none)* | 116 | Team files |

### How the list was extracted

`extract_deduced_game_ids.ps1` opens each zip with `System.IO.Compression`, reads only the entries
whose extension matches `\.ED[ANF]$` without unpacking them, and collects every line matching
`^id,(\S+)` — the Retrosheet record that opens each game.

**Result: 105 deduced files, 3,465 game identifiers, all between 1910 and 1968.** All 3,465 were
confirmed present in `retroGamesReg`, which is the direct proof that they had been loaded.

### Consequence

The extracted list is a stopgap that depends on the zips still being on disk in the state that
produced the current database. §32 records the real fix: **a provenance column written at load
time**, so the distinction lives in the data rather than in a list that has to be regenerated and
can drift out of step with a refresh.
