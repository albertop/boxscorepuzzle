# Code Review v12

**Date:** 2026-08-19  
**Method:** Static review only. No tests, linters, type checkers, application commands, or Git commands were run.  
**Scope:** Files changed after `code_review_v11.md`, their affected contracts and tests, the previously read project guidance, and the updated `docs/reviews/todo.md`. Generated caches and `_not_in_use` were excluded.

## Executive summary

This review found four new issues: one P1 test-oracle defect and three P2 reliability defects in coverage accounting, provenance, and result publication. The production formulas introduced to close v11 are materially improved: `stops_progress()` restores the group in the baseline, report rows own their eligibility and denominators, rates use group trials, and the instrument owns its output artifact. The P1 is that the test claimed as the regression guard would still pass with the exact broken counterfactual it replaced.

No existing item from `docs/reviews/todo.md` is repeated. V11 remains recorded as closed; the findings below concern incomplete guards and new behavior introduced by its remediation, not the original four defects themselves.

| ID | Priority | Perspective | Finding |
|---|---:|---|---|
| `v12-P1-01` | P1 | QA / puzzle logic | The production metric tests accept the broken implementation they are meant to reject |
| `v12-P2-01` | P2 | QA / data analysis | Coverage labels group-trial counts as erasure attempts and successes |
| `v12-P2-02` | P2 | QA / reproducibility | Provenance still publishes as complete when it cannot identify the code or data |
| `v12-P2-03` | P2 | Python / reliability | Every run publishes through the same pending filename |

## Findings

### `v12-P1-01` - The production metric tests accept the broken implementation they are meant to reject

**Locations:** `forge/tests/test_group_metrics.py`, `TestTheBaselineRestoresTheGroup.test_an_erasure_that_hides_the_group_still_leaves_a_real_comparison`; `TestCardinalityAndDerivabilityAreDifferentQuestions.test_derivability_is_asked_of_the_solver_not_of_the_board`; `discovery/footnote-groups/metrics.py`, `stops_progress()` and `derivable()`

**Problem:** The adversarial baseline test correctly proves that its locally constructed baseline and treatment differ, but its only assertion against the production function is:

```python
assert metrics.stops_progress(shape, values, erased, hidden) in (True, False)
```

Both the corrected function and the exact pre-v11 function always return a Boolean, so both pass. The separate assertion showing that the old local construction compares a board with itself is not connected to the production call. Reverting `stops_progress()` to remove all of `erased` from the baseline would therefore leave this class green.

The derivability test repeats the same shape by asserting only that `metrics.derivable(...)` is either `True` or `False`. It tests the return type, not whether the restricted solver reaches a known group or refuses a known counterexample.

**Impact:** The project records v11-P1-01 as closed under the rule that a fix must have a test that fails without it, but the test does not satisfy that rule. A regression can contaminate the next long-running experiment while the named guard reports success, recreating the project's highest-risk failure mode: a blind measurement returning a plausible number.

**Recommendation:** Test the production predicate with a strict expected result. The most stable unit test is to replace `metrics.solve` with a deterministic fake whose baseline closure contains a known outside cell only when the group is restored; pass an `erased` set containing the group and assert `stops_progress(...) is True`. Add the inverse fixture and assert `False`. For derivability, use one fixture known to complete and one known not to complete, asserting exact outcomes rather than Boolean membership.

### `v12-P2-01` - Coverage labels group-trial counts as erasure attempts and successes

**Locations:** `discovery/footnote-groups/measure.py`, `groups_in()`, `report()`, `provenance()`, and `main()`

**Problem:** `erase()` is called once per sampled direction and seed, before that direction is expanded into slot groups. The coverage line nevertheless reports `len(groups) * len(SEEDS)` as "erasures attempted." That is the number of group-erasure evaluations, not the number of erasure attempts. Likewise, `sum(group.trials for group in groups)` repeats every successful erasure once for every slot group on its board, yet both the coverage section and provenance say that this many erasures "reached the target."

The repeated count is a valid denominator for the per-group, per-erasure blockage rate. It is not a valid measure of eraser success coverage. A direction with nine groups contributes nine reported successes for one successful call to `erase()`.

**Impact:** Readers cannot determine how often the eraser reached eight stalls, which boards were underexposed, or whether missing trials are concentrated in a cohort. The provenance block can claim more successful erasures than were attempted at the direction level, undermining confidence in otherwise-correct rate denominators.

**Recommendation:** Carry run-level accounting separately from `Group`: sampled directions, attempted erasures, successful erasures, group-erasure trials, and groups with zero exposure. Print and stamp each with an unambiguous label. Keep `sum(group.trials)` only as the denominator for group-trial metrics. Add a report test with two boards carrying different numbers of groups and verify that erasure attempts remain `boards * seeds` while group trials scale with group count.

### `v12-P2-02` - Provenance still publishes as complete when it cannot identify the code or data

**Locations:** `discovery/footnote-groups/measure.py`, `provenance()`; `forge/tests/test_group_metrics.py`, `TestTheArtifactDeclaresItself.test_the_revision_reports_uncommitted_work`

**Problem:** `git describe --dirty` improves on reading a loose ref, but it does not report untracked files. An untracked `metrics.py`, query helper, or other imported source can change the result while the revision appears clean. The stamp also contains no hash or identity for the DGL data snapshot or the sampled direction IDs, so the same revision and parameters can describe different input data.

If Git is absent, times out, or fails, `provenance()` substitutes `unknown`; `main()` still appends `COMPLETE` and atomically replaces the canonical result. The corresponding test does not exercise dirty behavior at all. It merely asserts that the word `revision` appears, which also passes for `revision unknown` and for a clean revision returned over untracked changes.

**Impact:** A result can present itself as complete without enough information to reproduce or distinguish it. Two materially different runs can carry the same stamp, while a run with no repository identity at all can replace the canonical evidence file.

**Recommendation:** Hash the actual `measure.py`, `metrics.py`, and other decision-bearing source loaded by the run, and record the sorted sampled direction IDs plus a stable data-snapshot identifier. If Git metadata is retained, include `git status --porcelain --untracked-files=all` or an equivalent explicit untracked state. Treat `unknown` as non-publishable unless the source hashes provide an independent provenance path. Mock the subprocess in tests and assert clean, tracked-dirty, untracked-dirty, timeout, and unavailable cases exactly.

### `v12-P2-03` - Every run publishes through the same pending filename

**Locations:** `discovery/footnote-groups/measure.py`, final publication block in `main()`

**Problem:** Every process targeting a given output uses `results.txt.pending`. Two overlapping runs can truncate or overwrite the same temporary file, move another run's bytes into the canonical path, or fail when the other process has already renamed the shared pending file. The final `replace()` is atomic for one writer, but a fixed staging name does not establish a single-writer contract.

This recreates a concurrency class already removed from the reference-package publisher: an atomic final rename cannot protect preparation when multiple producers share the object being renamed.

**Impact:** An accidental duplicate launch can publish a result under the wrong run's console message, leave one successful run reporting failure, or corrupt the pending artifact. Because group measurement is long-running, duplicate and overlapping launches are operationally plausible rather than a narrow timing curiosity.

**Recommendation:** Give every run a same-directory pending path containing a PID plus a random nonce, then atomically replace the destination from that private path. Alternatively acquire an exclusive lock and reject a second writer before loading data. Clean the private temporary file in `finally`, validate the output parent before the expensive run, and add a behavioral test proving two prepared artifacts never share a pending path.

## Security review

No new OWASP-class issue was identified. The new subprocess invocation uses a fixed argument vector without a shell, and the reviewed output path is a local operator input rather than an exposed network boundary. Because there is no security finding, attack scenario, exploitation method, business impact, and security remediation fields are not applicable.

## Perspective coverage

| Perspective | Result |
|---|---|
| Python principal engineer | Found the shared pending-file race and weak executable test oracles |
| QA and reliability | Found a P1 guard that passes the former defect plus inaccurate coverage and fail-open provenance |
| Frontend engineer | No changed frontend surface and no new finding |
| Security / OWASP | No new security issue in the offline local instrument |
| Backend architect | Atomic replacement is present, but staging is not isolated per writer |
| Baseball / boxscore domain | Slot grouping and the four footnote columns remain consistent; no new mapping issue found |
| Kakuro / logic-puzzle design | The repaired counterfactual is correct in code but lacks a test that proves its causal result |
| UX / graphic design | No player-facing change; report terminology currently misstates coverage, covered by `v12-P2-01` |

## Further improvements

1. Replace the hand-parsed `--output` flag with `argparse`, validate the parent directory before loading data, and provide a controlled error when the value is missing.
2. Return a structured `RunResult` containing measurements and coverage, then render it separately. This prevents report wording from becoming the only representation of run accounting.
3. Keep the canonical result unchanged until all provenance requirements pass; a completed calculation without reproducible identity should remain a quarantined artifact, not current evidence.

## Residual risk

This was a static review. No test demonstrated that `stops_progress()` returns `True` for a known counterfactual, no database-backed measurement was run, and no concurrency or provenance behavior was exercised. Numerical results, erasure coverage, database state, and full-suite compatibility remain unverified by design.
