# The route to beta 1

**The chart map.** `beta-1.md` says what beta 1 *is* and what counts as done; this says **how to get
there from here**, in groups and subtasks, with what each one depends on and what makes it finished.

Written 2026-08-26, against the repository as it actually stands rather than as the documents describe
it. ⚠️ Where the two differ, this file says so.

---

## Where it stands — last checked **2026-08-26**

| | | |
|---|---|---|
| **A** the width | ✔ **met 2026-08-26** | `--board-width`, three readers, and a test at desktop viewport |
| **B** the input model | ▶ **B1-B3, B5 met 2026-08-26** | digits, arrows, Enter, and one path to `game.enter`. ⬜ B4, the keypad, is not in this change |
| **C** the wide screen | ✔ **met 2026-08-26** | ⚠️ **and two of the three needed no code.** C-i is already true, C-ii is *build nothing*, and C-iii's answer is **there is no breakpoint** |
| **D** every screen reachable | ✔ **met 2026-08-26** | ⚠️ **the measurement closed most of it**: there is no new interface to reach. Photographed |
| **E** the evidence | ✔ **met 2026-08-26** | **`engine/` was not touched**, and a guard now fences the seam |

⚠️⚠️ **BETA 1 IS MET — 2026-08-26**, against the rewritten deliverable below. ⬜ **B4 is the one item
left open and it blocks nothing**: the keypad still renders where there is a keyboard, and its honest
detection is *has a fine pointer* rather than *is wide* — which is a decision, not an oversight.

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

- ✔ **A1.** One token in `tokens.css`, with the §6 reasoning beside it: 375 minus 2×8 margin is 359, six
  data columns at 44.8, a 66px label, a 24px slot. The number is a **presentation** constant, so it lives
  in `serve/ui/phone/tokens.css` and never in `boxscore_domain` — §33 is exactly the boundary a shared
  one would break.
- ✔ **A2.** `board.css:74`, `board.css:603` and `landing.css:18` read `var(--board-width)`.
- ✔ **A3.** A browser test asserting the board's rendered width **at a desktop viewport**, not by reading
  the stylesheet. ⚠️ `docs/beta-0.md` measured this once by hand at 1400×900 and found it correct; what
  it recorded is that **nothing guards it**.
- **Done when:** the value appears once, and a test fails if the board stretches.

⚠️ **Do this before any desktop layout exists.** A width that disagrees with itself is cheap to find now
and expensive to find inside a layout built on top of it.

---

## Group B — the input model

**A physical keyboard is the reason desktop comes before tablet** (`beta-0.md`), so this is the group
that earns the milestone rather than merely widening it.

- ✔ **B1.** Digits type into the selected cell, and **a second digit CONCATENATES** — the operator's
  decision, because board totals exceed nine and replacing puts 29 and 31 out of reach. ⚠️ **It needed no
  new rule**: `grow` already appended and capped at two digits for the pad, so the keyboard reaching the
  same `applyKey` is what makes one rule serve both. Moving on starts fresh because the next cell's value
  is what `grow` is handed.
- ✔ **B2.** Arrows walk **blank cells only**, wrapping at the end. ⚠️ `select()` already refused given
  cells, so arrowing over one would have landed on a cell that then refuses to be selected.
- ✔ **B3.** Backspace and Delete clear, Escape deselects, and **Enter does NOT Check** — it confirms and
  moves to the next blank. `Check` records a failed attempt on the C7 record, and one keystroke from a
  commitment is a commitment pressed by accident.
  ⚠️⚠️ **`select(null)` did nothing before this.** It fell out of `if (!game.isBlank(name)) return`, so
  Escape was decoration: the amber stayed and the next digit went back into the abandoned cell.
- ⬜ **B4.** The keypad is **not rendered** where there is a keyboard. `beta-0.md`'s own argument applies:
  a control that does nothing occupies a third of the screen.
  ⚠️ **A laptop with a touchscreen is both**, so the honest detection is *has a fine pointer* rather than
  *is wide*.
- ✔ **B5.** ⚠️⚠️ **`applyKey` does not fork.** Both the pad and the keyboard call one `press()` in the
  shell, which calls `applyKey`. Nothing in the keyboard decides what a digit *means*; it decides which
  key is a digit.
- ⬜ **B4** is not in this change. The keypad still renders everywhere.
- ✔ **Met by:** a browser test that arrows to every plain blank and types its answer, touching no button.

⚠️⚠️ **One of B's tests could not fail and was found by breaking the code.** *Enter does not Check* was
asserted on an EMPTY board by comparing `failed_checks` — and `check()` on an empty board records
nothing, so the assertion was true whether or not Enter ran one. It asserts on a **full** board now, and
the mutation that made Enter call `check()` turns it red. **A check that cannot fire is indistinguishable
from a broken one**, and this one was guarding the decision the operator named as the reason for the
rule.

---

## ✔ Group C — the wide screen, **met 2026-08-26**

**All three decided by the operator, and two of them needed no code at all.**

| | the decision | what it took |
|---|---|---|
| **C-i** | the board sits **centred with air on both sides, nothing beside it** | ⚠️ **already true.** `#app` has `max-width` and `margin: 0 auto`, so §6's *whitespace, not content* was in force before beta 1 opened. Contact and FAQ belong in a footer and neither page exists — that is content, not CSS |
| **C-ii** | the mouse is the **alternative**, not first class | **build nothing.** What desktop wins is the keyboard, and the mouse works because it already works |
| **C-iii** | the breakpoint is **measured, not chosen** | ⚠️⚠️ **measured, and there is not one** — see below |

### ⚠️⚠️ C-iii: the sweep says there is no breakpoint

`/today` was rendered at sixteen widths from 320 to 1920 and asked, at each, for `#app`'s box, the grid's
box, the air either side, whether any cell's text overflowed its own box, and whether the document
scrolled sideways.

| | 320 | 375 | 768 | 1440 | 1920 |
|---|---|---|---|---|---|
| `#app` | 320 | 375 | **375** | **375** | **375** |
| grid | 304 | 359 | **359** | **359** | **359** |
| air each side | 0 | 0 | 197 | 533 | 773 |
| clipped cells | 0 | 0 | **0** | **0** | **0** |
| sideways scroll | no | no | **no** | **no** | **no** |

**Nothing degrades at any width.** From 414 upwards the board holds 375 and every extra pixel becomes
air. **There is no width at which the board stops fitting**, so there is no number — and putting one here
anyway would be §7's forbidden parameter: a value that shapes the product and came from nobody's
measurement. `--wide-from` stays undeclared, and `wide.js` carries the sweep.

⚠️ **The machinery stays** because the question can be reopened and because it is what makes a media
query refusable at all — see the note below.

⚠️⚠️ **§6 is what this group is most likely to break by accident**, because everything it forbids becomes
cheap the moment the screen is wide: **six data columns, the same board on every screen, more whitespace
rather than more content.** A seventh column does not appear on desktop. The constraints were never only
about width.

---

## Group D — every screen reachable

**Not rebuilt, reached.** Everything beta 0 has must work on the new interface.

- ✔ **D1.** ⚠️⚠️ **There is no new interface to reach**, which is what C's measurement made of this
  group. The same 375px board on the same screen, with keys as well as buttons. **Photographed at 1440
  rather than deduced**: landing, tutorial, the finished board and the reveal each measure 375 wide with
  533px of air a side, no clipped cell, no sideways scroll.
  ⚠️ **The first probe reported 1440 for the tutorial** and it was the probe, not the page: the tutorial's
  root is `#tutorial`, which the selector list did not name, so it fell through to `document.body` — and
  body is always the viewport. An instrument answering about the wrong subject, one more time.
- ✔ **D2.** Built before group A, because it is what protected the width token while it moved.
  ⚠️ **The share image is 375px wide and that is deliberate** — it is a printed artefact that
  travels to other people's phones, and it must not become a desktop screenshot. `share-image.js` draws
  with the board's own renderers, so a desktop layout could silently change what gets shared.
  **A test that rasterises at a desktop viewport and asserts the image is still the phone board.**
- ✔ **D3.** ⚠️ **It does not have more room.** `.reveal-sheet` reads the same `--board-width`, so the same
  measurement that answered C-iii answers this: the boxscore is 375 wide at every viewport.
- ✔ **Met by:** every route photographed at 1440, with the box measured at each.

---

## ▶ Group E — the evidence, which is half the deliverable

- ✔ **E1. `engine/` was not touched.** Both beta 1 commits change it by **zero lines**:

  | | | |
  |---|---|---|
  | `25d7d7f` | beta 1 groups A, B and C | `engine/`: nothing |
  | `800c2f8` | wide layout is a class | `engine/`: nothing |

  ⚠️⚠️ **And the reason is concrete rather than lucky.** `game.js` already exposed `enter`, `clear`,
  `blanks` and `cells`; `grow` in `board.js` already concatenated and capped at two digits for the
  keypad. **Everything deciding what a key means already lived in `ui/phone/`**, so the keyboard had
  nothing to ask the engine for. The one `engine/` change of the week is `strings.js` in `438bc1f` —
  tutorial copy, which is beta 0.
- ✔ **E2.** `forge/tests/test_the_engine_knows_nothing_about_screens.py`. Seen red three ways: a viewport
  condition in `game.js`, a `matchMedia` in `game.js`, and the marker removed from `report.js`.
  ⚠️⚠️ **It is a list of terms and it says so.** It covers the vocabulary a screen is described with;
  it cannot see a screen concern expressed in words it does not know — a `columns` count, a boolean named
  `compact` — because *being about a screen* is intent, not text. **The residual is named in the file
  rather than left to read as the class being closed.**
  ⚠️ One line is exempt, marked **at the line**: `report.js` records the viewport into an error report,
  which is recording what the screen was rather than deciding because of it. Exempting by filename would
  have been the hand-maintained shape again, in a list nobody reading `report.js` would ever see.
- ✔ **Met.** The claim is written, with the diff behind it.

⚠️⚠️ **Both outcomes are acceptable and only one is currently believed.** A desktop build that has to
reach into the engine is `serve-brief.md`'s central claim failing, and it will say so. **The architecture
becomes checkable exactly once** — after beta 1 the engine has been shaped by two interfaces and the
question can no longer be asked cleanly.

---

## ▶ Deliverable — **rewritten 2026-08-26, to say what the measurement found**

**A board somebody can play with a keyboard, and a statement about `engine/`.**

⚠️⚠️ **It said *a desktop board* and there is no desktop board to build.** The old sentence promised a
wide-screen layout, and the measurement says there is none: **what beta 1 wins is the keyboard.** The
deliverable is rewritten before it is marked, for the same reason beta 0's Deliverable B was — marking
against a sentence the work does not support puts a false claim in the document that defines done.

### ⚠️⚠️ The measurement, here rather than in a footnote

**The next reader has to be able to see why there is no layout work, rather than assume it was skipped.**

`/today` was rendered at **sixteen widths from 320 to 1920** and asked, at each, for `#app`'s box, the
grid's box, the air either side, whether any cell's text overflowed its own box, and whether the document
scrolled sideways:

| | 320 | 375 | 414 | 768 | 1024 | 1440 | 1920 |
|---|---|---|---|---|---|---|---|
| `#app` | 320 | 375 | **375** | **375** | **375** | **375** | **375** |
| grid | 304 | 359 | **359** | **359** | **359** | **359** | **359** |
| air each side | 0 | 0 | 20 | 197 | 325 | 533 | 773 |
| clipped cells | 0 | 0 | **0** | **0** | **0** | **0** | **0** |
| sideways scroll | no | no | **no** | **no** | **no** | **no** | **no** |

**From 414 upwards the board holds 375 and every extra pixel becomes air. Nothing degrades anywhere.**

### What that made of C

| | |
|---|---|
| **C-1**, the board centred with air and nothing beside it | **needed no code.** `#app` has `max-width` and `margin: 0 auto`, so §6's *desktop gets more whitespace, not more content* was already in force before beta 1 opened |
| **C-2**, the mouse as the alternative | **needed no code.** It works because it works, and what desktop wins is the keyboard |
| **C-3**, the breakpoint | ⚠️⚠️ **has no answer.** There is no width at which the board stops fitting, so there is no breakpoint. `--wide-from` stays undeclared: **declaring a number that came from no measurement is what §7 forbids** |

⚠️ **`wide.js` stays even though nothing turns it on.** It is not the layout; it is what makes a media
query refusable — a wide rule written as one reaches the share image's measurement stage and a rule
scoped to `#app.wide` cannot. The sweep lives in its header so the next person to reach for `@media`
meets the reason first.

### What beta 1 actually is

**The keyboard**, and the width made into one value so the §6 arithmetic has a single premise. That is
smaller than the milestone was written to be and it is what the screen turned out to need.

⚠️ **What it does not include:** tablet, and anything that begins *while we are in there*. Each milestone
has its successor named so nothing drifts into the wrong one (`beta-0.md`), and the failure that prevents
is the ordinary one — a tablet or subscription concern arriving during beta 1 and being fixed *there*,
because fixing it is small and the milestone boundary is invisible from inside the work.
