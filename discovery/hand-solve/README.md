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

---

## ⚠️⚠️ What is tracked here, what is ignored, and why they are opposite

Two kinds of artefact live in this directory and the rule for each is the reverse of the other. Both
are enforced by `forge/tests/test_hand_solve_keys_are_ignored.py` rather than by this paragraph.

| | | |
|---|---|---|
| `*key.csv` | **ignored, never committed** | it maps board → game, and the boards only measure anything if they are met blind |
| `pack-a-difficulty.csv` | **tracked, must stay tracked** | it is the answers *out*, not the answers *in* |

**The results file is safe to track precisely because the key is not.** Its columns are
`board,how_hard,solved,had_to_guess` — a board number and three verdicts. Without the key it names no
game, no season, no team and no cell, so committing it discloses nothing that would spoil a future
solve.

⚠️⚠️ **And it must not be swept up by a broader rule.** `.gitignore` names `discovery/hand-solve/*key.csv`
and not `*.csv`, and the difference is load-bearing: sixteen boards solved by a person is the one thing
in this directory that **no process can regenerate**. The packs rebuild from the inventory, the PDFs
rebuild from the packs, the keys rebuild with them — the verdicts exist once. `CLAUDE.md` §33 names the
laptop as the single point of failure and the repository as the backup, and this is the same argument
that keeps `docs/calendar.md` in Git while every generated package stays out of it.

⚠️ **It sat untracked and unignored for a day** and was found by comparing two `git status` outputs by
eye. The ignore rule for the keys was three hand-maintained lines at the time and `fifty-key.csv` had
never been added to them, so the same afternoon produced both halves of the failure: a key one
`git add -A` from being disclosed, and a finding one disk failure from being lost. Neither was
detectable by anything the repository ran.
