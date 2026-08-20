# Code Review v28 - Full Source Review

## Review contract and scope

This is a full-tree static review, not a delta review. It covers the active authored source under
`forge/src`, `forge/scripts`, `serve/engine`, `serve/ui`, `tools`, and `discovery`, together with the
Python and browser test suites and the source templates used to produce research artifacts. Generated
HTML, published puzzle JSON, fonts, logs, historical review documents, and `_not_in_use` were treated as
artifacts rather than independently maintained source; their producers and consumers were reviewed.

The review uses the solo-developer threat and operating model in `docs/reviews/non-issue.md`. Findings
do not depend on a second developer, a hostile repository actor, CI, or concurrent publishers. Work
already identified as pending in `docs/reviews/todo.md` is not repeated as a finding. In particular,
unfinished serve routing/reveal/finish behavior and the open product decision about whether layer 3b
should become a publication gate are excluded.

No tests, linters, type checks, builds, database queries, PDF rendering, or browser validation were run.
The findings below come from source inspection and direct traces through the relevant code paths.

## Findings

### v28-P2-01 - The weak solver turns lower-bound inequalities into exact values

- **Persona:** Software architect / data scientist / test engineer
- **Severity:** P2
- **Location:** `forge/src/boxscore_verify/reason.py:188`, `forge/src/boxscore_verify/reason.py:203`, `forge/tests/verify/test_weak_solver.py:64`
- **Description:** `_bound_one_relation()` calculates both ends of a finite interval for every relation.
  For an inequality it then resets `low` to zero but leaves `high` untouched. That is valid only for a
  positive target coefficient, where a relation of the form `c*x + rest <= constant` supplies an upper
  bound. With a negative target coefficient, the inequality supplies a lower bound and no upper bound;
  retaining the equality-derived `high` can collapse an open range to one fabricated value. The strong
  narrowing implementation in the same module handles the two signs correctly at lines 92-97, but the
  one-relation-at-a-time solver does not mirror that rule.
- **Impact:** `derive_in_view()` can report a puzzle as human-derivable after inserting values the
  inequalities do not determine, and those values can be wrong. Layer 3b is report-only today, so this
  does not let an invalid package through the publication gate. It does invalidate the evidence used to
  say that layer 3b itself is sound, including the pass/fail counts recorded in the current TODO and any
  decision about promoting it to a gate.
- **Reproduction:** Use the existing verifier relation `H - AB <= 0` (`AB >= H`). Give `H = 0` and leave
  `AB` unknown. Every non-negative `AB` satisfies the relation. With no other unknown terms,
  `_bound_one_relation()` computes `low = 0`, `high = 0` for the `-AB` term, resets only `low`, and records
  `AB = 0`. A real row with `H = 0, AB = 4` therefore receives an unsupported and incorrect deduction.
  The current weak-solver tests exercise complete boards, one-blank equalities, and one particular
  weak-versus-strong subset comparison, but no negative-coefficient inequality in isolation.
- **Recommended fix and rationale:** Treat inequalities as one-sided in `_bound_one_relation()`, exactly
  as `narrow()` does: positive coefficients may tighten only the upper side; negative coefficients may
  tighten only the lower side. Resolve a cell only when the legitimate bounds coincide. Add a direct
  regression for `H - AB <= 0` with `H = 0`, plus a generated property asserting that every value the
  weak solver claims agrees with the strong solver over varied erasures. Rerun every recorded layer 3b
  measurement after the fix; the existing figures were produced by the affected predicate.

### v28-P2-02 - The provenance rebuild can replace the canonical table with an empty or partial table

- **Persona:** Software architect / security and data-integrity reviewer / solo-maintainer
- **Severity:** P2
- **Location:** `discovery/retrosheet-coverage/load_provenance.ps1:52`, `discovery/retrosheet-coverage/load_provenance.ps1:91`, `discovery/retrosheet-coverage/load_provenance.ps1:96`, `discovery/retrosheet-coverage/load_provenance.ps1:106`
- **Description:** The script collects provenance into `$origin`, then drops and recreates
  `dbo.retroGameProvenance` before inserting it in batches. It has no minimum/non-empty precondition and
  no transaction or staging-table swap. A valid but empty zip directory, or a directory containing no
  matching `.E??` entries, reaches the database phase with `$origin.Count == 0`, drops the existing
  table, skips the insert loop, and completes with an empty canonical table. An ODBC failure after any
  batch similarly leaves a partial table in place.
- **Impact:** The loader's inner join to provenance interprets missing rows as an empty or selectively
  truncated admissible population. Subsequent measurements can therefore return no boards or a biased
  subset while reading the table as authoritative. This needs only one operator, one incorrect local
  path or one interrupted load; it does not rely on concurrency or an adversary. The source zips make
  the table rebuildable, but they do not prevent a bad rebuild from becoming the active input.
- **Reproduction:** Point `-ZipDirectory` at an existing empty folder and omit `-DryRun`. `Get-ChildItem`
  succeeds with no archives, `$origin` remains empty, lines 96-102 replace the populated table, the loop
  at line 107 performs no inserts, and the final report prints zero rows. Alternatively, interrupt the
  connection after one 200-row batch; the already-created table and committed rows remain available to
  later queries.
- **Recommended fix and rationale:** Refuse before opening the database when no files, games, or expected
  source types were found. Load into a new staging table inside a transaction, validate uniqueness,
  non-zero volume, expected source categories, and full correspondence with `retroGamesReg`, then replace
  the canonical table and commit. On any failure, roll back and leave the previous table untouched. A
  rebuildable derived table still needs an all-or-nothing publication boundary because every discovery
  cohort trusts its absence semantics.

### v28-P2-03 - Active discovery renderers do not show the package's canonical footnote clues

- **Persona:** Statistician/methodologist / UX and API-contract reviewer / data scientist
- **Severity:** P2
- **Location:** `discovery/sample-boards/render.py:79`, `discovery/sample-boards/render.py:129`, `discovery/board-prototype/build.py:93`, `discovery/pitcher-cap/render_boards.py:250`, `discovery/batting-order/arms.py:316`
- **Description:** The PDF and browser surfaces now render every live footnote carrier with both its
  count and slot reference, for example `SH: 2 #9b`. The discovery renderers still build terms from
  `loaded.labels` and a truthiness test. They print a row label once regardless of whether the row's
  value is one or greater, and use a position label instead of the package's unambiguous slot reference.
  `render_step.py` routes several current measurements through this representation, while the
  batting-order experiment explicitly calls the text renderer for the specimen pages on which its eye
  check rests. The renderer's own contract says it is the board exactly as the player sees it.
- **Impact:** Numerical solving is unaffected, but visual evaluation is performed against a different
  clue surface from the one that ships. Multiplicity is lost, repeated position labels can be
  ambiguous, and a reviewer deciding whether a PA deduction feels like real work may see weaker or
  different footnote information than the player receives. That directly weakens the specimen evidence
  for the active batting-order decision and any discovery report whose mandatory eye check uses
  `render_step.py`.
- **Reproduction:** Give one batting row two sacrifice hits in slot `9b`. The canonical browser/PDF line
  is `SH: 2 #9b`. Both discovery builders test only whether the value is truthy and append the row's
  position label once, producing a shape such as `SH: P`; the value `2` and row reference `9b` are both
  absent. Two rows with the same position label become indistinguishable as well.
- **Recommended fix and rationale:** Make discovery footnote rendering consume the same canonical
  conformance vectors as the independent PDF and browser implementations, while keeping its formatting
  code separate. Derive carriers from `loaded.slots` through the established slot-reference rule and
  print every count, including one. Add the discovery renderer as a third consumer of
  `serve/tests/footnote-line-vectors.json`, then regenerate the current batting-order specimens before
  using their eye check. Shared data preserves independent implementations without allowing the visible
  contract to drift.

### v28-P3-01 - The footnote-height instrument reports zero terms for every package

- **Persona:** UX and API-contract reviewer / test engineer
- **Severity:** P3
- **Location:** `serve/tests/footnote-height.html:42`, `serve/tests/footnote-height.html:45`, `serve/tests/footnote-height.html:52`, `serve/tests/engine.test.js:445`
- **Description:** The height page counts `line.querySelectorAll(".cell").length` and labels the result
  `erased terms`. The current footnote renderer deliberately contains no `.cell` elements; the browser
  suite explicitly asserts that both `.cell` and `[data-cell]` counts are zero. Consequently every row
  in the height table reports zero terms, and sorting by that number preserves manifest order rather
  than ordering boards by footnote complexity.
- **Impact:** Pixel height remains measured correctly, but the table cannot support its intended
  relationship between term count and height. A reader can attribute a tall block to an unexplained
  package rather than to the number of live terms/carriers, and the heading still describes the retired
  erasable-footnote UI.
- **Reproduction:** Open the measurement page against any package with a live footnote. The rendered
  line contains `.term` and `.who` elements but no `.cell`, so `terms` is zero even though visible terms
  exist. The same invariant is pinned by the test at `engine.test.js:451`.
- **Recommended fix and rationale:** Count `.term:not(.lob)` for live categories, or count `.who`
  carriers if carrier density is the variable being measured, and rename the column accordingly. Add a
  non-vacuity assertion that at least one package has a positive count. The instrument should measure a
  DOM shape the product still has.

### v28-P3-02 - The PDF checker silently skips a key file that the operator explicitly supplied

- **Persona:** Test engineer / solo-maintainer
- **Severity:** P3
- **Location:** `discovery/hand-solve/check_pdf.py:70`, `discovery/hand-solve/check_pdf.py:91`, `discovery/hand-solve/check_pdf.py:104`
- **Description:** The command accepts an optional key path and checks its required columns only when
  `key.exists()` is true. If the operator supplies a misspelled, moved, or absent key path, the key
  branch is silently skipped and the command can print its full success message. This contradicts the
  module's stated fail-closed purpose: omission is a deliberate mode, but an explicit unreadable input
  is not omission.
- **Impact:** A hand-solve pack can be declared checked even though the artifact needed to interpret its
  ratings was never opened. A single local typo is enough; no unusual environment or second actor is
  required. The PDF checks still run, so the output looks like a complete pass rather than a partial
  one.
- **Reproduction:** Run `python check_pdf.py boards.pdf missing-key.csv` with a valid PDF. `main()` passes
  a non-null `Path`, line 91 evaluates false, no problem is added, and the success line at 101 is printed
  if the PDF itself passes.
- **Recommended fix and rationale:** When a key argument is present, require `is_file()` and a readable,
  non-empty CSV before checking its columns; fail with the supplied path otherwise. Keep `None` as the
  only explicit PDF-only mode. An input named by the operator must be verified or rejected, never
  silently downgraded out of the check.

## Persona disposition

- **Software architect:** The publish/verify split and signed package boundary remain coherent. The weak
  solver has one independent semantic implementation defect, but it is not currently a publication
  gate.
- **Security reviewer:** No practical confidentiality or remote-exploitation finding exists under the
  documented single-operator model. The provenance finding is data integrity, not an adversarial race.
- **Performance engineer:** No material active runtime or memory defect was found. The expensive
  discovery scripts generally persist or protect long-running work appropriately.
- **Test engineer:** The production and verifier suites are unusually strong about non-vacuity. The
  remaining actionable gaps are narrowly tied to the weak inequality semantics and two standalone
  instruments outside the main suite.
- **Data scientist:** Layer 3b figures must be rerun after `v28-P2-01`; their current pass/fail pattern is
  not reliable evidence about human derivability.
- **Statistician/methodologist:** Cohort pairing and denominator discipline are mostly explicit. The
  active visual specimens remain a different observation surface from the product (`v28-P2-03`).
- **UX/API-contract reviewer:** The shipped browser and PDF footnote contract agrees through shared
  vectors. Discovery views and the height instrument have not fully migrated to it.
- **Solo-maintainer pragmatist:** Fix the three P2s before making another layer 3b or batting-order
  decision. The two P3s are small, local repairs and do not justify broader refactoring.

## Verdict

No P0 or P1 finding was identified. The full review found **three P2 findings and two P3 findings**.
The publication core, package boundary, signature flow, strong verifier, and current browser game engine
show no new practical correctness defect from this pass. The immediate risk is instead that research
evidence can certify unsupported weak-solver deductions or show a clue surface different from the one
being judged, while the provenance rebuild has an avoidable destructive failure mode.

Recommended order:

1. Correct the weak solver and rerun layer 3b evidence.
2. Make the provenance rebuild validate and commit atomically.
3. Bring discovery footnotes onto the canonical visible contract and regenerate the batting-order specimens.
4. Repair the two fail-open/stale measurement checks.
