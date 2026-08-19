# Code Review v13

**Date:** 2026-08-19  
**Method:** Static review only. No tests, linters, type checkers, application commands, or Git commands were run.  
**Scope:** Files changed after `code_review_v12.md`, their affected contracts and tests, the previously read project guidance, and the newly updated `docs/reviews/todo.md`. Generated caches and `_not_in_use` were excluded.

## Executive summary

This review found three new issues: one P1 evidence-integrity defect and two P2 boundary/test defects. The v12 formula, coverage, and private-staging repairs are present and internally coherent. The principal remaining risk is that the provenance block is assembled after the long run from current disk and repository state, while the actual input data is not identified at all. It can therefore describe a state different from the one that produced the measurements.

The updated backlog says every v01-v12 finding is closed except `v05-P1-02`. None of those findings is repeated here. The issues below concern new implementation details or incomplete regression protection introduced while closing v12.

| ID | Priority | Perspective | Finding |
|---|---:|---|---|
| `v13-P1-01` | P1 | QA / reproducibility | Provenance is not a snapshot of the code and data that produced the run |
| `v13-P2-01` | P2 | Python / backend | The constructor accepts strings and mutable lists as `slot_references` |
| `v13-P2-02` | P2 | QA / reliability | The private pending-file repair is marked closed without a regression test |

## Findings

### `v13-P1-01` - Provenance is not a snapshot of the code and data that produced the run

**Locations:** `discovery/footnote-groups/measure.py`, `_git()`, `source_hashes()`, `provenance()`, and `main()`; `forge/tests/test_group_metrics.py`, `TestTheArtifactDeclaresItself`

**Problem:** `source_hashes()` and both Git queries run inside `provenance()`, after every board has been measured. This is a long-running database experiment. If `measure.py`, `metrics.py`, the branch, or the working tree changes while it runs, the stamp records the end-of-run disk state rather than the code already loaded and executed by the process.

The stamp also omits the actual experiment input. It records only a direction count and sampling parameters, not the sampled direction identifiers or a digest of their loaded values. The DGL database can change while the repository revision and source hash stay identical, producing a different sample or different boards under the same provenance.

The fallback remains partially open. If `git describe` succeeds but `git status` fails, `_git()` returns `unknown` for status and publication continues because `main()` refuses only text containing `revision           unknown`. The artifact then claims completion without knowing whether untracked files shadowed or altered an imported dependency. When status does succeed, every porcelain entry is labelled `+untracked`, including ordinary tracked modifications, and only the count is preserved. Different dirty contents with the same count remain indistinguishable.

The test does not exercise any of these branches. It calls the live repository and asserts only that the output contains `revision` and an instrument hash, which also passes when the status check failed or when the hash describes files edited after execution.

**Impact:** A canonical `COMPLETE` result can identify code that did not run and omit the data that did. Two materially different experiments can carry the same stamp, while one experiment can be attributed to source edited after its calculations finished. That makes the evidence non-reproducible and can conceal exactly the mid-run changes this provenance mechanism is intended to expose.

**Recommendation:** Capture an immutable `RunIdentity` before measurement begins. Hash the decision-bearing source as loaded at startup, then hash a canonical representation of the complete sampled inputs immediately after `load()` and before calling `groups_in()`. Record the sorted direction IDs as inspectable evidence beside the digest. Require both repository commands to succeed or rely entirely on content hashes; never publish when the untracked-state check is `unknown`. Parse `??` entries separately from tracked changes and include content hashes rather than only counts. Unit-test clean, tracked-dirty, untracked-dirty, status-failure, mid-run file-change, and changed-input cases with injected repository and hashing functions.

### `v13-P2-01` - The constructor accepts strings and mutable lists as `slot_references`

**Locations:** `forge/src/boxscore_package/format.py`, `Package.slot_references`, `Package.__post_init__()`, and `_check_slot_references()`

**Problem:** `_check_slot_references()` was widened to `Sequence[object]` so the element-type guard remains reachable. That correctly handles malformed elements, but it never validates the outer container. At runtime a direct caller can pass a list despite the field contract requiring a tuple. More subtly, a string is itself a `Sequence`: a nine-row package given `slot_references="123456789"` passes the length, per-character grammar, and uniqueness checks.

Accepting a list also defeats the immutability promised by the frozen dataclass. The caller can mutate the list after construction, changing future serialization and any signature payload derived from the same object. `published()` carries the same mutable object forward rather than establishing a tuple value.

**Impact:** The programmatic construction path can hold a runtime shape excluded by its own type and frozen-value contract. Accidental mutation can make a previously signed package serialize differently or make two objects derived from the same package observe different references. A bare string can pass validation while downstream code receives a string where it expects a tuple of references.

**Recommendation:** Make the shared helper accept `object`, first require an allowed non-string container, then validate elements. Prefer canonicalizing an accepted sequence to `tuple` inside `__post_init__()` with `object.__setattr__`, or reject every outer type except `tuple` for a strict constructor contract. Add direct-constructor tests for a bare string and a mutable list, including mutation after construction, and assert the stored field is always a tuple.

### `v13-P2-02` - The private pending-file repair is marked closed without a regression test

**Locations:** `discovery/footnote-groups/measure.py`, final publication block in `main()`; `forge/tests/test_group_metrics.py`, artifact tests; `docs/reviews/todo.md`, v12-P2-03 closure

**Problem:** The implementation now creates a pending name with PID and random nonce, which removes the fixed-name collision. No test invokes or extracts that publication behavior, asserts two runs receive distinct pending paths, verifies replacement, or proves cleanup on failure. The test module stops at provenance and report rendering.

The backlog's project-wide closure rule requires both the fix and a test that fails without it, yet v12-P2-03 is recorded as closed. Reverting the pending path to `results.txt.pending` would leave the current suite unchanged.

**Impact:** A concurrency defect already recreated once in this instrument has no automated guard against returning. The review ledger overstates closure under its own definition, and future cleanup of the inline publication block can silently restore shared staging.

**Recommendation:** Extract publication into a function that accepts the destination, text, PID, and nonce source. Assert two invocations targeting the same destination create different pending paths, each uses same-directory atomic replacement, and temporary files are removed after write or replace failures. Include a deliberate fixed-name implementation in the test reasoning and ensure the new assertion would fail against it.

## Security review

No new OWASP-class issue was identified. The mutable constructor input is an internal programmatic boundary, and package signatures still detect a payload changed after signing when verification occurs. The Git subprocess uses a fixed argument vector without a shell. Because there is no security finding, attack scenario, exploitation method, business impact, and security remediation fields are not applicable.

## Perspective coverage

| Perspective | Result |
|---|---|
| Python principal engineer | Found an outer-container validation and immutability gap in `Package` |
| QA and reliability | Found non-snapshot provenance and a closure recorded without a regression test |
| Frontend engineer | No changed frontend surface and no new finding |
| Security / OWASP | No new externally exploitable trust-boundary issue |
| Backend architect | The package boundary accepts runtime shapes outside its contract; private result staging is untested |
| Baseball / boxscore domain | Slot-reference grammar remains correct; the defect is container shape rather than baseball meaning |
| Kakuro / logic-puzzle design | The corrected blockage predicate and denominators remain coherent; input identity is not preserved |
| UX / graphic design | No player-facing change and no new visual finding |

## Further improvements

1. Increment the result schema whenever a previously publishable artifact changes its accounting or provenance contract, even if no canonical result is believed to have survived.
2. Replace manual `sys.argv` indexing with `argparse` and validate the output parent before beginning the expensive database run.
3. Extract result publication and run identity from `main()` so both can be tested without loading DGL or executing the full experiment.

## Residual risk

This was a static review. No database-backed measurement, package-signing scenario, concurrent publication, Git-state branch, or test suite was executed. Numerical results, sampled inputs, runtime provenance, and full-suite compatibility remain unverified by design.
