# Code Review v07

**Date:** 2026-08-18  
**Method:** static review only; no tests, scripts, browser checks, or generated-artifact validation were run  
**Scope:** project context established by all Markdown documentation, followed by the post-v06 changes in `discovery` and `forge`; `_not_in_use` excluded  
**Backlog policy:** findings already recorded as pending in `docs/reviews/todo.md` are intentionally not repeated

## Executive summary

The post-v06 changes correctly establish one shared cell order for the open-versus-given comparison, retain zero-stall boards, separate the main footnote-group report by row/term cohort, strengthen renderer assertions, and remove the obsolete prototype from the active set.

Two new, deduplicated findings remain. The first can invalidate the experiment's stated control conclusion by comparing differently composed term-count populations. The second leaves the active-prototype invariant open to the multi-digit form of the exact suffix it is intended to reject. No new OWASP/security issue was found in this delta.

## Findings

### v07-P1-01: The footnote control confounds assignment with the distribution of term counts

**Personas:** Python Principal Developer, QA/Reliability Engineer, baseball/boxscore specialist, Kakuro/logic-puzzle specialist  
**Confidence:** High

The experiment explains the control as a comparison between a one-row group with two terms and a two-row group with two terms. That is a valid way to isolate assignment ambiguity: term count stays fixed and only the number of possible carrier rows changes. The implementation instead compares all one-row groups with two **or more** terms against all two-row groups with two **or more** terms.

Evidence:

- [discovery/footnote-groups/measure.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/footnote-groups/measure.py#L151) builds both control cohorts with `terms >= 2`.
- [discovery/footnote-groups/measure.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/footnote-groups/measure.py#L153) prints each mixed cohort as one percentage.

Multi-row groups have more opportunities to contain footnote events, so their term-count distribution can differ systematically from the one-row distribution. A lower success rate for the two-row `2+` cohort can therefore be caused by carrying more terms, by assignment ambiguity, or by both. The aggregate cannot distinguish those explanations even though its accompanying text claims that it can.

**Impact:** A representation decision could attribute failure to unknown carrier assignment when the actual threshold is event volume. That can lead to adding row-reference UI or giving away attribution unnecessarily, while leaving the real high-term-count problem unsolved.

**Recommended fix:** Make the named control exactly `terms == 2` on both sides. Then report the same comparison separately for every exact term count with adequate `n`. If one summary effect is still needed, match or standardize the term-count distribution across row-count cohorts before comparing them. Treat the already stratified `(rows, terms)` table as authoritative and remove any causal wording from an unmatched aggregate.

### v07-P2-01: The prototype guard accepts obsolete suffixes with more than one digit

**Personas:** QA/Reliability Engineer, Frontend Engineer, baseball/boxscore specialist, UX/graphic-design specialist  
**Confidence:** High

The active-prototype guard is intended to reject every numbered position label, but its regular expression permits exactly one digit after the hyphen. Labels such as `P-10` or `PH-12` therefore pass. Those values are within the shape of the old numbering convention, especially for positions repeated many times in long or substitution-heavy games.

Evidence:

- [forge/tests/test_prototype_shell.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/tests/test_prototype_shell.py#L68) uses `-\d` rather than `-\d+` or an equivalent full-label parser.
- [forge/tests/test_prototype_shell.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/tests/test_prototype_shell.py#L82) proves the check only against the archived page's one-digit examples.

**Impact:** A regenerated active sample can reintroduce the obsolete visual language while the domain guard remains green. That sample could then be used to evaluate grouping, spacing, or footnote comprehension and feed stale assumptions back into the product renderer.

**Recommended fix:** Match the complete forbidden suffix form, for example `[A-Z0-9]{1,3}-\d+`, with appropriate token boundaries. Add a synthetic can-it-fire case containing both `PH-2` and `PH-10`; do not rely only on one historical file to define the adversarial space. A small HTML parser or fixture-level label extraction would be more robust than matching raw markup if these prototypes stop being one-line generated documents.

## Persona coverage

| Persona | Result |
|---|---|
| Python Principal Developer | Finding v07-P1-01. No additional new code-quality or performance issue was promoted from this delta. |
| QA / Reliability Engineer | Findings v07-P1-01 and v07-P2-01. Tests were not executed by request. |
| Frontend Engineer | Finding v07-P2-01. No application frontend exists yet; review was limited to active research prototypes and their guards. |
| Security Engineer | No new OWASP-style finding. Authentication, authorization, sessions, cookies, uploads, and multi-tenant boundaries are not implemented in the reviewed delta; prior package-signing concerns remain governed by the backlog and are not duplicated here. |
| Backend Architect | No new unique finding. Existing packaging, manifest, concurrency, and schema decisions already tracked in `todo.md` were excluded. |
| Baseball / boxscore specialist | Findings v07-P1-01 and v07-P2-01. Slot grouping remains the correct domain key; the control must hold event count fixed before attributing a difference to assignment. |
| Kakuro / logic-puzzle specialist | Finding v07-P1-01. The main per-cell table is useful, but the unmatched control cannot support a causal interpretation. |
| UX / graphic-design specialist | Finding v07-P2-01. Archiving the stale sample is appropriate; the active-set guard needs to cover the full obsolete label form. |

## Positive changes observed

- `footnotes-open-or-given` now orders the union once and derives the given treatment by filtering, preserving the relative order of shared cells.
- A zero-stall walk is now retained as a real result rather than dropped as a failure.
- The main footnote-group technique output now uses the same row/term dimensions as the uniqueness output, and the tail is honestly labeled `4+`.
- Footnote renderer checks now compare structured reference sets instead of prefix-sensitive substrings.
- The suffixed-label prototype is outside the active glob and carries an archival guard.

## Recommended order of work

1. Replace the `2+` control with exact, matched term-count comparisons before running or interpreting `footnote-groups`.
2. Expand the prototype suffix guard and its adversarial fixture.
3. Run the corrected research instruments only when validation is requested, then record their outputs and decisions in the existing documentation flow.

## Review boundary

This review does not restate the slots-package schema decision, footnote representation decision, hand-solve pack migration, signing/manifest work, or any other item already pending in `docs/reviews/todo.md`. No source code was changed; this Markdown review is the only created file.
