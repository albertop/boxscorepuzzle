# Board topology: how interconnected each candidate column set is

Produces the numbers §4 and §6 of the design document cite. Run date: 2026-08-17.

The question is not how big the board is but how tangled its constraint graph is. A graph where
every cell sits in exactly one equation has no middle difficulty: one blank per equation is a
subtraction, and two blanks in one equation are usually ambiguous rather than hard, so validation
throws them away. The generator is then pushed back to trivial puzzles by the correctness rules
themselves.

## Results

| Board | Max overlap | Cells in 2+ equations | Independent cycles |
|---|---:|---:|---:|
| A — current: `AB R H RBI BB K` | 1 | 10 of 85 | **0** |
| B — `PA AB R H BB K`, footnotes per team | 1 | 35 of 85 | 16 |
| C — `PA AB R H BB K`, footnotes per player | 1 | 38 of 121 | 18 |
| D — `PA AB R H BB RBI`, footnotes per player | 1 | 36 of 121 | 18 |

Share of random erasures a T1/T2 solver finishes, 4,000 draws per cell count:

| Cells erased | A | B | C | D |
|---:|---:|---:|---:|---:|
| 2 | 87.5% | 93.8% | 96.4% | 96.2% |
| 4 | 39.7% | 69.3% | 80.2% | 80.1% |
| 6 | 8.3% | 43.4% | 57.0% | 57.3% |
| 8 | 0.3% | 20.6% | 35.3% | 34.1% |
| 10 | 0.0% | 7.9% | 17.2% | 15.4% |

## What the numbers say

**The 2×2 rung is closed, permanently.** Maximum overlap is one cell on every board tried. Every
identity in this system is a sum over a row or over a column, so two of them can share at most the
single cell where a row crosses a column, never the two a 2×2 needs. That is a property of the
constraint family, not of the column choice.

**The interconnection measure that does move is the cyclomatic number**, 0 → 16. Any test guarding
this property should assert on that, not on overlap.

**Board D is the control** for whether RBI is the right column to drop. Dropping strikeouts instead
scores the same, but strikeouts carry one of only four cross-team links, and §3 identifies that
cross as the part without which the puzzle degenerates into row arithmetic. RBI carries none.

## Caveats

- Built on one real direction, the Cubs at Braves 1968 game used as the forge's fixture. The
  topology follows from the shape rather than the values, but the survival percentages are for a
  9-batter, 2-pitcher board and will differ on other shapes.
- The T1/T2 solver here is a small standalone one, not the forge's. That is deliberate for a
  throwaway comparison, but the numbers should be reproduced against the real solver before the
  column set is treated as settled.
- Erasures are drawn uniformly from the batting half. A real erasure algorithm will not be uniform,
  so these are a comparison between boards rather than a prediction of the eventual pool.

## Reproducing

```powershell
uv run python ../../forge/../discovery/board-topology/compare_column_sets.py
```

Run it from `forge/` so the environment is on the path; it imports nothing from the package.
