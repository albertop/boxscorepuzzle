# The fifty boards — a launch gate, and an experiment

Built by `build_pack.py`. Four files:

| File | What it is |
|---|---|
| `boards.pdf` | Fifty puzzles, one per page, printable. **Open this one.** |
| `solutions.pdf` | The same fifty completed, in the same page order. After solving, not during. |
| `key.csv` | Which board was which. **Do not open until every board is finished.** |
| `recording-sheet.csv` | One row per board, to fill in as you go. |

## Why it is a gate rather than a review step

§22 promoted this from sanity check to requirement. Two reasons:

1. **It is the only real verification of human derivability that exists.** Layer 3 of the verifier
   certifies that a propagator holding forty-odd relations at once needs no guess. Nobody solves like
   that.
2. **It is the only check the common-author risk does not touch.** The verifier shares no code with
   the generator, but the same author wrote both, so a misreading of §3 would be made twice and agree
   with itself. It would not survive somebody solving the board.

## The experiment inside it

Layer 3b is a deliberately weak solver — one relation in view at a time, never carrying a narrowed
range from one relation to the next. **29% of Saturday boards fail it.** A player sits somewhere
between the two solvers and nothing automated says where.

So **17 of these fifty come from the uncertified 29%**, randomly interleaved and unmarked:

- solved with no more difficulty than the rest → **3b is too conservative** and stays a reported
  property
- stuck systematically on them → **3b becomes a gate** on publication

That only works if the boards are met blind. Nothing on a page names the game, the date, the teams,
the chain target, the difficulty or the certification status; the board reference is a sequential
number and encodes nothing.

## What the fifty contain

| | |
|---|---|
| Chain 5 / 7 / 9 / 11 / 13 | 5 / 7 / 9 / 13 / 16 — every rung, weighted to the hard end |
| Uncertified by layer 3b | 17 |
| Pre-1950 | 2, respecting §5's 5% calendar quota |
| With a suffixed label (`LF-2`) | 33 |
| With a live footnote | 33 |
| Distinct games | 50 — no lineup appears twice |

## Recording: three different things, recorded separately

Only the first bears on layer 3b. The other two bear on the quality criterion and the weekly curve,
and conflating them would lose both answers.

| Column | Means |
|---|---|
| **underivable** | Could not find the next move by reasoning. Had to guess, or gave up. |
| **tedious** | Solvable but unpleasant — too much arithmetic, or too much scanning. |
| **boring** | Solvable and easy, with nothing to think about. |

`got_stuck_where` matters as much as the flags: a board that stalled at one cell and then opened is a
different animal from one that stalled everywhere. Note the cell if you can.

**A board solved by guessing counts as underivable even if the guess was right.** That is the failure
§22 calls the worst, and it does not announce itself — it feels like solving.
