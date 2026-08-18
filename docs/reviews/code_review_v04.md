# Code Review v04

**Date:** 2026-08-18  
**Method:** Static review only. No tests, generators, database queries, or validation commands were run.  
**Scope:** Active project code and project-owned Markdown under `forge/`, `serve/`, `discovery/`, and `docs/`. `_not_in_use` was excluded. Existing open or pending backlog items were not reopened.

## Executive summary

The current code is materially stronger than v03: package parsing rejects ambiguous JSON types, publication evidence is bound to the package identity, the global identity now has an explicit two-phase path, and the RBI/HR instrument contains useful assertions against a false null result.

Six new findings remain. The two P1 findings are both in the generation-manifest contract and should be resolved before a frontend depends on it. The four P2 findings affect provenance stability, the validity of difficulty conclusions, before/after experiments, and solver telemetry. `serve/` contains generated puzzle data but no active frontend implementation, so there was no DOM, accessibility, responsive-layout, or client-state code to review.

| Priority | Count | Meaning in this review |
|---|---:|---|
| P1 | 2 | Must be fixed before `serve` consumes the publication contract |
| P2 | 4 | Can produce unstable batches, invalid research conclusions, or contradictory telemetry |

## Findings

### v04-P1-01: Committing a manifest immediately destroys the snapshot that existing readers may still be following

**Perspectives:** Backend Architect, QA/Reliability, Frontend Developer  
**Locations:** `forge/scripts/write_reference_puzzles.py:248`, `forge/tests/test_reference_batch.py:107`, `forge/tests/test_reference_batch.py:119`, `docs/package-format-v1.md:114`

`_publish()` correctly stages a complete immutable generation and atomically replaces `manifest.json`, but it then immediately deletes every other generation directory. Atomic replacement protects the manifest file from being torn; it does not make the reader's manifest fetch and subsequent puzzle fetch one transaction.

A valid sequence is:

1. A reader or CDN obtains manifest generation `A`.
2. The publisher commits generation `B`.
3. The publisher deletes directory `A`.
4. The reader follows its valid manifest and receives `404` for an `A` puzzle.

The current test encodes the unsafe behavior by asserting that the previous directory is gone as soon as `_publish()` returns. Cached manifests make the window much longer than the local filesystem operation. The same cleanup also removes other processes' staging directories, while the fixed `.manifest.pending` filename gives concurrent publishers another collision point. There is no lock that makes the implicit single-writer assumption true.

**Impact:** A normal release can interrupt active or cached clients, violate the whole-generation promise, and make concurrent publication fail nondeterministically. This directly weakens the planned offline-first user experience.

**Recommended fix:** Serialize publication with a lock, use a publisher-specific pending filename, and remove garbage collection from the commit path. Retain old immutable generations for a grace period longer than the maximum manifest cache lifetime, or retain a fixed number and collect them in a separate job. Add a test where a reader captures manifest `A`, publication commits `B`, and the reader can still fetch all of `A`; also add a two-publisher test.

### v04-P1-02: Signed puzzle files sit behind an unsigned, replayable manifest

**Perspectives:** Security Engineer, Backend Architect, Frontend Developer  
**Locations:** `forge/scripts/write_reference_puzzles.py:235`, `docs/package-format-v1.md:114`

The package signature authenticates an individual puzzle payload, but the manifest decides which generation and puzzle IDs constitute the release. That decision is not authenticated. The content-derived generation name detects neither a changed puzzle list nor a replayed pointer unless a reader independently reconstructs and validates the entire generation, and the contract does not require that.

**Attack scenario:** An attacker can modify or poison `manifest.json` in a CDN, static bucket, deployment step, or cache while being unable to forge a valid puzzle package.

**Exploitation method:** The attacker omits selected IDs, reorders the calendar, points at another retained generation, or points at a nonexistent generation. Every package the client does receive can still pass its own signature check, so package verification does not detect manipulation of the release inventory.

**Business impact:** Players can receive repeated or stale puzzles, a partial calendar, or a complete outage. Editorial ordering and no-repetition guarantees can be changed without breaking any package signature. This would make the security indicator say that the content is authentic while the release itself is not.

**Recommended fix:** Define a canonical signed manifest envelope covering `schema`, the full generation digest, the ordered puzzle IDs, and a monotonic release sequence or equivalent anti-rollback value. Verify it before following any generation path. When the already-planned public-key signing migration lands, sign manifests with that same release key and verify with the public key in the client; do not introduce a second shared secret into `serve`. Specify client behavior for an invalid, expired, or older manifest.

### v04-P2-01: Publication provenance is selected by two unrelated, nondeterministic `TOP 1` queries

**Perspectives:** Backend Architect, QA/Reliability, Baseball Data Expert  
**Locations:** `discovery/difficulty-metrics/measure.py:324`, `discovery/difficulty-metrics/measure.py:329`, `discovery/difficulty-metrics/measure.py:355`

Candidate eligibility requires an actual provenance row that is both non-deduced and in the accepted source list. The evidence projected for certification does not select that row. `source_type` and `is_deduced` are fetched by two independent `SELECT TOP 1` subqueries with no acceptance predicate and no `ORDER BY`.

If a game has multiple provenance rows, SQL Server may return a rejected source, a deduced row, or values from two different rows even though the accepted row used by `EXISTS` is present. The publication gate can then reject a valid candidate nondeterministically, shorten a batch, or record an evidence tuple that does not correspond to any provenance record.

**Recommended fix:** Select one deterministic accepted, non-deduced provenance row once with `CROSS APPLY` or a joined ranked CTE, and project both evidence fields from that same row. If the schema intends exactly one provenance row per game, enforce that invariant instead. Add a fixture with multiple provenance rows, including one rejected and one accepted source.

### v04-P2-02: The ceiling pack reports a theoretical ceiling from one greedy path over 48 sampled directions

**Perspectives:** Kakuro/Logic Puzzle Expert, QA/Reliability, UX/Graphic Design  
**Locations:** `discovery/hand-solve/build_ceiling_pack.py:1`, `discovery/hand-solve/build_ceiling_pack.py:49`, `discovery/hand-solve/build_ceiling_pack.py:74`

The artifact calls its result “the hardest this board family can be made, in theory” and “the top.” The implementation uses one seed, one default ordering, four sampled directions per decade, and one nested greedy erasure trajectory per direction. `ceiling_of()` keeps the highest stall count encountered on that path, but it never explores the many alternative erasure sets produced by different orders or restarts.

Because stall count depends on which cells are absent and is not a proven monotonic function of blank count, `19` is only the largest value observed on 48 particular paths. It is not a per-board maximum, a sample-wide upper bound, or a theoretical family ceiling. Hand-solvers may therefore be anchored against an understated and incorrectly characterized upper endpoint.

**Recommended fix:** Rename the output and prose to “highest observed one-path stall count” immediately. For a stronger estimate, run multiple independent seeds and orderings per direction, keep per-board maxima, report the convergence curve and distribution, and state the sample size beside every maximum. Reserve “ceiling” for a proven bound or an explicitly qualified estimated ceiling.

### v04-P2-03: The before/after comparator can declare a null result after silently changing the cohort

**Perspectives:** QA/Reliability, Python Principal Developer, Kakuro/Logic Puzzle Expert  
**Location:** `discovery/global-identity-phase/compare.py:116`

`compare()` converts each JSON file to a dictionary keyed by `(game_id, seed)`, which silently collapses duplicate keys. It then requires only that the two files share at least one key and performs every comparison on their intersection. Rows present on only one side are printed but do not make the experiment fail.

That behavior conflicts with the script's stated requirement of the same boards and seeds. A database change, query drift, partial run, or solver failure can remove exactly the boards affected by a code change; the comparator can then report a clean null over the survivors. The instrument intended to prevent a false null therefore still has a path to one.

**Recommended fix:** Reject duplicate keys while loading and require exact key-set equality by default. If partial comparison is useful diagnostically, put it behind an explicit `--allow-partial` option and label its output as non-experimental. Persist and compare the sampling parameters or a cohort hash alongside the rows.

### v04-P2-04: One `Solution` can report that the global family was used while counting it zero times

**Perspectives:** Python Principal Developer, QA/Reliability, Kakuro/Logic Puzzle Expert  
**Locations:** `forge/src/boxscore_forge/solver.py:165`, `forge/src/boxscore_forge/solver.py:189`, `forge/tests/test_solver.py:518`

`families_used` now correctly includes `GLOBAL_IDENTITY` when a bounding deduction has `needed_global_identity=True`. `family_counts` still counts only `from_identity`; bounding deductions intentionally have `from_identity=None`. The same immutable result can therefore say the global family was required while returning a global count of zero.

There is no production consumer of `family_counts` yet, which limits current impact, but the API is precisely the kind of telemetry a future difficulty or character classifier will consume. Two plausible consumers can reach opposite conclusions from the same solve.

**Recommended fix:** Decide and encode one contract. If `family_counts` means all family participation, count a global-assisted bounding deduction. If it means only direct propagation deductions, rename it to `direct_family_deduction_counts` and document why it intentionally differs from `families_used`. Extend the existing synthetic `needed_global_identity` test to assert the chosen relationship between both properties.

## Perspective coverage

| Review perspective | Result |
|---|---|
| Python Principal Developer | Comparator key handling and contradictory solver telemetry are covered by v04-P2-03 and v04-P2-04. |
| QA/Reliability Engineer | Publication races, provenance nondeterminism, cohort drift, and measurement overclaim are covered. |
| Frontend Developer | No active UI source exists to review; the manifest lifetime and trust contract are the current client blockers. |
| Security Engineer | Manifest integrity, replay, and release-selection tampering are covered by v04-P1-02 with an attack path and remediation. |
| Backend Architect | The publication transaction and provenance selection are covered by v04-P1-01, v04-P1-02, and v04-P2-01. |
| Baseball/Boxscore Expert | Accepted-source provenance must correspond to one real source record; the RBI/HR experiment otherwise models the baseball identities carefully. |
| Kakuro/Logic Puzzle Expert | The claimed ceiling and family telemetry are covered by v04-P2-02 through v04-P2-04. |
| UX/Graphic Design | No UI is present. The RBI/HR width calculation is useful evidence that a seventh interactive column does not fit the stated 375 px/44 px touch-target budget without a layout redesign. |

## Improvements worth preserving

- Package deserialization now rejects booleans where JSON integers are required and guards the envelope at `Package.from_json()` itself.
- The global identity's phase boundary is represented explicitly, and global-assisted bounding is no longer invisible in `families_used`.
- The batch writer stages a complete generation before moving the manifest; retaining generations safely will complete rather than replace that design.
- The RBI/HR instrument asserts that each variant really changed the production constraint system before interpreting a null result.
- Publication evidence now includes an independent game-log comparison for at-bats and left on base; v04-P2-01 is about selecting its provenance row deterministically, not reversing that improvement.

## Review boundary and residual risk

No source code was changed. No tests were executed. Generated PDFs and HTML were treated as outputs of the reviewed producers, not visually revalidated. Existing backlog items, including work already marked open, pending, blocked, or explicitly owed, were intentionally omitted rather than assigned new v04 IDs.
