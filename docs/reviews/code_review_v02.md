# Code Review v02

**Date:** 2026-08-18  
**Review type:** Static, repository-wide review  
**Release recommendation:** **No-go for publication or difficulty labeling until the P1 findings are resolved and the affected artifacts are regenerated.**

## Scope and method

This review covered the active project under the following perspectives:

1. Python Principal Developer
2. QA and Reliability Engineer
3. Frontend Engineer
4. Security Engineer
5. Backend Architect
6. Baseball and box-score domain specialist
7. Kakuro and logic-puzzle specialist
8. UX and graphic-design specialist

Every Markdown document in the repository and its subdirectories was read before the code review. The `_not_in_use` tree was excluded as requested. The active code and generated/reference artifacts under `forge`, `discovery`, and `serve` were then inspected, with emphasis on the complete path from historical data loading through erasure, solving, package conversion, verification, and publication.

This was a static review. Tests and discovery programs were not executed.

## Backlog handling

`docs/reviews/todo.md`, `docs/reviews/code_review_v01.md`, and `docs/reviews/non-issue.md` were cross-checked before recording findings. No v01 item is currently marked pending, so no finding was suppressed on that basis. Findings below do not restate completed v01 work. `v02-P1-03` is explicitly identified as a regression of the previously accepted hand-solve quota fix.

## Severity model

- **P1:** Publication blocker, invalid difficulty evidence, or historical-data integrity failure.
- **P2:** Material correctness, reliability, or maintainability problem that should be fixed before production work builds on it.
- **P3:** Lower-risk improvement. No P3-only findings were necessary in this review.

## Findings summary

| ID | Priority | Primary persona | Finding |
|---|---|---|---|
| v02-P1-01 | P1 | Backend Architect | Footnote erasures disappear at the generator-to-package boundary |
| v02-P1-02 | P1 | Kakuro / Logic Puzzles | Active artifacts still use chain length after stalls became the difficulty model |
| v02-P1-03 | P1 | QA / Reliability | A duplicate `audit()` definition disables the strict hand-solve quota |
| v02-P1-04 | P1 | Baseball / Box Scores | The provenance gate fails open when a game has no provenance row |
| v02-P1-05 | P1 | Baseball / Box Scores | Offensive hits are checked against a total derived from the same batting rows |
| v02-P1-06 | P1 | QA / Reliability | The publication path does not enforce the implemented plausibility checks |
| v02-P2-01 | P2 | Python Principal Developer | The solver uses the global identity before non-global deductions are exhausted |
| v02-P2-02 | P2 | Kakuro / Logic Puzzles | The stall-family report cannot identify the family that restarts solving |
| v02-P2-03 | P2 | Backend Architect | Current source-of-truth documents disagree with executable rules |
| v02-P2-04 | P2 | QA / Reliability | Reference-package regeneration deletes the prior set before a replacement is valid |

---

## Persona 1: Python Principal Developer

### v02-P2-01 - The solver uses the global identity before non-global deductions are exhausted

**Evidence**

- `forge/src/boxscore_forge/constraints.py:37` documents that the global identity must be held back until simpler families are exhausted.
- `forge/src/boxscore_forge/solver.py:298` separates `system` from `global_equations`.
- `forge/src/boxscore_forge/solver.py:336` immediately recombines both into `whole_system` and passes that combined set into propagation.
- `forge/src/boxscore_forge/solver.py:401` passes the full shape into `narrow()`, whose equation set also includes the global identity.

**Why this matters**

The solver may still reach the correct numeric solution, but it is not following the intended deduction policy. A global deduction can be selected while a local or cross-team route should still have priority. That changes the recorded solution path, family usage, chain length, and potentially stall placement. Those outputs are inputs to the project's difficulty research, so this is a measurement-correctness defect rather than merely an implementation-detail disagreement.

**Recommendation**

Implement an explicit two-phase fixed-point loop. Propagate and bound with non-global equations until no progress remains, then admit the global identity. Add a focused test in which a global and a non-global move are simultaneously available and assert that the non-global move is recorded first. Keep global equations out of the bounding equation set until the same admission point.

**Also affects:** Personas 2, 5, and 7.

---

## Persona 2: QA and Reliability Engineer

### v02-P1-03 - A duplicate `audit()` definition disables the strict hand-solve quota

**Evidence**

- `discovery/hand-solve/build_pack.py:293` defines an audit that requires the uncertified share to remain within two boards of the intended one-third allocation.
- `discovery/hand-solve/build_pack.py:325` defines `audit()` again. Python replaces the first function with this second definition.
- The active definition accepts between 5 and 25 uncertified boards in a 50-board pack, rather than the intended approximately 15 to 19.

**Why this matters**

The hand-solve pack is the project's human difficulty gate. A pack can now pass while containing only 10% uncertified boards or as many as 50%. Results from such a pack cannot support conclusions about the intended certified/uncertified mix. This is a regression of the v01 hand-solve quota correction, not a duplicate report of the old issue.

**Recommendation**

Remove the shadowing definition and keep one audit policy with named constants for pack size, target share, and tolerance. Add boundary tests for the minimum accepted count, maximum accepted count, and the two immediately rejected counts. Regenerate `boards.pdf`, `solutions.pdf`, and `recording-sheet.csv` after this and `v02-P1-02` are fixed.

**Also affects:** Personas 7 and 8.

### v02-P1-06 - The publication path does not enforce the implemented plausibility checks

**Evidence**

- `forge/src/boxscore_verify/verify.py:98` performs package, structure, arithmetic, solution, and signature checks, but does not call `boxscore_verify.plausibility.faults()`.
- `forge/tests/verify/test_plausibility.py:57` explicitly demonstrates that a mathematically valid but implausible board can be accepted by `verify()`.
- `forge/scripts/write_reference_puzzles.py:94` uses `verify()` as its acceptance gate.
- The same writer calls `reveal_faults()` after writing, but it does not call the board-level `faults()` function.
- `discovery/loader-invariants/sweep.py:119` runs plausibility as a separate research sweep, not as an enforced publication step.

**Why this matters**

The repository has checks for phantom rows, roster shape, impossible volume, and related baseball plausibility defects, but the publication path can bypass them. A source or adapter regression can therefore produce a package that is signed and mathematically self-consistent while still representing an impossible box score.

**Recommendation**

Create one fail-closed `certify_for_publication()` boundary that composes package verification, board plausibility, reveal plausibility, provenance completeness, and independent source correspondence. All writers should call that boundary rather than assembling subsets of checks. Preserve the lower-level `verify()` function if its narrower mathematical contract is useful, but do not present it as sufficient for publication.

**Also affects:** Personas 5 and 6.

### v02-P2-04 - Reference-package regeneration deletes the prior set before a replacement is valid

**Evidence**

- `forge/scripts/write_reference_puzzles.py:123` deletes every existing JSON output before all replacement packages have been generated and certified.
- `forge/src/boxscore_package/format.py:381` writes package JSON directly to the destination rather than through an atomic temporary-file replacement.

**Why this matters**

A loader error, exhausted candidate pool, interrupted process, or disk failure can leave `serve/data/puzzles` empty, partial, or containing a truncated file. Although this is currently reference data, the pattern is unsafe to reuse for a production inventory pipeline and makes fixture regeneration unnecessarily fragile.

**Recommendation**

Generate the complete set in a temporary sibling directory, validate every package there, and replace the published set only after the batch succeeds. Write each JSON file with a temporary file plus atomic rename. Do not delete the last known-good set at the start of the job.

**Also affects:** Personas 1 and 5.

---

## Persona 3: Frontend Engineer

There is no production frontend implementation to review under `serve`; it currently contains six JSON reference packages only. The HTML files under `discovery` are research instruments and explicitly declare that they are not the product.

No standalone frontend finding is recorded. Before frontend implementation begins, its package consumer should be blocked on `v02-P1-01`, `v02-P1-02`, and `v02-P1-06`, because otherwise the UI would faithfully display incorrectly graded or insufficiently certified inputs.

---

## Persona 4: Security Engineer

No exploitable production security finding was established in the current repository. There is no HTTP application, authentication system, session handling, database write API, or production browser client under `serve` to assess. The package signer uses keyed HMAC verification and the verifier rejects a missing secret unless the explicit test-only `UNSIGNED` capability is supplied.

The known fallback signing key in `forge/scripts/write_reference_puzzles.py` is clearly scoped to reference fixtures. It would become a security finding if these signatures were ever treated as production authenticity. At that point, the required report would include an attack scenario, exploitation method, business impact, and remediation; reporting that as a current vulnerability would overstate the present attack surface.

Security review must be repeated when a production publisher, API, or frontend exists. In particular, production code must never import the reference fallback key or expose the unsigned verification capability through user-controlled configuration.

---

## Persona 5: Backend Architect

### v02-P1-01 - Footnote erasures disappear at the generator-to-package boundary

**Evidence**

- `forge/src/boxscore_forge/erasure.py:53` defines the current erasable cell set.
- `forge/src/boxscore_forge/erasure.py:73` includes per-batter footnote cells in that set.
- `discovery/verifier/rejection_rates.py:59` is the shared `Direction`-to-`Board` adapter used by the discovery and reference-package flows.
- `discovery/verifier/rejection_rates.py:87` always copies every per-batter footnote value and never checks whether its cell path is in the erased set.
- Batting and pitching cells in the same adapter do consult the erased set, making the omission specific and silent.
- `discovery/difficulty-metrics/measure.py:373` still describes the old grid-only erasable set, while `discovery/stall-targeted/measure.py:90` adds footnote cells to a list that already receives them from the core engine.

**Why this matters**

The generator can erase a footnote and use that unknown while measuring the solution path. Conversion to a package then restores the value. The verifier validates the easier, restored board rather than the board the generator graded. Published/reference metadata can therefore claim a difficulty, chain length, stall count, and blank count that do not describe the artifact delivered to the player.

The stale research helpers compound the problem: some experiments omit the new cells, while another can include them twice. Results are no longer directly comparable even though they use the same terminology.

**Recommendation**

Move `Direction`-to-`Board` conversion into one canonical production module rather than importing it from a discovery experiment. Apply the erased-cell set to batting rows, totals, pitching rows, totals, and per-batter footnotes uniformly. Add a contract test that forces a footnote erasure, serializes the package, asserts that the published value is `null`, reparses it, and verifies that the solution statistics still match the generated puzzle. Remove local erasable-cell reimplementations and regenerate all affected JSON, PDF, HTML, and text results.

**Also affects:** Personas 1, 2, 3, 7, and 8.

### v02-P2-03 - Current source-of-truth documents disagree with executable rules

**Evidence**

- `CLAUDE.md:255` and `CLAUDE.md:317` still describe a two-pitcher cap, while the active loader and newest design decision use up to four pitchers.
- `CLAUDE.md` and `docs/package-format-v1.md` state that the per-batter footnote line is given rather than erased, while `forge/src/boxscore_forge/erasure.py:73` makes those cells erasable.
- The design record contains both a current 5-to-11 chain range and stale 5-to-13 references, while the engine now states that stalls, not chain length, grade difficulty.

**Why this matters**

These are not harmless historical notes because `CLAUDE.md` and the package-format document are presented as current implementation contracts. A contributor following them can reintroduce a two-pitcher cap, restore footnotes, or continue publishing chain-based grades. The current code already shows each form of drift.

**Recommendation**

Create one concise current-contract document containing the active roster caps, erasable cell classes, difficulty metric and bands, and publication gates. Make `CLAUDE.md` and package documentation point to it. Keep historical decisions in the design record, but label every superseded section and remove stale values from current checklists and open items.

**Also affects:** All personas.

---

## Persona 6: Baseball and Box-Score Domain Specialist

### v02-P1-04 - The provenance gate fails open when a game has no provenance row

**Evidence**

- `discovery/difficulty-metrics/measure.py:243` filters with `NOT EXISTS` only for provenance rows marked `is_deduced = 1` or `source_type = 'EVR'`.
- A game with no row in `retroGameProvenance` satisfies that predicate and enters the eligible pool.
- The research documentation says the source gate is intended to fail closed because deduced/NGL records can be internally balanced while not corresponding to an acceptable external source.

**Why this matters**

Completeness of the provenance import becomes an unstated precondition. A partial refresh, new season, failed import, or identifier mismatch silently converts “unknown source” into “approved source.” Those games can pass every arithmetic identity and still violate the project's historical-source policy.

**Recommendation**

Require an explicit acceptable provenance row with an inner join or positive `EXISTS` predicate. Separately assert that every candidate game has exactly one recognized provenance classification. Fail the load or publication job when coverage is incomplete, and report counts for missing, deduced, excluded-source, and accepted rows.

**Also affects:** Personas 2, 4, and 5. This is a data-integrity control; no external attack path is currently exposed.

### v02-P1-05 - Offensive hits are checked against a total derived from the same batting rows

**Evidence**

- `discovery/difficulty-metrics/measure.py:225` loads an official defensive hit total but does not load the corresponding official offensive hit total.
- `discovery/difficulty-metrics/measure.py:345` sets `line_score.offense_hits` to `sum(line.hits for line in batting)`.
- The solver then checks that batting hits equal line-score offensive hits, but both values came from the same batting rows.
- `discovery/loader-invariants/sweep.py:84` independently compares several totals to game-log data, but does not perform the equivalent offensive-hit comparison.

**Why this matters**

An omitted batter, duplicate batter, join fan-out, or incorrect hit value can still satisfy every internal hit identity because the supposed anchor was manufactured from the rows being checked. The package can be mathematically consistent yet fail to correspond to the historical box score. This is precisely the class of error the independent-source layer is meant to prevent.

**Recommendation**

Load the official offensive team hit total independently from the game or game-log source and preserve it as the line-score anchor. Reject a direction whenever the summed batting hits differ from that source value. Add the same comparison to the invariant sweep and to the fail-closed publication certification recommended in `v02-P1-06`.

**Also affects:** Personas 2 and 5.

---

## Persona 7: Kakuro and Logic-Puzzle Specialist

### v02-P1-02 - Active artifacts still use chain length after stalls became the difficulty model

**Evidence**

- `forge/src/boxscore_forge/erasure.py:4` states that `target_stalls` is the difficulty target and warns that `target_chain` measures length rather than difficulty.
- `forge/scripts/write_reference_puzzles.py:68` still generates reference packages with `target_chain`.
- `discovery/hand-solve/build_pack.py:105` still creates the human-validation pack with `target_chain`.
- `discovery/verifier/rejection_rates.py:122`, `discovery/render_step.py:26`, `discovery/pitcher-cap/render_boards.py:212`, and the active discovery measurements continue to use chain targets.
- `discovery/hand-solve/build_pack.py:47` says the pack must not be printed until erasure can target stalls; the engine now can, but the caller was not migrated.

**Why this matters**

A long sequence of forced subtractions can have a high chain count without presenting meaningful decision points. The repository's own research identified stalls as the better proxy for difficulty, yet the package writer and human test still select boards by the retired proxy. Labels such as easy, medium, or hard cannot be defended from these artifacts, and existing PDFs/reference packages do not validate the current model.

**Recommendation**

Define versioned difficulty bands in terms of actual stall counts, migrate active producers to `target_stalls`, and record at least `difficulty_model_version`, requested stalls, actual stalls, chain length, blank count, seed, and ordering in internal metadata. Treat chain length as descriptive telemetry only. Invalidate and regenerate all chain-targeted reference and hand-solve artifacts before drawing difficulty conclusions.

**Also affects:** Personas 2, 3, 5, and 8.

### v02-P2-02 - The stall-family report cannot identify the family that restarts solving

**Evidence**

- `discovery/stall-targeted/measure.py:74` says the report will identify the family that restarts propagation after each stall.
- `discovery/stall-targeted/measure.py:83` records the bounding deduction itself.
- Bounding deductions intentionally have `from_identity=None`, so the report maps them to “bounding only.”
- `discovery/stall-targeted/results.txt` confirms the failure: every target reports `bounding only 100%`.

**Why this matters**

The experiment cannot answer its stated question. The result does not show which identity family broke a stall; it only restates that a stall was broken by bounding. Any design or weighting decision based on that family distribution is unsupported.

**Recommendation**

For each transition into bounding, inspect the first subsequent propagation deduction and attribute the restart to that deduction's identity family. If bounding itself needs richer attribution, record the equations or candidate constraints that established the winning bound. Add a fixture with a known post-bound propagation family and regenerate the results.

**Also affects:** Personas 1 and 2.

---

## Persona 8: UX and Graphic Design Specialist

There is no production visual interface to evaluate. The current browser boards and PDFs are research instruments, so recording general visual preferences as product defects would be premature.

The UX evidence is nevertheless blocked by three findings already recorded once above:

- `v02-P1-01`: players can receive more given information than the generator measured.
- `v02-P1-02`: the boards selected for human evaluation use the wrong difficulty variable.
- `v02-P1-03`: the certified/uncertified composition of the hand-solve pack is not enforced.

Until those are fixed and the artifacts are regenerated, timing, completion, frustration, and perceived-difficulty observations from the existing pack should not be used to set UI progression or difficulty labels.

---

## Recommended repair order

1. Fix the canonical erasure-to-package conversion (`v02-P1-01`).
2. Make provenance and independent hit correspondence fail closed (`v02-P1-04`, `v02-P1-05`).
3. Introduce one publication certification boundary (`v02-P1-06`).
4. Migrate active generation to stall targets and repair the hand-solve audit (`v02-P1-02`, `v02-P1-03`).
5. Correct solver family admission and stall attribution (`v02-P2-01`, `v02-P2-02`).
6. Reconcile the current contracts and make regeneration atomic (`v02-P2-03`, `v02-P2-04`).
7. Regenerate reference JSON, hand-solve PDFs/CSV, and affected discovery result files only after the corrected gates pass.

## Residual review limitations

- No production frontend or backend service exists yet, so runtime browser, HTTP, authentication, authorization, deployment, and operational-security behavior could not be assessed.
- No test suite or discovery script was executed during this static review.
- Historical database contents were not queried; database findings are based on the active SQL and documented source guarantees.

