# Code Review v22

Date: 2026-08-19

## Result

Three new findings: two P2 findings and one P3 finding. No P0 or P1 finding is reported.

This pass reviewed the completed schema-4 tightening, the Python and browser package readers, the
publication and certification boundaries, the corrected footnote renderers and shared vectors, the
new gated multiplicity measurement, and the updated product and package documentation.

The v21 package fix is effective at both parse boundaries: `solution` is required, answer cells are
complete, and puzzle LOB is required. Its direct-construction path is still inconsistent and is
reported below rather than treating v21-P1-01 as fully closed. The v21 measurement now applies the
zero-density predicate and counts affected rows with one OR, but its full eligibility cohort still
differs from the loader and is also reported below.

Known work already recorded in `docs/reviews/todo.md` is excluded: the five-board hand solve, ladder
labels and layer 3b, the remaining six-pitcher measurements, the scoreboard rerun, the existing
discovery ruff findings, and the unbuilt serve persistence, reveal, timer, routing, and event surfaces.

No tests, linters, type checks, builds, database queries, or browser validation were run during this
review.

## Backend Architect

### v22-P2-01 - Direct construction can still serialize a solution that schema 4 forbids

**Severity:** P2

**Locations:**

- `forge/src/boxscore_package/format.py:489`
- `forge/src/boxscore_package/format.py:521`
- `forge/src/boxscore_package/format.py:577`
- `forge/src/boxscore_package/format.py:608`
- `forge/tests/verify/test_package_and_limits.py:414`
- `forge/tests/verify/test_package_and_limits.py:419`
- `docs/reviews/todo.md:2283`

**Description:** Schema 4 now has the right two board profiles at both JSON readers, but
`Package.__post_init__` does not enforce the answer profile on a directly supplied `Board`.

`Board.from_json(..., complete=True)` rejects null answer cells, and the browser reader applies the
same rule. Direct `Package(...)` construction checks labels, slot references, the schema number, and
the puzzle's per-batter footnotes, but it never verifies that `solution` is a `Board` with no null
batting or pitching cells or totals. `as_json()` then serializes that incomplete answer. The resulting
dictionary is output accepted by the writer and rejected by its own `Package.from_json()` reader.

The gap is not merely untested. The tally test deliberately constructs a package with a holed solution
and says that it must still reach verification layer 2. That test preserves the exact constructor
asymmetry v21-P1-01 required `__post_init__` to remove, while `todo.md` records the constructor fix as
closed.

**Impact:** A normal Python API path can create and serialize a document outside schema 4's language.
The standard verifier catches the demonstrated null cell as malformed, which limits current
publication exposure and is why this residual issue is P2 rather than P1. The package model still
cannot guarantee that what it writes can be read back, however, and any writer or signer used before
verification receives an invalid document without an error at the boundary that created it.

**Reproduction:** Start with a valid `Board`, replace one solution batting value with `None`, and pass
that board as `solution` to an otherwise valid `Package(...)`. Construction succeeds and `as_json()`
emits the cell as JSON null. Passing that emitted value to `Package.from_json()` raises `PackageError`
because the solution is required to be complete. The existing tally test at line 424 constructs this
same holed answer and demonstrates that it passes `Package.__post_init__`.

**Fix and rationale:** Put the two board-profile checks behind one helper and call it from both
`Board.from_json` and `Package.__post_init__`: puzzle allows nulls only in erasable grids and totals;
solution allows no nulls anywhere. Also require `solution` to be a `Board` at runtime. Replace the tally
test's malformed identity example with a complete numeric board whose identities disagree, then add a
direct-constructor test proving that a holed answer is refused before serialization. One profile
validator keeps direct construction, JSON parsing, and browser parsing answerable to the same schema.

## QA / Reliability

### v22-P2-02 - The repaired multiplicity report still measures a different cohort from the loader

**Severity:** P2

**Locations:**

- `discovery/footnote-multiplicity/measure.py:53`
- `discovery/footnote-multiplicity/measure.py:63`
- `discovery/footnote-multiplicity/measure.py:103`
- `discovery/footnote-multiplicity/measure.py:114`
- `discovery/difficulty-metrics/measure.py:442`
- `discovery/difficulty-metrics/measure.py:449`
- `discovery/difficulty-metrics/measure.py:450`
- `discovery/footnote-multiplicity/result.log:14`

**Description:** The new shared `SHAPE_CTE` and `zero_density_clause()` correctly close the missing-gate
part of v21-P2-01, but they are only part of the loader's eligibility query. The multiplicity script
still defines its own `admissible` CTE twice and calls it the cohort from which the board draws.

The real loader inner-joins `retroGameLogs`, requires a non-null `VisLineScore`, and samples only its
1910-through-2029 decade windows. Neither multiplicity CTE contains those requirements. A game can
therefore pass provenance, roster caps, and zero density and enter the reported `100,742` directions
even though `load()` cannot return it. This is especially material because the loader's own comments
record incomplete game-log coverage; the omitted join is not only a theoretical SQL distinction.

**Impact:** The corrected report proves that repeated footnote terms occur, so the unambiguous
`<count> #<slot>` format remains the right behavior. Its exact `4,040 of 100,742`, `4.01%`, and decade
rates still do not describe the stated production cohort. Those numbers have been copied into the PDF
renderer, browser renderer, shared vectors, and tests, so a denominator mismatch is now repeated as a
project fact.

**Reproduction:** Consider a `retroGamesReg` game with accepted non-deduced provenance whose two team
shapes pass the caps and 30% gate, but which has no qualifying `retroGameLogs` row or has a null
`VisLineScore`. Both multiplicity `admissible` CTEs count its offensive directions. The loader removes
the game at its inner join or `l.VisLineScore IS NOT NULL` predicate, before it can build a `Loaded`
direction.

**Fix and rationale:** Extract the complete candidate-eligibility CTE, including the game-log join,
line-score requirement, season scope, provenance rule, caps, and optional gate, from the loader rather
than sharing only the shape and ratio fragments. Use that one definition in both multiplicity queries,
rerun the instrument, and update every copied count and percentage. Sharing the complete cohort is the
only durable way for a research denominator and the generator to mean the same thing.

## Python Principal

### v22-P3-01 - The multiplicity instrument executes its full aggregate query twice

**Severity:** P3

**Locations:**

- `discovery/footnote-multiplicity/measure.py:75`
- `discovery/footnote-multiplicity/measure.py:76`
- `discovery/footnote-multiplicity/measure.py:78`

**Description:** The first cursor executes the full cohort-and-row aggregate and fetches its result.
After leaving that block, a second cursor executes the identical query again solely to read
`cursor.description`. The second result set is never consumed.

**Impact:** Every measurement performs two full scans for the first report before running the separate
per-decade query. This deterministically increases database work and the operator's wait time for a
read-only discovery command whose result requires only one execution.

**Reproduction:** Call `main()` and observe the two explicit `execute(query)` calls at lines 76 and 78.
Both interpolate the same aggregate SQL; only the row from the first and the column metadata from the
second are retained.

**Fix and rationale:** Keep the first cursor, read `cursor.description` from it after `fetchone()`, and
build `found` before discarding that cursor. The DB-API cursor retains its result metadata, so one
execution supplies both values and column names without a redundant scan.

## Other Personas

**Frontend Engineer:** The browser reader now enforces a complete solution, and the browser footnote
renderer matches the canonical count/slot/order vectors. No independent frontend finding was found.

**Security:** No new practical security finding was found. The reviewed changes do not add an
attacker-controlled network, credential, authorization, or command-execution boundary, so
attack-scenario fields are not applicable.

**UX / Visual:** Printing every carrier as `<count> #<slot>` removes the previous count-versus-slot
ambiguity, and both renderers place LOB consistently. No independent visual or interaction regression
was found in the implemented surface.

**Baseball / Boxscore:** The corrected row-level OR and the count-first notation preserve repeated HBP,
SF, SH, and CI values without losing their lineup attribution. The remaining cohort issue is covered by
v22-P2-02.

**Kakuro / Logic-Puzzle:** A complete answer is now enforced at both parse boundaries, and the residual
direct-construction hole is covered by v22-P2-01. No separate deduction or uniqueness regression was
found.

## Recommendation

Make direct package construction enforce the same answer profile as both readers before considering
the schema-4 contract fully closed. Then centralize the complete loader cohort and rerun the
multiplicity measurement before treating its exact prevalence as settled. The duplicate aggregate
execution can be removed in the same small measurement change.
