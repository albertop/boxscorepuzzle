# Puzzle package, schema version 5

**Version 4 is not amended.** A version is replaced, never extended — the fourth time that rule has
been applied here, which is the reason to keep applying it.

⚠️ **What version 5 adds: the boxscore the player reconstructed half of.** Version 4's `reveal` carried
the names of the rows the board drew and nothing else, so the finished screen could only redraw the
board the player had just filled in with the names attached. A printed boxscore is a different object.
It has **both clubs**, it has **runs batted in**, and it **names the teams** rather than abbreviating
them to three letters.

⚠️ **The playing board is untouched, and that is deliberate.** §6 is a screen budget for the board and
nothing here spends any of it: `puzzle`, `solution`, `labels` and `slot_references` are byte-identical
to what version 4 wrote. The new block is display-only. It feeds no deduction, enters no identity, and
is read by nothing the four validation layers depend on — `certify_for_publication` checks it for
plausibility, and no arithmetic anywhere consults it.

⚠️ **It is a version rather than a tightening, by the test the previous four were decided with.** Every
schema-4 file in the repository would be *rejected* by this reader, because `reveal.boxscore` is
required whenever a reveal is present. A document that used to be valid and now is not is exactly the
case that must not reuse a number.

## ⚠️⚠️ The rule this version puts on the calendar

**The reveal now prints both clubs, and the other club's half is the other puzzle of that game.** §5
makes a game up to two boards, one per direction — A's offence against B's pitching, and the reverse.
Publishing both directions of one game hands the second board away inside the first one's reveal,
completely: every cell of it, before it is played.

**The decision taken with this version is one game, one puzzle.** The pool is 400,000+ directions, so
spending a whole game on each board costs nothing measurable, and it is the only rule here that cannot
be checked by looking at a package — a file cannot know what else was published.

`write` cannot enforce it. It sees one package and the rule is about a set. It is enforced where sets
are assembled: `write_reference_puzzles.refuse_second_direction` asserts it over the batch that was
actually written, separately from the `claim` filter that already refuses a repeated game while
*choosing* — a rule applied during selection is not a check performed at the boundary. **When the
calendar is built it inherits the obligation**, over everything ever published rather than over one
batch.

## ⚠️ The reveal repeats the board, and the repetition is checked

`reveal.boxscore.offense.batting` restates every batting column the board carries except `PA`, and
`reveal.boxscore.defense.pitching` restates the whole pitching line. **Two places holding one set of
facts is the shape of every serious defect this project has found.**

It is duplicated anyway, on purpose. The alternative — a block carrying only the half the board does
not have — leaves the renderer stitching a printed sheet from two sources with different row orders,
which trades a checkable duplication for an unchecked join.

So it is checked. `check_reveal_agrees` compares the two cell by cell on every column they share, plus
the names and the labels, and it runs in `Package.__post_init__` — the one boundary a package crosses
whether it was built in memory or parsed from a file. A package whose two halves disagree cannot be
constructed.

**What it cannot check: the other half.** `offense.pitching` and `defense.batting` appear nowhere else
in the package, so nothing here could tell a real one from a fabrication. That is the layer-4 problem
and it belongs to `certify_for_publication` against the game log.

## What travels

Two shapes exist. The forge holds the full package; **`published()` produces what leaves the
laptop**, and the *Published* column below is the part `serve` actually receives. That distinction
used to live only in the code, which is the implicit-contract shape this project has paid for
repeatedly — `forge/tests/verify/test_schema_document.py` asserts this table against what `published()`
really does, so the two cannot drift.

⚠️ **The section was lost in the cut from v4 to v5, and the guarantee it describes never lapsed.** The
test reads *this* document rather than a pinned version — `DOCUMENTS` is keyed off `SCHEMA_VERSION` — and
it checks both directions: every field the table calls **kept** is published, and **nothing published is
absent from the table**, which is the direction that matters more, because a field reaching `serve` that
nobody wrote down is a contract the client can come to depend on by accident.

⚠️ **The path is `forge/tests/verify/test_schema_document.py`.** v4 said `forge/tests/test_schema_document.py`,
which is not where it is — a pointer that sends a reader to nothing is how a real guarantee comes to look
like a claim.

| Field | Type | Null? | Published | Meaning |
|---|---|---|---|---|
| `schema` | integer | no | kept | Always `5` here. A reader that sees anything else must refuse the file — including `4`, whose reveal cannot name a club or print a second one. |
| `puzzle_id` | string | no | kept | Opaque, 16 hex characters. Derived from the game and the batting team, **never** the Retrosheet id, and it encodes neither team nor date (§7, §21). |
| `puzzle` | board | no | kept | What the player is handed. `null` in a grid cell is a blank to fill. |
| `solution` | board | no | **kept** | The completed board. Ships deliberately — see below. |
| `labels` | list of strings | no | kept | One per batting row: the **bare** fielding position the man entered at — `CF`, `SS`, `P`. **Never suffixed.** Two rows may read `CF`; `slot_references` is what identifies a row, and a suffix would number by position while the indentation groups by slot, which are different partitions (§7). |
| `pitcher_labels` | list of strings | no | kept | `SP`, then `RP-1` onwards in order of appearance from the substitution record. Never a bare `P`, which the batting section already uses. |
| `slot_references` | list of strings | **no** | kept | One per batting row, in row order: `9` where a lineup slot holds one row, `9a`/`9b` where it is shared. **The string the board draws and the footnote line prints** — the client never derives it. Pitching rows carry none: those are the opposing team's pitchers and have no place in this batting order. |
| `offense_is_home` | boolean | **no** | kept | Which half of the line score batted last. **Not derivable by the client**: it is determined by a ragged line score and undetermined by a square one, so a client that inferred it would be right only sometimes. `true` or `false` — never `0`/`1`, which is a producer speaking a language this field does not. |
| `reveal` | object | yes | kept | The answer to the mystery: the printed boxscore, names, teams, date, card (§7, §29). |
| `metadata` | object | no | **filtered** | Rich metadata per seam C3. Keys that would give the game away are removed on publishing: `game_id`, `retrosheet_id`, `season`, `date`, `teams`. |
| `signature` | string | yes | kept | Ed25519 over the published shape, keys sorted, separators compact, `signature` itself excluded. 128 hex characters. The forge holds the private key and `serve` holds the public one, so the service can verify and cannot sign. |

### board

| Field | Type | Null cells? | Meaning |
|---|---|---|---|
| `batting` | list of rows, 6 wide | yes | `PA, AB, R, H, BB, SO` — the column order is part of the format (§6). The keys are `plate_appearances … strikeouts`; `SO` is the printed label and always was the same column. |
| `batting_totals` | row, 6 wide | yes | The totals line, erasable like any row. |
| `footnotes` | list of rows, 4 wide | no | `HBP, SF, SH, CI`, one row per batter. ⚠️ **Never erased, and this is what version 4 changes.** The cells were open in version 3 and the pool run closed them: coverage is identical either way because 96% of the pool's terms are zero. A `null` here is a blank the player is asked for and given no way to enter, so the reader refuses it (§5, §6). |
| `footnote_totals` | row, 4 wide | **no** | Never erased; a null here is malformed rather than difficult. |
| `left_on_base` | integer | no | The team footnote. Without it the global identity cannot be expressed at all. |
| `pitching` | list of rows, 6 wide | yes | `IP, H, R, ER, BB, SO`, **innings held as outs**. |
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
| `boxscore` | object | **Required from version 5.** Both clubs, complete. See below. |
| `card` | string | §29's generated reveal card. **Outstanding** — empty in the reference files, template work over data already present. |

**⚠️ `offense_team` was wrong in four of the first six files**, because it was taken from the game
identifier, which holds the *home* club. It coincides whenever the home side batted and lies
otherwise, and no verifier layer can see it: a wrong team name breaks no equation. It is now taken
from the same query as the roster, and `boxscore_verify.plausibility.reveal_faults` checks the block
before a file is written.

### reveal.boxscore

Two keys, `offense` and `defense`. ⚠️ **They name the *puzzle's* sides, not the game's** — the offence
is the club whose batting the board carried, the defence the club whose pitching it carried. Each side
holds **both** its batting and its pitching, so `offense.pitching` and `defense.batting` are the half
the board never showed. Named after the puzzle rather than after home and away so one vocabulary runs
through the package; `offense_is_home` already means this.

| Field | Type | Meaning |
|---|---|---|
| `code` | string | The three-letter Retrosheet key. Equals `offense_team` / `defense_team`, and the reader refuses a package where it does not. |
| `city` | string | `St. Louis`. **Non-empty**, and there is no fallback to `code`. |
| `nickname` | string | `Browns`. **Non-empty.** |
| `batting` | list of objects | `name`, `position`, `ab`, `r`, `h`, `rbi`, `bb`, `so`. |
| `pitching` | list of objects | `name`, `role`, `outs`, `h`, `r`, `er`, `bb`, `so`. `outs`, never innings. |

**⚠️ `city` and `nickname` are two fields rather than one string** because the narrow places on a phone
print the city alone — a line score has ten numeric columns at 375px and no room for a nickname — and a
renderer splitting a joined string would be guessing where the city ends.

**⚠️ Both are required and a blank is refused rather than filled in.** Measured over every team-season
the pool can draw: **2,892 of 2,901 resolve to exactly one `retroTeams` row, and the nine that fail
resolve to zero rather than to two** — Negro League and exhibition clubs whose season windows do not
cover the game. So there is no ambiguous case to arbitrate, only an absent one, and the loader drops
that direction. A renderer silently substituting the abbreviation would put `SLA` back on the one
screen this version exists to take it off, and the absence would read as a passing check.

**⚠️ `rbi` is here and on no board.** §6 gives the board six columns and `PA` takes one of them because
`PA` is what breaks the constraint forest. `RBI` earns none of that — no cross-team counterpart, no
place in the row identity — which is exactly why it is worth printing at the end: it is the one number
on the finished sheet the puzzle never asked for. **`PA` is not here**, because no newspaper printed it.

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

## How a batch is published

A generation is a directory of packages, immutable once written, named by a digest of its own
contents. `manifest.json` at the root names the generation that is current:

```
<inventory>/
  manifest.json          {"schema": 1, "generation": "<12 hex>", "puzzles": ["<id>", ...]}
  <generation>/<puzzle_id>.json
  <generation>/days/<date>.json   {"date", "puzzle_id", "generation", "schema", "signature"}
```

⚠️⚠️ **That is the PRIVATE inventory, and since E1 it is not what `serve/data/puzzles/` looks like.**
The served root is flat and holds two days (`docs/calendar.md`):

```
serve/data/puzzles/
  today.json  yesterday.json          the dated pointers, copied by publish.rotate
  <puzzle_id>.json                     the two public packages
  manifest.json                        {"schema": 1, "puzzles": [<the two ids>]}
```

**A pointer names the generation that owns its package**, which the rotation uses to find the file in the
inventory. The browser never does: the public path has no generation directories at all.

⚠⚠ **`schema` there is the *manifest's* own format version and does not track the package schema.**
Two documents, two independently versioned formats, one key name. It is `MANIFEST_SCHEMA` in
`forge/scripts/build_inventory.py` and it has been `1` since the manifest existed, while the package
schema is on its fifth version — so a reader who takes the `1` for a package version concludes the
inventory is four versions behind. **A package's own `schema` is a different field in a different file**,
written from `Package.written_as`.

**A reader follows the manifest and reads only the puzzles it names.**

⚠️ **The generation the manifest previously named is retained.** Replacing the manifest atomically
stops a reader seeing a torn pointer; it does not make *fetch the manifest* and *fetch a puzzle* one
transaction, and a cached manifest stretches the gap between them far past the rename. A reader
holding the old pointer must still be able to read all of it. **One generation back is kept, and the
commit path collects nothing** — anything older is swept on the next publish, by which time no live
manifest can name it.

⚠️ **Replacing the manifest is the commit, and it is the only atomic step there is.** Per-file atomic
renames stop a reader seeing half a file; they cannot stop it seeing three puzzles from one generation
beside three from another, and a puzzle's name cannot save it either — the name is a function of the
game (§21), so a regenerated puzzle lands on top of its predecessor rather than beside it. Everything
before the manifest rename can fail without changing what is published.

Because the generation is derived from the contents, regenerating an unchanged batch resolves to the
same generation and republishing is a no-op. That is §21's idempotence arriving at the file layer.
