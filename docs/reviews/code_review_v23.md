# Code Review v23

Date: 2026-08-20

## Result

Two new findings, both P2. No P0, P1, or P3 finding is reported.

This pass reviewed the v22 package-profile fix, the verifier cleanup, the shared eligibility SQL and
regenerated multiplicity evidence, and the latest phone-board accessibility, input, cascade, and
two-digit-entry changes.

All three v22 findings are closed and are not repeated. Direct package construction now enforces the
same complete-answer profile as parsing, the loader and multiplicity instrument share the complete
candidate cohort, and the aggregate query executes once. The operator's already recorded filled-cell
highlight and unbounded-innings-entry defects are also fixed and are not review findings here.

Known work already recorded in `docs/reviews/todo.md` is excluded: persistence, reveal, timer, Done-time
validation, routes, the hand-solve decisions, the remaining six-pitcher measurements, the unexplained
8-stall coverage difference, the volume generator, and the unfinished product surfaces.

No tests, linters, type checks, builds, database queries, browser runs, or accessibility-tool runs were
performed during this review.

## Frontend Engineer

### v23-P2-01 - An editable cell's accessible name never reports its current value

**Severity:** P2

**Locations:**

- `serve/ui/phone/board.js:119`
- `serve/ui/phone/board.js:126`
- `serve/ui/phone/board.js:181`
- `serve/ui/phone/board.js:184`
- `serve/ui/phone/board.js:195`
- `serve/ui/phone/board.js:203`
- `serve/ui/phone/main.js:129`

**Description:** The new keyboard and screen-reader path gives each editable cell a static
`aria-label` containing only its row and column, such as `SS, H`. `paint()` later changes the cell's
visible text when the player enters or clears a value, but it never updates that label.

An explicit `aria-label` supplies the element's accessible name instead of its text content. The
visible `5` written by `paint()` is therefore not what assistive technology reads when focus returns to
the cell. The opening state has the same mismatch: the implementation comment promises an announcement
such as `SS, hits, blank`, but the label built at line 126 does not contain a blank state either.

**Impact:** A VoiceOver, TalkBack, switch-control, or keyboard user can now find and activate a cell,
but cannot inspect the value currently stored in it. On a deduction board where reviewing earlier
entries is the primary interaction, this leaves the accessible path unable to communicate the player's
own work even though the sighted path does. `aria-pressed` communicates which cell is selected, not what
number it contains.

**Reproduction:** Render any blank batting cell and inspect its `aria-label`; it contains only the row
and column. Enter `5` through the game and call `paint()` as `repaint()` does. The cell's `textContent`
becomes `5`, while its `aria-label` remains unchanged. Clearing the cell produces the same static name,
so filled and empty states are indistinguishable through the accessible name.

**Fix and rationale:** Keep the row/column context as a base label and update the accessible name from
`paint()` every time the displayed value changes. Append a catalogued blank state when the value is
null and the same rendered value shown on screen when it is filled, including `inningsToDisplay()` for
outs. Alternatively, use labelled row/column context without an `aria-label` that masks the cell text.
Add a DOM test that enters, changes, and clears a value and asserts that the accessible name follows all
three states. Accessibility state must be derived in the same redraw path as visual state or the two
will drift again.

## UX / Visual

### v23-P2-02 - The thirds keys silently edit every kind of statistic

**Severity:** P2

**Locations:**

- `serve/ui/phone/board.js:300`
- `serve/ui/phone/board.js:307`
- `serve/ui/phone/board.js:314`
- `serve/ui/phone/main.js:137`
- `serve/ui/phone/main.js:138`
- `serve/ui/phone/main.js:140`
- `serve/ui/phone/main.js:145`

**Description:** The keypad always enables the `1/3` and `2/3` controls, although only pitching outs
are displayed as fractional innings. The shell correctly computes an `innings` flag for the selected
cell, but the `key.thirds` branch runs before and independently of that flag.

For a batting, pitching-hit, run, walk, strikeout, or totals cell, pressing a thirds key interprets the
ordinary integer as a count of outs and writes `floor(current / 3) * 3 + thirds`. The result is then
rendered as an ordinary integer. A control labelled `1/3` can therefore enter `1` into a hits cell or
change an existing non-innings value according to modulo-three arithmetic.

**Impact:** A visible keypad control performs a different operation from the one printed on it and can
silently replace a valid entry with another valid-looking integer. Because immediate correctness
feedback is deliberately absent, the player may carry that accidental value through later deductions.
This affects the normal phone UI and requires no unusual data or environment.

**Reproduction:** Select an empty batting hits cell and press the `1/3` key. `innings` is false, but the
unconditional thirds branch computes `0 + 1`, calls `game.enter()` with `1`, and repaint displays the
whole number `1`. The key neither enters one third nor refuses an operation that has no meaning for that
cell.

**Fix and rationale:** Accept `key.thirds` only when `innings` is true, and make the interface communicate
the same rule by disabling the two thirds buttons until a pitching-outs cell is selected. Keep a guard
in the handler even when the buttons are disabled so input correctness does not depend on presentation.
Add interaction tests proving that thirds adjust an outs cell and leave every plain-integer cell
unchanged. The set of enabled controls and the handler's accepted operations should express one rule.

## Other Personas

**Backend Architect:** The v22 constructor/profile issue is closed: both direct construction and parsing
now require a complete answer board. No new practical backend boundary finding was found.

**Python Principal:** The complete eligibility fragment is shared by the loader and multiplicity
instrument, and the report reuses its first cursor metadata instead of executing the aggregate twice.
No independent Python finding was found.

**QA / Reliability:** The multiplicity figures were regenerated against the corrected cohort and the
absolute counts were updated consistently in the reviewed consumers. The missing interaction coverage
is included in v23-P2-01 and v23-P2-02 rather than reported separately.

**Security:** No new practical security finding was found. The reviewed changes do not add an
attacker-controlled network, credential, authorization, or command-execution boundary, so
attack-scenario fields are not applicable.

**Baseball / Boxscore:** The corrected `4,019 of 100,226` footnote measurement and count-first notation
remain internally consistent. The misuse of baseball thirds outside innings pitched is covered by
v23-P2-02.

**Kakuro / Logic-Puzzle:** The answer profile and footnote presentation preserve a complete,
unambiguous solution. The inability to review entered values through assistive technology is covered by
v23-P2-01; no separate deduction or uniqueness regression was found.

## Recommendation

Fix the accessible value state before treating the new keyboard/screen-reader path as usable, and bind
the thirds controls to pitching-outs selection at both the UI and handler layers. Both changes are local
to the phone shell and should be protected with interaction-level tests rather than additional engine
rules.
