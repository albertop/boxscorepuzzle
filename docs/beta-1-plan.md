# The route to beta 1

**The chart map.** `beta-1.md` says what beta 1 *is* and what counts as done; this says **how to get
there from here**, in groups and subtasks, with what each one depends on and what makes it finished.

Written 2026-08-26, against the repository as it actually stands rather than as the documents describe
it. ⚠️ Where the two differ, this file says so.

---

## Where it stands — last checked **2026-08-26**

| | | |
|---|---|---|
| **A** the width | ⬜ **not started** | owed since beta 0, and it is the first thing |
| **B** the input model | ⬜ **not started** | the keyboard replaces the keypad |
| **C** the wide screen | ⛔ **blocked** | on three decisions that are the operator's |
| **D** every screen reachable | ⬜ **not started** | landing, tutorial, reference, reveal, share |
| **E** the evidence | ⬜ **not started** | the statement about `engine/` |

⚠️ **A is first and B can run beside it.** C cannot start until the three questions in `beta-1.md` are
answered, and D depends on C. E is written at the end and is not a formality — see the deliverable.

---

## ⚠️⚠️ What the survey already found, before any of this is built

**Three things were checked in the tree rather than assumed, and all three are good news.**

**The engine has no input model to change.** `clock.js` listens for `keydown`, and only as an *activity*
signal for the pause. Every decision about what a key means lives in `ui/phone/`: `renderKeypad` and
`applyKey` in `board.js`, and the cells' own Enter/Space in `board.js`. **`game.js` already exposes
`enter`, `clear`, `blanks` and `cells`** — everything a keyboard needs is a method that exists.

**The board has almost no responsive machinery**, which is a clean slate rather than a problem. There is
exactly one layout media query in the whole product: `board.css:189`, `max-width: 359px`, for narrow
phones. Nothing else branches on width.

**And `max-width: 375px` is spelled three times**: `board.css:74`, `board.css:603`, `landing.css:18`. The
other seven appearances of `375` are prose in comments, which is where the reasoning belongs.

---

## Group A — the width becomes one value

**Blocks everything, and it is owed.** `docs/beta-0.md` recorded it and deliberately left it: *the fix is
a token and a test; it is not beta 0 work, but beta 1 is the milestone that edits exactly this, and
finding out then that three files disagree is the expensive order.*

- ⬜ **A1.** One token in `tokens.css`, with the §6 reasoning beside it: 375 minus 2×8 margin is 359, six
  data columns at 44.8, a 66px label, a 24px slot. The number is a **presentation** constant, so it lives
  in `serve/ui/phone/tokens.css` and never in `boxscore_domain` — §33 is exactly the boundary a shared
  one would break.
- ⬜ **A2.** The three call sites read the token.
- ⬜ **A3.** A browser test asserting the board's rendered width **at a desktop viewport**, not by reading
  the stylesheet. ⚠️ `docs/beta-0.md` measured this once by hand at 1400×900 and found it correct; what
  it recorded is that **nothing guards it**.
- **Done when:** the value appears once, and a test fails if the board stretches.

⚠️ **Do this before any desktop layout exists.** A width that disagrees with itself is cheap to find now
and expensive to find inside a layout built on top of it.

---

## Group B — the input model

**A physical keyboard is the reason desktop comes before tablet** (`beta-0.md`), so this is the group
that earns the milestone rather than merely widening it.

- ⬜ **B1.** Digits type into the selected cell. `game.enter` already exists; what does not is the
  decision about what a **second** digit does — replace, or append to make a two-digit number.
  ⚠️ **Board values run past 9** — a totals row reads 29, 31 — so this is not a keypad with a keyboard
  attached, and the answer cannot be assumed from the phone.
- ⬜ **B2.** Arrows move the selection. ⚠️ **Over every cell, or only over blanks?** A board is mostly
  given cells, and arrowing through them is arrowing through things that cannot be typed into.
- ⬜ **B3.** Backspace and Delete clear. Escape deselects. Enter checks, or does not — **`Check` is a
  commitment**, and a keystroke away from it is a different product than a button away from it.
- ⬜ **B4.** The keypad is **not rendered** where there is a keyboard. `beta-0.md`'s own argument applies:
  a control that does nothing occupies a third of the screen.
  ⚠️ **A laptop with a touchscreen is both**, so the honest detection is *has a fine pointer* rather than
  *is wide*.
- ⬜ **B5.** ⚠️⚠️ **`applyKey` is the one place that must not fork.** Two paths into `game.enter` — one
  from a key, one from a button — is this project's most-recorded defect. The keyboard calls what the
  keypad calls.
- **Done when:** a board is solvable with the keyboard alone, asserted by a browser test that types.

---

## ⛔ Group C — the wide screen

**Blocked on `beta-1.md`'s three open questions, and they are the operator's.** They are not written here
as tasks because writing an answer would be inventing a product decision (§7).

| | the question | what it changes |
|---|---|---|
| **C-i** | what a desktop screen shows beside the board | §6 settles the *board* and says nothing about what surrounds it. The C9 slots are the obvious candidate, and *none during play* is already the rule there |
| **C-ii** | whether the mouse is first-class or a fallback | a keyboard-first board that can also be clicked, and a board with two equal input models, are different things to build and to test |
| **C-iii** | where the breakpoint is, or whether there is one | the product has exactly one layout media query today |

⚠️⚠️ **§6 is what this group is most likely to break by accident**, because everything it forbids becomes
cheap the moment the screen is wide: **six data columns, the same board on every screen, more whitespace
rather than more content.** A seventh column does not appear on desktop. The constraints were never only
about width.

---

## Group D — every screen reachable

**Not rebuilt, reached.** Everything beta 0 has must work on the new interface.

- ⬜ **D1.** Landing, tutorial, reference sheet, check, reveal, share, persistence, the event record.
- ⬜ **D2.** ⚠️ **The share image is 375px wide and that is deliberate** — it is a printed artefact that
  travels to other people's phones, and it must not become a desktop screenshot. `share-image.js` draws
  with the board's own renderers, so a desktop layout could silently change what gets shared.
  **A test that rasterises at a desktop viewport and asserts the image is still the phone board.**
- ⬜ **D3.** The reveal is a printed boxscore. It has more room now, and §6's *whitespace, not content*
  applies to it too.
- **Done when:** every route in `ROUTES` works at a desktop viewport, photographed.

---

## ▶ Group E — the evidence, which is half the deliverable

- ⬜ **E1.** The statement: **`engine/` was not touched**, or an account of exactly what had to change
  there and why the brief was wrong.
- ⬜ **E2.** ⚠️ **A guard, so the claim survives the milestone.** Something that fails if a desktop-only
  concern reaches `engine/`. The survey above says the seam is clean today, which makes now the cheapest
  moment to fence it.
- **Done when:** the claim is written, with the diff behind it.

⚠️⚠️ **Both outcomes are acceptable and only one is currently believed.** A desktop build that has to
reach into the engine is `serve-brief.md`'s central claim failing, and it will say so. **The architecture
becomes checkable exactly once** — after beta 1 the engine has been shaped by two interfaces and the
question can no longer be asked cleanly.

---

## ▶ Deliverable

**A desktop board somebody can play with a keyboard, and a statement about `engine/`.**

⚠️ **What it does not include:** tablet, and anything that begins *while we are in there*. Each milestone
has its successor named so nothing drifts into the wrong one (`beta-0.md`), and the failure that prevents
is the ordinary one — a tablet or subscription concern arriving during beta 1 and being fixed *there*,
because fixing it is small and the milestone boundary is invisible from inside the work.
