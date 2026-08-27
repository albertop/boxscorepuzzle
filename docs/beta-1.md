# Beta 1 — ✔ **MET 2026-08-26**

**The second milestone. Opened 2026-08-24, the day beta 0 was met, and closed two days later.**

⚠️⚠️ **What it turned out to be is the KEYBOARD, and that is smaller than this file was written to
promise.** It opened expecting a desktop layout. `/today` was then rendered at sixteen widths from 320 to
1920: from 414 up the board holds 375, no cell is clipped, nothing scrolls sideways, and every extra
pixel becomes air. **There was no layout to build** — §6's *desktop gets more whitespace, not more
content* was already in force. `docs/beta-1-plan.md`'s deliverable was rewritten to say that before it
was marked.

⚠️⚠️ **And the central claim survived the one milestone that could have falsified it.** Both beta 1
commits change `engine/` by **zero lines**, because `game.js` already exposed `enter`, `clear`, `blanks`
and `cells` and `grow` already concatenated — everything deciding what a key means already lived in
`ui/phone/`. A guard now fences that seam, and it says in its own file what it cannot see.

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

✔ **The board, playable with a keyboard**, at desktop widths, with the same six columns and the same
rules. ⚠️ **The board did not change** — sixteen widths from 320 to 1920 said there was no layout to
build, and §6 is what that is: the same board on every screen, the surplus becoming air.

✔ **The keypad's replacement — `3cc1ab1`.** Digits type; arrows walk blank cells only; Backspace and
Delete clear; Escape deselects; **Enter confirms and moves on rather than Checking**, because `Check`
records a failed attempt on the C7 record and one keystroke from a commitment is a commitment pressed by
accident. The pad is gone where there is a fine pointer and hover.

✔ **Everything beta 0 has, on the new interface**: landing, tutorial, reference sheet, check, reveal,
share, persistence, the event record. Not rebuilt — reached, and photographed at 1440.

---

## ⚠️ What is open and is the operator's

**Deliberately unanswered here.** Writing an answer would be inventing a product decision, which §7
forbids, and this file is the place the absence should be visible rather than a section that quietly
reads as decided.

- ⬜ **What a desktop screen shows beside the board.** §6 says more whitespace rather than more content,
  which settles the *board* and says nothing about what surrounds it. The reserved slots of C9 are the
  obvious candidate and *none during play* is already the rule there.
- ⚠️⚠️ **Whether the mouse is a first-class input or a fallback — still open, and the code has taken a
  position without a decision being made.** On a pointed device the pad is gone and the keyboard types,
  **but cells are still selected by clicking**, because `select()` was never touched. That is *keyboard
  for values, mouse for navigation*, which is a third answer neither of the two this line offers. It works
  and nobody chose it. **Left open on purpose rather than declared met**: writing it down as decided would
  be inventing a product decision (§7), and the honest state is that the implementation is ahead of the
  decision.
- ✔ **Where the breakpoint is — ANSWERED 2026-08-26, and the answer is that there is none.** `/today`
  was rendered at sixteen widths from 320 to 1920 and asked at each for `#app`'s box, the grid's box, the
  air either side, and whether any cell's text overflowed its own box. **From 414 up the board holds 375,
  nothing clips, nothing scrolls sideways, and every extra pixel becomes air** — which is §6 already in
  force. So there is no number to put in `--wide-from`, and inventing one would be the forbidden parameter
  (§7): a value that shapes the product and came from nobody's measurement.
  ⚠️ **The machinery stays and the token stays undeclared**, because the question can be reopened and
  because a class is what makes a media query refusable — `wide.js` carries the table.

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
