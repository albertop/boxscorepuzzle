# Code Review v29 - Batting-Order Adoption

## Review contract and scope

This is a static delta review of the source changed after v28. It covers the adopted batting-order
path from generator constraints and fallback erasure through package construction, all verifier layers,
publication certification, property fixtures, and the new adoption guards. The provenance-loader repair
was also checked at its changed boundary. Unchanged source was followed only where it is a direct caller
or consumer of the new path.

The solo-developer operating model in `docs/reviews/non-issue.md` applies. Neither finding needs a second
developer, concurrent publisher, CI, an adversary, or an unattended process. Work already identified in
v28 is not renumbered here; in particular, the remaining discovery-renderer scope of v28-P2-03 is not a
v29 finding.

No tests, linters, type checks, generator runs, database queries, or publication builds were run. The
findings come from tracing the changed source and its existing tests.

## Findings

### v29-P1-01 - The confirmation arm contains the control arm, making `lost` impossible by construction

- **Persona:** Statistician/methodologist / data scientist / solo-maintainer
- **Severity:** P1
- **Location:** `discovery/batting-order/confirm.py:14`, `discovery/batting-order/confirm.py:20`, `discovery/batting-order/confirm.py:123`, `discovery/batting-order/confirm.py:128`, `discovery/batting-order/confirm.py:176`, `forge/src/boxscore_forge/lineup_fallback.py:81`
- **Description:** The pre-registration defines `lost` as a direction that reaches the target plain but
  not through the fallback, and uses gained-minus-lost as its first adoption criterion. The `plain` arm
  calls `erase()` directly. The `fallback` arm calls `erase_with_lineup_fallback()` with the same seed
  and target; that wrapper first makes the identical plain call and returns that exact puzzle whenever
  it succeeds. Consequently every direction covered by `plain` is necessarily covered by `fallback`.
  `plain - fallback` is structurally empty, not an observed zero.
- **Impact:** The headline comparison cannot measure a cost of adopting the mechanism. `lost` can never
  be positive, so net gain can be zero or favourable but never negative; a criterion described as able
  to overturn the adoption is wired to one treatment that contains the other. The per-seed table does
  not repair this because the containment holds independently for every seed. This is the same
  saturation shape the pre-registration says it was written to prevent, now built into the arm rather
  than the target.
- **Reproduction:** For any target and seed where the plain row is reached and certified, follow the
  fallback call. Its first call is the same `erase(direction, target_stalls=target, seed=seed)` and it
  returns immediately with reason `"plain"`. Verification is deterministic on the same erased board,
  so `_covered(rows, "plain", ...) - _covered(rows, "fallback", ...)` is empty for every run.
- **Recommended fix and rationale:** Separate the two questions. Measure treatment trade-offs with a
  true constraint-on arm that calls `erase(..., slots=slots)` against the plain arm at the same seed.
  Measure product coverage with the conditional fallback wrapper, while stating explicitly that this
  path is monotone by design and has no meaningful `lost` category. Do not compare a net figure from
  one treatment definition with an earlier figure from another.

### v29-P2-01 - Uniqueness and end-to-end verification omit the adopted lineup relations

- **Persona:** Software architect / verification and test engineer / solo-maintainer
- **Severity:** P2
- **Location:** `forge/src/boxscore_forge/erasure.py:241`, `forge/src/boxscore_verify/verify.py:188`, `forge/src/boxscore_verify/verify.py:236`, `forge/src/boxscore_verify/verify.py:259`, `forge/scripts/write_reference_puzzles.py:108`, `forge/tests/test_lineup_fallback_is_adopted.py:96`
- **Description:** The fallback erases and solves against a `BoardShape` carrying lineup slots, and layer
  3 now correctly rebuilds the verifier's independent batting-order relations from the package. Layers
  2 and 4 still call `relations(board)` without those slots. They therefore search a different, weaker
  constraint system from the one that allowed the generator to erase the cells and from the one layer
  3 says the player may use. The test class named `TestTheVerifierCanActuallyCertifyTheseBoards` never
  invokes `verify()` or `certify_for_publication()` on a fallback-produced package; it tests the value
  step in isolation and inspects only the two derivability call sites.
- **Impact:** A valid fallback board whose uniqueness depends on the adopted batting-order clue is seen
  by layer 2 as having multiple solutions and is discarded before the new derivability step can run.
  A board that happens to remain unique under the old four families passes only by accident, and layer
  4 still does not independently solve against the same clue surface. Because the reference writer
  discards the fallback reason and may fill its six slots with ordinary boards, the production run and
  the current tests can both stay green while the newly adopted branch publishes no board at all.
- **Reproduction:** Produce a candidate for which the plain erasure misses the requested stall target
  and `erase_with_lineup_fallback()` succeeds after erasing plate-appearance cells that the lineup
  relations determine. Package it as `build()` does and call `check_uniqueness()`. The function passes
  no slots to `relations()`, so any alternatives excluded only by batting order remain legal and the
  package is rejected as `MULTIPLE_SOLUTIONS`. The adoption test does not exercise this sequence.
- **Recommended fix and rationale:** Derive `slots_of(package)` independently in every verifier layer
  whose model can speak about batting order. Pass the slots to the relation sets used by identity
  validation, uniqueness, derivability, and end-to-end solving; keep the existing independent relation
  implementation rather than importing generator code. Add one end-to-end fixture that first proves
  the plain attempt misses, then proves the fallback reason is `"fallback"`, and finally passes that
  exact package through `certify_for_publication()`. This tests adoption as an observable outcome rather
  than as the presence of imports and function calls.

### v29-P2-02 - The fallback publication test skips when no fallback exists and never calls the publication gate

- **Persona:** Verification and test engineer / solo-maintainer
- **Severity:** P2
- **Location:** `forge/tests/test_lineup_fallback_is_adopted.py:177`, `forge/tests/test_lineup_fallback_is_adopted.py:183`, `forge/tests/test_lineup_fallback_is_adopted.py:184`, `forge/tests/test_lineup_fallback_is_adopted.py:199`, `forge/scripts/write_reference_puzzles.py:146`
- **Description:** The repair adds a test whose contract is that the plain attempt misses, the fallback
  succeeds, and the exact result passes the publication gate. It finds the first target the plain path
  misses, but if the fallback returns anything other than `"fallback"` it calls `pytest.skip()` instead
  of failing. `"unreachable"` and `"discarded_filler"` are therefore successful suite outcomes for a
  test whose only purpose is proving that a fallback board exists. When it does obtain a board, the test
  calls `verify()` rather than `certify_for_publication()`, despite its docstring claiming to take the
  package through the publication gate.
- **Impact:** The exact regression v29-P2-01 described can return without making the suite red: the
  adopted branch may produce no certifiable board and the new test reports a skip. A separate defect in
  plausibility or external-evidence certification can also refuse every fallback board in production
  while this test passes, because those checks live outside `verify()`. The source-level slot threading
  is now correct, but the non-vacuous evidence that the adopted outcome reaches publication is still
  absent.
- **Reproduction:** Make the fallback attempt return `None, "unreachable"` for the selected fixture, or
  make the filler guard return `"discarded_filler"`. The test reaches line 187 and is skipped rather
  than failed. Alternatively, make `certify_for_publication()` refuse the package after `verify()`
  accepts it; this test never invokes that boundary and remains green.
- **Recommended fix and rationale:** Pin a fixture, seed and target known to exercise the fallback, then
  assert the plain result is `None`, assert `reason == "fallback"`, and assert the puzzle is present.
  A missing fallback is a failed precondition, never a skip. Pass that exact package, with synthetic
  independent `Evidence`, to `certify_for_publication()` and assert `publishable`. Keep the direct
  `verify()` assertion only if per-layer attribution is useful; it is not a substitute for the gate the
  production writer calls.

### v29-P2-03 - The authoritative coverage instrument equates `verify()` with publication certification

- **Persona:** Software architect / data scientist / verification engineer
- **Severity:** P2
- **Location:** `discovery/batting-order/confirm.py:1`, `discovery/batting-order/confirm.py:22`, `discovery/batting-order/confirm.py:32`, `discovery/batting-order/confirm.py:64`, `discovery/batting-order/confirm.py:150`, `forge/scripts/write_reference_puzzles.py:146`
- **Description:** `confirm.py` says it measures boards that can actually publish, defines coverage as
  passing every certification layer, and stores the result in a field named `certified`. `_measure()`
  calls only `verify(..., secret=UNSIGNED)`. Production publication calls
  `certify_for_publication()`, which additionally applies plausibility and independent evidence checks.
  The confirmation instrument imports neither that gate nor `Evidence` and therefore cannot answer its
  stated question.
- **Impact:** A generator result can be counted as covered and publishable here while the real writer
  refuses it for roster plausibility, source provenance, game identity, or official-total
  corroboration. The certification-refusal share and the 8-stall coverage figure are then numbers about
  the arithmetic verifier, not about the product, despite the report explicitly presenting them as the
  latter. Using `UNSIGNED` also means the signature layer is deliberately bypassed, so the phrase “all
  five layers” should not be used as evidence that the publication boundary ran.
- **Reproduction:** Compare line 152 with the writer's gate at `write_reference_puzzles.py:146`. Alter
  the independent evidence so that official totals disagree while keeping the package internally
  consistent. `verify()` accepts the arithmetic package and this instrument records `certified=True`;
  `certify_for_publication()` refuses it.
- **Recommended fix and rationale:** Build `Evidence` from the same `Loaded` fields the production
  writer uses and call `certify_for_publication()` on the measured package. Store both arithmetic-layer
  acceptance and publication-gate acceptance if the distinction is useful, with names that do not
  conflate them. An unsigned discovery run may deliberately skip cryptographic authenticity, but it
  must still execute the same plausibility and evidence boundary whose outcome it reports.

### v29-P2-04 - The filler criterion is computed over common, lower-target and plain-return rows

- **Persona:** Statistician/methodologist / data scientist
- **Severity:** P2
- **Location:** `discovery/batting-order/confirm.py:25`, `discovery/batting-order/confirm.py:223`, `discovery/batting-order/confirm.py:229`, `discovery/batting-order/confirm.py:240`
- **Description:** The pre-registered third criterion is causal deductions versus division filler on
  the gained boards at the hard end. The per-direction table first identifies directions gained at
  target 8, but chooses each displayed row from every certified fallback-arm row for that direction,
  without requiring `target == 8` or `reason == "fallback"`. The aggregate immediately below is broader
  still: it sums every certified row at all five targets and all three seeds, including common boards
  and fallback-arm rows whose wrapper returned the plain result. Those plain-return rows necessarily
  carry zero lineup division and dilute the filler share.
- **Impact:** The report does not calculate the criterion written at the top of the same file. A
  favourable all-target aggregate can hide filler-heavy target-8 gains, and `max(stalls)` can select a
  different target or treatment path from the board whose membership in `gained` is being explained.
  This can confirm the adoption with evidence from easier or common boards that the pre-registration
  explicitly excluded.
- **Reproduction:** Take a direction gained through a fallback row at target 8 and also reached plain at
  a lower target. The lower-target row enters the aggregate with zero division. It is also eligible for
  the `max()` at line 229 because that selection filters neither target nor reason. Neither row is the
  target-8 fallback observation the criterion names.
- **Recommended fix and rationale:** Form one explicit analysis cohort from rows with `target == 8`,
  `arm == "fallback"`, `reason == "fallback"`, `certified`, and a direction in the paired gained set.
  Report causal and division counts only for that cohort, per seed unless a direction-level reduction
  rule was pre-registered. If one row per direction is required, choose the seed deterministically
  before reading outcomes rather than maximizing over targets and seeds.

### v29-P3-01 - Active source and decision records disagree about whether batting order is adopted

- **Persona:** Software architect / technical writer / solo-maintainer
- **Severity:** P3
- **Location:** `forge/src/boxscore_forge/lineup_fallback.py:3`, `forge/src/boxscore_forge/lineup_fallback.py:20`, `forge/src/boxscore_forge/erasure.py:227`, `forge/src/boxscore_forge/constraints.py:126`, `docs/reviews/open-decisions.md:18`, `docs/reviews/open-decisions.md:21`, `docs/reviews/batting-order-reversal.md:185`, `forge/scripts/write_reference_puzzles.py:32`
- **Description:** The hand-solve record says the operator adopted the constraint, the production
  reference writer imports the fallback, and the new test says the publication fence came down by
  decision. The fallback module still opens with `EXPERIMENTAL. NOT ADOPTED. NOTHING HERE MAY REACH
  PUBLICATION` and says the verifier step is deliberately unwritten. `erasure.py` and `constraints.py`
  still say passing slots is experimental and that production passes none. `open-decisions.md` likewise
  records both the constraint and verifier step as not adopted.
- **Impact:** There is no current source of truth a solo maintainer can follow. Reading the production
  caller says to preserve and extend the path; reading the called module or the decision table says to
  restore the fence and prevent publication. This is not historical wording in an archived review: it
  is the module-level contract on the active implementation and the document named for open decisions.
  A later correction can therefore undo the adopted behavior while honestly following repository
  instructions.
- **Reproduction:** Start at `write_reference_puzzles.py`, which imports and calls the fallback before
  certification, then open the imported module. Its first executable documentation says that exact
  connection must not exist and later says the verifier capability added in this delta is absent.
- **Recommended fix and rationale:** Update the active module and function contracts in the same change
  that adopts the behavior. Preserve the earlier decision as dated history, but add an explicit
  superseding row or section to `open-decisions.md` pointing to the hand-solve verdict. Rename test-local
  `EXPERIMENTAL` identifiers where they now describe production. One current statement plus preserved
  history is safer than several individually reasonable statements with opposite instructions.

## Verdict

v29 found **one P1, four P2 findings and one P3**. The independent lineup arithmetic
and relation implementations agree on the cases covered by the new tests, slot parsing is taken from
the signed package boundary, and the conditional retry remains scoped to the production writer rather
than turning the constraint on globally. The blocking issue is now the confirmation instrument: its
comparison cannot observe losses, its certification predicate is not the publication gate, and its
filler calculation does not use the pre-registered cohort.

Recommended order:

1. Stop the confirmation run and separate the constraint-on comparison from conditional product coverage.
2. Make both the adoption test and confirmation instrument call `certify_for_publication()` on a real fallback result, failing rather than skipping when none exists.
3. Restrict the filler analysis to pre-registered target-8 gained observations.
4. Finish updating the two remaining stale source statements about adoption.

---

## Re-check after the latest corrections (2026-08-20)

The latest implementation closes **v29-P1-01**, **v29-P2-01**, **v29-P2-02**, **v29-P2-03**, and **v29-P2-04**. The fallback test is now pinned and non-skipping, the publication gate is exercised, the confirmation runner uses publication certification, and lineup slots are threaded through every verifier path. **v29-P3-01 remains partially open** because two source comments still describe lineup arithmetic as experimental or unreachable in production.

### v29-P2-05 - The filler decision silently changes its unit from directions to direction-seed rows

**Severity:** P2  
**Location:** `discovery/batting-order/confirm.py:291`, `discovery/batting-order/confirm.py:303`

`_covered()` and `_gained_cohort()` identify gains at direction level, but `_gained_cohort()` then returns every successful fallback row for every seed. `_report_filler()` uses `len(cohort)` as the denominator and aggregates filler across those rows. A gained direction that succeeds under all three seeds therefore receives three votes, while one that succeeds under only one seed receives one.

That is not the unit used by the earlier claim being tested: "nine of eleven" referred to directions, and the requested follow-up was explicitly per direction. The weighting can reverse the majority criterion without any change in the underlying set of useful directions, so it can change the adoption decision for purely incidental seed-frequency reasons.

**Recommended fix:** pre-register one decision unit and keep it throughout the comparison. The least surprising option is to retain directions as the unit: emit the seed rows for transparency, reduce them to one deterministic classification per gained direction, and evaluate the majority over gained directions. If seed rows are intentionally the unit instead, state that explicitly and do not compare the result with the earlier 9-of-11 direction result.

### Updated verdict

The production and verifier defects found earlier are corrected. The remaining decision blockers are **v29-P2-05** (measurement denominator) and the already documented need to validate whether the target of eight stalls corresponds to felt difficulty. **v29-P3-01** is documentation cleanup and does not block the experiment.

---

## Re-check after the direction-unit correction (2026-08-20)

**v29-P2-05 is closed.** The confirmation report now reduces qualifying seed rows to one deterministic observation per gained direction, marks the selected row, and retains all seed rows for auditability. This restores the direction-level denominator used by the claim under test.

### v29-P1-02 - The confirmation runner sends packages without a reveal to a gate that correctly refuses them

**Severity:** P1  
**Location:** `discovery/batting-order/confirm.py:160`, `forge/tests/test_lineup_fallback_is_adopted.py:246`

`_measure()` now correctly calls `certify_for_publication()`, but `_package()` still constructs a `Package` without `reveal`. The corrected end-to-end test explicitly records that the publication gate refused its first package for a missing reveal, and fixes that fixture by supplying a `Reveal`. The confirmation runner does not carry the same fix.

As a result, a fallback board can reach and pass every arithmetic layer and still be recorded as `publishable=False` solely because the measurement package is incomplete. Since `_covered()` only counts publishable rows and criterion 1 says that zero added boards overturns adoption, this can make the experiment reject the mechanism without measuring it. This is not an edge case: every row produced by this runner uses the same package builder.

**Recommended fix:** construct the confirmation package through the same production package-building path, including its reveal, rather than maintaining another partial `Package(...)` assembly. If reuse is not currently possible, populate a complete `Reveal` from the loaded source metadata and add an assertion before the expensive run that one pinned produced package passes the gate for reasons unrelated to the treatment.

### Updated verdict

Do not run or interpret `confirm.py` yet. The direction denominator is repaired, but **v29-P1-02 makes the publication result structurally zero or gate-refused until the package includes its reveal**. After that repair, the remaining source issue is the non-blocking stale adoption comment in `lineup_fallback.py` from **v29-P3-01**. The unresolved product question about whether eight stalls corresponds to felt difficulty remains outside this code defect.

---

## Re-check after the reveal correction (2026-08-20)

**v29-P1-02 is closed.** `confirm.py` now builds its reveal through the production writer's `reveal_for()` function, so the measurement and production paths share the same reveal contract. Importing that writer does not execute generation: its side effects are limited to imports and path setup, while `main()` remains guarded.

The new `_preflight()` is also correctly placed before the expensive loop. It submits an unerased package to both the arithmetic verifier and `certify_for_publication()` and aborts loudly if the instrument cannot publish the trivial control. That directly prevents the missing-reveal failure from being recorded as a treatment result.

**No new P1 or P2 finding was found in the files changed for this correction.** The only code-review item still open from v29 is the non-blocking stale adoption statement in `lineup_fallback.py` under **v29-P3-01**. Separately, the experiment still cannot establish that eight stalls corresponds to human-perceived difficulty; that is an outstanding product-validation question rather than a defect in this correction.

---

## Final re-check of v29-P3-01 (2026-08-20)

**v29-P3-01 is closed.** The `division_against_chain()` documentation now states the actual production contract: plain-path boards carry no lineup-arithmetic deductions, fallback boards may carry them, and `LINEUP_DIVISION_SHARE_CAP` bounds how much is accepted. This removes the last contradiction between the adopted fallback and its source documentation.

**No v29 code-review findings remain open.** The separate human-validation question about whether eight stalls corresponds to felt difficulty is still unresolved, but it is not a source-code defect and does not reopen this review.
