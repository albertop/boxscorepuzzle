# Code Review v05

**Date:** 2026-08-18  
**Method:** Static review only. No tests, generators, database queries, PDF rendering, or validation commands were run.  
**Scope:** Active project code and project-owned Markdown under `forge/`, `serve/`, `discovery/`, and `docs/`. `_not_in_use` was excluded. Markdown unchanged since v04 was not reread; the three changed Markdown files were reviewed against the already-read baseline. Existing open or pending backlog items were not assigned new IDs.

## Executive summary

The post-v04 work makes a useful domain correction: batting positions now come from the position of entry, lineup slots are explicit, substitute grouping no longer depends on label punctuation, and the highest-observed-stalls experiment now calls itself a lower bound rather than a ceiling.

Seven new findings remain. Three P1 findings block a trustworthy handoff to `serve` or invalidate the human-solve evidence: lineup slots do not cross the package boundary, erased footnotes are revealed by the renderers, and the reference writer silently signs with a repository-known fallback key. Four P2 findings affect obsolete ambiguity research, metric units, mobile prototype validity, and regression-test strength.

The six v04 findings remain in `docs/reviews/todo.md` and are deliberately absent here. The chain-to-stall pack replacement, Ed25519 migration, generation retention, signed manifest, exact-cohort comparator, and family-count semantics are also not reopened.

| Priority | Count | Meaning in this review |
|---|---:|---|
| P1 | 3 | Blocks a correct package/UI contract, invalidates a launch-gate experiment, or defeats a security boundary |
| P2 | 4 | Can produce false research conclusions, misleading prototypes, or false regression confidence |

## Findings

### v05-P1-01: The slot identity required by the new board design disappears at the package boundary

**Perspectives:** Backend Architect, Frontend Engineer, QA/Reliability, Baseball/Boxscore Expert  
**Locations:** `discovery/difficulty-metrics/measure.py:122`, `forge/scripts/write_reference_puzzles.py:76`, `forge/src/boxscore_package/format.py:288`, `serve/data/puzzles/**/*.json`

`Loaded.slots` is now the source of truth for substitute grouping, the visible `9a`/`9b`/`9c` row reference, and footnote attribution. The package writer transfers labels, pitcher labels, boards, reveal data, and metadata, but it does not transfer either `slots` or the derived slot references. `Package` has no field for them, and the published reference JSON contains neither.

This information cannot be reconstructed from the remaining payload. Position labels are intentionally no longer suffixed, repeated positions often belong to different lineup slots, and substitutes in one slot can carry different positions. Row order alone says that the rows are adjacent; it does not say where one slot group ends and the next begins.

**Impact:** A frontend built against the current signed packages cannot render the decided slot column, indent substitutes reliably, or turn `SH: 9b` into a reference to one visible row. Inventing grouping in the client would create a second baseball rule and can attach a footnote term to the wrong row, breaking the row identity while every column total still balances.

**Recommended fix:** Add a versioned, signed row-identity field such as `batting_slots` or canonical `slot_references`. Validate that its length equals the batting rows, labels, and footnote rows; validate slots in `1..9`; and validate that each slot is one contiguous group. Derive human references once on the forge side. Because schema 1 is frozen, coordinate this with the next package schema rather than hiding a required client contract in undocumented metadata. Regenerate the reference packages after the contract exists.

### v05-P1-02: Human-facing renderers reveal footnote cells that the solver treated as erased

**Perspectives:** Kakuro/Logic Puzzle Expert, QA/Reliability, UX/Graphic Design, Python Principal Developer  
**Locations:** `discovery/hand-solve/build_pack.py:90`, `discovery/hand-solve/build_pack.py:519`, `discovery/pitcher-cap/render_boards.py:49`, `discovery/pitcher-cap/render_boards.py:246`, `CLAUDE.md:355`, `docs/design-boxscore-puzzle.md:722`

The canonical erasure set includes per-batter HBP, SF, SH, and CI cells. `to_board()` correctly turns an erased footnote cell into `None`, so solver difficulty and layer 3b are measured with that value unknown.

The hand-solve PDF does not render those puzzle cells. It calls `footnote_line(candidate.loaded)`, which reads the complete source `Direction` and prints every real carrier. The HTML renderer has the same boundary mismatch: `blanks()` records only batting and pitching cells/totals, while the page prints the complete `board["footnotes"]` strings. Therefore a value removed for grading is handed back to the person looking at the artifact.

This is distinct from v02-P1-01. That finding fixed `Direction -> Board`; the current recurrence is `Board -> human-visible artifact`. The contradictory documentation makes recurrence easier: `CLAUDE.md` says per-batter footnotes are erasable, while a still-active design section says the footnote line is complete and never erased.

**Impact:** The printed board is easier than the puzzle whose stalls, chain, and independent derivability are recorded in its key. Any conclusion about perceived difficulty, layer 3b, or whether footnotes create useful work is invalid because the human and solver did not solve the same state. The planned fifty-board launch gate cannot answer its stated questions until this is fixed.

**Recommended fix:** Build every visual footnote from `candidate.puzzle.footnotes`, never from `Loaded.direction`. Design an explicit visible representation for `None` in the sparse footnote line before producing another pack; an erased attribution must have a placeholder the player can resolve. Extend the renderer's blank model to footnotes. Add a surface-parity test that maps every erased cell to a visible blank and proves that its value is absent from all generated text, while footnote totals and LOB remain visible.

### v05-P1-03: The reference publisher silently replaces a missing signing secret with a public fallback

**Perspectives:** Security Engineer, Backend Architect, QA/Reliability  
**Locations:** `forge/scripts/write_reference_puzzles.py:51`, `forge/scripts/write_reference_puzzles.py:257`

This is not the already-closed v01 verifier issue. Verification now correctly requires a secret, but this publisher always supplies one: if `BOXSCORE_SIGNING_SECRET` is absent or empty, it silently uses `reference-puzzles-only, replace before anything is published`. The packages are written directly under `serve/data/puzzles` and pass the same publication certification path as configured packages. The comment calls the key non-production, but no executable boundary enforces that claim.

**Attack scenario:** A release, CI job, or developer deployment runs the writer without the environment variable and deploys the resulting valid-looking reference packages or configures the verifier with the same convenient fallback.

**Exploitation method:** Anyone who obtains the repository or the literal key can alter puzzle answers, reveal data, or metadata and calculate a matching HMAC. No cryptographic break is required; the signing authority is in the source.

**Business impact:** Forged packages are indistinguishable from forge output under the fallback trust profile. Players can receive manipulated solutions or reveals while verification reports success, undermining the product's core correctness promise.

**Recommended fix:** Fail closed when the environment secret is missing. If fixtures must exercise signed-package parsing, require an explicit `--fixtures` mode, write outside the deployable inventory path, mark the trust profile in the artifact, and make production import reject it. Emit a conspicuous mode banner. Coordinate the final production key shape with the already-planned public-key migration, but do not wait for that migration to remove the silent fallback.

### v05-P2-01: The active ambiguity experiment now measures duplicate positions rather than ambiguous footnote references

**Perspectives:** Kakuro/Logic Puzzle Expert, Baseball/Boxscore Expert, QA/Reliability  
**Locations:** `discovery/difficulty-metrics/measure.py:220`, `discovery/difficulty-metrics/measure.py:751`, `discovery/difficulty-metrics/measure.py:844`

`_batting_labels()` now intentionally returns bare positions, so two `CF` rows in different lineup slots remain two `CF` labels. `ambiguity()` still groups rows by `loaded.labels`, erases the matching footnote cells as an ambiguous group, and is still called from `main()`.

Its docstring describes the opposite implementation: it says labels are still suffixed (`LF-1`, `LF-2`) and predicts that no current groups will be found. Current samples can instead produce many same-position groups that are not ambiguous at all because their slot references differ. The experiment then creates an artificial domain over unrelated rows and reports its solver effects as footnote ambiguity.

**Impact:** Running the main difficulty instrument can emit plausible percentages for a case the current board does not contain. Those values can revive a removed erasure constraint or influence difficulty reasoning from fabricated ambiguity.

**Recommended fix:** Remove `ambiguity()` from the active report. If a historical record is useful, freeze it with its old input model and results outside the active instrument. A current invariant should instead assert that every rendered footnote reference identifies exactly one row through `slot_references`; any duplicate reference is a construction error, not a solver experiment.

### v05-P2-02: The compressibility report compares normalized search cost against impossible raw-count thresholds

**Perspectives:** Python Principal Developer, QA/Reliability, Kakuro/Logic Puzzle Expert  
**Locations:** `discovery/difficulty-metrics/compressibility.py:334`, `discovery/difficulty-metrics/compressibility.py:342`, `discovery/difficulty-metrics/compressibility-results.txt:221`

The current run shows search costs with means around `0.8-0.9` and a maximum of `1.0`. The report then asks how many trivial steps have “scan cost” at least `5`, `10`, and `20`. Every answer must be zero under the current normalized metric, regardless of the data.

The section is intended to test whether the trivial-resolution discount throws away steps that were hard to find. Because its thresholds are in an obsolete unit, the printed `0.0%` values cannot falsify or support that claim.

**Recommended fix:** Define the unit and expected domain next to `search_cost` and assert it in the instrument. Use meaningful normalized thresholds or quantiles, such as the upper decile, if the normalized score is the intended metric. If the question requires raw scan volume, report `equations_live` or another raw counter under a different name. Include the metric version and range in generated results so a solver telemetry change cannot silently preserve stale thresholds.

### v05-P2-03: The 375 px prototypes are wider than a 375 px viewport and omit mobile viewport configuration

**Perspectives:** Frontend Engineer, UX/Graphic Design, QA/Reliability  
**Locations:** `discovery/board-prototype/slot-column-sample.html:1`, `discovery/board-prototype/substitute-grouping-sample.html:1`, `discovery/board-prototype/footnote-reference-sample.html:1`, `discovery/board-prototype/row-corrections-sample.html:1`

Each prototype claims to judge the board at `375px`, but each starts with a style block rather than a document shell and has no viewport meta tag. The body adds `14px` padding on both sides, while each content-box section is fixed at `375px` plus borders. The resulting document needs roughly `405px`, not `375px`.

On an actual 375 px phone this causes horizontal overflow or browser scaling. Without `<meta name="viewport" content="width=device-width, initial-scale=1">`, a mobile browser may also use its wider default layout viewport and shrink the entire page. A nominal `44px` cell can therefore render below the touch-size assumption the prototype is supposed to validate.

**Recommended fix:** Give every prototype a complete HTML shell and viewport meta tag. Use global `box-sizing: border-box`, `section { width: 100%; max-width: 375px; }`, and keep page padding inside the 375 px budget. Judge at 320, 375, and a desktop width. If any prototype is promoted into `serve`, add semantic row/column headers and keyboard/focus behavior then; there is no active application UI to audit yet.

### v05-P2-04: The new regression guards do not exercise the branches and consumers they claim to protect

**Perspectives:** QA/Reliability, Python Principal Developer, Backend Architect  
**Locations:** `forge/tests/test_row_labels.py:43`, `forge/tests/test_row_labels.py:175`, `forge/tests/test_no_label_formatting_decisions.py:28`, `forge/tests/test_no_label_formatting_decisions.py:37`

The starter-position repair added the `started_at` branch to `_position()`, but the position parameterization still calls `_position()` with only the original three arguments. Its “starter” examples therefore test the fallback `appeared_at` path, not the lineup-fielding-code branch that fixed the two-third-basemen defect.

The test named `test_the_cell_and_the_footnote_are_the_same_string_for_the_same_row` assigns both variables from the same `references[index]` expression. It is a tautology and will stay green if `board_table()` or `footnote_line()` stops using that helper. The AST-wide label guard also detects only a punctuation literal used with the `in` operator against a variable whose name contains `label`; `startswith`, `endswith`, indexing, splitting, regexes, aliases, and a newly added renderer sharing the allowlisted basename all bypass it.

**Impact:** The suite advertises end-to-end protection for the exact non-arithmetic failure class that prompted the change, but common regressions can pass without exercising the SQL-derived starter position or either rendering consumer.

**Recommended fix:** Add `_position("3B", None, None, 8) == "CF"` and DH starter cases, plus an integration fixture proving the lineup query supplies `started_at` only to the named starter. Test actual `board_table()` and `footnote_line()` outputs for one shared slot rather than assigning the helper result twice. Narrow renderer exemptions to explicit paths and expand the static guard with representative bypass cases, or replace punctuation policing with a typed row view-model that makes slot-based decisions the only available API.

## Perspective coverage

| Review perspective | Result |
|---|---|
| Python Principal Developer | Renderer/source separation, stale metric units, dead experiment logic, and weak regression abstractions are covered. |
| QA/Reliability Engineer | All seven findings have a reproducible failure path or a missing invariant. |
| Frontend Engineer | No active `serve` UI exists. The package lacks required row identity data, and the prototypes do not measure a real 375 px viewport. |
| Security Engineer | v05-P1-03 includes attack scenario, exploitation method, business impact, and a fail-closed fix. Other authentication, authorization, session, CSRF, and multi-tenant topics do not yet apply because `serve` has no application code. |
| Backend Architect | The package seam and signing mode are the principal architectural blockers. Existing manifest findings remain in v04 and are not duplicated. |
| Baseball/Boxscore Expert | Entry positions and lineup slots are the right domain sources; the failure is that slot identity does not survive publication and obsolete code still groups by position. |
| Kakuro/Logic Puzzle Expert | The human artifact receives hidden terms back, the ambiguity model no longer matches the board, and one difficulty diagnostic uses impossible thresholds. |
| UX/Graphic Design | The slot/reference direction is promising, but the experiment width and erased-footnote representation must be corrected before visual conclusions are trusted. |

## Improvements worth preserving

- `_position()` now expresses one baseball rule with two sources: starting lineup for starters and substitution events for substitutes.
- `slot_references()` gives the visible slot cell and footnote attribution one canonical representation.
- The pack and reference writer now detect substitutions from slot data rather than punctuation in labels.
- Generated HTML in `render_boards.py` escapes interpolated database values and includes a viewport meta tag; the standalone board prototypes should reuse that shell.
- The highest-observed-stalls script now searches nine paths per board, reports non-convergence, and explicitly calls the result a lower bound.
- The reference writer targets stalls rather than silently relabelling chain length as difficulty.

## Review boundary and residual risk

No source code was changed. No tests were executed. PDFs were not visually rendered or compared, and SQL behavior was assessed from query construction rather than against the database. Existing backlog work and explicit open research tasks were omitted rather than renumbered as v05 findings.
