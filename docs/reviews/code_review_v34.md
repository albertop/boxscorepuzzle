# Code review v34

**Date:** 2026-08-20  
**Mode:** Full-source review, not a delta review  
**Result:** One finding, `v34-P2-01`, now closed; no new findings in the correction review

## Scope

This pass reviewed the active project as if it were new rather than limiting the review to recent changes:

- The product and engineering contracts in the root and `docs/`, followed by a duplicate check against `docs/reviews/todo.md` and the previous review records.
- All active Python under `forge/src` and `forge/scripts`, including generation, erasure, solving, package parsing, signing, certification, publication, and the independent verifier.
- The complete browser application under `serve/engine` and `serve/ui`, including package boundaries, game state, persistence, timing, input, completion, reveal, styles, and localization.
- The Python and browser test sources, including expected failures and the boundary/property coverage they claim.
- Active discovery Python, PowerShell, and generated-page source, with particular attention to SQL parameterization, provenance loading, source filtering, HTML escaping, and historical measurement scripts.
- Operational source and configuration: `compose.yaml`, CI, project configuration, and the scripts in `tools/`.

Generated puzzle data, rendered measurement output, caches, virtual environments, and `_not_in_use` material were not treated as active source.

No tests, linters, type checks, containers, database queries, or publication commands were run during this review. The result is based on static inspection, as required by the review workflow.

## Findings

### v34-P2-01: the modal overlays leave keyboard focus behind them and can be stacked

**Status:** ✅ **Closed 2026-08-20.** Accepted in full and fixed as proposed — the shell owns one modal
boundary, `present()` and `dismiss()`; the renderers keep the panel's content and no longer wire their
own close, because a `panel.remove()` inside a renderer can close the panel and nothing else: it cannot
un-inert what the shell hid, cannot restore focus the shell moved, and cannot know a panel is open.

⚠️ **The finding was exactly right, and worth restating in this project's own terms:** `aria-modal="true"`
is a *claim* to assistive technology that every surface behind the panel is unavailable, and nothing was
making it true. The accessibility tree and the DOM described different screens with nothing checking
that they agree — two places that should say the same thing, saying different things, wearing an ARIA
attribute.

**Two further defects surfaced while building the coverage the finding asked for, and neither would
have been found by reading the change.**

⚠️⚠️ **The browser harness rendered nothing.** `serve/tests/index.html` held the board in a `hidden`
container, so `getClientRects()` returned zero boxes and **no element inside it could take focus** —
`focus()` silently did nothing and `document.activeElement` stayed on `<body>`. The focus assertions
this finding requires were not expressible. The board renders off-screen now. ⚠️ Two colour tests were
toggling `hidden` off for their duration and restoring it to a **hardcoded `true`**, which put the page
back to `display: none` for everything that ran after them — a second copy of the page's initial state,
and the copy won. Removed; nothing needs revealing now.

⚠️⚠️ **`equal()` could not compare DOM nodes and said nothing about it.** It compares `JSON.stringify`
output, and every DOM node stringifies to `{}` — so `equal(document.activeElement, opener)` compared
`"{}"` with `"{}"` and **could never fail**. One of the new tests was written that way and passed
against a build with the focus restoration deleted. It was caught by the mutation run showing the wrong
test go red, not by reading either file. `equal()` now refuses nodes and names the trap; the call sites
use `assert(a === b)`.

**Verified by mutation, six runs:** removing the focus move, the single-panel guard, the `inert` loop,
the focus restoration and the Escape handler each turns the matching test red, and a control run with no
change at all stays green. ⚠️ **The control earned its place**: the first mutation harness reported
CAUGHT for all five *and* for the control, because a nested `uv run` resolved an environment without
Chromium. Five confirmations and no control is five confirmations of nothing.

**188 browser tests pass** (183 before, 5 added), 1014 Python tests, ruff clean, ratchet at zero.

**Correction review, 2026-08-21:** Independently inspected the implemented lifecycle and its regression
coverage. The fix satisfies the original finding without introducing a second modal state: `present()`
owns insertion and the single-panel guard, `dismiss()` owns removal and restoration, every pre-existing
application child is inert while the panel is present, both renderers leave close wiring to the shell,
and the automatic reveal returns to the replacement **See the boxscore** control because **Check** no
longer exists. The tests cover the reference opener, repeated activation, Close, Escape, the removed
Check opener, and the DOM-node comparison trap in the harness. **No new issue was found.** This review
did not rerun the suites; the execution counts above are the developer's recorded verification.

**Priority:** P2  
**Locations:** `serve/ui/phone/shell.js:172`, `serve/ui/phone/shell.js:258`, `serve/ui/phone/finish.js:92`, `serve/ui/phone/finish.js:160`, `serve/ui/phone/finish.js:392`, `serve/ui/phone/finish.js:423`

Both the completed boxscore and the relations reference identify themselves as modal dialogs with `role="dialog"` and `aria-modal="true"`. Their open paths only append the returned panel, however, and their close handlers only remove it. Nothing moves focus into the dialog, prevents the obscured board controls from receiving focus, limits the application to one active panel, or restores focus to the opener when the panel closes.

This is reachable through an intended, already-supported input path:

1. Use the keyboard or switch-control path to focus **The relations** or **See the boxscore**.
2. Press Enter. The full-screen panel appears, but focus remains on the opener behind it.
3. Press Enter again. The still-focused hidden control appends a second modal panel.
4. Closing one panel removes only that instance; another panel remains, while normal tab traversal can still reach controls behind the object represented to assistive technology as modal.

The solve path has the complementary failure: the focused **Check** button is removed before the reveal is appended, but no destination receives focus. A keyboard or screen-reader user therefore reaches the payoff screen without a reliable announcement or a defined starting control. This is not a speculative browser or deployment edge case; it is the keyboard/accessibility route the board explicitly implements for editable cells.

**Impact:** The visual overlay and the accessibility tree disagree about which surface is active. Keyboard, switch-control, and screen-reader users can operate hidden controls, create duplicate overlays, lose their place when closing a panel, or fail to be placed in the completed boxscore at the moment it opens.

**Proportional fix:** Give the shell one modal-opening boundary used by both panels. It should refuse or replace a second active panel, remember the opener, move focus to the dialog heading or close button after insertion, keep background controls out of the focus order while open, support Escape, and restore focus to the opener on close. The renderers can remain responsible for panel content; lifecycle and focus belong to the shell that appends them.

**Regression coverage:** Drive both openers through their real click/keyboard handlers and assert `document.activeElement` moves inside the panel, background controls are unavailable while it is open, a repeated activation cannot append a second dialog, Escape/Close removes the panel, and focus returns to the original trigger. Include the automatic reveal after **Check**, whose opener is removed during completion.

## Areas with no new finding

### Forge and package boundary

Generation is deterministic, the lineup fallback remains conditional, publication calls the complete certification gate, packages are checked again after a disk round-trip, and publication commits through the signed manifest after a complete staging batch. Package and manifest signatures cover the published data, including the solution and reveal. No new integrity, identity, or fail-open defect was found.

### Verifier and source correspondence

The independent verifier remains separate from generator reasoning, all certification checks are registered, absent evidence fails closed, and the current aggregate checks for the printed half outside the puzzle match the explicitly accepted scope. This review does not reopen row-level validation of the half that was not played as a puzzle.

### Discovery and provenance tooling

The active provenance rebuild validates its input before opening a transaction, loads with parameters into staging, checks the staged population, and swaps atomically. The postseason source checker retains the corrected empty-set and unexpected-source branches. Older measurement scripts are historical instruments rather than publication paths, and their retired thresholds were not reported as product bugs.

### Browser engine

Package parsing, session validation, fail-soft storage, accumulated timing, finished-session sealing, keypad rules, hint accounting, and the boxscore reveal have direct regression coverage. The retained `hinted` marker after clearing a cell was examined but not filed: the hint remains historically spent, and an empty cell has no text for the hint-color rule to affect. The imprecise test title alone does not establish player impact.

### Docker and operations

`compose.yaml` is explicitly a laptop development environment. Its official Python image, read-only source mounts, no-cache development server, and LAN bind are consistent with that purpose. A production image, nginx policy, health check, runtime signature acceptance step, and VPS hardening are explicitly deferred to the VPS deployment work in `todo.md`; reporting their absence as defects in this development Compose file would duplicate a scheduled product boundary rather than identify a current bug.

### Tests

The single strict `xfail` records that no unique-but-underivable example has been found and states the research boundary directly. It is not a skipped production regression. No other skip/expected-failure mechanism was found that turns a required product assertion into a passing result.

## Priority summary

| Priority | New findings | Open |
|---|---:|---:|
| P0 | 0 | 0 |
| P1 | 0 | 0 |
| P2 | 1 | **0** |
| P3 | 0 | 0 |
