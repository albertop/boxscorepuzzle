# Code Review v37

**Date:** 2026-08-21  
**Scope:** Fresh verification of every finding in v36 against the current source and TODO, plus new findings discovered during that verification.  
**Contract:** [code_review_contract.md](code_review_contract.md)

## Result

The statement that every v36 point is closed is not supported by the current repository.

| Result | Count |
|---|---:|
| Fixed or otherwise resolved | 64 |
| Incomplete fixes | 3 |
| Still pending and explicitly tracked in TODO | 3 |
| **Total v36 findings audited** | **70** |

The three incomplete fixes are reissued below as v37 findings. The three pending items already have explicit TODO entries, so the review contract requires that they remain in the TODO rather than receive duplicate v37 IDs. One genuinely new P3 documentation/diagnostic issue was also found.

No P0, P1, or P2 issue was found in this pass. Four P3 issues are open in v37.

## Method and boundaries

- The current [code_review_contract.md](code_review_contract.md) was applied, including its solo-developer and TODO de-duplication rules.
- [code_review_v36.md](code_review_v36.md) supplied the authoritative 70-item inventory: 1 P1, 20 P2, and 49 P3 findings.
- [todo.md](todo.md) was checked to distinguish implemented work from deliberately pending work.
- Current source, tests, scripts, CI, hooks, client assets, and deployment files relevant to each v36 finding were inspected.
- The existing v37 contents were intentionally disregarded and replaced, as requested.
- No full test suite was run. Read-only static checks completed successfully: Ruff lint, Ruff formatting, the discovery-lint ratchet, and the configured hook-path check. The discovery ratchet still reports its existing 168-findings baseline; that backlog is already tracked and is not a new v37 finding.

## v36 disposition matrix

### P1

| v36 ID | Status | Verification |
|---|---|---|
| v36-P1-01 | **Fixed** | [tools/lint_discovery.py](../../tools/lint_discovery.py) now distinguishes Ruff operational failure from ordinary findings, including the empty-stdout exit-1 case. The ratchet executes successfully. |

### P2

| v36 ID | Status | Verification |
|---|---|---|
| v36-P2-01 | **Fixed** | [bounds.py](../../forge/src/boxscore_forge/bounds.py) now has bounded propagation and raises a contradiction error instead of risking non-termination. |
| v36-P2-02 | **Fixed** | Puzzle/profile consistency is checked during verifier construction, and the profile check is covered by tests. |
| v36-P2-03 | **Fixed** | The batting-order measurement script imports the canonical provenance literal instead of duplicating it. |
| v36-P2-04 | **Fixed** | [.githooks/pre-push](../../.githooks/pre-push) consumes the reference updates supplied on standard input rather than assuming a branch name. |
| v36-P2-05 | **Fixed** | The repository config reports .githooks as core.hooksPath, so the checked-in hook is active in this checkout. |
| v36-P2-06 | **Fixed** | [write_reference_puzzles.py](../../forge/scripts/write_reference_puzzles.py) validates required traits before publishing written packages, with tests for the failure path. Some wording left behind by this change is separately reported as v37-P3-04. |
| v36-P2-07 | **Fixed** | The division-chain boundary test now exercises the real implementation and patches only the controlled dependency. |
| v36-P2-08 | **Fixed** | Python and browser validation now both reject disagreement between givens and solution values. |
| v36-P2-09 | **Fixed** | Tutorial totals are valid catalogue keys and a regression guard checks that invariant. |
| v36-P2-10 | **Fixed** | Published metadata is checked for leakage through the certificate registry, including the serialized package read from disk. |
| v36-P2-11 | **Fixed** | Database identifiers are parameterized and the flattened parameter list matches the generated placeholders. |
| v36-P2-12 | **Fixed** | Lineup reasoning is emitted in metadata, and batting order has an explicit family mapping. |
| v36-P2-13 | **Fixed** | [tokens.css](../../serve/src/assets/tokens.css) defines the missing dark-theme palette. |
| v36-P2-14 | **Fixed** | Reference-key controls meet the 44-pixel minimum target size. |
| v36-P2-15 | **Fixed** | Innings/outs conversion is centralized in Python and JavaScript; both supported notations and decimal-zero input are handled consistently. |
| v36-P2-16 | **Fixed** | Client tests use the valid outs interval for the selected innings value rather than the former equality assumption. |
| v36-P2-17 | **Fixed** | Browser title and description are catalogue-driven through applyHead; the original hard-coded generic title is gone. The crawler-only delivery gap is the separately pending v36-P2-18. |
| v36-P2-18 | **Pending in TODO** | The landing shell still has no meaningful pre-JavaScript catalogue content, and rendering waits for puzzle loading. This is explicitly open in [todo.md](todo.md), so it is not duplicated as a v37 finding. |
| v36-P2-19 | **Pending in TODO** | Test fixtures remain under the deployment tree and no production image/build boundary currently proves their exclusion. This is explicitly open in [todo.md](todo.md), so it is not duplicated as a v37 finding. |
| v36-P2-20 | **Fixed** | Zero-density wording is produced only when the gate is active, and callers/tests enforce the conditional behavior. |

### P3

| v36 ID | Status | Verification |
|---|---|---|
| v36-P3-01 | **Fixed** | CI and the local hook both enforce Ruff formatting; the current formatting check passes. |
| v36-P3-02 | **Fixed** | Font-fetch paths are anchored to the repository root rather than the caller's working directory. |
| v36-P3-03 | **Fixed** | Discovery build/render output defaults beside the owning script instead of depending on the launch directory. |
| v36-P3-04 | **Fixed** | The render helper is root-anchored and returns a controlled nonzero result when rendering fails. |
| v36-P3-05 | **Incomplete** | Solution values, puzzle givens, and derivation values are protected, but signed Package.metadata is still a mutable dictionary and is exposed by as_json(). Reissued as v37-P3-01. |
| v36-P3-06 | **Fixed** | The stray second module string was merged into documentation and the unused Relation.family surface was removed. |
| v36-P3-07 | **Fixed** | The discovery query uses portable path handling and deterministic SQL tie-breakers. |
| v36-P3-08 | **Fixed** | Shared verifier helpers now own the duplicated reference/key-pair logic. |
| v36-P3-09 | **Fixed** | The pre-push hook preserves and prints discovery-ratchet failure output. |
| v36-P3-10 | **Fixed** | A regression test compares the tools invoked by the hook and CI instead of merely checking filenames. |
| v36-P3-11 | **Fixed** | The browser test runner captures server output, reports fatal page errors, and has a termination fallback. |
| v36-P3-12 | **Fixed** | The standalone check exits unsuccessfully when mismatches are found. |
| v36-P3-13 | **Fixed** | Row-shape validation checks collection lengths before paired iteration can truncate evidence. |
| v36-P3-14 | **Fixed** | The evidence call site explicitly limits its claim to the four fields that establish to_board fidelity. |
| v36-P3-15 | **Fixed** | The mutation test no longer rotates rows and therefore isolates the intended invalid condition. |
| v36-P3-16 | **Resolved** | The duplicate/incorrect test was removed and the accepted pinch-runner domain rule is documented. |
| v36-P3-17 | **Fixed** | The verifier test now uses real evidence and asserts the expected path prefix. |
| v36-P3-18 | **Fixed** | The lint exemption is path-based, and its remaining blind spot is explicitly documented rather than silently broad. |
| v36-P3-19 | **Incomplete** | The AST helper collects every LineScore constructor, but assertions remain outside the loop and inspect only the final collected call. Reissued as v37-P3-02. |
| v36-P3-20 | **Fixed** | Stale test docstrings were corrected to describe the behavior actually tested. |
| v36-P3-21 | **Fixed** | Ungated selection begins at the minimum eligible candidate instead of inheriting a gated threshold. |
| v36-P3-22 | **Fixed** | The unused reseal API was removed. |
| v36-P3-23 | **Fixed** | Client manifest loading is centralized through readManifest. |
| v36-P3-24 | **Fixed** | ISO-date validation checks both shape and real month/day ranges. |
| v36-P3-25 | **Fixed** | Reveal-card content is inserted as text rather than interpreted as markup. |
| v36-P3-26 | **Fixed** | Enter, clear, and hint paths all refuse mutation after completion, with browser coverage. |
| v36-P3-27 | **Fixed** | Restore accepts entries only for cells whose given value is null. |
| v36-P3-28 | **Fixed** | Package-error tests verify the concrete PackageError type. |
| v36-P3-29 | **Fixed** | Signing documentation no longer recommends a permanent environment secret, and the writer accepts a key file. |
| v36-P3-30 | **Fixed** | GitHub Actions dependencies are pinned to immutable commit SHAs. |
| v36-P3-31 | **Fixed** | Compose uses the explicit no-restart policy. |
| v36-P3-32 | **Fixed** | Generated reference HTML escapes title and introduction content. |
| v36-P3-33 | **Fixed** | Embedded JSON neutralizes closing-tag sequences before insertion into HTML. |
| v36-P3-34 | **Fixed** | Manifest identifiers are escaped before use in generated markup. |
| v36-P3-35 | **Fixed** | The README accurately states that the browser client does not verify package signatures. |
| v36-P3-36 | **Fixed** | The reference writer imports the canonical ZERO_DENSITY_GATE. A stale comment about the prior gate remains and is included in v37-P3-04. |
| v36-P3-37 | **Incomplete** | Slotting and board conversion moved into the package, but the production reference writer still imports its loader and Loaded type from discovery/measure.py. Reissued as v37-P3-03. |
| v36-P3-38 | **Fixed** | Identity mapping has an explicit UNMAPPED set and a completeness assertion. |
| v36-P3-39 | **Fixed** | Totals labels include their section and are scoped to prevent ambiguous lookup. |
| v36-P3-40 | **Fixed** | Percentile calculation uses nearest-rank semantics and tests the floor behavior. |
| v36-P3-41 | **Pending in TODO** | The plain-erasure route still lacks its requested calibrated lower bound. The TODO explicitly records the required measurement before implementation, so this is not duplicated as a v37 finding. |
| v36-P3-42 | **Fixed** | Bounding evidence computes equations_live from the phases actually scanned. |
| v36-P3-43 | **Fixed** | Compose enables init so the service has correct signal/reaping behavior. |
| v36-P3-44 | **Fixed** | The misleading selected-set comment was corrected. |
| v36-P3-45 | **Resolved by decision** | The documented decision keeps the current query fallback until the future route work; no immediate code change remained in the original finding. |
| v36-P3-46 | **Fixed** | The static document declares English as its language. |
| v36-P3-47 | **Fixed** | Page descriptions are catalogue-driven through applyHead. |
| v36-P3-48 | **Resolved by decision** | The serve brief now documents the canonical URL/status behavior; implementation was not part of this documentation finding. |
| v36-P3-49 | **Resolved by decision** | The social-metadata decision is documented and its eventual implementation is correctly dependent on the still-pending crawler-shell work. |

## Findings

### Python Principal Engineer

#### v37-P3-01 — Signed package metadata remains externally mutable

- **Hat:** Python Principal Engineer
- **Severity:** P3
- **Origin:** Incomplete fix for v36-P3-05
- **Location:** [forge/src/boxscore_package/format.py:891](../../forge/src/boxscore_package/format.py#L891), [forge/src/boxscore_package/format.py:1017](../../forge/src/boxscore_package/format.py#L1017)
- **Description:** Package is a frozen dataclass, but metadata remains a caller-owned dict. The immutability work copied and wrapped Solution.values, Puzzle.given, and Derivation.values, but not Package.metadata. Package.as_json() also returns the same mutable mapping rather than a detached representation.
- **Impact:** A caller can mutate metadata after signing. The in-memory object still appears frozen, but its canonical payload changes and its signature no longer describes the object. This weakens the value-object contract at the signed package boundary and leaves the original v36 finding only partially corrected.
- **Reproduction:** Create and sign a Package, retain or obtain its metadata dictionary, mutate one metadata entry, and serialize or verify the same Package again. The mutation succeeds even though Package is frozen, and the signed bytes change.
- **Suggested fix:** Copy and recursively freeze metadata at Package construction, or store an immutable normalized representation and return a fresh JSON-compatible copy from as_json(). Add a regression test that attempts nested and top-level mutation after signing.

#### v37-P3-03 — Reference publication still imports its loader from discovery code

- **Hat:** Python Principal Engineer
- **Severity:** P3
- **Origin:** Incomplete fix for v36-P3-37
- **Location:** [forge/scripts/write_reference_puzzles.py:23](../../forge/scripts/write_reference_puzzles.py#L23), [forge/scripts/write_reference_puzzles.py:30](../../forge/scripts/write_reference_puzzles.py#L30)
- **Description:** slot_references and to_board were promoted into boxscore_forge.publish, but the production reference writer still modifies sys.path and imports Loaded and load from discovery/measure.py. The publication path therefore continues to depend on a research module that is outside the typed/linted production package boundary.
- **Impact:** Cleanup or experimentation in discovery can still break the reference publication command. It also prevents the publication path from being understood and checked as a self-contained production dependency graph.
- **Reproduction:** Rename or make an incompatible research-only change to discovery/measure.py, then import or run write_reference_puzzles.py. Publication fails before it reaches the promoted helpers.
- **Suggested fix:** Promote the stable loader contract and Loaded representation into boxscore_forge.publish (or another production module), import them normally, and remove the discovery sys.path injection from the writer.

### QA and Reliability

#### v37-P3-02 — Line-score source guard validates only the final constructor

- **Hat:** QA and Reliability Engineer
- **Severity:** P3
- **Origin:** Incomplete fix for v36-P3-19
- **Location:** [forge/tests/test_line_score_anchors.py:65](../../forge/tests/test_line_score_anchors.py#L65), [forge/tests/test_line_score_anchors.py:75](../../forge/tests/test_line_score_anchors.py#L75)
- **Description:** line_score_calls() now returns all LineScore constructor calls, but the test assigns expression inside a loop and performs its assertions after the loop. Consequently, only the final collected constructor is validated. The companion inning-array test also selects index zero explicitly rather than proving the invariant for every constructor.
- **Impact:** A new or modified LineScore constructor can derive scores from row data, restoring the exact source-of-truth regression the guard is intended to prevent, while the test remains green as long as the constructor inspected last is safe.
- **Reproduction:** Add a second LineScore constructor to the scanned source and place a forbidden row-derived score expression in any call not retained as the loop's final expression. The guard does not assert on that expression.
- **Suggested fix:** Move every constructor-specific assertion inside a loop over all collected calls. Apply the same all-calls rule to inning-array anchors, and include a fixture or mutation test with at least two constructors so a first-only/last-only regression cannot recur.

#### v37-P3-04 — Reference writer still states pre-fix behavior as current fact

- **Hat:** QA and Reliability Engineer
- **Severity:** P3
- **Origin:** New
- **Location:** [forge/scripts/write_reference_puzzles.py:11](../../forge/scripts/write_reference_puzzles.py#L11), [forge/scripts/write_reference_puzzles.py:64](../../forge/scripts/write_reference_puzzles.py#L64), [forge/scripts/write_reference_puzzles.py:170](../../forge/scripts/write_reference_puzzles.py#L170), [forge/scripts/write_reference_puzzles.py:364](../../forge/scripts/write_reference_puzzles.py#L364)
- **Description:** Several comments and diagnostics still describe conditions that the v36 fixes changed. The writer says trait survival is what the tutorial must teach, although the current check protects client/rendering coverage; it says batting order cannot be carried by a family, although Identity.BATTING_ORDER now maps to Family.BATTING_ORDER; and it describes the current six references as coming from the former 0.25 gate despite the closure record stating they were regenerated under the selected 0.30 gate.
- **Impact:** These statements are operator-facing guidance in the publication path, not harmless historical notes. They can send a maintainer toward the wrong component, cause the already-settled family decision to be reopened, and make the provenance of the reference batch ambiguous.
- **Reproduction:** Compare the writer's module/error text with its _traits_survived docstring and client coverage checks; compare its batting-order comment with the canonical identity mapping; compare its gate comment with the recorded v36 closure in TODO.
- **Suggested fix:** Rewrite the trait text as client/rendering coverage, remove the obsolete family assertion, and make the gate comment match verifiable package provenance. If the gate cannot be inferred from an artifact, record it explicitly in generated metadata rather than preserving an unverifiable comment.

## Pending v36 work retained only in TODO

The following are open, but they intentionally receive no v37 finding ID because [todo.md](todo.md) already tracks them:

| v36 ID | Why it remains open |
|---|---|
| v36-P2-18 | Meaningful crawler/no-JavaScript catalogue content still requires the planned shell/rendering work. |
| v36-P2-19 | A production deployment boundary that excludes serve/tests is not yet buildable or demonstrated. |
| v36-P3-41 | The plain-erasure floor awaits the explicitly required calibration measurement. |

## Bottom line

The developer closed most of v36 correctly, but not all of it. The accurate state is:

- **64 of 70** v36 findings are fixed or resolved.
- **3 of 70** were only partially corrected and are reopened as v37-P3-01 through v37-P3-03.
- **3 of 70** remain explicitly pending in TODO and must not be represented as completed.
- **1 new P3** issue, v37-P3-04, records contradictory pre-fix guidance still present in the reference writer.

No production source was changed by this review.
