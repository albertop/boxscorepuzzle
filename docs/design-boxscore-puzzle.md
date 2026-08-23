# Boxscore Puzzle — Design Document

> Status: **Level 100 (what and why).** No implementation decisions.
> Domain: `boxscorepuzzle.com`
> Target launch: Spring Training 2027
> Last updated: August 15, 2026

---

## 1. Concept

### The one-line pitch

> **A daily puzzle where you reconstruct the boxscore of a real Major League game by logic.**

Conversational version, for explaining fast: *"Sudoku with real baseball boxscores."* Technically it's kakuro, not sudoku, but the imprecision earns its keep: it communicates in three words that this is deduction, that it's daily, and that there's no guessing.

The official definition says **"real"** and **"by logic"** — the two differentiators against Immaculate Grid and against cosmetic baseball-sudoku products.

*Neither version mentions the reveal, the archive, or the stats. That's correct: if the pitch needed to explain monetization, something would be wrong with the product.*

### Description

A website that publishes a daily puzzle built on the boxscore of a real Major League game. The boxscore is shown with cells erased, and the player reconstructs them. The solution is unique and reachable by deduction, never by guessing.

**Why it works:** a boxscore is an overdetermined system of integer equations. Baseball's accounting identities force the missing values.

**What it is NOT:** it is not reconstructing play-by-play from the boxscore. That mapping is massively many-to-one and has no unique solution.

### Anti-goals

Approved as explicit product boundaries:

- **Not trivia.** You don't answer with baseball knowledge, you answer with deduction. This is the line separating this from Immaculate Grid.
- **Not a simulator.** The game is not reconstructed play by play.
- **Not a stats tool.** Even though the data comes from Retrosheet, this is not for querying or analysis.
- **Not a baseball social network.** There is comparison among friends, but no profiles, walls, or forums.
- **Not a sudoku app with a baseball skin.** It's the reverse: baseball is the substance, not the veneer.

**The first one matters most**, because that's where real pressure will come: it will be tempting to add "guess the player" or trivia questions to make it more accessible. That would dissolve the product — **a puzzle is either deduction or guessing, not both.**

---

## 2. Target audience

**The baseball fan**, not the puzzle solver.

Consequences:

- Vocabulary (PA, AB, R, H, BB, K, IP, ER) is assumed known. No need to teach it.
- Keep the **canonical boxscore format**. Visual familiarity *is* part of onboarding. Do not "simplify" the design.
- The risk inverts: the danger isn't that baseball scares people off — it's that the fan **isn't a puzzle person** and lacks patience for constraint propagation. The opening curve must be gentler than a sudoku site's.
- Distribution channel: baseball communities (newsletters, SABR, forums), not puzzle communities.

---

## 3. The logic engine

### Constraint families

The board's constraints fall into **four families**, and which of them a solution actually had to use
is one of the two axes that describe a puzzle (§4).

**1. Column sums**

- Σ individuals = team totals, for every column (PA, AB, R, H, BB, K, and the footnote columns)
- Σ runs per inning = total R in the line score
- The line score's R and H for the offense = the batting totals for the same

**2. Row identity — per batter, and again for the totals row**

```
PA = AB + BB + HBP + SF + SH + CI
```

**This is the constraint the board hangs on.** Without it no individual cell takes part in a second
equation, the constraint graph is a forest, and the only puzzles that survive validation are rows of
unconnected subtractions (§4). With it, at-bats and walks live in two equations each, cycles appear,
and a deduction can chain.

**CI — reaching base on catcher's interference — is not optional.** Verified against every batter
row Retrosheet has: with it the identity holds in all 5,325,173; without it 1,956 fail. It is rare
enough to look like decoration and load-bearing exactly where it appears.

**3. Cross-team**

- Team A's H = Σ hits allowed by team B's pitchers, and the same for R, BB and K
- Outs made by the offense = Σ outs recorded by the opposing pitchers

**Without this the puzzle degenerates into row arithmetic.** It is the link between the two halves of
the board and the reason this is a puzzle rather than unrelated columns.

**4. Global identity**

```
PA = Outs + R + LOB
```

Every batter who came to the plate made an out, scored, or was left on base. It assumes every runner
arrived by way of a plate appearance, which was true of every team-game before 2020 bar eleven —
those eleven are source errors. Extra innings now begin with a runner already on second who never
batted, so modern extra-inning games break it and are correctly rejected.

**Inequalities**

- AB ≥ H
- **PA ≥ AB + BB** — available wherever the footnote terms are not, and it narrows from the opposite
  side to the row identity: the identity says what plate appearances add up to, this says what they
  cannot fall below
- ER ≤ R
- Non-negativity in all cells

*Dropped with the RBI column (§6): team RBI ≤ team R, and RBI ≥ HR per player. Also gone are
H ≥ 2B + 3B + HR and anything else over a column the width budget excluded — an identity over a
quantity the player cannot see is not a deduction they can make.*

### ✅ A footnote whose row is ambiguous — removed, not modelled

> **The premise no longer holds.** Repeated position labels are suffixed by order of appearance, so
> `HBP: SS-2` names one row and there is no ambiguity to express. **None of the model below is
> built**, and it should not be: it is a correct treatment of a problem the labels created and the
> labels removed. Kept because the reasoning is sound and would be needed again if the label
> convention ever changed. See §5 and §7 for the measurement that made the trade obvious.

A position label did not always name one row: with ten batters a substitute shares the starter's
label, so `HBP: SS` could mean either of two rows (§7).

**Stated as a domain, not as a choice.** Both candidate cells are left unknown, each with a domain of
{0, 1}, and the footnote's own column sum already says the pair adds to one. Nothing extra is needed
to express it. It is then settled by **bounding** — narrowing until one value is left standing —
rather than by trying each placement in turn, which would be backtracking and is what the publication
rule forbids. Usually the row's own identity settles it immediately.

**Measured, it is rarely more than bookkeeping:** across 31 ambiguous groups tried under 20 erasure
patterns each, the assignment was irrelevant in 56.6% of patterns and load-bearing in 13.5%, and
when it did matter it exercised only column sums and the row identity. It is not a source of
difficulty and is not counted as one.

---

## 4. Deduction, not guessing

**The real risk isn't ambiguity — it's derivability.**

A uniqueness proof guarantees one answer exists, but does **not** guarantee a human can reach it by reasoning. You can generate unique-solution puzzles whose uniqueness depends on a system of four simultaneous unknowns. Mathematically perfect, and the player experiences them as trial and error.

### Two axes, not a ladder

The original T1–T5 ladder did not survive contact with the board. T3 cannot fire at all (below), and
with it gone T1 and T2 are the same operation — propagation to a fixed point — while T5 is not a
technique but one more equation inside that propagation. Only bounding is genuinely different,
because it reasons over ranges rather than values.

**Axis 1 — technique required**

| | |
|---|---|
| Propagation | An equation with one unknown left in it, run to a fixed point |
| Propagation plus bounding | Narrowing a cell's range until one value is left standing |

**Axis 2 — equation families required** (§3): column sums · row identity · cross-team · global
identity. Not which were available — which the solution path actually needed.

**Publication rule, unchanged in substance:** a puzzle ships only if a solver restricted to these
techniques finishes **without backtracking**. If it needs to guess a single cell, it is discarded or
given one cell back as a hint.

Neither axis alone says how hard a puzzle feels. What describes that is the *shape* of the solution
path — how long the chain of dependent steps ran and how narrow the choice of next move became —
measured in §31.

### ⚠️ T3 is unreachable on this board (measured, August 2026)

Solving a 2×2 system needs two equations whose unknowns are the **same pair**, which requires those
two equations to share two cells. Across the board's full system — 21 equations, including the
global identity — **no two equations share more than one cell.**

The reason is structural, not a matter of degree: 90 of the 99 cells appear in exactly one equation,
because an individual batter's or pitcher's cell lives only in its own column sum. The nine that
appear in more are the team totals and the line score's runs, and no pair of equations contains two
of them together. The constraint graph is tree-like.

**No column set fixes this.** The measurement was repeated against four candidate boards, including
ones with plate appearances as a column and with footnotes attributed per player: **the maximum
overlap is one cell in every case.** The reason is that every identity here is a sum over a row or
over a column, so two of them can share at most the single cell where a row crosses a column. T3
would need a different *family* of constraint, not a different column. Treat it as closed.

### The consequence T3 carries: a board with no middle difficulty

A tree-like graph has only two regimes and nothing between them.

- Erase one cell per equation and propagation recovers it with a single subtraction.
- Erase two from the same equation and nothing can move. Propagation needs a lone unknown, the 2×2
  rung cannot fire, and bounding only settles a cell when the bound happens to be tight. Most of the
  time two blanks in one column sum are not *hard* — they are **ambiguous**, and §22 correctly throws
  the puzzle away.

So the generator converges on the trivial regime, and not because the erasure algorithm is wrong:
it is the only thing that survives the correctness rules. **The ceiling is topological, not
algorithmic.** The resulting puzzle is nine independent subtractions — solving the hits cell tells
you nothing about the strikeouts cell. Nine one-move puzzles rather than one nine-move puzzle.

Measured, as the share of random erasures that a T1/T2 solver finishes — which is the share that
could survive validation as anything other than trivial:

| Batting cells erased | Current board | With PA as a column | PA plus per-player footnotes |
|---|---:|---:|---:|
| 2 | 87.5% | 93.8% | 96.4% |
| 4 | 39.7% | 69.3% | 80.2% |
| **6** | **8.3%** | **43.4%** | **57.0%** |
| 8 | 0.3% | 20.6% | 35.3% |
| 10 | 0.0% | 7.9% | 17.2% |

### What restores the middle regime

Making **plate appearances a column** gives every batter row its own identity:

```
PA = AB + BB + HBP + SF + SH + CI
```

At-bats and walks then live in two equations each — their column sum and their row identity — and
the graph stops being a forest: **independent cycles go from 0 to 16, and cells appearing in two or
more equations from 10 to 35.** Erasing two cells from the at-bats column stops being ambiguous,
because one of them comes back through its row and the other follows from the column. That is
chaining and ordering restored, and it is done by propagation rather than by any 2×2 rule.

**The column set that followed from this is decided: `PA, AB, R, H, BB, K` (§6).**

A test in the forge holds the interconnection line. Its assertion is the **cyclomatic number**, not
the overlap: overlap can never reach two, so testing for it would be testing for something that
cannot happen.

Secondary benefit: difficulty derives itself. Not from "the highest technique required and how many
times", which is the phrasing this line carried while the ladder existed — the solver reports three
numbers instead, and which of the four equation families the path needed (§31).

### Two properties that bring it close to sudoku

- **Bounded domains.** If the team has 8 hits, no individual H cell can exceed 8. Enables a **candidates mode** (pencil marks) that makes the deduction visible.
- **Self-verifying.** If all equations balance, the player knows they're done without the site confirming it.

### What must be accepted

In sudoku all 81 cells mean the same thing. Here each column has its own semantics and the player must learn boxscore accounting. That forces an onboarding curve.

---

## 5. Daily game selection

> # ⚠️ CORRECTION (August 2026): a loader defect invalidated most of the pool measurements below
>
> **Retrosheet's `B_G = 1` marks a player as having *appeared*, not as having *batted*.** 18.8% of
> those rows — **1,000,892 of 5,325,173** — have no plate appearance at all, and 83% of those also
> pitched: the designated-hitter era's pitchers, on the card and never coming up. The loader put them
> on the board.
>
> Two consequences, and the second is what wrecked the numbers:
>
> 1. **The lineup order was wrong.** Those rows carry `SLOT_CT = 0`, and **not one row in slot zero
>    has ever batted** — the slot *is* the marker for "did not bat". Ordering by it put pitchers at
>    the top of the card and pushed the leadoff hitter to third. *Found by the operator reading the
>    hand-solve PDF, not by any test.*
> 2. **Every phantom row was six cells of nought**, so it inflated zero density, and it counted
>    against the ≤13 batter cap, so it threw out directions that fit the board perfectly well. Modern
>    teams carry more never-batting pitchers than old ones, **so the defect fell hardest on the modern
>    era** — which is exactly the era every conclusion below is about.
>
> ### What the corrected pool looks like
>
> | | With phantom rows | **Corrected** |
> |---|---:|---:|
> | Directions after caps ≤13/≤4 | 25,270 | **77,968** |
> | Median zero density | 40.0% | **34.4%** |
> | Pre-1950 share of the gated pool | 78% | **29%** |
> | Post-1980 share | 4.7% | **47%** |
> | Years of calendar at ≤2 pitchers | 5.3 | **25.5** |
> | Years of calendar at ≤4 pitchers | 18.6 | **94.7** |
>
> **The era skew was almost entirely the defect.** Survival through the 30% gate now runs 21–31% in
> every decade from the 1910s to the 2020s, and each decade contributes 5–11% of the pool. The century
> is flat.
>
> ### What this overturns
>
> - **The 5% pre-1950 quota is now solving a problem that does not exist.** Pre-1950 is 29% of the
>   pool naturally rather than 78%. The quota remains available as a *preference* about what the
>   player meets; it is no longer a fix for a broken distribution.
> - **The pitcher cap's pool argument collapses.** ≤2 gives 25.5 years of calendar, not 5.3. The move
>   to ≤4 still buys a great deal (94.7 years) but it is no longer forced. **Its quality argument —
>   cross-team falling from 100% to 78%, global rising from 50% to 70% — was measured on boards that
>   carried phantom rows and has to be re-measured before it can be leaned on.**
> - **Every metric measured on loaded boards is suspect**: chain ceiling, the bands, where the metrics
>   stop discriminating, the week topping at 13, the erasure ordering comparison, the 71% layer-3b
>   figure, and the fifty-board hand-solve pack. All were computed with all-zero rows on the board.
>
> ### What is unaffected
>
> The board's column set and the identities; the verifier and its four layers; the label suffix rule
> (re-measured: 44.2% of directions still carry a collision, 9.0% one a footnote lands on); innings as
> outs; the team-named section headers; the removal of the line score tint. None of those depend on
> which rows were loaded.
>
> **Everything below this box that quotes a pool figure or a difficulty metric is pre-correction
> unless it says otherwise.** It is left in place rather than rewritten, because the shape of the
> reasoning still holds and silently restating the numbers would hide that a measurement error drove
> two decisions.

**Criterion: random among games with good puzzle shape.** Not anniversaries, not historical significance.

### The quality criterion (rewritten August 2026 — the original was wrong at the root)

This section used to name **compressibility as the primary metric** with three cheap screens
approximating it. Measurement showed both halves of that to be wrong, and the correction matters
enough to state before anything else:

> **Compressibility is a volume metric, not a quality one.** It measures how much can be taken away,
> not whether what remains gives the player anything to think about. **Maximising it selects
> boredom** — a column summing to nothing forces every blank in it, so the most compressible boards
> are the emptiest ones.
>
> **The three screens do not approximate it. They anticorrelate with what we want.** Zero density
> predicts compressibility at **+0.79** and digit range at **−0.70**, so screening *for*
> compressibility selects exactly the low-scoring games the original list wanted to exclude.

**What replaces it, in order:**

1. **Roster compactness** — hard filter, **≤13 batters in the offensive team and ≤2 pitchers in the
   defensive team**, decided by the browser prototype's measured row ceiling (§6). The filter is
   **asymmetric**: only the offensive team's batters and the defensive team's pitchers appear on the
   board.
2. **The zero-density gate — below 30%, decided.** Direct, cheap, and it attacks the cause instead of
   trying to score it.
3. **Compressibility as a viability constraint, not a ranking.** A board must be able to lose enough
   cells to be a puzzle at all. Above that floor, compressing further is not better and does not
   order one candidate above another.
4. **Chain length, search cost and resolution p90** — the three numbers that grade what survives
   (§31). These are properties of an erasure, not of a direction, so they belong to the generator
   rather than to pool admission.

*Line score variety and digit range are dropped as filters. They were proposed as proxies for
compressibility, they do correlate with it, and correlating with the wrong target is not a reason to
keep them.*

### What the gate costs and what it removes

**Re-measured over the whole pool under the decided caps (August 2026).** The earlier table came
from 300 sampled directions under the provisional ≤10/≤3 pair and is superseded: loosening the
batter cap to 13 admits bench rows that are mostly noughts, so the distribution moved up by about
five points and every threshold now keeps less than it used to. Zero density runs from 10.3% to
68.9% with its **median at 40.0%** and its p10 at 29.2%.

| Threshold | Directions kept | Pool kept | Years of calendar |
|---|---:|---:|---:|
| **below 30% — decided** | **12,218** | **11.0%** | **18.1** |
| below 35% | 29,532 | 26.6% | 43.8 |
| below 40% | 51,723 | 46.7% | 76.7 |

*Computed in SQL over all 110,833 surviving directions rather than sampled, and checked cell for
cell against the board's own definition on twelve directions spanning every decade — the two agree
to the sixth place.*

**Why 30% and not the median.** A median has no properties; it is where the pool happens to sit.
Between 30% and 35% the boards passing through have a median of **three runs**, which is the shape
being excluded in the first place. And with 18.1 years of calendar against a five-month forward
inventory requirement (§33), a generous threshold buys nothing while a strict one costs almost
nothing. That reasoning survives the re-measurement: the threshold now sits near the pool's tenth
percentile rather than a third of the way up it, and 18.1 years is still far more calendar than the
product needs.

⚠️⚠️ **30% is the decision, and for a long time twelve instruments measured at 25% instead.** Until
2026-08-21 the gate was spelled by hand in seventeen `discovery/` scripts — fourteen at `0.25`, three
at `0.30` — so a figure quoted downstream of one of them may describe a **stricter pool than this
section decides**, and a stricter gate is not a smaller sample of the same thing: it removes exactly
the boards that compress least, leaving a livelier population than production draws from. Every script
reads `ZERO_DENSITY_GATE` now, each says at its own `GATE` which gate produced its figures, and
`docs/reviews/todo.md` lists the twelve. **The figures are annotated rather than re-run**, on the same
grounds as the four-family and zero-fill corrections: they were not wrong, they were counting a
different pool.

**It removes the right boards, not merely the correlated ones** (300-direction sample, old caps):

| | Boards | Median runs | Median hits | Shutouts |
|---|---:|---:|---:|---:|
| Excluded at 30% | 220 | **3** | 7 | 18 |
| Excluded at 35% | 130 | **2** | 6 | 18 |
| **Kept below 30%** | 80 | **7** | — | **0** |

Every shutout goes; three-run games go; seven-run games stay. **And family variety survives the
filter** at every chain target, so the gate does not buy quality by flattening character.

### ⚠️ What the gate does to the eras — open

The gate is not era-neutral, and under the decided caps it is dramatically so. Mean zero density
rises with every decade, from **0.367 in the 1910s to 0.475 in the 2020s**, because a modern board
carries more bench rows and spreads the same counting stats over more of them.

| Decade | After caps | Below 30% | Survives | Share of the gated pool |
|---|---:|---:|---:|---:|
| 1910s | 20,698 | 4,365 | 21.1% | 27.2% |
| 1920s | 15,732 | 3,130 | 19.9% | 19.5% |
| 1930s | 14,547 | 2,981 | 20.5% | 18.6% |
| 1940s | 12,244 | 2,051 | 16.8% | 12.8% |
| 1950s | 9,676 | 1,169 | 12.1% | 7.3% |
| 1960s | 10,625 | 795 | 7.5% | 5.0% |
| 1970s | 14,684 | 819 | 5.6% | 5.1% |
| 1980s | 11,934 | 398 | 3.3% | 2.5% |
| 1990s | 7,042 | 192 | 2.7% | 1.2% |
| 2000s | 4,632 | 96 | 2.1% | 0.6% |
| 2010s | 3,057 | 50 | 1.6% | 0.3% |
| 2020s | 754 | 12 | 1.6% | 0.1% |

**Four decades before 1950 make up 78% of what ships.** Everything from 1980 on is 4.7%. The two
filters compound: the ≤2 pitcher cap already selects complete games, which modern baseball barely
produces, and the gate then removes the low-scoring remainder.

### ✅ Decided: a 5% pre-1950 calendar quota

**Pre-1950 boards must not exceed 5% of what the player sees** — roughly eighteen puzzles a year, one
every three weeks. Enough that Ruth turns up occasionally and is an *event*, rather than being the
scenery.

**It is a quota on the calendar, not a filter on the pool.** Nothing is discarded and no direction
becomes ineligible; the pool may stay 78% old. The calendar builder rations which directions get
used.

**What it does is move the binding constraint.** The question stops being "how many directions
survive" and becomes "how many survive *from 1950 onwards*", because with the old half capped at one
puzzle in twenty, everything else has to come from the modern half:

> years of calendar = post-1950 directions ÷ 0.95 ÷ 674 a year

### ✅ And that is why the pitcher cap moved to ≤4

At ≤2 pitchers the modern half is **3,405 directions — 5.3 years of calendar.** The cap was not
expensive at the margin; it was the whole constraint.

| Pitcher cap | Directions | From 1950 on | **Years under the quota** |
|---|---:|---:|---:|
| ≤2 *(the old cap)* | 12,218 | 3,405 | 5.3 |
| ≤3 | 20,507 | 8,200 | 12.8 |
| **≤4 — decided** | **25,270** | **11,884** | **18.6** |
| ≤5 | 26,877 | 13,262 | 20.7 |

*Batters ≤13, gate 30%. Raising the batter cap to 14 or 15 moves these by about 1% — the batter cap
is no longer a lever at all.*

**≤5 is not worth the row.** 2→3 buys 141% more modern calendar, 3→4 buys 45%, 4→5 buys 12%.

**The gate is not spent to buy era.** 35% would give 46.5 years at ≤4 and it is tempting, but
pitchers buy era while the gate sells quality: between 30% and 35% the three-run boards return, which
is the shape the gate exists to remove. **Spend on caps, not on the gate.**

**The screen-cost justification for ≤2 was wrong, and it is retired.** The argument was that a third
pitcher takes visible batting rows from 9 to 8 at 375px. The working-set measurement in §6 had
already established that rows on screen are not the binding constraint — that is exactly what let the
batter cap go from 10 to 13 — and the finding was never applied to pitchers. **Four pitchers is a
fifteen-row board and scrolls exactly as thirteen batters does.**

*One thing the cap was suspected of is not true either: adding pitchers does not make a board
zero-dense. Mean zero density by exact pitcher count runs 0.421 at one, 0.385 at two, 0.380 at three,
0.382 at four, 0.386 at five. The zero-dense board is the complete-game shutout, not the bullpen
game.*

### The hypothesis that the extra rows would be filler — measured, and wrong

It was a real hypothesis, not an objection: a pitching line crosses the offense only through totals,
so four pitching rows might give nearly the same constraints as two, lengthening the board without
improving it. It predicted weakly participating rows and more free steps.

**Its structural half was exactly right.** Constraints per row fall as pitchers are added, and three
extra rows buy less than one extra equation:

| Pitchers | Rows | Equations | Per row | Cycles per row |
|---:|---:|---:|---:|---:|
| 2 | 11.9 | 35.9 | **3.03** | 4.99 |
| 3 | 13.2 | 36.2 | 2.76 | 4.62 |
| **4** | 14.6 | 36.6 | **2.52** | 4.34 |
| 5 | 15.7 | 36.7 | 2.35 | 4.08 |

**And it did not matter.** At a chain target of 14 with the same ~30 cells erased:

| Pitchers | Ceiling | Reached | Trivial steps | Steps touching pitching | Search | Resolution |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 23 | 94% | **0.23** | **23.9%** | 0.82 | 7 |
| 3 | 25 | 92% | 0.20 | 26.3% | 0.71 | 7 |
| **4** | 24 | 93% | **0.20** | **29.1%** | 0.75 | 7 |
| 5 | 27 | 98% | 0.18 | 30.3% | 0.75 | 8 |

Trivial steps **fall** rather than rise, which is the clearest evidence the hypothesis predicted and
got backwards. The ceiling holds. The extra rows participate more than proportionally: with two
pitchers the section is 17% of the rows and 24% of the steps, and it displaces free steps as it
grows.

**The control window is what makes this readable.** Pitcher count and era are nearly the same
variable in this data, so everything was repeated on 1970–2009 where all four counts coexist:
trivial steps 0.22 → 0.18, pitching steps 22.6% → 30.5%. Same result. *Without that window the whole
measurement would have been era wearing a pitcher-count costume.*

*⚠️ 20 directions per cell in the control window. The ceiling oscillates there (22 at four pitchers,
28 at five) and that is noise, not depth.*

### The one real change: cross-team stops being compulsory

At a chain target of 11, the cross-team family is required by **100% of two-pitcher boards and
77–85% of boards with three or more.**

**This is a gain, not a loss.** What disappears is not the family but its compulsoriness, and that
was an artefact of the shape: with two pitching rows the totals are nearly determined by those two
rows, so any pitching cell forces a crossing. A board where the cross is inevitable is not better
than one where it is one of several routes — it is less varied.

It also feeds §31's character axis, which has been collapsing across several measurements. **A family
demanded by 100% of boards distinguishes nothing.** At ≤4 it distinguishes.

*One side effect, small and in the wrong direction: filtering makes hard boards slightly more
uniform in the families they demand — 79% → 96% requiring all four at a chain target of 20. That is
consistent with a collapse already recorded in §31 rather than a new problem.*

**Measured funnel (August 2026), counted by direction:**

| Step | Directions | Survives |
|---|---|---|
| Games with event files (203,908) | 407,816 | — |
| Minus deduced (3,465 games) | 400,886 | 98.3% |
| Roster fits the board (≤13 batters, ≤2 pitchers) | 125,625 | 31.3% |
| Minus discrepancies against official data in board columns | 110,833 | 88.2% |
| Minus the zero-density gate at 30% | **12,218** | 11.0% |

**The pool holds with room to spare.** 12,218 directions is **18.1 years of calendar** against the
674 directions a year the week consumes (§31). The five-month forward inventory §33 requires is not
remotely in question.

*Superseded: this paragraph used to read "even if the remaining quality filters cut 80%, that leaves
~11,000 puzzles". The estimate happened to land close, but it was reasoning from an invented cut
rather than from a measured one.*

**Caveat:** the discrepancy filter only covers 1898–1986. From 1987 on, "no reduction" means "not
measured," not "clean" — though modern rosters barely pass the roster filter anyway, so those years
contribute little.

### What compressibility actually correlates with (measured, August 2026)

Per-direction compressibility — the ceiling for *this* boxscore, not the average board's response to
random erasure — searched over 120 directions, 10 per decade. This is the question that orders
candidates against each other, and it is deliberately not the §31 measurement.

**Boards compress much further than assumed.** Median **58.6%** of the grid removable, p10 50%, p90
68%, range 42–80%. Mean 48 of 82 cells. The 25–35% that used to sit in §6 was invented and is low by
half. **Flat across decades**, 55% to 63% — compressibility is no argument for any era.

**Chains at the ceiling are long:** 16 to 51 steps, concentrated between 30 and 42, and
compressibility and chain length move together (r = +0.74). The worry that a board might compress far
only into short independent chains does not materialise.

**The cheap screens predict compressibility strongly — with the wrong sign:**

| Screen | Correlation with compressibility | What §5 assumed |
|---|---:|---|
| Zero density | **+0.79** | Penalize it |
| Digit range (cells > 3) | **−0.70** | Reward it |
| Scoring innings | −0.65 | Reward variety |
| Line score variety | −0.54 | Reward variety |

**So the prefilter idea works and the polarity is inverted.** Screening *for* compressibility means
selecting zero-heavy, low-scoring games — exactly the boards §5 wanted to exclude on the grounds that
"forced-by-zero cells are not puzzles". Both statements are right at once: a board full of zeros
compresses beautifully because a column summing to nothing forces every blank in it, and that is a
long solution made of trivial steps.

**✅ Consequences, now resolved** *(this list was open; each item below has since been decided or
measured, and the resolutions are recorded at the top of this section and in §31)*:

1. **Compressibility on its own is not a quality metric.** Maximising it selects for boredom. It
   measures how much can be taken away, not whether taking it away leaves anything to think about.
   → **Demoted to a viability constraint.** It no longer ranks anything.
2. **Chain length may be gameable the same way.** It counts dependent steps without weighting how
   hard each one is, so a cascade of zero-forcings scores as a long chain.
   → **Answered twice over.** The zero-density gate removes the boards that would game it, and §31's
   search cost and resolution p90 grade what a step actually costs. Chain length does not stand
   alone, but its companion is not a zero-density side constraint on the generator — it is the pool
   gate plus two orthogonal numbers.
3. **The screens keep their value as screens, with their sign flipped back to §5's intent.**
   → **Dropped instead.** A screen that predicts the wrong target is not saved by reading it
   backwards; the gate attacks the cause directly and the three numbers do the ranking.

**Search cost: 4.6 seconds per direction**, worst case 8.6. Across all 110,833 that is **141 hours** —
a long batch rather than an impossibility, so the expensive measurement can run pool-wide if it is
worth doing. The search is randomised greedy with five restarts, which finds a *maximal* erasure
rather than a *maximum* one, so every figure above is a lower bound.

### What each difficulty level costs the pool (measured, August 2026)

A harder puzzle is also a more expensive one: the solver rejects more candidate erasures, so more
directions are consumed to produce one publishable board.

| Cells erased | Candidate attempts per valid puzzle |
|---:|---:|
| 2 | 1.03 |
| 4 | 1.16 |
| 6 | 1.42 |
| 8 | 1.85 |
| 10 | 2.56 |
| 12 | 3.91 |

**The calendar is not close to constrained.** Illustratively — the mapping from weekday to erasure
count is not decided — a week using each level once with two easy days consumes about 13 directions,
so roughly 674 a year. Against the 12,218 directions that survive the gate that is **18.1 years of
calendar**. Reusing a direction at a different difficulty years apart is available and not needed.

### ✅ The footnote ambiguity is gone — the labels were the bug

> **Superseded, and not by a better model.** Everything below is correct about a board where two rows
> can share a position label. **They no longer can.** Repeated labels are suffixed by order of
> appearance — `LF-1`, `LF-2` — so `SF: LF-2` names one row and the attribution has nothing left to
> resolve. **The erasure constraint this section derived is not needed**, and the domain-bounding
> model it called for is not built.
>
> It was worth removing rather than modelling: measured over the gated ≤13/≤4 pool, **42.9% of
> directions have at least one label collision and 10.0% have one where a colliding row also carries
> a footnote**. `P` is the worst offender by far — 7,232 groups, one of them five rows deep — because
> the pitcher bats and his replacement bats in the same slot. It also gets worse under the new caps:
> the collision rate runs 20% at one pitcher, 35% at two, 49% at three and **67% at four**, and by
> decade from 30% in the 1910s to 82% in the 2020s, which is exactly where the era quota points.
>
> **And the suffix is a better label, not a patch.** `LF-2` tells the player a substitution happened
> at that position — real information the boxscore already contains and the bare label threw away.
> Four characters, inside the seven §7 fixed.
>
> *The batting section's pitchers become `P-1` and `P-2`, **not** `SP`/`RP-n`. The pitching section
> shows the **opposing** team's pitchers, so the same symbol in both sections would name two
> different men on two different teams.*

### The footnote ambiguity is a constraint on erasure, not on the pool

Whether an ambiguous footnote assignment resolves depends on **which cells are blank, not on the
direction**. Measured across 31 ambiguous groups under 20 erasure patterns each: **no direction was
stuck under every pattern, and none was clean under all of them** — on average 29.8% of patterns
left the board unresolvable and the rest were fine.

**So nothing leaves the pool.** The generator must not emit an erasure pattern that leaves the
ambiguity unresolved, which discards patterns and costs a little of the yield above. The exclusion
rule that looked necessary does not exist.

**Era skew, measured:** the pool sits **62% in 1910–1949** and only 30% in 1950–1985 — older than
originally assumed. The 2020s contribute 66 directions against 13,782 from the 1910s. The batter cap
is the cause, not a historical preference.

This is acceptable: the target market is the United States (§20), and 1910–1949 is the most
mythologized era of American baseball.

**Re-measured after the gate, and the guess above was backwards.** The paragraph that stood here
predicted the distribution would shift forward on its own, on the reasoning that zero density selects
against low-scoring games and those cluster in the dead-ball era. It does select against them — and
it removes *more* modern boards than old ones anyway, because a modern board carries more bench rows
and each of them is mostly noughts. After the gate the pool is **78% pre-1950 and 4.7% post-1980**.
The table and the open question are in §5.

---

### Regenerated on the corrected board: the correlation is **+0.890**

Compressibility was demoted from a ranking metric to a viability constraint because it correlates with
zero density — ranking on it selects boredom. That was measured at **+0.79** on a definition that
counted only the grid, while production also erases the per-batter footnote cells.

Re-measured over the board the generator actually erases: **+0.890**, on 120 directions.

**The measurement was wrong and the conclusion was right, and it is now stronger than when it was
made.** A regeneration that confirms a decision is worth as much as one that overturns it; this project
has had both, and knowing which is which is the only reason either is worth running.

The other three components behave as they were asked to — digit range −0.721, line-score variety
−0.522, scoring innings −0.657 against zero density. **Correlating negatively is the evidence that they
measure something other than boredom**, which is what they were kept for.

⚠️ **And a warning that is not about compressibility.** At the compression ceiling, **100% of boards
require all four equation families** — every board identical, no character axis at all. At a chain
target of 5 the same measure opens into five combinations. Nothing distinguishes at the extreme of its
range, and this is the second metric to teach that lesson.

## 6. The board — mobile decides the UX

**Decision: the phone screen defines the design.**

### Why the general rule doesn't apply

**The board cannot change by screen size.** This is a shared daily puzzle: everyone solves the same one. There can't be a reduced phone version and a full desktop version, because it would stop being the same game and the same share grid.

And something harder: **in a deduction puzzle you cannot hide columns.** Every visible number is part of an equation. Hiding a column on mobile doesn't simplify the view — it erases a constraint.

**Resulting rule: whatever fits on a phone IS the puzzle.** Desktop only gets more air, larger type, and side space for the reference sheet. Never the reverse.

### Width budget

Reasonable worst case: 375px minus margins ≈ **343px usable**.

The hard floor isn't typography — it's the **44px minimum touch target**. With a ~70px label column, 273px remain → **six data columns maximum**.

- Batting line (PA, AB, R, H, BB, K) = 6 columns. **Fits, with zero margin.** *(RBI was the sixth here until the column set was decided; see below.)*
- Pitching line (IP, H, R, ER, BB, K) = 6 columns. **Fits, with zero margin.**
- **Consequence: a seventh column cannot be added.** No HBP, no 2B/3B/HR as their own columns.

### The line score doesn't fit — and that resolves an open question

Nine innings + R/H/E = 12 columns. At 44px that's 528px. Impossible.

**Solution: the line score is given complete and never erased. It is the puzzle's anchor.** Being non-editable, it needs no touch target, so it renders small and read-only — and then it fits.

The screen constraint answered the design question of which cells are never erased.

### Height budget — worse than width

iPhone SE: ~667px, minus browser chrome, minus the custom numeric keypad (250–300px). That leaves **~300–350px of visible board** against roughly 16 required rows. **Scrolling is unavoidable.**

**Critical derived rule: header and totals row stay pinned during scroll.** In a deduction puzzle the totals are consulted constantly; if they leave the screen, the player loses the ability to reason. Non-negotiable.

### Other consequences

- **No hover.** Candidates mode needs a different interaction.
- **Row and column highlighting on cell selection goes from decoration to necessity** — it's the only thing showing the player which equations that cell touches.
- "Luis Aparicio" doesn't fit in 70px. **The progressive name reveal must appear outside the label column** (below the row, or as a transient notice).

### v1 board composition — ⚠️ PROVISIONAL, pending measurement

**These numbers are unvalidated estimates and must not be treated as decided.**

- Line score for both teams + R/H/E — **complete, read-only, never erased** *(this part is decided)*
- Offense for **one team only**: rows × PA, AB, R, H, BB, K + totals
- Pitching for the **opposing team**: rows × IP, H, R, ER, BB, K + totals
- **Footnote line: LOB, HBP, SF, SH** — given, read-only, never erased *(decided; see below)*

⚠️⚠️ **~~Superseded: the per-batter footnote cells ARE erasable.~~ This note was itself superseded and
went on standing for months, saying the opposite of the decision.** Corrected 2026-08-21.

~~Measured twice, the second time paired per board on the canonical list: with the line given, the
median board reaches **5** stalls and only half the pool reaches five at all; with the per-batter cells
open it is **16**, and **47 of 47 boards are higher**.~~

**Those figures were counting zeros.** When `HBP`, `SF`, `SH` and `CI` are all zero for a batter the
row identity is `PA = AB + BB`: the erased terms contribute nothing **because they did not happen**.
The solver deduced each zero correctly and recorded a step for it, so the boards scored as harder while
a person never met one — **35 of 36 footnote cells are zero on the reference fixture, and 96% of the
pool's footnote terms are zero.**

**The pool run settled it: coverage with the cells erasable and with them given is the same at every
target, identical on every field in 91% of paired trials.** The cells are **given**, the line above
stands as written, and everything built for the open case was **deleted rather than disabled**.

⚠️ **It was found by a person solving a board and noticing the numbers did not match his experience**,
not by a test — nothing about the instrument was broken. `CLAUDE.md` carries the full account under
*a metric can be correctly computed and still measure something the player never encounters*, and the
code agrees: `erasable()` returns the grid and no footnote cell, per-batter or total.

⚠️⚠️ **The defect worth recording is not the stale figure, it is where it stood.** This document is the
one `CLAUDE.md` says to read before proposing architecture or product changes, and it disagreed with
`CLAUDE.md` about a §6 decision with nothing checking that the two agree. **Two places saying different
things is this project's named failure shape**, and the most expensive place for it is the place the
rules are looked up.

**What is actually decided:** six data columns maximum (derived from the width budget above), the
column sets, one team's offense against the other team's pitching, the line score as anchor, and
the footnote line.

### The footnote line — why the board needs one

**Found while starting the solver (August 2026): the column sets alone cannot express two of the
four equation families.**

- **The global identity is `PA = Outs + R + LOB`.** `Outs` derives from the opposing `IP` and `R` is
  in the line score, but **LOB appears nowhere.** Without it the family is not applicable at all.
- **The row identity is `PA = AB + BB + HBP + SF + SH + CI`** (§3). Those last four cannot be
  columns — the width budget closed that above.

**This is not a defect in the column choice.** A printed boxscore publishes exactly these values as
footnotes rather than columns: LOB, 2B, 3B, HR, SF, SH, HBP, DP. The width budget forbids a seventh
**column** because of the 44px touch target; a footnote line consumes no column width and needs no
touch target, because like the line score it is given and never erased.

It also plays in favour of §2, which says keeping the canonical boxscore format *is* part of
onboarding. A board with footnotes looks more like a real boxscore, not less.

**The alternative was measured and rejected:** restricting the pool to games where HBP, SF and SH
are all zero would cost 57% of surviving directions (85,497 instead of 195,359 at a 15-row budget).
It would have improved the era balance as a side effect — the sacrifice bunt was constant in the
dead-ball era, so requiring zero pushes the pool forward in time — but paying 57% of the pool to
avoid a line of footnotes that real boxscores print anyway is the wrong trade.

### Two corrections found by reading cwbox and checking against the database

**1. A fifth footnote quantity was missing: reaching base on catcher's interference (CI).** It is a plate
appearance that is not an at-bat and not any of the other four categories, and a boxscore missing it
still looks right — which is why it went unnoticed. Measured across every batter row Retrosheet has:

| Forward count of plate appearances | Rows that fail |
|---|---:|
| `AB + BB + HBP + SF + SH + CI` | **0** of 5,325,173 |
| `AB + BB + HBP + SF + SH` | 1,956 |

It affects 1,933 team-games, roughly one in every 200.

**Resolved: those games leave the pool, and the footnote line keeps four values.** A fifth footnote
would cost board space in every puzzle to serve one in two hundred. **The identity still knows about
interference**, because a boxscore containing it is arithmetically correct — it is unusable, not
wrong, and the two rejections must not be confused. Validation says the boxscore is broken;
board-fit says the board cannot show it.

**2. The backward count stops holding in 2020.** `PA = Outs + R + LOB` assumes every runner arrived
by way of a plate appearance. Extra innings now begin with a runner already on second who never
batted, so the identity breaks by exactly the number of extra half-innings:

| Era | Team-games that fail | Of those, in extra innings |
|---|---:|---:|
| 2020 onward | 2,304 | 2,252 |
| Before 2020 | **11** | 1 |

Eleven failures in more than 400,000 team-games before 2020 — those are source errors, and catching
them is what layer 1 is for. **Rejecting the modern extra-inning games is correct, not a false
negative:** the board genuinely cannot express that identity for them, so they are not solvable
puzzles regardless.

### ✅ Decided: the column set is `PA, AB, R, H, BB, K`

Footnotes are attributed **per batter**, labelled by position (§7).

The board's difficulty ceiling is set by how interconnected its constraint graph is, not by its size
(§4). The previous set left the graph a forest, which capped every puzzle at the trivial regime.
Putting **plate appearances** on the board gives each row its own identity; the six-column ceiling is
a real calculation and does not move, so RBI leaves.

**Confirmed by the forge:** independent cycles go from 0 to 16, and drop back to 0 if the row
identity is removed. That test is the tripwire — it guards interconnection, not any particular
number, and fails if a future change flattens the graph again.

**Why RBI is the column to drop.** It is the only batting column with neither a cross-team
counterpart nor a place in the row identity — all ten of its cells have degree one, participating in
its own column sum and in the inequality `RBI ≤ R` and nothing else. The alternative of dropping
strikeouts was measured and scores the same on solvability (57.3% against 57.0% at six erasures),
but it costs one of only four cross-team links, and §3 identifies that cross as the part without
which the puzzle degenerates into row arithmetic.

**Why attribution goes per player.** This reverses the earlier reading above, which was correct only
while plate appearances were not a column: with PA on the board, an attributed footnote closes a row
identity instead of sitting inert. It is worth 14 points of survival at six erasures (57.0% against
43.4%), and it is how a printed boxscore already writes them ("SF: Aparicio").

**Availability was checked before recommending it.** The row identity holds in **all 5,325,173
batter rows** Retrosheet has. Between 87.5% (the 1910s, the pool's heaviest decade) and 94% of rows
close on `PA = AB + BB` alone, needing no footnote term at all; per-team attribution would leave
roughly one row per game without a usable identity, and per-player leaves none.

**Consequences, now carried through:** §3 states the row identity as a board-level constraint, §7
attributes footnotes by position label, §8's tutorial loses RBI from its vocabulary and gains the row
identity, and §31 rests on measurements taken against this board rather than the previous one.

**What is NOT decided:**

### ✅ The column sets and their order — decided on boxscore convention

**Batting: `PA, AB, R, H, HR, RBI, BB, SO`**
**Pitching: `IP, H, R, ER, BB, SO, HR`**

**The reason is convention, not preference.** §2 commits to preserving the canonical format and column
order is part of that format — a fan reads a boxscore by shape before reading it by value.

- **`PA` first, not last.** It is the total of which `AB` is a part, and Baseball Reference places it
  at the start when it shows it at all. A printed boxscore usually omits `PA` entirely; it is here
  because the row identity needs it, so its *position* follows the convention even though its
  presence does not.
- **`HR` after `H`**, grouped with the hit-related columns rather than among the secondaries.
- **`AB, R, H, RBI, BB, SO`** is the canonical core in that exact order.
- **Pitching puts `HR` last**, which is where Baseball Reference puts it.

### ✅ `SO`, not `K`

A printed boxscore labels the column **`SO`**. `K` is scorer's notation — what goes in a scorebook,
not what a newspaper prints. If convention is the argument for the column order, it is the argument
here too, and taking one and not the other would be picking whichever felt better.

**⚠️ The rename is the dangerous part of this change.** A global `K` → `SO` replacement hits unrelated
identifiers; a `sed` in this project has already silently rewritten a dataclass field it was not aimed
at. It must be verified by compiling and running the suite, never by reading the diff.

**What the strip gains.** The formula sheet carries `AB ≥ H` and the row identity today. With `HR`
present it gains **`H ≥ HR`** and **`RBI ≥ HR`**, and both belong on it — the strip is what a solver
actually works from.

**And the width budget has to be re-measured rather than assumed.** `SO` is two characters like `PA`
so nothing should move, but the budget was measured with the old set and two fewer columns, and §6's
own history is a list of provisional numbers that turned out wrong when measured.

*Applied together with the `RBI` and `HR` columns, and **after** the v02 P1 repairs: no pack, no
reference packages and no measurement of what those columns buy until the certification boundary and
the fail-closed gates exist.*

### ✅ The roster caps, decided (browser prototype, August 2026)

> **⚠️ The pitcher half of this was wrong and has been corrected: the cap is ≤4, not ≤2.** The
> screen-cost argument below does not hold — the working-set measurement in this very section retired
> it, and the cap was left at ≤2 out of inertia. Four pitchers is a fifteen-row board and scrolls
> exactly as thirteen batters does. What follows is kept as the reasoning that was actually used at
> the time; the decision and its measurement are in **§5**. The batter cap of ≤13 is unaffected.

**≤13 batters in the offensive team, ≤6 pitchers in the defensive team.** ⚠️ **Corrected from ≤4,
which rested on invalidated data.** The comparison that chose 4 counted the solver deducing footnote
terms worth zero as stalls, and a pitching row carries no footnote terms at all — so pitcher-heavy
boards had fewer zeros inflating their scores and the comparison was biased against the very thing it
was judging. Re-measured after the correction: coverage at 8 stalls 22% → 33%, the pitching section's
share of stalls 34% → 45%, 41% more directions in the pool with the 1990s and 2000s reachable, global
identity required on 70% of boards against 55%, cross-team on 80% against 88%.

⚠️ **The two stall figures have no recorded run and are marked rather than removed.** Neither
`22% → 33%` nor `34% → 45%` appears in any output file — the commit that introduced them added no
results — so they cannot be reproduced, which by this project's own rule makes them not evidence. They
stay because they are probably right and deleting a number quietly is how a record stops being one.
**The pool figure is sourced** (`discovery/pitcher-cap/cap_gate_sweep_results.txt`) and so are both
reasons the ≤4 cap was wrong, so the decision does not rest on the unsourced pair. See
`docs/reviews/todo.md`. The median ceiling is
unchanged at 5. **And the screen-cost argument was wrong twice**: it was retired for the batter cap by
the working-set finding and never re-derived for pitchers. Nothing in §6 is
provisional any more.

**Rows on screen turned out not to be the binding constraint.** With the active section's totals
pinned they never scroll away, so the question is not how many rows are visible but whether a step's
working set can be held together. Measured: 70% of steps at a chain target of ten touch rows within
a five-row window, and the ones that span the whole lineup are column sums combining a **median of
two non-zero numbers** — scanning ten rows to find two is a scan, not something carried in the head.

**The pitcher cap is the one that costs screen, and the batter cap is the one that costs pool** —
the opposite of the provisional pair, which had them the other way round.

*⚠️ Superseded. The first half of that sentence is the error: it prices a pitcher in screen rows,
and the working-set finding two paragraphs above had already established that rows on screen are not
the binding constraint. It also turned out to be false about pool — under the era quota the pitcher
cap is by far the more expensive of the two (§5).*

| Caps | Directions | Against the old pair |
|---|---:|---:|
| ≤10 batters, ≤3 pitchers *(the old provisional pair)* | 65,522 | — |
| ≤12, ≤2 | 103,304 | +58% |
| ≤13, ≤2 *(decided here, superseded in §5)* | 125,625 | +92% |
| ≤14, ≤2 | 148,815 | +127% |

So the old caps were **dominated**: loosening batters and tightening pitchers buys more pool *and*
more visible rows at once. At 320px, three pitchers left two batting rows visible where two pitchers
left four.

**Era distribution at the decided caps**, against the pair it replaces:

| Decade | ≤10/≤3 | ≤13/≤2 |
|---|---:|---:|
| 1910 | 13,995 | 21,040 |
| 1940 | 10,257 | 15,484 |
| 1970 | 5,059 | **14,684** |
| 1980 | 2,874 | **11,934** |
| 2000 | 900 | 4,632 |
| 2020 | 66 | 754 |

The 1970s and 1980s roughly triple, which is where the recognisability deficit for the progressive
reveal sat. The 1910–1949 skew softens from 68% to around 57%. **⚠️ Accepted rather than solved:**
the modern game is still thin — 754 directions in the 2020s against 21,040 in the 1910s — because a
game with seven relievers cannot fit a board of any size this project will build.

*⚠️ Pre-cap-change. Everything in this subsection is measured at ≤2 pitchers and is kept as the
record of that decision. The ≤4 numbers, and the era quota that made the pitcher cap the binding
constraint, are in §5.*

### Other measured values, no longer estimates

| Element | Value | Where it came from |
|---|---|---|
| Label column | **66px, seven characters fixed** | 76% of surnames render whole against 55% at six; one pixel of cell width |
| Data column | 52px at 375px, 42px at 320px | Six columns after the label |
| Custom keypad | **107px** | Measured. §6 had assumed 250–300, which was a *system* keyboard |
| Line score | 46px, complete, 9pt | Twelve columns and both teams fit without a touch target |
| Pinned totals | 34px | |
| Rows visible at once | **9 at 375px, 7 at 320px** | |
| % of cells erased | *superseded* | The erasure algorithm targets a chain length; cell count is whatever reaching it costs (§21, §31) |

### How these get resolved

**Two measurements were required before fixing these numbers. One is done.**

1. **Height budget, measured not estimated.** Prototype the board in a browser with real data at
   375px and count how many rows actually fit above the keypad. That gives the true row ceiling,
   which sets the roster caps. **⚠️ Still outstanding, and now the only thing blocking them.**

2. ~~Compressibility and technique distribution across the pool.~~ **Done (August 2026).** The board
   does produce hard puzzles: chains run past twenty steps, the search cost of finding the next move
   spans 0.25 to 0.92, and all four equation families appear. The measurements are in §5 and §31.

*The fear this pair was meant to settle — that the board might be too small, most of the sample
resolving by plain propagation alone — did not materialise. What the measurements did overturn was
the quality criterion (§5), not the board size.*

**If pool size ever needs loosening, the lever is the batter cap, not the pitcher cap.** Measured:
only 18.5% of directions pass ≤10 batters, while 66.9% pass ≤3 pitchers. The batter cap is what
constrains the pool, and it is also what produces the 1910–1949 era skew.

### On the relationship between board size and difficulty

Fewer rows does **not** mean an easier puzzle. Difficulty comes from how many equations intersect and
how long a chain of dependent steps runs, not from row count. A 26-row board solvable entirely by
column sums is trivial and long; a 12-row board that needs the global identity and the pitching cross
is hard and short.

**Measured, and it went further than that.** Harder boards ask for *less* arithmetic per step, not
more: resolution p90 falls from 8 additions to 5 as difficulty rises, while the cost of finding the
next move climbs from 0.50 to 0.92. Difficulty on this board is searching, not calculating. Nobody
designed that — it emerged from the format (§31).

The effect actually runs the other way: **more rows means more equations, and more equations makes
uniqueness easier to reach** — more redundant paths to deduce each cell. That is what produces easy
puzzles.

This is an argument for measuring rather than assuming, in either direction.

### Why the board is a subset at all

A full MLB boxscore is ~26 rows, unplayable on a phone. This is the minimum shape preserving all
three constraint families, including the cross-team constraint that §3 identifies as essential.

### Design process

- **Prototype in the browser with real data, not in Figma.** Tables lie in mockups: real numbers have different widths.
- Test on small physical devices. iPhone SE is the worst case.
- **Accessibility from the start:** correct table semantics so a screen reader announces "row Aparicio, column hits". Retrofitting this means rebuilding the board.
- Consider outside design help at this point. It's where a purchased hour returns the most.

---


### ✅ Decided: short row labels, `CF-3`, and no slot column

The label keeps the number, because the number is what identifies a row and a slot cannot — several
rows share a slot, which is what broke the slot-column proposal. And once the label keeps the number
it can be short: **progressive reveal was dropped, so no label carries a surname**, and the 66px
column was sized for "Aparicio".

| Form | Label | Data | Per cell | Clears the 44px target |
|---|---|---|---|---|
| `CF3` | 32px | 311px | 51.8px | yes |
| **`CF-3`** | **42px** | **301px** | **50.2px** | **yes — chosen** |
| today, seven characters | 66px | 277px | 46.2px | yes |

**`CF-3` over `CF3`.** The 1.6px the compact form saves buys nothing, and the hyphen stops `P2` reading
as a position — there is no second pitcher's position, but the string looks like one.

**The suffix never exceeds one digit.** The largest slot group anywhere in the pool under the caps is
**five rows**, so four characters is the worst real case rather than an assumption.

**This gains width rather than spending it:** 50.2px per data cell against 46.2px today. No new column,
no `rowspan`, and no scroll problem — the merged cell that vanished with its starter was a risk that
now does not exist. The four-variant sample is cancelled: two of its variants were moot once the slot
could not identify a row, and the other two are unnecessary once the width passes without a column.

### ✅ Settled: the batting rows as a boxscore shows them

- **Position column stays.** A boxscore without positions stops reading as a boxscore, and the three
  defects it caused are closed by the entry-position rule rather than by removing it.
- **Slot column stays**, carrying the *full* reference in every cell — `9` where a slot holds one row,
  `9a`/`9b`/`9c` where it is shared. The letter is the signal that a substitution happened rather than
  noise on every row, and the cell says literally what the footnote says, so the search is recognition
  and there are not two representations of one thing to drift apart.
- **Footnotes reference slot plus letter**, never `2a` when there is no `2b`.
- **Labels are bare positions**, no suffix. The reference left the label, so the suffix has no work.
- **Indentation plus a rule between slots** as the visual cue.
- **Home runs stay out** — measured: no new independent cycles in any configuration.

⚠️ **One function produces both the cell and the footnote reference.** Two places applying one
condition is the defect this project has spent the day closing; a test asserts the two strings come
from the same call for the same row.

**Grouping is carried by order, indentation and a rule between slots — form B, chosen by eye.** The
difference between indentation alone and indentation with a rule shows on a board where a substitute is
*buried mid-lineup* rather than trailing at the end: with four pinch hitters grouped at the bottom the
indent is enough, and with a substitute sitting between two unrelated rows it is easy to miss. The rule
helps exactly where the indent alone fails, and it costs vertical pixels rather than horizontal ones.

⚠️ **And it exposed a clash that has no cheap fix: the suffix partitions by position and the indent
partitions by slot, and they are different partitions shown at once with nothing telling them apart.**
A reader meets `3B-2` unindented — correct, a different man in a different slot who replaced nobody —
beside an indented `CF` with no suffix. The suffix has to be global or footnotes stop being unique, so
numbering within a slot is not available: two `3B` in different slots would collide again. A printed
boxscore never meets this because names disambiguate; the suffix inherits that job here and then
collides with the indent.

**Three exits, none decided.**

1. **Footnotes reference a row ordinal** — `HBP: row 7`. This does more than decouple: it removes the
   suffix's reason to exist, so the label goes back to being purely descriptive, `P2`-reads-as-a-position
   disappears, and the label drops to about 32px, returning **51.8px per data cell**. It costs the player
   counting rows, on a board of up to thirteen, exactly where the load is already highest.
2. **The ordinal inside the label** — `1 CF`, `2 3B`, `2 CF`. Identifies without counting and groups at
   the same time, at the price of a label carrying two things.
3. **Keep the suffix and accept the clash**, which is today's board plus a rule.

⚠️ Whichever is chosen, **it interacts with the starter-who-moved defect**: the `3B-2` that prompted this
is a man who started in centre, so correcting his label turns him into a second `CF` and moves the clash
rather than removing it. That is evidence the collision is structural.

Grouping is otherwise carried by order and indentation — `CF`, `CF-2`, `CF-3` consecutive, the
substitutes indented — which is the printed convention and what the row-order fix has to do anyway.

⚠️ **What is still open is not the label.** Whether a footnote left unassigned across a group resolves
by deduction is a separate question, measured per group size and per term count; if large groups with
several terms go non-unique, the answer is that the generator must not leave one open there, which
discards erasures rather than directions.

⚠️ **The width arithmetic below assumes the label can shrink to 50px because the suffix is gone, and
the suffix cannot go.** A slot disambiguates positions repeated across *different* slots — 42.1% of
repeated labels — and does nothing for rows sharing one: three `P` rows in slot 9 leave `HBP: 9`
pointing at three candidates. With the suffix still on the label there is no 16px to spend and the
column does not fit.

**What is actually being decided is not a label.** The two-row case was measured weeks ago and modelled
as domain bounding rather than notation: the term is 1 in one row and 0 in the others, and one row's
own identity stops admitting it, so it falls to the other by elimination. 99.96% of ambiguous groups
are exactly two rows. **The question is whether a person can do at three what the solver does at two**
— and if they can, that is deduction rather than ambiguity, possibly one of the better moments on the
board. Measurement pending; nothing below is decided until it lands.

**This is a change to §6 rather than a rendering improvement**, which is why it is written here as a
proposal with its arithmetic rather than applied as a side effect of correcting row labels.

**What it is.** A read-only column carrying the batting-order slot, `rowspan`-merged across the rows
that share one. Measured across the whole pool: the slot is **always 1 to 9**, never wider than one
character, and every direction has **exactly nine distinct slots** — 407,815 of 407,816, the single
exception being a source error the check would rightly reject.

**The width, which is what makes it possible.** With a slot column the label stops carrying a suffix,
so §7's seven characters can shrink and the budget closes. The slot needs no touch target — it is
read-only like the line score — so its 16px does not compete with the 44px minimum.

| Reparto of the 343px inside the margins | Per data cell | Fits the 44px target |
|---|---|---|
| 66 label + 16 slot + 261 data | 43.5px | **no**, by half a pixel |
| 50 label + 16 slot + 277 data | 46.2px | yes |

**What it fixes, in order.**

1. **`SF: P` stops being ambiguous, and without a suffix.** A slot is unique by definition; a position
   is not — measured, **42.1% of repeated position labels span more than one lineup slot**, so `P-2`
   routinely names a man who never replaced anybody.
2. **The relationship §7 says the player loses comes back.** Rows sharing a slot are the ones whose
   plate appearances sum against that slot, and the grouping makes that visible instead of implied.
3. **The three pitchers stop lying.** Three `P` rows at slots 7, 10 and 11 read as three slot-holders
   rather than as a substitution chain that never happened.

⚠️ **The risk is specific to the merged form and is not cosmetic.** If the starter's row scrolls out of
view, the merged cell goes with it and the substitute is left with no visible slot — the information
disappearing exactly when the player is working on that row, and a `SF: 7` is no use with slot 7
off-screen. **A slot holding three rows is the case that splits**; two rarely does. The sample must
carry one and be scrolled.

**Four things the sample must let the operator judge**, none of them settled here: merged against
repeated-and-dimmed; and `SF: 7` against `SF: 7 P`. Slot-only is better if a slot is unique by
definition — redundancy in a label invites the two halves to contradict each other, which is the
pattern this project has spent the week fighting — but both get rendered rather than argued.

**Nothing on the board changes until the sample is judged.** When it is, the label rule, the footnote
attribution and the row grouping are one change, with both hand-solve packs rebuilt afterwards.

## 7. Game identity — progressive reveal

**Decision: progressive reveal.**

- Rows start labeled with **positions** (C, 1B, 2B, SS, LF...), not names. It's authentic baseball grammar and identifies nothing.
- **On completing and validating a row, that player's name appears.**
- Teams, date, and context are revealed at the end.

**Rationale:** with a baseball-fan audience, names are not decoration — they're the emotional payload of a boxscore. A boxscore without names is a spreadsheet. Progressive reveal turns the tension into mechanics: the mystery holds at the start, which is when a Google search would still help, and names arrive as reward. A name you earned weighs more than one handed to you.

**Note on cheating:** the risk of players looking up the game is overrated. The solution already lives in the client JSON and that's accepted. A daily puzzle is only cheated against oneself. Wordle had the answer one click away and nothing happened.

### Footnotes are attributed by position, never by name

`HBP: SS`, `SF: 2B`. A printed boxscore writes `HBP: Aparicio`, and that would hand the player a name
before they had earned the row — the one thing progressive reveal exists to prevent. The position
label is authentic baseball grammar, gives the player everything the row identity needs, and leaks
nothing. Once a row is completed and its name appears, the footnote may be rewritten with the name.

**✅ Every label names exactly one row: repeats are suffixed by order of appearance.** `LF-1` and
`LF-2`, `P-1` and `P-2` — a label used once stays bare, so the suffix appears only where a position
was played by two men.

*What that replaces.* A shared label was previously accepted as a constraint to be modelled: labels
are unique in **99.89%** of nine-batter team-games but only **24.28%** of ten-batter ones, and on the
gated ≤13/≤4 pool **42.9%** of directions carry a collision with **10.0%** carrying one that a
footnote actually lands on. `P` is the worst — the pitcher bats and his replacement bats in the same
slot, up to five rows deep. Suffixing removes the ambiguity at the source, so the domain-bounding
model §3 called for and the erasure constraint §5 recorded are both unnecessary.

**And it is a better label, not a workaround.** `LF-2` tells the player a substitution happened at
that position — information the boxscore already contains and the bare label discarded. Four
characters, inside the seven fixed below. §8's tutorial shows one board with a substitution so the
convention is met once deliberately.

*The pitching section uses `SP` and `RP-1`, `RP-2` — the starter and the relievers in order of
appearance, which bounds the IP column before any equation is touched: a starter is where the long
innings are and a third reliever is where they are not. **Never a bare `P` there**, because the
batting section has `P` rows of its own, and never `SP` in the batting section either — the pitching
rows belong to the **opposing** team, so the same symbol would name two different men.*

### ✅ Innings pitched: outs inside, thirds on the keypad

**`4.1` is not a decimal.** It is four innings and one out, so the value is held as an **integer count
of outs** everywhere — loader, solver, format, renderer — and converted only where it is printed.
Audited: nothing in the pipeline turns it into a float. That matters beyond tidiness, because the
identity linking the pitching section to the global count is `Outs = 3 x IP`, and a decimal
representation makes that multiplication a source of boards that fail validation for no visible
reason.

**The editable domain is thirds.** A cell may hold `.0`, `.1` or `.2` and never `.3` — three outs is
a whole inning. That is information rather than a limitation: a board that accepted `4.7` would be a
board whose pitching column stops adding to the defensive innings.

**Twelve keys, always present, and no decimal point.** A decimal-point key would let `.3` through
`.9` be typed and then refused; two explicit keys make the domain visible and a wrong value
unenterable. They stay on screen for every cell rather than appearing on IP cells only, because a
keypad that changes shape under the player's finger is the reflow problem that argued against the
system keyboard in the first place.

**And it costs nothing vertically.** Measured in the prototype:

| Keypad layout | Height | Key size | Rows of board visible |
|---|---:|---:|---:|
| 5 columns, 12 keys | 158px | 71 x 48 | 11 |
| **6 columns, 12 keys — decided** | **107px** | **59 x 48** | **12** |
| *(the same at 320px)* | 107px | 50 x 48 | 12 |

The five-column layout needs a third row and takes 51px of board. Six keeps two rows at the height
§6's budget was measured with, and the keys stay above the 44px touch minimum at both widths.

### ✅ Section headers name the team, and the line score is left neutral

Headers read **`AWAY BATTING`** and **`HOME PITCHING`** — team first, then role, the way a boxscore
reads. They are always opposites by the board's construction, and stating it is what makes the two
sections read as **two teams** rather than two halves of one. That matters because the cross-team
family is unusable until the player sees that the hits allowed below are the hits in the *other*
team's line score row (§3).

**Neither line score row is tinted.** An earlier version shaded the batting team's row as a reading
aid. It is wrong on the merits: that row is not the batting section's property — its runs and hits
are what the batting section must reconcile *and* what the pitching section conceded, which makes it
precisely the shared object the cross-team family passes through. **Marking it as belonging to one
section works against the family the headers exist to support.**

**⚠️ Live footnotes must be visually prominent.** Nine rows in ten have every footnote term at zero,
so a player will learn to stop looking — and the row where one finally appears is precisely the row
whose arithmetic fails if they miss it.

### The revealed name goes in the row label, abbreviated to a fixed width

**Seven characters, always** — never full names truncated only where they overflow. A fixed width is
something the player can learn; a conditional one is not, and they cannot tell what the column will
show. It costs no pixels, puts the identity where the row's identity belongs, and lets the names
accumulate as the free progress bar §7 was counting on.

**Disambiguation by first initial is mandatory, and independent of the width.** Measured across
291,481 boards: **6.64% carry two batters with the genuinely identical full surname** — Waner leads
the list, then Smith, Jones, Davis, Robinson, Collins. Abbreviating to seven characters adds only
0.08 points on top of that, so **this is not a truncation artefact and would occur with no
abbreviation at all.** A first initial resolves all but 0.35%.

**Those 0.35% stay in the pool.** Two players sharing a surname and an initial are still told apart
by position, which the row showed before it was revealed — and the label identifies a *row*, not a
player. Paying pool for a cosmetic ambiguity buys nothing.

**The end-of-game reveal shows complete names**, unabbreviated and undisambiguated. Abbreviation is
a constraint of the label column and belongs nowhere else; the closing card has room, and that is
the moment the name is the point.

### Consequences

- **Forces row-level validation.** Constrains the open error-handling question.
- **The name appearing _is_ feedback.** The game stops being silent. This is welcome: it softens the experience exactly where the "fan without puzzle patience" risk lives.
- **Free visual progress.** Nine names appearing one by one is a progress bar nobody had to design.
- **⚠️ The final reveal loses its surprise.** With nine names visible the player already knows the game. The closing must deliver something else: date, teams, ballpark, and **why that game mattered**.
- Position labels depend on era. The pool skews to 1950–1985, much of it pre-DH. The pitcher batting ninth is a strong era tell.
- The share grid cannot contain names.
- Reserve width in the label column: "SS" and "Luis Aparicio" don't occupy the same space.

---

## 8. Tutorial

**Not a modal.** The first games *are* the tutorial. There are **five equation families** on this
board (§3), not six techniques, so there are five steps plus one on the bounding technique:

1. **P1 — Column sums.** One missing cell with the total given. Impossible to fail.
2. **P2 — The row identity:** `PA = AB + BB + HBP + SF + SH + CI`. Also where the footnote line is
   introduced, because it is the term a player will not think to look for.
3. **P3 — The batting↔pitching cross.** **The game's "aha" moment.** Stage it deliberately.
4. **P4 — Bounding.** Inequalities and non-negativity to eliminate candidates rather than compute
   them. Not an equation family but the second technique, and the only one that reasons over ranges.
5. **P5 — The global identity** `PA = Outs + R + LOB`. The most powerful and least intuitive, and
   measured as the rarest: it appears in a few percent of solution paths even at the hardest level
   (§31), so a player who has not been taught it will meet it cold and rarely.
6. **P6 — The batting order.** The lineup bats in a cycle and never skips, so the team's plate
   appearances are dealt round the nine places: every place gets the same number, and the places at
   the front of the order get one more when the total does not divide evenly.

### ⚠⚠ P6 needs the clearest explanation of the six, and for a reason the others do not share

**The first five are baseball bookkeeping.** A fan recognises them without ever having written one
down: totals rule, a batter's row balances, the two halves cross, runners are accounted for. Even the
global identity, the least intuitive of them, is a statement about things printed on the card.

**The batting order is logic over a sequence.** It is true because the order is *cyclic*, and
deducing the single-step distribution from that is reasoning about cycles rather than knowing
baseball. **Nothing on the board shows it.** A player can stare at a boxscore for an hour and never
recover it, because it is not a fact the boxscore records — it is a fact about how the boxscore came
to be.

⚠️ **That does not disqualify it, and the precedent is P5.** `PA = Outs + R + LOB` is not visible on
a boxscore either, and it went in without this argument. The tutorial is mandatory on first play and
taught there like the other five, and — since the tutorial became skippable — restated on §3b's
reference sheet, which is what a player who skipped has. What follows is not an exemption but a
weighting: **this step carries more of the tutorial's job than any other**, because it is the only one
a player cannot arrive at by looking.

**P2 and P3 are different techniques and both need a step.** The row identity works down a single
row; the cross works across the board between the two halves. Neither substitutes for the other.

### Scope: the mechanics, not baseball

- **Does explain:** that totals rule, that a batter's row balances, that opposing pitching crosses with the offense, that PA = Outs + R + LOB, and that the lineup bats in a cycle
- **Does not explain:** what AB means, what a sacrifice fly is, why there are nine innings

**The tutorial teaches identities, not statistics.** A hardcore fan knows what LOB is and has never once thought that PA = Outs + R + LOB.

**One tutorial board must carry a substitution**, so the player meets `LF-1` / `LF-2` once
deliberately rather than being puzzled by it mid-solve. The convention is self-explaining in context
— the suffix appears only where a position was played by two men — but 43% of boards carry one (§5),
so it is not an edge case worth discovering by accident. Nothing needs explaining beyond the label
itself; the identities are unchanged.

### ⚠️ Mandatory on first play — SUPERSEDED 2026-08-20

**The tutorial is skippable.** The design and the reasoning are in `docs/serve-flow.md` §1b; the rule as
it stood is kept below rather than deleted, because it was right about the risk and wrong about the
remedy.

> **Mandatory on first play.** The tutorial is not skippable on the first game. It's short, and it's the
> only guarantee that nobody reaches the real puzzle without understanding the mechanics. Permanent
> access to replay it, alongside the reference sheet.

**What changed is the last clause of that paragraph.** *The only guarantee* was true when it was
written: the tutorial was the sole place the five relations were ever stated. The reference sheet now
carries all five and the bounds, on a button, during play — so a player who skips has the rules a tap
away, and compulsion is buying something that is already owned.

**And what it cost was aimed at the wrong person.** A required tutorial is spent on a visitor who has
not yet decided whether they are interested; the ones who do not want it leave before reaching a board,
which is the outcome this rule existed to prevent, arriving one screen earlier.

⚠️ **Skippable is not thinner.** Five steps, one per relation family, a made-up four-batter board, one
hole per step, the batting order last because it is the only relation invisible in a real board. Nothing
about the reversal is a reason to teach less.

**Permanent access to replay it** — unchanged, and more important now than when it was a footnote to a
compulsory flow.

### Policy for players who don't know baseball

**Not served, but not shut out either.**

No baseball tutorial, no stats glossary, no simplified mode — all of that would dilute the canonical board that §2 decided to preserve.

But the reference sheet serves them anyway and position labels are learnable. Someone curious can come in and stay. **They're simply not designed for, and failing to capture them isn't measured as failure.**

**Permanent collapsible reference sheet** with the five identity families. Sudoku doesn't need one because there's a single rule; here there are five and the casual player forgets them between sessions. Not optional.

---

## 9. Platform

**Website (PWA), not a native app.**

- The growth mechanism of a daily puzzle is the **shared link**. An app inserts an app-store page into that flow and loses half the people.
- Maintenance cost: two stores and two review cycles are a new front for a solo operator.
- The content demands nothing native: it's a grid of numbers.
- Iterating the generator on the web means deploying; in a store it means waiting for review.
- **PWA** recovers what matters: installable, offline, daily notification.

**Critical mobile care:** custom on-screen numeric keypad, never the system keyboard.

**Accepted consequences:**

- Cache only the day's puzzle, not the week, to avoid leaking future puzzles.
- The solution lives in the client and will be visible in devtools. Accepted — the streak is against yourself.

### Native app for the paid tier — rejected

**Question evaluated:** a mobile app for paying users and web only for free users?

**No.** Four reasons:

1. **It puts an app store at the only point where money enters.** Apple takes a cut of in-app subscriptions; added to the merchant of record, a considerable slice is lost. Rules about linking to external payment change every year.
2. **It inverts the commitment ladder.** The path would become: free game on web → pay → *now install an app and start over*. That's asking for friction right after someone paid — the worst possible moment.
3. **It doubles the product surface.** Two codebases, two deployment cycles. For a solo operator, the worst return on the list.
4. **It breaks seams C4, C5, and C6**, which exist so the same engine serves every context.

**The underlying intuition was right** — paying users should feel they get something better. But that's delivered through the product (no ads, archive, stats, streak insurance), not a different platform. The PWA already provides install, offline, and daily notification.

The only thing a native app would add is store visibility as a discovery channel — and that would serve to acquire **free** users, the opposite of what was proposed.

If there's ever an app, it should be for everyone and only after the site works.

---

## 10. Monetization

### Principle

The base design must support **all** paths without rebuilding the site. Not implementing them all in v1, but closing off none.

### Data license

Retrosheet explicitly permits commercial use, with one requirement: the copyright notice must appear prominently. It goes in the footer.

### Reference model: crossword and sudoku sites

**Decision: copy the NYT Games playbook and equivalents.** Three pillars:

1. **One free daily game, forever.** Habit and acquisition engine. Never touched.
2. **The archive behind the wall.** The number-one conversion driver — at the NYT what you buy is the full crossword and the 10,000+ puzzle archive, not "more puzzles per day."
3. **No ads for paying users.** The free tier is monetized with advertising; removing it is part of what the subscription sells.

**Consequence:** ads return to the plan, and logically so — they're the complement to the wall, not the primary model. This reactivates seam C9.

### ⚠️⚠️ Ads: the design stays ready, and nothing is built — 2026-08-22

**This is not a decision to run ads.** The requirement is that **if that decision is ever taken, it is not
a rebuild.** C9 and C10 already reserve the slots and the two-phase boot; this is about making the
reservation real rather than a sentence in a document.

**The decision itself waits until there is a problem to solve** — poor conversion against real traffic,
which does not exist yet.

#### Where a slot belongs

| slot | why there |
|---|---|
| **Between the solved board and the reveal** | the player has just finished, there is already a transition, and nothing is interrupted. It is what daily games that monetise this way do |
| **The landing, beneath the button** | seen before playing, competing with nothing |
| **The finished board on return** | a screen with nothing on it today |

#### ⚠️⚠️ No slot during play, and the exclusion is deliberate

**The board is 375px and every pixel was argued for** (§6). A banner there destroys the height budget and
interrupts somebody concentrating.

**Recorded as a decision so nobody adds one later as the obvious spot** — and it is the obvious spot: it
is where the attention is, which is exactly why it is worth more to an advertiser and costs more here.

#### What *ready* has to mean concretely

A slot that is **empty today and can be filled without moving anything else**.

- **Empty slots render nothing at all** — no placeholder, no border, no gap.
- **The two-phase boot exists and works with zero ad code**, so adding a network dependency later does not
  change the boot sequence. C10 already requires this.
- ⚠️ **Nothing in the play path may depend on an ad loading.** §23 requires the daily to play with the
  backend down; **an ad network that fails, is slow, or is blocked must not be able to stop the game.**
  That is a property of *where the slots sit*, and it is the second reason none goes on the board.

#### ⚠️⚠️ *Renders nothing* and *does not shift the layout* contradict each other, and resolving it is what picks the locations

**Stated plainly, the two requirements cannot both hold.** A slot with zero height that later fills with a
250px block **must** move whatever is beneath it. Reserving the 250px instead means shipping a 250px hole
for a decision that may never be taken.

**The resolution is not a compromise between them — it is a constraint on placement:**

> **A slot goes where nothing the player might be about to touch sits below it, or it is filled before
> first paint.**

That is the real property. It is not *the layout must never move*; it is **nothing the player is reaching
for may move under their finger** — which is what a layout-shift rule is actually protecting, and it is
satisfiable with slots that render nothing.

**Check the three against it:**

- **Between the solved board and the reveal** — a transition of its own, nothing below. ✔
- **The finished board on return** — nothing below. ✔
- **The landing, beneath the button** — ⚠️ **the Retrosheet footer is below it.** The footer moving costs
  nothing: it carries no control and no one is reaching for it. **But that has to be checked rather than
  assumed**, and if the landing ever gains a control below the button, the slot moves or the rule breaks.

⚠️ **A reservation that fails this test is decorative**, and a decorative reservation is worse than none:
it reads as done in a document while the rebuild is still waiting.

#### Two things to record while the reasoning is fresh

**1. Ads and subscription cannibalise each other.** If the free tier with ads is tolerable, fewer people
pay. **The resolution is already in the two-tier design above** — removing ads is part of what the
subscription sells — and it is written here, where the ad decision would be taken, rather than somewhere
it would have to be rediscovered.

**2. ⚠️ A generic ad network will clash with everything built here.** A boxscore is a sober object; the
Fenway green, the monospace and the restraint are the product's character. **Network ads are not going to
respect any of it.**

**The mitigation is niche advertisers** — baseball retailers, memorabilia, card shops. ⚠️ **But that is
direct sales, not a network: a different business with a different amount of work.** Worth stating now
because *turn on a network* and *sell to baseball advertisers* get conflated when the decision is being
made in a hurry, and they share almost nothing but the word.

#### ✔ One of the three already exists, and it is the pattern for the other two

**The landing slot is not hypothetical.** `serve/ui/phone/landing.js` appends `.landing-later` between the
button and the footer — put there for the archive, the streak and the subscription, on the reasoning that
*the shape is present before the feature is*. **An ad slot is that element or one beside it.**

**Measured 2026-08-22 at 375px:** height 0, no margin, no padding, no border, no children, `display:
none`. **It renders nothing at all**, which is the requirement, and it is worth reading how:

```css
.landing-later:empty { display: none; }
```

⚠️ **`:empty` is what makes the reservation self-maintaining**, and that is the part to copy. The slot
disappears while nothing is in it and appears the moment something is, with no flag to set and nothing to
remember — so a slot cannot be left showing an empty box, and filling one cannot be forgotten halfway.
**A reservation that needs somebody to toggle it is a reservation that will one day be toggled wrong.**

#### Build nothing

**Empty slots, no ad code, no network, no configuration.** This document says where they go and what they
must not break; the code reserves the space when the slots are built. **One of the three is built, and it
was built for something else** — which is the seams working as intended rather than a head start on ads.

### Chosen model: recurring subscription

**Recurring subscription**, not one-time purchase.

Rationale (from the operator): a one-time purchase is a perpetual obligation to maintain the site. A subscription bounds the commitment — on shutdown, renewals stop, the unused portion is refunded, and nothing is owed to anyone.

**Consequence:** what's sold isn't "the archive" (a static asset that gets exhausted), it's a **membership** — unlimited play, catalog, stats, packs. The product does deliver continuously: a new puzzle every day.

Structure:

- Monthly and annual, annual discounted
- **No lifetime tier** — it reintroduces the problem being avoided
- Cancel anytime; on cancellation the free daily puzzle continues
- Terms: access while the service operates

### Two tiers from day 0

**Firm operator decision.** The site launches with both levels:

- **Free:** one daily puzzle
- **Paid:** archive, stats, packs, no ads, unlimited play

**Rationale:** converting a free site into a paid one burns trust, and the base attracted while free self-selected for free. Launching with the price in place means everyone who arrives knows the rules from day one.

**Warning on "all you can eat" as the sole argument:** the value of a daily game is in the ritual and in everyone solving the same puzzle today, not in quantity. People don't want more puzzles, they want *the* puzzle. The paid tier needs: archive, personal stats, **streak insurance** (one grace day a month — the strongest hook that exists in daily games), themed packs. Unlimited works well as part of the bundle, poorly as the sole argument.

**Rare advantage to exploit:** the NYT archive took thirty years to exist. Here it's possible to **launch with an archive** — hundreds or thousands of verified puzzles from day one, because Retrosheet already has them and the generator produces them in batch. The asset that in this category is a longevity prize is available before opening.

### ⚠️⚠️ Payments: Stripe — decided 2026-08-22, reversing the merchant of record

**Operator's decision. Stripe, and the operator is the seller.**

**What changed is the audience, not the arithmetic below.** The merchant-of-record case was overwhelmingly
a *tax* case: VAT and sales tax across 200+ jurisdictions, collected and remitted by somebody else. That is
worth two points of revenue when the tax surface is global. **The audience for a boxscore puzzle is US
baseball fans**, and against a US-only tax surface the obligation is state sales tax, which **Stripe Tax
computes automatically**. Two points of revenue for a problem that mostly is not there.

⚠️ **The old reasoning was not wrong; it was priced against a market this product does not have.** Same
shape as the SQLite decision in `serve-flow.md` §9 — not a stated condition firing, but a premise quietly
ceasing to hold.

**⚠️ What this hands back to the operator, stated rather than discovered later.** Everything in the list
below that the merchant of record was doing is now either Stripe's, the operator's, or nobody's:

- **Kept, and Stripe does it well:** processing, subscriptions and proration, failed-payment recovery,
  hosted checkout, invoices and receipts, 3D Secure. **PCI stays out of scope** — with hosted checkout or
  tokenised Elements the card never touches our servers.
- **Now the operator's:** being the legal seller, **chargeback liability**, and **billing support**. That
  last one was called *decisive* below and the point still stands — most tickets in a subscription
  business are billing. It is now a solo-support cost rather than a delegated one.
- **EU VAT: closed 2026-08-22, not conditional.** Stripe Tax handles US sales tax and **no European is
  subscribing to a baseball puzzle.** This was written as an open condition with EU revenue share as the
  trigger; the operator's answer is that the trigger will not fire, and treating a market that does not
  exist as a live edge is analysis for its own sake.

⚠️ **And a related sentence in §16 stays true and is not part of this change:** *with users in Spain and
the EU, GDPR applies.* GDPR follows the users, not the seller of record, so it was never something the
merchant of record removed. **Do not "tidy" it away as a leftover of Paddle.**

⚠️⚠️ **The audience premise in the old section was wrong too, and that is the stronger finding.** The
superseded preference justified itself by *selling to the Dominican Republic, Venezuela, and Spain*. That
list does not describe this market:

- **Spain is not a baseball country**, and there is no reason to expect Spanish players. It was the only
  member of the set that generated the EU VAT obligation the merchant of record was being paid to absorb —
  **the tax argument's whole weight rested on the one entry with no reason to be there.**
- **The Dominican Republic and Venezuela are baseball countries and are still not the target market.** §2
  and §13 both say the target market is the United States, and §13 is explicit that Latin America is *not*
  a target market and that treating it as one would need a design review rather than an extension. Nothing
  about that changed.

**So it was not one premise that stopped holding; it was two, and the second was never true.** The tax
premise expired with the market it was priced for. The audience premise was built on a list that does not
describe the audience.

### ⚠️ One processor, and PayPal is not rejected — it is undecided pending evidence

**Do not add a second processor.** The integration is not the cost. The cost is:

- **Two sources of truth about who has paid.** Every state change — renewal, cancellation, failed charge —
  arrives by two paths in two formats, and reconciling them is permanent work.
- **Two webhooks to verify, each with its own signature.** §35 calls the unverified webhook the
  highest-value attack in this system: a forged notification grants a free subscription. Doubling that
  surface buys a second way to get it wrong.

**And it would not solve what it is being considered for.** PayPal has serious restrictions in Venezuela,
and in the Dominican Republic somebody with PayPal generally has a card.

⚠️ **Record this as undecided, not as rejected**, because those are different states and only one of them
can be reopened cheaply. **Launch with Stripe. A second processor waits for evidence of a blocked
customer.** What that evidence looks like: someone who wants to pay, tries, and cannot — arriving as a
support message, a failed-checkout pattern in Stripe, or a country whose cards are declining. Adding a
processor before there is one subscriber is complexity bought against a customer who may never arrive.

---

**Everything below this line is the superseded reasoning, kept.**

**Paddle or Lemon Squeezy** rather than raw Stripe. What it covers beyond payment — they become the **legal seller of record**, the customer buys from them:

- **Global tax:** they collect and remit sales tax and VAT across 200+ jurisdictions. Avoids VAT registration in Europe and tracking state thresholds in the US.
- Payment processing (cards, PayPal, Apple/Google Pay, local methods)
- Subscription management: recurrence, plan changes, proration, cancellation
- **Failed payment recovery** — retries and expired-card updates. Involuntary churn is a large share of total churn
- **Fraud and chargebacks** — they assume legal liability for transactions
- Hosted checkout with per-country currency and translation
- Automatic invoices and receipts
- **Customer billing support** — they handle payment inquiries directly
- PCI compliance and 3D Secure

**That second-to-last point is decisive:** most tickets in a subscription business are billing, not product. Delegating them is what makes solo support manageable.

**Cost:** Paddle and Lemon Squeezy both charge 5% + $0.50 per transaction, against ~2.9% + 30¢ for raw Stripe. Two points more for everything above.

**Tentative preference: Paddle.** ⚠️ *Superseded — see the heading above. This line is kept because it
names the reason (international rate, and Lemon Squeezy's acquisition), and a preference recorded with
its reason is evidence; deleting it would leave the question looking unexamined the next time somebody
asks it.* Lemon Squeezy adds 1.5% on international payments while Paddle includes everything in its rate — relevant when selling to the Dominican Republic, Venezuela, and Spain. Also, Lemon Squeezy was acquired by Stripe in 2024 and its direction now depends on that strategy. *Verify pricing and features when deciding.*

### Operational consequences of charging from day 0

- There are paying customers on day 1 with an untested generator. An unsolvable puzzle in week 2 is no longer a bug — it's a refund.
- **Pre-validation of arithmetic and the pre-generated puzzle bank stop being maintenance and become launch requirements.**
- Pre-launch checklist: merchant of record configured, terms, privacy policy, refund policy.
- Consider a **founder price** locked for the first subscribers: it compensates the risk they take and builds a committed core.

### Other paths (priority order)

1. **Sponsorship / B2B** — embeddable widget for newsletters and media. Doesn't depend on volume.
2. **Themed packs** — the database is a real competitive advantage
3. **PDF / print books** — set aside for now at the operator's request

---

## 11. Accounts and abuse

- **Social login only:** Google + Apple + email magic link. **No Facebook** (declining usage, more review process, marginal coverage).
- No own passwords: zero storage, zero recovery flows, zero breach liability.

### Sharing policy

**Personal and household use**, stated explicitly in the terms.

Rationale: it's what will happen anyway; writing it down aligns the rule with reality, removes guilt from paying customers, and leaves room to treat extreme cases as abuse without having criminalized a family.

**Also, sharing with a family member produces customers.** Stats and streaks are personal; shared, they mean nothing. Whoever gets hooked ends up wanting their own account.

### Mechanism

- 8–10 devices per account, **silent eviction of the oldest**
- No accusations, no blocks, no manual review, no fraud detection, no geographic analysis
- Self-enforcing: a family never notices; an account shared among thirty people becomes useless on its own
- Identifier: random UUID at first login, **not browser fingerprinting**
- **In v1:** only record the device. The limit stays off by configuration.

**Guiding principle:** wrongly blocking someone who pays costs more than the fraud avoided.

---

## 12. Architectural seams

These must exist in v1 even if no paid feature is used.

| # | Seam | Enables |
|---|------|---------|
| C1 | Three sealed layers: generator → data → client. Zero puzzle logic in the client | Books, embed |
| C2 | Puzzle = pure data with immutable ID and versioned schema | Everything else |
| C3 | Rich metadata on every puzzle even if unused (year, teams, flags, difficulty, techniques) | Themed packs |
| C4 | The engine doesn't know what day it is; a *loader* decides | Unlimited mode, archive |
| C5 | Engine with no chrome or branding, themeable via CSS variables | B2B licensing |
| C6 | Per-puzzle routes from day one: `/p/<id>` canonical, `/today` redirect | Archive, sharing |
| C7 | **Store events, not state** (puzzle_id, duration, hints, techniques, errors) | Stats, calibration, migration to accounts |
| C8 | `canAccess(puzzle, user)` — in v1 always returns true | Any gating |
| C9 | Reserved, empty layout slots — three of them, **none during play** (§10) | Ads without wrecking mobile |
| C10 | Two-phase boot that can wait for consent | Privacy |
| C11 | Zero strings in code, including generated text and metadata | Optional Spanish (§13) |

**C7 is the irreversible one.** If v1 only stores "streak: 7", that history is never recoverable.

**Note on C8 and subscription:** a signed token with expiry validates offline, which makes it copyable. Device control requires a short token (24h) refreshed against an endpoint. That refresh call is where devices are counted. Still nearly static — a single endpoint.

---

## 13. Language

**Interface: English. Spanish is a nice-to-have, not a must-have.**

The target market is the United States. Spanish adds convenience for Latin American baseball fans —
who can play because they read a boxscore the same way — but it is not required for launch and can
slip without affecting the product.

⚠️ **The payment decision rests on this same premise, and the two must not drift** (§10, 2026-08-22).
Dropping the merchant of record for Stripe was justified by *the audience is US baseball fans*, and the
superseded preference it replaced had argued the opposite from a list — Dominican Republic, Venezuela,
Spain — that does not describe this market. **The Caribbean-audience reasoning that would have raised
Spanish to a must-have is the same reasoning that was found not to hold there.** This section is
unchanged by that: it already said the United States, and it already said Latin America is not a target
market. What is new is that **a second decision now depends on it**, so a future argument for a Caribbean
market has to move both or neither.

**What stays mandatory regardless: seam C11 — zero user-facing strings in code.** All copy goes
through the string catalog from day one, including generated reveal text and metadata. That costs
almost nothing to do now and is expensive to retrofit, so the option stays open even if Spanish never
ships.

**Project convention:** all documents, code, and source comments in **English**. Discussion happens
in Spanish; artifacts are in English.

---

## 14. Competitive landscape

**Nobody is doing exactly this.** The adjacent space is populated:

| Product | What it is | Relationship |
|---------|-----------|--------------|
| **Immaculate Grid** (Sports Reference) | Daily baseball trivia | **The real incumbent.** Owns the fan's daily habit. Knowledge, not deduction. |
| **Daily Walkoff** | Daily MLB trivia, 30 puzzles | Same genre as Immaculate Grid |
| **Baseball Sudoku** (ESPN, books, baseballsudoku.com) | Sudoku with positions instead of numbers | Cosmetic skin, zero baseball logic. **Name collision risk.** |
| **TripleLog Baseball Sudoku** | Sudoku where cells are at-bat outcomes and you must score the correct runs per inning | Closest conceptually. Integrates real baseball logic, but over constructed puzzles, not real games. |

**The gap:** none uses a **real historical boxscore** as substrate, nor arithmetic deduction as the mechanic. That space is open.

**The threat:** not that someone copies the idea, but that Immaculate Grid already owns the mental space of "the daily baseball game."

---

## 15. Risks of success

Scenario: 9,000 paying users within 3 months.

1. **Support volume.** The most underestimated cost. Thousands of paying customers generate hundreds of tickets a month for one person. Mitigation: self-serve cancellation, aggressive FAQ, zero manual account fixes.
2. **Daily delivery stops being a promise and becomes a contract.** A day without a puzzle is an incident. Mitigation: pre-generated batch months ahead, automated publishing.
3. **A defective puzzle hits everyone the same day.** Requires an emergency switch and rollback.
4. **Obligation and burnout.** With people paying, walking away isn't an option. Hence the subscription and the orderly-shutdown clause.
5. **Tax and administration.** Delegated to the merchant of record.

### Price — pending

The figures used in conversation ($1.99/month, $9.99/year) **were examples, not proposals.** Real pricing is a later discussion.

It depends on three still-open items: how many puzzles the archive has at launch, whether the free tier carries ads, and exactly what's in the membership.

**The only thing fixed now, because it's structural and doesn't change with the number:** annual should equal **~10 months** of monthly. Enough to push annual without giving away half the revenue.

**Category reference:** NYT Games costs $39.99/year.

---

## 16. Protecting the idea

**Game mechanics are not protectable.** Rules and ideas are explicitly outside copyright. Only concrete expression is protected: code, visual design, name.

**Worth doing:**

- Register the name as a trademark
- **Don't publish the generator algorithm.** It's a trade secret and the genuinely hard piece to replicate — above all the human-solvability guarantee.

**The real defenses:**

1. **Habit and streak.** Enormously sticky. Nobody abandons a 200-day streak to move to a clone.
2. **The generator with its derivability guarantee.** Hard to replicate.
3. **The Retrosheet pipeline and database.** Years of accumulated work.
4. **Being first with that audience.**

**Precedent:** Wordle was cloned within days and still won. First-mover plus habit beat the copies.

**Registered caveat:** with AI, the implementation barrier is low — which also means secrecy protects less than it seems, since whoever sees the site in February can also copy it quickly. What AI does not shorten: historical data quality and validation, design judgment, and above all the audience.

---

## 17. Legal structure

**LLC formed before public launch**, not before design.

Since the site launches charging from day 0, the trigger coincides with launch. The moments that require it:

- Before charging the first person
- Before registering the trademark (registering personally means an assignment later)
- Before opening the separate bank account

**An LLC only protects if real separation is maintained.** Collecting into a personal account and paying expenses with a personal card makes the shield decorative — that's what allows piercing the veil of a single-member LLC.

**Notes:**

- BOI reporting: LLCs formed in any US state are exempt from the federal requirement. The law wasn't repealed, only suspended by rule — verify current status when forming.
- A single-member LLC is a pass-through by default; it changes nothing tax-wise at the start. S-corp election only enters the conversation with substantial net profit, and with an accountant.
- *None of this is legal or tax advice. Confirm with a professional.*

---

## 18. Daily operational load

**The game is almost no work. The subscribers are.**

**What is NOT a load:** publishing the puzzle. With months pre-generated and verified, it's an automated process. Zero minutes a day. A huge advantage over a crossword site, which depends on human constructors and editors — here the content comes from a database.

**What IS a load: support**, and nothing is close to second. With thousands of subscribers, daily emails arrive: login won't work, I was charged twice, I want a refund, I lost my streak, I changed phones, this puzzle is broken. Mostly account and billing problems, not the game. **Realistic range: 30 minutes to 2 hours daily, with spikes when something breaks.**

**By frequency:**

- **Daily:** verify the puzzle shipped and nothing is down
- **Weekly:** metrics, community responses
- **Monthly:** reconcile payments, review the pool, bookkeeping
- **Annual:** LLC report, taxes, renewals

**The psychological load nobody mentions:** it's a *daily* game. There is no weekend or vacation without a puzzle. Even automated, the operator is the only one who can fix it. People who run daily games solo describe that as the most exhausting part — not the hours, but never being able to disconnect.

**How it's reduced — designed now, not later:**

- **Self-serve** cancellation and account management. Every action requiring manual intervention multiplies by thousands
- Merchant of record, absorbing most billing tickets
- Aggressive FAQ and **a single contact channel**, not five
- **Automatic, no-questions refunds** below a certain amount: arguing costs more than refunding
- Publishing months ahead, so a failure gives days of margin rather than hours
- Automated alerts instead of manual checking

With that discipline: **1–2 hours daily in steady state.** Without it, it becomes a full-time job.

---

## 19. Timeline and launch

**Chosen window: Spring Training 2027.**

Advantage: 4–6 weeks of shakedown **before** Opening Day, which is the real attention peak. Launch in February with few people watching, fix what breaks, and arrive at late March working. Launching directly on Opening Day would mean maximum traffic against an untested product.

**Working backward:**

| Period | Focus |
|--------|-------|
| Aug–Sep 2026 | Close design; start building audience |
| Oct 2026 | Playoffs — second attention peak of the year |
| Oct–Dec 2026 | Construction |
| Jan 2027 | Closed beta (friends and family, controlled environment) |
| Feb 2027 | Spring Training launch |
| Late March 2027 | Opening Day — the moment of truth |

**If something falls out of scope, let it be the billing infrastructure before the game.**

---

## 20. Audience strategy

**Decision: no free puzzles posted on social media before launch.** The project ships complete or not at all.

Operator's rationale: fear that someone takes the idea and implements it faster, and not wanting to burn the single first impression available in a small niche.

**What is done starting now:** build audience **without showing the game.** The baseball history content the operator already writes leaks nothing about the product and attracts baseball fans. Mailing list and consistent presence through February.

**Launch channels (by weight):**

1. **The product is the main channel** — the share grid. Every solved game is a potential post aimed at people who already read boxscores. **This makes grid design a growth decision, not an aesthetic one.**
2. **Baseball newsletters** — probably the best external channel, and it overlaps with the B2B embeddable-widget path
3. **Communities:** r/baseball, r/Sabermetrics, SABR, Discord. SABR fits the operator's profile particularly well
4. **The archive is SEO** — every archived puzzle is an indexable page about a real game. Thousands of long-tail pages no other puzzle game has
5. **The baseball calendar** — Opening Day, playoffs, World Series

**Market note:** the target market is the United States. Latin American baseball fans can use the
product because they read a boxscore the same way — hence optional Spanish — but Latin America
is **not a target market**. Treating it as one would require detailed design review, not an
extension.

**Warnings:**

- A thousand users who try is easy. **A thousand who return on day 30 is the real problem**, and that's solved by the game, not by distribution.
- Charging from day 0 dampens sharing. **The free tier must be a complete, satisfying game on its own**, or the growth channel is choked off.
- For the closed beta to be useful: don't ask whether they like it. **Measure whether they return on day seven without a reminder.** Recruit baseball people with no personal attachment (SABR) before family.

---

## 21. Batch generation and calendar

### Generation

**A single offline run producing thousands of puzzles.** The generator runs offline against Retrosheet and publishes the batch as static files.

**Its input is a target chain length, not a number of cells to erase.** Chain length grades effort
more cleanly than cell count does, so erasure is the means and the chain is the objective; how many
cells come out is whatever reaching the target costs (§31, §36). Admission to the pool happens before
that, on the roster caps and the 30% zero-density gate (§5).

**Double idempotence — two distinct things that must not be conflated:**

1. **Puzzle idempotence** — the same Retrosheet game always produces the same puzzle with the same ID. Regenerating the batch creates no duplicates.
2. **Calendar idempotence** — the date → puzzle assignment is fixed and never recomputed. Running the process again reassigns nothing.

**The puzzle ID derives from the game, never from the date.** If it derived from the date, the same puzzle in the archive and in the daily calendar would be two distinct entities, breaking the no-repetition promise.

The process that extends the calendar must be able to run twice with no effect, because sooner or later it will be run twice by mistake.

**Interaction with the difficulty curve (§31):** calendar assignment isn't only "don't repeat." The generator must **classify each puzzle by level and shape the week** — easy Monday, hard Saturday. The calendar is built once respecting that pattern, then it's immutable.

### The calendar, not local consumption

**Rejected:** each device "burning" games from a local list.

Rationale: it breaks the daily game. Each user would end up on a different puzzle, losing what sustains the model — that **everyone solves the same puzzle today**. Without that there's no conversation, no result comparison, and the share grid means nothing. Also, someone playing on phone and laptop would be on different puzzles.

**Solution, still requiring no backend:** which puzzle corresponds to each date is fixed in advance. The client computes today's date and requests that static file from the CDN. Zero front-back interaction to play, same puzzle for everyone.

No-repetition is resolved at batch generation, not at runtime.

**Purely local consumption does apply to the archive** — there's no reason for a shared puzzle, each person plays what they want, and no backend is involved at all.

### Calendar rule: extend, never rewrite

Once someone has played a date's puzzle, that date cannot change — streaks, shared results, and stats hang from it. **The past calendar is history, not configuration.**

Case of a defective puzzle detected late:

- **If the date hasn't arrived:** it can be replaced. That stretch is future and nothing hangs from it.
- **If the date has passed:** don't touch it. Mark it void and exclude it from streaks and stats, but leave the assignment.

The calendar "freeze" date is a real parameter: what's published through today is immutable; what comes after is editable.

---

## 22. Correctness guarantee — design principle

**An incorrect puzzle must be virtually impossible. This is where all the effort goes.**

With customers paying from day 0, a broken puzzle isn't a bug: it's a refund and a lost streak that can't be given back.

### "Incorrect" is not one thing

| Failure type | Description |
|---|---|
| **Bad data** | The historical boxscore doesn't balance at source |
| **No solution** | Constraints contradict each other |
| **Multiple solutions** | Cells were erased that weren't forced |
| **Unique but not derivable** | **The worst.** Looks correct and the player is trapped guessing |

The last one demands the real work, and is covered by the no-backtracking rule (§4).

### Independent layers, each able to reject on its own

1. Validate the boxscore against all identities before admitting it to the pool
2. Prove solution uniqueness
3. Require the human-technique solver to finish without guessing
4. **End-to-end verification:** take the published puzzle, solve it from scratch, and compare against the original boxscore. If it doesn't match exactly, discard.

**Critical requirement: each layer is implemented separately and shares no code with the generator.** If the verifier reuses the generator's functions, it inherits its bugs and the validation is theater.

### Operating rules

- **Nothing publishes without passing all layers.**
- **A puzzle that fails is discarded silently — never "fixed."** With thousands of candidates, throwing away 30% costs nothing.
- **Sign every published puzzle** and verify the signature before serving, to catch post-generation corruption.
- **Have an escape hatch:** a pre-verified backup puzzle and a switch to substitute the day's. "Virtually impossible" is not "impossible," and with 30,000 people playing you find out fast.

### The worked case that justifies the redundancy

Layer 4 re-solves a board the earlier layers already cleared, and it is fair to ask what that buys.
This is what:

> Take a valid, published puzzle and **swap two batters' hits values**. Every column still sums
> correctly. Every row identity still closes, because hits appear in no row identity. The cross-team
> link still holds, `AB ≥ H` still holds for both rows, the board still has **exactly one**
> completion, and that completion is still reachable without a guess.
>
> **Layers 1, 2 and 3 pass it entirely.** The puzzle is internally perfect and is about a different
> game.

Only a comparison against the original boxscore sees it, which is what layer 4 is. Every other layer
asks whether the board is consistent; layer 4 is the only one that asks whether it is *true*. That
distinction is the argument for keeping a layer whose work looks duplicated.

### ⚠️ What layer 3 actually certifies, which is not what this section claims

**§22 believes it has a human-derivability barrier. What it has is an interval propagator running to
a fixed point over forty-odd simultaneous relations.** A narrowing found in the pitching column is
instantly available to a row identity twelve rows up. Nobody solves like that. **A board can pass
layer 3 and still be underivable by a person**, and nothing in the four layers would say so.

*This was found by writing the verifier against this document rather than against the generator: §4
names the techniques as propagation and then bounding, and never says how strong the bounding step
may be. The ambiguity is the finding.*

**A search for a counterexample found none** — roughly 24,000 random erasures across 400 generated
boards produced no board that was unique and yet underivable. **That is not reassurance.** It says
that *at this bounding strength* uniqueness appears to imply derivability, which is a claim about the
solver rather than about the player.

#### ⚠️ On the corrected pool, 3b stops being an expensive decision

Re-measured after the loader was fixed: **78%** of chain-13 boards certify under the weak solver
against 71% before, and **91% at chain 11** — which is where the week now tops out (§31). So inside
the publishable range the uncertifiable share is **9%, not 29%**.

**That changes what the choice costs.** Gating on 3b and discarding every uncertified board would
leave 91% of thirty-plus years of calendar, which is far more than will ever be used. The expensive
option became cheap, so the argument against gating is no longer pool.

~~**The decision stays open until the fifty come back**~~ — **closed on 2026-08-21, and it closed
itself.** 3b does not become a gate: with §5's gate actually applying and the batting order adopted as
the fifth family, the measurement finds every publishable board certifying under the weak solver.
**Not "we chose not to gate" — there is nothing left for it to reject**, so the population that made
the question meaningful no longer exists.

⚠️ One measurement disagrees — 3 of the 6 published reference packages do not certify, non-monotonically
— and is recorded in `docs/reviews/todo.md` rather than dropped. Those six are chosen one per stall
count rather than drawn from the pool, which is the likely reconciliation.

**The afternoon keeps its value and gains focus.** It was going to decide 3b; it is now entirely the
answer to the two questions that matter more — **are these boards interesting, and is the difficulty
curve right** — plus the one thing only a person can supply: whether the stall scale corresponds to
felt difficulty at all.
Those are answered by the *tedious* and *boring* ticks on the survey sheet, not by *had to guess*.

#### Layer 3b: a lower bound on humanness, measured

So the verifier also carries a deliberately weak solver — one relation in view at a time, never
carrying a narrowed range from one relation to the next. Layer 3 is an upper bound on what a person
can do; this is a lower one, and the gap between them is uncertainty that was previously invisible.

**Measured over 298 puzzles from the real generator:**

| Chain target | Published boards | Also derivable one relation at a time |
|---:|---:|---:|
| 5 | 60 | **100%** |
| 7 | 60 | 98% |
| 9 | 60 | 93% |
| 11 | 60 | 80% |
| **13 — Saturday** | 58 | **71%** |

**The gap is real and it concentrates where the week peaks.** At Saturday's target, **29% of
published boards cannot be certified derivable under a conservative reading.** That does not mean
they are unsolvable — a person sits somewhere between the two solvers, so the truth is between 71%
and 100% — but it does mean the guarantee §22 believes it has is weaker at the hard end than
anywhere else.

**Not yet decided: whether 3b becomes a gate.** The argument for is that the discard cost is 29% at
the worst target, and this section already declares throwing away 30% to cost nothing. The argument
against is that the weak solver is a caricature of a person in the other direction, and gating on it
would discard boards a player would have solved comfortably.

### ⚠️ Known residual risk: the verifier is not independently authored

§22's critical requirement is that the verifier share no code with the generator. **It does not** —
separate package, identities restated from §3, its own cell naming, and the one thing both genuinely
need (the file format) in a third package owned by neither.

**But the same author wrote both.** No code is shared and the generator's implementation was not
consulted while the verifier was written, which removes inherited bugs but not shared blind spots. A
misreading of §3 would be made twice and agree with itself. **This is a residual risk, not a solved
problem**, and it is recorded here rather than only in a docstring so that it is visible when the
guarantee is being relied on.

### The layer no automated test replaces — now load-bearing

**Solve a sample by hand. Fifty puzzles before launch, and this cannot be skipped.**

It was written as a sanity check for what no test detects: correct but boring, or brutally hard. It
has been promoted, because the two findings above leave it carrying more weight than that:

- **It is the only real verification of human derivability that exists.** Layer 3 certifies a machine
  can do it; layer 3b says 29% of Saturday boards are not certifiable under a weak reading; a person
  is between them and nothing automated resolves where.
- **It is the only check the same-author risk does not touch.** A blind spot shared between generator
  and verifier survives every automated layer and does not survive somebody solving the board.

Record for each: whether it was solvable, where it stalled, and whether it was boring. A board that
was solved only by guessing is the failure §22 calls the worst, and it will not announce itself.

---

## 23. Infrastructure

Scenario: 9,000 registered accounts, 30,000 daily unique players, 99.9% availability target.

### The load is smaller than the numbers suggest

Daily-game traffic concentrates at the puzzle rollover and in the morning. Even assuming a third within the same hour, that's a few requests per second with peaks of dozens in the peak minute.

**And above all it's static traffic.** The day's puzzle is the same file for everyone: kilobytes from a CDN edge with near-total cache hit rate.

The dynamic part is small — token refresh, device registration, event sync. With 9,000 accounts that's tens of thousands of operations a day.

### Three nines: 43 minutes of downtime a month

**Availability isn't bought with bigger servers — it's achieved by having fewer pieces.** Chaining CDN + backend + database as mandatory dependencies multiplies their availabilities and lands *below* the target even if each is good.

**Way out: define "up" as the puzzle being playable.**

And it's possible because it's already designed that way: the puzzle is static, validation is client-side, and C7 stores events locally. **If the backend goes down, you can't log in or sync stats, but the day's game still works.** It's the only realistic way to sustain three nines solo.

### From where the real outages come

- **Your own deployments.** Most outages are self-inflicted. Don't deploy near the puzzle rollover; have instant rollback.
- **The daily rollover** — the only moment something must fire on time. Publish ahead; don't generate at midnight.
- **Third parties** — a Google OAuth or Stripe outage is inherited.
- **Expired certificates and domains.** Silly, and among the most common causes of total outage.

**The system must degrade on its own, not wait for human reaction.** If something breaks at 3am, the month's budget is spent.

*Note: §33 chose Docker + nginx on a VPS rather than serverless. That satisfies the underlying argument — fewer chained pieces — but it does mean there is a server to patch. Revisit this section at level 200.*

---

## 24. Brand and domain

**Primary domain: `boxscorepuzzle.com`**

**Name language: English, no concessions.** The audience will come overwhelmingly from the US, and baseball vocabulary is already English throughout the Caribbean. Any Spanish applies to the **interface**, not the name.

### Advantages and limitation of the chosen name

**In favor:** describes the product unambiguously, helps in search, no legal risk, works equally for the Caribbean audience.

**⚠️ Limitation:** it's descriptive, which makes it **hard to register as a trademark on its own** — purely descriptive marks aren't protected because nobody can appropriate the words naming a category.

Not a problem today, but for §34: trademark protection will likely come from a **distinctive logo or a secondary name**, not the two words alone. And for that same reason it doesn't block the umbrella of §30 — you can have the descriptive domain and a separate mark when needed.

### Registered domains ✅

- **`boxscorepuzzle.com`** — canonical
- `boxscorepuzzles.com` — defensive, redirects
- `boxscorepuzzle.app` — for an eventual wrapped PWA, redirects

**Canonical policy:** one indexable version, `boxscorepuzzle.com`. The other two redirect. If search engines see the same content at three addresses, ranking is diluted — which is precisely the advantage of having chosen a descriptive name.

**Operations:** auto-renewal and privacy protection enabled on all three ✅. An expired domain is among the most common causes of total outage (§23).

### Rejected for unavailability

Scorekeeper · Left on Base · Ghost Game · The Daily Box · Crack the Box · Boxly · Scorely

**Lesson:** short combinations of common English words have been taken for years, mostly by resellers. The `-ly` suffix is swept clean from the startup era. That path is exhausted.

### Criteria used

1. Don't say "sudoku" — there are registered marks associated with the term, baseballsudoku.com exists, and the game is kakuro anyway. The analogy belongs in the **copy**, not the name.
2. Don't box into a single game (§30)
3. Pronounceable and spellable on hearing
4. One or two words

### Pending, not urgent

- [ ] Consider a **short separate brand name**, registrable, providing the asset the descriptive name cannot. `boxscorepuzzle.com` would keep working for search.

---

## 25. Seasonality

**The puzzle ships all 365 days, without exception.** Interrupting the daily would be suicidal: the streak sustains the habit, and a pause breaks it for everyone at once.

**But the puzzle doesn't stop and attention does.** Baseball has a winter; from November to February attention to the sport collapses regardless. The question isn't whether to publish, but what to expect of those months.

**Annual is the defense.** Someone who subscribed in April keeps paying in December whether they play or not. A strong argument for pushing annual beyond the discount: **winter is exactly when monthly subscriptions get cancelled.**

**Winter is the construction window.** November to February: nobody's watching, traffic is at the floor, and things can be changed without exposure. It matches the project's real cycle.

**Two zero-cost uses:**

- **Baseball winter moments** — Hall of Fame, awards, free-agent signings. And for the Caribbean audience, **winter leagues are in full season while MLB sleeps.** Hooks for content, not for the product.
- **Seasonality as a metric** — the retention curve will drop in winter for reasons unrelated to the game. Know it in advance so the calendar isn't mistaken for a product problem.

---

## 26. Time, competition, and the social layer

**Principle: don't split the experience by tier, split the analysis.** Everyone plays the same; paying users see more about how they played.

### Rejected: competitive mode only for subscribers

- **A leaderboard needs population.** With typical 2–5% conversion, a subscriber-only board is thin precisely where it needs density. It would mean charging for the worse version of the feature.
- It's backwards: the daily puzzle is the same for everyone, so that's exactly where comparison makes sense with everybody in.
- **Timing changes how you play, not only what you see at the end.** If the clock runs, you rush; if not, you savor. It can't be one contemplative experience for some and competitive for others.

### Decision: measure for everyone, compare as a paid feature

- **Timer for everyone, silently.** C7 already stores duration, so it's free. Your own time is shown discreetly, not as the headline.
- **The paid feature isn't "a subscriber leaderboard," it's personal stats with a percentile against the whole user base:** times over time, highest technique level, relative position among everyone who played today.

**The key property: that feature improves as the free tier grows**, rather than degrading. That's the correct incentive.

### On a public global leaderboard — two warnings

- **The solution lives in the client and so does the timer.** A public ranking is trivially manipulable, and verifying server-side fights the static architecture (§23) and the three nines. High cost for the most fragile feature.
- In daily games these rankings are always won by the same few speedrunners, which demotivates everyone else. **Wordle has none and grew more than anyone.**

### Social competition: among friends, not global

Small private groups. No incentive to cheat because it's social, it fits the share grid, and it works as a paid feature without needing mass population.

*Note: private friend groups are the one feature that genuinely requires a real backend — comparing between people can't be done with static files.*

---

## 27. Failure and retention

**Decision: you can never lose.**

### Why

In a unique-solution, pure-deduction puzzle, losing is artificial — it would have to be invented with an error limit or a clock. And that punishes exactly the profile identified as fragile in §2: the baseball fan who isn't a puzzle person. It would put a barrier in front of the very user who needs protecting.

### Design

- The puzzle stays **open all day**
- It saves itself
- At midnight it **closes for streak purposes, but doesn't disappear** — it can be finished later from the archive
- Failure isn't "you lost," it's "you missed the day"

Generates urgency without punishment.

### The return hook

The usual mechanisms — streak, notification, rising difficulty — work and must exist. But they're the same ones everyone has, and none is a reason to choose this game.

**Note:** the reveal was originally framed as the differentiating hook ("no sudoku can tell you that you just reconstructed a game from August 1974"). With §29 deciding it will be an automatic template card with no manual writing, **the weight of retention returns to habit and puzzle quality.** The disproportionate effort goes to the generator and the difficulty curve.

### Warning about streaks

They're effective, but they have a known effect: **when someone breaks a long streak, many never play again.** Guilt expels.

That's why streak insurance isn't only a paid feature — it's **protection against your own mechanism**. There must also be **a free grace day**, even if only one per month.

#### ⚠️⚠️ Yesterday's puzzle is playable and does **not** count for the streak — decided 2026-08-22

`docs/calendar.md` puts **two** puzzles on the public path, today's and yesterday's. **Read that rule
and this one together; neither makes sense alone.**

**Playable and counting are not the same thing**, and naming the distinction is the whole decision.
Yesterday's board can be opened and solved. **Solving it does not keep a streak alive.**

**Two forgiveness mechanisms stacked would make the streak nearly unbreakable, and an unbreakable streak
means nothing.** The grace day above is the one this section argues for and it is deliberate — one a
month, free. *"Yesterday is always available and it counts"* on top of it removes the last way to lose,
which empties the thing the grace day exists to protect.

⚠️ **And the second day exists for a different purpose entirely.** It is there so somebody who starts at
eleven at night can finish their game: **a fix for a rollover boundary, not a second grace day.** The
two look alike from outside — both let you play after the day ended — and they answer different
questions, which is exactly why leaving it implicit would have granted a grace day by accident.

**Principle:** a game people return to out of enjoyment retains better than one they return to out of fear of losing something.

---

## 28. Community

**Decision: no comments or forums on the site. Not in v1.**

### Reasons

- **The cost isn't building it, it's moderating it.** An unwatched comment space degrades, and with thousands of users it adds directly to the daily support hours §18 identifies as the biggest load.
- **It conflicts with the anti-goals** (§1): this is not a baseball social network.
- **Comments on a daily puzzle are a spoiler machine.** Someone posts an answer and ruins the day for latecomers.

### The alternative, at no cost

**Community lives outside.** The share grid pushes conversation to social media, Reddit, and WhatsApp groups, which is where the audience already is. Traffic is retained without taking on moderation.

### If community is wanted later

A dedicated Discord channel, **separate from the site**, with volunteer moderators drawn from the player base.

---

## 29. Site content

**Decision: system-generated content yes. Blog with a publishing commitment, no.**

Rationale: a blog with a calendar is a recurring obligation on top of the daily one, competing with the time the product needs.

### What the system generates on its own

**Every archived puzzle is a page about a real game.** Thousands of indexable pages no other puzzle game can have. The system generates the content, not the operator.

### The reveal card

**Decision: template-generated card, no manual improvement.**

Content, all by database query:

- How the game unfolded per the line score
- Who had the best batting line
- Winner and loser
- Statistical oddities: many strikeouts, late comeback, complete game

**Two things that make it pay off far more than it sounds:**

- **Comparative data** — that it was the only time that pitcher struck out thirteen, that the team was on a nine-game losing streak. It's a query, not writing, and it gives a flavor a generic summary can't. **Almost nobody else has that database.**
- **Link to Baseball Reference** for the game. One line of code: the fan who wants depth goes there on their own. Delegates narrative to whoever already has it.

### Consequence for retention — important

**If the reveal is a card, it stops being the retention hook** §27 assigned it. A card is a pleasant closing, not a reason to return.

**The weight of retention returns to habit, streak, and above all puzzle quality.** The disproportionate effort goes to the **generator and the difficulty curve**, not the text.

*Reason for the decision: with a perpetual daily puzzle, committing to write by hand every day is exactly the kind of recurring obligation the project decided to avoid. Consistency with that principle is worth more than better text.*

### Existing owned content

The operator already writes about baseball history on another site. **That content stays where it is and links to the game.** No duplicated effort, nothing to migrate.

### Recorded, not adopted

It was assessed that the real narrative interest isn't in the game but in **the players** — every boxscore has nine names and almost always one with a story. It would fit progressive reveal and the audience well. Set aside because it would require manual writing.

---

## 30. Game or platform — the growth axis

**Decision: the umbrella is "deduction on real baseball data," not "baseball puzzles."**

It isn't decided now that there will be a platform, but **the name is chosen and the seams left as if there could be.** It's a free option: an umbrella name obligates nothing, while an overly literal name closes the door.

### What's in and what's out

**In — natural growth that reuses the machinery:** deduction on season lines, on standings, on player careers. Same generator, same pipeline, same promise.

**Out — trivia and crosswords.**

- **Trivia uses a different faculty.** One recalls, the other reasons. It's the anti-goal approved in §1, and Immaculate Grid already owns that space and does it well.
- **None of what's built transfers.** The generator, the uniqueness proof, the human-technique solver, and layered validation serve deduction games and are worthless for trivia. It would be starting from zero.
- **Crosswords are built by humans** and don't come from the data.

**The real risk isn't failing at trivia, it's the umbrella ceasing to mean anything.** With "baseball puzzles" you compete head-on with the incumbent. With "deduction on real baseball data" there's nobody.

### Consequences

- **On seams:** C4 and C5 already separate engine from site. A platform would additionally need the shell to host several games and accounts/subscription not tied to one.
- **Note:** if this works, the second game is the cheapest growth available — audience, billing, and data will already exist; only the mechanic is missing.

---

## 31. Novelty and the difficulty curve

### The genre doesn't depend on novelty, it depends on ritual

Crosswords and sudokus have gone decades without exhausting themselves. Nobody does today's sudoku expecting something new — they do it because it's what they do with coffee. **Repetition isn't a defect of the product, it is the product.**

What they provide is **variation within a constant form**: difficulty changes, the solution path changes, the player changes.

### Decision: difficulty tied to the day of the week

**Easy Monday, hard Saturday**, crossword-style. **It's free and worth more than any feature that could be added.**

### Measured, August 2026: three dimensions, not one scale

Over 420 real directions, 35 per decade, solved under random erasure. This replaces the invented
scale that used to sit here.

| Dimension | Lever | What it controls | Available |
|---|---|---|---|
| **Effort** | Target chain length | How long and how chained the solve is | Every day |
| **Character** | Equation families required | Which technique opens the board | Easy and mid days only |
| **Attention** | A live footnote on the direction | Whether the player *can* be made to notice a non-zero footnote | Every day |

**Effort is one variable with three names.** Chain length and narrowest frontier width are near
mirror images of each other (r = −0.81), and erasure count predicts both only moderately (+0.66 and
−0.48). **Pick one and set thresholds on it** — but note that erasure count is the weakest of the
three, so selecting on chain length gives a cleaner grade than selecting on how many cells are blank.

| Cells erased | Solve rate | Chain p50/p90 | Mean frontier | Boards that pinch to one move |
|---:|---:|---|---:|---:|
| 2 | 97.3% | 1 / 1 | 1.99 | — |
| 4 | 86.3% | 1 / 2 | 2.83 | 0% |
| 6 | 70.3% | 2 / 4 | 3.51 | 3% |
| 8 | 54.0% | 2 / 4 | 4.04 | 10% |
| 10 | 39.1% | 4 / 6 | 4.46 | 20% |
| 12 | 25.6% | 4 / 7 | 4.79 | 35% |

Mean frontier *rises* with erasure count: more blanks give more simultaneous openings, not fewer.
What narrows is the minimum.

**Bottleneck frequency was proposed as a fourth dimension and measured out.** No board in the sample
pinched to a single move more than twice, and the frequency rises with erasure count rather than
varying within a level — 0% of boards pinch at four cells erased, 3% at six, 10% at eight, 20% at
ten, 35% at twelve. It grades effort, badly, and adds no dimension. Closed.

**Chain length is the control variable, not cell count.** Of the three effort metrics it is the one
that grades cleanly, so the erasure algorithm takes a target chain length and lets the cell count
fall out of reaching it (§21, §36), and the bands are set on chain length.

### What the erasure algorithm produces (measured, August 2026)

Four orderings, 72 gated directions across every decade, three seeds each — 864 runs. The full
write-up is `discovery/erasure/README.md`.

**⚠️ Measure on the gated pool or the ceiling is fiction.** The first run sampled the whole pool, and
the gate keeps 11% of it. Zeros are exactly what makes a board compressible, so the boards that will
never ship are also the ones that erase furthest:

| | Ungated pool | **Gated pool** |
|---|---:|---:|
| ceiling, max chain p50 | 39 | **23** |
| cells erased at the ceiling | 54 | **40** |
| runs reaching chain 20 | 90% | **64–73%** |

The consequence for the weekly curve is direct: **a chain of 20 is near the top of the range, not
comfortably inside it**, and about a third of gated candidates cannot reach it. This is the
ceiling-measurement error from earlier in this section reappearing as a sampling error.

**Ordering barely matters, and `column_first` loses.** All four reach the same ceiling. `row_first`
gives the least padded easy board — 12% trivial steps at a chain target of 5 against 19–20% for the
others — and `column_first` is last or joint-last on every axis while overshooting its target. The
reach differences at chain 20 (64% to 73%) are about 1.5 standard errors apart and **do not decide
anything**.

*Do not rank orderings by search cost at a fixed chain.* Search cost rises with how empty the board
is, so an ordering that needed more erasures scores harder for free — the same bias that killed
`live/solvable`.

**Symmetric erasure is real and free.** `mirrored` pairs 72.9% of erased batting cells with their
mirror against a 42.9% coincidence baseline, at the same ceiling and cell count. Available as an
aesthetic choice, decided by nothing but taste.

**Targeting: resolution p90 is a separate lever, search cost is half of one.** With the chain fixed,
resolution is independent (|r| ≤ 0.11 at every target) while search cost is weakly tied (r ≈ +0.2)
and its band closes as the chain grows — 0.33–0.67 at chain 5, 0.83–0.92 at chain 20. On a hard board
the search cost fixes itself and there is nothing left to aim at.

A joint target — chain ≥ 11 with both other metrics above their medians — costs **2.39×** the pool
against 1.04× for chain alone, or 7.6 years of calendar instead of 18.1. Affordable. **The data
suggests targeting chain and resolution p90 and reporting search cost rather than pursuing it; the
thresholds themselves are a product decision and are not set here.**

### The three numbers (measured off the ceiling, August 2026)

| Number | Measures | Form |
|---|---|---|
| **Chain length** | Effort — how long the solve runs | — |
| **Search cost** | How hard the next move is to find | max or p90 |
| **Resolution p90** | How much arithmetic a step demands | **p90, never max** |

**They are independent of each other and of zero density**, which is what makes them three numbers
rather than one restated. At chain targets of 5 and 10: search against zero density −0.09 and −0.07,
resolution p90 against chain length −0.04 and −0.07, and the two components against each other +0.01
and −0.13.

**⚠️ All of this was nearly discarded on a measurement error.** The same figures taken at each
board's *compressibility ceiling* said the opposite — search correlated with zero density at +0.48
and separation vanished — because a board pushed to its limit has a maximally hard step somewhere, so
every board scores alike. **No puzzle ships at its ceiling.** The metrics have to be read where
puzzles will actually live. Recorded because it is the kind of error that looks like a failed metric.

**Resolution p90, never its maximum.** The hardest resolution step is almost always a column sum over
nine or ten rows, so the maximum is 8 or 9 on every board and grades nothing. The p90 runs 2 to 9.

**They saturate near the ceiling, in the same direction the character axis collapses.** Search cost
separates by 0.61 at a chain of 5, by 0.47 at 10, by 0.27 at 20, and by 0.02 at the ceiling. Two
independent things going dark in the same place is evidence the saturation is real rather than an
artefact of either measurement — and it is another argument for Sunday sitting mid-difficulty, where
all of this works.

**Hard boards ask for less arithmetic and more searching.** Across the six rendered sample boards,
resolution p90 falls from 8 to 5 as difficulty rises while search cost climbs from 0.50 to 0.92.
**Nobody designed that**; it emerged from the format, and it is worth recording as a property of the
board: difficulty here is scanning, not calculating.

*And the mechanism is now known rather than only observed.* **A single blank in a full column *is*
the long-arithmetic step** — the player adds every other number and subtracts from the total. Erasing
more puts several blanks in each column, so each step combines fewer known terms. Arithmetic weight
is therefore highest where the board is fullest, which is the easy end. See the resolution-ceiling
finding below.

### ⚠️ What the fifty hand-solved boards can and cannot say

**They cannot answer the absolute question.** The operator is a sample of one, with complete command
of the identities, after months of thinking about this board. What he finds easy will be easy for
very few people, and a threshold set from his times would be a threshold set for him.

**What they do give is relative calibration**, which is what the curve actually needs: if rung 9
consistently feels harder than rung 7, the ordering is right even though its absolute position is
unknown. That is worth having and it is all they are.

**The absolute question is answered by the January beta**, and the design already provides for it —
seam C7 records time, hints and errors per game, so a few hundred players give a distribution of
times per rung and the thresholds stop being opinion.

**Before then, ten boards spread across the curve, solved by somebody who knows baseball and nothing
about this project.** Not the full fifty. Ten is enough to see whether the operator's scale and a
stranger's agree at all, and it is the one contrast he cannot give himself.

**And there is no universal difficulty scale to appeal to.** Every puzzle publisher defines its own —
a crossword's Saturday is that paper's Saturday. That is the justification for taking thresholds from
this project's own data rather than an external reference, and it is worth stating so nobody later
goes looking for a standard that does not exist.

### What sudoku's playbook does *not* transfer: balanced clue distribution

Sudoku generators spread their givens evenly across the grid, and it is meaningful there because
every cell of a sudoku means the same thing. **This board is not uniform**: its columns have different
semantics, its rows come in two kinds, and a blank in the LOB footnote is not a blank in a batter's
strikeout column.

It was measured rather than argued. `column_first` — the erasure ordering closest to the sudoku
analogue, round-robin across columns so no column empties before another is touched — **was the worst
of the four on every axis**: most cells erased for a given chain, most trivial steps, lowest ceiling,
and it overshot its target (§31). Recorded here so the analogy does not get proposed again from the
same intuition.

### ⚠️ Two things called "the character axis", and only one of them is difficulty

**Which families a board *contains* and which families *make the player think* are different, and
this section spent weeks measuring the first while meaning the second.**

The evidence is blunt. Attributing each stall to the identity that restarts propagation afterwards:

| Stalls | What restarts them |
|---|---|
| 5 | column_sum 60%, row_identity 40% |
| 8 | row_identity 54%, column_sum 46% |
| 12 | row_identity 63%, column_sum 37% |

**Neither cross-team nor the global identity ever restarts a stall.** Those are the two families that
most distinguish boards — and the two the four-pitcher cap was decided on, at 100% → 78% and 51% →
78%. They separate boards without being where the difficulty lives.

*Same class of correction as chain-versus-stalls: not a missing measurement, but two things sharing a
name.* The family set a board contains is a real property and a usable one for variety; it is simply
not what makes a board hard.

### 🔬 Candidate, not a task: selecting on the restart mix

The mix **shifts with difficulty** — column sums dominate the easy end, the row identity the hard end.
If the generator could favour boards where the row identity breaks most of the stalls, that would give
**variety without touching difficulty**: two boards at eight stalls that open differently.

That is what this section wanted from the character axis and never got, because it was selecting on
families *contained* rather than on families that do the work.

- **Why it is promising:** it sits exactly where the thinking happens, and the solver already reports
  it, so testing costs nothing beyond a measurement run.
- **Why it is unproven:** nobody has checked whether the mix is *selectable*. It may be a property of
  the boxscore that erasure cannot steer, in which case the generator can report it and not aim at it.
- **What would settle it:** erase the same board towards the same stall count under different
  orderings and seeds, and see whether the restart mix moves. If it does not, the candidate is closed.

**Not built.** Recorded so that someone reading in six months knows what was found and what was never
tried.

### ✅ The week runs from chain 5 to chain 11 — decided

> *⚠️ Was 5 → 13, and before that 5 → 20. Both earlier figures are kept below rather than restated,
> because the gap between them is the record of what a contaminated loader cost. The 13 was measured
> on boards carrying phantom rows; the 20 was measured at the compressibility ceiling.*

**The family table decides it.** At a chain target of 11, **41% of boards do not require all four
families**, across two real routes. At 13 it is 19% down a single route:

| Chain target | All four | Second route | Third |
|---:|---:|---|---|
| 9 | 37% | col+cross+row 44% | col+cross+global+row 37% |
| **11** | **59%** | col+cross+row 30% | col+row 7% |
| 13 | 77% | col+cross+row 19% | col+global+row 2% |

Double the variety for two rungs, on a scale that only spans 5 to 11.

**And the character axis goes dark between 11 and 13, not near the ceiling.** §31 spent several
measurements watching it collapse and each time concluded "structural property". The collapse starts
two rungs below where anyone was looking — the same mis-scaling that put the week at 20 also put
Saturday two rungs too high, twice over.

**With the week at 5 → 11, all three dimensions are live on all seven days**, which is what this
section wanted from the beginning and never had. The cost is a slightly easier Saturday, and that is
acceptable: §2's audience is baseball fans who are not necessarily puzzle people, and the first-week
risk was always too hard rather than too soft.

*Record alongside it: on the corrected pool **resolution separates boards out to chain 19 at a width
of 3.0**, where it used to flatten at 15. That does not argue for a harder Saturday, but it means
resolution stays informative across the whole publishable range. And the boredom effect weakened
rather than vanished — the gap is 5.5 points where it was 8.2, and r = +0.478 where it was +0.575.*

### The measurements that set the earlier ceiling of 13

**Not to 20.** Two independent measurements on the ≤4 pool converge on the same ceiling, and the
second one is the serious one.

**The metrics stop separating boards above 15.** A metric earns its place while its spread is wide;
when p10 meets p90 every board scores alike and the number has stopped saying anything.

| Chain target | Reached | Search band width | Resolution band width |
|---:|---:|---:|---:|
| 5 | 100% | 0.20 | 2.0 |
| **9** | 99% | **0.42** | **3.0** |
| **13** | 96% | 0.29 | **3.0** |
| 15 | 91% | 0.23 | 2.0 |
| 17 | 83% | 0.19 | 2.0 |
| 21 | 63% | 0.14 | 2.0 |

Both bands peak between 9 and 13 and are closing by 15. At 21 the search band is a third of its
maximum.

**⚠️ And the hardest day was quietly re-selecting the boards the gate exists to remove.** Boards that
reach a chain of 17 have a mean zero density of **26.6%** against **18.4%** for those that fail —
pressed against the gate's own 30% threshold — and zero density correlates **+0.575** with the chain
ceiling. Compressibility comes from noughts, so aiming at the longest chains selects the emptiest
boards that squeaked through admission. *The hardest day of the week would have been the dullest, and
nothing in the difficulty numbers would have said so.*

*The effect only appears from a target of 17 upward, because below that almost every board reaches
the target and there is no failing group to compare against. That is the reading, not a gap in the
measurement: the selection pressure exists exactly where a large fraction fails.*

**Monday at the low end of 5, Saturday at 13.**

### ✅ And the resolution ceiling is not needed — long arithmetic is an *easy*-board problem

A ceiling on resolution p90 was proposed against the step that combines eleven known numbers, which
is addition rather than deduction. Rescaling the week to 13 changed the question from "what should
the ceiling be" to "is there anything left to cap", and the answer is no. Measured over 144 gated
directions, twelve per decade, walking only as far as the week goes:

| Chain target | p50 | p90 | max | ≥ 10 | ≥ 11 |
|---:|---:|---:|---:|---:|---:|
| 5 | 8 | 10 | 12 | **11%** | 2% |
| 9 | 8 | 9 | 12 | 8% | 1% |
| **13** | **7** | **9** | 11 | **3%** | 0% |

**The tail thins as the chain grows, which is the opposite of the premise.** A board erased to a
chain of 5 still has columns with a single blank, and a single blank in a full column *is* the
eleven-number step. Erase more and the columns carry several blanks, so each step combines fewer
known terms. The arithmetic-heavy board is the Monday board, not the Saturday one.

At the hardest published target the whole tail sits in one place: **23% of thirteen-row boards reach
resolution 10, against 0–3% for nine to twelve rows**, and by decade it is 11% in the 2020s and 8% in
the 2010s against 0% for most of the century — the same batting-row mechanism, at a size that no
longer matters.

**So no ceiling, and the decade skew it would have carried is avoided entirely.** *If one is ever
wanted it belongs at the easy end, where 11% of chain-5 boards clear 10 — and it would still be a
covert batter cap, so it needs the same scrutiny then.*

### The character axis survives to 13 — as a minority route, not a restored lever

> *⚠️ The table below is pre-cap-change, measured at ≤2 pitchers where cross-team was required by
> 100% of boards and therefore distinguished nothing. Kept as the record of what was concluded from
> it. The ≤4 measurement follows.*

| Erasure aimed at | Reachable family combinations |
|---|---|
| chain 5 | col+cross+row 48%, col+row 38%, all four 8%, col+global+row 3%, col alone 1% |
| chain 10 | col+cross+row 58%, all four 29%, col+row 12%, col+global+row 2% |
| chain 20 | all four 81%, col+cross+row 19% |
| the compressibility ceiling | **all four, 100%** |

On the ≤4 pool, at the targets the week actually uses:

| Chain target | All four | cross_team | global_identity | Second most common route |
|---:|---:|---:|---:|---|
| 11 | 46% | 82% | 54% | col+cross+row 36% |
| **13** | **71%** | 93% | 75% | **col+cross+row 22%** |
| 15 | 80% | 97% | 82% | col+cross+row 17% |
| 21 | 93% | 100% | 100% | col+cross+row 7% |

**The "two dimensions on hard days" rule was an artefact of measuring at chain 20 under the old cap.**
At 13 — the hardest day the week now has — **29% of boards do not require all four families**, and
the alternative is not noise: **22% never need the global identity at all.** Saturday can therefore
vary between a board that demands LOB and one that never touches it.

**Stated at its real size: that is a usable minority route, not a symmetric lever.** A 71/22 split
gives Saturday two flavours with one of them rare, which is worth having and is not the third
dimension the easy days enjoy. The axis is not restored; it is alive.

**Saturday's variation has to come from somewhere other than the families, and it is not the roster.**
Board character was measured against the solve and mostly does not separate it:

| Board property | vs search | vs resolution | vs chain |
|---|---:|---:|---:|
| Pitching rows | +0.05 | +0.09 | +0.08 |
| Live footnotes | −0.12 | +0.01 | −0.14 |
| Batting rows | +0.10 | **+0.45** | +0.31 |
| Total runs | −0.34 | −0.05 | **−0.54** |

One, two and three pitching rows give identical search, identical resolution and near-identical chain
length. **Roster shape is not the Saturday lever**, and neither are live footnotes. Only batting rows
(through resolution) and total runs (through effort) move anything.

*That row survives the cap change and is worth keeping in view: pitching rows still do not move the
three numbers at four or five pitchers either (§5). What the extra rows changed is not difficulty but
which families a board can be solved through — the axis this section is about.*

**So Saturday's character is that it is the only day the global identity appears at all** — 82% of
boards at a chain target of 20 need all four families against 8% at a target of 5. That is a real
distinction, and it is the one the format actually offers.

*⚠️ Written when Saturday sat at chain 20. At 13 the statement is nearly inverted: the global
identity is required by 75% of Saturday boards and skipped entirely by 22%, so Saturday's character
is no longer "the day the global identity appears" but a choice between two routes. The paragraph
above stands as what was concluded from the old curve.*

### Sunday is the character day, and the week is an arc rather than a ramp

Sunday had been missing from every version of this curve. The crossword answer does not transfer: the
NYT Sunday is Thursday-difficulty at much larger size, and **this board cannot grow** — six columns is
a hard ceiling and the height is screen-limited.

- **Monday → Saturday:** rising effort from **chain 5 to chain 13**, Saturday the peak.
- **Sunday:** mid difficulty, chosen for the **memorable game** rather than for effort. A shutout, a
  pitchers' duel, a twenty-run game.

*The ceiling moved from 20 to 13 after the rescaling above, which changes the numbers on the ramp but
not its shape. **Worth a fresh reading rather than a patched one:** Sunday became the character day
because Saturday was pinned at the ceiling with no lever, and at 13 Saturday has a minority family
route it did not have. That does not overturn the arc — Sunday's job is recovering the player who
broke on Saturday, which is independent — but the reason "Sunday is the only day with room" is no
longer the whole story.*

Two reasons. **A gentle Sunday recovers the player who broke on Saturday** — with streaks as the
retention mechanism (§27), someone who just lost one needs a reason to come back rather than another
wall. And Sunday is the one day with room for the selection dimension above to work, because it is
not pinned at the compressibility ceiling.

Seven days with distinct identity: six graded by effort, one distinguished by nature.

### The family distribution under random erasure, for reference

Superseded by the chain-targeted figures above, and kept because it shows how much the erasure
strategy changes the answer. At a fixed cell count the families look far more varied than they are.

| Families required | at 6 cells | at 12 cells |
|---|---:|---:|
| Column sums only | 35% | 2% |
| Column sums + row identity | 49% | 50% |
| Column sums + cross-team | 10% | 2% |
| Column sums + cross-team + row identity | 4% | 41% |
| Anything requiring the global identity | <1% | 3% |

Every Tuesday can demand a different opening without changing how long it takes. **The global
identity is rare** — it appears in a few percent of paths even at the hardest level — so a puzzle
that requires it is a genuinely distinct event and worth placing deliberately.

**Attention is a selection axis, and it is two different things that must not be run together.**

- **Whether the direction carries a live footnote at all** is a property of the boxscore. It is
  fixed before any cell is erased, and it is what the calendar selects on.
- **Whether a given solution path had to use one** depends on which cells came out, so it rises with
  erasure count — 0.3% at two cells, 5.7% at six, 21.3% at twelve — and the generator does not
  control it directly.

**Select on the first; the second is a consequence you get more of by erasing more.** Choosing a
Saturday direction that carries a live footnote raises the odds the solver leans on it without
changing the cell count, which is what makes this a third dimension rather than a restatement of
effort. It does not guarantee it, and nothing here can.

**Frontier width ignores the last three steps of a solution, and that is not arbitrary.** A solve
narrows by exhaustion as it runs out of cells. Trimming one step leaves 43% of boards reporting a
bottleneck of one; trimming two leaves 36%; trimming three leaves 10% and the distribution comes out
smooth. Less than three and the metric mostly reports its own artefact. Recorded here so it is not
relitigated.

**⚠️ The band boundaries are not set.** These are distributions, not thresholds. Where the lines
fall gets fixed against real solving times from the January beta — which is what C7 records — and
not against anyone's estimate of what feels hard.

### Rejected: random daily difficulty

- **It removes the player's ability to plan.** Someone who knows Monday is five minutes and Saturday is forty can do it at breakfast on weekdays and save the weekend. Without anticipation, the day a hard one lands with ten free minutes, it gets abandoned — **and that abandonment breaks the streak**, which is the retention mechanism.
- **The weekly pattern *is* part of the ritual.** Saturday being hard gives Saturday character. Random is noise, and noise doesn't become habit.
- **It makes progression invisible.** A player can't feel improvement without a stable reference.
- **First-week risk.** With baseball fans who aren't necessarily puzzle people, the first week decides whether they stay. The calendar guarantees their first Monday is gentle; random could hand them a brutal Saturday on day one.

### Yes: randomness *within* the level

Every Tuesday at medium difficulty, but **each Tuesday demanding different techniques** — one opens via the pitching cross, another via the global identity. Predictable in effort, unpredictable in path.

It's what crosswords do: Saturday is always hard, but never the same kind of hard.

**This is now a pool query rather than an aspiration.** The family distributions above show the
variety is really there at every effort level, so the calendar builder selects on two axes and
sprinkles the third.

### Format's own advantage

**The data does vary.** A sudoku is always the same nine digits. Here there are different eras, one-run games and twenty-run games, shutouts and blowouts, names appearing. Every board has its own texture even though the rules don't change — more variety than the genre has.

### Warning about what does NOT help

**Adding features.** Daily games that age badly are the ones that answer boredom with achievements, coins, and events. That doesn't fix a weak puzzle, it only disguises it.

**What decides whether it lasts five years:** that the puzzle is well made, that difficulty is honest, that there's never guessing, and that it ships every day without failing.

**The defense against novelty decay isn't a feature. It's the generator.**

---

## 32. Data sources

### Primary source: Retrosheet

Confirmed. Event files in SQL Server, already in the operator's possession. Commercial use permitted with the prominent copyright notice (see §10 and the notice at the end of this document).

### Generation tool: cwbox (Chadwick tools)

`https://github.com/chadwickbureau/chadwick`

**This is the pipeline's input engine.** `cwbox` is a boxscore generator, part of the command-line tools for extracting information from Retrosheet event files, alongside `cwevent`, `cwgame`, `cwsub`, and `cwdaily`.

**Why it fits:**

- **It derives the boxscore from the events**, so totals balance by construction — it inherits no transcription errors.
- Starting from play-by-play, it carries what a newspaper boxscore lacks: **RBI, BB, and K per batter, LOB, and complete pitching lines**. Resolves the board's column problem (§6).
- The operator already has experience with these tools.

**License:** Chadwick is GPL. No impact on the project — running a command-line tool doesn't contaminate the output. It would only matter if its source were incorporated.

### ⚠️ Pool criterion: the three source file types are not equivalent

Retrosheet publishes the material in three forms, and **they must be distinguished when building the pool**:

| Type | Reliability |
|---|---|
| **Boxscore files** | Reflect **official totals**. Most reliable. |
| **Event files** | Reflect the limitations of known play-by-play sources for that game. |
| **Deduced event files** | **Reconstructions** from partial information and context, not complete accounts. |

**Games from deduced event files must be excluded from the pool.** They are reconstructions, and that's where boxscores that don't balance will show up.

**⚠️ Loader defect found (August 2026):** the download script concatenates `<season>*.E??`, and that
wildcard swallows `.EDA/.EDN/.EDF` — the deduced files. 105 files, 3,465 games, 1910–1968, already
loaded with nothing distinguishing them. The zips are the only place the distinction survives.

**Fix: record provenance as a column** on the game table (source file extension), rather than
maintaining a separate exclusion list. A regenerated exclusion list is a second source of truth that
can drift; a provenance column is permanent, queryable data — and §22's layer 1 needs it anyway.

**Done (August 2026):** `dbo.retroGameProvenance`, one row per game, carrying the extension it was
found under and rebuildable from the zips. 202,036 games, 3,465 of them deduced. Pool queries join
it: `WHERE is_deduced = 0 AND source_type <> 'EVR'`.

### Negro Leagues games are excluded, and that is a position rather than housekeeping

**MLB reclassified the Negro Leagues as major leagues in December 2020.** Leaving them out of a
baseball product is therefore a decision someone can read backwards, and stated as one line in a list
it reads as disinterest. It is not, and the reasoning belongs on the record.

**The reason is data quality, and it is the same criterion that excludes deduced event files.**
Retrosheet's Negro Leagues data is transcribed from newspaper box scores rather than scored from a
scoresheet, so a column that was never printed arrives as nought rather than as unknown: **93.7% of
their batter rows carry K = 0 against 74.2% in contemporary regular play.** A board built from them
would state strikeout figures that nobody recorded.

**The awkward part, said plainly: they pass every identity.** 3,744 directions, zero row-identity
failures, zero mismatches on all four cross-team sums — cleaner than the 1935–1949 control, which has
one of each. So layer 1 of §22 does *not* catch them on its own merits, and the exclusion is a
provenance rule rather than an arithmetic one. A board that balances perfectly and is quietly wrong
is the failure mode §22 calls the worst, because no later layer can see it.

**The acknowledged cost.** Josh Gibson and Satchel Paige are genuinely recognisable — a fan knows
them, and the progressive reveal (§7) would land well on either. But that is two or three names
across 1,872 games, against a pool that already has eighteen years of calendar without them. **It
does not change the conclusion**, and it is worth saying that it was weighed rather than overlooked.

*If Retrosheet's Negro Leagues coverage ever gains scored play-by-play rather than transcribed box
scores, this decision should be revisited on its merits.*

### The exclusion list turned out to have a second entry

The provenance load left **1,872 games with no row**, all of them Negro Leagues: Retrosheet ships one
`<season>NGL.EVR` per season inside the same regular-season zip, and the extension pattern everything
had been written against — `.E[VD][ANF]` — does not match an R. They were in the pool from the first
day and had never passed through the deduced filter, because that filter was a list of ids from a
different set of files.

**Excluded, and not because they fail anything.** They pass: 3,744 directions, **zero** row-identity
failures and zero mismatches on all four cross-team sums — cleaner than the 1935–1949 control, which
has one of each. They are newspaper box scores transcribed rather than games scored from a
scoresheet, so a column that was never printed arrives as nought rather than as unknown: **93.7% of
their batter rows carry K = 0 against 74.2% in contemporary regular play.** A board that balances
perfectly and is quietly wrong is the failure mode §22 calls the worst, because no later layer can
catch it. The pool loses 0.9% and has years of calendar to spare.

*The general lesson is the one the provenance table was built for: an exclusion written as a pattern
over filenames is a guess about a naming scheme, and this one was wrong for thirty-six seasons
without anything going red.*

### Good news about the chosen columns

Retrosheet proofs **offensive and pitching** statistics closely. **Defensive** ones — putouts and assists — are proofed less, because they were known to be kept far less reliably.

The §6 board uses PA, AB, R, H, BB, K and IP, H, R, ER, BB, K: **all from the well-proofed side.** The problematic columns are exactly the ones dropped for lack of screen space. **The mobile constraint prevented a data problem.**

### Evaluated and rejected: chadwickbureau/data-boxscores

`https://github.com/chadwickbureau/data-boxscores`

*(A different repository from the Chadwick tools; reviewed due to a URL mix-up.)* **Unusable as a source.** Four reasons:

1. **It's minor league, not Major League.** The one-line pitch (§1) says "a real Major League game," and the reveal card with its Baseball Reference link loses its value with a forgotten minor-league game.
2. **It is deliberately an uncorrected archive.** The README warns that sources contain errors and that the collection doesn't attempt to correct them. The governing principle is *"type what's in the source,"* and it warns that **totals will not balance.** Conflicts with §22.
3. **It deliberately omits derivable values.** Its own example: if a boxscore lists Smith with 8 innings and doesn't mention Jones, they instruct *not* to transcribe Jones's inning even though it follows logically. **That deduction is exactly the game's mechanic.**
4. **Missing columns.** The most common header set is `ab r h po a e` — no RBI, BB, or K per batter.

**License:** data CC BY 4.0 (commercial use permitted with attribution); parser GPL 2.0.

### Separately useful: the Chadwick Bureau person register

`chadwickbureau/register` — for resolving player identities and names, exactly what §7's progressive reveal needs.

---

## 33. Environment separation: forge and serve

**These are not two environments of the same system. They are two separate systems communicating by artifact transfer, not over the network.**

> *Naming note: "forge" and "serve" replace the earlier informal terms. Pending final confirmation.*

### The boundary

**Operator's laptop — "forge", intermittent availability:**

- SQL Server with Retrosheet
- cwbox and the rest of the Chadwick tools
- Pool quality filter (§5)
- Generator and erasure algorithm
- Human-technique validation solver (§4)
- End-to-end verification (§22)
- Calendar construction (§21)

Everything heavy and everything that can take hours.

**VPS — "serve", permanent availability:**

- Serving already-cooked puzzles
- The few endpoints: token, device registration, event sync

**The artifact that crosses is an immutable package of already-validated puzzles. The VPS never generates or validates anything — it only serves what it received.**

### The complete rule

**The forge knows nothing about users. The service knows nothing about generating.**

### The puzzle identifier is opaque, and the mapping back to the game stays in the forge

C2 asks for an immutable id derived from the game. **Derived, not transcribed:** a Retrosheet id like
`SLN191310050` spells out the team and the date, which §7 withholds until the player has earned
them, so shipping it hands the reveal to anyone who opens the developer tools once.

That is a different thing from the answer being findable. §9 already accepts that the solution lives
in the client and is visible to anyone who looks, because the streak is against yourself. What this
avoids is the answer being **legible at a glance** — it costs nothing and does not pretend to stop
anyone determined.

So the served artefact carries a hash. **The table mapping puzzle id back to game and direction is
forge-side and never leaves the laptop**, alongside the generator itself.

Neither machine needs to know the other's world. **The backend laptop knows nothing about rankings, accounts, or streaks.**

### Three independent domains with distinct lifecycles

| Domain | Who writes | Lifecycle |
|---|---|---|
| **Puzzles and calendar** | Forge only | Immutable, versioned. The VPS receives and never touches them |
| **The application** (engine, interface, copy) | Deployment | Deployed and rolled back at will, **without touching inventory** |
| **User data** (accounts, streaks, events, devices) | VPS only | The laptop never sees it |

**The use case this solves:** changing the application for a UX reason must not require touching the puzzle inventory or the calendar. And vice versa: loading new inventory must not require touching the application.

**Free privacy benefit:** personal data never leaves the server. The laptop is not an exposure surface for customer information, which simplifies the privacy policy.

### Service stack: Docker and nginx

**Decided.** With one care that follows from the above:

**The container and the puzzle inventory must be separate things.** If puzzles travel inside the image, every application deployment rebuilds the image and drags the inventory along — exactly what must be avoided.

- **The application goes in the container**
- **The puzzles are mounted as a volume**
- **Inventory updates and application deployments are independent operations**

**Domain configuration in nginx** (decided in advance, applied when the server is set up):

- Permanent (301) redirect from `boxscorepuzzles.com` and `boxscorepuzzle.app` to `boxscorepuzzle.com`
- Choose with or without `www` and redirect the other variant
- One indexable address only, to avoid diluting ranking across duplicates

### Forward inventory: 5 months

**Decision: the VPS always holds five months of puzzles served ahead.**

Covers an entire winter, which is exactly when the project might go unattended (§25).

**Alert when inventory drops below three months**, to find out with margin rather than all at once.

### The data container and its API

**The inventory lives in its own container with its own read layer.** The application requests puzzles and doesn't know how they're stored; updating inventory still doesn't touch the app.

**The key distinction is public read versus private write:**

| Operation | Protection |
|---|---|
| **Daily puzzle** | **None.** Static file served by nginx, no API, no key |
| **Inventory upload from the laptop** | **Header key.** It's a write, happens rarely, isn't in anyone's play path |
| **Paid historical archive** | **`canAccess()` from C8** validating the user token |

**Why the daily puzzle carries no key:**

- A header key **travels to the browser** and anyone can see it in the network tab. It protects nothing.
- It turns game delivery into an authenticated call, exactly what §23 avoids. If that layer falls or the key expires, **the game doesn't load** — introducing a fragile dependency in the one path that must survive everything.
- The daily puzzle is **public by nature**: everyone will see it today.

**And a static key is useless for the paid archive:** it's the same for everyone and doesn't distinguish who paid, which is the only thing that actually needs controlling.

### Abuse of the open daily puzzle — what's defended and what isn't

Three distinct scenarios, and only one deserves a defense:

| Scenario | Response |
|---|---|
| **Copying the daily puzzle to republish** | Unlikely — would require building an interface and attracting users. The defense is brand, not technical: streaks and stats live on the original site |
| **Downloading the full inventory** | Real, but **a key doesn't solve it.** Publishing only the day's file does; the archive sits behind C8 |
| **Automated traffic that takes down the server** | **The only one that truly matters** |

**For the third, the tool isn't authentication:**

- Per-IP rate limiting in nginx
- Only the current date's puzzle published, nothing future
- Caching with correct headers, absorbing almost all traffic before it reaches the container

**A cached static file withstands far more than an authenticated endpoint**, so leaving it open makes it *more* abuse-resistant, not less.

**And the underlying point:** the daily puzzle is public by design. Everyone will see it today and sharing is desired — it's the main growth channel (§20). Putting a barrier on it fights the model itself.

**What protects the business is what's already decided:** archive, stats, and streaks behind an account.

### Consequences

**1. Publishing well ahead stops being good practice and becomes mandatory.** If the laptop is the only machine that can produce puzzles, the VPS needs **months of inventory served ahead**. The laptop can be off, on a plane, or broken.

**2. The transfer must be verifiable.** Sign the package and verify the signature on receipt — already planned in §22 against corruption — now also covering an incomplete or interrupted upload.

**3. ⚠️ The laptop is a single point of failure.** If it dies, the pipeline and the ability to produce are lost. The site stays alive as long as inventory lasts, but can't be replenished.

Requires:

- Backup of the generator code
- Backup of the processed Retrosheet database
- Knowing how long rebuilding the environment on a new machine would take

### Folder and repository structure

```
boxscorepuzzle/
├── CLAUDE.md
├── docs/
│   ├── design-boxscore-puzzle.md
│   └── python-conventions.md
├── forge/           ← generator, cwbox, SQL, validation, calendar
└── serve/           ← app, nginx, docker, endpoints
```

A single root containing everything, with this section's separation visible in the structure itself. Name without spaces or hyphens, matching the domain.

**A single private Git repository on GitHub: `boxscorepuzzle`.** Rationale: one push backs up everything, which matters because the repository's primary job is being the backup. The forge/serve separation is enforced where it actually matters — in deployment configuration and in the no-cross-imports rule — not by repository boundaries. **Deployment ships `serve/` only; generator code must never reach the VPS.**

**The repository stays private permanently.** `forge/` holds the generator algorithm and the solvability guarantee — the trade secret identified in §16.

**GitHub is also the backup that consequence 3 requires.** Pushing is not optional hygiene, it's the disaster recovery plan: push at the end of every working session.

**What GitHub does not cover, and how each is handled:**

| Asset | Coverage |
|---|---|
| Generated puzzle inventory | The VPS is already a second copy — five months stay served even if the laptop dies |
| Processed Retrosheet database | Not backed up; **the loader script is.** Keep the load process reproducible from Retrosheet's original files |

That second row is the design rule: **make the pipeline reproducible rather than backing up its output.** The backup is the code.

*If `serve` ever needs its own CI, collaborators, or release cadence, splitting it out later is minor work.*

**⚠️ Generated puzzle inventory does not go in Git.** Thousands of files growing indefinitely, and not code. They go to an ignored folder inside `forge` and from there transfer to the VPS. If they enter the repository, within a year it's unusable.

**`CLAUDE.md` at the root** with the non-negotiable constraints, so they're read every working session:

- The no-backtracking guarantee (§4)
- Layered validation with code independent of the generator (§22)
- Double idempotence (§21)
- The calendar extends, never rewrites (§21)
- The forge knows nothing about users; the service knows nothing about generating (§33)

---

## 34. Legal matters — revisit before launch

> *None of this is legal advice. Confirm with a lawyer before launch.*

### Required on day 1

Since the site launches charging from day 0 (§10), these are not optional:

- **Terms of service.** The essential content is already decided and scattered through this document: access while the service operates (§10), personal and household use (§11), free cancellation. Drafting remains.
- **Privacy policy.** Mandatory as soon as there are accounts. **With users in Spain and the EU, GDPR applies**, even with operations in Miami.
- **Refund policy.** ⚠️ **Nobody now requires it and it matters more, not less.** Paddle required one as a condition of selling; with Stripe the operator is the seller and **carries chargeback liability**, and a published refund policy is the primary defence against a dispute. §18 already decided on no-questions refunds below a threshold.
- **Retrosheet notice**, visible and prominent.
- **LLC formed** (§17).

### Not yet discussed

- **⚠️ Right to data deletion.** GDPR and California law require it. **It conflicts with the design and must be resolved:** if someone asks to delete their account, what happens to their C7 events that feed §26's percentiles? The likely answer is **anonymize rather than delete** — see §35, which resolves this at the schema level.
- **Cookies and consent.** Needed the day there are ads or analytics. C10 already anticipated this architecturally.
- **Taxes.** Collection delegated to the merchant of record. Declaring the income remains the operator's responsibility.
- **Minors.** A puzzle game will attract teenagers. In the US, COPPA applies under 13; the standard approach is to **prohibit registration under 13 in the terms**.
- **Real player names and data.** Statistical data are facts and nobody owns them. **But team photos and logos are owned.** With the text card and the Baseball Reference link (§29), there's no issue — best not to stray from that.
- **Accessibility.** Lawsuits over inaccessible commercial sites have proliferated in the US. Reinforces that accessibility is designed, not retrofitted (§6).

### Priority

**Trademark goes first.** It isn't a document drafted in an afternoon — clearance and registration take months.

---

## 35. User data

**Principle: the minimum required to operate.** Store what the already-decided features need, nothing more. Every extra field is leak surface and compliance work.

### What is stored

**Identity**

- Own internal identifier
- Email
- Link to the OAuth provider
- Creation and last-access dates

**No real name, photo, or date of birth**, even if Google offers them. They aren't needed, and requesting fewer permissions improves conversion on the login screen.

**Subscription**

- Stripe customer identifier
- Status
- Expiry date

**No card or billing data** — ⚠️ **and the reason changed with the processor, so do not carry the old one
across.** Under a merchant of record it lived at Paddle because Paddle was the seller. Under Stripe it
lives at Stripe because **the card never reaches our servers**: hosted checkout or tokenised Elements keep
this system out of PCI scope entirely. Same field list, different guarantee — and the new one only holds
as long as nothing ever posts a card number to us "just for a moment".

**Devices** (§11)

- Random UUID
- Last seen
- Human-readable label so the user can recognize which one it is

No browser fingerprinting.

**Games — the heart of C7**

Per game: puzzle identifier, date, duration, whether completed, hints used, errors, and the highest technique required.

⚠️ **Events from players without an account are inside "the minimum to operate", not outside it.** They
upload under the device UUID §11 already creates. The reason is not convenience: **without them the
retention numbers would describe subscribers only**, and the retention of people who do not pay is what
decides whether this grows at all (§20). Measuring only the people who already converted is measuring the
answer to the wrong question.

⚠️ **And the account link has to be possible from the start.** The event carries the device UUID always,
and the account identifier when one exists; on registration, that device's events are attributed to the
account **without dropping the UUID**, since the same device may keep being used signed out. Retrofitting
this means losing every pre-registration event or reconstructing an association nobody recorded. It costs
one column now. Full reasoning in `docs/serve-flow.md`.

**The filled cells are not stored.** They aren't needed: percentiles, streaks, and difficulty calibration all come from aggregates.

**Preferences**

- Language
- Accessibility settings, if any

### What is NOT stored

- **IP address.** Personal data under GDPR and it adds nothing. For rate limiting, nginx uses it in memory without persistence
- Geolocation
- In-site browsing history
- Anything kept "just in case"

### Two schema requirements

**1. Separate events from identity at schema design time.** If a game references an unlinkable user identifier, **GDPR deletion is resolved by breaking that link** — and percentiles survive because the aggregate data becomes anonymous. **This resolves the conflict noted in §34.**

**2. Define a retention policy.** An account inactive for three years probably doesn't need to stay. Less old data is less risk.

---

## 36. Open items

**Blocking**

- [x] ~~Player names~~ — **resolved:** progressive reveal (§7)
- [x] ~~**v1 board.**~~ — **resolved (August 2026).** Column set, six-column ceiling, line-score-as-anchor and per-batter footnotes decided in §6; roster caps decided at **≤13 batters and ≤4 pitchers** (§5, §6). The browser prototype ran and its finding was that rows on screen do not bind, which is what freed both caps. *Erasure percentage is not a parameter — the generator targets a chain length and the cell count is whatever reaching it costs (§31).* The principle that puzzle quality outranks board size held: the pitcher cap moved because it was costing era, not because the board grew.

**Game core**

- [x] ~~**Erasure algorithm.**~~ — **resolved (August 2026).** Its input is a target chain length and the cell count is whatever reaching it costs (§31). Ordering is `row_first`, chosen because it pads the easy board least; symmetry was measured, found real and free, and **dropped** because mirroring a boxscore pairs the leadoff hitter with the ninth and means nothing in baseball. The zero-density companion constraint is unnecessary: the 30% gate handles it at admission (§5)
- [x] ~~Which cells are never erased~~ — **resolved:** the line score, by width constraint (§6)
- [ ] ⚠️ **Re-measure everything computed on loaded boards.** A loader defect put non-batting pitchers on the board as all-zero rows — 18.8% of Retrosheet's batting rows have no plate appearance — which inflated zero density, wrongly failed directions against the batter cap, and put the lineup in the wrong order. Fixed, and the pool measurements are re-run. **Still to redo:** the difficulty metrics, the erasure ordering comparison, the week's ceiling at 13, the pitcher cap's quality argument, layer 3b's 71%, and the fifty-board pack (§5)
- [ ] **Whether the 5% pre-1950 quota is still wanted.** It was adopted to fix a 78% pre-1950 pool that turned out to be 29% once the defect was removed. It survives as a preference about what the player meets rather than as a correction, and that is a different decision (§5)
- [ ] ⚠️ **Layer 3 does not verify human derivability.** It runs interval propagation to a fixed point over forty-odd simultaneous relations, which is stronger than any person. Measured: at a chain target of 13, only **71%** of published boards also certify under one-relation-at-a-time solving. The true figure for a human is somewhere between 71% and 100% and is currently unknown (§22)
- [ ] **Whether layer 3b becomes a gate.** Decided by the fifty-board hand-solve rather than by further measurement — two solvers already bracket the answer and neither of them is a player. For: 29% is inside the 30% discard §22 calls free. Against: the weak solver is a caricature in the other direction (§22)
- [ ] **The fifty-board hand-solve is a launch gate, not a review step.** It is the only real verification of human derivability that exists, and the only check the common-author risk does not touch. Boards, solutions, key and recording sheet are built in `discovery/hand-solve/` (§22)
- [x] ~~Error handling~~ — **resolved (August 2026): validation only on *done*, and never *where* or *how many*** (`docs/serve-flow.md`). Immediate marking and a wrong-cell count were both considered and both rejected for one reason: they turn the board into an oracle. Unlike sudoku this board can tell instantly that a value breaks an identity, so marking makes probing beat deducing — and a count is worse, because changing one cell and watching the number is a binary search over the board. Unlimited attempts, and **no error limit is available at all**: §27 forbids a fail state. The disincentive is the clock
- [x] ~~What exactly a hint is~~ — **resolved (August 2026): there are none** (`docs/serve-flow.md`). §22 guarantees every published board is solvable without a single guess, so *stuck with no way forward* is a state that cannot occur — **a board that needed a hint means the guarantee failed**, and the fix is the generator. The consequence is that the only exit from being stuck is to give up, which §27's free grace day, streak insurance and non-disappearing puzzle already cover
- [x] ~~Saving, pausing, resuming~~ — **resolved:** the puzzle stays open all day and saves itself (§27), and **the mechanics are now written** (`docs/serve-flow.md`): `localStorage` rather than cookies, holding the filled cells, the accumulated time and the event record. ⚠️ **An accumulated duration, never a start timestamp** — the clock pauses, so a start time would count the pause
- [x] ~~What time the puzzle rolls over: local midnight or UTC~~ — **resolved (2026-08-23): neither. The day rolls at 08:00 UTC, a fixed `UTC-8`** (`docs/calendar.md`). *Local midnight* was never available — `CLAUDE.md` forbids deriving the day from device-local state, and the hard reason is that a device clock is something the player **sets**, so it would make changing a phone setting a way to fetch tomorrow's board. And **UTC is the worst of the server-side answers**: it lands at 20:00 Eastern, so a player who sits down at 19:45 loses the board fifteen minutes later. UTC-8 lands at 03:00 Eastern and midnight Pacific in winter, **04:00 and 01:00 under daylight saving** — nobody in the contiguous states is at a board at any of the four. ⚠️ It rests on §10's US-audience premise, which now carries three decisions rather than two
- [x] ~~What breaks the streak and whether there's grace~~ — **resolved:** midnight close for streak purposes, free monthly grace day, streak insurance in the paid tier (§27)
- [x] ~~Weekly difficulty curve~~ — **resolved, revised, and now scaled:** an arc rather than a ramp, running **chain 5 to chain 13** rather than to 20. The metric bands close above 15, and boards reaching 17 are the emptiest ones the gate let through — the hardest day was re-selecting what admission removed. At 13 a minority family route survives, so Saturday has two flavours rather than one (§31)

**Presentation**

- [x] ~~What the final reveal shows~~ — **resolved:** template-generated card with comparative data and a Baseball Reference link (§29)
- [ ] What the share grid encodes without spoilers (no names)
- [x] ~~Where the revealed name appears on mobile~~ — **resolved:** in the row label itself, as the surname abbreviated to seven characters, disambiguated by first initial where two are identical (§6, §7)
- [ ] How candidates mode works without hover (§6)

**Level 100**

- [x] ~~Can you lose?~~ — **resolved:** §27
- [x] ~~Does time matter?~~ — **resolved:** §26, and **what the clock counts is now written** (`docs/serve-flow.md`): page visibility plus a deliberately generous inactivity timeout, because staring at a deduction board without touching it *is* play. ⚠️ **Invisible until the end** — §26 says a running clock changes how the game is played, and §2's audience is exactly who a climbing counter drives away. Not tamper-proof, and does not need to be: the time is shared between friends, not ranked
- [x] ~~Is there a social layer?~~ — **resolved:** §26
- [x] ~~Does novelty run out?~~ — **resolved:** §31
- [x] ~~Seasonality~~ — **resolved:** §25
- [x] ~~Puzzle only, or content too?~~ — **resolved:** §29
- [x] ~~Is there community?~~ — **resolved:** §28
- [x] ~~What about players who don't know baseball?~~ — **resolved:** §8, ⚠️ with its *mandatory on
  first play* clause superseded 2026-08-20 (`docs/serve-flow.md` §1b)
- [x] ~~The one-line pitch~~ — **resolved:** §1
- [x] ~~The anti-goals~~ — **resolved:** §1
- [x] ~~What the product is in a year~~ — **resolved:** §30
- [x] ~~Brand and domain~~ — **resolved:** §24
- [x] ~~What gets measured to know it's working~~ — **decided in design, built in no part** (`docs/serve-flow.md`). C7's record already gives starts, completions, duration, errors and technique, and therefore **which days people abandon**, which is the honest difficulty signal. Owed: retention at 1, 7 and 30 days (§20), streak-break-and-never-return (§27), and conversion. Nothing beyond what will actually be read — §35's minimum-to-operate applies to analytics too
- [ ] **Accessibility as a product decision.** A grid of numbers with correct semantics is surprisingly playable with a screen reader — one of the few games a blind person could play in full. Could be a differentiator, not just compliance

**Data**

- [x] ~~Retrosheet coverage~~ — **measured (August 2026), re-measured under the decided caps:** funnel in §5. 110,833 surviving directions, **12,218** after the zero-density gate — 18.1 years of calendar
- [x] ~~**The era the gate leaves behind.**~~ — **decided: a 5% pre-1950 calendar quota**, roughly eighteen puzzles a year. A quota on the calendar and not a filter on the pool: nothing is discarded, and the calendar builder rations which directions get used. It is what made the pitcher cap the binding constraint and moved it to ≤4 (§5)
- [x] ~~Is T3 reachable~~ — **resolved: no, and no column set changes that.** Every identity is a sum over a row or a column, so two of them share at most one cell (§4)
- [x] ~~The column set~~ — **resolved: `PA, AB, R, H, BB, K`** with footnotes attributed per batter by position label (§6, §7)
- [x] ~~Technique distribution~~ — **measured (August 2026):** two axes replace the ladder, and the calendar model is in §31
- [x] ~~Compressibility as a pool quality metric~~ — **measured, and it is not one (August 2026).** Median 58.6% of the grid removable, against the 25–35% that had been invented. But it correlates +0.79 with zero density, so ranking on it selects boredom. **Demoted to a viability constraint**; the quality criterion is the zero-density gate plus the three numbers (§5, §31)
- [x] ~~The quality criterion~~ — **resolved: the 30% zero-density gate**, then chain length, search cost and resolution p90. The gate removes every shutout and the three-run games while keeping seven-run ones, and family variety survives it (§5)
- [x] ~~Bottleneck frequency as a difficulty dimension~~ — **measured and rejected (August 2026).** No board pinches to a single move more than twice, and the frequency rises monotonically with erasure count rather than varying within a level, so there is nothing in it to grade. Closed; do not propose it again (§31)
- [x] ~~Does board character separate the solve~~ — **measured, mostly no (August 2026).** Roster shape and live footnotes do not; only batting rows and total runs move anything, and both through effort rather than character (§31)
- [x] ~~**Erasure ordering.**~~ — **measured (August 2026), and it is not a lever.** Its input is a target chain length, not a number of cells (§21). All four orderings reach the same ceiling; `column_first` loses on every axis and is the one worth removing; symmetric erasure is real and free, so it is taste. §31 carries the numbers and the ceiling correction
- [x] ~~**Whether the generator targets one metric or three.**~~ — **resolved: one.** Target chain length, report search cost, and no resolution ceiling. The ceiling was going to cap long arithmetic on hard boards; measured inside the publishable range it turned out long arithmetic is *Monday's* problem — a single blank in a full column is the eleven-number step, and erasing more gives each step fewer known terms. 11% of chain-5 boards reach resolution 10 against 3% at chain 13 (§31). **The difficulty bands themselves are still unset** and go on chain length, against real solving times from the January beta
- [x] ~~**Whether a resolution ceiling is needed at all.**~~ — **measured, and it is not (August 2026).** Inside the publishable range the long-arithmetic tail is thin and points the wrong way: see §31
- [x] ~~**Footnote row ambiguity.**~~ — **removed at the source (August 2026).** Repeated position labels are suffixed by order of appearance, so `SF: LF-2` names one row. The erasure constraint and the domain-bounding model it implied are not needed (§5)
- [x] ~~Re-measure era distribution after the zero-density gate~~ — **done (August 2026):** the decade table is in §5, and it moved the opposite way from the prediction. The calendar does need era weighting, which is the 5% quota below
- [x] ~~**Loader fix:** add a provenance column so deduced event files are distinguishable (§32)~~ — **done (August 2026):** `dbo.retroGameProvenance`, 202,036 games. It immediately found 1,872 Negro Leagues games that had been in the pool all along; they are excluded too (§32)
- [x] ~~Prior arithmetic validation~~ — **resolved:** layer 1 of §22
- [x] ~~No-repetition policy~~ — **resolved:** at batch generation (§21)

**Business and operations**

- [ ] Final pricing and the free/paid line
- [x] ~~Retention metrics~~ — **specified, not built** (`docs/serve-flow.md` §8). Day 1, day 7, day 30; streak distribution and the break-and-vanish rate; conversion once there is a paywall
- [ ] Privacy, terms, refunds, and data deletion — full inventory in §34
- [ ] Retention policy: how long an inactive account is kept (§35)
- [ ] Accessibility: screen readers, color blindness, touch targets
- [ ] Forge rebuild plan if the laptop is lost (§33)
- [x] ~~Months of forward inventory~~ — **resolved:** 5 months, alert below 3 (§33)
- [x] ~~Daily publishing: batch or scheduled process~~ — **resolved:** pre-generated batch with fixed calendar (§21)
- [x] ~~What to do if a puzzle ships defective~~ — **resolved:** verified backup + substitution switch; if the date has passed, void it but don't reassign (§21, §22)

---

## Required notice

> The information used here was obtained free of charge from and is copyrighted by Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".
