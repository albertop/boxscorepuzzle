# The pitcher cap, and two questions no correlation could answer

Run date: 2026-08-17. Scripts: `cap_gate_sweep.ps1`, `measure_pitching.py`, `render_boards.py`.

## Why the cap moved

Under §5's 5% pre-1950 calendar quota the binding number stops being "directions that survive" and
becomes "directions from 1950 onwards", because the old half is capped at one puzzle in twenty.

| Pitcher cap | Directions | From 1950 on | Years of calendar |
|---|---:|---:|---:|
| ≤2 *(old)* | 12,218 | 3,405 | 5.3 |
| ≤3 | 20,507 | 8,200 | 12.8 |
| **≤4 — decided** | **25,270** | **11,884** | **18.6** |
| ≤5 | 26,877 | 13,262 | 20.7 |

Batters ≤13, gate 30%. The batter cap has stopped being a lever: 13 → 15 moves every figure by about
1%.

## The filler hypothesis: structurally right, and it did not matter

The prediction was that extra pitching rows would participate weakly and add free steps, because a
pitching line crosses the offense only through totals.

**Structurally correct.** Constraints per row fall from 3.03 at two pitchers to 2.35 at five, and
three extra rows buy less than one extra equation (35.9 → 36.7).

**Behaviourally backwards.** At a chain target of 14 with the same ~30 cells erased, trivial steps
*fall* from 0.23 to 0.18, the ceiling holds, and the pitching section grows from 23.9% to 30.3% of
the solution path. With two pitchers the section is 17% of the rows and 24% of the steps; it
over-participates and then displaces free steps as it grows.

Repeated on a **1970–2009 window** where all four counts coexist, because pitcher count and era are
nearly the same variable in this data: trivial 0.22 → 0.18, pitching steps 22.6% → 30.5%. Same
result. *Without that window the whole measurement would have been era wearing a pitcher-count
costume.* ⚠️ 20 directions per cell there; the ceiling oscillates (22 at four, 28 at five) and that is
noise.

## The family table, which is the real finding

At a chain target of 11, read off the `Family` enum rather than hand-written strings — the first
version of this table looked up `"global"` against a family whose value is `"global_identity"` and
reported it as never used, which hid the result below:

| Pitchers | column_sum | row_identity | cross_team | global_identity | all four |
|---:|---:|---:|---:|---:|---:|
| 2 | 100% | 100% | **100%** | 50% | 50% |
| 3 | 100% | 100% | 77% | 50% | 49% |
| **4** | 100% | 100% | **78%** | **70%** | 48% |
| 5 | 100% | 100% | 85% | 59% | 51% |

**Two pitching rows were forcing a single route.** With only two rows the pitching totals are nearly
determined by those rows, so any pitching cell forces a crossing — cross-team was universal, and a
family every board demands distinguishes nothing. At four it sits at 78% and the global identity
rises from 50% to 70%: **both land in the range where they separate boards.**

That is a structural cause for §31's character-axis collapse, which had been chased across several
measurements and written off as half dead. The variety was never absent; the board shape was hiding
it.

*Global peaks at four and falls back to 59% at five — a third independent reason the knee is there.*

---

## Rendered: does a four-pitcher board read as noise?

`boards.html`, erased by the real algorithm at chain 11, `row_first`, viewed at 375px. Built by
`render_boards.py`, which is the **flat, no-JavaScript** renderer — judging a board needs it whole.
The interactive prototype in `board-prototype/` answers a different question, what the player can see
at once, and both are kept; the comparison is in that folder's README.

**The premise inverts.** The worry was four pitching rows of two or three visible cells each. What
the erasure actually produces:

| Board | Pitching cells left visible |
|---|---|
| 1954, four rows | 17 of 24 — **71%** |
| 1964, four rows | 18 of 24 — 75% |
| 1974, four rows | 19 of 24 — 79% |
| 1913, two rows | 7 of 12 — **58%** |

**More pitching rows means fewer blanks per row, not more.** `row_first` round-robins across rows, so
a board with more rows spreads the same erasure budget thinner. The four-row section reads *denser*
than the two-row one.

What does change is proportion rather than clutter: at four rows the pitching half carries the visual
weight of a third of the lineup, so the board reads as two comparable sections instead of a lineup
with an appendix. That is a judgement about what the board should look like, not a legibility
problem — nothing crowds, nothing truncates, and the section is about 190px of a 812px screen.

## Rendered: is a high resolution p90 good or bad?

Two boards at the same chain length, at opposite ends of the resolution distribution (which runs 5 to
11 across the sample, median 8).

**High resolution is roster size wearing a metric's name, and what it buys is arithmetic.** The
p90-of-11 board is a 2003 game with thirteen batting rows: its hardest step is *add eleven known
numbers in the PA column and subtract from 44*. The p90-of-5 board is a 1944 game with ten rows,
where a step combines about five.

That is the +0.45 correlation between batting rows and resolution already recorded in §31, seen
rather than computed. **More numbers per step is not more deduction — it is more addition.** The
board is no harder to reason about; it is longer to arrive at.

**Recommendation, for the operator to decide:** treat resolution p90 as something to keep *low or
bounded* rather than to maximise, and if it becomes a generator target, target it as a ceiling. The
direction was genuinely not obvious from the number alone.
