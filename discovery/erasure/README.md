# What the erasure algorithm actually produces

Run date: 2026-08-17. Script: `measure_erasure.py`. Results: `results.txt` (gated pool, the real one)
and `results-ungated.txt` (kept as the contrast, see below).

Four orderings exist in `erasure.py` because three of them were guesses. This measures them against
the three numbers that describe a solution path — chain length, search cost and resolution p90 — over
72 directions stratified across every decade, four orderings × three seeds = 864 runs.

**Method.** One greedy pass per (direction, ordering, seed), snapshotting every accepted state,
rather than one `erase` call per target. `erase` is prefix-greedy and deterministic, so a single pass
answers every target at once. That is a shortcut, so it is checked rather than assumed: across 5
directions × 4 orderings × 6 targets it agrees with the real function on all 120, with no mismatches.

---

## ⚠️ Measure on the gated pool or the ceiling is fiction

The first run sampled the whole pool. The zero-density gate keeps 11% of it (§5), so that sample was
nine parts boards that will never ship — and zeros are exactly what makes a board compressible, since
a column summing to nothing forces every blank in it.

| | Ungated pool | **Gated pool (§5)** |
|---|---:|---:|
| ceiling, max chain p50 | 39 | **23** |
| cells erased at the ceiling | 54 | **40** |
| runs reaching chain 20 | 90% | **64–73%** |

**The ungated run overstated the ceiling by 70%.** A chain of 20 looked like a comfortable
mid-difficulty ask; on boards that will actually ship it is close to the top of the range and about a
third of candidates cannot reach it. This is the same error as measuring at the compressibility
ceiling, in a new place: the sample was not the population.

Everything below is the gated pool.

---

## Ordering: it barely matters, and `column_first` is the one to drop

| ordering | cells for chain 5 | trivial share | reach at chain 20 | ceiling |
|---|---:|---:|---:|---:|
| **row_first** | 13 | **12%** | 66% | 23 |
| mirrored | 13 | 19% | **73%** | 24 |
| random | 14 | 20% | 69% | 23 |
| column_first | 15 | 19% | 64% | 22 |

The four are within a couple of points of each other nearly everywhere, and the ceiling is the same
for all of them. Two differences survive:

**`row_first` produces the least padded easy board.** At a chain target of 5 it fills 12% of the path
with trivial steps against 19–20% for the others. Whether that is desirable is a product judgement,
not a measurement: an easy Monday may *want* free cells to build momentum.

**`column_first` is last or joint-last on every axis** — most cells erased, lowest ceiling, worst
reach — and it overshoots, returning chain 6 when asked for 5. The hypothesis behind it was that
spreading blanks across columns avoids the ambiguous case; it buys nothing.

The reach differences at chain 20 (64% to 73%) are about 1.5 standard errors apart on this sample.
**Not decisive.** What is solid is that no ordering beats `random` by enough to matter, and that
`column_first` never wins.

### A confound worth naming

Search cost rises with how empty the board is. At a fixed chain target, an ordering that needed more
erasures scores "harder" for free — `column_first` reads 0.67 where `row_first` reads 0.50 at chain
8, and the difference is the extra cells, not better structure. This is the same bias that killed
`live/solvable` as a metric. **Comparing orderings by search cost at fixed chain compares how many
cells each one had to remove.**

## Symmetry: real, and free

`mirrored` produces **72.9%** of erased batting cells paired with their mirror, against a **42.9%**
baseline that coincidence produces under `random`. It does what it claims.

And it costs nothing measurable: same ceiling, same cell count as `row_first`, the best reach at hard
targets of the four. **Symmetry is available as a pure aesthetic choice** if the board ever wants it.

## Targeting: resolution is a separate lever, search is half of one

With the chain fixed, how much room is left in the other two:

| chain target | search p10–p90 | resolution p10–p90 | r(chain, search) | r(chain, resolution) |
|---:|---|---|---:|---:|
| 5 | 0.33–0.67 | 7–9 | +0.23 | −0.11 |
| 8 | 0.41–0.83 | 6–9 | +0.21 | −0.02 |
| 11 | 0.50–0.88 | 5–9 | +0.23 | −0.03 |
| 14 | 0.67–0.90 | 5–8 | +0.25 | +0.06 |
| 17 | 0.75–0.91 | 5–8 | +0.26 | +0.10 |
| 20 | 0.83–0.92 | 5–8 | +0.15 | −0.02 |

**Resolution p90 is independent of chain length** — |r| ≤ 0.11 at every target. Aiming at it buys
something aiming at chain does not.

**Search cost is weakly tied to chain and its band closes as the chain grows**, from 0.33–0.67 at
chain 5 to 0.83–0.92 at chain 20. On a hard board there is nothing left to target: the number fixes
itself.

### What a joint target costs

Asking for chain ≥ 11 *and* both other metrics above their medians (search ≥ 0.75, resolution ≥ 8):

| | Runs | Cost |
|---|---:|---:|
| chain ≥ 11 alone | 827 / 864 | 1.04× |
| all three | 346 / 864 | **2.39×** |

Against 12,218 gated directions that is **7.6 years of calendar** instead of 18.1. Affordable, and
measured at exactly one point — the medians of what chain-11 erasures produce. A stricter joint
target costs more and that is not measured here.

**What the data suggests, for the operator to decide:** target chain *and* resolution p90, and treat
search cost as a property that gets reported rather than pursued — it is nearly determined once the
chain is long. The thresholds themselves are a product decision (§7); nothing here sets them.

## Not measured

- Whether a lower trivial share makes a *better* easy puzzle, or a meaner one. Needs real solvers.
- Joint targets away from the median.
- Whether the ordering that suits an easy board suits a hard one — the sample is one algorithm run
  per (direction, ordering, seed), not a per-difficulty design.
