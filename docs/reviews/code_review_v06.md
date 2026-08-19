# Code Review v06

**Date:** 2026-08-18  
**Method:** static review only; no tests or project commands were run  
**Scope:** post-v05 changes in `forge`, `discovery`, project documentation, and the HTML research prototypes; `_not_in_use` excluded  
**Backlog policy:** issues already open or pending in `docs/reviews/todo.md` are intentionally not repeated

## Executive summary

The post-v05 work closes several important gaps, especially the unsafe signing-key fallback, the position-label ambiguity experiment, renderer parity coverage, and the mobile document shell. The new footnote research, however, is not yet safe to use for a representation decision. The open-versus-given comparison changes the erasure order between treatments and silently removes zero-stall outcomes, so its reported 47-board paired result does not isolate the effect it claims to measure. The group experiment also aggregates dimensions that its research contract says must remain separate.

Five new, deduplicated findings are listed below: two P1 and three P2. No new OWASP/security finding was identified in the reviewed delta.

## Findings

### v06-P1-01: The open-versus-given experiment is not actually paired by erasure trajectory

**Personas:** Python Principal Engineer, QA/Reliability, Kakuro/logic-puzzle specialist  
**Confidence:** High

The experiment independently builds and orders two different candidate lists. The `given` treatment removes footnote cells before calling the configured ordering, while the `open` treatment includes them; each list is then randomized from a newly seeded RNG. Using the same seed does not preserve the order of the common cells when the input sequence and length differ. Therefore the two walks differ in both treatment and erasure trajectory.

Evidence:

- [discovery/footnotes-open-or-given/measure.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/footnotes-open-or-given/measure.py#L67) filters the treatment-specific candidate list first.
- [discovery/footnotes-open-or-given/measure.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/footnotes-open-or-given/measure.py#L69) independently orders that changed list.
- [discovery/footnotes-open-or-given/measure.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/footnotes-open-or-given/measure.py#L130) then presents the two walks as a pair.

**Impact:** The reported difference can include ordering luck rather than the effect of leaving footnotes open. A schema or printed-representation decision based on this result could be made for the wrong reason, and the apparently unanimous result cannot repair the confound.

**Recommended fix:** Assign one deterministic random priority to every cell in the union, derive one canonical order, and obtain the `given` order only by filtering footnote cells from that order. Preserve the relative order of every common cell. Run several matched seeds and report paired deltas with sample counts and uncertainty, rather than relying on one path per board.

### v06-P1-02: Zero-stall outcomes are silently removed from the paired cohort

**Personas:** Python Principal Engineer, QA/Reliability, Kakuro/logic-puzzle specialist  
**Confidence:** High

`walk()` returns `None` whenever the maximum observed stall count is zero, even though zero is a valid experimental outcome. The caller then keeps a board only when both treatments are truthy. This changes the denominator and preferentially removes the weakest treatment results. The checked-in result says 48 directions were selected but reports only 47 pairs, which is consistent with this path.

Evidence:

- [discovery/footnotes-open-or-given/measure.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/footnotes-open-or-given/measure.py#L85) conflates a valid `ceiling == 0` with failure.
- [discovery/footnotes-open-or-given/measure.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/footnotes-open-or-given/measure.py#L131) drops the entire pair if either side is falsy.
- [discovery/footnotes-open-or-given/results.txt](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/footnotes-open-or-given/results.txt) reports 47 pairs from a 48-direction cohort.

**Impact:** Given-footnote reach and median ceiling are biased upward, and the comparison is no longer a complete paired analysis. A board on which the given treatment makes no progress is especially important evidence, not a failed sample to discard.

**Recommended fix:** Always return a `Walk`, including `ceiling=0`; represent actual load/solve failures with a separate explicit status or exception. Assert that the output pair count equals the eligible cohort, and report failures and zero outcomes separately. Regenerate the result before using it in a design decision.

### v06-P2-01: The footnote-group report aggregates dimensions its contract says must remain separate

**Personas:** Python Principal Engineer, QA/Reliability, baseball/boxscore specialist, Kakuro/logic-puzzle specialist  
**Confidence:** High

The experiment says outcomes must be reported by group size and term count, but the report maps every group with four or more terms into the same bucket and labels that bucket as exactly four terms. Its technique section then aggregates all term counts for each row count. Both choices can conceal the point at which an unassigned group becomes difficult or needs bounding.

Evidence:

- [discovery/footnote-groups/measure.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/footnote-groups/measure.py#L88) uses `min(group.terms, 4)`.
- [discovery/footnote-groups/measure.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/footnote-groups/measure.py#L114) starts a technique report that filters only by row count at line 116.

**Impact:** The instrument can produce a reassuring aggregate while a specific `(rows, terms)` cohort fails. That is exactly the threshold the experiment is intended to discover before selecting a printable notation.

**Recommended fix:** Keep exact term counts as dynamic columns or explicitly use a `4+` bucket if the tail is too sparse. Report uniqueness, dependency, and technique by the same `(rows, terms)` key, always with `n`; add confidence intervals or exact numerators for small cells. Do not approve a representation until the currently empty result file has been generated with the corrected stratification.

### v06-P2-02: The surface-parity tests can pass with wrong footnote references and do not cover every erased section

**Personas:** QA/Reliability, Frontend Engineer, Backend Architect  
**Confidence:** High

The new tests are directionally valuable, but their assertions are weaker than their module-level guarantee. For an erased carrier they reject only the exact prefix `"LABEL: reference"`; a leaked reference later in `"LABEL: first, reference"` passes. For a given carrier they assert only that the label exists, so any reference under that label satisfies the test. The table checks also enumerate only `board.batting`, despite claiming that every erased cell is blank; erased pitching and line-score cells are not compared to rendered output.

Evidence:

- [forge/tests/test_surface_parity.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/tests/test_surface_parity.py#L63) performs the prefix-sensitive negative check.
- [forge/tests/test_surface_parity.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/tests/test_surface_parity.py#L82) checks only the footnote label on the positive path.
- [forge/tests/test_surface_parity.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/tests/test_surface_parity.py#L104) derives blank coordinates only from batting rows.

**Impact:** A renderer regression can disclose an erased footnote after another carrier, attach a term to the wrong row, or reveal erased non-batting values while this guard remains green. That reopens the human-board-versus-graded-board class of failure without necessarily repeating the original implementation bug.

**Recommended fix:** Parse each rendered footnote segment into `label -> set[reference]` and compare it exactly with an expected mapping derived from the puzzle board. Build a complete renderer projection for batting, pitching, line score, and every other erasable section, then assert both directions for every coordinate: erased renders blank and given renders its value. Include a mutation-style fixture that deliberately leaks a second comma-separated carrier and one non-batting value, proving the guard can fire.

### v06-P2-03: A maintained prototype still presents obsolete suffixed position labels

**Personas:** Frontend Engineer, baseball/boxscore specialist, UX/graphic-design specialist  
**Confidence:** High

The current label rule is a bare baseball position plus a separate slot reference. The responsive-shell update touched the prototype suite, but `substitute-grouping-sample.html` still shows labels such as `PH-2`, `PH-3`, `3B-2`, `P-2`, and `P-3`. Nothing on that page marks the sample as historical or incompatible with the current row-identity decision.

Evidence:

- [discovery/board-prototype/substitute-grouping-sample.html](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/board-prototype/substitute-grouping-sample.html#L13) contains the obsolete suffixed labels.
- [forge/tests/test_row_labels.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/tests/test_row_labels.py#L76) establishes that repeated positions are not numbered.

**Impact:** Side-by-side UX evaluation can validate grouping, spacing, and reference comprehension against a visual language the product no longer uses. Reviewers may also copy the stale convention back into future renderers or documentation.

**Recommended fix:** Regenerate this prototype with bare positions and the accepted slot-reference column, or move it to an explicitly historical archive outside the active prototype glob. Add a semantic prototype check that rejects known position suffixes in active samples; shell-string checks alone cannot establish domain parity.

## Persona coverage

| Persona | Result |
|---|---|
| Python Principal Engineer | Findings v06-P1-01, v06-P1-02, and v06-P2-01. No additional unique implementation defect found in the reviewed delta. |
| QA / Reliability Engineer | Findings v06-P1-01, v06-P1-02, v06-P2-01, and v06-P2-02. Tests were not executed by request. |
| Frontend Engineer | Findings v06-P2-02 and v06-P2-03. The new viewport and box-sizing shell is a useful improvement. |
| Security Engineer / OWASP | No new security finding in the post-v05 delta. Existing signing, manifest, and trust-boundary work remains governed by `todo.md` and is not duplicated here. |
| Backend Architect | Finding v06-P2-02. Existing package/manifest architecture items in `todo.md` were excluded from this review. |
| Baseball / boxscore specialist | Findings v06-P2-01 and v06-P2-03. Slot-based footnote grouping is the correct domain direction, subject to corrected reporting. |
| Kakuro / logic-puzzle specialist | Findings v06-P1-01, v06-P1-02, and v06-P2-01. The present measurements should not yet define easy/medium/hard or notation policy. |
| UX / graphic-design specialist | Finding v06-P2-03. No additional unique visual issue was promoted from the research-only prototypes. |

## Recommended order of work

1. Fix matched ordering and retain zero outcomes in `footnotes-open-or-given`, then regenerate its result.
2. Preserve the full `(rows, terms)` stratification in `footnote-groups`, run it, and use that evidence for the notation decision.
3. Strengthen surface parity with exact structured expectations across every erasable section.
4. Regenerate or clearly archive the prototype that still uses suffixed labels.

## Review boundary

This review intentionally does not restate unresolved items from prior reviews, including the pending slots-package schema decision, footnote representation decision, pack migration, and previously recorded signing/manifest concerns. No source code was changed, and no runtime, test, browser, or PDF validation was performed.
