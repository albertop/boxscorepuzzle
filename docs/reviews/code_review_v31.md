# Code Review v31

**Date:** 2026-08-20  
**Mode:** solo-developer review  
**Result:** two retained P3 findings; the original P2 is retracted

## Scope and method

This is a fresh pass over the current tree, built on the full-tree v30 baseline. Every source and
normative-document change made after the last v30 pass was read, with priority given to the new phone
completion flow, its browser tests, the batting-order confirmation, and the updated project contracts.
`_not_in_use`, generated caches, and scenarios requiring a second developer or a hostile actor remain
out of scope.

No tests or linters were run. This is a static review, as required by the operator's validation
contract.

## Findings

### v31-P2-01 — RETRACTED: this is a test-improvement opportunity, not a demonstrated bug

**Locations:** `serve/tests/engine.test.js:1652`, `serve/tests/engine.test.js:1654`

The helper comment overstates what the test does: it assembles the game and UI components rather than
booting `main.js`. That is inaccurate test documentation, but the review did not demonstrate a broken
completion flow. Requiring dependency injection and a new shell harness solely to close that gap would
be disproportionate for this project. The component tests remain useful; the comment can be corrected
when the file is next touched. No product fix or test refactor is required by this review.

### v31-P3-01 — The finished-cell cursor rule is unreachable

**Locations:** `serve/ui/phone/board.css:322`, `serve/ui/phone/board.css:523`,
`serve/ui/phone/main.js:167`

Every `.cell` receives `cursor: pointer`. The stylesheet attempts to remove that input affordance with
`.app-finished td.cell`, but no changed code adds `app-finished`; the only completion-related class the
shell adds is `solved`, and it is added when the reveal opens. After the player closes the reveal, the
cells correctly have no role, tab stop, or listener, but a mouse still presents them as clickable.

This does not corrupt the game and is minor on a touch-only phone, so it is P3. It is still a real
desktop/PWA inconsistency, and the adjacent comment states the opposite of the rendered behavior.

**Required correction:** apply one canonical finished-state class when the game finishes and when a
finished session restores, or derive the cursor rule from a state/class the shell already applies.
Add the assertion to the real-shell test requested by v31-P2-01.

### v31-P3-02 — The normative GitHub contract still requires infrastructure this repository cannot use

**Locations:** `docs/python-conventions.md:439`, `docs/python-conventions.md:541`,
`.githooks/pre-push:2`

The updated conventions still require branch protection on `main`, a red CI that blocks merge, and a
pre-commit gate. The repository's actual local gate documents that branch protection and rulesets are
unavailable for this permanently private repository on the current plan, and implements a manually
enabled pre-push hook instead. These are mutually exclusive instructions about the solo developer's
normal workflow.

The mismatch does not make a build fail, but it makes the normative document prescribe a state the
operator cannot reach and hides which check is actually load-bearing.

**Required correction:** make `python-conventions.md` state the current arrangement: CI runs but is not
a required server-side check; `.githooks/pre-push` is the local substitute and must be enabled; and
`--no-verify` remains an acknowledged escape hatch rather than protection. Describe a pre-commit hook
only if one actually exists.

## Known open findings carried forward

These are not renumbered as v31 findings:

- **v30-P1-01 is retracted.** The remaining causal question is useful research, not a demonstrated
  code or product defect.
- **v30-P1-02 is retracted.** It wrongly required row-level proof for the reveal-only half that was not
  part of the puzzle; aggregate corroboration is proportionate and no verifier expansion is owed.
- **v30-P3-02 remains open.** `run_browser_tests.py` still writes `window.__fatal` while waiting only
  for `window.__results`, so a known page failure waits the full timeout.

## Disposition

No new P0, P1, or P2 product defect was found in the changed code. The component-level completion
behavior is internally coherent, and the batting-order edit does not introduce a new defect. Two small
P3 code/document contracts still disagree with reality.
