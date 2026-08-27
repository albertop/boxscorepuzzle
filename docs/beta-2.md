# Beta 2 — the tablet

**The third milestone. Opened 2026-08-26, the day beta 1 was met.**

**One puzzle, a third interface.** `docs/serve-brief.md` §2 says what a tablet is meant to be, and it is
the only one of the three that promises something the phone does not have:

> **Tablet.** The whole board fits without scrolling. The keypad can sit *beside* the board instead of
> beneath it, which changes where the eye goes between entering a number and reading a total. There is
> room to keep the reference sheet open, where the phone has to fold it away.

**The route there: `docs/beta-2-plan.md`.** It is the authority on progress; this file is what done
means.

`§N` points at `docs/design-boxscore-puzzle.md`.

---

## ⚠️⚠️ The lesson beta 1 leaves, applied before anything is built

**Beta 1 opened expecting a desktop layout and there was none to build.** Sixteen widths said the board
holds 375 from 414 up, nothing clips, and every extra pixel becomes air — §6 already in force. The
deliverable was rewritten to say that *before* it was marked.

**So beta 2 opens by measuring, and the measurement is already done.** It is in
`docs/beta-2-plan.md` in full. The short version, and it is not what beta 1's was:

| | |
|---|---|
| **portrait** — mini, 10.9, 12.9, and iPadOS Split View | **the whole board already fits, with no scroll at all** |
| **landscape** — all three | **it scrolls**, short by 366, 290 and 86 pixels, while 379 to 496 pixels sit empty on *each* side |

⚠️⚠️ **That is the opposite finding to beta 1's and it is why this milestone is not a repeat.** Beta 1
measured and found nothing to build. Beta 2 measured and found **one specific thing**, in one specific
orientation, with a number attached: the board scrolls in landscape while the screen is mostly air.

⚠️ **And beta 1's sweep could not have found it, which is the methodological point.** It measured
**width, on a desktop profile**. The tablet promise is about **height**, on a **touch** device, in an
orientation the sweep never set. *An instrument can be correct and pointed at the wrong question.*

---

## The claim this milestone tests, and how it fails

Beta 1 tested *the engine knows nothing about screens* and it survived — six commits changed
`serve/engine/` by one comment. **That question is settled and beta 2 does not re-ask it.**

What beta 2 tests is the other half of the brief:

> **A tablet is additive. The board does not change; what is around it does.**

**It fails if the keypad beside the board requires the board itself to change** — a different column
count, a different label width, a different row height. §6 is unconditional: *six data columns maximum;
the board is identical on all screens; desktop gets more whitespace, not more content.* A tablet that
earns its layout by editing the board has broken the rule that makes one puzzle possible.

⚠️ **§6 is the rule most likely to break by accident here, and for a new reason.** On desktop everything
§6 forbids became cheap because the screen was wide. On a tablet it becomes *tempting*, because there is
a real layout to build for the first time and the board is sitting in the middle of it.

---

## ⚠️⚠️ The device that is BOTH, which is what a tablet actually is

**A tablet is the one device whose input model changes while the game is open.** An iPad with a keyboard
attached reports `pointer: fine` and `hover`; detached, it reports neither. **The player does that
mid-game**, and it is not an edge case — it is the hardware.

**Today the class follows and the controls do not.** `followPointer` toggles `.pointed` on `#app` live,
so the CSS re-lays correctly. But `shell.js` reads that class **once, at boot**, to decide between
`renderKeypad` and `renderTypedControls`.

⚠️ **The two directions are not equally bad.**

| | |
|---|---|
| keyboard **attached** mid-game | the keypad stays on screen. Harmless: it still works, it is just redundant |
| keyboard **detached** mid-game | **there is no keypad and no keyboard.** The player cannot enter a number until they reload |

**The second is a player losing their input on the device this milestone is named after.** It was
recorded as a deliberate non-finding in code review v43 — correctly, because on a phone or a desktop it
cannot happen. **On a tablet it is the normal path**, which is what moves it from a non-finding to
beta 2's first group.

---

## What beta 2 is

⬜ **The keypad beside the board where there is room for it**, so the board stops scrolling in the
orientation where it scrolls. `serve-brief.md`'s own reason is the one that matters: *it changes where
the eye goes between entering a number and reading a total.*

⬜ **The controls follow the hardware, not the boot.** Attach a keyboard and the pad may go; detach one
and the pad must come back. No reload.

⬜ **Everything beta 0 and beta 1 have, on a tablet**: landing, tutorial, reference sheet, check,
reveal, **share**, persistence, the event record. Not rebuilt — reached, and *photographed*.

⚠️ **The share is named separately because it is the only growth mechanism the product has.** G3 closed
by sending the image from a **real phone** through WhatsApp, iMessage and X. Nothing has ever sent it
from a tablet, and the sheet is measured in the live document before being drawn into a 375px SVG — a
measurement that happens on whatever device is holding it.

---

## What beta 2 is NOT

**Beta 3: Stripe, accounts, subscription, `canAccess()`, the archive endpoint.** Named here so nothing
drifts into the wrong milestone — the failure that naming prevents is a subscription concern arriving
during beta 2 and being fixed *there*, because fixing it is small and the boundary is invisible from
inside the work.

**Not a second board.** See the claim above.

**Not the reference sheet kept open.** `serve-brief.md` offers it as tablet room and it is a product
decision nobody has taken: whether a permanently visible reference changes what the puzzle asks. Left
open in this file rather than assumed into the plan.

---

## ⚠️ Open questions, deliberately unanswered here

**Writing an answer would be inventing a product decision (§7), and this file is where the absence
should be visible rather than a section that quietly reads as decided.**

- ⬜ **Whether "the whole board fits without scrolling" is a promise per orientation.** The measurement
  says portrait already keeps it and landscape cannot keep it on two of three iPads even after the
  keypad moves — short by 210 and 134 pixels. §6 *designs for* scrolling: the header and totals stay
  pinned precisely so a scrolling board is workable. So a scrolling landscape tablet may be acceptable
  rather than broken. **Nobody has decided, and the plan does not assume.**
- ⬜ **Whether the mouse is a first-class input or a fallback.** Carried forward from beta 1 unchanged,
  and a tablet is where it stops being theoretical: the same session has both. The code has taken a
  position nobody chose — keyboard for values, pointer for navigation.
- ⬜ **Whether the reference sheet stays open on a tablet.** Above.

---

## The beta sequence

| | |
|---|---|
| **Beta 0** | ✔ **met 2026-08-24** — the free daily, complete, on the VPS |
| **Beta 1** | ✔ **met 2026-08-26** — desktop, which turned out to be the keyboard |
| **Beta 2** | ▶ **open** — tablet |
| **Beta 3** | Stripe, accounts, subscription |
