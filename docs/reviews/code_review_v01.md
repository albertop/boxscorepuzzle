# Code Review v01

Date: 2026-08-18

Scope reviewed:
- Project markdown under `CLAUDE.md`, `docs/`, and `discovery/**`.
- `forge/src/**` and `forge/tests/**`.
- Code under `discovery/**`, excluding any `_not_in_use` folder.
- `serve/`, currently only `.gitkeep`.

Backlog note: no `TODO.md` or backlog file was found in the project tree, so no finding could be suppressed as already pending.

No source code was changed. This file is the only artifact updated.

---

## Findings By Priority

### P1 - Discovery loader can drop real no-PA contributors after counting them in shape

Primary hats: Baseball/boxscore expert, QA/reliability engineer, backend architect

Files:
- `discovery/difficulty-metrics/measure.py:177`
- `discovery/difficulty-metrics/measure.py:246`
- `forge/src/boxscore_verify/plausibility.py`

Finding:
The shape query counts a batting row when it contributed anything meaningful, including `B_R`, `B_H`, `B_BB`, `B_SO`, `B_HP`, `B_SF`, `B_SH`, or `B_XI`. The row query then loads only rows with `d.B_PA > 0`. That means a pinch runner or other player with `PA = 0` but a real contribution can be counted in the candidate shape but omitted from the actual `Direction`.

Why this matters:
This contradicts the verifier's own baseball note that "the true invariant is that a row on the board contributed something." It can silently discard valid games after identity checks, bias discovery measurements, and understate the pool. Because many discovery scripts use `load()` as their source of truth, the error propagates into pitcher-cap, difficulty, erasure, hand-solve, and prototype measurements.

Recommended fix:
Use one shared "contributed anything" predicate for both candidate shape and row loading. Add a loader invariant that compares loaded batting totals against the game log for games with zero-PA contributing rows.

---

### P1 - Package format accepts malformed JSON too late and too loosely

Primary hats: Python principal developer, QA/reliability engineer, security engineer

Files:
- `forge/src/boxscore_package/format.py`
- `forge/src/boxscore_verify/verify.py`

Finding:
`Board.from_json()` and `Package.from_json()` convert raw JSON directly into tuples without validating column counts, cell types, row lengths, metadata shape, or that required complete sections are complete before math begins.

Why this matters:
A syntactically valid but semantically malformed package can fail later as an uncontrolled `TypeError` or arithmetic exception instead of a deterministic `PackageError`, `MALFORMED`, or `BAD_DATA` rejection.

Recommended fix:
Add boundary validation in `boxscore_package.format`: exact row widths, integer-or-null cells, complete line score fields, metadata as a JSON object, and controlled errors for malformed structures.

---

### P1 - Signature verification can be accidentally disabled by passing `secret=None`

Primary hat: Security engineer

Files:
- `forge/src/boxscore_verify/verify.py`
- `forge/src/boxscore_package/signing.py`

Finding:
`check_signature()` returns success when `secret is None`.

Attack scenario:
If the future serving/import path misconfigures the signing secret, corrupted or replaced puzzle packages can skip the integrity layer entirely.

Exploitation method:
Provide a modified package to a process running verification without a configured secret.

Business impact:
The pipeline can serve an artifact whose integrity was never checked, weakening the main protection against interrupted upload or tampering.

Recommended fix:
Keep explicit unsigned verification only for test/discovery call sites. Production or publish/import commands should fail closed when the secret is missing.

---

### P2 - Public package terminology does not match forge terminology for CI

Primary hats: Python principal developer, baseball/boxscore expert, logic puzzle expert

Files:
- `forge/src/boxscore_forge/boxscore.py`
- `forge/src/boxscore_forge/identities.py`
- `forge/src/boxscore_package/format.py`
- `discovery/verifier/rejection_rates.py`

Finding:
The internal model calls the fourth footnote term `catcher_interference`, while the package format names the same column `catcher_interference`. The adapter in discovery writes the internal field positionally, so the values move, but the public schema and internal model do not speak the same vocabulary.

Why this matters:
This is fragile at the exact boundary meant to keep forge, verifier, and package separate. Future UI, analytics, or schema users may read the column by name and display or validate the wrong concept.

Recommended fix:
Choose one canonical schema term and document aliases if compatibility is needed. Prefer testing package round-trips by named column semantics, not only by tuple position.

---

### P2 - Several discovery scripts depend on implicit import path state

Primary hats: QA/reliability engineer, backend architect

Files:
- `discovery/sample-boards/render.py:20`
- `discovery/board-prototype/build.py:19`
- `discovery/board-prototype/alternations.py:17`
- `discovery/board-prototype/working_set.py:20`
- `discovery/verifier/rejection_rates.py:33`
- `discovery/pitcher-cap/measure_pitching.py:32`

Finding:
Some scripts patch `sys.path`, while others import `measure` or `compressibility` directly and rely on the caller's working directory or `PYTHONPATH`.

Why this matters:
The README commands can fail or produce environment-dependent behavior. More importantly, discovery results become hard to reproduce because the import graph is not deterministic from the script alone.

Recommended fix:
Centralize discovery bootstrap/import setup, or package discovery helpers as importable modules. At minimum, make every runnable script compute `_ROOT` and insert the same paths consistently.

---

### P2 - Hand-solve pack replacement can violate quotas after adding required traits

Primary hats: QA/reliability engineer, logic puzzle expert

File:
- `discovery/hand-solve/build_pack.py:150`
- `discovery/hand-solve/build_pack.py:172`
- `discovery/hand-solve/build_pack.py:176`

Finding:
`choose()` fills chain quotas, then if a required trait is missing it appends a trait-bearing candidate and removes `chosen.pop(-2)`. That removes an arbitrary earlier board, not one selected to preserve the same target, era quota, certification balance, or uniqueness intent.

Why this matters:
The generated pack can report that it satisfies quotas while silently dropping a required chain rung or changing the uncertified share. Since this pack is a launch gate, the selection constraints should be audited by code, not trusted by print output.

Recommended fix:
When replacing, choose a victim from the same target/certification bucket where possible. After selection, assert `WANTED`, all `QUOTAS`, pre-1950 allowance, one-board-per-game, and intended uncertified range.

---

### P2 - Discovery HTML renderers interpolate data into `innerHTML` without escaping

Primary hats: Frontend engineer, security engineer

Files:
- `discovery/pitcher-cap/render_boards.py:100`
- `discovery/pitcher-cap/render_boards.py:147`
- `discovery/pitcher-cap/render_boards.py:160`
- `discovery/pitcher-cap/render_boards.py:170`
- `discovery/board-prototype/template.html:189`
- `discovery/board-prototype/template.html:191`

Finding:
Prototype/rendering code builds HTML strings from board fields and inserts them with `innerHTML`. Some values come from database-backed labels, names, game ids, or generated notes.

Attack scenario:
A database value or manually supplied note containing HTML can execute script in the local browser when the discovery artifact is opened.

Exploitation method:
Place markup in a source value that reaches `label`, `note`, `pitcherLabels`, or related rendered fields.

Business impact:
This is not production-facing today, but these pages are measurement instruments. A compromised or malformed rendered board can mislead product decisions or execute code in the operator's browser.

Recommended fix:
Use DOM construction with `textContent`, or HTML-escape every interpolated value before inserting into generated HTML.

---

### P3 - Discovery scripts assume non-empty samples in places where a data filter can empty them

Primary hats: QA/reliability engineer, Python principal developer

Files:
- `discovery/sample-boards/render.py:181`
- `discovery/sample-boards/render.py:195`
- `discovery/board-prototype/build.py:113`

Finding:
Several discovery scripts index fixed sample positions like `pool[6]` or `widest[0]` after filters. The current data may make that safe most of the time, but the code does not fail with a useful explanation when a gate, era window, DSN issue, or future data change reduces the sample.

Why this matters:
Discovery scripts are decision tools. When they fail, they should say the sample is too small or too filtered, not crash with an unrelated `IndexError`.

Recommended fix:
Add explicit sample-size checks with messages that include the applied filters and the minimum required count.

---

## Persona Notes

### Persona 1 - Python Principal Developer

The core `forge` code is generally strong: frozen dataclasses, typed public surfaces, clear exception hierarchy, and property tests around solver invariants. The main Python risks are at boundaries and scripts: loose JSON parsing, inconsistent schema vocabulary, path bootstrap drift, and brittle sample assumptions.

### Persona 2 - QA / Reliability Engineer

The highest reliability risk is not the solver; it is the data and measurement layer in `discovery`. The loader predicate mismatch can invalidate downstream measurements. The hand-solve selector also needs post-selection assertions because it is a launch gate.

### Persona 3 - Frontend Engineer

`serve/` has no frontend implementation yet. For discovery prototypes, the main frontend concern is using `innerHTML` with unescaped values in local measurement pages.

### Persona 4 - Security Engineer

No production auth/session/API surface exists yet. Current security findings are integrity/configuration (`secret=None`) and local HTML injection in discovery artifacts. Both are small now and cheap to harden before `serve/` exists.

### Persona 5 - Backend Architect

The forge/package/verifier separation is conceptually sound. The weak spots are implicit contracts: column naming, JSON schema validation, and duplicated SQL predicates. Shared code is intentionally avoided between generator and verifier, but boundary contracts still need explicit validation.

### Persona 6 - Baseball And Boxscore Expert

The `B_PA > 0` row loading predicate is the most important domain issue in this pass. A baseball row can matter with no plate appearance, especially substitutions and pinch runners. Dropping those rows can make the board less faithful to real boxscores.

### Persona 7 - Kakuro / Logic Puzzle Expert

The solver and erasure logic are directionally consistent with the "deduction, no guessing" goal. The risk is in the evidence pipeline: if discovery omits valid row shapes or the hand-solve pack misses quotas, the measured difficulty curve may be trusted for the wrong population.

---

## Short Priority List

1. Fix the discovery loader row predicate so shape and loaded rows use the same contributed-anything definition.
2. Add strict package JSON validation and fail-closed signature configuration for publish/import paths.
3. Normalize CI footnote terminology across package and forge boundaries.
4. Make discovery scripts reproducible without hidden `PYTHONPATH` state.
5. Add post-selection assertions to the hand-solve pack generator.
6. Escape or DOM-render discovery HTML output.
