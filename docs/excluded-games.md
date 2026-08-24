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

⚠️ The classes overlap. `PHA194309240` is a tie **and** sixteen innings; `DET193208010` is a forfeit
**and** an upheld protest. The counts are per class, not a partition.

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

⬜ **The season boundary is not settled here.** The contradiction appears in 2021 and 2023 and not in
1954, 1994 or 2013. **Whether the rule applied in the postseason, and exactly what happened in the
shortened season it was introduced in, is a fact about the rulebook that the data cannot answer** — it
is the operator's, and it decides admissibility for every extra-inning game after it.

### ⚠️⚠️ What the unset boundary does, and the version of it that was wrong

`AUTOMATIC_RUNNER_FROM` is `None` in `boxscore_domain`, and the rule around it is fully wired: the
query would exclude the era, `produce()` would refuse it, `audit()` would refuse a board already in the
calendar from it. **All three are dormant until the year exists.**

**The loud failure is scoped by `AUTOMATIC_RUNNER_FLOOR = 2014`** — the last season measured clean, plus
one. An extra-inning game from 2014 on raises while the boundary is unset; one from before it does not.

⚠️⚠️ **The first version raised on every extra-inning game, and it aborted a production run on a 1964
board.** That is *unknown* being applied as *always*: it does not fail closed on the case in question, it
halts all production for a question about a different era. **An open decision that blocks the seasons it
is not about is not caution, it is a different defect** — and it is the one that reads as rigour.

⚠️ **What makes the narrow form safe is that neither constant is the guarantee.** A placed runner is
caught **per game** by the global identity at construction, whatever the season — he is put out, scores,
or is stranded, and each leaves an out or a run or an LOB with no plate appearance behind it. That is
exactly what the five-game measurement above shows. **The boundary buys work avoided, not correctness:**
306 games not processed to be discarded.

⚠️ **`AUTOMATIC_RUNNER_FLOOR` is not a stand-in for the boundary and cannot become one.** It says which
seasons *demand an answer*; only `AUTOMATIC_RUNNER_FROM` says which games are excluded. If a clean
extra-inning board from 2016 is ever published, the floor becomes 2017 and no game changes status.

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

## What is still open

- ⬜ **Batting out of order.** No column found that marks it. **Named as unknown rather than guessed.**
- ⬜ **The automatic-runner season boundary** (§2 above) — the operator's, and it is a rulebook fact.
- ✔ **The four shipped partial-account games and the seventeen-inning board were replaced on
  2026-08-23**, all five future dates, by `build_inventory.py --replace` (§21: a future date is replaced).
  The table in §7 records what each one was.
- ✔ **The 145 boards produced before the facts existed were restamped, not regenerated.**
  `--restamp` reloads each game, rebuilds the board, **asserts every field matches the published
  package**, and writes it back with `innings`, `account` and `disposition` recorded. A board that came
  back different would have stopped the run as a finding about the producer. ⚠️ This is what lets
  `audit()` ask the register of the *population* rather than only of the arrivals.
