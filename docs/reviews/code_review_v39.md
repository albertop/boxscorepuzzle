# Code Review v39 - Full Codebase Review

**Date:** 2026-08-22  
**Method:** Static review of the complete active repository. No test, lint, type-check, build, database, or browser command was run.  
**Excluded:** `_not_in_use/`, historical findings already closed, and work already recorded as pending in `docs/reviews/todo.md`.

## Disposition — 2026-08-22, all five closed

**Every finding was reproduced in the code before anything was changed, and every fix was checked by
reverting the thing its test asserts.** `docs/reviews/todo.md` carries the two instrument failures that
came out of doing it.

| ID | Status | What closed it |
|---|---|---|
| v39-P1-01 | ✔ Fixed | The pointer reads `entry.assigned`. The `generation` **parameter is gone** rather than corrected, so there is no longer a way to pass the wrong one. `test_a_pointer_names_the_generation_that_owns_its_package` builds two generations and asserts each pointer resolves to a package that exists. |
| v39-P1-02 | ✔ Fixed | `_era_plan()` derives the quota and the offsets from the whole window and reconciles with the early boards already inside it. Three cases: the retry's allowance, the retry's spacing, and an **overlapping** window. |
| v39-P2-01 | ✔ Fixed | Every Postgres statement rolls back on failure and re-raises. The `INTEGER` range is checked at the boundary, so the ordinary cause never reaches the driver. Three Postgres-only cases prove a rejected row leaves writes **and the health check** working. |
| v39-P2-02 | ✔ Fixed | The line score is compared scalar by scalar and inning by inning, length first; `reveal` is required. The now-unreachable `if (reveal)` in `finish.js` was **deleted** rather than left as a guard that cannot fire. |
| v39-P3-01 | ✔ Fixed | The §6 bullet says the whole footnote line is given and read-only, and records that it said the opposite for weeks. The historical correction above it is untouched. |

### One thing the report asked for that was deliberately not done

v39-P2-01's fix suggests capping counters to their declared SQL range **and** using `BIGINT` for
`duration_ms` if long durations are valid. The range check is in. **The duration ceiling is not**, and
it is not an oversight: `CLAUDE.md`'s *sanity-check client-reported durations* is a number that shapes
the product, so §7 puts it to the operator rather than into this file. `todo.md` carries it as open.

⚠️ **What that leaves true:** the connection-abort defect is closed, because no accepted value can now
overflow the column. A twenty-five-day duration is still storable and would still skew a percentile.
There are no percentiles yet.


## Executive summary

Five actionable findings remain: **two P1, two P2, and one P3**. The two P1 findings are both in the new inventory workflow and are reachable through the documented solo-operator procedure: a short build followed by the instructed retry, or a later top-up that creates a second generation.

The v38 corrections themselves remain statically closed: the import exemption is present, a short build now exits non-zero while retaining resumable checkpoints, the inventory header describes the active producer, and the tutorial gate wording was corrected. The inventory findings below are new invariants that the v38 tests do not exercise; they do not reopen the already-fixed exit-code defect.

## P1 findings

### Backend Architect

#### v39-P1-01 - A top-up signs old dates as if their packages belonged to the new generation

- **Hat:** Backend Architect
- **Severity:** P1
- **Location:** `forge/scripts/build_inventory.py:296`, `forge/scripts/build_inventory.py:315`, `forge/scripts/build_inventory.py:339`, `forge/scripts/build_inventory.py:477`, `docs/runbook-inventory.md:277`
- **Description:** Each calendar entry correctly records the generation that produced its package in `Entry.assigned`. However, `write_pointers()` ignores that field. It walks the complete calendar and writes the single current `generation` argument into every active date pointer. `build()` calls it with `out.name`, so a top-up in generation B rewrites pointers for generation-A dates claiming their packages live in B. The runbook explicitly says that multiple generations after a top-up are normal and that old packages remain in their original generations.
- **Impact:** The signed date-to-package guarantee is false after the first top-up. If the daily rotation copies an old date's pointer from the newest pointer tree, it requests `generation-B/<old-id>.json`; that package exists only in generation A, producing a 404 on a legitimately assigned date. The signature makes the incorrect mapping look authoritative rather than catching it.
- **Reproduction:** Build one window into `genA`, then build a later window into `genB`. Inspect `genB/days/<date-from-genA>.json`: its `puzzle_id` is the old ID but its `generation` is `genB`. The manifest and package files in `genB` contain only the packages produced by the second run, so `genB/<old-id>.json` does not exist.
- **Suggested fix:** Build each pointer with `entry.assigned`, not the current output directory name. Keep writing a complete pointer schedule into the newest private generation if that is the intended rotation source, but let each pointer resolve to the generation that actually owns its package. Add one mixed-generation test that creates an A entry and a B entry, then asserts that each pointer names its entry's `assigned` generation and that `<inventory>/<pointer.generation>/<pointer.puzzle_id>.json` exists.

### Python Principal Developer

#### v39-P1-02 - Retrying a short build recomputes the era quota over only the gaps

- **Hat:** Python Principal Developer
- **Severity:** P1
- **Location:** `forge/scripts/build_inventory.py:299`, `forge/scripts/build_inventory.py:421`, `forge/scripts/build_inventory.py:438`, `forge/scripts/build_inventory.py:441`, `forge/scripts/build_inventory.py:472`
- **Description:** A retry correctly removes assigned dates from `wanted`, but then computes both `era_quota(len(wanted))` and `spread(len(wanted), pre_wanted)` from that reduced list. It neither subtracts pre-1950 boards already assigned in the requested window nor preserves the original window offsets. Every retry therefore receives a fresh five-percent allowance and a fresh spacing plan.
- **Impact:** The runbook's normal recovery path can exceed the pre-1950 ceiling or bunch historical games that were meant to appear roughly three weeks apart. `_fill()` checkpoints every assignment to the authoritative calendar before the final `audit()`. If the audit catches the excess, the command fails only after leaving the invalid calendar on disk. If an older calendar gives the global audit enough unused allowance, the malformed local window can pass and receive signed publication artifacts.
- **Reproduction:** Start a 150-day build that successfully assigns all seven permitted pre-1950 boards but runs out after assigning only part of the modern arm. Re-run the same command as instructed. The remaining gaps receive `floor(remaining * 0.05)` additional pre-1950 slots, even though the original window has already spent its full allowance. For example, 43 remaining gaps permit two more historical boards, taking that window from seven to nine.
- **Suggested fix:** Derive the era plan from the complete requested window, then reconcile it with entries already present in that window. At minimum, compute remaining historical allowance as the full-window allowance minus historical entries already assigned, and select eligible gaps by their original offsets rather than by their position in the reduced list. If the early pool cannot fill an allowed historical slot, permit a modern board there rather than granting a fresh historical allowance on the next run. Add a test where the first pass fills the entire historical arm and only part of the modern arm, then retry and assert both the final count and the original-window spacing.

## P2 findings

### Security Reviewer

#### v39-P2-01 - One database value error leaves the PostgreSQL connection permanently aborted

- **Hat:** Security Reviewer
- **Severity:** P2
- **Location:** `keep/src/keep/reading.py:39`, `keep/src/keep/reading.py:43`, `keep/migrations/001-initial.sql:27`, `keep/src/keep/store.py:204`, `keep/src/keep/store.py:218`, `keep/src/keep/app.py:85`
- **Description:** The API accepts every non-negative Python integer, while the production schema stores durations and counters in 32-bit PostgreSQL `INTEGER` columns. `PostgresStore._insert()` commits on success but never rolls back on `executemany()` or `commit()` failure. PostgreSQL therefore leaves the service's reused connection in the aborted-transaction state after an out-of-range value or another statement error.
- **Impact:** One rejected batch prevents every later event, client-error report, and health query from succeeding until the process reconnects or restarts. The outbox preserves the data, but it cannot make progress against a connection that every request reuses in the failed state.
- **Reproduction:** Send an otherwise valid authenticated event with `duration_ms: 2147483648`. `read_event()` accepts it, PostgreSQL rejects it as outside the `INTEGER` range, and no rollback occurs. Send a normal event or call `/health` afterward; PostgreSQL answers that the current transaction is aborted instead of executing the new statement.
- **Trust boundary and preconditions:** The boundary is JSON accepted from `serve` over the internal network. Exploitation requires the shared-token caller, a forwarding defect in `serve`, or another process on that Docker network; the data-layer port itself is deliberately not public.
- **Exploitation method:** Submit one schema-valid batch containing an integer outside PostgreSQL's column range. No SQL injection or secret recovery is required.
- **Blast radius / business impact:** All persistence and health reporting in the single `keep` process remain unavailable until restart. Existing rows are not exposed or overwritten.
- **Classification:** CWE-703, Improper Check or Handling of Exceptional Conditions; operationally aligned with OWASP A04:2021 Insecure Design because an accepted boundary value can permanently disable the service's only transaction channel.
- **Suggested fix:** Put the PostgreSQL insert and commit inside a transaction context, or catch database exceptions, call `rollback()`, and re-raise. Also align boundary ranges with storage: use `BIGINT` for `duration_ms` if long durations are valid, and cap counters to their declared SQL range. Add a real-PostgreSQL contract test that causes one rejected insert and then proves a normal insert and `alive()` still succeed.

### Frontend Engineer

#### v39-P2-02 - The browser reader accepts publication-invalid clues and an absent reveal

- **Hat:** Frontend Engineer
- **Severity:** P2
- **Location:** `docs/javascript-conventions.md:82`, `docs/javascript-conventions.md:85`, `serve/engine/package.js:146`, `serve/engine/package.js:200`, `serve/engine/package.js:251`, `serve/engine/package.js:278`, `serve/engine/package.js:316`, `serve/ui/phone/finish.js:178`
- **Description:** `readPackage()` parses a line score independently from both `puzzle` and `solution`, but `agreesWithTheAnswer()` compares only the three grids, totals, footnote totals, and LOB. A changed puzzle line-score clue is therefore accepted even when the solution says something else. The same reader treats a missing or explicit-null `reveal` as valid, although the publication gate requires a complete reveal and the client has no use for an unpublished draft package.
- **Impact:** A one-field static-file corruption can show a line-score clue that contradicts the answer board, making a valid daily puzzle look arithmetically impossible while the checker continues grading against the untouched solution. Removing `reveal` is even quieter: the player can finish the entire puzzle and receive a result dialog whose earned boxscore area is empty. Neither case becomes the controlled package refusal required by the JavaScript boundary convention.
- **Reproduction:** In a current package, change only `puzzle.line_score.offense_runs`; `readPackage()` still returns successfully. Separately, delete `reveal` or set it to `null`; the reader returns a puzzle, and `renderReveal()` deliberately skips `clippingFor()` because `reveal` is falsy.
- **Suggested fix:** Keep the existing reader architecture and add the two missing checks: compare every line-score scalar and inning array between puzzle and solution, and require `reveal` on the browser's served-package path. Add focused browser tests for those two mutations. If a future tool genuinely needs to read unpublished drafts, give that tool an explicitly named draft reader rather than weakening the player boundary.

## P3 findings

### Kakuro / Logic Puzzle Expert

#### v39-P3-01 - The primary project guide still says per-batter footnotes are erasable

- **Hat:** Kakuro / Logic Puzzle Expert
- **Severity:** P3
- **Location:** `CLAUDE.md:324`, `CLAUDE.md:326`, `CLAUDE.md:643`, `serve/ui/phone/board.js:294`
- **Description:** `CLAUDE.md` correctly records that the 5-to-15-stall result was a working instrument pointed at solver-filled zeros, but its authoritative mobile-board section still states the superseded opposite: per-batter footnote cells are erasable and produce that 5-to-15 increase. The live board renders them as given, read-only clues.
- **Impact:** The main implementation guide gives a future editor a direct instruction to restore a retired interaction and the invalid difficulty scale behind it. Because the contradiction is inside one document, reading the historical correction does not reliably protect the implementation section from being followed literally.
- **Reproduction:** Compare `CLAUDE.md:326` with the board rule at `CLAUDE.md:643`; both claim to describe the current product and give opposite answers. `renderFootnotes()` confirms the live behavior by drawing prose rather than editable cells.
- **Suggested fix:** Rewrite only the section-6 bullet to say that per-batter footnotes, their totals, and LOB are given and read-only, and that live non-zero terms remain visually prominent. Keep the historical correction at lines 324-330 intact because it explains why the old 5-to-15 number must not be reused.

## Hat coverage with no additional unique finding

- **QA / Reliability:** The active tests, conformance vectors, browser harness, inventory tests, CI workflows, and developer tools were reviewed. Their relevant coverage gaps are attached to v39-P1-01, v39-P1-02, and v39-P2-02 rather than duplicated.
- **UX / Visual Design:** Phone layout, focus lifecycle, modal behavior, tutorial flow, error presentation, HTML, and CSS were reviewed. No additional concrete defect was found beyond the empty final clipping described in v39-P2-02.
- **Baseball / Boxscore Domain:** Visitor-first ordering, line-score mapping, innings-as-outs, substitutions, footnote attribution, and complete-boxscore reveal mapping were reviewed. No row-level validation was demanded for the reveal-only half that is intentionally taken as-is. The only new clue-integrity issue is included in v39-P2-02.
- **Docker Expert:** `compose.yaml`, container-facing comments, service binding, init behavior, restart policy, mounts, CI PostgreSQL services, and the documented development-only scope were reviewed. The absent production Docker/VPS shape is already pending in `todo.md` and was not refiled as a bug.

## Deliberate non-findings

- Research questions and human difficulty measurements remain questions, not bugs.
- The retired v30-P1-02 claim about independently validating the reveal-only half remains retracted.
- Pending SEO/server-rendering work, production nginx/Docker work, daily rotation implementation, and human hand-solve tasks were not duplicated from `todo.md`.
- No issue was opened merely for preferring a different abstraction, adding enterprise concurrency machinery, or increasing validation that does not protect a load-bearing product behavior.
