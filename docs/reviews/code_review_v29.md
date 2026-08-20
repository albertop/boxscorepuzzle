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

No P0 or P1 finding was identified. v29 found **two P2 findings and one P3**. The independent lineup arithmetic
and relation implementations agree on the cases covered by the new tests, slot parsing is taken from
the signed package boundary, and the conditional retry remains scoped to the production writer rather
than turning the constraint on globally. The blocking issue is integration: all four verification
layers must reason about the same published clue set, and the gate needs one non-vacuous fallback package
test before adoption can be considered complete.

Recommended order:

1. Keep package slots threaded through every model-bearing layer and make the fallback test fail rather than skip when its precondition disappears.
2. Pass the fallback-produced package through `certify_for_publication()`, not only `verify()`.
3. Finish updating the active module contracts and superseded decision text.
