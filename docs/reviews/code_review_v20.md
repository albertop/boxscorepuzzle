# Code Review v20

Date: 2026-08-19

## Result

Three new findings: one P1 and two P3. No P0 or P2 finding was found.

This pass reloaded the current Markdown contract and reviewed the implementation after v19, with discovery and the player-visible package path receiving the highest weight. Closed v19 items are not repeated. The known fifty-board `build_pack.py` migration from chain targets to stall targets is also not repeated because `docs/reviews/todo.md:2267` already records it as pending work.

No tests, linters, type checks, builds, or browser validation were run during this review.

## Backend Architect

### v20-P1-01 - A valid retained schema-3 board can be accepted but can never be completed

**Severity:** P1

**Locations:**

- `serve/engine/package.js:97`
- `serve/engine/game.js:49`
- `serve/ui/phone/board.js:226`
- `serve/tests/engine.test.js:394`
- `serve/tests/package-vectors.json:86`
- `forge/src/boxscore_package/format.py:219`
- `forge/src/boxscore_forge/erasure.py:78`

**Description:** Schema 3 still permits nullable per-batter footnote cells. The browser reader accepts those cells through the generic nullable row reader, and `createGame()` includes them in the set whose blanks determine completion. The new footnote renderer, however, deliberately emits no cell and no `data-cell` element for any footnote value. It only prints the known attribution text.

That leaves the three layers with incompatible contracts: the package reader says the blank is valid, the game says the blank must be filled, and the UI gives the player no way to fill it. This is not only a synthetic mutation. The retained generation `serve/data/puzzles/5dce9f673a0f/` contains six packages with 91 nullable per-batter footnote cells, while the current generation contains none. At least four puzzle IDs occur in both generations, so the generation boundary does not create a new package identity.

The tests miss the seam. The browser test asserts only that the six packages selected by the current manifest have no footnote blanks. The shared vectors cover a null footnote *total*, but not a null per-batter footnote cell, even though the latter remains valid under schema 3. Two Python docstrings also preserve the old nullable statement while the current generator policy says the opposite; this is contract drift from the same incomplete migration rather than a separate finding.

**Impact:** A rollback, retained-generation request, mixed deployment, or any other schema-3 producer can load a board that remains permanently unsolved after every visible blank has been entered. Completion, timing, and result recording never finish. The default current manifest avoids the defect only because its six current artifacts happen not to exercise the nullable branch accepted by the reader.

**Reproduction:** Serve the app and load `serve/data/puzzles/5dce9f673a0f/126c049659c4a61c.json` through `readPackage()`. Create the game and render its footnote line. The package is accepted and the game retains null footnote cells, but `renderFootnotes()` produces no editable element for them. Filling every visible batting and pitching blank still leaves the game incomplete.

**Fix and rationale:** Preserve the schema-3 contract at the boundary. Prefer a compatibility renderer that detects nullable per-batter footnotes and restores editable controls only for those legacy cells, including zero-total terms that would otherwise be hidden. New packages can continue to render the compact read-only line. If nullable footnotes are intentionally no longer supported, introduce a new schema version with non-null footnote rows and reject incompatible schema-3 input explicitly instead of accepting an impossible game. Add a shared conformance vector for a null per-batter footnote and exercise every retained generation, not only the manifest's current six. Update the two stale Python docstrings in the same change. This keeps parsing, completion, rendering, tests, and the documented schema on one contract.

## Python Principal

### v20-P3-01 - Nineteen live discovery dataclasses do not follow the required frozen-and-slotted shape

**Severity:** P3

**Locations:**

```text
discovery/footnote-groups/measure.py:80
discovery/footnote-groups/measure.py:97
discovery/footnote-groups/measure.py:146
discovery/footnote-groups/measure.py:249
discovery/footnote-grouping/measure.py:67
discovery/verifier/rejection_rates.py:51
discovery/independent-cells/prune.py:55
discovery/independent-cells/measure.py:51
discovery/erasure/measure_erasure.py:46
discovery/stall-targeted/measure.py:51
discovery/difficulty-weights/measure.py:68
discovery/board-topology/compare_column_sets.py:27
discovery/footnotes-open-or-given/measure.py:48
discovery/difficulty-metrics/measure.py:86
discovery/hand-solve/build_pack.py:84
discovery/pitcher-cap/measure_pitching.py:57
discovery/board-configurations/measure.py:59
discovery/pool-at-4-pitchers/resolution_in_range.py:45
discovery/pool-at-4-pitchers/remeasure.py:47
```

**Description:** The project convention requires data records to use `@dataclass(frozen=True, slots=True)`. Eighteen of these decorators are frozen but omit `slots=True`; `discovery/board-topology/compare_column_sets.py:27` omits both `frozen=True` and `slots=True`. These are live discovery files and are not under `_not_in_use`.

**Impact:** The records retain a dynamic `__dict__`, permit undeclared storage, and in one case permit mutation. More importantly for this project, the highest-priority discovery layer no longer follows the data-shape invariant used by the forge and verifier, so future scripts can silently depend on behavior the production records intentionally disallow.

**Reproduction:** Inspect the listed decorators or instantiate one of the affected records and observe that it has a `__dict__`; the board-topology record can also be reassigned after construction.

**Fix and rationale:** Add `slots=True` to the frozen decorators and use `@dataclass(frozen=True, slots=True)` for the board-topology record. There are no live `__dict__` accesses in the searched source trees, so no known serializer requires preserving the dynamic mapping. Apply the convention consistently to keep research records immutable and structurally equivalent to the records whose behavior they measure.

## Frontend Engineer

### v20-P3-02 - The new footnote attribution text bypasses the string catalog

**Severity:** P3

**Location:** `serve/ui/phone/board.js:237`

**Description:** `renderFootnotes()` constructs player-visible attribution text with hard-coded `#` and multiplication sign literals: `#2b` and `#2b x 2` in semantic form. The project contract requires every player-visible string, including small symbols whose meaning or spacing can vary by locale, to come from the catalog. The surrounding renderer already obtains labels from `text()`, and the keypad catalogs even its fraction pieces, so this line is an unguarded exception rather than an established presentation rule.

**Impact:** A future catalog can translate the footnote name but cannot change the slot prefix, multiplier marker, or their ordering. Catalog-completeness tests still pass because they cannot see literals embedded in rendering code.

**Reproduction:** Install any complete replacement catalog and render a live footnote term with a value greater than one. The term label changes through the catalog, while `#` and the multiplier syntax remain fixed by `board.js`.

**Fix and rationale:** Put the slot-prefix and repeated-value formatting in catalog data, preferably as a single attribution formatter or as explicit prefix and multiplier keys. Add a rendering assertion using a replacement catalog whose markers differ from English. That tests the user-visible seam rather than merely testing that catalog keys exist.

## Other Personas

**QA / Reliability:** v20-P1-01 is the reliability finding; no separate duplicate was created. The current-package-only test scope and missing compatibility vector are included in that finding.

**Security:** No new practical security finding was found. The changed paths remain local/static package production and rendering paths; no attacker-controlled network, credential, authorization, or command-execution boundary was introduced. Attack-scenario fields are therefore not applicable.

**UX / Visual:** The impossible legacy-board state is covered by v20-P1-01, and the catalog bypass by v20-P3-02. No independent layout or interaction defect was found from static inspection.

**Baseball / Boxscore:** The current generated footnote policy and six-pitcher cap are internally coherent for the active generation. The schema-3 footnote mismatch is covered by v20-P1-01.

**Kakuro / Logic-Puzzle:** The solver can continue to hold a legacy footnote blank that the player cannot enter; that completion mismatch is covered by v20-P1-01. No separate deduction-rule defect was found.

## Recommendation

Do not rely on retained-generation rollback or claim complete schema-3 browser compatibility until v20-P1-01 is closed. The two P3 findings are not release blockers, but they should be folded into the same cleanup window while the affected files are already being touched.
