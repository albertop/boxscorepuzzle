# Code Review v16

Date: 2026-08-19

## Scope and method

This is a static delta review of the files changed after v15:

- `discovery/footnote-groups/measure.py`
- `forge/src/boxscore_package/format.py`
- `forge/tests/test_group_metrics.py`
- `forge/tests/verify/test_boundary.py`

The review used the same eight perspectives as the earlier rounds. Tests, linters, type checking, and Git commands were not run. `_not_in_use` was excluded. Items already pending in `docs/reviews/todo.md` are not repeated.

## Findings

### v16-P1-01: Repository provenance can identify bytes that were never executed

**Personas:** Python Principal Engineer, QA/Reliability Engineer, Backend Architect

**Location:** `discovery/footnote-groups/measure.py`, `identify()`, `_describe()`, `source_hashes()`, and `main()`

`identify()` still does not capture one coherent repository state. Python imports the instrument and its dependencies before `main()` calls `identify()`, after which status, the binary diff, untracked-file bytes, and source hashes are collected in separate operations. The new `_describe()` guard correctly refuses the specific `no paths + non-empty diff` contradiction from v15, but it accepts every `paths + non-empty diff` pair without proving that the paths and diff came from the same state.

A concrete sequence is enough to produce a false stamp:

1. Version A of a dirty source file is imported and becomes the code the process will execute.
2. `git status` observes the path while it contains A.
3. The file changes to version B before `git diff` and `source_hashes()` read it.
4. The run executes A, while the publishable identity records hashes derived from B.

The publication gate cannot detect this because it checks the original frozen `RunIdentity` again rather than comparing it with a fresh observation. The result can therefore claim reproducible provenance for a source state that did not produce the measurement. That undermines the principal purpose of this long-running research artifact and can make two runs appear comparable when they are not.

**Recommended fix:** Make identity capture and execution share an immutable source snapshot. The strongest design is a small launcher that captures a canonical manifest, starts the worker from a clean worktree/archive matching that manifest, and publishes only from that worker. A smaller repair is to collect the complete identity twice, require byte-for-byte equality before starting, capture the exact source bytes used by the worker, and compare the repository/source manifest again before publication. Add a test whose mocked observations change from A to B between status and diff/hash collection and assert that the run refuses to start or publish.

### v16-P2-01: Different untracked trees can receive exactly the same identity

**Personas:** Security Engineer, Python Principal Engineer, QA/Reliability Engineer

**Location:** `discovery/footnote-groups/measure.py`, `_bytes_of()` and `_describe()`

The untracked-tree preimage is built by concatenating path bytes and file bytes without lengths, separators, record types, or per-file hashes. `_describe()` then prepends another delimiter-free concatenation of the same paths. This encoding is not injective even before SHA-256 is applied. For example, a one-file tree containing path `aa` with bytes `X` and a one-file tree containing path `a` with bytes `aaX` both feed `aaaaX` to the hash. Both also report `1 files`. The final digest is then shortened to eight hexadecimal characters, leaving only 32 bits.

**Attack scenario:** A contributor or compromised local build step wants an altered untracked tree to retain the provenance label previously approved for a different tree.

**Exploitation method:** The actor can prepare two path/content layouts with the same delimiter-free preimage, as above, or vary disposable file contents to search the 32-bit displayed digest space. The tree can then be exchanged while the artifact continues to display the same untracked identity.

**Business impact:** Reviewers can accept puzzle measurements or publication decisions as originating from an inspected working tree when a different untracked tree was present. This defeats auditability and can conceal a shadow module or data-dependent alteration.

**Recommended fix:** Serialize an explicit canonical sequence such as `(path_length, path_bytes, kind, content_length, content_bytes)` or canonical JSON/CBOR records. Prefer one full SHA-256 per file plus a canonical aggregate, include symlink targets and file kinds deliberately, and retain at least 128 bits in the artifact. Add a regression test using the two trees above and require different identities.

### v16-P2-02: The output probe does not test replacement of the actual destination

**Personas:** QA/Reliability Engineer, Backend Architect, UX/Graphic Design Reviewer

**Location:** `discovery/footnote-groups/measure.py`, `_refuse_unwritable()`

The new preflight creates a fresh sibling file and renames that fresh file to another fresh sibling. This proves that the parent directory permits creation and a sibling rename, but it does not prove that `pending.replace(out)` can replace an existing `out`. On Windows, an existing destination may be read-only, held open without delete sharing, or protected by a target-specific ACL while the sibling probe succeeds. The expensive run then proceeds and fails only in `publish()`, which is the late operational failure the preflight is intended to prevent.

The tests cover a destination directory, a missing parent, a failed probe write, and sibling placement, but not an existing file that permits sibling creation while refusing replacement.

**Recommended fix:** Model the real publication contract rather than generic parent writability. Prefer publishing each run to a unique immutable final artifact and updating a canonical pointer separately. If replacement of a canonical file is required, add a platform-aware preflight for the existing target's replace/delete rights and lock state, and still handle a later race as a first-class publication failure. Add a Windows regression test using an existing read-only or non-delete-share target and assert refusal before `load()`.

### v16-P2-03: Direct construction accepts `schema=2.0` and writes a package its parser rejects

**Personas:** Python Principal Engineer, QA/Reliability Engineer, Backend Architect

**Location:** `forge/src/boxscore_package/format.py`, `Package.__post_init__()` and `Package.written_as`

The constructor checks only `self.schema not in READABLE`. Python considers `2.0 == 2`, so `schema=2.0` passes membership in `(2,)`. `written_as` then returns the float and `as_json()` emits `"schema": 2.0`. `Package.from_json()` correctly requires an actual `int` and rejects that document. The public type can therefore still construct and serialize a package outside the language its own parser accepts, despite the invariant enforced for slot references.

Static typing reduces accidental calls but is not a runtime boundary, and this module explicitly validates direct construction because internal producers and migrations can supply unchecked values.

**Recommended fix:** When `schema` is explicit, apply the same exact runtime predicate used by `from_json()`: require `isinstance(schema, int)`, reject `bool`, and then check membership in `READABLE`. Better still, centralize schema validation in one helper called by both paths. Add constructor-to-JSON-to-parser tests for `2.0`, `"2"`, `True`, and the valid integer `2`.

## Relationship to v15

- The exact v15 clean-tree contradiction is now refused. `v16-P1-01` is the remaining mixed-snapshot problem when both path and diff observations are non-empty, not a restatement of the closed case.
- The v15 parent-only output check now performs a real sibling write and rename. `v16-P2-02` concerns the still-untested, target-specific replacement operation.
- The `slot_references` runtime/type mismatch is closed: direct construction now requires the annotated tuple, while the JSON boundary converts its list to a tuple.

## Eight-persona coverage

- **Python Principal Engineer:** Found the incoherent source snapshot, non-canonical digest encoding, and numeric-equality schema hole.
- **QA/Reliability Engineer:** Found missing adversarial coverage for mixed repository observations, exact destination replacement, hash encoding, and non-integer direct schemas.
- **Frontend Engineer:** No frontend files changed in this delta; no new frontend finding.
- **Security Engineer:** Found the untracked-tree identity collision and documented its attack path, exploitation method, impact, and repair.
- **Backend Architect:** Found boundary asymmetry in schema construction and the mismatch between the preflight and publication contracts.
- **Baseball/Boxscore Specialist:** Reviewed the tuple-only slot-reference repair; it preserves row-reference syntax and introduces no new baseball-domain defect.
- **Kakuro/Logic-Puzzle Specialist:** No solver, erasure, or deduction semantics changed in this delta; no new logic-puzzle finding.
- **UX/Graphic Design Reviewer:** No visual surface changed. The authoring-workflow impact of a late publication failure is covered by `v16-P2-02` rather than duplicated.

## Intentionally not repeated

- The pending erased-footnote attribution drawing item already tracked as `v05-P1-02`.
- The known Ruff coverage/debt for the discovery tree already documented in `docs/reviews/todo.md`.
- Closed findings from earlier review rounds unless the changed implementation introduced a distinct residual defect described above.

## Suggested order

1. Make the executed source and recorded source one immutable snapshot (`v16-P1-01`).
2. Restore constructor/parser symmetry for the schema (`v16-P2-03`).
3. Make output preflight exercise the actual publication contract (`v16-P2-02`).
4. Replace the untracked-tree encoding and short digest (`v16-P2-01`).
