# What is decided, what is open — 20 August 2026, 12:40

**Written because the conversation view is not a reliable record.** The operator reported his client
showing text from an earlier session rather than the last few hours. The repository is intact and was
checked: 258 commits, the last eight covering exactly the arc from the mutation sweep to the inning
cap, timestamped 09:24 to 12:21. Nothing was lost and nothing was redone — `MAX_INNINGS` and the line
score's media query appear in one commit, `90e8210`, and did not exist before it.

This file exists so the state does not live only in a chat window. It is a snapshot, not a plan;
`todo.md` remains the standing record.

---

## Decided today

| | |
|---|---|
| Batting-order constraint | ⚠️ **SUPERSEDED on 20 August — ADOPTED.** See below. |
| Conditional retry | Tries the ordinary path first; only a board that misses its target sees the constraint. |
| `LINEUP_DIVISION_SHARE_CAP` | `0.20`, `PROVISIONAL`, origin recorded as *two boards, not a measurement*. |
| Verifier's lineup step | ⚠️ **SUPERSEDED — written.** `lineup_values()`, independent and value-aware. |
| Weak solver (v28-P2-01) | Fixed. It treated every inequality as an upper bound and invented values. |
| Discovery footnote renderer (v28-P2-03) | Now a third consumer of the canonical vectors. |
| Inning cap | **12**, in `MAX_INNINGS`, with the 11px rule below 359px. |
| Provenance loader (v28-P2-02) | Fixed: preconditions before connecting, a shrink guard, and a staging table swapped under a transaction. |
| Half-inning marker | Raised from 2.21:1 to 4.51:1. |

---

## ⚠⚠ SUPERSEDING: the batting order is ADOPTED (20 August 2026)

**This file said the opposite for one commit after production started building through the fallback**
— v29-P3-01. Two rows above recorded the constraint and the verifier step as not adopted while
`write_reference_puzzles.py` called one and `boxscore_verify` contained the other. **A document named
for open decisions saying a settled one is open is worse than silence**, because it reads as current.

The rows are struck rather than deleted, and this is the current statement:

| | |
|---|---|
| The constraint | **Adopted.** Production erases through `erase_with_lineup_fallback`. |
| The retry | Conditional. Boards reaching their target plain never see it. |
| The verifier | `lineup_values()`, independent of the generator, value-aware. **All five layers read the lineup.** |
| The pool rule | `_check_batting_order()` rejects a distribution the cycle cannot produce — 35 in 371,802. |
| §8 | Teaches five equation families. The batting order gets the clearest explanation, because it is the one that cannot be read off a board. |

**What decided it is not a measurement.** The operator solved the five hand-solve boards with the
constraint active and reported that it makes them harder — not because it resolves more cells, but
because the player must hold one more rule in their head. Recorded in `batting-order-reversal.md` as a
human verdict rather than a measured quantity.

⚠️ **Still open: the confirmation run.** Every figure that decided this was measured while the
verifier had no lineup step, so the numbers describe what the generator produces rather than what can
ship. `discovery/batting-order/confirm.py` is pre-registered and committed before running.

## Decided since this file was written

### The inning cap is 12, with the type-size exception, and both were decided together

The operator's reading, recorded because it is the reasoning and not just the outcome: **the
identical-board rule is about content** — same cells erased, same data, same puzzle. A different type
size on a narrow screen changes none of that, and the line score is read-only, so it is the one element
that can shrink without touching a touch target. Dropping to eleven to preserve a uniformity nobody
would perceive costs a real baseball game that fits.

⚠️ **Twelve does need the exception**, which an earlier reading had assumed away: at 320px, twelve at
13px leaves 2.7px between a two-digit R and H. Eleven is the largest count that needs none (4.0px).
Both stylesheets now state that rather than implying it.

### The `x` is fixed, and one of the two proposed remedies did not exist

Raised to **4.51:1**, the same brightness as a played digit, distinguished by weight and by being a
letter among numerals. Two browser guards, both checked by reintroducing the old rule.

⚠⚠ **"A grey that reaches 4.5:1" is not available on this ground.** Against `--fenway`, **pure black
reaches only 4.27:1**, so nothing darker than the panel can pass at all; a neutral grey must be
`#f5f5f5` or brighter, which is the digit's own brightness. `--scoreboard-dim` at full opacity still
only reaches 2.95:1. The first remedy was the only one that existed.

⚠️ **And the marker was not the only thing below the floor.** The **inning header numbers** carry the
same token and render at **2.95:1** — under both floors, on twelve-odd cells rather than one, and they
are what tells the player which inning a column is. **Still open**, because it is a decision about the
panel's colour. There is a clean one: darken `--fenway` to 75% of itself, `rgb(62,90,81)`. Today's dim
colour then reaches 4.52:1 and the values 6.91:1 — the whole hierarchy survives, everything above the
floor, one token. If that is taken, the `x` can go back to the dim colour and recover its original
visual intent.

## Still open from before

- **Layer 3b figures are void** and need re-running once the hand-solve pack is done — including the
  33% certified reported for the pack. They came from the predicate fixed in `a73bbc1`.
- **No `.github/`** — no CI, no coverage floor on push, no branch protection, and ruff's
  `extend-include` claims `discovery/` is linted while nothing points ruff at it (194 findings never
  reported).
- **The hand-solve pack** is with the operator; the key is unopened and the five rendered pages are
  byte-identical to the committed ones.
