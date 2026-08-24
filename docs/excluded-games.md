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
| 9 | **Negro Leagues (`EVR`)** | **1,872** | source type | excluded **twice**; the rule's own bite is **zero** |
| 10 | **Postseason before 1969** | **384** | `POSTSEASON_SEASON_FLOOR` | real bite: **158 gated directions** |
| 11a | **No `retroGameLogs` row** | **2,901** | an inner `JOIN` | ⚠️ **incidental** — nobody asked for it; the block costs **6,060 gated** |
| 11b | **Deduced reconstructions (`ED*`)** | **3,465** | `is_deduced` | deliberate, **redundant** — §7 removes them first |
| 11c | **No line score** | **17,282** | `VisLineScore` | incidental: no line score, no board |
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

## 9. Negro Leagues games — `EVR`

**1,872 games, 1913–1961. Excluded, and excluded twice.** §32 states the rule: only `dbo.retro*`, and
only the three accepted source types.

| | |
|---|---|
| **Deliberately** | the acceptance list `('EVA', 'EVN', 'EVF')` in `REGULAR.admission`. `EVR` is not in it, and it is an **acceptance** list, so a game escapes only by having one of the three |
| **Incidentally** | **not one of the 1,872 has a row in `dbo.retroGameLogs`**, and the cohort `JOIN`s that table inner |
| **Marginal bite of the rule** | **zero directions**, gated and ungated |

### ⚠️⚠️ The deliberate exclusion never exercises, and that is what is worth recording

Accepting `EVR` and changing nothing else admits **0 games** — measured, both cohorts. The games are
gone before the acceptance list is consulted, because the game-log join removed them.

**So the presence of `EVR`-not-in-the-list must not be read as a tested guarantee.** It has never
rejected a game, and *a check that never fires is indistinguishable from a check that is broken.* It is
correct, it is the right shape, and nothing has ever demonstrated it working.

⚠️ **Re-admitting needs both pieces changed, not one.** Adding `'EVR'` to `PROVENANCE_SOURCES` does
nothing on its own; the game-log join would have to go too. **Stated so a future reader who makes the
one-line change and sees no effect does not go looking for what else is in the way and remove it.**

⚠️ **Where the exposure actually is:** if Retrosheet ever publishes game logs for these games, the
acceptance list becomes the only thing standing — and it will be doing, for the first time, a job
nothing has ever confirmed it does.

---

## 10. Postseason before 1969

**384 games, 1903–1968. A real filter with real bite: 669 ungated directions, 158 gated.** These are
boards that would otherwise be built.

`POSTSEASON_SEASON_FLOOR = 1969`, a `WHERE g.SEASON >= 1969` inside `POSTSEASON.admission`. ⚠️ **Not the
same mechanism as §9 and not the same SELECT** — a season predicate in one `Season`, an acceptance list
in the other.

### The declared reason, which is the provenance one rather than the taxonomic one

**The postseason has no provenance table**, and none is needed for what exists: every postseason event
file is `.EVE`, none deduced, no league letter. **So the floor is a blunt stand-in for a per-game check
that does not exist there** — and it is set where **the last deduced game in the whole database, regular
season included, is 1968.**

⚠️ **That is the reason. The divisional-play boundary is context, not the argument.** From the data:
**5.9 postseason games per season before 1969 against 26.7 from 1969** — the World Series alone against a
multi-round postseason. 65 of the 66 seasons from 1903 to 1968 are present; the one missing is **1904**,
when no World Series was played. It makes the line explicable to a player, and it is not why the line is
there.

⚠️ **A floor is a weaker guarantee than a provenance table.** The table asserts *this game came from a
scored file*; a floor asserts *no game in this era came from one that was not*, which is a claim about
Retrosheet's future behaviour rather than about a row.

**What would re-admit them:** lowering `POSTSEASON_SEASON_FLOOR`. One constant, and the 158 gated
directions come back.

---

## 11. What the sweep found — four populations nobody registered

⚠️⚠️ **Two of these are exclusions nobody asked for, and one is a clause that removes nobody.**

### 11a. Games with no `retroGameLogs` row — **incidental, 2,901 games**

The cohort does `JOIN dbo.retroGameLogs l`, inner. **Nobody wrote that as a rule**; it is there because
the line score, the forfeit, the protest, the completion and the account all come from that table.

**Dropping the join and every clause that depends on it admits 21,461 more ungated directions and
6,060 more gated ones.**

⚠️⚠️ **This is §6's `CompletionInfo` shape at fifteen times the size** — an exclusion that exists by
consequence, that no document asked for, and that a join change would undo silently. §6 is registered
because somebody noticed it; this is larger and was not.

**What re-admits it:** changing the join to `LEFT`, or moving any of the five dependent facts to another
source. Either does it **without the word *exclusion* appearing in the diff.**

### 11b. Deduced reconstructions — `ED*`, **deliberate but redundant**

**3,465 games**, 3,451 of them with a game log. `is_deduced = 0` in the acceptance apply excludes them
(§32). **Marginal bite: zero** — all 3,451 carry `AcquisitionInfo = 'D'`, so §7's complete-account rule
removes them first. Same standing as §9: correct, deliberate, and never the clause that does the work.

### 11c. Game logs with a NULL `VisLineScore` — **incidental, 17,282 rows**

`l.VisLineScore IS NOT NULL` is a construction requirement — no line score, no board — rather than a
product decision. **Marginal bite zero**, for the same interlock reason.

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

### ⬜ What the sweep put in front of the operator — four rulings, none of them taken here

**None of these is a defect and none is urgent.** They are places where *what the code does* and *what
anybody decided* are different sentences, and only he can close that gap. **Nothing has been changed in
the query, and none of these proposes admitting a game.**

| | the question | if he says nothing |
|---|---|---|
| **11a** | **`retroGameLogs` — does the exclusion become asked-for?** 2,901 games are out because five needed facts live in one table and the join is inner. **Nobody decided this**; it costs 6,060 gated directions | it stays, undecided, and a future join change undoes it without the word *exclusion* in the diff |
| **11c** | **A missing line score** — almost certainly a construction fact rather than a product decision, but it has never been written as either | same |
| **9, 11b, 11d** | **The three dead clauses — stay, go, or documented at zero?** Negro Leagues, deduced files and the season window each remove **nothing on the margin.** They are correct and none has ever fired | they stay and this register records the bite as zero, which is the state as written today |
| **10** | **Is 1969 the floor he wants?** It is a real filter costing 158 gated directions, resting on *the last deduced game is 1968* — a claim about Retrosheet rather than about a row | it stays at 1969 |

⚠️⚠️ **The recommendation on the three dead clauses is that deleting them is the one option with a
cost.** A clause that removes nothing today is doing no work and is also the only thing that would do
the work if the data changed — §9 says exactly where that could happen. **Documented-at-zero is what
this register now does**, and it is the state that survives somebody measuring them again and finding
zero.

⚠️ **11a is the one worth an actual answer**, because it is the largest exclusion in this document, it
was nobody's decision, and it is the only one that can be reversed by a change whose subject is
something else entirely.

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
