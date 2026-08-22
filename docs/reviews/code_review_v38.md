# Code Review v38

**Date:** 2026-08-22

**Scope:** Next full code review after v37, using `docs/reviews/code_review_contract.md`. I reviewed the current source tree, the updated review/TODO documents, the Python conventions document, the changed inventory/publication code, CI hooks, compose configuration, and the v37 findings. `_not_in_use` paths were ignored.

**Contract:** `docs/reviews/code_review_contract.md`

## Result

v37 is mostly closed, but one v37 item remains partially open and three new issues were found.

| Result | Count |
| --- | ---: |
| v37 findings fixed | 3 |
| v37 findings incomplete | 1 |
| New v38 findings | 3 |
| Open v38 findings | 4 |

No P0 issues were found. Current open set: one P1, one P2, two P3.

## v37 disposition

| v37 ID | Status | Verification |
| --- | --- | --- |
| v37-P3-01 | Fixed | `Package.metadata` is now copied/frozen with `MappingProxyType`, and `as_json()` returns a fresh dict. |
| v37-P3-02 | Fixed | The line-score anchor tests now iterate through every `LineScore` constructor result instead of validating only the final loop value. |
| v37-P3-03 | Fixed | `write_reference_puzzles.py` now imports `Loaded` and `load` from `boxscore_forge.pool`, not from the discovery script. |
| v37-P3-04 | Incomplete | Some stale diagnostic/comment text was corrected, but the reference writer still describes the surviving-traits gate as a tutorial requirement. Reissued below as v38-P3-02. |

## Findings

### Python Principal Developer

#### v38-P1-01 - The inventory builder violates the active Ruff import rule

- **Hat:** Python Principal Developer
- **Severity:** P1
- **Location:** `forge/scripts/build_inventory.py:50`
- **Description:** `build_inventory.py` adds the project roots to `sys.path`, then performs late imports. The existing late imports are marked with `# noqa: E402`, but the new `write_package` import is not. Ruff's `E402` rule is active, and the scripts override in `forge/pyproject.toml` does not ignore `E402`.
- **Impact:** The pre-push/CI lint command can fail on this file before the inventory work can be merged or published. This is a blocking tooling regression, not a style preference.
- **Reproduction:** From `forge/`, run `uv run ruff check scripts/build_inventory.py`; Ruff reports `E402` for the `write_package` import on line 50.
- **Suggested fix:** Combine the import with the already-exempt line, for example `from boxscore_package.format import Package, write as write_package  # noqa: E402`, or add the same `# noqa: E402` rationale to the new import.

### Backend Architect

#### v38-P2-01 - Inventory build can commit a short calendar as a successful run

- **Hat:** Backend Architect
- **Severity:** P2
- **Location:** `forge/scripts/build_inventory.py:232`, `forge/scripts/build_inventory.py:250`, `forge/scripts/build_inventory.py:259`
- **Description:** The default build path can generate fewer entries than requested, write those entries into the authoritative calendar, and still exit successfully. `per_decade` is computed with `round(days * DRAW_MARGIN / 12)`, `_entries()` may return fewer entries than `wanted`, `write(CALENDAR, extend(...))` runs before the shortfall check, and the shortfall is only printed as a warning.
- **Impact:** A 150-day inventory run can appear successful while leaving calendar gaps. Because the calendar is append-only and treated as serving truth, a missed warning can promote an incomplete beta inventory state instead of forcing the operator to retry or raise the draw margin.
- **Reproduction:** Use a sample where candidate games are rejected because of duplicate games or package-production failures. `_entries()` returns fewer entries than `wanted`; `build()` still writes the partial calendar and only prints `WARNING: ... dates unfilled`.
- **Suggested fix:** Treat a short build as failure before writing `forge/calendar.json`, or add a retry/top-up loop that guarantees `len(entries) == len(wanted)` before the authoritative calendar is mutated. If partial package directories are useful as evidence, keep them outside the committed calendar state. If `DRAW_MARGIN` is intended as a minimum margin, use `ceil()` instead of `round()`. Add direct tests for this path with fake candidates and a temporary calendar/output directory.

### QA and Reliability

#### v38-P3-01 - Inventory builder header still describes the pre-build measurement-only script

- **Hat:** QA and Reliability
- **Severity:** P3
- **Location:** `forge/scripts/build_inventory.py:8`, `forge/scripts/build_inventory.py:24`
- **Description:** The module docstring still says "Measuring is all it does today" and describes the "assignment half" as deliberately absent. That is no longer true: the default command builds packages and writes calendar entries, while `--measure` is the read-only mode.
- **Impact:** This is operator-facing source guidance on a script that now mutates publication state. A maintainer can reasonably read the header and assume the default invocation is safe measurement-only, which is exactly the dangerous assumption for inventory generation.
- **Reproduction:** Compare the module header with `main()`: without `--measure`, it calls `build()`, which writes packages and extends `forge/calendar.json`.
- **Suggested fix:** Rewrite the header around the current two modes: `--measure` is read-only measurement; default invocation is a build/write operation. Move the old rationale to history/TODO only if it is still useful.

#### v38-P3-02 - Reference writer still reports the surviving-traits gate as a tutorial requirement

- **Hat:** QA and Reliability
- **Severity:** P3
- **Origin:** Incomplete closure of v37-P3-04
- **Location:** `forge/scripts/write_reference_puzzles.py:11`, `forge/scripts/write_reference_puzzles.py:218`
- **Description:** The helper now correctly frames `_traits_survived()` as client/rendering coverage in one docstring, but two remaining strings still say the selected games must teach the tutorial: the module docstring names "the two cases the tutorial has to teach", and the failure message says a game "does not teach what the tutorial needs."
- **Impact:** The diagnostic points future maintainers back to a removed product requirement. If the rendering coverage gate fails, the error message sends the next fix in the wrong direction.
- **Reproduction:** Trigger `_traits_survived()` with a package that lacks the required rendering traits; the raised `ValueError` still mentions tutorial needs.
- **Suggested fix:** Replace the remaining tutorial wording with the actual invariant, for example "does not preserve the client rendering traits required by the reference set."

## Hats with no additional findings

- **Security Reviewer:** No new security issue found in the reviewed changes. The new publication-key helper avoids printing private key material and checks the configured private key against the checked-in public key.
- **Frontend Developer / UX and Visual Designer:** No new frontend or visual regression found in this pass.
- **Baseball / Boxscore Domain Expert:** No new scoring or boxscore-domain correctness issue found beyond the calendar completeness risk above.
- **Kakuro / Logic Puzzle Expert:** No new puzzle-logic issue found in this pass.
- **Docker / Containerization Expert:** No new Docker issue found in `compose.yaml`. Existing production container/image work remains covered by the beta plan/TODO and is not duplicated here.

