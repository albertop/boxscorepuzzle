# Code Review v14

**Date:** 2026-08-19  
**Method:** Static review only. No tests, linters, type checkers, application commands, Git commands, or process inspection were run.  
**Scope:** Files changed after `code_review_v13.md`, their affected contracts and tests, the previously read project guidance, and the updated `docs/reviews/todo.md`. Generated caches and `_not_in_use` were excluded. The zero-byte `run.log` contains no result to review.

## Executive summary

This review found three new issues: one P1 evidence-integrity defect and two P2 reliability/test defects. The v13 changes correctly capture repository identity before measurement, separate tracked and untracked state, canonicalize slot-reference containers, and extract result publication behind behavioral tests. The remaining P1 is that the values advertised as content identities do not hash the content they claim to identify, and the artifact does not render the sampled direction identifiers it says it preserves.

The updated backlog records every v01-v13 finding as closed except `v05-P1-02`. None is repeated here. The findings below concern incomplete behavior introduced by those closures. Because `todo.md` records the group run as active, `v14-P1-01` applies to the artifact that run would currently produce.

| ID | Priority | Perspective | Finding |
|---|---:|---|---|
| `v14-P1-01` | P1 | QA / reproducibility | `RunIdentity` hashes names and status lines instead of the loaded input and dirty contents |
| `v14-P2-01` | P2 | Python / reliability | A non-publishable identity is rejected only after the expensive run completes |
| `v14-P2-02` | P2 | QA / backend | The slot-reference container repair has no regression test |

## Findings

### `v14-P1-01` - `RunIdentity` hashes names and status lines instead of the loaded input and dirty contents

**Locations:** `discovery/footnote-groups/measure.py`, `RunIdentity.with_inputs()`, `identify()`, `_describe()`, and `provenance()`; `forge/tests/test_group_metrics.py`, `TestTheArtifactDeclaresItself`

**Problem:** `with_inputs()` claims to digest the boards as loaded, but it hashes only strings of the form `game_id:offense_team`. If any batting value, footnote value, pitching value, lineup slot, or other decision-bearing field changes for the same game and side, the input digest remains identical. The test changes the sample by adding another identifier; it never holds the identifiers fixed while changing board content.

`RunIdentity.directions` stores the sorted identifiers, but `provenance()` prints only their count. The report says the identifiers sit beside the digest so the digest can be checked, yet the canonical artifact contains neither the list nor a sidecar manifest from which it can be reconstructed.

The same mismatch exists for repository dirtiness. `_describe()` hashes sorted porcelain status lines, which identify status codes and paths, not file bytes. Two tracked edits to the same files, or two different versions of the same untracked helper, produce the same digest. The dedicated instrument hash covers only `measure.py` and `metrics.py`; dirty solver, loader, erasure, verifier, or shadowing helper contents are not identified by content.

**Impact:** Two runs over different boxscore values can carry the same input identity, and two runs using different dirty dependency code can carry the same tree identity. The artifact cannot reveal which direction set produced it because that set is discarded during rendering. This defeats the provenance mechanism at the exact point it exists to distinguish experimental evidence and means the currently active run cannot produce the reproducible identity described in `todo.md`.

**Recommendation:** Canonically serialize every decision-bearing loaded input before measurement, including direction identifier, side, slots, batting, footnotes, pitching, totals, and line score, with field names and explicit record boundaries. Store a per-direction digest and an aggregate digest, and render the sorted identifiers or publish an atomically paired manifest containing them. For tracked changes, hash `git diff --binary HEAD` or the bytes of every relevant modified file. For untracked dependencies, hash path plus file bytes, not the porcelain line. Add tests where identical identifiers carry different values and where the same dirty path carries different bytes; both identities must change. The active run should not be accepted as canonical evidence until this identity is corrected and the run is restarted.

### `v14-P2-01` - A non-publishable identity is rejected only after the expensive run completes

**Locations:** `discovery/footnote-groups/measure.py`, `main()` calls to `identify()`, `load()`, `groups_in()`, and the final `identity.publishable` check

**Problem:** `identify()` determines before loading data whether revision, tracked-state, or untracked-state collection failed. `main()` nevertheless evaluates `identity.publishable` only after loading the database sample, erasing every direction under three seeds, solving every group, and rendering the report.

The later input digest cannot repair an `unknown` repository field, so the outcome is known before the expensive work starts. A Git timeout, unavailable executable, or failed status command therefore guarantees that the run will be discarded, but the instrument spends its full runtime discovering nothing new before refusing publication.

**Impact:** A transient provenance failure can consume hours of CPU and database work and appear to operators as a progressing experiment that was never eligible to produce an artifact. This delays the already repeatedly restarted decision run and makes operational diagnosis unnecessarily expensive.

**Recommendation:** Check `identity.publishable` immediately after `identify()` and before `load()`. Keep a second defensive assertion before publication if desired. Add a test that injects a non-publishable identity and replaces `load` with a function that fails the test if called; assert the controlled provenance error occurs first.

### `v14-P2-02` - The slot-reference container repair has no regression test

**Locations:** `forge/src/boxscore_package/format.py`, `Package.__post_init__()` and `_check_slot_references()`; `forge/tests/verify/test_boundary.py`, package-construction tests; `docs/reviews/todo.md`, v13-P2-01 closure

**Problem:** The code now rejects a bare string and canonicalizes an accepted list to a tuple, which addresses v13-P2-01. No package-boundary test changed with that repair. The current group-metric tests contain no package construction, and the existing boundary coverage checks malformed elements rather than the outer string/list cases.

The backlog says the string rejection and post-construction list mutation were verified both ways, but reverting `_check_slot_references()` to accept any `Sequence` or removing the tuple canonicalization would not fail the reviewed tests. Under the project's explicit closure rule, the finding has a fix but not the regression guard required to call it closed.

**Impact:** The constructor can regress to accepting `"123456789"` or retaining a caller-owned mutable list without an automated signal. That would restore a package object whose runtime shape and serialized signature payload can change after construction while the review ledger still reports the boundary closed.

**Recommendation:** Add direct `Package(...)` tests at the shared boundary. Assert a bare string raises `PackageError`; assert a passed list is stored as an equal tuple; mutate the original list and prove the package serialization is unchanged. Include the accepted tuple path so a guard that rejects every container cannot pass.

## Security review

No new OWASP-class issue was identified. The reviewed changes concern an offline experiment, local repository provenance, and a programmatic package boundary. Package signature verification remains the security control for payload mutation. Because there is no security finding, attack scenario, exploitation method, business impact, and security remediation fields are not applicable.

## Perspective coverage

| Perspective | Result |
|---|---|
| Python principal engineer | Found a delayed fail-closed check and missing package-boundary regression coverage |
| QA and reliability | Found content identities that hash labels rather than values and a guaranteed-failure run that proceeds for hours |
| Frontend engineer | No changed frontend surface and no new finding |
| Security / OWASP | No new externally exploitable trust-boundary issue |
| Backend architect | Result publication is now testable; package container normalization remains unguarded by tests |
| Baseball / boxscore domain | The input digest omits the actual boxscore and lineup-slot values that determine group behavior |
| Kakuro / logic-puzzle design | Metric formulas remain coherent, but different puzzle inputs can share one provenance identity |
| UX / graphic design | No player-facing change; operator-facing provenance overstates what its digests identify |

## Further improvements

1. Increment `RESULT_SCHEMA` when the input-identity contract changes so pre-fix and post-fix artifacts cannot both present as schema 3.
2. Validate the `--output` argument and destination parent before loading DGL, alongside the early provenance gate.
3. Replace discovery-specific Ruff exceptions with an explicit command or CI target that names both `src` and `../discovery`; `extend-include` alone still does not execute Ruff over that tree.

## Residual risk

This was a static review. The active process was not inspected or interrupted, and no database sample, digest, package constructor, Git branch, publication failure, linter, or test suite was executed. Numerical results, current process state, runtime provenance, and full-suite compatibility remain unverified by design.
