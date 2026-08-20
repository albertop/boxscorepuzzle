# Code Review v21

Date: 2026-08-19

## Result

Two new findings: one P1 and one P2. No P0 or P3 finding is reported.

This pass reviewed the schema-4 migration, the regenerated reference packages, the corrected footnote renderers, the reveal-name loader change, and the newly recorded discovery measurement. All three v20 findings are closed and are not repeated.

Known work already recorded in `docs/reviews/todo.md` is excluded: the fifty-board pack still targeting chain, the six-pitcher remeasurements, the scoreboard-duplicate rerun, the existing discovery ruff findings, and the unbuilt product surfaces.

No tests, linters, type checks, builds, database queries, or browser validation were run during this review.

## Backend Architect

### v21-P1-01 - Schema 4 does not require the solution it needs, or require that solution to be complete

**Severity:** P1

**Locations:**

- `docs/package-format-v4.md:72`
- `docs/package-format-v4.md:89`
- `forge/src/boxscore_package/format.py:247`
- `forge/src/boxscore_package/format.py:267`
- `forge/src/boxscore_package/format.py:390`
- `forge/src/boxscore_package/format.py:464`
- `forge/src/boxscore_package/format.py:520`
- `forge/src/boxscore_package/format.py:550`
- `serve/engine/package.js:111`
- `serve/engine/package.js:130`
- `serve/engine/package.js:175`
- `serve/engine/game.js:49`
- `serve/engine/game.js:146`
- `serve/engine/game.js:169`

**Description:** The player engine cannot operate without a complete answer board, but schema 4 still has three incompatible definitions of that invariant.

The schema table marks top-level `solution` nullable. Python follows that statement: `Package.solution` defaults to `None`, construction accepts it, `as_json()` omits the field, and `from_json()` accepts an absent or null solution. The browser does the opposite and unconditionally parses `raw.solution` as a board, so it rejects the document Python accepts and can produce.

When a solution object is present, both readers parse its batting and pitching grids with the same nullable rules as the puzzle. Neither boundary requires the "completed board" to be complete. If a puzzle blank and its answer are both null, `createGame()` initially sees `valueOf(cell) === cell.answer`; `isSolved()` therefore treats the visible blank as solved. `enter()` can never mark a null answer correct because correctness explicitly requires a non-null entry. The game can finish with an unanswered cell, while entering any number is necessarily wrong.

The same profile disagreement exists for `puzzle.left_on_base`. The schema table and Python reader allow null, while the Python `Board` docstring and browser reader say it is a required given. A direct Python `Package(...)` validates only per-batter puzzle footnotes and can therefore serialize other incomplete givens that its own parse path or the browser refuses.

The shared conformance vectors do not cover an absent solution, a null solution, a null solution cell, or a null `left_on_base`. The schema-document test checks top-level field publication but does not read the board table's nullability or exercise the browser boundary.

**Impact:** A producer using the documented Python API can build, sign, and publish a schema-4 package that the browser refuses at boot. A different malformed package can be accepted by both readers and let the player finish or reveal the answer while a visible blank remains. This is the same producer/consumer contract split schema 4 was introduced to eliminate. The current six generated packages happen to contain non-null solutions and LOB values, so the active manifest does not exercise the defect.

**Reproduction:** Construct an otherwise valid Python `Package` without passing `solution`. The default `None` passes `__post_init__`, serializes without a `solution` key, and parses again in Python; `readPackage()` rejects it at `board(raw.solution, "solution")`. Separately, take a current package, choose one puzzle cell that is null, and set the matching solution cell to null. Both package readers accept it. `createGame().isSolved()` considers that cell correct while it remains visibly empty, and no non-null entry can match its null answer.

**Fix and rationale:** Define explicit board profiles instead of parsing puzzle and solution with one nullable rule. A puzzle may have nulls only in the erasable batting and pitching cells and totals; its footnotes, LOB, and line score are complete. A solution is required and every one of its cells is a non-negative integer. Enforce the same profiles in `Package.__post_init__`, Python `from_json`, and the browser reader. Change the schema table to make `solution` and `left_on_base` non-null, and correct the package module's stale opening statement that says the solution/source is stripped even though `published()` deliberately keeps it. Add shared vectors for all four failure shapes so neither reader can drift independently. Because the document says versions are never tightened in place, either make this correction explicitly before schema 4 is considered published, or cut the next schema version rather than leaving two meanings of 4.

## QA / Reliability

### v21-P2-01 - The footnote-multiplicity instrument reports a gated pool without applying the gate

**Severity:** P2

**Locations:**

- `discovery/footnote-multiplicity/measure.py:43`
- `discovery/footnote-multiplicity/measure.py:46`
- `discovery/footnote-multiplicity/measure.py:60`
- `discovery/footnote-multiplicity/measure.py:81`
- `discovery/footnote-multiplicity/measure.py:85`
- `discovery/footnote-multiplicity/measure.py:98`
- `discovery/footnote-multiplicity/measure.py:112`
- `discovery/difficulty-metrics/measure.py:340`
- `discovery/footnote-multiplicity/result.log:1`
- `docs/reviews/todo.md:2338`

**Description:** The new instrument says it measures the admissible pool after the 30% zero-density gate, imports `ZERO_DENSITY_GATE`, prints `gate applied downstream (30%)`, and copies the resulting 2.73% into code comments, test vectors, and `todo.md`. Neither SQL query applies that gate.

Its `shape` CTE computes only batter and pitcher counts, and the `WHERE` clauses enforce only `BATTER_CAP` and `PITCHER_CAP`. By contrast, the real loader computes twelve row/total zero counts and applies the ratio predicate at `discovery/difficulty-metrics/measure.py:340`. The imported gate constant is used only in the report label.

There is a second counting weakness in the same report: `total_many` sums the per-term counts and labels the result as rows. A single row carrying more than one repeated term is counted more than once. The per-direction query correctly uses an `OR`, but the reported row numerator does not.

**Impact:** The published figures `10,207 of 373,917`, `2.73%`, and the decade rates do not describe the pool the generator ships from. The gate is selective enough that an ungated prevalence cannot be substituted for a gated one. The safer count-first footnote format remains sensible, but the claimed incidence and era distribution have not been measured under the stated cohort, so they cannot support prioritization or historical conclusions.

**Reproduction:** Compare the instrument's `admissible` CTE with the loader's `gate_clause`. A direction above the 30% zero-density threshold still enters both multiplicity queries whenever its roster sizes and provenance pass. For the row count, a row satisfying two expressions such as `B_HP > 1` and `B_SH > 1` increments two `many_*` columns and is added twice to `total_many`.

**Fix and rationale:** Extract the loader's zero-density SQL shape and predicate into one reusable discovery helper, then use it in both multiplicity queries instead of reimplementing a partial `shape` CTE. Count affected rows with one `CASE WHEN term_a > 1 OR ... THEN 1` expression. Rerun the instrument and replace every copied rate in `result.log`, `todo.md`, `build_pack.py`, `board.js`, the canonical vectors, and their tests. Centralizing the cohort predicate matters more than adding another assertion around the current query: one definition prevents the measurement and production pool from drifting again.

## Other Personas

**Python Principal:** The actionable Python contract issue is v21-P1-01. The v20 dataclass corrections are present; the intentionally mutable board-topology record is not re-reported.

**Frontend Engineer:** The schema/engine completion mismatch is covered by v21-P1-01. The two footnote renderers now agree on count, slot marker, term order, and LOB placement; no independent frontend finding was found.

**Security:** No new practical security finding was found. The reviewed changes do not add an attacker-controlled network, credential, authorization, or command-execution boundary, so attack-scenario fields are not applicable.

**UX / Visual:** The count-first footnote notation is unambiguous in both renderers. The false-completion state from an incomplete solution is covered by v21-P1-01.

**Baseball / Boxscore:** The reveal-name source now uses the Retrosheet master and its nickname/surname fields consistently. The multiplicity cohort defect is covered by v21-P2-01.

**Kakuro / Logic-Puzzle:** A null answer violates the puzzle's requirement that every blank have one determinate integer and is covered by v21-P1-01. No separate deduction-rule regression was found.

## Recommendation

Close v21-P1-01 before treating schema 4 as a publishable contract. Re-run and correct the multiplicity evidence before quoting its prevalence, but the count-first rendering itself does not need to be reverted while that measurement is repaired.
