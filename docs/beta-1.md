# Beta 1 — desktop

**The second milestone. Opened 2026-08-24, the day beta 0 was met.**

**One puzzle, a second interface.** `docs/serve-brief.md` says *one puzzle and three interfaces, a core
that knows nothing about screens*. Beta 0 built the first interface and the core underneath it. **Beta 1
is the first time that claim can be false.**

**The route there: `docs/beta-1-plan.md`.** Five groups, A to E, against the repository as it
actually stands. **It is the authority on progress; this file is what done means.**

`§N` points at `docs/design-boxscore-puzzle.md`.

---

## ⚠️⚠️ The claim this milestone tests, and how it fails

> **If the engine is really screen-agnostic, beta 1 touches `ui/` and nothing under `engine/`.**

**That is not a style rule; it is the falsification test for the whole architecture.** A desktop build
that has to reach into `engine/` is the brief failing, and it will say so in the diff.

⚠️ **So the diff is the deliverable's evidence.** When this milestone is marked, the statement that
closes it is *`engine/` was not touched*, or an account of exactly what had to change there and why the
brief was wrong. **Either is an acceptable outcome and only one of them is the one currently believed.**

---

## Why desktop before tablet

**Operator's decision, 2026-08-22**, and the reasoning is recorded in `docs/beta-0.md` rather than
re-derived here. The short version:

**A physical keyboard is a different and better interaction.** Digits and arrow keys rather than a custom
keypad, so desktop is not the phone board on a bigger screen — it is the one platform where the input
model genuinely improves.

**And tablet has the fewest unique users of the three**, since whoever has one generally also has a phone
and a computer.

---

## ⚠️⚠️ What is already decided, and must not be re-opened here

**§6 is not up for negotiation on a bigger screen.** It is the rule this milestone is most likely to
break by accident, because everything it forbids becomes cheap the moment the screen is wide.

| | |
|---|---|
| **six data columns** | `PA AB R H BB SO` batting, `IP H R ER BB SO` pitching. **A seventh does not appear on desktop.** The column set is what makes the puzzle the puzzle, not what fits |
| **the board is identical on all screens** | *Desktop gets more whitespace, not more content* (§6). A desktop board showing anything the phone board does not is a different puzzle |
| **no names during play** | §7. Rows are positions until the reveal, on every screen |
| **the line score is complete and read-only** | It is the anchor |
| **footnotes are given** | v39-P3-01, settled by measurement. Not reopened because there is room |

⚠️ **The failure this list prevents is the ordinary one**: a decision made for the phone gets quietly
relaxed on desktop because the constraint that produced it — 375px — is not present. **The constraints
were never only about width.**

---

## What beta 1 is

⬜ **The board, playable with a keyboard**, at desktop widths, with the same six columns and the same
rules.

⬜ **The keypad's replacement.** Digits type; arrows move; something clears a cell; something checks. The
phone's on-screen keypad has no reason to exist where there is a keyboard, and leaving it there is the
phone board on a bigger screen.

⬜ **Everything beta 0 has, on the new interface**: landing, tutorial, reference sheet, check, reveal,
share, persistence, the event record. Not rebuilt — reached.

---

## ⚠️ What is open and is the operator's

**Deliberately unanswered here.** Writing an answer would be inventing a product decision, which §7
forbids, and this file is the place the absence should be visible rather than a section that quietly
reads as decided.

- ⬜ **What a desktop screen shows beside the board.** §6 says more whitespace rather than more content,
  which settles the *board* and says nothing about what surrounds it. The reserved slots of C9 are the
  obvious candidate and *none during play* is already the rule there.
- ⬜ **Whether the mouse is a first-class input or a fallback.** A keyboard-first board that can also be
  clicked and a board with two equal input models are different products to build and to test.
- ⬜ **Where the breakpoint is**, and whether there is one at all. See the width note below — the number
  that exists today is spelled three times and asserted nowhere.

---

## ⚠️⚠️ The first task, because it is owed and it is load-bearing

**`max-width: 375px` is spelled three times and tested nowhere** — `board.css:74`, `board.css:599` and
`landing.css:18`. `docs/beta-0.md` recorded it and deliberately left it: *the fix is a token and a test;
it is not beta 0 work, but beta 1 is the milestone that edits exactly this, and finding out then that
three files disagree is the expensive order.*

**This is that milestone.** The width every §6 column argument rests on is three copies with nothing
checking they agree, and beta 1 is the work that changes it. **It is the first thing to close, before any
desktop layout exists to be confused by it.** `docs/reviews/todo.md` carries the entry.

---

## ▶ Deliverable

**A desktop board somebody can play with a keyboard, and a statement about `engine/`.**

The second half is not a formality. **The architecture's central claim becomes checkable exactly once**,
and this is it — after beta 1 the engine has been shaped by two interfaces and the question can no longer
be asked cleanly.

---

## The beta sequence

| | |
|---|---|
| **Beta 0** | ✔ **met 2026-08-24** — the free daily, complete, on the VPS |
| **Beta 1** | ▶ **open** — desktop |
| **Beta 2** | tablet |
| **Beta 3** | Stripe, accounts, subscription |

⚠️ **Each milestone has its successor named so nothing drifts into the wrong one.** The failure this
prevents: a tablet or subscription concern arriving during beta 1 and being fixed *there*, because fixing
it is small and the milestone boundary is invisible from inside the work.
