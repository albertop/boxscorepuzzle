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
| Inning cap | **12**, in `MAX_INNINGS`. Implemented and uncommitted at the time of writing. |

---

## ⚠️ Open, and both are the operator's call

### 1. The inning cap and the type-size exception are one decision

The cap is 12. **At 320px that still needs the line score at 11px** — twelve at 13px leaves 2.7px
between a two-digit R and a two-digit H, which is where `11 16 2` starts reading as `1116 2`.

The reading that "at 12 the board looks the same at both widths, with no type-size exception" is not
what the measurement says. **Eleven** is the largest count that needs no exception: 4.0px at 13px on
320px.

| | cap | 320px | exception to "identical board" |
|---|---|---|---|
| as implemented | 12 | 11px type | yes — type size only, never content |
| the alternative | 11 | 13px type | none |

Pool cost is not the deciding factor either way: 12 costs 1,776 directions (0.89%), 11 costs 3,320
(1.66%). Both are under 2%.

### 2. The `x` marker has a real defect, and the cap does not fix it

⚠️ **The instruction that set the cap said the `x` clipped at 14 innings on 320px. It does not.** The
glyph is **5.1px in a 14.8px column** — a 9.8px margin against the digits' 2.9px. It is the roomiest
character on the board, and the constants module says so, because someone measuring digit widths later
would otherwise find the note there and be misled.

**But the concern behind it was right.** The `x` says the home side did not bat, which makes their outs
24 rather than 27 and feeds the global identity — a marker the player cannot read is a **lost given,
not a cosmetic flaw**. And it is hard to read:

| | contrast against the scoreboard ground |
|---|---|
| a played digit | 4.51:1 |
| the `x` | **2.21:1** |
| WCAG floor for any content | 3.0 |

`.linescore td.unplayed` sets a dim colour *and* `opacity: .7`. This happens at every inning count,
nine included, so the cap is unrelated to it. **Not changed**, because it is a colour decision.

---

## Still open from before

- **v28-P2-02** — the provenance loader drops and recreates its table with no non-empty precondition
  and no transaction. An empty zip directory replaces the canonical table with an empty one.
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
