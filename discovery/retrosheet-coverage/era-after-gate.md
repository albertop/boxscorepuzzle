# The era the zero-density gate leaves behind

Run date: 2026-08-17. Source: `DGL` on `LocalServer`. Script: `era_after_gate.ps1`.

> **These counts still include 1,872 Negro Leagues games**, found and excluded after this run (§32).
> They sit entirely in 1913–1961, so they inflate the pre-1950 share the run is about. The script now
> excludes them through `dbo.retroGameProvenance`; the numbers below are pending a re-run and will
> move by under a percent.

§5 left this open: the earlier era measurement was taken *before* the quality filter, and the note
that stood in the design document predicted the distribution would drift forward on its own, because
zero density selects against low-scoring games and those cluster in the dead-ball era.

**The prediction was backwards.** The gate removes proportionally more modern boards than old ones.

## Why the earlier numbers do not carry over

Two things changed at once. The caps are now **≤13 batters and ≤2 pitchers** rather than the
provisional ≤10/≤3, and the pool is measured whole rather than sampled.

Loosening the batter cap admits bench rows — a pinch hitter with one plate appearance contributes a
row that is five-sixths noughts — so the zero-density distribution moved up by about five points.
Every threshold now keeps less than the sampled run said it would.

| | Sampled, old caps | Whole pool, decided caps |
|---|---:|---:|
| median zero density | 34.5% | **40.0%** |
| kept below 30% | 26.7% | **10.9%** |
| kept below 35% | 56.7% | 26.5% |

## The funnel from the roster caps onwards

| Step | Directions |
|---|---:|
| Roster fits the board (≤13 batters, ≤2 pitchers) | 128,766 |
| Minus discrepancies against official data in board columns | 113,974 |
| **Minus the zero-density gate at 30%** | **12,456** |
| *(at 35%)* | *30,226* |
| *(at 40%)* | *53,088* |

12,456 directions is **18.5 years of calendar** at the 674 a year the week consumes. The pool is not
the problem.

## The era distribution

| Decade | After caps | Below 30% | Survives | Share before | Share after |
|---|---:|---:|---:|---:|---:|
| 1910s | 20,717 | 4,367 | 21.1% | 16.1% | **26.8%** |
| 1920s | 15,897 | 3,177 | 20.0% | 12.4% | 19.5% |
| 1930s | 15,974 | 3,088 | 19.3% | 12.4% | 19.0% |
| 1940s | 13,774 | 2,133 | 15.5% | 10.7% | 13.1% |
| 1950s | 9,676 | 1,169 | 12.1% | 7.5% | 7.2% |
| 1960s | 10,625 | 795 | 7.5% | 8.3% | 4.9% |
| 1970s | 14,684 | 819 | 5.6% | 11.4% | 5.0% |
| 1980s | 11,934 | 398 | 3.3% | 9.3% | 2.4% |
| 1990s | 7,042 | 192 | 2.7% | 5.5% | 1.2% |
| 2000s | 4,632 | 96 | 2.1% | 3.6% | 0.6% |
| 2010s | 3,057 | 50 | 1.6% | 2.4% | 0.3% |
| 2020s | 754 | 12 | 1.6% | 0.6% | 0.1% |

Mean zero density rises monotonically with the decades, from **0.367 in the 1910s to 0.475 in the
2020s**. Survival through the gate falls from 21.1% to 1.6%.

**Pre-1950 is 78% of what ships. Post-1980 is 4.6%.** The two filters compound rather than cancel:
the ≤2 pitcher cap already selects complete games, which modern baseball hardly produces, and the
gate then takes the low-scoring remainder of what is left.

## What this does and does not decide

It does not threaten the pool — 18.5 years of calendar is far more than the five-month forward
inventory §33 requires.

It bears on the progressive reveal (§7). A puzzle whose final screen names a 1913 lineup is a
different product from one that names a 2015 lineup, and the calendar will be built almost entirely
from the former unless something changes. **Not decided.** Levers, in ascending cost:

1. **Stratify the calendar by era deliberately** — ration the thin decades instead of letting the
   pool's shape decide. Costs nothing but calendar-builder complexity.
2. **Raise the gate to 35%** — 30,226 directions, 44.8 years, but three-run boards come back and the
   gate exists to remove them.
3. **Loosen the pitcher cap towards 3** — buys the modern era directly, at the price of a batting row
   on a 320px screen (§6).

## Verification

The zero density is computed in SQL rather than by loading each board, so it was checked against the
board's own definition (`compressibility.proxies`) on twelve directions, one per decade. Every pair
agreed to the sixth decimal place.
