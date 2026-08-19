# Code Review v15

**Date:** 2026-08-19  
**Method:** Static review only. No tests, linters, type checkers, application commands, Git commands, or process inspection were run.  
**Scope:** Files changed after `code_review_v14.md`, their affected contracts and tests, the previously read project guidance, and the updated `docs/reviews/todo.md`. Generated caches and `_not_in_use` were excluded. The zero-byte `run.log` contains no result to review.

## Executive summary

This review found three new issues: one P1 provenance defect and two P2 boundary/preflight defects. The v14 repairs are present: result schema 4 hashes the measured cell values and slots, lists per-direction digests, hashes tracked diffs and untracked bytes, rejects incomplete identity before loading data, and protects the slot-reference container with direct tests. The remaining P1 is that tracked status and tracked content are captured by separate commands and can contradict each other while `_describe()` reports `clean`.

The backlog records every v01-v14 finding as closed except `v05-P1-02`. None is repeated here. The issues below concern new implementation details in the v14 remediation.

| ID | Priority | Perspective | Finding |
|---|---:|---|---|
| `v15-P1-01` | P1 | QA / reproducibility | Separate status and diff snapshots can certify a dirty tree as clean |
| `v15-P2-01` | P2 | Python / reliability | Output preflight checks only that the parent directory exists |
| `v15-P2-02` | P2 | Python / backend | Runtime accepts list references while the public type contract rejects them |

## Findings

### `v15-P1-01` - Separate status and diff snapshots can certify a dirty tree as clean

**Locations:** `discovery/footnote-groups/measure.py`, `identify()`, `_describe()`, and `_bytes_of()`; `forge/tests/test_group_metrics.py`, `TestTheArtifactDeclaresItself`

**Problem:** `identify()` first runs `git status --porcelain` to obtain paths and then runs `git diff --binary HEAD` to obtain bytes. Those are two observations of a mutable working tree. If a tracked dependency changes after status reports no tracked paths but before diff reads the change, `_describe([], nonempty_diff)` returns `clean` because it ignores `contents` whenever `paths` is empty. The old revision plus `tracked changes clean` can then describe execution with a dirty solver, eraser, package, or verifier dependency not covered by the three-file instrument hash.

The opposite transition is conservative but still inconsistent: status can name a modified path that is restored before diff, producing a dirty digest over a path plus an empty diff. In both cases the stamp combines facts that never represented one repository state.

Untracked reads have a related fail-open edge. `_bytes_of()` replaces unreadable content with the fixed marker `<unreadable>` and still returns a publishable digest. Two different unreadable files at the same path are therefore indistinguishable even though the provenance block claims to identify content.

The tests prove that two byte strings produce different digests when the same non-empty path list is supplied, and that a failed diff becomes unknown. They do not test disagreement between path and content snapshots or unreadable untracked files.

**Impact:** A canonical `COMPLETE` artifact can claim a clean or fully identified tree even when a decision-bearing dependency changed during identity capture or could not be read. This preserves the exact evidence-integrity failure the provenance mechanism exists to prevent and can attach experimental results to the wrong code state.

**Recommendation:** Treat status and diff disagreement as `unknown`, never as clean. At minimum, a non-empty diff with no tracked status paths must fail closed, and tracked paths with an empty diff must be rechecked or marked inconsistent. Prefer deriving both the path set and content digest from one binary diff snapshot, using status separately only for untracked discovery. Parse porcelain with `-z` to preserve filenames exactly. Make `_bytes_of()` return failure on any unreadable entry and reject publication. Add adversarial tests for clean-status/non-empty-diff, dirty-status/empty-diff, files changing between observations, quoted filenames, and unreadable untracked content.

### `v15-P2-01` - Output preflight checks only that the parent directory exists

**Locations:** `discovery/footnote-groups/measure.py`, early output check in `main()` and `publish()`; `forge/tests/test_group_metrics.py`, `TestTheRunRefusesBeforeItSpendsAnything`

**Problem:** The early gate tests only `out.parent.is_dir()`. An existing directory at the output path, a read-only destination directory, or another condition preventing creation and replacement passes that check. The instrument then performs the complete database load, three-seed erasure run, and all solves before `pending.write_text()` or `pending.replace()` discovers the failure.

The test named `test_an_unwritable_destination_is_found_before_the_loader` supplies a nonexistent parent. It proves missing-directory detection, not writability or replaceability. The publication failure test proves cleanup after a destination-directory collision, but that collision remains discoverable only after the expensive run when entered through `main()`.

**Impact:** A run guaranteed to produce no artifact can again consume hours while appearing healthy. This is the same operational consequence v14-P2-01 moved the provenance check to prevent, now one field over in an incomplete destination preflight.

**Recommendation:** Before `load()`, reject `out` when it is a directory and create a uniquely named same-directory probe with exclusive creation, write, flush, close, and cleanup. If replacing an existing file is required, verify that operation through a harmless temporary target or acquire the publication lock early and retain it through the run. Add tests for an existing directory at `out`, denied creation in the parent, and replacement failure, each asserting the loader is never called.

### `v15-P2-02` - Runtime accepts list references while the public type contract rejects them

**Locations:** `forge/src/boxscore_package/format.py`, `Package.slot_references`, `Package.__post_init__()`, and `_check_slot_references()`; `forge/tests/verify/test_boundary.py`, `test_a_list_is_stored_as_a_tuple_the_caller_cannot_reach`

**Problem:** The repaired constructor deliberately accepts both tuples and lists and canonicalizes a list to a tuple. The dataclass field remains annotated as `tuple[str, ...] | None`. A statically checked caller cannot pass the supported list input without an argument-type error, including the new regression test itself under a strict test type-checking command.

The runtime API and type API therefore describe different languages: runtime and documentation say list input is accepted and normalized, while the constructor signature says list input is invalid. Changing `_check_slot_references()` to accept `object` makes the runtime guard honest but does not change the generated dataclass initializer's public annotation.

**Impact:** Typed producers and migrations either avoid a supported normalization path, add suppressions, or fail static validation. The shared package boundary once again applies different contracts depending on how the caller is checked, even though runtime serialization is now safe.

**Recommendation:** Choose one public contract and encode it consistently. If only tuples are supported, reject lists and update the mutation test accordingly. If normalization is intentional, provide a custom initializer or factory accepting `Sequence[str]` while storing a private tuple field exposed through a tuple-typed property. Add a signature/type assertion so the accepted constructor input and stored immutable output cannot drift apart again.

## Security review

No new OWASP-class issue was identified. The Git commands use fixed argument vectors without a shell, output publication uses a private same-directory temporary path, and the package issue is a static/runtime API mismatch rather than an exposed input bypass. Because there is no security finding, attack scenario, exploitation method, business impact, and security remediation fields are not applicable.

## Perspective coverage

| Perspective | Result |
|---|---|
| Python principal engineer | Found inconsistent constructor typing and incomplete destination preflight |
| QA and reliability | Found a two-snapshot provenance race that can report clean and missing adversarial coverage |
| Frontend engineer | No changed frontend surface and no new finding |
| Security / OWASP | No new externally exploitable trust-boundary issue |
| Backend architect | Runtime normalization and static package contracts disagree |
| Baseball / boxscore domain | Cell values and lineup slots are now included in the input digest; no new domain-mapping issue found |
| Kakuro / logic-puzzle design | Metric formulas and per-board digests remain coherent; repository identity can still misattribute them |
| UX / graphic design | No player-facing change; operator-facing `clean` can describe an inconsistent snapshot |

## Further improvements

1. Make `RunIdentity.publishable` require a loaded input identity for the final publication gate while allowing a separate repository-only preflight before `load()`.
2. Parse `--output` with `argparse` so a missing value produces a controlled error rather than `IndexError`.
3. Add an explicit Ruff/CI command naming both `src` and `../discovery`; the current `extend-include` and ignores configure discovery but still do not cause routine commands to lint it.

## Residual risk

This was a static review. No active process was inspected or interrupted, and no Git race, unreadable file, permission failure, package type-check, database sample, linter, or test suite was executed. Numerical results, current process state, runtime provenance, and full-suite compatibility remain unverified by design.
