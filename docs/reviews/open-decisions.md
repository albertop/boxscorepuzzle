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
| Batting-order constraint | **Not adopted.** Built as an opt-in fallback, publication fenced off by three guards. Steps 1 and 2 of the agreed plan, then frozen. |
| Conditional retry | Tries the ordinary path first; only a board that misses its target sees the constraint. |
| `LINEUP_DIVISION_SHARE_CAP` | `0.20`, `PROVISIONAL`, origin recorded as *two boards, not a measurement*. |
| Verifier's lineup step | **Not written.** This is the gate: layer 3 cannot replay a `batting_order` move, so no fallback board can publish. |
| Weak solver (v28-P2-01) | Fixed. It treated every inequality as an upper bound and invented values. |
| Discovery footnote renderer (v28-P2-03) | Now a third consumer of the canonical vectors. |
| Inning cap | **12**, in `MAX_INNINGS`, with the 11px rule below 359px. |
| Provenance loader (v28-P2-02) | Fixed: preconditions before connecting, a shrink guard, and a staging table swapped under a transaction. |
| Half-inning marker | Raised from 2.21:1 to 4.51:1. |

---

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
- **Where `MAX_INNINGS` is enforced.** It is recorded but `eligibility()` does not filter on it, so the
  generator could still produce a 16-inning board. ⚠️ The inning count is **not** `LEN()` of the line
  score: Retrosheet writes a ten-run inning as `(10)`.
- **No `.github/`** — no CI, no coverage floor on push, no branch protection, and ruff's
  `extend-include` claims `discovery/` is linted while nothing points ruff at it (194 findings never
  reported).
- **The hand-solve pack** is with the operator; the key is unopened and the five rendered pages are
  byte-identical to the committed ones.
