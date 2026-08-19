# Code Review v18

Date: 2026-08-19

## Contract applied

This review uses the operating model stated by the operator and recorded in the project documentation:

- One developer, one laptop, and manually controlled forge runs.
- No concurrent developers, unattended scheduler, CI execution, or adversary inside the repository.
- `forge/` is the local generator, `discovery/` contains decision-making research instruments, and `serve/` has no application implementation yet.
- `_not_in_use` is excluded.
- Findings already pending in `docs/reviews/todo.md` are excluded.
- The three declined v17 observations are not revived under new names.

This was a static review. No tests, linters, type checks, or Git commands were run. No source code was changed.

## Findings by persona

### Persona 2: QA / Reliability Engineer

#### v18-P2-01: The output preflight still does not exercise replacement of the real destination

**Supporting perspective:** Persona 1, Python Principal Developer

**Location:** `discovery/footnote-groups/measure.py`, `_refuse_unwritable()`; `forge/tests/test_group_metrics.py`, `test_the_probe_replaces_an_existing_file_rather_than_only_creating_one()`

`_refuse_unwritable()` creates two new sibling files and replaces one sibling with the other. It then checks `os.access(out, os.W_OK)` when the real output already exists. Those checks answer whether the directory permits a replace and whether the destination is writable; they do not answer whether Windows will allow `pending.replace(out)` against that specific destination.

This is reachable in the documented one-operator environment. The operator can leave `results.txt` open in a viewer or editor whose Windows sharing mode permits reading or writing but denies deletion/replacement. `os.access(out, os.W_OK)` can still return true, the sibling replace succeeds, and the multi-hour measurement starts. Publication then fails at the only operation the preflight did not perform: replacing `out` itself.

The new test does not guard the distinction it names. It records that `Path.replace()` was called, but evaluates `target.exists()` only after `_refuse_unwritable()` has removed the probe files in `finally`. Therefore this condition is automatically true:

```python
assert target.exists() is False or target.name != "results.txt"
```

Deleting `target.write_bytes(b"")` from production would reduce the probe to a rename onto an absent path, and the test would still pass. The test proves a replace call occurred, not that its target existed when the call occurred.

**Impact:** A normal operator action can waste the complete measurement run and leave no new artifact. The old artifact remains safe, so this is P2 operational loss rather than corruption or a false scientific result.

**Recommended fix:** Exercise the exact destination without creating a disappearance window. If `out` exists, read its bytes, write those same bytes to a unique sibling, and atomically replace `out` with that byte-for-byte copy. A failure caused by a read-only attribute, target ACL, or non-delete-sharing open handle is then discovered before `load()`. A crash before the replace leaves the old file untouched; a successful replace leaves identical content at the canonical path. The separate sibling probe remains sufficient when `out` does not exist.

Strengthen the regression test in two directions:

- Record `Path(target).exists()` inside the monkeypatched `Path.replace()` before delegating, and require it to be true.
- Make replacement fail only when `target == out`; assert that `_refuse_unwritable()` refuses before the loader and that the previous artifact's bytes remain unchanged.

## Personas with no additional findings

### Persona 1: Python Principal Developer

The changed implementation is readable, typed consistently with its local discovery scope, and avoids the former Git path parser. The only actionable issue is already reported once as `v18-P2-01`.

### Persona 3: Frontend Engineer

There is no frontend application in `serve/` yet. Product-level component, state, accessibility, rendering, and loading-state findings would be requirements speculation rather than review of implemented code.

### Persona 4: Security Engineer

No new reachable OWASP-style issue was found in the changed local research surface. Deliberate digest collision, compromised build-step, multi-tenant, authentication, session, and API-abuse scenarios do not apply to the current single-operator forge environment. Consequently there is no security finding requiring an attack scenario.

### Persona 5: Backend Architect

No new service-boundary, database, transaction, idempotency, or scaling defect was found. The output-preflight contract mismatch is already reported under QA rather than duplicated here.

### Persona 6: Baseball and Boxscore Expert

The delta does not change boxscore loading, lineup grouping, footnote attribution, innings-as-outs conversion, cross-team identities, or source traceability. No new baseball-domain defect was found.

### Persona 7: Kakuro and Logic-Puzzle Expert

The delta does not change completion counting, derivability, erasure, solving, hint behavior, uniqueness, or difficulty semantics. Existing open decisions about human derivability and the hand-solve remain backlog/design items and are not repeated.

### Persona 8: User Experience and Graphic Design Expert

No visual or interaction implementation changed. Avoiding a wasted multi-hour authoring run matters to the operator experience, but that impact belongs to `v18-P2-01` and is not a second finding.

## Backlog items intentionally not repeated

- `v05-P1-02`, the erased footnote attribution drawing.
- The documented re-measurement and hand-solve work invalidated by the former phantom batting rows.
- The known residual repository-snapshot windows accepted for the single-laptop environment.
- Ruff coverage/debt for discovery scripts.
- Product decisions and future `serve/` requirements already listed in the design document or `todo.md`.

## Summary

One actionable finding: `v18-P2-01`. It is reachable with one operator, can waste a real long-running measurement, and has a focused repair. No P1, frontend, security, baseball, logic-puzzle, or visual-design findings were identified in the current delta.
