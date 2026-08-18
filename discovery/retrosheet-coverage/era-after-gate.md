# The era the zero-density gate leaves behind

Run date: 2026-08-17. Source: `DGL` on `LocalServer`. Script: `era_after_gate.ps1`.

Deduced and Negro Leagues games are excluded through `dbo.retroGameProvenance`, which covers all
203,908 games with none missing.

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
| kept below 30% | 26.7% | **11.0%** |
| kept below 35% | 56.7% | 26.6% |

## The funnel from the roster caps onwards

| Step | Directions |
|---|---:|
| Roster fits the board (≤13 batters, ≤2 pitchers) | 125,625 |
| Minus discrepancies against official data in board columns | 110,833 |
| **Minus the zero-density gate at 30%** | **12,218** |
| *(at 35%)* | *29,532* |
| *(at 40%)* | *51,723* |

12,218 directions is **18.1 years of calendar** at the 674 a year the week consumes. The pool is not
the problem.

## The era distribution

| Decade | After caps | Below 30% | Survives | Share before | Share after |
|---|---:|---:|---:|---:|---:|
| 1910s | 20,698 | 4,365 | 21.1% | 16.5% | **27.2%** |
| 1920s | 15,732 | 3,130 | 19.9% | 12.5% | 19.5% |
| 1930s | 14,547 | 2,981 | 20.5% | 11.6% | 18.6% |
| 1940s | 12,244 | 2,051 | 16.8% | 9.8% | 12.8% |
| 1950s | 9,676 | 1,169 | 12.1% | 7.7% | 7.3% |
| 1960s | 10,625 | 795 | 7.5% | 8.5% | 5.0% |
| 1970s | 14,684 | 819 | 5.6% | 11.7% | 5.1% |
| 1980s | 11,934 | 398 | 3.3% | 9.5% | 2.5% |
| 1990s | 7,042 | 192 | 2.7% | 5.6% | 1.2% |
| 2000s | 4,632 | 96 | 2.1% | 3.7% | 0.6% |
| 2010s | 3,057 | 50 | 1.6% | 2.4% | 0.3% |
| 2020s | 754 | 12 | 1.6% | 0.6% | 0.1% |

Mean zero density rises with the decades, from **0.367 in the 1910s to 0.475 in the 2020s**, and
survival through the gate falls from 21.1% to 1.6%.

**Pre-1950 is 78% of what ships. Post-1980 is 4.7%.** The two filters compound rather than cancel:
the ≤2 pitcher cap already selects complete games, which modern baseball hardly produces, and the
gate then takes the low-scoring remainder of what is left.

## What this does and does not decide

It does not threaten the pool — 18.1 years of calendar is far more than the five-month forward
inventory §33 requires.

It bears on the progressive reveal (§7). A puzzle whose final screen names a 1913 lineup is a
different product from one that names a 2015 lineup, and the calendar will be built almost entirely
from the former unless something changes. **Not decided.** Levers, in ascending cost:

1. **Stratify the calendar by era deliberately** — ration the thin decades instead of letting the
   pool's shape decide. Costs nothing but calendar-builder complexity.
2. **Raise the gate to 35%** — 29,532 directions, 43.8 years, but three-run boards come back and the
   gate exists to remove them.
3. **Loosen the pitcher cap towards 3** — buys the modern era directly, at the price of a batting row
   on a 320px screen (§6).

## Verification

The zero density is computed in SQL rather than by loading each board, so it was checked against the
board's own definition (`compressibility.proxies`) on twelve directions, one per decade. Every pair
agreed to the sixth decimal place.
