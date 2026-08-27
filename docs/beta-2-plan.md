# The route to beta 2

**Five groups, A to E, against the repository as it actually stands on 2026-08-26.**
`docs/beta-2.md` is what done means; **this file is the authority on progress.**

`§N` points at `docs/design-boxscore-puzzle.md`.

---

## Where it stands — last checked **2026-08-26**

| | | |
|---|---|---|
| **A** the device that is both | ⬜ open | the controls are chosen at boot and the hardware changes after it |
| **B** the measurement | ✔ **done 2026-08-26** | portrait already fits; landscape scrolls by 366 / 290 / 86 px |
| **C** the keypad beside the board | ⬜ open | **blocked on one decision, not on code** — see the arithmetic |
| **D** every screen reachable, and the share | ⬜ open | the share has never been sent from a tablet |
| **E** the evidence | ⬜ open | **not the beta 1 claim** — this one is §6 |

⚠️ **B is done before the milestone opened, on purpose.** Beta 1's deliverable had to be rewritten
because the work was scoped before it was measured. Here the measurement came first and it is what
shapes C.

---

## ⚠️⚠️ What the measurement already found, before any of this is built

`/today` rendered in a **touch** context (`is_mobile`, `has_touch`, scale 2) at eight real tablet
viewports, both orientations, plus the two iPadOS multitasking widths. Every number below is measured.

| | visible | content | short by | air each side |
|---|---|---|---|---|
| iPad mini portrait 744×1133 | 821 | 821 | **fits** | 185 |
| iPad 10.9 portrait 820×1180 | 868 | 868 | **fits** | 223 |
| iPad Pro 12.9 portrait 1024×1366 | 1054 | 1054 | **fits** | 325 |
| Split View 507×1180 | 868 | 868 | **fits** | 66 |
| Slide Over 320×1180 | 875 | 875 | **fits** | 0 |
| **iPad mini landscape 1133×744** | 432 | 798 | **366** | 379 |
| **iPad 10.9 landscape 1180×820** | 508 | 798 | **290** | 403 |
| **iPad Pro 12.9 landscape 1366×1024** | 712 | 798 | **86** | 496 |

**`#app` is 375 wide in every row**, and nothing scrolls sideways anywhere — beta 1's finding holding on
a touch profile it was never run against. The keypad renders in all eight, which is correct: these are
touch devices and `(pointer: fine) and (hover: hover)` is false for all of them.

### ⚠️⚠️ The chrome is a constant, so C is arithmetic rather than opinion

**744 − 432 = 312. 820 − 508 = 312. 1024 − 712 = 312.** The furniture above and below the scrolling
board is the same on all three: **keypad 156, footer 61, and 95 of header and margins.**

So moving the keypad out of the vertical stack gives the board back **exactly 156 pixels**, and the
result is not a judgement call:

| landscape | short by now | short by after the move |
|---|---|---|
| iPad Pro 12.9 | 86 | **fits** — 868 against 798 |
| iPad 10.9 | 290 | still **134** |
| iPad mini | 366 | still **210** |

⚠️⚠️ **This is the whole reason C is blocked on a decision and not on code.** The brief promises *the
whole board fits without scrolling*; the move delivers that promise **on one of the three iPads**. On the
other two it helps and does not keep it. **Building it and reporting the promise met would be true of
the 12.9 and false of the device most people own.**

⚠️ **And a remedy that closes part of a gap is confirmed by the same evidence as one that closes it** —
this register's hardest shape. A screenshot of a 12.9 in landscape with no scrollbar would look exactly
like success.

---

## ⬜ Group A — the device that is both

**The first group because it is a defect, not a layout**, and because it is the only thing in this
milestone that can lose a player's input.

- ⬜ **A1.** `shell.js` chooses `renderKeypad` or `renderTypedControls` from
  `app.classList.contains(POINTED)` **once, at boot**. `followPointer` already watches and already keeps
  the class current, so the CSS re-lays on attach and detach today. **The controls do not.**
- ⬜ **A2.** Detaching a keyboard mid-game leaves **no pad and no keyboard**: the player cannot enter a
  number until they reload. Attaching leaves a redundant pad, which is harmless. **Both directions are
  in scope; only one is urgent.**
- ⬜ **A3.** The swap must not disturb the game. Nothing about which cell is selected, what is typed, the
  clock, or the C7 record may change because a keyboard was attached. ⚠️ **The clock is the trap**: §27
  accumulates only while the page is visible, and a hardware change is not a visibility change.
- ⚠️ **A4 — the seam this group must not cross.** Beta 1 proved everything deciding what a key means
  lives in `ui/phone/`. **A live swap that reaches into `engine/` is this milestone falsifying beta 1's
  result**, and the diff says so either way.
- **Met by:** a browser test that boots with a coarse pointer, swaps the matcher to fine and back, and
  asserts the game is still enterable **after each swap** — the pad present, then the typed controls,
  then the pad again — with the selection and the entered values intact across both.

⚠️ **Seen red by removing the swap**, not by reading it: the test must fail on today's code.

---

## ✔ Group B — the measurement, **done 2026-08-26**

Above. Three things it establishes and one it deliberately does not:

- ✔ **B1.** The board already fits without scrolling in **portrait** on every iPad, and in both iPadOS
  multitasking widths. **There is nothing to build for portrait.**
- ✔ **B2.** It scrolls in **landscape** on all three, by 366, 290 and 86 pixels.
- ✔ **B3.** The chrome is a constant 312 px, so the keypad's 156 is exactly what a move recovers.
- ⬜ **B4 — NOT established: whether a scrolling landscape board is a defect at all.** §6 pins the header
  and the totals row *during scroll*, which is a design for scrolling rather than an admission of it.
  **The operator decides**, and C waits on it.

⚠️ **The measurement is one puzzle's board.** Content height is a function of roster size — ≤13 batters
and ≤6 pitchers (§6) — so 798 is this board, not the worst board. **A worst-case pass is owed before any
number here is treated as a bound**, and it is C's first step rather than B's, because it only matters
if C runs.

---

## ⬜ Group C — the keypad beside the board

**Blocked on B4. Not blocked on anything technical.**

- ⬜ **C1.** Re-run B against the **tallest board the caps allow**, not one puzzle. Nothing below is
  worth sizing against a number that is not a bound.
- ⬜ **C2.** The keypad moves beside the board where the air exists — measured at 379 to 496 px per
  side in landscape, against a 375 px board. **A layout decision about the space around the board, never
  about the board.**
- ⬜ **C3.** ⚠️⚠️ **It is a class on `#app`, never a bare media query.** The reason is beta 1's and it
  has not weakened: `share-image.js` lays the sheet out in the real document to measure it and then draws
  it inside an SVG with its own 375 px viewport, so a media query is evaluated **twice against two
  different widths**. Measured on 2026-08-26: a probe rule made the shared PNG a third taller with the
  boxscore small at the top and blank paper below, and it does not even look broken because the
  background stretches. `forge/tests/test_the_share_image_is_not_the_screen.py` is what fails if a wide
  rule reaches the PNG.
- ⬜ **C4.** ⚠️ **`--wide-from` is still undeclared and declaring it is the whole of turning the
  machinery on.** `wide.js` refuses a token it cannot parse rather than guessing, and it matches the
  pixel pattern whole — `parseInt("48em")` is 48, finite, positive and wrong. **Whatever number goes
  there comes from C1, not from a device list**: an iPad mini in landscape is 1133 px and a desktop at
  1133 px is the same layout problem.
- ⬜ **C5.** The board does not change. Same six columns, same 66 px label, same 375 px width, same
  row heights. **This is E's subject and it is stated here because C is where it would be broken.**

---

## ⬜ Group D — every screen reachable, and the share

- ⬜ **D1.** Landing, tutorial, reference sheet, board, check, reveal, share, and a restored session —
  reached on a tablet profile in **both orientations**, and **photographed**. ⚠️ *A screenshot is not a
  slower text dump*: both of the reveal's defects were obvious in the first picture and invisible in
  every number produced before it.
- ⬜ **D2.** ⚠️⚠️ **The share, from a tablet.** G3 closed by sending the PNG from a **real phone**
  through WhatsApp, iMessage and X, and the share is the only growth mechanism the product has. The
  sheet is measured in the live document before being drawn into a 375 px SVG — so the device holding it
  participates in the measurement, and no tablet has ever done that.
- ⬜ **D3.** `canShare` and the clipboard fallback on iPadOS Safari. ⚠️ The clipboard branch calls
  `clipboard.write()` **synchronously with a promise-backed `ClipboardItem`** to keep the click
  activation (v42-P2-03); Safari is where that rule came from and where it is worth re-checking.
- ⬜ **D4.** The reveal's printed boxscore at tablet widths. ⚠️ It is the one surface where an instrument
  already lied: numeric checks said no clipped cell and no overflow, both true, while a text dump padded
  its own columns and the real page rendered `40 1` as forty-and-one.

---

## ⬜ Group E — the evidence, which is half the deliverable

**Beta 1's claim is settled and is not re-asked.** `engine/` changed by one comment across six commits,
and `forge/tests/test_the_engine_knows_nothing_about_screens.py` fences the seam.

**Beta 2's claim is §6**, and it is checked differently because it is a different kind of statement:

> **The board is identical on all screens. A tablet gets a different arrangement around it, never
> different content in it.**

- ⬜ **E1.** The diff touches `ui/phone/` and `tokens.css`. ⚠️ **`engine/` untouched is necessary and no
  longer interesting** — it was beta 1's test and it passed. *A necessary condition asserted where a
  sufficient one is needed is this register's near-neighbour class*, and quoting beta 1's evidence here
  would be exactly that.
- ⬜ **E2.** A guard that the tablet layout adds **no column, no row and no cell**: the set of
  `data-cell` names rendered at a tablet viewport equals the set at 375 px, for the same package.
  ⚠️ **Asserted over the set, never over a count** — a count is satisfied by a swap.
- ⬜ **E3.** Seen red by adding a seventh column behind the tablet class.
- ⬜ **E4.** The share image is byte-comparable before and after. ⚠️ The phone was verified byte-identical
  at SHA `774f21add9596173` across all of beta 1's desktop work, and the same evidence is owed here.

---

## ⬜ Deliverable

**Beta 2 is met when a person can play a whole board on a tablet, in both orientations, attach and
detach a keyboard in the middle of it without losing their place, share the result to a real
conversation, and the board they played is the same board a phone gets.**

⚠️⚠️ **And when the deliverable says what the measurement found rather than what this file expected.**
Beta 1's was rewritten before it was marked and beta 0's Deliverable B before that. **The rewrite is the
normal ending, not the exception** — if B4 is decided as *landscape scrolling is fine*, then C is
*build nothing* and this deliverable says so, in those words, before anybody ticks it.

---

## ⚠️ What this milestone must not quietly become

- **A second board.** §6, and E exists to catch it.
- **A media query.** C3, and the share image is what pays for it.
- **A device list.** `(pointer: fine) and (hover: hover)` asks what the person is pointing with. A rule
  keyed to iPad widths is wrong the day a 1133 px laptop opens the site — and *a justification is
  scoped, and it does not travel*.
- **Beta 3.** Stripe, accounts, subscriptions, `canAccess()`, the archive.
