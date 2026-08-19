# Code Review v19

**Date:** 2026-08-19  
**Requested as:** relaunch of review 18  
**Written as v19 because:** `code_review_v18.md` already exists and review files are append-only.

## Executive summary

This review found **9 new actionable findings**: **1 P1, 4 P2, 4 P3, and no P0**.

The highest-risk issue is in the new scoreboard-blank experiment. When either treatment cannot reach a
target, the instrument drops both treatment rows. That erases the strongest possible treatment effect
and can report a false null. The production generator's new exclusions themselves are coherent; the
problem is in the instrument intended to measure their effect.

The new phone implementation has a sound high-level split between package parsing, game state, and
presentation. Its main risks are narrower and concrete: the Python and JavaScript schema readers enforce
different v3 contracts, tappable cells have no accessible interaction semantics, and the renderer never
applies the `live`/`zero` classes on which the footnote visual hierarchy depends.

No current source package, test, or generated reference package was changed by this review.

## Review method and boundary

This was a static review. I did **not** run tests, Ruff, mypy, the browser harness, discovery jobs, or the
reference publisher.

I reviewed the project-owned Markdown corpus, with `docs/python-conventions.md` as the authoritative
Python standard and `docs/package-format-v3.md` as the active package contract. Historical package v1/v2
documents were treated as history, as v3 instructs. I also reloaded the current backlog, non-issues, and
review history through v18 before deduplicating findings.

The active `forge/`, `serve/`, `discovery/`, and `tools/` paths were in scope. `_not_in_use` and vendored
environment files were excluded. Existing roadmap items were not converted into findings: the hand-solve
ladder, the pool run for zero-valued footnotes, volume/calendar publishing, tablet/desktop layers, reveal,
and persistence remain planned work rather than review defects.

Severity means:

| Priority | Meaning in this project |
|---|---|
| P0 | Immediate loss, compromise, or publication of invalid inventory with no practical containment |
| P1 | Can invalidate a product decision or produce materially wrong behavior on a normal project path |
| P2 | Real correctness, reliability, accessibility, or contract risk with a narrower trigger |
| P3 | Maintainability or standards defect with limited immediate user impact |

## Findings by persona

### Persona 1: Python Principal Developer

#### `v19-P3-01` - Font fetching uses an optimization-removable runtime assertion

**Severity:** P3  
**Location:** [`tools/fetch_fonts.py:79`](../../tools/fetch_fonts.py#L79)  
**Convention:** `docs/python-conventions.md` forbids `assert` for runtime validation.

**Description:** The response from Google Fonts is validated with `assert found is not None`. This is
runtime input, not an internal invariant. Python removes the assertion under `-O`, after which line 80
calls `.group()` on `None` and replaces the explanatory failure with an `AttributeError`.

**Impact:** A changed or malformed upstream CSS response fails through two different error contracts
depending on interpreter flags. The optimized path loses the family, weight, and response excerpt needed
to diagnose why asset generation stopped.

**Reproduction:** Run the script with `python -O` while making `get()` return CSS without a WOFF2 URL.
The explicit message is skipped and `found.group(1)` fails instead.

**Recommended fix and rationale:** Replace the assertion with an explicit `if found is None` branch that
raises `RuntimeError` or exits with the existing explanatory message. Runtime input validation must stay
active in every interpreter mode.

#### `v19-P3-02` - New result dataclasses omit the mandatory `slots=True`

**Severity:** P3  
**Locations:** [`discovery/zero-footnotes/measure.py:83`](../../discovery/zero-footnotes/measure.py#L83),
[`discovery/scoreboard-blanks/measure.py:67`](../../discovery/scoreboard-blanks/measure.py#L67)  
**Convention:** Data containers must use `@dataclass(frozen=True, slots=True)`.

**Description:** `Row` and `Arm` are frozen but not slotted. `Arm` also relies on `row.__dict__` during
serialization, making the convention violation part of the implementation rather than an omitted flag.

**Impact:** These high-volume result records retain dynamic instance dictionaries and permit a serialization
pattern that blocks adoption of the repository's required immutable container shape.

**Reproduction:** Inspect `Row.__slots__` or `Arm.__slots__`; neither exists. Adding `slots=True` to `Arm`
then exposes the `row.__dict__` dependency at scoreboard line 256.

**Recommended fix and rationale:** Add `slots=True` to both decorators and serialize `Arm` with
`dataclasses.asdict`, as the zero-footnote instrument already does. This satisfies the mandatory convention
without changing the result schema.

### Persona 2: QA / Reliability Engineer

#### `v19-P1-01` - The scoreboard experiment deletes asymmetric treatment failures

**Severity:** P1  
**Location:** [`discovery/scoreboard-blanks/measure.py:104`](../../discovery/scoreboard-blanks/measure.py#L104)

**Description:** `_measure()` returns `[]` as soon as either arm's `erase()` call returns `None`. If the
`before` arm reaches a stall target only because a scoreboard duplicate is erasable, while the `after`
arm cannot reach it, both observations disappear. If `before` fails, the `after` arm is not run at all.
The report then intersects the remaining keys and has no count of discarded trials.

**Impact:** Failure to reach a target is the strongest evidence that removing scoreboard lookups changes
coverage. The instrument converts that evidence into absence and can report unchanged medians or a real
null while systematically omitting every pair where coverage changed. That can validate or reject a
generator rule on false evidence.

**Reproduction:** Stub `erase()` to return a puzzle for `before` and `None` for `after`. `_measure()` returns
an empty list, so `report()` receives neither the successful arm nor the failed arm and cannot show the
coverage loss.

**Recommended fix and rationale:** Record one `Arm` per treatment with an explicit `reached` field and
nullable metrics, exactly as the zero-footnote instrument records `reached=False`. Report paired reachability
before conditional chain/stall/blanks summaries, assert the expected number of arms per board/seed/target,
and add a regression test where only one arm reaches. A null must remain data, not become a missing row.

#### `v19-P2-01` - The zero-footnote decision instrument has no executable tests

**Severity:** P2  
**Locations:** [`discovery/zero-footnotes/measure.py:111`](../../discovery/zero-footnotes/measure.py#L111),
[`discovery/zero-footnotes/measure.py:121`](../../discovery/zero-footnotes/measure.py#L121)  
**Convention:** TDD is mandatory and behavior must be covered by tests.

**Description:** Static test-reference inspection found no test importing or exercising this instrument.
Its treatment membership, canonical-order filtering, failed-target retention, pair comparison, and report
denominators therefore have no executable guard. This is decision code intended to reverse or retain a
board feature, not a disposable formatting script.

**Impact:** A one-line change can compare different trajectories, include zeros in the wrong arm, drop a
failed target, or change a denominator without causing a test failure. The scoreboard instrument's P1
demonstrates that this exact class of defect is currently plausible.

**Reproduction:** Change the `non_zero` predicate at line 117 from `values[name] != 0` to `== 0`, or remove
the common-order filtering at line 129. No existing test references this module and therefore none can
reject the changed experiment.

**Recommended fix and rationale:** Extract the pure treatment/order/row comparison behavior into an
importable module and test it with a small constructed direction plus a stubbed eraser. Required cases are
all three candidate sets, stable relative order, one failed arm, complete arm counts, and pair denominators.
This protects the causal comparison before database time is spent.

#### `v19-P3-03` - The catalog-completeness test does not test an incomplete catalog

**Severity:** P3  
**Locations:** [`serve/engine/strings.js:91`](../../serve/engine/strings.js#L91),
[`serve/tests/engine.test.js:318`](../../serve/tests/engine.test.js#L318)

**Description:** `useCatalog()` accepts any object without checking its keys. The test named “a replacement
catalog is complete or the swap is refused” swaps in a complete copy of English and compares its keys with
the same complete catalog. It never supplies a missing or extra key, and no refusal exists.

**Impact:** The first partial translation can be installed successfully and fail later, mid-render, when
`text()` reaches the missing key. The test currently advertises a stronger boundary than the code provides.

**Reproduction:** Call `useCatalog({})`; it returns normally. The next `text("board.batting")` throws even
though the catalog swap was supposedly the refusal point.

**Recommended fix and rationale:** Validate that replacement keys exactly equal the canonical catalog keys
before mutating `table`, reject missing and unexpected keys, and add negative tests for both. This makes the
swap atomic: the active catalog is always complete.

### Persona 3: Frontend Engineer

#### `v19-P2-02` - Grid and footnote cells are mouse/touch-only controls with no accessible semantics

**Severity:** P2  
**Locations:** [`serve/ui/phone/board.js:119`](../../serve/ui/phone/board.js#L119),
[`serve/ui/phone/board.js:218`](../../serve/ui/phone/board.js#L218)

**Description:** Editable cells are rendered as `td` or `span` elements with click handlers. They have no
button role, focusability, keyboard activation, accessible name, selected state, or association between
row/column labels and the input target. The keypad buttons cannot help until a cell has been selected.

**Impact:** A phone user relying on VoiceOver/TalkBack, switch control, or an attached keyboard cannot
reliably discover or select a blank. Empty cells may be announced only as empty table cells, so the puzzle
is unusable before numerical entry begins. This does not require a desktop interface or a multi-user setup.

**Reproduction:** Navigate the phone page using Tab or a screen-reader rotor. The keypad buttons receive
focus, but blank grid/footnote cells do not; there is no semantic control with which to establish
`selected`.

**Recommended fix and rationale:** Give editable cells native button behavior where table semantics permit,
or add `tabindex="0"`, `role="button"`, Enter/Space activation, catalogued `aria-label` text containing the
row and column, and `aria-selected`. Keep focus stable across `repaint()` or avoid replacing the focused
node. Native semantics are preferable because they reduce custom interaction code.

### Persona 4: Security Engineer

No new actionable security finding. Production rendering uses `textContent`/DOM construction for package
values, the query-string id must be present in the trusted manifest before it reaches a fetch path, and the
browser intentionally does not pretend that same-origin signature verification creates a separate trust
boundary. The remaining `innerHTML` uses are confined to test/discovery pages and either contain static
markup or pass source values through the existing escaping boundary.

### Persona 5: Backend Architect

#### `v19-P2-03` - Schema v3 has incompatible executable dialects

**Severity:** P2  
**Locations:** [`forge/src/boxscore_package/format.py:483`](../../forge/src/boxscore_package/format.py#L483),
[`serve/engine/package.js:103`](../../serve/engine/package.js#L103),
[`serve/engine/package.js:159`](../../serve/engine/package.js#L159)

**Description:** The v3 document, Python reader/constructor, and JavaScript reader enforce different required
fields and invariants. Python defaults missing `labels`, `pitcher_labels`, and `metadata`; its constructor
also defaults the two label tuples and never checks their row counts. JavaScript correctly requires label
counts, but accepts nullable `footnote_totals`, missing metadata, and slot references with invalid or
duplicate syntax that Python refuses.

**Impact:** A package can be constructed, signed, parsed, and certified on the forge while the browser
rejects it for missing labels. In the opposite direction, the browser accepts a null footnote total as a
blank even though it never renders that totals row: `createGame()` counts the blank, `renderFootnotes()`
skips the null total, and the player can never complete the puzzle. Duplicate slot references can also make
footnote attribution ambiguous while passing the client boundary.

**Reproduction:** Two minimal cases demonstrate the split. Construct a valid multi-row Python `Package`
without passing `labels` or `pitcher_labels`; `as_json()` emits empty lists, while `readPackage()` rejects
their lengths. Separately, set `raw.puzzle.footnote_totals[0] = null` in a valid v3 document; JavaScript
accepts it, but no UI element is created for the resulting `footnote_totals.hit_by_pitch` blank.

**Recommended fix and rationale:** Make required Python fields required constructor arguments, validate label
counts in `Package.__post_init__`, and require their JSON keys instead of defaulting them. In JavaScript,
enforce complete footnote totals, required object metadata, and the documented unique slot-reference grammar.
Add a small corpus of valid and invalid JSON conformance vectors consumed by both Python and browser tests.
Shared data vectors preserve the no-code-sharing boundary while guaranteeing one schema language.

### Persona 6: User Experience and Graphic Design Expert

#### `v19-P2-04` - Live footnotes never receive the visual class that makes them prominent

**Severity:** P2  
**Locations:** [`serve/ui/phone/board.js:211`](../../serve/ui/phone/board.js#L211),
[`serve/ui/phone/board.css:381`](../../serve/ui/phone/board.css#L381)

**Description:** The stylesheet defines `.term.zero` and `.term.live`, and the design explicitly reserves
prominence for a live term because players learn to ignore the usually empty footnote line. The renderer
always creates `class="term"` and never adds either state class. Both rules are dead.

**Impact:** A real HBP/SF/SH/CI occurrence has the same hierarchy as a zero-total term containing an erased
cell. Missing that term makes the batting-row arithmetic appear contradictory and directly undermines the
deduction the footnote line exists to expose.

**Reproduction:** Render a reference package whose footnote total is greater than zero and inspect the
element. Its class list contains `term` but not `live`; the `.term.live` weight and color never apply.

**Recommended fix and rationale:** Add `live` when `total > 0` and `zero` when `total === 0`, at the point
where the term node is created. Add a DOM-level test covering one of each. The state is already known there,
so no duplicate puzzle logic is introduced.

### Persona 7: Baseball and Boxscore Expert

#### `v19-P3-04` - Active source docstrings still describe the retired footnote and label rules

**Severity:** P3  
**Locations:** [`forge/src/boxscore_package/format.py:65`](../../forge/src/boxscore_package/format.py#L65),
[`forge/src/boxscore_package/format.py:208`](../../forge/src/boxscore_package/format.py#L208),
[`forge/src/boxscore_package/format.py:343`](../../forge/src/boxscore_package/format.py#L343)

**Description:** The active format module says per-batter footnotes are “given complete and never erased,”
repeats that they are never `None`, and says repeated batting positions are suffixed by appearance. Schema
v3 and current packages say the opposite: per-batter footnotes are nullable, only their totals are complete,
and batting labels are bare positions while `slot_references` identify rows. The browser test even comments
that the forge docstring is wrong rather than failing on the disagreement.

**Impact:** A maintainer using the active Python source as the contract can recreate either retired behavior:
publishing erased footnote answers or adding position suffixes that partition rows differently from lineup
slots. Both produce plausible-looking baseball boards whose arithmetic or attribution semantics are wrong.

**Reproduction:** Compare the three cited docstrings with the v3 field table and any current reference
package containing null per-batter footnotes and bare repeated labels.

**Recommended fix and rationale:** Update the active docstrings to state that per-batter footnotes are
erasable, footnote totals are complete, labels are bare entry positions, and slot references provide row
identity. Extend schema-document parity checks to these semantics so stale source guidance cannot remain a
known comment in a passing test.

### Persona 8: Kakuro and Logic-Puzzle Expert

No additional finding after deduplication. The generator now excludes zero-valued footnote entries and the
four totals copied verbatim by the line score from its canonical erasable set. The actionable logic risk is
the P1 QA finding above: the experiment measuring the scoreboard exclusion can erase failed-arm evidence.
No separate finding was created for the same defect under a second persona.

## Priority order

1. Fix `v19-P1-01` before trusting any scoreboard-blank result.
2. Align the executable schema dialects in `v19-P2-03` before another producer or client layer is added.
3. Add the zero-footnote instrument tests in `v19-P2-01` before its pool result decides the board.
4. Fix mobile accessibility and live-footnote hierarchy in `v19-P2-02` and `v19-P2-04` before treating the phone layer as playable.
5. Close the four P3 convention/documentation defects during the same focused files' next edit.

## Residual validation gap

Because this review was static by contract, it does not claim that the current test suite, Ruff, mypy,
browser harness, real-phone layout, or discovery instruments pass. The findings above are reproducible from
the inspected control flow without executing those tools.
