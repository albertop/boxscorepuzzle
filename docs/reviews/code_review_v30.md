# Code Review v30

## Re-review after the 2026-08-20 corrections

This section is the authoritative current status of the findings below. The original review remains
in place as the record of what was found before the corrections.

### Current status

#### v30-P1-01 — RETRACTED: a causal measurement is research debt, not a product defect

The original false `causal` label was a real reporting error and is already corrected: the code now
calls the value `other_steps` and states exactly what it does and does not establish. Requiring a new
counterfactual experiment after that correction does not identify a broken board, an invalid proof, or
a player-visible failure. The fallback is conditional, every produced board still passes the existing
publication proof, and felt difficulty remains subject to the hand-solve launch gate. Whether the
constraint is best described as a reasoning tool or as permission for additional erasure is a useful
research question, but not a code-review P1 and not required work. No source change is owed.

#### v30-P1-02 — RETRACTED: the verifier does not owe row-level certification of the unplayed half

**Retraction:** this finding conflated puzzle certification with historical-display fidelity. The
opposite batting and pitching half is reveal-only: it was not played, contributes no clue, and cannot
affect uniqueness, derivability, correctness, or the player's result. Requiring independent row-level
evidence for that half would expand §22 into a second Retrosheet validator without protecting the
puzzle guarantee. The signed package, reveal shape checks, shared-half agreement, and aggregate
corroboration are proportionate to this boundary. No source change is required.

#### v30-P3-02 — A browser page error still waits the full two-minute timeout

**Locations:** `tools/run_browser_tests.py:79`, `tools/run_browser_tests.py:86`,
`.githooks/pre-push:45`

The `pageerror` callback writes `window.__fatal = 1`, explicitly to avoid waiting after a module or page
failure. The wait predicate observes only `window.__results`, so `__fatal` cannot release it. A normal
JavaScript import or runtime failure therefore stalls the local pre-push gate for 120 seconds before
returning the failure it already knows about.

**Required correction:** wait for either `__results` or `__fatal`, then fail immediately with the
captured console when `__fatal` is present.

### Closed findings

- **v30-P1-02 — Retracted.** The unplayed half is reveal-only and does not belong to the puzzle proof.
- **v30-P1-01 — Retracted.** The remaining causal question is research debt, not a demonstrated product defect.
- **v30-P1-03 — Closed.** Finished sessions now persist `finishedAt`, restore as sealed, and reopen the
  final reveal without restarting the clock.
- **v30-P2-01 — Closed.** Digit entry no longer records provisional prefixes as errors; errors are
  recorded only when the player explicitly checks a complete board.
- **v30-P3-01 — Closed.** The production fallback module and the decision document now agree that the
  mechanism is adopted, and both preserve the limitations of the confirmation.

### Re-review disposition

The corrections materially improve the implementation. No P1 or P2 finding remains open; one P3
tooling defect remains. No additional normal-operation product issue was found
in the corrected completion, keypad, reveal, hook, or fallback paths.

## Findings

### Kakuro / logic-puzzle specialist and QA / reliability

#### v30-P1-01 - The confirmation report calls every non-division deduction causal

**Hat:** Kakuro / logic-puzzle specialist; QA / reliability; discovery engineering  
**Severity:** P1  
**ID:** v30-P1-01  
**Location:** `discovery/batting-order/confirm.py:216`, `discovery/batting-order/confirm.py:270`, `discovery/batting-order/confirm.py:409`, `docs/reviews/batting-order-plan.md:186`

**Description:** `_steps()` counts `Technique.LINEUP_ARITHMETIC` as division filler and then labels every other deduction in the solution `causal`:

```python
division = sum(1 for step in solution.deductions if step.technique is Technique.LINEUP_ARITHMETIC)
return division, len(solution.deductions) - division
```

That subtraction does not establish causality. It includes ordinary column sums, row propagation, cross-team deductions, global-identity deductions, and bounding steps whether or not the batting-order relation contributed to them. This recreates the exact distinction the adoption measurement was required to settle: the constraint may resolve cells, or it may merely permit more erasure while unrelated equations resolve the additional cells. The report currently calls both mechanisms causal.

The resulting claim in `batting-order-plan.md` that the confirmation found 346 causal deductions against two division steps is therefore not supported by the recorded fields. `confirm.json` records technique totals, not a counterfactual or dependency attribution proving that those 346 deductions used the batting-order relation.

**Impact:** Criterion 3 of the pre-registered confirmation is evaluated with an inflated denominator. A fallback board containing two division steps and hundreds of completely unrelated deductions will report a very low filler percentage and confirm adoption even if the relation resolves no useful cell. This is decision-changing measurement error, not presentation noise.

**Reproduction scenario:** Pass `_steps()` a solution containing 100 `PROPAGATION` deductions and no `LINEUP_ARITHMETIC` deductions. It returns `(0, 100)`, and `_report_filler()` prints all 100 as causal even though the input contains no evidence that any deduction used the lineup relation. The same misclassification applies to ordinary deductions in every measured fallback solution.

**Recommended fix:** Measure causality rather than infer it from exclusion. For each selected fallback board, solve the identical erasure both with and without the batting-order mechanism and count only cells or downstream deductions that disappear without it. A dependency-graph implementation is acceptable for direct propagation, but bounding currently depends on the whole known board and carries no originating identity, so the counterfactual is the safer authority. Report three quantities separately: direct division filler, deductions causally enabled by the relation, and unrelated deductions. Add a guard where an all-propagation synthetic solution produces zero causal deductions, plus a fixture with one direct lineup deduction and one demonstrated downstream deduction. Regenerate `confirm.json` and revise the adoption result only after this measure exists.

### Security engineer, backend architect, and baseball domain expert

#### v30-P1-02 - Publication certification accepts a fabricated half of the printed boxscore

**Hat:** Security engineer; backend architect; baseball historian / boxscore domain expert  
**Severity:** P1  
**ID:** v30-P1-02  
**Location:** `forge/src/boxscore_package/format.py:737`, `forge/src/boxscore_package/format.py:752`, `forge/src/boxscore_verify/certify.py:62`, `forge/src/boxscore_verify/certify.py:139`, `forge/src/boxscore_verify/plausibility.py:139`, `forge/tests/reveals.py:15`, `forge/tests/verify/test_certification.py:66`, `forge/tests/verify/test_certification.py:184`

**Description:** Schema 5 promises a complete printed boxscore for both clubs. The package boundary correctly compares the shared half, `reveal.boxscore.offense.batting` and `reveal.boxscore.defense.pitching`, with the solution. Its own contract explicitly delegates the unshared half, `offense.pitching` and `defense.batting`, to `certify_for_publication()` against source evidence.

That delegated check does not exist. `Evidence` carries game identity, provenance, line-score totals, at-bats, and left on base, but no canonical rows for the two unshared grids or RBI. `check_independent_correspondence()` examines only those aggregate fields. `reveal_faults()` checks basic presence and naming, not whether the printed rows describe the game.

The test fixtures make the gap conclusive rather than hypothetical. `forge/tests/reveals.py` documents that the unshared half is invented, names every such row `Not A Real Player`, and fills it with zeros. `package_for()` uses that fixture, and `test_a_sound_package_is_publishable()` expects the publication gate to accept it.

**Impact:** The sole publication gate can certify and sign a package whose final payoff contains false players and false batting or pitching lines. An accidental side swap, stale join, partial loader result, or corruption before signing is promoted from candidate data to an authenticated historical claim. The puzzle arithmetic remains correct, so none of the four mathematical layers exposes the false reveal.

**Reproduction scenario:** Build `package_for(board)` from `test_certification.py` and supply `good_evidence(board)`. Its `offense.pitching` and `defense.batting` contain the fixture's explicitly invented rows, yet `certify_for_publication()` returns `publishable=True`. Equivalently, mutate a real package's unshared batter hits or pitcher outs before certification; the constructor, reveal plausibility check, and correspondence check have no value to compare and accept the change.

**Recommended fix:** Extend the certification evidence with canonical complete-boxscore rows obtained independently of the `Package` being judged. Add a registered certification that compares every unshared batting and pitching row, row order, player identity, role or position, RBI, and club identity. Keep `check_reveal_agrees()` for the shared half; the two checks protect different boundaries. Replace the certification happy-path fixture with canonical evidence and add mutations proving that every unshared numeric and identity field causes refusal. If no independent source can supply these rows, the gate must not claim to certify a complete boxscore; fail closed or narrow the published promise.

**Security analysis:** The trust boundary is candidate reveal data entering the signed publication namespace. No second developer or hostile contributor is required; a normal loader or mapping defect is sufficient. A hostile or corrupted producer could use the same unchecked path. This is primarily CWE-345, Insufficient Verification of Data Authenticity, and maps to OWASP A08 Software and Data Integrity Failures. It exposes no private data, but it invalidates the integrity guarantee attached to signed packages.

### Frontend engineer and backend architect

#### v30-P1-03 - A completed session reopens as unfinished and its final time starts growing again

**Hat:** Frontend engineer; backend architect; QA / reliability  
**Severity:** P1  
**ID:** v30-P1-03  
**Location:** `serve/engine/game.js:121`, `serve/engine/game.js:214`, `serve/engine/game.js:245`, `serve/engine/game.js:265`, `serve/ui/phone/main.js:193`, `serve/ui/phone/main.js:204`, `serve/tests/engine.test.js:1099`

**Description:** `finish()` freezes the duration only in the in-memory `finishedAt` variable. `snapshot()` persists entries, hints, first-wrong cells, and elapsed time, but not completion or the frozen duration. `restore()` therefore cannot restore `finishedAt`. After boot, `followAttention()` starts the clock for every visible board, including one whose restored entries already solve the puzzle. The shell also does not restore the reveal or any completed state.

**Impact:** Closing and reopening a correctly completed daily puzzle removes its payoff, resumes its clock, and changes the duration the player earned. Pressing Check again records the later value as the new finish. Duration is the comparison and sharing metric, so the persisted event becomes false on the ordinary reopen path the persistence feature exists to support.

**Reproduction scenario:** Solve a puzzle, call `finish()`, and save `snapshot()`. Restore that snapshot into a new game, start its clock as `main.js` does for a visible page, advance time, and press Check. The entries are still solved, but the new game has `finishedAt === null`; its next `finish()` freezes the enlarged elapsed time. The existing persistence test covers entries, mistakes, and elapsed time before completion, so it cannot detect this loss.

**Recommended fix:** Persist an explicit completed state with the frozen duration, validate it as part of the versioned session shape, and restore the game with the clock held. Expose completion through the game API so boot can render the completed state and reveal without requiring another Check. Stop or permanently guard `followAttention()` after completion so pointer, visibility, and idle events cannot restart the finished clock. Add a round-trip test that finishes, snapshots, restores, advances the injected clock, and proves both `solved` and `duration_ms` remain unchanged; add a shell-level test for restoring the reveal.

### QA / reliability and frontend engineer

#### v30-P2-01 - Typing a correct two-digit value records a mistake on its first digit

**Hat:** QA / reliability; frontend engineer  
**Severity:** P2  
**ID:** v30-P2-01  
**Location:** `serve/ui/phone/board.js:323`, `serve/ui/phone/board.js:341`, `serve/engine/game.js:181`, `serve/engine/game.js:190`, `serve/tests/engine.test.js:222`

**Description:** The keypad appends digits one press at a time and calls `game.enter()` after each press. `game.enter()` immediately records the cell in `firstWrong` whenever the current value is not the final answer. For a correct answer such as 12, the normal sequence is `1` followed by `12`; the intermediate `1` is recorded as a wrong entry before the player has finished typing.

**Impact:** Every correctly entered multi-digit answer can be reported as an error. Totals and pitcher outs routinely require two digits, so this is normal play rather than malformed storage or an unusual device. C7's error history is corrupted at collection time and cannot be reconstructed later. The reveal currently hides the count, but the record is explicitly retained for later measurement and sharing.

**Reproduction scenario:** Select a blank whose answer is 12. Apply digit 1 and then digit 2 through `applyKey()`. The board ends with the correct value, but `game.record().errors` is 1. The existing test calls `game.enter()` with an already-complete wrong value; it never drives the keypad's multi-key input path.

**Recommended fix:** Define when an entry becomes an attempt and record errors only at that boundary. The cleanest current boundary is Check: have the game record first-wrong cells internally when the whole board is checked, while still returning only the aggregate verdict so the UI reveals no cell. If selection change is chosen as the commit boundary instead, make it an explicit engine operation rather than a timeout. Add tests for a correct two-digit entry producing zero errors, a committed wrong value producing one, and repeated checks of the same wrong cell remaining one.

### Python principal engineer

#### v30-P3-01 - The production fallback still says its completed confirmation has not run

**Hat:** Python principal engineer; documentation contract  
**Severity:** P3  
**ID:** v30-P3-01  
**Location:** `forge/src/boxscore_forge/lineup_fallback.py:35`, `forge/src/boxscore_forge/lineup_fallback.py:39`, `forge/src/boxscore_forge/lineup_fallback.py:71`, `docs/reviews/batting-order-plan.md:161`

**Description:** The production module says the subgroup has not survived a confirmation run, says `confirm.py` has not been run, and says the filler unit remains for that run to settle. The current decision record says the confirmation completed and all three criteria held. These statements cannot all describe the current production mechanism.

**Impact:** The solo developer reading the production entry point is instructed to treat completed evidence as pending and may rerun, defer, or reverse work for the wrong reason. This is the same dangerous class as the stale experimental fence fixed in v29, but it is a new post-run contradiction rather than the already-closed text.

**Reproduction scenario:** Read lines 35-40 of `lineup_fallback.py`, then lines 161-187 of `batting-order-plan.md`. The former says the confirmation has not run; the latter records its completed result.

**Recommended fix:** Update the module contract to state the date and outcome of the completed confirmation, while preserving the real limitations: the causal metric must be corrected under v30-P1-01, the 20% chain ratio remains provisional, and eight stalls is not itself a human-validated difficulty label. Do not erase the historical pre-confirmation caveat; move it to the dated review record where it remains true.

## Hat coverage with no additional unique finding

**UX / visual design:** The phone board, completed-state clipping, responsive scoreboard, typography, and modal presentation were inspected. Known contrast and real-device screen-reader work is already recorded in `todo.md`; no separate untracked visual finding was added.

**Baseball domain:** Lineup-cycle arithmetic, substitution aggregation, visitor-first rendering, innings-as-outs, line-score ordering, and complete-boxscore side mapping were inspected. The only new domain-integrity issue is v30-P1-02.

**Security:** Signing, package parsing, publication gating, static serving, development server exposure, subprocess use, and browser rendering sinks were inspected. No private-data or practical solo-environment exploit was found beyond the publication-integrity failure in v30-P1-02.

## Review scope and residual risk

This was a full live-tree review, not a delta-only pass. The v28 full-tree review was used as the closed baseline; all current Markdown contracts and review ledgers were reloaded, `docs/python-conventions.md` was applied, current live source was inventoried, and the changed or high-risk paths in `forge/`, `serve/`, `tools/`, CI, and `discovery/` were inspected in detail. Historical discovery instruments were included in structural and risk scans. `_not_in_use`, generated measurement data, fonts, images, logs, and other non-source artifacts were excluded from source findings.

No tests, linters, type checks, browser runs, database queries, or generators were executed during this review, in accordance with the repository instruction not to run validation unless requested. Findings are based on static control-flow and data-flow inspection plus the repository's existing tests and artifacts. No source, test, configuration, or documentation file was modified other than this review report.

No P0 finding was identified. The five unique findings are three P1s, one P2, and one P3. None is already pending in `todo.md`; previously tracked launch work, human difficulty validation, screen-reader checks, production nginx, and discovery lint debt were not re-raised.
