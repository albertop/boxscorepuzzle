# Code Review v17

Date: 2026-08-19

## Scope and method

This is a static incremental review of the files changed after v16:

- `docs/reviews/todo.md`
- `discovery/footnote-groups/measure.py`
- `forge/src/boxscore_package/format.py`
- `forge/tests/test_group_metrics.py`
- `forge/tests/verify/test_boundary.py`

Generated caches were excluded, as was `_not_in_use`. No tests, linters, type checks, or Git commands were run. Existing pending work in `docs/reviews/todo.md` is not repeated.

## Reassessment against the documented operating environment

**Actionable findings: none.**

The first version of this review applied a generic multi-developer and adversarial operating model. That is not this project's contract: the forge runs locally on one laptop, under one operator, with no CI, unattended scheduler, concurrent editor, untrusted contributor, or adversary inside the repository. Under the explicit test in `docs/reviews/todo.md`, an observation that requires a second uncontrolled process or actor is declined rather than converted into engineering work.

The three observations below are retained for traceability but withdrawn as current findings:

- `v17-P1-01` requires two instrument runs to overlap at one precise filesystem interval.
- `v17-P2-01` requires deliberate collision generation by an adversary or compromised build step.
- `v17-P2-02` concerns Git-quoted tracked filenames that are not part of this repository's naming surface.

They would be reconsidered only if the environment gains CI, unattended scheduling, another developer, untrusted repository input, or a requirement to support arbitrary tracked filenames.

## Declined observations, not current findings

### Declined v17-P1-01: The replaceability preflight can overwrite another run's newly published result

**Personas:** QA/Reliability Engineer, Backend Architect, Python Principal Engineer, UX/Graphic Design Reviewer

**Location:** `discovery/footnote-groups/measure.py`, `_refuse_unwritable()`, `_prove_replaceable()`, and `publish()`

`_prove_replaceable()` tests an existing destination by moving the canonical artifact to a private `aside` path and restoring it in `finally`. That makes the check destructive and creates a lost-update race with the concurrent runs that `publish()` explicitly supports through unique staging names.

A concrete interleaving loses a completed result:

1. Run A moves the previous `results.txt` to `results.txt.replaceable-A` during preflight.
2. Run B completes and atomically publishes its new result to the now-vacant `results.txt`.
3. Run A enters `finally` and calls `aside.replace(out)`, silently replacing B's new result with the old artifact.
4. Run A then starts its hours-long measurement. If it fails or is stopped, B's valid completed result is permanently absent from the canonical path.

The same design leaves the canonical path missing if the process is terminated in the small interval between the two renames because `finally` does not run after process kill, interpreter crash, or power loss. The normal-path restoration test cannot exercise either failure mode.

This is more severe than the v16 late-write failure it repairs: a preflight intended to preserve operational safety can now destroy a result that another process successfully committed.

**Recommended fix:** Never move the canonical artifact merely to test it. Establish a single-writer lease or OS-level lock before preflight and hold it through the entire measurement and publication, or publish immutable run-specific artifacts and update a small canonical pointer with compare-and-swap/generation semantics. If concurrent runs remain supported, restoration must never replace a destination that appeared after the preflight began. Add a deterministic interleaving test that writes a new `out` after `out.replace(aside)` and proves the cleanup does not overwrite it.

### Declined v17-P2-01: Published provenance identifiers remain collision-feasible

**Personas:** Security Engineer, Python Principal Engineer, Backend Architect

**Location:** `discovery/footnote-groups/measure.py`, `_describe()`, `source_hashes()`, `_board_digest()`, and `RunIdentity.with_inputs()`

The v16 structural collision is fixed correctly with length-prefixed records, but the displayed tracked/untracked digest is only 16 hexadecimal characters, or 64 bits. The instrument hash, each board hash, and the aggregate input hash remain 12 hexadecimal characters, or 48 bits. A 64-bit hash needs about `2^32` evaluations for a birthday collision between two attacker-controlled candidates; a 48-bit hash needs about `2^24`. Those are not security-strength collision bounds.

The new test checks only that the tree digest is longer than the old eight characters and therefore locks in 64 bits without testing the actual requirement: resistance to substituting one inspected input for another.

**Attack scenario:** A contributor or compromised build step can prepare both the benign checkout presented for review and a second checkout containing an untracked shadow module or altered measurement input.

**Exploitation method:** Generate two families of otherwise equivalent trees by varying nonce/comment bytes in disposable untracked files, one family benign and one malicious, and search offline for a cross-family collision in the 64-bit displayed digest. The revision, tracked diff, and instrument fields stay the same, so swapping the colliding untracked tree preserves the complete published repository identity. The 48-bit board/input fields offer an even smaller collision space when data candidates are attacker-controlled.

**Business impact:** An artifact can display the same provenance as an approved run while executing a shadowed dependency or measuring different board contents. That invalidates auditability and can drive book composition or puzzle-policy decisions from results that cannot be distinguished by their recorded identity.

**Recommended fix:** Use full SHA-256 values in the artifact, or at minimum 128 collision-resistant bits, consistently for tracked changes, untracked files, instrument sources, individual boards, and the aggregate sample. The human cost of another 16 to 48 hexadecimal characters is negligible compared with the cost of an unauditable multi-hour result. Tests should assert the agreed security width for every provenance field rather than merely asserting that one field grew.

### Declined v17-P2-02: `_diff_paths()` rejects valid diffs whose paths Git quotes

**Personas:** Python Principal Engineer, QA/Reliability Engineer, Backend Architect

**Location:** `discovery/footnote-groups/measure.py`, `_diff_paths()` and `identify()`

`_diff_paths()` recognizes only lines beginning exactly with `diff --git a/`. Git quotes and escapes diff header paths containing tabs, newlines, quotes, backslashes, and, under the usual `core.quotePath` behavior, some non-ASCII bytes. Those headers begin with a quoted `"a/...` token and do not match the hard-coded prefix.

If the only tracked edit has such a path, `_diff_paths()` returns an empty list while the diff bytes are non-empty. `_describe()` then returns `unknown`, and the run refuses to start even though Git produced a complete, valid diff. If ordinary and quoted paths are both changed, the full diff still enters the hash, but the displayed file count silently under-reports the tracked changes.

The tests cover simple ASCII headers and NUL-safe porcelain parsing for an untracked tabbed name, but they do not pass the equivalent quoted tracked header through `_diff_paths()` or `identify()`.

**Recommended fix:** Do not reconstruct Git's path grammar from the human patch header. For identity, a non-empty binary diff can be hashed directly without parsing paths. If the file count is required, request machine-readable raw/name records with `-z` from the same Git invocation as the patch snapshot and parse that documented format, or use a parser that implements Git's quoting rules. Add cases for a tab, quote, backslash, non-ASCII byte sequence, rename, and a path containing the literal separator text ` b/`.

## Relationship to v16

- `v16-P1-01` is closed for tracked files as documented: tracked paths now come from the diff snapshot itself. `v17-P2-02` concerns the new parser's inability to consume all valid diff headers, not the former two-command race.
- `v16-P2-01` is closed with respect to delimiter-free structural aliases. `v17-P2-01` concerns the remaining cryptographic truncation after canonical framing was added.
- `v16-P2-02` now tests target-specific rename rights. `v17-P1-01` is a new data-loss race introduced by moving the canonical target during that test.
- `v16-P2-03` is closed: direct construction and JSON parsing now share `_check_schema()`, including rejection of `2.0`, strings, and booleans.
- The tuple-only direct-construction contract for `slot_references`, with list-to-tuple conversion only at the JSON boundary, remains coherent.

## Eight-persona coverage

- **Python Principal Engineer:** Found the destructive preflight race, incomplete digest widths, and fragile Git header parser.
- **QA/Reliability Engineer:** Found missing concurrent-publication and quoted-path cases; normal `finally` coverage does not model hard termination.
- **Frontend Engineer:** No frontend files changed in this delta; no new frontend finding.
- **Security Engineer:** Found collision-feasible provenance identifiers and documented attack scenario, exploitation method, business impact, and repair.
- **Backend Architect:** Found that preflight and publication lack one ownership/locking contract and that provenance parsing depends on presentation-format output.
- **Baseball/Boxscore Specialist:** Reviewed the board/input identity changes and slot-reference boundary repair; no new baseball-rule defect was introduced.
- **Kakuro/Logic-Puzzle Specialist:** No solver, deduction, erasure, or metric semantics changed; no new logic-puzzle finding.
- **UX/Graphic Design Reviewer:** No visual surface changed. Loss or disappearance of the canonical authoring result is captured once in `v17-P1-01` rather than duplicated.

## Intentionally not repeated

- `v05-P1-02`, the erased footnote attribution drawing still tracked in `docs/reviews/todo.md`.
- The explicitly recorded millisecond residual between imported Python code and repository observation under `v16-P1-01`; closing it requires the launcher/snapshot architecture already described in the backlog.
- The known Ruff coverage/debt for the discovery tree.
- Closed findings from earlier reviews unless a changed repair introduced a distinct defect identified above.

## Action

No implementation change is recommended for v17. The observations remain documented only as triggers to reassess if the operating environment changes.
