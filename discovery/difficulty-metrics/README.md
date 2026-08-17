# What makes a board hard, and what makes a boxscore worth using

Two measurements that answer different questions and must not be conflated.

- `measure.py` — under random erasure, what shape does the solution path take? Compares boards to
  each other under the same treatment. Feeds §4 and §31.
- `compressibility.py` — for one boxscore, how far can it be compressed at all? Orders candidate
  directions against each other. Feeds §5.

Both run read-only against `DGL`, stratified by decade, from `forge/`:

```powershell
$env:PYTHONPATH = "../discovery/difficulty-metrics"; uv run python ../discovery/difficulty-metrics/measure.py
```

## Headline results, August 2026

**Difficulty separates into three dimensions, not one scale.** Effort (chain length, frontier width
and cell count, which correlate at r ≈ 0.7 and are one variable with three names), character (which
equation families a path needed, which varies widely at every effort level), and attention (whether a
live footnote is present, which is a property of the direction rather than of the erasure).

**Boards compress much further than assumed** — median 58.6% of the grid, against the 25–35% that had
been invented. Flat across decades.

**§5's prefilter assumption is inverted.** Zero density predicts compressibility at r = +0.79 and
digit range at r = −0.70, so screening for compressibility selects the zero-heavy low-scoring games
§5 wanted to exclude. Compressibility measures how much can be removed, not whether what remains is
worth solving.

## What was chosen rather than derived

- **Greedy with restarts, not exhaustive search.** Finding a true maximum is combinatorial. The
  search erases a random still-given cell, keeps it if the board still solves, and stops when nothing
  more can go; five restarts, best kept. That finds a *maximal* set, not a *maximum* one, so every
  compressibility figure is a **lower bound**. Chosen because a quality filter needs a defensible
  floor, and a direction that clears the bar on a lower bound clears it.
- **Sample of 10 or 35 directions per decade.** Enough for distributions, not enough for tails.
- **Erasure restricted to the grid.** The line score is the board's anchor and the footnotes are
  given, so neither is ever erased.
- **Frontier width ignores the last three steps.** A solve narrows by exhaustion as it runs out of
  cells; trimming one step leaves 43% of boards reporting a bottleneck of one, trimming three leaves
  10% and the distribution comes out smooth.

## Caveats

- The 3-step trim means boards solved in three steps or fewer report no frontier at all. That is
  intended — they never offered a choice — but it removes the easiest boards from that statistic.
- Random erasure is not what the real algorithm will do, so §31's figures compare boards rather than
  predicting the eventual pool.
- Search cost is 4.6 seconds per direction, 70 hours across the whole pool. Feasible as a batch,
  not as something to run casually.
