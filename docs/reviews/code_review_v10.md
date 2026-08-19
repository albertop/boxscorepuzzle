# Code Review v10

**Date:** 2026-08-19  
**Method:** Static review only. No tests, linters, type checkers, application commands, or Git commands were run.  
**Scope:** Changes made after `code_review_v09.md`, their directly affected contracts and tests, all project Markdown guidance, and the unresolved-item register in `docs/reviews/todo.md`. `_not_in_use` was excluded.

## Executive summary

This review found four new issues: three P2 reliability defects in the revised footnote-group experiment and one P3 package-boundary defect. The production signing-key guard and destination split address `v09-P1-01`; constructor rejection of unreadable schemas addresses `v09-P2-01`. The revised group experiment now measures real solver behavior, but its blockage and conditional-rate calculations still do not match the questions stated by the report.

No previously recorded item from `docs/reviews/todo.md` is repeated here. In particular, the old `discovery/footnote-groups/results.txt` output is treated as the already-known invalid result covered by `v09-P2-02`, not as a new finding.

| ID | Priority | Perspective | Finding |
|---|---:|---|---|
| `v10-P2-01` | P2 | QA / puzzle logic | The blockage metric observes deductions that occur, so it misses the strongest form of blocked progress |
| `v10-P2-02` | P2 | QA / data analysis | A failed erasure trial is silently counted as a non-blocking trial |
| `v10-P2-03` | P2 | QA / puzzle logic | The advertised conditional derivability rate uses the unconditional population as its denominator |
| `v10-P3-01` | P3 | Python / backend | Programmatic packages with non-string slot references escape the package error boundary |

## Findings

### `v10-P2-01` - The blockage metric observes deductions that occur, so it misses the strongest form of blocked progress

**Locations:** `discovery/footnote-groups/measure.py:110`, `discovery/footnote-groups/measure.py:114`, `forge/tests/test_group_metrics.py:45`

**Problem:** A group is marked as blocking only when the treatment trace contains a successful deduction outside the hidden group whose recorded dependencies intersect the group. That is evidence that a resolved group value was used by one solver path; it is not evidence that the rest of the puzzle had to wait for the group assignment.

When hiding the group prevents an outside deduction entirely, no corresponding trace step exists and the metric returns `False`. This creates a false negative for the strongest possible blockage. The reverse is also possible: solver ordering may choose a dependency through the group even when an independent deduction path exists, creating a false positive for causal blockage.

The behavioral test does not protect the predicate. It asserts that some outside deductions exist, but never asserts that the production expression `hidden & step.depends_on` can become true or that removing the group changes outside progress.

**Impact:** The experiment can report that a footnote group does not gate the board precisely when hiding it prevents downstream progress. A generator or UI decision based on that percentage could expose an assignment before it is needed or hide one that is required for a fair solve.

**Recommendation:** Run a paired counterfactual for each trial. Solve the same erased puzzle once with the group assignment available and once with the group additionally hidden, then compare the outside-cell fixed-point closure and, if timing matters, deduction depth. Define blockage from outside cells derivable in the baseline but absent or delayed in the treatment. Keep direct dependency use as a separate metric. Add a behavioral fixture where hiding the group removes a known outside deduction and assert the final production predicate, not just trace activity.

### `v10-P2-02` - A failed erasure trial is silently counted as a non-blocking trial

**Locations:** `discovery/footnote-groups/measure.py:90`, `discovery/footnote-groups/measure.py:91`, `discovery/footnote-groups/measure.py:114`

**Problem:** If `erase(..., target_stalls=8, ...)` returns no puzzle, the code substitutes an empty erased set. The group record has only a Boolean `blocked` field, so an unobserved trial becomes indistinguishable from a successfully measured negative and remains in the report denominator.

**Impact:** The blockage rate is biased downward whenever the requested erasure cannot be produced. The bias can also be selective: board shapes that are harder to erase may have different group behavior, so silently treating them as negatives can distort comparisons among design alternatives.

**Recommendation:** Represent the result as `True`, `False`, or unmeasured. Exclude unmeasured trials from the rate, report attempted and successful trial counts for every cohort, and fail the experiment when coverage falls below an explicit threshold. Add a test with an eraser stub that returns `None` and assert that the sample is reported as missing rather than non-blocking.

### `v10-P2-03` - The advertised conditional derivability rate uses the unconditional population as its denominator

**Locations:** `discovery/footnote-groups/measure.py:100`, `discovery/footnote-groups/measure.py:142`

**Problem:** The report describes derivability as a question about groups with exactly one completion: "of those, could the restricted solver derive it?" The derivability table nevertheless passes all groups to `report(...)`. Non-unique groups therefore contribute negative observations to a conditional rate whose denominator should contain only `completions == 1` groups.

**Impact:** As soon as the corpus contains ambiguous groups, the published derivability percentage understates solver coverage and conflates two different failure modes: no unique assignment and a unique assignment outside the solver's repertoire. That prevents the experiment from answering whether uniqueness alone is sufficient for the current solver.

**Recommendation:** Filter the derivability cohort to `group.completions == 1` before calculating percentages. Publish both the qualifying count and total count beside every percentage. Add a mixed fixture with one unique/derivable group and one ambiguous group; the conditional derivability rate should remain 100%, while the uniqueness rate should reflect both groups.

### `v10-P3-01` - Programmatic packages with non-string slot references escape the package error boundary

**Locations:** `forge/src/boxscore_package/format.py:355`, `forge/src/boxscore_package/format.py:474`, `forge/src/boxscore_package/format.py:483`, `forge/src/boxscore_package/format.py:499`

**Problem:** The JSON parser verifies that every slot reference is a string before calling `_check_slot_references`, but direct `Package(...)` construction does not. `_check_slot_references` sends each value directly to the regular expression. A value such as `1` or `None` raises a raw `TypeError` rather than the package-level `PackageError` used for malformed data.

**Impact:** Internal producers, migrations, and tests can terminate with an implementation exception instead of a stable validation diagnostic. The two supported construction paths also expose different error contracts for the same malformed field.

**Recommendation:** Move the element type check into `_check_slot_references` so both JSON parsing and direct construction share it. Raise `PackageError` with the offending index and expected grammar. Add direct-constructor tests for an integer, `None`, and a mixed sequence, in addition to the existing serialized-input coverage.

## Security review

No new OWASP-class finding was identified in the changed surface. Production mode now derives the public key from the supplied private key, compares it with the reader's pinned key before filesystem mutation, and publishes only to the served destination after that check. Ephemeral mode uses a distinct non-served destination. Because this review has no new security finding, no attack-scenario template is applicable.

## Perspective coverage

| Perspective | Result |
|---|---|
| Python principal engineer | Found the inconsistent runtime validation boundary in `Package` construction |
| QA and reliability | Found three experiment-contract and denominator defects; current tests do not exercise the blockage predicate |
| Frontend engineer | No changed frontend surface and no new finding |
| Security / OWASP | The v09 trust-domain defect is remediated; no new issue found |
| Backend architect | Output destination selection is now explicit; one package error-boundary issue remains |
| Baseball / boxscore domain | The four-cell footnote group remains aligned with the documented boxscore assignment; no new domain-integrity issue found |
| Kakuro / logic-puzzle design | Cardinality and derivability are now separate, but blockage and the conditional derivability denominator are still unsound |
| UX / graphic design | No changed presentation surface and no new finding |

## Further improvements

1. Give discovery outputs a result-schema version plus the instrument configuration, seed, attempted count, successful count, and source revision so stale measurements cannot look current.
2. After correcting the estimands, run multiple deterministic seeds per direction and report dispersion rather than presenting one erasure as a population rate.
3. Replace source-text assertions in the changed tests with calls through the public behavior whenever practical; source strings prove that words exist, not that the safety property holds.

## Residual risk

This was a static review. Runtime success, corpus coverage, statistical values, and compatibility with the complete test suite were deliberately not verified. The existing `results.txt` should not be interpreted as output from the revised instrument until a new run is explicitly performed and identified.
