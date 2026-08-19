# Code Review v09

**Review date:** 2026-08-19  
**Review mode:** static re-review of the current tree after the v08 repairs and the first v09 pass  
**Scope:** all project Markdown was considered first; changed source, tests, experiments, prototypes, and generated reference artifacts were then reviewed. `_not_in_use` was excluded.  
**Validation:** no tests, commands that exercise application behavior, or source modifications were performed.  
**Deduplication:** items already pending or open in `docs/reviews/todo.md` are intentionally not repeated.

## Findings

### v09-P1-01 - An untrusted signing key can replace the production inventory

**Severity:** P1  
**Personas:** Security / OWASP, Backend Architect, QA / Reliability, Python Principal, UX  
**Evidence:** `forge/scripts/write_reference_puzzles.py:48`, `forge/scripts/write_reference_puzzles.py:289`, `forge/scripts/write_reference_puzzles.py:311`, `forge/scripts/write_reference_puzzles.py:318`, `forge/scripts/write_reference_puzzles.py:347`, `forge/scripts/write_reference_puzzles.py:394`, `serve/data/signing-public-key.hex:1`

The writer correctly makes `--ephemeral` mutually exclusive with `BOXSCORE_SIGNING_KEY`, but both modes still publish through the same global `OUT` and the same `_publish()` path. The production-key path also validates packages with `key.public_key()`, which is derived from the private key supplied to that same run; it never compares that public key with the public key pinned by `serve`. Consequently, successful self-verification proves only that the batch is internally consistent, not that the deployed reader will trust it.

The operator output makes the boundary less reliable. After accurately saying that `serve` will refuse an ephemeral batch, lines 318-320 also print that the batch is in fixtures mode and was signed with a key living in the repository. That statement is false for the freshly generated ephemeral key and can cause an operator to misclassify the resulting artifacts.

**Attack scenario:** a contributor, compromised CI worker, or other process that can run the writer and modify the workspace but does not possess the production private key invokes the documented `--ephemeral` mode. The process generates its own key and then atomically replaces `serve/data/puzzles/manifest.json` with a manifest signed by that key.

**Exploitation:** no signing-key theft or cryptographic forgery is required. The attacker only needs permission to execute the writer against its default output, or to cause the resulting data directory to enter a deployment. The same failure can happen accidentally when `BOXSCORE_SIGNING_KEY` contains a valid Ed25519 private key that does not correspond to `serve/data/signing-public-key.hex`.

**Business impact:** `serve` rejects the new manifest or its packages, so the active puzzle inventory becomes unavailable even though the publisher reported a successful, certified commit. The prior generation may still exist on disk, but the live manifest no longer points to it. This can produce a complete puzzle outage and a confusing recovery path during release.

**Recommended fix:**

- Make ephemeral output structurally separate from production output. Require an explicit non-production `--out`, or default ephemeral runs to a temporary directory that `_publish()` cannot resolve to `serve/data/puzzles`.
- Before creating or deleting anything under the production output, derive the supplied key's public bytes and compare them with the pinned value in `serve/data/signing-public-key.hex`. Abort on any mismatch.
- Pass the output/trust target into `_publish()` instead of relying on mutable module-global `OUT`; this makes the trust-domain decision explicit at the call boundary.
- Remove the stale fixtures-mode messages and print exactly one trust-domain status.
- Replace the source-text assertions in `test_reference_batch.py` with behavioral tests proving that an ephemeral run cannot modify production output, a mismatched configured key is rejected before staging, and the matching production pair can publish.

**Reasoning:** refusing an untrusted batch at read time preserves integrity but not availability. The safest publication design prevents an untrusted writer mode from changing the trusted namespace at all, and verifies key pairing before the first filesystem mutation rather than after artifacts have been built.

### v09-P2-01 - The default package constructor can still emit schema 2 documents its reader rejects

**Severity:** P2  
**Personas:** Python Principal, Backend Architect, QA / Reliability, Frontend  
**Evidence:** `docs/package-format-v2.md:17`, `forge/src/boxscore_package/format.py:353`, `forge/src/boxscore_package/format.py:364`, `forge/src/boxscore_package/format.py:367`, `forge/src/boxscore_package/format.py:376`, `forge/src/boxscore_package/format.py:415`, `forge/src/boxscore_package/format.py:476`, `forge/tests/verify/test_schema_document.py:47`

`Package.__post_init__()` now rejects an explicitly declared schema 2 package with no `slot_references`, but it returns immediately when `schema is None`. That is the normal construction path. `written_as` then defaults the object to schema 2, while `as_json()` omits `slot_references` when they are absent. `Package.from_json()` correctly refuses that serialized document because schema 2 requires one reference per batting row.

The constructor also checks only the reference count. Programmatic packages with duplicate references or values that do not match `^[1-9][a-z]?$` serialize successfully and are rejected only when read back. The boundary validator already contains the complete rules, but construction and parsing apply different subsets.

**Impact:** a future inventory producer can call the supported `Package` and `write()` APIs, produce a file labelled schema 2, and hand `serve` an artifact the shared reader refuses. The current reference writer's explicit read-back catches this before its manifest commit, but that caller-specific safety does not make the package API safe for the batch generator or other producers.

**Recommended fix:**

- Since schema 1 is no longer writable or readable, require `slot_references` unconditionally for every `Package` instance that can be serialized.
- Put syntax, cardinality, and uniqueness validation in one helper used by both `__post_init__()` and `from_json()`.
- Remove or privatize the public `schema` override if every constructible package is schema 2.
- Add direct constructor-to-JSON-to-parser tests for absent, duplicate, malformed, and valid references. The current schema fixture always supplies valid references, so it cannot fire on the default-path defect.

**Reasoning:** the invariant is not merely that parsed input is valid. The shared package type must be unable to create output outside the language its own parser accepts; otherwise every producer has to rediscover the round-trip guard independently.

### v09-P2-02 - The footnote-group experiment cannot observe the dependency it reports

**Severity:** P2  
**Personas:** Kakuro / Logic Puzzles, Baseball / Box Scores, QA / Reliability, UX  
**Evidence:** `discovery/footnote-groups/measure.py:61`, `discovery/footnote-groups/measure.py:64`, `discovery/footnote-groups/measure.py:74`, `discovery/footnote-groups/measure.py:75`, `discovery/footnote-groups/measure.py:77`, `discovery/footnote-groups/measure.py:83`, `discovery/footnote-groups/measure.py:120`, `discovery/footnote-groups/measure.py:132`

`groups_in()` starts from `cell_values(direction)`, removes only the selected group's footnote cells, and leaves every other board cell given. Therefore every deduction the solver can make belongs to `hidden`; there cannot be a later non-hidden deduction whose `depends_on` intersects the group. `had_to_resolve` is structurally false for every sample, regardless of whether a realistic erased board would stall until that attribution was resolved.

The field named `unique` also combines two separate questions. It is true only when the restricted human solver completes and reproduces the hidden values. A false result can mean that several assignments exist, or that one assignment exists but the implemented propagation/bounding techniques did not derive it. The report labels the resulting share as "uniquely solvable," so ambiguity and underivability are indistinguishable.

`discovery/footnote-groups/results.txt` is still empty, so this instrument has not yet produced a recorded product decision. Fixing it before the run preserves that clean boundary.

**Impact:** the run can falsely report that an attribution never blocks the rest of a puzzle and can undercount uniquely solvable groups. Those numbers decide whether erased footnotes need a generator constraint and how the UI must draw an unknown carrier; a false result can either admit frustrating boards or force unnecessary visual complexity and pool loss.

**Recommended fix:**

- Measure mathematical uniqueness independently with the verifier's solution enumerator at `limit=2`; report zero, one, and multiple completions separately.
- Measure human derivability with the restricted solver as a second axis rather than naming it uniqueness.
- For `had_to_resolve`, start from actual representative erased puzzles, additionally hide the target group, and compare the downstream trace or completion with and without those assignments.
- Add a synthetic case where a non-footnote cell explicitly depends on a hidden footnote and assert that the metric becomes true, plus a unique-but-not-derived case if one can be constructed.

**Reasoning:** local assignment ambiguity and whether the rest of a puzzle waits on that assignment are different experiments. One requires counting completions; the other requires other unknown cells to exist. The current complete-board setup can answer neither question as labelled.

## Persona coverage

| Persona | Result |
|---|---|
| Python Principal | v09-P1-01 covers the global output/trust coupling; v09-P2-01 covers the constructible-but-unreadable package state. |
| QA / Reliability | All three findings include a missing behavioral or falsification case. No tests were run. |
| Frontend | v09-P2-01 can deny the client the slot references required to resolve footnotes. The active static prototypes produced no separate finding. |
| Security / OWASP | v09-P1-01 is the release-integrity and availability finding. |
| Backend Architect | v09-P1-01 covers the missing binding between publisher identity and trust anchor; v09-P2-01 covers the asymmetric writer/reader contract. |
| Baseball / box scores | v09-P2-02 covers the unresolved attribution experiment. The global baseball identity fix produced no additional finding. |
| Kakuro / logic puzzles | v09-P2-02 separates solution cardinality, human derivability, and downstream dependency. |
| UX / graphic design | The contradictory trust-mode console copy is in v09-P1-01, and v09-P2-02 protects the decision that will define the erased-attribution drawing. No active visual prototype produced a separate finding. |

## Improvements confirmed in this delta

- The reference writer now signs the manifest and includes tamper tests for both the generation and puzzle list.
- `--ephemeral` no longer silently uses a configured production key.
- The solver checks the global identity when validating givens and the completed deduction state.
- The package reader now explicitly limits readable input to schema 2.

## Review boundary and residual risk

The sole open item in `docs/reviews/todo.md`, v05-P1-02, was excluded rather than renumbered. Historical documentation drift already attached to closed v08 findings was not counted as a separate issue; v09-P2-01 is included because the repaired constructor still has an executable path that emits an unreadable current-schema document.

This was a static review. Runtime behavior, concurrency, deployment integration, signature verification against the checked-in public key, generated PDFs, and the complete test suite remain unverified in this review.
