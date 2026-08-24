# Games excluded from the pool, and why

**The register.** Decided 2026-08-23. `forge/src/boxscore_forge/pool.py` is where the clauses live and
`produce()` is where a board is actually refused; this says **which games** and **on what grounds**, so
a future reader who meets a refusal on a game that balances perfectly does not conclude the check is
broken and delete it.

⚠️⚠️ **Most of these are not arithmetic failures.** They balance. Several were tested through the
production path and **published boards the four validation layers accepted**. §22's layers ask whether
the numbers agree with each other, and for these games they do — the numbers describe a game the board
cannot honestly show. **That is a product decision, not a correctness one**, and it is the reason this
document exists rather than a comment.

**What lies is the reveal.** §29 prints the finished boxscore with teams and date beside a Baseball
Reference link. A player who follows it finds *forfeited*, or *tie, called*, or a game finished three
weeks later — a disposition the board never showed and **cannot** show.

---

## The register

Counts are over the **gated** cohort (§5's zero-density gate at 0.30): **100,196 directions** before
these exclusions. Measured 2026-08-23 against the dataset then loaded.

| # | Excluded | Games | Source of truth | Tested outcome |
|---|---|---|---|---|
| 1 | **More than 12 innings** | **888** | line score length | ❌ **fails at the reader** — `PackageError: line_score.offense_by_inning has 17 innings` |
| 2 | **Extra innings from 2020 on** | **306** | season + innings | ❌ **fails at construction** — `global_plate_appearances is off by -1` |
| 3 | **Forfeits** | **9** | `ForfeitInfo` | ⚠️ **PUBLISHES** — 4 of 9 directions produced boards the layers accepted |
| 4 | **Protested games** | **132** | `ProtestInfo` | ⚠️ **PUBLISHES** — 4 of 5 tested |
| 5 | **Tied games** | **185** | final scores equal | ⚠️ **PUBLISHES** — 4 of 5 tested |
| 6 | **Completed on a later date** | **0 in the pool** | `CompletionInfo` | not reachable today — see below |
| 7 | **Partial game accounts** | **5,177** | `AcquisitionInfo` | ⚠️⚠️ **PUBLISHES — 6 of 6 tested** |
| 8 | **Home club batted first** | **30** | event rows | already excluded before today |
| 9 | **Negro Leagues (`EVR`)** | **1,872** | source type | ✔ **settled 2026-08-17.** Not a question — see §9 |
| 10 | **Postseason before 1950** | **268** | `POSTSEASON_SEASON_FLOOR` | ✔ **floor lowered from 1969 on 2026-08-24**: +116 games, +50 gated directions |
| 11a | **No `retroGameLogs` row** | **2,901** | an inner `JOIN` | **1,872 are §9's, settled.** The other **1,029 are a stale snapshot** — the 2025-12 game logs called the 1955–67 Athletics `OAK`, the current ones say `KC1`. ✔ **deferred to the off-season reload, 2026-08-24** |
| 11b | **Deduced reconstructions (`ED*`)** | **3,465** | `is_deduced` | deliberate, **redundant** — §7 removes them first |
| 11c | **No line score** | **17,282** | `VisLineScore` | 19th-century coverage: **200 from 1910 on**, and the pool starts at 1910 |
| 11d | **Seasons outside 1910–2029** | **0** | season window | ⚠️ **removes nobody** — the data runs 1910–2025 |

⚠️ The classes overlap. `PHA194309240` is a tie **and** sixteen innings; `DET193208010` is a forfeit
**and** an upheld protest. The counts are per class, not a partition.

⚠️⚠️ **Rows 1–8 were written from incidents; rows 9–11 from walking the query.** The two halves were
produced by different methods and the second found four populations the first never looked for — see
*Why this register was incomplete* below. **The Games column is the size of the population, not what the
clause is the one removing**, and for 9, 11b, 11c and 11d those two numbers differ; each section says
which.

⚠️ **What is deliberately not here: the roster caps and §5's zero-density gate.** They define the cohort
the counts above are measured against rather than excluding a game the board could otherwise show, and
they live in §5 and §6. Named so their absence is not read as a fifth thing nobody swept for.

---

## 1. More than twelve innings

**The board draws twelve** (§6, `MAX_INNINGS`). A seventeen-inning line score has seventeen columns and
375px does not have them.

⚠️⚠️ **This was found by accident, and one had already shipped.** `a74a6230760c872b` — game
`BAL197409111`, seventeen innings — was assigned to **2026-11-01** in the published calendar. It was
signed, certified and dated, and the failure only appeared when something tried to *read* it back.

**How it got published:** `MAX_INNINGS` was checked in `_innings()`, which only runs on the **parse**
path. The constructor did not check it, so the forge built and signed a package **its own reader
refuses**. That is the write/read asymmetry `format.py` records closing three times already — slot
references, `schema`, the blank profile — plus `puzzle_id` and `signature` in v36-P2-02. **The rule was
written down, applied to five fields, and the inning cap was not one of them.**

---

## 2. Extra innings from the automatic-runner era

A runner placed on second to start an extra inning **scores or is stranded without a plate appearance
producing him**, so the global identity `PA = Outs + Runs + LOB` is short by exactly one per placed
runner — either way, because if he scores there is a run with no PA behind it and if he is stranded he
is in LOB with no PA behind him.

**Tested, not reasoned.** Three era games and three pre-era controls through the production path:

```
ERA  ANA202106200  ContradictionError: global_plate_appearances is off by -1
ERA  ANA202304090  ContradictionError: global_plate_appearances is off by -1
ERA  ANA202305050  ContradictionError: global_plate_appearances is off by -1
pre  BOS199408072  PUBLISHES  (1994, twelve innings)
pre  SEA201308270  PUBLISHES  (2013, ten innings)
```

**So this class cannot produce a wrong board** — it fails loudly during construction. The exclusion buys
nothing in correctness and stops 306 games being processed to be thrown away.

## ✔ The boundary — **settled by the operator on 2026-08-24**

| | |
|---|---|
| **From** | **2020** — the season MLB introduced the automatic runner |
| **Applies to** | **regular-season** games, 2020 onward |
| **Never applies to** | the **postseason**, in **any** season |

`AUTOMATIC_RUNNER_FROM = 2020` in `boxscore_domain`. It is a rulebook fact, which is why the data could
not answer it and §7 forbade inventing it here — the measurement above says the contradiction appears in
2021 and 2023 and not in 1954, 1994 or 2013, which is consistent with the ruling and does not establish
it.

### ⚠️⚠️ The season is half the rule, and half of it passes for the whole very easily

**A floor that refuses every 2020+ extra-inning game has the right number and the wrong rule.** It would
discard legitimate postseason boards, which have never had a placed runner in any season. The exclusion
is scoped in `boxscore_forge.produce.inadmissible` and the scoping is asserted **separately from the
constant**: `test_a_postseason_game_from_the_era_is_admitted` and `test_no_postseason_season_is_touched`
both go red if the `source_type` clause is dropped, which was verified by dropping it.

⚠️ **The exemption is an acceptance test, not an exclusion list.** A game escapes only by being
positively known to be postseason (`source_type == POSTSEASON_SOURCE`); a game whose source is
unrecorded is treated as regular season and refused. That is the fail-closed direction — a board lost
costs a board, a placed runner published costs the identity — and it is the same shape as §32's
`account != "Y"`.

### ⚠️ `AUTOMATIC_RUNNER_FLOOR` was deleted with the ruling, and this is the record of what it was for

It was `2014` — the last season measured clean, plus one — and it existed **only** to scope a loud
failure while `AUTOMATIC_RUNNER_FROM` was unset: an extra-inning game from 2014 on raised, one from
before it did not. With the boundary settled there is no question left to demand an answer to, so the
constant and the raise are gone rather than set to a value nothing reads.

⚠️⚠️ **Why it existed at all, kept because the lesson outlives it.** The first version of that raise
fired on **every** extra-inning game and aborted a production run on a **1964** board. That is *unknown*
applied as *always*: it does not fail closed on the case in question, it halts all production for a
question about a different era. **An open decision that blocks the seasons it is not about is not
caution, it is a different defect** — and it is the one that reads as rigour.

⚠️ **And neither constant was ever the guarantee.** A placed runner is caught **per game** by the global
identity at construction, whatever the season — he is put out, scores, or is stranded, and each leaves an
out or a run or an LOB with no plate appearance behind it. That is what the five-game measurement above
shows. **The boundary buys work avoided, not correctness:** 306 games not processed to be discarded. So
an error in it costs yield, never a wrong board.

### ⬜ One thing is owed, and it is engineering rather than a decision

**`audit()` cannot honour the postseason exemption**, because it reads a package's metadata from disk and
the metadata does not record whether the game was postseason. It therefore applies the regular-season
rule to every board. **That is sound today and stated at the line rather than assumed:** the batch
producer draws no postseason games at all, so a 2020+ extra-inning board in the calendar *is* a fault.

**The day the batch draws postseason games, a legitimate board is flagged and the build stops on it.**
Closing that means carrying the fact in the metadata, which is a §7 question — a postseason flag narrows
the game to 0.6% of the pool, and §7 strips `season` precisely to avoid that kind of hint. **Not the
operator's to decide until somebody proposes a shape; recorded here so it is not discovered by a false
fault.**

---

## 3. Forfeits — `ForfeitInfo`

Retrosheet's codes, from `retrosheet.org/gamelogs/glfields.txt`:

| code | meaning | in the pool |
|---|---|---|
| `V` | forfeited to the visiting team | 4 |
| `H` | forfeited to the home team | 0 |
| `T` | ruled a no-decision | 5 |

⚠️ **These games balance, and the line score agrees with the official score.** Checked on all four that
published:

```
DET192406130   official 10-6   line 033000400 / 02002200x   forfeit=V
NYA193708060   official  6-7   line 0001030101 / 0200000032 forfeit=T
```

They were **played to completion and then disposed of administratively**. Nothing is truncated and
nothing is inconsistent. The board is a truthful record of the play and a false record of the game.

---

## 4. Protested games — `ProtestInfo`

| code | meaning | in the pool |
|---|---|---|
| `P` | protested by an **unidentified** team | 0 |
| `V` | **disallowed** protest by the visiting team | 65 |
| `H` | **disallowed** protest by the home team | 62 |
| `X` | **upheld** protest by the visiting team | 2 |
| `Y` | **upheld** protest by the home team | 3 |

⚠️⚠️ **All 132 are excluded, and the distinction is recorded because it was nearly a rule.**

**A disallowed protest leaves the game exactly as played.** The 127 `V`/`H` games are sound: the protest
was lodged, rejected, and the record stands. An **upheld** protest means replay from the point of
protest — **two games stitched into one record**, which is the genuinely broken case, and there are five.

**The operator ruled to exclude all 132 rather than pay for the distinction**: 132 games out of 203,908
is not worth a rule that has to be right about five letters. ⚠️ **This is written down so nobody later
"tidies up" in the other direction and re-admits the 127 believing they were excluded by mistake — and
so nobody re-opens the question thinking the five were missed.**

⚠️ `P` — *protested by an unidentified team* — does not occur in the pool today. If a reload produces
one, it is a protest of **unknown disposition** and the acceptance form of the clause already excludes
it, which is the correct direction: unknown is not sound.

---

## 5. Tied games

**185 in the pool.** Final scores equal. The game was called and the record is complete: the line
scores reconcile and four of five tested published clean boards.

There is nothing arithmetically wrong with them. **What the reveal shows is a boxscore with no winner**,
and the share, the streak and the reveal all read a game as something somebody won.

---

## 6. Games completed on a later date — `CompletionInfo`

Retrosheet sets it when a game **was completed at a later date, after a suspension or an upheld
protest**, and records `yyyymmdd,park,vs,hs,len`.

⚠️⚠️ **Zero of these are in the pool today, and that was never an exclusion.** They are lost by the
joins — every one lacks something the query requires — so nobody asked for it and nothing states it.

**That is the shape `docs/reloading-retrosheet.md` records for the `source_type IN (...)` half of the
§32 gate: a clause that reads as a rule and excludes nothing, and nobody knew until it was measured.**
An exclusion that happens by accident is undone by a join change, silently. **It is asked for now.**

---

## 7. Partial game accounts — `AcquisitionInfo`

| code | Retrosheet's own words | in the pool |
|---|---|---|
| `Y` | we have the complete game | 94,722 |
| `P` | **we have some portion of the game. We may be missing innings at the beginning, middle and end** | **5,177** |
| `N` | we don't have any portion of the game | 0 |
| `D` | derived from box score and game story | 0 |
| *(none)* | — | 297 |

⚠️⚠️ **The largest class, and entirely silent.** Six of six tested **published boards the four layers
accepted**. A game Retrosheet says may be missing innings produces a board that balances, because the
layers check the numbers against each other and these numbers are internally consistent.

**What cannot be established from here is whether such a board is historically accurate or merely
self-consistent** — that is `CLAUDE.md`'s named limit: *the four layers cannot tell a real boxscore from
a fabricated one*, and the answer needs an independent source rather than another identity.

### ⚠⚠ The exclusion is on the flag, and the question underneath it is deliberately not asked

**All 5,177 are excluded. Retrosheet states the account may be missing innings; that is sufficient.**

**How many of them are *really* incomplete is not investigated, not compared against the game log, and
not narrowed.** Validating Retrosheet's own flag against Retrosheet's own data is not this project's
job — the flag is the source of truth about what Retrosheet has, and nothing here is better placed to
second-guess it.

⚠️ **Written down because it reads like an optimisation.** Five thousand games is the largest class in
this register and somebody will eventually notice that most of them probably have complete box scores.
**That is the reopening this paragraph exists to refuse.** The cost of being wrong is a board built from
a game with a hole in it, balancing perfectly, in front of a player — and the pool has 100,000
directions, so the games are not scarce and the saving buys nothing.

⚠️ **Four had already shipped.** These four are in the published calendar with `AcquisitionInfo = P`:

| game | puzzle id | date assigned |
|---|---|---|
| `SLN192310071` | `4f0744440236caef` | **2026-11-26** |
| `SLN192310072` | `1dc57470b44caded` | **2026-11-04** |
| `WS1191310032` | `540c14cba5fb0d37` | **2026-09-01** |
| `WS1193305312` | `2326abc48337a444` | **2027-01-08** |

**Their dates need replacing** (§21: a future date is replaced, a past one is voided and left in place).

⚠️⚠️ **Two fields, one letter, unrelated meanings.** `P` in `AcquisitionInfo` is *a partial account*;
`P` in `ProtestInfo` is *protested by an unidentified team*. They are not related and confusing them
would exclude or admit the wrong five thousand games.

---

## 8. The home club batted first

**30 in the gated pool.** Excluded before today, by an `EXISTS` over the event rows requiring the
visitor to bat the first event — never a `NOT EXISTS` over the exceptions, because an exclusion list
admits a game with no event rows at all.

**Everything about the board assumes the visitor bats first**: the `x` for the half-inning never played,
which side is `AWAY BATTING`, and the outs for a home team that wins without batting in the ninth.

⚠️ Retrosheet also carries this as `HTBF` in the game-log's field 160. **The pool does not use it** — it
asks the event rows. The two are not known to disagree and nothing checks that they agree.


---

## ✔ 9. Negro Leagues games — `EVR` — **SETTLED 2026-08-17. CLOSED. NOT A QUESTION.**

**1,872 games, 1913–1961. Excluded. Decided by the operator on 2026-08-17** (`5354e69`, *exclude Negro
Leagues games from the pool, and record why*), and **the reasoning is `docs/design-boxscore-puzzle.md`
§32** — *Negro Leagues games are excluded, and that is a position rather than housekeeping.* It is a
provenance decision, weighed and written up at length: transcribed newspaper box scores rather than
scored scoresheets, **93.7% of batter rows carrying K = 0 against 74.2% in contemporary play**, and the
cost of losing Gibson and Paige named rather than overlooked.

⚠️⚠️ **The acceptance-list clause stays, whether or not it bites.** That is settled with the exclusion
and is not contingent on measurement.

**How it is excluded, for completeness only — this changes nothing above:**

| | |
|---|---|
| the rule | `('EVA', 'EVN', 'EVF')` in `REGULAR.admission`; `EVR` is not in it |
| in fact | none of the 1,872 has a `dbo.retroGameLogs` row, and the cohort joins that table inner |
| the rule's own bite | **zero** — recorded on **2026-08-20** in `38470b9`, *the Negro League clause has never excluded a game* |

**Re-admitting would need both pieces changed, not one.** Noted so nobody makes the one-line change,
sees no effect, and starts removing whatever else is in the way.

### ⚠️⚠️ Why this section is headed the way it is

**This settled exclusion was put back in front of the operator on 2026-08-24, in a list of things to
decide.** It got there because a *redundancy* question — "these clauses bite zero: keep, remove, or
document at zero?" — swept it up with two unrelated clauses that genuinely had no ruling. The question
being only about redundancy did not matter: **the operator had to read a list and see this on it, and
say again what he had said a week earlier.**

⚠️ **Worse, the zero-bite fact was not new.** `38470b9` recorded it on 2026-08-20, four days before it
was presented as a discovery. **The sweep re-derived something already written down and then attached a
question to it.**

**The rule that follows, and it is not about this exclusion:**

> **A clause implementing a settled exclusion never appears in a list of things to decide — not even
> when the question is only about redundancy, coverage, or tidiness.**

A settled decision has one status and it is *settled*. A list headed *decide these* re-opens everything
on it, whatever the column next to it says, and the cost lands on the person who already decided. **If
a sweep finds a settled exclusion, the finding is recorded under that exclusion — as above — and does
not travel to any list.**

---

## ✔ 10. Postseason before 1950 — **the floor was lowered from 1969 on 2026-08-24**

**`POSTSEASON_SEASON_FLOOR = 1950`.** The operator's decision. It admits **116 games, 1950–1968 — 222
ungated directions and 50 gated.** All nineteen seasons are present, so the era does not arrive through
a hole in coverage. **268 games remain excluded below 1950**, 1903–1949.

### ⚠️⚠️ The justification changed with the number rather than surviving it

**What 1969 rested on was provenance, not divisional play.** The postseason has no provenance table, so
a floor set above **the last deduced game in the whole database, which is 1968** was a blunt stand-in
for the per-game check the regular season gets from `dbo.retroGameProvenance`.

**1950 gives that up deliberately.** Nineteen of the admitted seasons sit inside the deduced era, so the
floor **no longer asserts that nothing above it came from a reconstruction.**

**What it rests on now is narrower, and it is a fact about these 116 games rather than about the era.**
Every one was checked against every other rule before the floor moved:

| checked | trips it |
|---|---|
| a deduced provenance row | **0** |
| no game-log row | **0** |
| more than `MAX_INNINGS` | **0** |
| forfeit · protest · completed later · partial account · tie | **0 each** |
| home club batted first | **0** |
| extra innings | 9 — and the automatic-runner rule cannot reach them: §2 is **regular season only**, from 2020 |

⚠️ **So the floor is now a bound, not a guarantee.** Below it nothing is admitted; above it,
admissibility is whatever the per-game rules say and nothing more. That is weaker than what 1969
claimed, and it is the choice that was made — against 268 games below 1950 where Retrosheet's
transcription thins and this same check has not been run.

⚠️ **`discovery/retrosheet-coverage/check_postseason_sources.ps1` now covers nineteen more seasons than
it did.** It is what re-establishes *every postseason file is `.EVE`, none deduced* against a new
download. Without it that claim ages silently, and the floor is no longer standing in front of it.

**Context, and not the reason:** **5.9 postseason games per season before 1969 against 26.7 from 1969** —
the World Series alone against a multi-round postseason. 65 of the 66 seasons from 1903 to 1968 are
present; the missing one is **1904**, when no World Series was played.

**What would change it again:** the constant. Lowering it further reaches the 268, raising it gives the
116 back.

---

## 11. What the sweep found — four populations nobody registered

⚠️⚠️ **Two of these are exclusions nobody asked for, and one is a clause that removes nobody.**

### 11a. Games with no `retroGameLogs` row — **2,901, and only 1,872 of them are an exclusion**

The cohort does `JOIN dbo.retroGameLogs l`, inner. **Nobody wrote that as a rule**: it is there because
the line score, the forfeit, the protest, the completion and the account all come from that table.

**Investigated 2026-08-24. The 2,901 split cleanly, no overlap, no remainder:**

| | | |
|---|---|---|
| **1,872** | Negro Leagues, `EVR`, 1913–1961 | ✔ **excluded on purpose** — §9, settled 2026-08-17 |
| **1,029** | **Kansas City Athletics home games, 1955–1967** | ⚠️⚠️ **not an exclusion. A stale snapshot, and Retrosheet has already fixed it.** |

## ⚠️⚠️ The Athletics half: our download is old, and 1,015 games are waiting in the new one

**The download of 2025-12-01 named the same club two ways in two file families.**

| | event files | game logs, **2025-12-01 download** | game logs, **2026-08-24 download** |
|---|---|---|---|
| Philadelphia Athletics, to 1954 | `PHA` | `PHA`, park `PHI11` | `PHA` |
| **Kansas City Athletics, 1955–1967** | **`KC1`** | **`OAK`**, park `KAN05` | ✔ **`KC1`**, park `KAN05` |
| Oakland Athletics, 1968 on | `OAK` | `OAK`, park `OAK01` | `OAK`, first appearing in 1968 |

A `GAME_ID` is built from the home club's code, so in the old files the same game carried two
identifiers and the join missed every one of them:

```
old game log   OAK195504120   park KAN05
event file     KC1195504120   home=KC1 away=DET     <- Detroit at Kansas City, opening day 1955
new game log   KC1195504120   park KAN05            <- they agree
```

**The fresh files were checked directly**, `gl1955.zip` … `gl1968.zip`: `KC1` as the home club for
**76, 77, 77, 78, 77, 78, 80, 81, 81, 81, 81, 81, 81 = 1,029 games**, no `OAK` before 1968 and 83 in
1968, which is when the club moved. **Those thirteen counts match `retroGamesReg`'s `KC1` home games
season for season.**

## ✔ Deferred to the next full reload — **the operator's decision, 2026-08-24. Do not raise it again.**

**The database is loaded from the 2025-12 download and stays that way until the off-season**, when the
2026 season is published and everything is reloaded together. **1,015 American League games with
accepted provenance stay out of the pool until then** — known, priced, and accepted.

⚠️ **A targeted `UPDATE` was considered first and the scope check is what argued against it.** The stale
`OAK` is not confined to the game logs:

| table.column | rows carrying `OAK` in 1955–1967 |
|---|---|
| `retroRosters.teamId` | 2,520 |
| `retroTransactions.toTeam` / `.fromTeam` | 1,829 / 1,649 |
| `retroGameLogs.VisTeam` / `.HomeTeam` / `GAME_ID` | 1,031 / 1,029 / 1,029 |
| `retroCoaches.team` | 336 |
| `retroDiscrepancies.teamId` | 331 |
| `retroParkFactorsByTeam.HOME_TEAM_ID` | 171 |
| `retroTeams_6d.franchiseID` / `.teamId` | 5 / 2 |

**Each would have to be judged separately, because `OAK` is not wrong everywhere.**
`retroTeams_6d.franchiseID` is a franchise identifier and `OAK` is what it should say; the rosters and
transactions tables come from file families whose current spelling has not been checked. **A rewrite that
is correct for one table and wrong for the next is worse than the stale snapshot**, which is at least
uniformly one vintage. The reload replaces all of them from one download, consistently.

⚠️ **What the reload still owes when it happens, and it is a §21 question:** if Retrosheet corrected the
Athletics it may have corrected other things in the same files. The pool *gaining* games is safe; a
published board whose underlying row has changed is not, because the calendar's past assignments are
permanent. **Check the new files against the loaded rows field by field before the reload lands**, not
after.

### ⚠️⚠️ What this cost, and it was not the data

**The exclusion was reported twice before it was understood, and each version was confidently wrong.**

| | what it said | why it was wrong |
|---|---|---|
| first | all 2,901 are an incidental exclusion, one question for the operator | 1,872 of them were settled a week earlier |
| second | the Athletics half is *a gap in the load* | nothing was dropped; the rows were there under another name |
| third | *the data is complete and the two sides disagree about a name* — and **a fresh download will say the same, because that is how Retrosheet publishes this club** | **it was not. Retrosheet had already fixed it, and the operator found that out by downloading the files.** |

⚠️⚠️ **The third is the one worth keeping.** A single snapshot was treated as a property of the source.
The evidence was thirteen files from **one download on one date**, and the claim made from it was about
what Retrosheet *publishes* — present tense, no date, not checkable. **A downloaded file has a date, and
any statement about what a source contains inherits it.** The correct sentence was *the December
download says `OAK`*, which invites exactly the check that settled it.

⚠️ **`discovery/retrosheet-coverage/` exists for this** — re-establishing source claims against a new
download rather than trusting a loaded snapshot. It had not been run against the game logs.

### 11b. Deduced reconstructions — `ED*`, **deliberate but redundant**

**3,465 games**, 3,451 of them with a game log. `is_deduced = 0` in the acceptance apply excludes them
(§32). **Marginal bite: zero** — all 3,451 carry `AcquisitionInfo = 'D'`, so §7's complete-account rule
removes them first. Same standing as §9: correct, deliberate, and never the clause that does the work.

### 11c. Game logs with a NULL `VisLineScore` — **17,282 rows, and 17,082 of them are the 19th century**

`l.VisLineScore IS NOT NULL` is a construction requirement: no line score, no board. **Not a product
decision, and now measured rather than assumed.**

| decade | NULL | of | |
|---|---|---|---|
| 1870s | 1,489 | 2,025 | **73.5%** |
| 1880s | 8,759 | 8,759 | **100%** |
| 1890s | 6,829 | 9,468 | **72.1%** |
| **1900s onward** | **5 or fewer per decade**, except 34 in the 1950s and 34 in the 1970s | | **≈0.1%** |

**It is a coverage artefact of one era, and that era is outside the pool's window anyway** — the sampler
draws from 1910. **From 1910 on there are 200 NULL line scores in the entire database.**

⚠️ So this clause is a construction fact with an almost-empty population, not an exclusion anybody needs
to rule on. Recorded with the numbers so the next sweep does not have to ask again.

### 11d. ⚠️⚠️ The season window `1910–2029` — **excludes nobody**

`dbo.retroGamesReg` runs **1910 to 2025**. Games before 1910: **0**. Games after 2029: **0**. The clause
**removes zero games** and has, on this dataset, never removed one.

**That is the `source_type` shape — a clause that reads as a rule and excludes nothing — and it is the
third instance in this register.** It is not therefore wrong: it bounds a sampler against a dataset that
may grow. But *what it is* and *what it does* are different sentences, and only one of them was written
down anywhere.

---

## ⚠️⚠️ Why this register was incomplete, and what closed it

**It was written from what had been investigated, not from what the query does.** Every entry above
§9 arrived because something went wrong and was traced: a seventeen-inning board reached a date, a
forfeit published, a partial account published. Each was then registered. **Nothing ever walked the
query clause by clause and asked what each one removes** — so the classes that never caused an incident
were never written down, and their absence looked exactly like their not existing.

⚠️ **The operator found two of them by reading this document and noticing what was not in it.** One
missing entry is an oversight; **two found by a person reading, in a document whose subject is
completeness, means the enumeration was never done.**

**What closed it:** the whole query, clause by clause, with **population and marginal bite measured
separately** — how many games the clause is about, and how many directions it is the one removing.

### ⚠️⚠️ The instrument was wrong first, inside the sweep meant to catch exactly this

**The first pass dropped one clause at a time and reported zero for four of them.** Provenance
acceptance, the season window, the game-log join and the line score all measured as removing nothing.

**Three of those zeros were an artefact of the instrument.** The other `l.*` clauses were left in place
and every one of them requires a game-log row, so dropping the join alone changed nothing: the
population was still removed, by its neighbours. **The measurement was of marginal bite and it was
reported as population.**

⚠️ **That is the near-neighbour class again** — asserting a property that is true in the broken state —
and it happened **inside the sweep written to find instances of it**, by someone who had recorded the
rule twice the same day. It was caught the way this project catches these: four zeros in a row is a
metric that cannot vary, and a metric that cannot vary is broken rather than informative.

**What the numbers above do instead:** population is counted directly against the tables, and marginal
bite is counted by dropping a clause **with its dependants**, asserting the substitution matched exactly
once first — because a replacement that matches nothing is silent and would compare the baseline against
itself.

---

## What is still open

- ⬜ **Batting out of order.** No column found that marks it. **Named as unknown rather than guessed.**

### ✔ What the sweep left for the operator — **nothing open. All four closed 2026-08-24.**

⚠️⚠️ **This heading is the record of the list, not a live list.** Every row below is settled, and it
stays here so the same four are not re-derived and re-asked by the next sweep — which is exactly what
happened to the Negro Leagues on the day this was written.

⚠️⚠️ **This list had four rows and three of them should never have been on it.**

| | why it is gone |
|---|---|
| **Negro Leagues** | **settled 2026-08-17.** It reached a decision list because a redundancy sweep did not distinguish *a clause with no ruling* from *a clause implementing a ruling.* §9 carries the rule that stops it happening again |
| **Deduced files, and the season window** | not decisions either. Both are **documented at zero bite** in §11b and §11d, which is a fact about them and not a question. Deleting a clause that removes nothing today is the only option with a cost — it is also the only thing that would do the work if the data changed |
| **The postseason floor** | ✔ **decided: 1950** — see §10 |

**And what was actually left, now also closed:**

| | the question |
|---|---|
| ✔ **11a — the 1,029 Kansas City Athletics games** | **Settled 2026-08-24: deferred to the off-season reload.** Not an exclusion and not a pool decision — the loaded snapshot is from 2025-12, which named the club `OAK`, and the current files say `KC1`. A targeted `UPDATE` was rejected because seven tables carry the stale code and `OAK` is correct in some of them. See §11a |

⚠️ **§11c is not on this list.** A missing line score means no board can be drawn; and from 1910 on it
is **200 rows in the whole database**. It is a construction fact and §11c now says so.

- ✔ **The automatic-runner boundary was settled by the operator on 2026-08-24** (§2 above): **2020, regular season only, never the postseason in any season.** ⚠️ It stayed marked open here after he had answered it and was raised with him again as a result — **the cost of a stale marking lands on the person who already decided.**
- ⬜ **`audit()` cannot see the postseason exemption** (§2 above). Engineering, not a decision, and not live until the batch draws postseason games.
- ✔ **The four shipped partial-account games and the seventeen-inning board were replaced on
  2026-08-23**, all five future dates, by `build_inventory.py --replace` (§21: a future date is replaced).
  The table in §7 records what each one was.
- ✔ **The 145 boards produced before the facts existed were restamped, not regenerated.**
  `--restamp` reloads each game, rebuilds the board, **asserts every field matches the published
  package**, and writes it back with `innings`, `account` and `disposition` recorded. A board that came
  back different would have stopped the run as a finding about the producer. ⚠️ This is what lets
  `audit()` ask the register of the *population* rather than only of the arrivals.
