# Code Review v31

**Date:** 2026-08-20  
**Mode:** solo-developer review  
**Result:** three new findings: one P2 and two P3

## Scope and method

This is a fresh pass over the current tree, built on the full-tree v30 baseline. Every source and
normative-document change made after the last v30 pass was read, with priority given to the new phone
completion flow, its browser tests, the batting-order confirmation, and the updated project contracts.
`_not_in_use`, generated caches, and scenarios requiring a second developer or a hostile actor remain
out of scope.

No tests or linters were run. This is a static review, as required by the operator's validation
contract.

## Findings

### v31-P2-01 — The completion suite says it boots the real shell, but never executes the shell

**Locations:** `serve/tests/engine.test.js:1652`, `serve/tests/engine.test.js:1654`,
`serve/ui/phone/main.js:171`, `serve/ui/phone/main.js:241`, `serve/ui/phone/main.js:253`

The new fixture is documented as “Boot the real shell against a package, solve it through the keypad,
and hand back the app.” It imports `createGame`, `renderSection`, and `renderKeypad`, calls them
independently, and never imports or executes `main.js`. The assertions therefore prove useful component
properties, but none of the behavior added in the shell:

- the keypad and verdict are removed after a successful check;
- the finished board is redrawn without selection behavior;
- `See the boxscore` replaces the keypad;
- a restored finished session opens the reveal;
- closing and reopening the reveal uses the frozen completion record.

This is a recurrence of the backlog's standing observation that a rule left in `main.js` is unguarded
by construction, not a duplicate of v23's input-rule finding: the newly affected behavior is the entire
completion lifecycle, and the new test explicitly claims to cover that lifecycle. A green suite can
therefore accompany a broken primary finish path.

**Required correction:** make the shell boot path importable with injected package, store, document,
and clock boundaries, then drive one board through the real keypad and Check handler. Assert the live,
just-finished, and restored-finished DOM states, including reveal close and reopen. Keep the component
tests, but do not describe them as a shell test.

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

- **v30-P1-01 remains open.** `confirm.py` now labels `other_steps` honestly, but still says the causal
  counterfactual needed to distinguish a reasoning tool from an erasure permit was not run.
- **v30-P1-02 remains open.** No new certification change adds independent row-level boxscore
  evidence; aggregate R/H/outs correspondence is still the boundary.
- **v30-P3-02 remains open.** `run_browser_tests.py` still writes `window.__fatal` while waiting only
  for `window.__results`, so a known page failure waits the full timeout.

## Disposition

No new P0 or P1 product defect was found in the changed code. The component-level completion behavior
is internally coherent, and the batting-order edit does not introduce a new defect; it leaves the known
v30 decision gap unresolved. v31 is not clean because the primary completion lifecycle is not exercised
by the test that claims to cover it, and two smaller code/document contracts disagree with reality.
