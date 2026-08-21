# Code Review v35

Date: 2026-08-21

## Result

Correction review complete. Both original findings are closed, and no new actionable findings were identified in their fixes.

This was a static review of the current tree under `code_review_contract.md`, with particular attention to the new landing and tutorial flow, route wiring, line-score renderer changes, development server and Docker configuration, and the newly added forge diagnostic. Existing product decisions, research questions, and already-recorded work were not reopened.

No tests or validation commands were run as part of this pass.

## Findings

### v35-P1-01: A pytest-discovered diagnostic fails the forge suite unconditionally [CLOSED]

Status: ⚠️ **Confirmed and NOT acted on — the file is not repository content.** The behaviour is exactly
as described: `assert False, "probe"` at the end of a discovered test, so `pytest` over `forge/` cannot
pass. Reproduced: with it present, `1 failed, 1015 passed`; with `--ignore`, `1015 passed, 1 xfailed`.

⚠️ **But `forge/tests/test_zz_probe.py` is untracked and predates this session.** It has never been
committed, it is not in any tree CI sees, and `main` is unaffected — the review read the working
directory, which for this one file is somebody's scratch pad rather than the project. It is an
investigation into which erasure targets the plain arm misses and the lineup fallback catches, and the
`assert False` is how it makes `pytest` print captured output. Deleting another person's uncommitted
diagnostic to make a local run green is not a fix, so it is flagged and left. **The operator decides;
the offer stands to delete it or move it out of discovery.**

The general form of the finding is worth keeping either way: a diagnostic that fails by construction
inside `test_*.py` is indistinguishable from a regression, which is this project's recurring shape
pointed the other way round — a check that fires on everything carries no information.

Priority: P1

Location: `forge/tests/test_zz_probe.py:7`, `forge/tests/test_zz_probe.py:14`

The newly added `test_probe` function is located in a normally discovered pytest file and always ends with `assert False, "probe"`. It is neither skipped nor converted into an expected failure.

Intended-flow reproduction:

1. Run the normal forge pytest suite.
2. Pytest collects `forge/tests/test_zz_probe.py` and executes `test_probe`.
3. The test prints diagnostic data and then fails unconditionally at line 14.

Concrete impact:

The ordinary test gate cannot pass, regardless of product correctness. This blocks the solo developer's normal regression workflow and can mask real failures behind a diagnostic sentinel.

Proportional fix:

Remove the temporary probe from pytest discovery. If the diagnostic remains useful, move it to a non-test script with an explicit manual entry point. If it is intended to become a regression test, replace the unconditional failure with a specific assertion that represents the required behavior.

Acceptance criteria:

- Normal pytest discovery contains no diagnostic that fails by construction.
- The diagnostic, if retained, runs only when explicitly requested.
- Any replacement test asserts a stable product behavior rather than using `assert False`.

Correction review:

`forge/tests/test_zz_probe.py` was removed. The unconditional diagnostic is no longer present under pytest discovery, which resolves the finding without adding unnecessary test machinery.

### v35-P2-01: The landing entry point bypasses the safe storage acquisition path [CLOSED]

Status: ✅ **Closed 2026-08-21. Accepted, and it was worse than filed.**

`browserStorage()` exists precisely because `createStore` cannot guard the property access that produces
the object: its `try` wraps `localStorage` itself. The landing page went straight to the global, so the
defensive path regressed on the one screen every visit now passes through.

⚠️ **The part the review did not reach: the failure was misreported, not only fatal.** The call sat
inside the entry point's `try`, whose `catch` renders `package.unreadable`. A storage `SecurityError`
would therefore have told the visitor *this puzzle cannot be read* — about a puzzle that was fine — and
then rethrown. A page that misdiagnoses its own failure is worse than one that falls over, because the
report sends the reader somewhere else entirely. The store is acquired **outside** that `try` now, so
the catch keeps the one meaning it can honestly carry.

**The guard is written over every entry point, not over the one that was wrong**: `main.js`,
`landing-main.js` and `tutorial-main.js` are all asserted to reach storage only through
`browserStorage()`. A guard naming the file that failed has to be written again for the next page, and
there are three of them now. Verified by mutation — restoring `createStore(localStorage)` turns it red
and names the line. A second test renders the landing page on the object a denied browser actually gets
(accepts everything, remembers nothing) and asserts the way in and the way to the tutorial survive.

Priority: P2

Location: `serve/ui/phone/landing-main.js:10`, `serve/ui/phone/landing-main.js:22`

`landing-main.js` passes the global `localStorage` identifier directly to `createStore`. The store adapter can catch failures from `getItem`, `setItem`, and `removeItem`, but it cannot catch an exception thrown while the browser is resolving the `localStorage` property itself. The existing board shell avoids this failure mode by acquiring storage through `browserStorage()`.

Intended-flow reproduction:

1. Open the landing page in a browser context where storage access is denied and reading `window.localStorage` throws a security exception.
2. Module startup evaluates `createStore(localStorage)`.
3. The exception occurs before `createStore` receives a storage object, so `renderLanding` never runs and the landing route is unavailable.

Concrete impact:

A supported defensive path regresses specifically on the new default entry page. Users with blocked storage cannot reach the play or tutorial links even though the application already has a no-storage fallback.

The test at `serve/tests/engine.test.js:2787` does not cover this case. It injects an object whose storage methods throw, which verifies method-level protection inside `createStore`, but not failure while acquiring the global storage object.

Proportional fix:

Import `browserStorage` in `landing-main.js` and construct the store with `createStore(browserStorage())`, matching the established shell path. Add a small entry-point test in which acquisition of `localStorage` itself throws.

Acceptance criteria:

- The landing entry point does not read the global `localStorage` object directly.
- The landing page renders when storage acquisition is denied.
- The existing method-level hostile-storage behavior remains covered.

Correction review:

`landing-main.js` now imports `browserStorage` and constructs its store with `createStore(browserStorage())` before entering the package-loading `try` block. This uses the established safe acquisition path and also avoids misreporting a storage exception as a package failure.

The correction adds a source-level guard covering every entry point and a landing render test using the forgetful storage shape returned by the denied-storage fallback. Together with the existing hostile-method coverage, these tests are proportional to the regression. No new issue was found in the correction.

## Reviewed without findings

- The five-step tutorial sequence, arithmetic progression, skip/back behavior, and final route.
- Landing content, restored-session state, play/tutorial routing, and use of the real box-score renderers.
- The line-score renderer ownership change and its updated callers.
- Development server aliases and history fallback behavior.
- The development-only Docker Compose service and its documented scope.
- The v34 modal-focus correction.

## Disposition

| | |
|---|---|
| v35-P1-01 | Confirmed. **Not acted on** — untracked scratch file, not repository content, operator's call |
| v35-P2-01 | **Closed**, and the misreported-failure half it did not reach is closed with it |

208 browser tests (2 added), 1015 Python tests with the probe excluded, ruff clean, ratchet at zero.

## Deduplication

Neither finding was present in `docs/reviews/todo.md`, `docs/reviews/non-issue.md`, or the closed v34 review material examined for this pass.
