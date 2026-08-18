# Puzzle package, schema version 1 — frozen

The only contract between the forge and `serve`. They are separate systems with separate deployment
cycles (§33), and this file is what `serve` is built against — **not** the forge's source.

*⚠️ Amended before anything shipped: the per-batter footnote cells became nullable, and boards are
selected on stalls rather than chain length. Both are recorded in the metadata guidance below. Nothing
had been published, so this is version 1 being finished rather than version 1 changing meaning.*

**Version 1 is append-only from here.** Fields may be added. Nothing existing changes meaning, type
or nullability. If something must change, it becomes version 2 and both stay readable.

## What travels

Two shapes exist. The forge holds the full package; **`published()` produces what leaves the
laptop**, and the *Published* column below is the part `serve` actually receives. That distinction
used to live only in the code, which is the implicit-contract shape this project has paid for
repeatedly — `forge/tests/test_schema_document.py` asserts this table against what `published()`
really does, so the two cannot drift.

| Field | Type | Null? | Published | Meaning |
|---|---|---|---|---|
| `schema` | integer | no | kept | Always `1`. A reader that sees anything else must refuse the file. |
| `puzzle_id` | string | no | kept | Opaque, 16 hex characters. Derived from the game and the batting team, **never** the Retrosheet id, and it encodes neither team nor date (§7, §21). |
| `puzzle` | board | no | kept | What the player is handed. `null` in a grid cell is a blank to fill. |
| `solution` | board | yes | **kept** | The completed board. Ships deliberately — see below. |
| `labels` | list of strings | no | kept | One per batting row: the position, suffixed by order of appearance where it repeats (`LF-1`, `LF-2`). The pitcher who batted is `P-1`, never `SP` (§5, §7). |
| `pitcher_labels` | list of strings | no | kept | `SP`, then `RP-1` onwards in order of appearance from the substitution record. Never a bare `P`, which the batting section already uses. |
| `reveal` | object | yes | kept | The answer to the mystery: names, teams, date, card (§7, §29). |
| `metadata` | object | no | **filtered** | Rich metadata per seam C3. Keys that would give the game away are removed on publishing: `game_id`, `retrosheet_id`, `season`, `date`, `teams`. |
| `signature` | string | yes | kept | HMAC-SHA256 over the published shape, keys sorted, separators compact, `signature` itself excluded. |

### board

| Field | Type | Null cells? | Meaning |
|---|---|---|---|
| `batting` | list of rows, 6 wide | yes | `PA, AB, R, H, BB, K` — the column order is part of the format (§6). |
| `batting_totals` | row, 6 wide | yes | The totals line, erasable like any row. |
| `footnotes` | list of rows, 4 wide | **yes** | `HBP, SF, SH, CI`, one row per batter. ⚠️ **Erasable** — each is an unknown inside the row identity, closed by the totals row below (§5, §6). |
| `footnote_totals` | row, 4 wide | **no** | Never erased; a null here is malformed rather than difficult. |
| `left_on_base` | integer | yes | The team footnote. Without it the global identity cannot be expressed at all. |
| `pitching` | list of rows, 6 wide | yes | `IP, H, R, ER, BB, K`, **innings held as outs**. |
| `pitching_totals` | row, 6 wide | yes | |
| `line_score` | object | no | The board's anchor: shown complete, never erased (§6). Every field required. |

`line_score` holds `offense_by_inning` and `defense_by_inning` (lists of integers) plus
`offense_runs`, `offense_hits`, `offense_errors` and the three defence counterparts.

**⚠️ The two inning arrays may be different lengths, and the shorter one means "did not bat".** The
home side does not bat in the ninth when it is already ahead, so its array is one entry short. The
client renders **`x`** in that cell, which is what a printed boxscore does.

It can only happen on the **home** side, and only in the final inning. The array is never padded, and
a reader must not assume the two lengths match — the number of innings is
`max(len(offense_by_inning), len(defense_by_inning))`.

*Written down because it was true of two of the first six files and nothing said so. An inferred
contract is the failure this project has paid for repeatedly.*

### reveal

| Field | Type | Meaning |
|---|---|---|
| `batter_names` | list of strings | One per batting row, in row order. §7 reveals a name when its row is completed, so a short list means rows that reveal nothing. |
| `pitcher_names` | list of strings | One per pitching row. **Not placeholders** — a pitching row reveals its pitcher exactly as a batting row reveals its batter. |
| `offense_team` | string | The club that batted. **⚠️ Not derivable from the puzzle id, and not the home club.** |
| `defense_team` | string | The opposing club. Both halves of "teams" or the reveal is incomplete. |
| `played_on` | string | `YYYY-MM-DD`. |
| `card` | string | §29's generated reveal card. **Outstanding** — empty in the reference files, template work over data already present. |

**⚠️ `offense_team` was wrong in four of the first six files**, because it was taken from the game
identifier, which holds the *home* club. It coincides whenever the home side batted and lies
otherwise, and no verifier layer can see it: a wrong team name breaks no equation. It is now taken
from the same query as the roster, and `boxscore_verify.plausibility.reveal_faults` checks the block
before a file is written.

## Two decisions worth stating, because both reverse an earlier one

**The solution ships with the puzzle.** It used to be stripped as an answer key. §23 requires the game
to work with the backend down, so the client cannot fetch a name when a row is completed — it has to
be holding both the solution and the reveal already. §9 accepts that a determined player can read
them in devtools. That is a trade against a network dependency in the play path, which §23 forbids
outright.

**So the solution is signed.** Anything that travels is inside the signature. A solution outside it
would be an answer a corrupted transfer could alter without the check noticing, which is exactly the
interrupted upload §33 wants caught.

**And what publishing removes is metadata, not the board.** The opaque identifier exists so nothing
in a URL names the teams or the date. A package whose `metadata` carries `game_id` beside it protects
nothing — the deliberate looseness of C3 was the hole.

## Innings

Every value in the format is an integer, and innings pitched are **outs**. `7.2` on the board is `23`
in the file. One of §3's cross-team identities is stated in outs, so storing the display form would
put a division in the middle of an identity.


## Difficulty metadata

A package records how it was selected, and the field that matters is `difficulty_model`.

| Key | Meaning |
|---|---|
| `difficulty_model` | `"stalls"`. A reader that finds anything else is looking at an artefact from before the model changed and must not compare it. |
| `target_stalls` / `stalls` | Requested and achieved. A **stall** is a transition into bounding — propagation ran dry and something beyond direct substitution was needed — counted once however many bounding steps follow. |
| `chain_length` | **Descriptive telemetry only.** It measures how long a solve is, not how hard: a chain-10 board is ten subtractions in single file. Kept so earlier measurements stay comparable; never a selection criterion. |
| `blanks`, `seed`, `families`, `batters`, `pitchers` | What the board is and how to reproduce it. |

**No difficulty label is defined.** Nothing is easy, medium or hard until the fifty-board hand-solve
returns; a band expressed in stalls will be added here when it exists.
