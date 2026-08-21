# The postseason, a season cut, and dropping the zips

Three questions arrived in one thread and they turned out to be one question.

1. `retroDailyPost` / `retroGamesPost` / `retroSubstitutionsPost` exist and `retroGameLogs.GameType`
   separates the rounds — how hard is it to add them so the universe of games is bigger?
2. Cut at **1952+** so the Negro Leagues need no filtering.
3. Then **only `dbo.retro*` is used and the zips can be forgotten.**

**Analysis only. Nothing was changed.** Every number uses the project's own predicates — `SHAPE_CTE`,
`CONTRIBUTED` and `zero_density_clause` imported from `discovery/difficulty-metrics/measure.py`, never
reimplemented — with the table name swapped. Both sides omit the provenance and discrepancy filters, so
both are upper bounds and the ratios between them are sound.

---

## ⚠️ The headline: 1952 does not buy either thing it was chosen for

The cut year was proposed to do two jobs. **Measured against the live database, it does neither.**

| The premise | What the data says |
|---|---|
| *"the last Negro League was 1951"* | **`EVR` games run 1913–1961.** Seven are already 1952 or later |
| *"then the zips can be forgotten"* | **Deduced games run 1910–1968.** 276 of them are 1952 or later |

Both goals are met at **1969+**, and the gap between the two years costs less than it sounds like.

| Cut | Directions | Share of pool | Calendar | Negro Leagues gone? | Zips droppable? |
|---|---:|---:|---:|:---:|:---:|
| none | 102,228 | 100% | 151.7 yr | no | no |
| **1952+** | 73,426 | 71.8% | 108.9 yr | **no** (7 remain) | **no** (276 deduced) |
| 1962+ | 68,004 | 66.5% | 100.9 yr | **yes** | no (40 deduced) |
| **1969+** | **63,691** | **62.3%** | **94.5 yr** | **yes** | **yes** |

*(Calendar years at the 674 directions a year the week consumes, §33.)*

**1969 costs 9,735 directions more than 1952 — fourteen years of calendar out of ninety-five.** §33
requires five months of forward inventory. Both numbers are absurd next to that requirement; the choice
between them is not a pool question.

### ⚠️⚠️ 1969 arrives twice, from two directions that know nothing about each other

The operator reached 1969 independently, from the sport rather than the data: *the first MLB playoffs
are 1969, before that there were none.* The database agrees, with one correction worth making precise:

| Round | Seasons | Games |
|---|---|---:|
| **WS** | **1903–2025** | 705 |
| **LCS** | **1969**–2025 | 584 |
| DVS | 1981–2025 | 511 |
| WCG | 2012–2025 | 72 |

**The World Series runs back to 1903 — what begins in 1969 is a postseason with more than one round.**
Before it, the postseason *was* the World Series. So "there were no playoffs" is right about playoff
series and needs that caveat, and 1969 is a real line in the sport rather than an arbitrary year.

**And it is the same year the deduced files stop.** The last deduced game is 1968; the first LCS is
1969. Two arguments with no connection to each other — one about how baseball was organised, one about
how Retrosheet reconstructed missing scoresheets — landing on the same cut. That is the strongest thing
that can be said for a parameter, and neither argument was derived from the other.

Divisional play also begins in 1969 and the mound is lowered the same year, so a cut there is
explicable to a player, which a cut at 1952 is not.

⚠️ **One thing the 1952 proposal gets right and the measurement confirms:** protecting against *future*
Retrosheet data is the correct instinct, because that is exactly the shape of defect this project keeps
meeting — a filter that is true about today's data and silently false about tomorrow's. The instinct is
sound. The year is a decade early, and the deduced files, which are the actual reason the zips exist,
were not in the frame at all.

---

## What the provenance table is really for

Worth restating, because the 1952 proposal was aimed at the Negro Leagues and they are not the point.

`retroGameProvenance` carries two facts and **only one of them is information**:

- **`source_type`** — the letter is the home team's league in **all 203,908 rows, zero exceptions**, and
  the `EVR` clause has never excluded a game: all 1,872 Negro League games lack a `retroGameLogs` row,
  and the pool query joins that table, so the join already excludes them completely. Redundant twice.
- **`is_deduced`** — **3,451 games** with a game log. Reconstructions from partial information, which
  §32 excludes because reconstructions are where boxscores that do not balance come from. **This is the
  whole reason the zips are read**: the DGL loader concatenates `<season>*.E??` into one `<season>.EVE`,
  so by the time the data reaches SQL Server the file of origin is gone and a deduced game is
  indistinguishable from a real one.

**So "can we forget the zips?" is exactly "is every deduced game before the cut?"** — and the answer is
1969, because the last one is 1968.

Deduced games by decade: **1910s 224 · 1920s 567 · 1930s 676 · 1940s 1,534 · 1950s 424 · 1960s 40.**
The 1960s tail is thin (15 in 1968, 3 in 1967, 5 in 1966) and it is real.

⚠️ **A cut is not the same guarantee as the table.** The table asserts *this specific game came from a
scored file*. A cut asserts *no game in this era came from a deduced file*, which is true of today's
download and is a statement about Retrosheet's future behaviour. Cheaper, and weaker in a way worth
naming rather than discovering. If Retrosheet ever publishes a deduced reconstruction of a 1975 game,
the cut admits it silently and the table would have refused it.

---

## The postseason itself: the prize is 0.73%

| | Games | Directions | Within caps | **Admissible** |
|---|---:|---:|---:|---:|
| Regular season | 203,908 | — | — | **102,228** |
| **Postseason** | **1,878** | 3,748 | 3,399 (90.7%) | **751** |
| All-Star | 95 | 16 | 16 | **2** |

**751 against 102,228 is 0.73%.** The regular season's **2010s alone** yields 11,287 — fifteen times the
entire postseason, every round, every year since 1903. By round: **WS 319, LCS 233, DVS 179, WCG 19.**

**Under a 1969+ cut the postseason keeps 573 of its 751** — LCS 233, DVS 179, WS 141, WCG 19. What the
cut removes is 178 directions of pre-1969 World Series, which is where the postseason's whole pre-war
tail lives.

### The modern skew is real and is not a reason

59% of the 751 fall in 1990 or later, which looks like an answer to the era thinness `era-after-gate.md`
describes. It is not, and the operator named the cause immediately: **playoffs are a modern-era thing.**
One round until 1968, then the LCS, the Division Series from 1995, the Wild Card game. The supply is
itself modern-skewed.

Holding the decade fixed separates the two explanations:

| 2010s only | Directions | Within caps | **Admissible** |
|---|---:|---:|---:|
| Postseason | 710 | 611 (86.1%) | **100 (14.1%)** |
| Regular | 48,594 | 45,204 (93.0%) | **11,287 (23.2%)** |

**Postseason boards survive at 14.1% against the regular season's 23.2% in the same decade.** Mean zero
density is higher (0.363 vs 0.346), mean pitchers used is higher (4.65 vs 4.09) — deeper bullpens and
lower scoring, which is what October is. There are simply more postseason games in the years the regular
pool is thin in, and the postseason is thinner there too.

⚠️ **A confound caught by design, not by inspection.** Decade and season type vary together in the raw
comparison, and the by-decade table reads exactly as clean either way. No number in it distinguishes
*postseason boards are better* from *there are more postseason games recently*. Only fixing the decade does.

---

## What adding the postseason would cost

Less than expected, and the surprises are on the cheap side.

- **Schemas are identical.** `retroDailyPost` has the same 156 columns in the same order as
  `retroDailyReg`; `retroGamesPost` the same 85; `retroSubstitutionsPost` the same 11.
- **The SQL surface is small.** 22 references to a `*Reg` table across five files, **all in
  `discovery/`** — `forge/src` does not query the database at all (the two hits in `certify.py` are
  prose in a docstring).
- **`GAME_ID`s do not collide.** Zero shared between Post and Reg, so §21's
  `sha256(namespace | game_id | offense_team)` stays unique with no namespace change.
- **The postseason needs no provenance at all.** All 121 `events-post` zips hold **403 files, every one
  `.EVE`** — 1,878 games, **not one deduced**, no league letter. There is nothing to exclude.

### ⚠️ The trap, which is the only hard part

`retroGamesPost` has **0 rows in `retroGameProvenance`**, and the pool reaches it through a **`CROSS
APPLY`** — which drops a game with no provenance row. **Today the postseason is excluded correctly and
by accident.**

**The tempting fix is `OUTER APPLY`, and it must not be taken.** It would admit the postseason and
simultaneously turn the regular season's fail-closed drop into a fail-open pass: a regular-season game
missing from a stale provenance table would enter the pool instead of being refused. That is this
project's recorded defect verbatim — *the absence of a check reading as the presence of a passing one* —
arriving attached to a feature that has nothing to do with it.

⚠️ **Note that a 1969+ cut makes this disappear rather than solving it.** With no provenance table there
is no `APPLY` to get wrong, for either season type. That is the strongest argument for the cut and it is
not the one it was proposed on.

### Two smaller things

- **4 postseason games have no `retroGameLogs` row** and are dropped by the join already there. Noted so
  the count is not a mystery later.
- **`GameType` has NULLs.** 739 log rows carry no type — 713 also in `retroGamesReg`, 2 in
  `retroGamesPost`. Any filter on it must be an **acceptance list** (`IN ('WS','LCS','DVS','WCG')`),
  never `<> 'REG'`, which would sweep the NULLs in silently. The column looks like it partitions cleanly
  and does not.

---

## The one argument for the postseason that survives

Not pool size. **319 of the 751 are World Series games.**

§7's reveal prints the complete boxscore with the clubs' real names and the date. Resolving to *Game 7
of the 1991 World Series* is a different payoff from a Tuesday in June 1953 — and 1991 survives a 1969+
cut, while the 1912 World Series does not. Nothing about the solve
changes — the player learns which game it was only at the end, so it stays deduction rather than
knowledge and the Immaculate Grid line in the anti-goals is untouched.

**That is a §7 decision about the reveal, worth 319 directions, and it should be taken as one.** Framing
it as *the universe of games gets bigger* attaches it to a 0.73% pool argument that does not hold, and
this project has a rule about bundled claims: a fix that solves most of a problem reads like one that
solves all of it.

---

## What is actually on the table

**Recommended: cut at 1969+, and let the provenance table and the zip dependency go.**

It delivers both stated goals — no Negro League data ever, no deduced game ever — which 1952 delivers
neither of. It costs 14 years of calendar out of 95, against a requirement of five months. It deletes
`load_provenance.ps1`, the 203,908-row table, the `CROSS APPLY`, the staleness hazard in
`docs/reloading-retrosheet.md`, and the whole class of *"did you rebuild provenance after the load?"*.
And it removes the `OUTER APPLY` trap above rather than requiring it to be navigated.

⚠️ **What it costs that is not in the table:** the guarantee changes from *this game came from a scored
file* to *no game in this era came from a deduced file*. The second is a claim about Retrosheet's future
behaviour. If that matters, keeping the table and cutting at 1952 is coherent — but then the zips stay,
and the reason to cut at 1952 rather than anywhere else disappears.

**The postseason is a separate decision and should not ride on this one.** On pool grounds: no, 0.73%
with worse boards. On reveal grounds: possibly, for the World Series, and that wants measuring against
players rather than against the database.

**Both are the operator's calls.** Nothing here has been implemented.

---

## ⚠️ A stale document found on the way

`era-after-gate.md` is cited as the open era problem and **its funnel is measured at ≤2 pitchers.** At
the decided ≤6 the same predicates give **102,228 admissible directions against its 12,218**, and the
2010s go from **50 to 11,287** — a 225× change in the decade the document calls starved, because ≤2
selected complete games and modern baseball hardly produces them.

The modern era is not thin any more. Its three levers — stratify the calendar, raise the gate to 35%,
loosen the pitcher cap to 3 — were all costed against a starvation that no longer exists. **Not
corrected here**, because this file is about the postseason and rewriting another measurement in passing
is how a correction gets lost. Recorded in `docs/reviews/todo.md`.
