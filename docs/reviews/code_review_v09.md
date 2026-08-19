# Code Review v09

**Review mode:** incremental static review after `code_review_v08.md`  
**Scope:** all project Markdown was considered first; source review was then limited to files changed after the v08 cutoff. `_not_in_use` was excluded.  
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

## Persona coverage

| Persona | Result |
|---|---|
| Python Principal | The implicit global output/trust coupling is covered by v09-P1-01; no additional unique Python finding was found in the changed files. |
| QA / Reliability | The behavioral gap around key modes is covered by v09-P1-01. No tests were run. |
| Frontend | No changed frontend runtime file was in the v09 delta; no new unique finding. |
| Security / OWASP | v09-P1-01 is the release-integrity and availability finding. |
| Backend Architect | v09-P1-01 covers the missing binding between publisher identity and the reader's trust anchor. |
| Baseball / box scores | The global baseball identity is now included in contradiction validation; no new unique baseball finding. |
| Kakuro / logic puzzles | The solver's initial and final global contradiction checks close the reviewed failure path without introducing a new static finding. |
| UX / graphic design | The contradictory trust-mode console copy is included in v09-P1-01. No changed visual artifact produced a separate finding. |

## Improvements confirmed in this delta

- The reference writer now signs the manifest and includes tamper tests for both the generation and puzzle list.
- `--ephemeral` no longer silently uses a configured production key.
- The solver checks the global identity when validating givens and the completed deduction state.
- The package reader now explicitly limits readable input to schema 2.

## Review boundary and residual risk

Open and pending items already recorded in `docs/reviews/todo.md`, including the remaining v1 migration and the open v08 P2 items, were excluded rather than renumbered. Existing documentation drift attached to those findings was also not counted again.

This was a static review. Runtime behavior, concurrency, deployment integration, signature verification against the checked-in public key, and the complete test suite remain unverified in this review.
