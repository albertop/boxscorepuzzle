# Code Review v40 - Full Codebase Review

**Date:** 2026-08-23  
**Method:** Static review of the complete active repository. No test, lint, type-check, build, database, browser, Docker, or Git command was run.  
**Scope:** Active Python, JavaScript, HTML/CSS, tests, workflows, hooks, Docker/development configuration, and current Markdown documentation. `_not_in_use`, generated inventory, caches, and historical review findings already closed or explicitly pending in `todo.md` were excluded as sources of new findings.

## Executive summary

Three actionable findings remain: **one P1, one P2, and one P3**. All three are in the newly added publication boundary or its verification. The P1 is a false-green health verdict during a concrete daily-game outage. The P2 undermines the rotation's deliberate strategy of preserving the last valid public state on an I/O failure. The P3 leaves `publish/` outside the weekly clean-checkout safety net while the guard that calls that run complete still passes.

No finding below depends on multiple developers, concurrent publishers, hostile Retrosheet data, independent validation of the reveal-only boxscore half, or a future paid-access design. None duplicates the open pre-push-hook decision or the two pending `MANIFEST_SCHEMA` items in `docs/reviews/todo.md`.

## P1 findings

### Backend Architect

#### v40-P1-01 - Inventory health is green when today's pointer names no public package

- **Severity:** P1
- **Confidence:** High
- **Location:** `publish/src/publish/health.py:55` (`inspect`), especially the package-count ceiling and the independent date-only read at `publish/src/publish/health.py:63`
- **Description:** `inspect()` verifies only that there are at most two package-shaped JSON files and that `today.json.date` equals the serving date. It never reads `today.json.puzzle_id` or checks that `<puzzle_id>.json` exists. Consequently, zero packages is healthy as long as a current-dated pointer remains. The same false green occurs with one surviving package when the missing file is today's.
- **Why this matters:** F3 explicitly exists for the case where the web service is up while the puzzle inventory is empty. In this state Uptime Kuma receives a healthy verdict while `/today` ultimately leads the player to a 404. The only game offered by the product is unavailable and the monitor designed to detect that outage stays green.
- **Reproduction:** Start from a successfully rotated public directory, delete the package named by `today.json`, and call `inspect(public, serving_day)`. The package count falls from two to one, which satisfies `<= PUBLIC_LIMIT`, and the unchanged date satisfies the second check, so the returned `Verdict` has `healthy=True`. An otherwise empty directory containing only `today.json` with the current date also passes.
- **Suggested fix:** Parse the pointer once into at least `date` and `puzzle_id`, require today's target file to exist, and report the missing id as a fault. Apply the same consistency check to `yesterday.json` when that pointer exists, without turning the calendar's legitimate first day into a failure. Add a focused health test that removes today's target after a successful rotation and requires a red verdict. This checks the files the application itself publishes; it does not require revalidating Retrosheet or the package's baseball contents.
- **Blast radius:** The health verdict and future F3 endpoint only. The rotation itself still refuses a missing private source package before publishing, but deletion, an incomplete deploy, or filesystem damage after rotation is currently invisible to monitoring.

## P2 findings

### Python Principal Developer

#### v40-P2-01 - In-place writes can destroy the last valid public pointer during a failed rotation

- **Severity:** P2
- **Confidence:** High
- **Location:** `publish/src/publish/rotate.py:157`, `publish/src/publish/rotate.py:158`, and `publish/src/publish/rotate.py:194`
- **Description:** Packages are copied directly to their served names, and `today.json`, `yesterday.json`, and `manifest.json` are written directly with `write_text()`. Opening an existing JSON file for writing truncates it before the replacement bytes are complete. A disk-full, short-write, permission, or other ordinary filesystem failure can therefore leave a malformed pointer or manifest on the public path. This contradicts the implementation's stated ordering: a part-way failure is supposed to leave more public content rather than less, so the health check can report the excess while the last game remains playable.
- **Why this matters:** At rollover, `today.json` is the control file that selects the daily game. If its write fails after truncation, the previous valid pointer has already been destroyed and the new one is incomplete. The rotation raises, but players have neither a valid old pointer nor a valid new one. The same pattern can expose a torn public manifest once E1 consumes it.
- **Reproduction:** Begin with a valid rotated directory, run the next day's rotation, and inject an `OSError` after the destination `today.json` has been opened/truncated but before all bytes are written. The call fails and the served pointer is no longer valid JSON. No concurrent process or multi-developer timing is required; this is one writer experiencing one local filesystem error.
- **Suggested fix:** Keep the current simple ordering, but write every public artifact to a sibling pending file and use `Path.replace()` only after the pending write or copy closes successfully. On a pre-replace failure, remove the pending file and leave the old served file untouched. Add one fault-injection test around the extracted atomic-write helper that proves the old bytes survive a failed pending write. A multi-file transaction, lock service, or concurrent-publisher protocol is not needed for this project.
- **Blast radius:** The daily and yesterday pointers, the public manifest, and any package being copied at rollover. Successful rotations are unchanged; only failed filesystem writes gain a safe previous state.

## P3 findings

### QA / Reliability

#### v40-P3-01 - The weekly clean-checkout run omits `publish/`, and its completeness guard cannot see that

- **Severity:** P3
- **Confidence:** High
- **Location:** `.github/workflows/weekly.yml:79` through end of file; `forge/tests/test_the_hook_runs_what_ci_runs.py:119`
- **Description:** `weekly.yml` runs the forge, browser, and keep checks, then ends after the `keep` coverage command. It never installs or checks `publish/`. `test_the_weekly_run_is_the_complete_one` still passes because it compares a set of tool names: keep already contributes `ruff check`, `ruff format`, `mypy`, and `pytest`, so a second project using the same tools is invisible. The later tree-coverage guard checks the hook and push workflows only, not the scheduled workflow.
- **Why this matters:** `docs/ci.md` defines the weekly job as the complete independent run from a clean checkout, specifically to reveal a disabled or diverged local hook. That assurance is false for the executable responsible for enforcing which puzzles remain public. The dedicated push workflow reduces the immediate risk, which is why this is P3 rather than a release outage, but it does not make the documented weekly guarantee true.
- **Reproduction:** Read the steps in `.github/workflows/weekly.yml`: there is no `working-directory: publish` and no publish install/check/test block. The weekly guard nevertheless sees the same six generic tool names it sees in the hook and reports equality.
- **Suggested fix:** Add the same frozen install, lint, format, mypy, and coverage commands used by `ci-publish.yml` to `weekly.yml`. Extend the existing tree guard so every directory containing a `pyproject.toml` must be named by the scheduled workflow as well as by the hook and a push workflow. Keep the tool-set comparison for detecting genuinely new tools; the two checks answer different questions.
- **Blast radius:** Scheduled verification and its documentation. Push-time `ci-publish.yml` and the local pre-push publish block already exist and are not changed by this finding.

## Hat coverage with no additional unique finding

- **Security Reviewer:** The public/private inventory split, opaque ids, signed pointers, key placement, archive-removal rule, event authentication, and browser trust boundary were reviewed. The availability-preserving write defect is reported once as v40-P2-01; no separate security issue was created from the same root cause.
- **Frontend Engineer:** All active hand-written JavaScript was checked against `docs/javascript-conventions.md`, including package reading, daily scaffolding, storage, outboxes, reporting, clock behavior, DOM construction, and network boundaries. No new concrete defect was found.
- **UX / Visual Design:** Mobile board structure, focus handling, reveal lifecycle, tutorial, finish states, and current responsive assets were reviewed. No new user-facing defect was found.
- **Baseball / Boxscore Domain:** Row identities, innings-as-outs, line-score mapping, footnotes, substitutions, visitor/home direction, and reveal mapping were reviewed. The reveal-only half remains intentionally taken as-is; no issue asks the application to independently reconstruct or validate it.
- **Kakuro / Logic Puzzle Expert:** Erasure, solver families, certification, stall targets, and current difficulty documentation were reviewed. Open hand-solving and measurement decisions remain research or operator work, not bugs.
- **Docker Expert:** The current development container, Compose exposure, planned unprivileged production containers, private keep port, nginx proxy boundary, and the pending F deployment work were reviewed. Missing production images and wiring are explicitly open deliverables, not defects in code claimed complete.

## Deliberate non-findings

- The pre-push hook's moving-working-tree problem is already open at the top of `docs/reviews/todo.md`; it is not duplicated here.
- The two `MANIFEST_SCHEMA` cleanup items are already pending in `docs/reviews/todo.md`; they are not duplicated here.
- `publish/` currently exposes a health verdict as a function rather than an HTTP endpoint, and the production Docker/nginx wiring does not exist. Both are explicitly assigned to F, so neither is reported as a missing implementation.
- Copying new packages before deleting stale ones is an explicit availability decision. v40-P2-01 does not dispute that ordering; it reports that direct truncating writes fail to provide the previous valid state that the ordering relies on.
- No concurrency, multi-developer, enterprise deployment, or adversarial local-inventory scenario was treated as an actionable defect.
- The retired v30-P1-02 claim about independently validating the reveal-only half remains retracted.

## Residual risk and validation gap

This was a static review by instruction. The three reproductions are direct consequences of the current control flow, but no commands were executed to demonstrate them. Once fixed, the narrow useful validation is: one health test with today's package removed, one atomic-write failure test preserving old bytes, and the CI guard test with the publish block temporarily removed from `weekly.yml` to prove it turns red.
