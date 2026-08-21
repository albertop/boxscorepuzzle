# Code Review v36

Date: 2026-08-21

## Result

Full-tree review under `code_review_contract.md`: `forge/` (source, scripts, tests), `serve/`
(engine, phone UI, tests, data handling), `discovery/` and `tools/` (highest priority per the
contract), and the infrastructure files (`compose.yaml`, `.github/workflows/ci.yml`,
`.githooks/pre-push`, `.gitignore`, `.gitattributes`).

**Second pass, same day:** the operator expanded the contract
(`full_code_review_contract.md`) with two hats — SEO / Search Discoverability (Hat 10) and
Data & Data Pipeline Quality (Hat 11). Hat 10 ran to completion. **Hat 11 was stopped by the
operator before completing**; its one finding verified before the stop is recorded
(v36-P2-20), and the rest of that hat's scope — the loader's joins and row mapping end to end,
the shipped packages against the format document, the committed discovery artifacts checked
for staleness — is explicitly **not covered** by this review.

`docs/python-conventions.md` exists and was treated as the authoritative Python guideline.
All `.md` files bearing on scope were read, including `todo.md`'s open items, `non-issue.md`,
and `open-decisions.md`, for deduplication.

**1 × P1, 20 × P2, 49 × P3. No P0.** The forge's mathematical core is clean: identities are
baseball-correct on both sides including the walkoff and ghost-runner cases, the verifier imports
no generator code, puzzle IDs are idempotent, interval arithmetic is sound in both
implementations, erasure is deterministic per seed, and `mypy --strict` and `ruff check` pass over
`forge/src`. The findings cluster elsewhere: **checks that cannot fire** (the discovery lint
ratchet fails open when ruff itself is broken; the pre-push hook gates on the wrong thing and is
not enabled; a boundary test that never calls the implementation; launch-promises printed rather
than asserted) and **two copies of one rule disagreeing** (three renderers of innings pitched
asserting two different notations; a client test encoding a false baseball rule the certifier
explicitly allows for; construction and parsing applying different rules to the same fields).
That is the project's own recorded failure shape, found again in new places — including twice
inside instruments built to prevent it.

Method: static review by six parallel area reviewers, each finding then verified by reading the
cited code (and for the highest severities, re-verified independently: the ratchet's fail-open
branch, the hook's branch gate, the missing leak check, the walkoff test, the shape-only solution
check, and the vacuous cap boundary test were all confirmed by direct read; the dead import in
`discovery/batting-order/measure.py` and the `narrow()` non-termination were confirmed by
execution against a scratchpad harness, outside the repository). No repository file was modified,
created, or deleted. The test suite was not run.

---

## Hat 1 — Python Principal Developer

### v36-P2-01: `narrow()` can loop forever on a contradictory system instead of raising

Severity: P2

Location: [bounds.py:67](../../forge/src/boxscore_forge/bounds.py), lines 67 (`Bounds(0, None)`
initial domains) and 72–74 (`while _tighten_once(...): pass`).

Description: The fixed-point loop terminates on consistent input, but on an inconsistent system
whose contradictory cycle lives among cells with `high=None`, lower bounds climb by a positive
constant per pass forever. `Bounds.is_empty` requires `high is not None`, so the empty-range check
never fires. Reproduced through the public `system` parameter (the way `solver._bounding_moves`
calls it) with the pair `a − b = 1`, `b − a = 1` over real cell names on a real `BoardShape`: the
call never returns. The verifier's twin (`reason.py`) is immune because it seeds every unknown
with `(0, CELL_CAP)` — the two independent solvers disagree about termination on bad data.

Impact: `solve()` is reached by `erase()` on directions loaded from the database *before* any
layer-1 validation. The comment at `erasure.py:258–261` promises a broken boxscore "fails loud"
via `ContradictionError`; in this shape it hangs the batch with no error — worse than the promised
crash. Reaching it from a full real board additionally requires the contradiction to be isolated
from the always-given anchors, hence P2 rather than P1.

Reproduction: feed `narrow()` two relations forming `a = b + 1`, `b = a + 1` with both cells
unknown; the loop never exits.

Suggested fix: bound the loop — either a pass count derived from the cell count, or seed a
generous finite cap the way the verifier does — and raise `ContradictionError` on exhaustion.
Converts a hang into the loud failure the module already promises.

### v36-P2-02: `Package` construction and parsing apply different rules to the same fields

Severity: P2

Location: [format.py](../../forge/src/boxscore_package/format.py) — `PUZZLE_ID` and `SIGNATURE`
patterns applied only in `from_json` (lines 1024, 1043); no constructor check; row *widths*
(6 batting / 4 footnote / 6 pitching cells) enforced only in the parse path's `_cells`, not in
`check_profile` or `__post_init__`.

Description: The suite's own stated invariant — `TestAPackageCannotContradictItself` in
`forge/tests/verify/test_boundary.py`, "the shared type must be unable to produce output outside
the language its own parser accepts" — is enforced for `slot_references` and `schema` but not for
`puzzle_id`, `signature`, or row widths. The constructor builds packages whose `as_json()` output
`from_json()` refuses. Three verify fixtures depend on the hole today:
`verify/test_properties.py:151` (`puzzle_id="property"`),
`verify/test_plausibility.py:50` (`puzzle_id="plausibility"`),
`verify/test_schema_document.py:66` (`signature="deadbeef"`, 8 hex where the parser requires 128).

Impact: a producer or migration constructing packages in memory — the path the forge signs — can
emit unreadable documents with no `PackageError`. This is the exact write/read asymmetry the file
documents fixing three separate times (slot references, schema, blank profile), open on three more
fields.

Reproduction: `Package.from_json(a_package(board).as_json())` in `test_schema_document.py` would
raise `PackageError` today; no test performs that round-trip, so nothing is red.

Suggested fix: validate `puzzle_id` and `signature` in the constructor (same precedent as slot
references) and extend `check_profile` to assert row lengths against the column tuples; repair the
three fixtures to contract-shaped values; parametrize
`TestConstructionAndParsingApplyTheSameRule` over these fields so the closure is guarded rather
than remembered.

### v36-P2-03: `discovery/batting-order/measure.py` cannot run — it imports a constant renamed by the postseason refactor

Severity: P2

Location: [measure.py:48-57](../../discovery/batting-order/measure.py), importing
`ACCEPTED_LITERAL` from `discovery/difficulty-metrics/measure.py`, which now defines
`PROVENANCE_LITERAL` / `PROVENANCE_SOURCES` / `ACCEPTED_SOURCES` instead.

Description: verified by executing the import — `'ACCEPTED_LITERAL' in dir(measure)` is `False`;
the script dies with `ImportError` before printing anything. No other file references the old
name.

Impact: this is the instrument that measured the batting-order hypothesis over the whole pool and
from which the pool rule was decided ("THE POOL RULE IS DECIDED FROM THIS ONE"). The project's own
rule: a discovery result that cannot be re-run identically is not evidence. The guard at lines
82–86 that exists to catch "the provenance rule moved" never fires because the import fails first.
Note that after fixing the import, the guard's anchor must be built from `PROVENANCE_LITERAL`
(what `eligibility()` actually interpolates), not from the accepted list.

Reproduction: `cd forge && python ../discovery/batting-order/measure.py` →
`ImportError: cannot import name 'ACCEPTED_LITERAL' from 'measure'`.

Suggested fix: import `PROVENANCE_LITERAL` and build the `original` anchor from it, with a comment
recording the rename.

### v36-P3-01: `ruff format` is mandated, runs nowhere, and the drift it would catch is on `main`

Severity: P3

Location: [certify.py:295-297](../../forge/src/boxscore_verify/certify.py) (one blank line where
the formatter wants two — `ruff format --check src/ scripts/` reports "1 file would be
reformatted"); `.github/workflows/ci.yml` and `.githooks/pre-push` run only `ruff check`.

Description: `docs/python-conventions.md` lines 53–54 mandate "Formatting via `ruff format`… Run
it in the pre-push hook and in CI." Neither invokes it — a documented check that does not exist,
one paragraph from the section rewritten for exactly that reason.

Suggested fix: run `ruff format` once, then add `uv run ruff format --check src scripts tests` to
both CI and the hook.

### v36-P3-02: `tools/fetch_fonts.py` depends entirely on the caller's working directory

Severity: P3

Location: [fetch_fonts.py:21-22](../../tools/fetch_fonts.py) (`OUT = pathlib.Path("serve/ui/fonts")`
with `mkdir` at import time), 46, 49, 112 — every path CWD-relative.

Description: run from anywhere but the repo root it either crashes after creating a stray
`serve/ui/fonts` tree wherever the caller stands, or — quieter — `rglob` over a nonexistent
`serve/data/puzzles` yields nothing and the font subset silently loses every package-carried
glyph, the one-glyph-in-the-fallback-face failure the file's own docstring warns about. All three
sibling tools compute `ROOT` from `__file__`; this one does not.

Suggested fix: `ROOT = Path(__file__).resolve().parents[1]`, anchor all five paths, move the
`mkdir` into `main()`.

### v36-P3-03: two board-writing discovery scripts default their artifacts to the caller's working directory

Severity: P3

Location: [build.py:141-143](../../discovery/board-prototype/build.py) (`out = Path(sys.argv[1] if
len(sys.argv) > 1 else ".")`); [render.py:243](../../discovery/sample-boards/render.py) (same
pattern; writes `sample-boards.txt` / `solve-this-one.txt` into whatever directory the operator
happened to be in — and this one produced the operator's hand-solve artifacts).

Description: violates the recorded rule "Reproducible from the script alone. No reliance on the
caller's working directory." Both use `bootstrap()` for imports and then undercut it for
artifacts.

Suggested fix: default `out` to `Path(__file__).resolve().parent`, keep `argv[1]` as override.

### v36-P3-04: `discovery/render_step.py` states a contract it does not implement, and carries dead code

Severity: P3

Location: [render_step.py:12-31](../../discovery/render_step.py).

Description: the docstring promises "Failures here must not kill a run" but nothing catches
anything — in `pool-at-4-pitchers/remeasure.py` a render failure after the trajectories are
computed in memory discards the compute, the recorded three-hours-lost shape. `_ROOT` at line 12
is computed and never used; the real root is re-derived from `out_path.resolve().parents[2]`,
silently assuming every output lives exactly two levels under the repo root. The module is also
untyped, alone among the tree's shared helpers.

Suggested fix: implement the contract (wrap, print, return 0) or delete the sentence; delete
`_ROOT`; derive the import root from `__file__`.

### v36-P3-05: mutable `dict` fields inside frozen result containers

Severity: P3

Location: [solver.py:169](../../forge/src/boxscore_forge/solver.py) (`Solution.values`),
[erasure.py:49](../../forge/src/boxscore_forge/erasure.py) (`Puzzle.given`),
[reason.py:54](../../forge/src/boxscore_verify/reason.py) (`Derivation.values`);
`Package.metadata: dict` travels mutably inside a signed object.

Description: `frozen=True` freezes the binding, not the value — a caller mutating `puzzle.given`
alters a "frozen" result difficulty metadata was already computed from. The conventions default to
frozen precisely against action-at-a-distance; `format.py:1097–1103` refuses a `list` for exactly
this reason one field over. No in-scope caller mutates them today.

Suggested fix: return `Mapping` views or freeze into immutable structures where practical, at
minimum `Puzzle.given`, which outlives the solve.

### v36-P3-06: dead second docstring on `slot_references`; `Relation.family` assigned but never read

Severity: P3

Location: [format.py:882-888](../../forge/src/boxscore_package/format.py) — two consecutive string
literals; only the first documents the field, and the second is stale ("absent in version 1
packages" — schema 1 is gone). [rules.py:270, 286, 354, 363](../../forge/src/boxscore_verify/rules.py)
— `.family` is never read anywhere in `forge/src` (grep-verified), and its assignments disagree
with the forge's axis (batting order tagged `ROW_IDENTITY` where the forge keeps `BATTING_ORDER`
outside the four families; `ER ≤ R` tagged `COLUMN_SUM`).

Description: a classification nothing consumes is a check that can never fire; if a consumer ever
appears, the taxonomy disagreement activates silently. See also v36-P2-12.

Suggested fix: merge/delete the second string; either drop `Relation.family` or align it with the
forge's taxonomy and add the agreement test.

### v36-P3-07: `difficulty-metrics/measure.py` — string-concatenated path, and a samplable nondeterminism in `ORDER BY CHECKSUM`

Severity: P3

Location: [measure.py:30](../../discovery/difficulty-metrics/measure.py)
(`sys.path.insert(0, str(__file__).rsplit("discovery", 1)[0] + "forge/src")` — string
concatenation against the pathlib convention, in the single most-imported file in the tree) and
line 729 (`ORDER BY ABS(CHECKSUM(g.GAME_ID, o.TEAM_ID))` with `TOP (?)` — CHECKSUM is 32-bit, so
ties are possible and SQL Server's ordering among ties is nondeterministic; a `TOP n` sample could
in principle differ between runs on identical data).

Suggested fix: `Path(__file__).resolve().parents[2] / "forge" / "src"`; append
`, g.GAME_ID, o.TEAM_ID` as a deterministic tiebreaker.

### v36-P3-08: `refs()`, the key pair, and a board-replacement helper are copy-pasted across seven verify test files

Severity: P3

Location: identical `refs()` in `verify/test_layers.py:30`, `test_boundary.py:29`,
`test_weak_solver.py:23`, `test_properties.py:34`, `test_plausibility.py:30`,
`test_certification.py:34`, `test_package_and_limits.py:36`; the `_KEY/SECRET/PUBLIC` block in
four of them; `test_layers.py:58` defines `replacing()`, a duplicate of the `replace` fixture
already in `verify/conftest.py:82`.

Description: conventions put shared fixtures in `conftest.py`; more to the point, `refs()`'s own
docstring records that a previous version of this helper carried a defect (an invented tenth
slot) — with seven copies the next such fix must land seven times.

Suggested fix: move `refs()` and a package factory into `verify/conftest.py` as fixtures; delete
`replacing()` in favor of the existing fixture.

---

## Hat 2 — QA / Reliability Engineer

### v36-P1-01: the discovery lint ratchet passes with exit 0 when ruff is missing or broken — and `--update` in that state would wipe the baseline

Severity: P1

Location: [lint_discovery.py:57-78](../../tools/lint_discovery.py) and 86–89.

Description: `python -m ruff` when ruff is not importable exits with code **1** — the same code
ruff uses for "findings found" — with empty stdout and the error on stderr. The
`returncode not in (0, 1)` guard at line 66 therefore does not fire, and
`json.loads(findings.stdout or "[]")` at line 78 converts the empty output into **zero
findings**. Zero beats every baseline count, so `main()` prints "These rules improved" and returns
0. Worse: `--update` (line 86, which runs before the baseline-exists check) in that state writes
an all-zero baseline, silently destroying the ratchet's reference point. The docstring at lines
91–95 explicitly guards the *baseline-missing* fail-open case — this is the same hole one step
earlier, unguarded.

Impact: this is the only mechanism keeping the ~199 recorded findings from growing, in CI and in
the pre-push hook. A venv rebuild, ruff dropped from the dev group, or a broken interpreter
resolution turns the ratchet into a permanent green light — "the absence of a check reading as
the presence of a passing one", inside the tool built to prevent it.

Reproduction: in a venv without ruff, `python tools/lint_discovery.py` → empty report, "0
findings", the "improved" list, exit 0. With `--update` → `baseline written: 0 findings`.

Suggested fix: treat `returncode == 1 and not findings.stdout.strip()` as fatal and print stderr
(ruff with findings always emits a JSON array on stdout, so empty stdout with exit 1 is never a
legitimate lint result); or drop the `or "[]"` so `json.loads` fails loudly, and check
`ruff --version` first. Add a test that fires when ruff's invocation errors.

### v36-P2-04: the pre-push hook gates on the checked-out branch, not the refs being pushed

Severity: P2

Location: [pre-push:22-26](../../.githooks/pre-push).

Description: Git passes the refs being pushed on the hook's **stdin**
(`<local ref> <local sha> <remote ref> <remote sha>` per line). The hook never reads stdin; it
decides from `git rev-parse --abbrev-ref HEAD`. It therefore runs the suite only when `main`
happens to be checked out, regardless of what is being pushed.

Impact: fails open on every push to `main` not made from a `main` checkout: `git push origin
main` while a feature branch is checked out, `git push origin HEAD:main`, any push from detached
HEAD — all print the reassuring "Skipping; CI is the check for a branch" and push unchecked.
These are forgetting-class paths, inside the hook's advertised scope ("guards against forgetting,
not against intent"). The documented `--no-verify` escape hatch is not re-raised; this is a
different hole.

Reproduction: on a feature branch with un-pushed `main` commits, `git push origin main` — a red
`main` reaches the unprotected remote with zero checks.

Suggested fix: read stdin and gate on the remote ref:

```sh
while read -r _local _lsha remote _rsha; do
  case "$remote" in refs/heads/main) push_to_main=1;; esac
done
[ "${push_to_main:-}" ] || exit 0
```

Worth a one-line comment that the checks still run against the working tree, not the pushed
commits — inherent to any local hook.

### v36-P2-05: the hook is not enabled in this working copy

Severity: P2

Location: repository configuration state (`git config core.hooksPath` returns unset in all
scopes), against the enablement instruction in `.githooks/pre-push` and CLAUDE.md.

Description: as with v35-P1-01, this is a statement about the working environment rather than
repository content, flagged for the operator rather than acted on. Every push to `main` from this
laptop currently runs no local checks at all; combined with the documented absence of branch
protection, nothing anywhere blocks a red push — CI reports after the fact. It may have been
enabled once and lost with a re-clone, which is precisely the failure a visible check would catch.

Suggested fix: run `git config core.hooksPath .githooks`. To make the state visible rather than
remembered, consider an advisory warning from a tool that already runs (e.g. `lint_discovery.py`)
when `core.hooksPath` is unset in a git checkout on the operator's platform.

### v36-P2-06: the two required tutorial traits are selected but never asserted on the batch actually written

Severity: P2

Location: [write_reference_puzzles.py:213-240](../../forge/scripts/write_reference_puzzles.py)
(`_choose` puts the traits into the *candidate* list) and 453–497 (the write loop discards any
candidate that reaches no target with a `print` and continues).

Description: the module docstring promises the six published boards "include the two cases the
tutorial has to teach: a suffixed label and a live footnote." The guarantee holds only over the
twelve candidates; if the substitution board or the footnote board is among the discards — and the
docstring itself records that "two of six candidates produced no puzzle at any target from 12
down" — six boards publish with the promise silently broken. The project's own rule: "anything
acting as a launch gate is asserted, not printed."

Impact: `serve`'s tutorial is built against these files; a batch without a suffixed label or a
live footnote leaves the tutorial referencing a case its data does not contain, with no error
anywhere.

Suggested fix: after the loop and before `_publish`, assert over the *written* packages that at
least one carries a shared slot reference and at least one a non-zero footnote cell;
`SystemExit` otherwise, leaving the published set untouched.

### v36-P2-07: the lineup-cap boundary test never calls the implementation, so the `>` vs `>=` it names is unguarded

Severity: P2

Location: [test_lineup_fallback.py:127-139](../../forge/tests/test_lineup_fallback.py)
(`test_the_cap_is_a_strict_ceiling_at_the_boundary` computes `share = division / total` and
asserts `(share <= LINEUP_DIVISION_SHARE_CAP) is kept`); the implementation's comparison is
[lineup_fallback.py:144](../../forge/src/boxscore_forge/lineup_fallback.py)
(`if division_against_chain(fallback) > LINEUP_DIVISION_SHARE_CAP:`).

Description: the test evaluates its own restatement of the predicate on literals; line 144 never
executes. This is the "test assigns both sides from one expression" shape the project's record
names. Flip line 144 from `>` to `>=` — rejecting boards exactly at the cap, the precise
off-by-one the test's docstring says it guards — and the whole suite stays green: the over-cap
test monkeypatches the cap to `-1.0` (over under either operator) and the kept-board test uses a
board strictly below the cap.

Reproduction: edit `lineup_fallback.py:144` `>` → `>=`; `pytest tests/test_lineup_fallback.py`
passes.

Suggested fix: drive the boundary through `erase_with_lineup_fallback`: monkeypatch
`division_against_chain` so the share equals the cap exactly and assert the reason is
`"fallback"`, plus one case a hair above asserting `None, "discarded_filler"`.

### v36-P3-09: the hook discards the ratchet's failure diagnostics

Severity: P3

Location: [pre-push:37](../../.githooks/pre-push)
(`uv run python ../tools/lint_discovery.py > /dev/null`).

Description: `lint_discovery.py` prints everything — including which rule got worse and the
`--update` guidance — to stdout. On failure the push aborts with no indication of what to fix; the
operator's likely next move is `--no-verify`, which defeats the hook. It also contradicts the
ratchet's own recorded design ("the whole report is printed every run").

Suggested fix: `out=$(uv run python ../tools/lint_discovery.py) || { echo "$out"; exit 1; }` —
quiet on success, self-explaining on failure.

### v36-P3-10: the hook and CI are two hand-maintained copies of "what runs", with nothing asserting they agree

Severity: P3

Location: [pre-push:33-46](../../.githooks/pre-push) vs
[ci.yml:68-90, 111-117](../../.github/workflows/ci.yml).

Description: the hook re-spells CI's five commands. Today they match, command by command — but the
agreement is maintained by hand, and there is already deliberate divergence
(Windows-without-coverage in CI vs coverage-always in the hook) proving the lists can differ
without anything noticing. A sixth CI step never reaches the hook, which then keeps passing while
checking less than CI does — the fail-open the hook exists to prevent, via the project's
"one predicate, one place" rule.

Suggested fix: extract one `tools/check.py` (or script) both invoke; or a small test asserting the
hook's command list equals the workflow's, failing when either is edited alone.

### v36-P3-11: `run_browser_tests.py` — a late page error is ignored, and startup failures are undiagnosable

Severity: P3

Location: [run_browser_tests.py](../../tools/run_browser_tests.py) lines 62–67 (server `Popen`
with both streams to `DEVNULL`), 84 (`page.goto` with no readiness wait), 101–107 (a `pageerror`
firing *after* `window.__results` is set does not fail the run, though the docstring calls a page
error fatal), and the `finally`'s `server.wait(timeout=10)`, which can raise `TimeoutExpired` and
mask the original exception.

Description: all current paths fail closed (verified) — this is diagnosability and flakiness, not
correctness. A stolen port between `free_port()` and `Popen`, or a crash in `dev_server.py`,
presents as a bare `net::ERR_CONNECTION_REFUSED` with the server's own diagnostics discarded.

Suggested fix: fail when any `[pageerror]` line was captured even if results exist; poll
`socket.create_connection` briefly before `goto`; capture server stderr to a buffer printed on the
failure path; `kill()` fallback after `wait(timeout=10)`.

### v36-P3-12: `check_equivalence` in the erasure instrument prints its verdict instead of enforcing it

Severity: P3 — possibly superseded (the instrument targets chain rungs; the control variable is
now stalls).

Location: [measure_erasure.py:96-109](../../discovery/erasure/measure_erasure.py).

Description: the file's docstring says this check keeps the duplicated trajectory loop honest
("it measures air" otherwise), but a non-zero mismatch count only prints one line and `main()`
produces every table anyway — four screens of ordering comparisons above a one-line disclaimer.

Suggested fix: `raise SystemExit` on mismatches; or, if the file is retired, say so in its
docstring the way `ambiguity()` does in `difficulty-metrics/measure.py`.

### v36-P3-13: `check_reveal_agrees` fail-opens on short `batter_names` / `pitcher_names` / label tuples

Severity: P3

Location: [format.py:836, 839](../../forge/src/boxscore_package/format.py)
(`if index < len(names) and row.name != names[index]:` — the guard silently skips every row beyond
the shorter list).

Description: a `Reveal` with an empty `batter_names` tuple constructs and parses with no name
checked at all — absence of the data reads as agreement. `plausibility.reveal_faults` backstops
this only at the certification gate; the format's own doctrine argues the length check belongs at
construction ("a policy living only at the parse boundary let this type emit a document its own
reader refused").

Suggested fix: in `_check_rows`, refuse `len(names) != len(printed)` and
`len(labels) != len(printed)` outright.

### v36-P3-14: four `Evidence` fields are filled from the board's own in-memory object

Severity: P3

Location: [write_reference_puzzles.py:186-189](../../forge/scripts/write_reference_puzzles.py)
(`official_errors`, `official_defense_runs/hits/errors` read from `loaded.direction.line_score` —
the same `Direction` object the package's line score was built from, one `to_board` copy apart).

Description: `check_independent_correspondence` compares the package against these, so the
comparison can only catch a field-swap inside `to_board`'s eight-line copy — near-tautologies
presented in the same list as the two real anchors (`official_at_bats`, `official_left_on_base`
from `retroGameLogs`). The anchor-derived-from-what-it-verifies shape in miniature, documented as
deliberate only for the query-level case.

Suggested fix: populate them from separately-selected loader columns, or annotate at the
`evidence_for` call site that these four assert only `to_board` fidelity.

### v36-P3-15: a row-identity test's named mutation is not what fires its assertion

Severity: P3

Location: [test_identities.py:112-124](../../forge/tests/test_identities.py)
(`test_detects_a_row_with_the_wrong_plate_appearance_count`).

Description: the test sets `batting[3].plate_appearances=5` and rotates the batting tuple while
`batter_footnotes` stays in original order. After rotation the mutated row lands beside the
leadoff man's `SH=1` footnote and its identity *holds* (`5 = 4+0+1`); what fires
`ROW_PLATE_APPEARANCES` is pure footnote misalignment, which another test already covers. Revert
the PA mutation to 4 and the test still passes. If the row-identity check regressed specifically
on a wrong PA with correctly aligned footnotes, no test would notice.

Suggested fix: drop the rotation (or rotate footnotes with the rows) so the only broken thing is
the PA value.

### v36-P3-16: two "different" plausibility tests assert the identical predicate; the described second check does not exist

Severity: P3

Location: [test_plausibility.py:72-83](../../forge/tests/verify/test_plausibility.py) — both tests
run the same fixture through the same function and assert the same `"entirely nought"` substring;
the comment's second case ("no plate appearance while carrying stray numbers") is checked by
nothing here.

Suggested fix: make the second test exercise the case its comment describes, or delete it and the
comment.

### v36-P3-17: the certification test named "…names every registered check" asserts only that refusal happened

Severity: P3

Location: [test_certification.py:119-124](../../forge/tests/verify/test_certification.py) — no
assertion touches `result.refusals` or any prefix; stripping the check-name prefixing from
`certify_for_publication` leaves the suite green.

Suggested fix: assert every string in `result.refusals` is prefixed by a name in `CERTIFICATIONS`.

### v36-P3-18: the label-formatting guard exempts by basename, against the conventions' own rule

Severity: P3

Location: [test_no_label_formatting_decisions.py:28-29, 59](../../forge/tests/test_no_label_formatting_decisions.py)
(`_MAY_FORMAT = {"render_boards.py"}` checked via `path.name`).

Description: the conventions state "Exemptions are listed by path, never by basename" — the
sibling constants guard obeys this with `Path` objects; this one exempts any future
`render_boards.py` anywhere in scope. Secondary: the matcher covers only the
`"<punct>" in label` shape; `label.split("-")`, `label.endswith("-1")`, `label.count("-")` are
realistic reintroductions it cannot see, and unlike the constants guard the narrowness is
undocumented.

Suggested fix: convert `_MAY_FORMAT` to repo-relative paths; extend the matcher to
attribute-call shapes or record the soft edge in the docstring.

### v36-P3-19: the line-score anchor guard reads only the first `LineScore(...)` call in the loader

Severity: P3

Location: [test_line_score_anchors.py:35-42](../../forge/tests/test_line_score_anchors.py)
(`line_score_arguments()` returns on the first match from `ast.walk`).

Description: if the loader gains a second `LineScore` construction (a postseason branch, a
fallback), the per-field "not summed from the board" checks cover only whichever call is found
first — the anchor-manufactured-from-what-it-anchors defect free to return in the second site.

Suggested fix: collect all `LineScore` calls and apply the assertions to each.

### v36-P3-20: test documentation asserting the pre-adoption world, twice

Severity: P3

Location: [test_lineup_fallback.py:3-6](../../forge/tests/test_lineup_fallback.py) — the module
docstring says "Experimental, not adopted" and cites `test_lineup_fallback_cannot_publish.py`,
which was deleted and replaced by `test_lineup_fallback_is_adopted.py`; the source module itself
opens with "✅ ADOPTED. This is the production erasure path".
[verify/conftest.py:3](../../forge/tests/verify/conftest.py) — "Nothing in the verifier's tests
imports `boxscore_forge`", contradicted by deliberate two-sided agreement checks in
`test_boundary.py:15, 281` and `test_expected_id.py:15, 33`.

Description: both are v29-P3-01's shape — a contract statement left saying the opposite of the
settled state. The conftest's underlying rule is sound (no verifier *fixture* is built by
generator code); the stated absolute is false.

Suggested fix: rewrite the fallback docstring to the adopted state and the correct guard file;
reword the conftest to the actual invariant, optionally enforced by an AST check that
`boxscore_forge` names never reach fixture construction in `tests/verify/`.

### v36-P3-21: the innings-pool report silently omits shortened games from its rung table

Severity: P3

Location: [pool.py:103-110](../../discovery/innings/pool.py) — the rung loop starts at
`range(9, ...)` while the cohort can contain 5–8-inning games, which are counted in the
denominators but never printed as rows, so the shares do not sum to 100% and the reader cannot see
why.

Suggested fix: print rungs from `min(ungated)`.

---

## Hat 3 — Frontend Engineer

### v36-P2-08: the package boundary never checks that a given puzzle cell agrees with the solution

Severity: P2

Location: [package.js:193-199](../../serve/engine/package.js) — `readPackage` compares only the
*shape* of `puzzle` and `solution`.

Description: a package where a non-null (given) puzzle cell differs from the corresponding
solution cell passes `readPackage` cleanly. `game.isSolved()` iterates every cell, givens
included, comparing `valueOf` (which returns the given) against `cell.answer` — so a mismatch
makes `isSolved()` permanently false and `check()` returns `"wrong"` even when every blank the
player owes is correct.

Impact: an unwinnable board that renders perfectly and reports "Something doesn't add up yet."
forever — the class the file's own header calls "the unsolvable-board defect, reached from the
schema side." The board gives no per-cell feedback by design, so the player has no way to
discover the fault. Security framing: an actor who can tamper with a single static package file
(CDN or server compromise, a stale mirror) can brick a day's puzzle undetectably — the file
parses, the client verifies no signatures by design, and no check fires; for a streak product a
day of "everyone fails" is the worst available reliability event. The fix converts it into a
controlled boot-time rejection.

Reproduction: take any reference package, set one given batting cell to `answer + 1` in `puzzle`
only; `readPackage` accepts; with all blanks entered correctly, `check()` → `wrong` indefinitely.

Suggested fix: at the end of `readPackage`, assert every non-null cell of `puzzle` (grids, totals,
footnotes, `left_on_base`, line score) equals the same position in `solution`, failing with the
cell path; add the case to `package-vectors.json` so the Python reader stays answerable to the
same rule.

### v36-P2-09: C11 violation — user-facing English hardcoded in the tutorial's `sum` strings

Severity: P2

Location: [tutorial.js:71-96](../../serve/ui/phone/tutorial.js) (the `STEPS` `sum` values,
rendered at line 317 via `sum.textContent`), notably
`"2 innings = 6 outs · 9 − 6 − 1 = 2"`.

Description: the `sum` line is player-visible copy (19px bold). The fourth one contains the
English words "innings" and "outs" as literals in code; `strings.js` has no `tutorial.sum.*` keys.
Every neighbouring string goes through the catalog, and the C11 source-scan tests check
storage/fetch/routes but not these literals — the exact blind spot they were written against,
one file over.

Impact: CLAUDE.md makes C11 mandatory regardless of whether Spanish ships: "zero user-facing
strings in code… Cheap now, expensive to retrofit." A replacement catalogue would translate the
five step bodies and leave "2 innings = 6 outs" in English mid-screen.

Suggested fix: five catalog keys (`tutorial.sum.*`), referenced from `STEPS` by key as `body` and
`rule` already are.

### v36-P3-22: `clock.reseal()` is uncalled dead code whose docstring describes the opposite of what it does

Severity: P3

Location: [clock.js:155-158](../../serve/engine/clock.js) — the comment says "A restored session
may bring back a clock that was already stopped for good"; the body sets `sealed = false`,
*un-sealing*.

Description: zero callers anywhere in `serve/` (the restore path correctly calls `clock.seal()`),
no test touches it, and the next shell author who reads the docstring and calls it on restoring a
finished session reopens the sealed clock — recreating v30-P1-03, the invariant this module
exists for.

Suggested fix: delete it.

### v36-P3-23: `loadPuzzle` trusts the manifest's shape; a malformed manifest dies as a `TypeError`

Severity: P3

Location: [daily.js:34-40](../../serve/ui/phone/daily.js) — no check that `manifest` is an object,
`puzzles` a non-empty array, `generation` a string; an empty `puzzles` array fetches
`.../undefined.json` and fails in `.json()` as a `SyntaxError`.

Description: the package gets rigorous boundary validation; the pointer that selects it gets
none — and the manifest is the one file served `no-store`, the most exposed to a half-written
deploy. The player-visible outcome is survivable (both entry points catch and render
`package.unreadable`), but the console carries an unrelated `TypeError` — a page misdiagnosing
its own failure. (`?p=` input is used only after membership in the manifest — no traversal;
verified.)

Suggested fix: a small `readManifest(raw)` throwing `PackageError` naming the field.

### v36-P3-24: `reveal.played_on` is validated only as "a string"; a malformed date throws mid-reveal

Severity: P3

Location: [package.js:264](../../serve/engine/package.js) (`text(raw.played_on, ...)`), consumed
by `longDate` in [strings.js:291-294](../../serve/engine/strings.js), which computes
`month.NaN` for a malformed date and throws inside `renderReveal` — inside `check()`'s success
path, on the one screen the player reaches once — against `reveal()`'s own promise of controlled
rejection at the boundary.

Suggested fix: validate `played_on` against an ISO-date pattern in `reveal()`, failing with the
field name.

### v36-P3-25: `reveal.card` is passed through unvalidated — the pass-through the same function's docstring condemns

Severity: P3

Location: [package.js:265](../../serve/engine/package.js) (`card: raw.card ?? "",` — accepts an
object, an array, anything; nothing reads it today, which the `reveal()` header itself identifies
as the incubation condition for the next `undefined`-rendered heading, telling that story about
`raw.reveal` one field up).

Suggested fix: `card: text(raw.card ?? "", "reveal.card")`, or drop the field until something
reads it.

### v36-P3-26: the engine still accepts `enter()`, `clear()` and `hint()` on a finished game

Severity: P3

Location: [game.js:208, 229, 247](../../serve/engine/game.js) — each checks `cell.given` but never
`finishedAt`.

Description: the clock was sealed *in the engine* with the stated justification that "sealing is a
fact about the clock rather than a promise every future shell has to keep" — but the board's
immutability got the opposite treatment: only the phone layer removes handlers and the keypad.
`__game.enter(...)` from the console changes entries on a finished board; the next visibility-save
persists them under the frozen `finishedAt`, and `record().solved` can flip on a record already
reported. Tablet and desktop layers are planned; each must re-remember the rule.

Suggested fix: `enter`/`clear`/`hint` refuse when `finishedAt !== null`, with a test — mirroring
`seal()`.

### v36-P3-27: `restore()` installs saved entries into given cells

Severity: P3

Location: [game.js:388](../../serve/engine/game.js) — `if (cells.has(name))` filters on existence
but not on `given === null`, unlike `enter()`. Harmless today because `valueOf` prefers the given,
but a hand-edited session's junk entry on a given cell survives every snapshot round-trip and
awaits the first consumer that reads `entries` directly.

Suggested fix: add `&& cells.get(name).given === null` so restore and enter apply one rule.

### v36-P3-28: the conformance-vector reject tests accept *any* throw

Severity: P3

Location: [engine.test.js:435](../../serve/tests/engine.test.js)
(`throws(() => readPackage(document), undefined, ...)` — with no pattern, `harness.throws` passes
on any exception).

Description: the boundary's contract is "a controlled rejection naming the field, never an
uncontrolled `TypeError` three layers later" — the distinction the shared vectors exist for is
the one thing they cannot see. A refactor making `readPackage` crash with a `TypeError` on a
mutation would keep every reject vector green.

Suggested fix: assert the thrown error is a `PackageError` for every reject vector.

---

## Hat 4 — Security Engineer

### v36-P2-10: the publication gate never checks for leaking metadata, and leaking keys sit outside the signed surface

Severity: P2

Location: [certify.py:297-305](../../forge/src/boxscore_verify/certify.py) — `CERTIFICATIONS`
contains no check that `LEAKING_METADATA` keys (`game_id`, `retrosheet_id`, `season`, `date`,
`teams` — [format.py:444](../../forge/src/boxscore_package/format.py)) are absent;
[signing.py:64](../../forge/src/boxscore_package/signing.py) —
`document = package.published().as_json()`;
[write_reference_puzzles.py:480-482](../../forge/scripts/write_reference_puzzles.py) — the only
leak check in the tree, ad hoc inside one script.

Description: two gaps with one root. (a) `certify_for_publication` — built to be "the single gate
a puzzle passes before it may be published" — never asserts the metadata is free of leaking keys;
a producer that forgets `.published()` before writing signs, certifies and publishes a file
carrying the answer, and only the reference script's ad-hoc `if "game_id" in restored.metadata`
catches it today. The script's own `refuse_second_direction` docstring states the principle
violated: "a rule applied during selection is not a check performed at the boundary."
(b) Because `canonical_bytes` signs `published().as_json()`, content under a leaking key is
*outside the signed surface*: a served file into which `game_id` has been injected still
verifies, and a file that was never stripped verifies as authentic.

Attack scenario: no external attacker needed for the damaging case — a future inventory pipeline
(the calendar builder) writing packages without `.published()` ships `game_id`/`date`/`teams` in
every file; every check passes; every player with devtools open reads the reveal before playing.
Exploitation method: read the JSON the client fetches. Business impact: §7's core promise (the
mystery) silently void for a whole generation of inventory, with nothing in the pipeline able to
notice.

Recommended fix: add a certification asserting `LEAKING_METADATA.isdisjoint(package.metadata)` —
it composes into the registry and the existing registry-wiring test covers it. Separately, decide
whether signed bytes should equal served bytes (sign the file's canonical parse as-is); if not,
document that leaking keys are unsigned surface.

### v36-P2-11: SQL assembled from database-derived values under a `noqa` that claims "module constants only"

Severity: P2

Location: [measure.py:285-301](../../discovery/batting-order/measure.py) — the `excluded`
predicate interpolates `(a.GAME_ID = '{game}' AND a.TEAM_ID = '{team}')` from `broken`, which is
built from rows returned by the previous query (line 183), under
`# noqa: S608 - module constants only`.

Description: the values are database content, not module constants, interpolated with no
escaping. The convention is absolute: "Parameterized queries only… Ever, including in throwaway
scripts." The false `noqa` justification blinds the reader and the ratchet at the one place they
would look.

Attack scenario: values come from `dbo.retroGameProvenance`/`retroDailyReg` on a local trusted
database, so practical injection requires poisoned Retrosheet load data; a `GAME_ID` containing
`'` would at minimum break the query. Exploitation likelihood very low; business impact limited
to a local read-only analysis run. The real cost is the false suppression and the drift
precedent.

Recommended fix: parameterize (`(a.GAME_ID = ? AND a.TEAM_ID = ?)` joined per pair, values
flattened into `execute`); at minimum correct the `noqa` comment — a suppression that misstates
its grounds is worse than none.

### v36-P3-29: the signing-key doc recommends persisting the unrotatable secret as a permanent User environment variable

Severity: P3

Location: [signing-keys.md:38-39](../../docs/signing-keys.md)
(`[Environment]::SetEnvironmentVariable("BOXSCORE_SIGNING_KEY", ..., "User")`).

Description: a User-scope variable is inherited by every process the account runs — every
`npm install` postinstall, every pip build hook, every script from every sibling project on this
multi-project machine. The same doc states this is the one secret that cannot be rotated cheaply.
Attack scenario: any compromised dependency executed anywhere on the laptop reads `os.environ`
and exfiltrates the key; the holder can then sign inventory `serve` accepts. The failure the
permanent variable prevents — "publish fails for a forgotten shell" — is already a loud,
fail-closed error by the doc's own design, so the convenience buys nothing. (The compose
container does not inherit it — no `environment:` in `compose.yaml`; verified.)

Recommended fix: remove the permanent-scope option; keep the per-session line, or have the
publish tool read the key file directly at publish time so the key is in a process environment
for zero seconds.

### v36-P3-30: GitHub Actions pinned by mutable tag in a permanently-private, trade-secret repo

Severity: P3

Location: [ci.yml:49, 58, 98, 103](../../.github/workflows/ci.yml) (`actions/checkout@v4`,
`astral-sh/setup-uv@v5`).

Description: both are mutable references; `permissions: contents: read` is correctly minimal and
no secrets are referenced (verified), so exfiltration of the checked-out `forge/` — exactly the
asset that keeps this repo private forever — is the entire supply-chain risk. Low likelihood,
high asymmetry, one line per action to fix.

Recommended fix: pin both to full commit SHAs with the version as a comment.

### v36-P3-31: the dev container's `restart: unless-stopped` keeps an unauthenticated server on every network the laptop joins

Severity: P3

Location: [compose.yaml:32-35](../../compose.yaml) (`0.0.0.0:8137:8080` +
`restart: unless-stopped`), serving the whole `serve/` working tree via stdlib
`SimpleHTTPRequestHandler` with directory listings.

Description: the all-interfaces publish is deliberate (phone testing); the undocumented
interaction is the restart policy — once started, the container auto-starts with Docker Desktop
on every boot, indefinitely, including on public Wi-Fi. What it serves is low-value today
(`forge/` is not mounted; mounts are `./serve` and `./tools`, read-only — verified); the standing
exposure includes uncommitted work and gitignored leftovers such as
`serve/data/puzzles/.staging/`, plus the general surface of an unhardened stdlib server.

Recommended fix: `restart: "no"` (or a compose profile) so exposure is opt-in per session; keep
`0.0.0.0`, which is the feature.

### v36-P3-32: `render_boards.page()` interpolates `title` and `intro` without `esc()`, against `esc()`'s own contract

Severity: P3

Location: [render_boards.py:259-273](../../discovery/pitcher-cap/render_boards.py).

Description: `esc()`'s docstring states "Everything interpolated into generated HTML goes through
here", and every board value does — but the page title and intro do not. All eight current call
sites pass literals; the day a caller builds a title from a database label, the project's explicit
rule ("Escape or DOM-render any interpolated value in generated HTML, including discovery
instruments") breaks silently. Attack scenario: a DB-sourced label carrying markup executes in
the operator's browser when the report opens. Low likelihood; the harm is to the operator's
machine and the fidelity of a decision page.

Recommended fix: wrap both in `esc()`.

### v36-P3-33: `board-prototype/build.py` embeds DB-derived JSON into a `<script>` block without `</script>` hardening

Severity: P3

Location: [build.py:143](../../discovery/board-prototype/build.py)
(`template.replace("/*BOARDS*/", json.dumps(boards, indent=1))`).

Description: the template's runtime rendering is properly escaped (verified), but the injection
point is inside a script element and `json.dumps` does not escape `/` — a string value containing
`</script>` (player names come from `retroMaster`) would terminate the block before the page's own
escaping runs. Not a live risk with Retrosheet surnames; the standard fix removes the assumption.

Recommended fix: `.replace("</", "<\\/")` on the dumped JSON.

### v36-P3-34: `footnote-height.html` interpolates manifest ids into `innerHTML` unescaped

Severity: P3

Location: [footnote-height.html:67-78](../../serve/tests/footnote-height.html)
(`rows.map((r) => \`<tr><td>${r.id}</td>…\`)`) — `r.id` comes from `manifest.puzzles`, which
nothing validates (the package reader validates the file's `puzzle_id`, never the manifest entry
it was fetched by).

Description: rule-conformance rather than a live hole — an attacker who controls the manifest
controls the served content anyway. Secondary nit, same file, line 42:
`renderFootnotes(puzzle, game, () => {})` passes a third argument the function no longer takes, a
leftover from the erasable-footnote era. (`linescore-width.html`, `linescore-cap.html`, and the
harness's `innerHTML` uses were checked and are clean.)

Recommended fix: build the rows with `createElement`/`textContent`, or validate each manifest id
against `/^[0-9a-f]{16}$/`; drop the stale argument.

### v36-P3-35: `serve/data/README.md` claims "serve verifies before rendering"; the brief and the code say the client never verifies

Severity: P3

Location: [README.md:9-11](../../serve/data/README.md) versus `docs/serve-brief.md` §5 ("The
client does not verify signatures") and [package.js:9-12](../../serve/engine/package.js) ("this
file contains no verifier by design").

Description: no verification code exists anywhere under `serve/` (no consumer of
`signing-public-key.hex` or the manifest's `signature` field — verified). If the README means a
future VPS ingest step, it states it in the present tense as an existing guarantee — a rule
stated falsely in the place people go to learn the rules, the shape CLAUDE.md's CI section was
rewritten to close.

Recommended fix: reword to say where verification actually happens and what the committed public
key is for.

---

## Hat 5 — Backend Architect

### v36-P2-12: a fallback board's dependence on the batting order is recorded nowhere in the package

Severity: P2

Location: [write_reference_puzzles.py:127-128](../../forge/scripts/write_reference_puzzles.py)
(`produced, why = erase_with_lineup_fallback(...)` followed by `del why`);
[identities.py:93-104](../../forge/src/boxscore_forge/identities.py) — `FAMILY_OF` has no entry
for `Identity.BATTING_ORDER`, so `Solution.families_used` / `family_counts` silently exclude
every `LINEUP_ARITHMETIC` step.

Description: `erase_with_lineup_fallback` returns the reason precisely because "every measurement
comparing these boards needs to know which population each one is in"
(`lineup_fallback.py:127–129`) — and the one production caller deletes it. Package metadata
records `families`, which cannot represent the batting order. A published board that is unique
and derivable *only because of the batting-order clue* is indistinguishable, in its own metadata,
from a plain board.

Impact: seam C3 requires "rich metadata … techniques required." §8 has to teach the cyclic rule
because it is the one family that cannot be read off a boxscore; a calendar shaping the week by
required techniques, or a client deciding what to surface, cannot see the one technique that
most needs teaching. `family_counts` also silently undercounts deductions on fallback boards.
Cheap now, expensive to retrofit onto published inventory.

Suggested fix: record `why` in metadata (e.g. `"erasure_path": "fallback"`) and/or a flag when
any deduction's technique is `LINEUP_ARITHMETIC`; decide `BATTING_ORDER`'s place on the family
axis explicitly (see also v36-P3-38 and v36-P3-06).

### v36-P3-36: `GATE = 0.25` overrides the decided zero-density gate with an unexplained literal

Severity: P3

Location: [write_reference_puzzles.py:55](../../forge/scripts/write_reference_puzzles.py)
(`GATE = 0.25`, no note) used at line 419; `load()` defaults to
`boxscore_domain.ZERO_DENSITY_GATE` (0.30, "Measured… decided").

Description: a *stricter* pool gate than the decided one, with no reason, no measurement, no
`PROVISIONAL` marker — everything the constants convention requires for a value that shapes the
product. The literal-copy guard cannot fire because 0.25 is a different number for the same knob,
the drift the guard is blind to. The six reference boards `serve` is built against are drawn from
a different pool than the one every measurement describes.

Suggested fix: use `ZERO_DENSITY_GATE`, or attach the note the convention requires.

### v36-P3-37: the production publication script imports its loader from `discovery/`

Severity: P3 — possibly tracked (adjacent to the recorded move of the adapter out of
`discovery/verifier/`).

Location: [write_reference_puzzles.py:25-29](../../forge/scripts/write_reference_puzzles.py)
(`sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))` then
`from measure import Loaded, load, slot_references`).

Description: `publish.py`'s own docstring records this exact pattern as a fixed defect ("a
research experiment supplying the conversion for the artefact that ships. It is here now."). The
pool loader and `slot_references` — load-bearing for what gets published — still live in a
discovery instrument, outside `mypy src` and inside the ratcheted lint tree.

Suggested fix: when the inventory pipeline is built, promote the loader (at least
`slot_references`, which produces a published, schema-validated field) into `forge/src`.

### v36-P3-38: the equality-identity set is spelled in three places, tied only by subset assertions that cannot fire on the realistic drift

Severity: P3

Location: [test_identities.py:209-223](../../forge/tests/test_identities.py) (hand-listed
`equalities`, asserted `<= FAMILY_OF.keys()`);
[test_constraints.py:20-31](../../forge/tests/test_constraints.py) (a second hand-written copy);
[identities.py:93-104](../../forge/src/boxscore_forge/identities.py) (`FAMILY_OF` itself).

Description: the subset assertion fires only if an identity is *removed* from `FAMILY_OF` while
still on a hand list. The realistic drift — a new equality identity added to `find_violations`
but forgotten in `FAMILY_OF` — is invisible, because the hand lists won't contain the newcomer
either. `BATTING_ORDER` is the live demonstration: absent from all three, and nothing
distinguishes "deliberately unmapped" from "forgotten". The `test_constraints` copy also blinds
the system-strength agreement test in one direction.

Suggested fix: one definition in `identities.py` — an explicit `UNMAPPED` set with the reason
each member is outside the family axis — and assert
`set(Identity) - UNMAPPED == FAMILY_OF.keys()`, so a newcomer must be classified somewhere or the
test goes red; have `test_constraints` import it.

---

## Hat 6 — UX + Visual Design Expert

### v36-P2-13: the dark palette lives in `board.css`, so the tutorial page ignores dark mode entirely

Severity: P2

Location: [board.css:43-79](../../serve/ui/phone/board.css) — the only
`@media (prefers-color-scheme: dark)` token override block;
[tutorial.html:5-11](../../serve/ui/phone/tutorial.html) — links `tokens.css` and `landing.css`
but deliberately not `board.css` (the comment's reason is the *rules*, not the palette).

Description: `tokens.css` defines only light values, so in dark mode the flow goes landing (dark)
→ *How to play* (full-brightness white page) → board (dark). The omission of `board.css` was
decided for the tutorial's layout rules; the side effect on the palette is mentioned nowhere.
Also a token-discipline violation by both files' own charters: the entire dark palette —
constants, decisions — lives outside the constants file.

Reproduction: OS dark mode → open `tutorial.html` → white page; `index.html` → dark page.

Suggested fix: move the dark token block into `tokens.css` (linked by all three pages); update
the parse-survival test at `engine.test.js:1326` whose `REQUIRED` entry pins the media rule to
`board.css`.

### v36-P2-14: the reference-sheet button is a ~26px touch target on a product with a 44px floor

Severity: P2

Location: [board.css:538-546](../../serve/ui/phone/board.css) (`.reference-key`: 12px line-height
+ 2×6px padding + 2×1px border ≈ 26px tall).

Description: §6's 44px minimum is honoured everywhere else — keypad keys, `.again`,
`.reveal-close`, `.landing-how`, `.tutorial-skip` all carry explicit `min-height` — and the brief
rebuilt an entire footnote line because its terms measured 29px. The reference key is the one
persistent in-play control (§3b: the safety net that made the tutorial skippable) and it is the
smallest target on the screen; a mis-tap lands on the verdict strip or the keypad's top edge.

Suggested fix: `min-height: var(--cell)` (the footer has the vertical room), keeping the quiet
pill look via padding — then verify with a screenshot, per the project's own rule for anything
visual.

### v36-P3-39: the two totals rows produce identical accessible names

Severity: P3

Location: [board.js:204](../../serve/ui/phone/board.js) — `cellNode` builds
`dataset.label = \`${rowLabel}, ${column}\``, so a blank batting-totals hits cell and a blank
pitching-totals hits cell are both announced "Totals, hits, blank". Because the cells carry
`role="button"`, table-header context is not reliably announced; totals are an input surface in
every reference package, so these ambiguous cells are among the most edited. Secondary: the
board's header cells carry no `scope` attributes (the reveal's do).

Suggested fix: include the section in the totals label, composed from existing catalog keys
(keeping C11); add `scope="col"` while there. Judge the result with a screen reader on a device.

---

## Hat 7 — Baseball + Boxscore Domain Expert

### v36-P2-15: the innings-pitched notation exists in three copies asserting two different rules, and one parser refuses the other side's output

Severity: P2

Location:
[innings.py:28-56](../../forge/src/boxscore_package/innings.py) — `to_display(12)` → `"4.0"`,
docstring: "Whole innings keep their `.0`"; `from_display("4.0")` → 12; module docstring: "one
place that converts."
[columns.js:72-79](../../serve/engine/columns.js) — `inningsToDisplay(12)` → `"4"` (the bare form
the Python docstring names as the misaligned case); `inningsFromDisplay("4.0")` → `null` (regex
`(?:\.([12]))?`).
[finish.js:57](../../serve/ui/phone/finish.js) — a third, hand-written copy
(`\`${Math.floor(outs / 3)}.${outs % 3}\``), printing `9.0` on the reveal — the exact form the
tutorial's comment at `tutorial.js:110-116` condemns and replaced with the shared definition
("A tutorial teaching a notation the real board does not use is worse than one that teaches
nothing"). Its guarding test (`engine.test.js:2574-2581`) re-implements the same formula, so the
test agrees with the copy rather than with the board — the harness supplying the property under
test, in miniature.

Description: both sides are tested, asserting opposite answers for whole innings
(`test_innings.py:42` pins `"4.0"`; `engine.test.js:369` pins `"1"`), and the client parser
rejects the string the format's own reference implementation emits. The player sees `4` on the
board and the tutorial, then `9.0` on the reveal. The hand-solve pack — a launch gate whose
boards are supposed to feel like the product — prints IP with the Python rule.

Impact: no wrong puzzle can ship from this today (the surfaces are disjoint), but this is the
project's named failure shape — two copies of one rule, each with a green test — inside the
module whose docstring promises there is only one copy.

Suggested fix: the two docstrings carry contradictory design claims (column alignment vs "the way
a printed boxscore writes them"), so which rule wins is an operator decision. Then: make the
loser follow it, replace `finish.js`'s copy with the shared `inningsToDisplay` (or record the
alignment exception beside it), make `inningsFromDisplay` accept `.0` regardless, change the
reveal test to assert against the shared definition, and add the round-trip to the shared
conformance vectors so the sides cannot drift again.

### v36-P2-16: a client test encodes a false baseball rule — a staff's out total is not always a multiple of three

Severity: P2

Location: [engine.test.js:384-391](../../serve/tests/engine.test.js) ("the real packages'
pitching totals are whole innings": `equal(outs % 3, 0, ...)` over every reference package, with
the comment "a staff total ending in a third means somebody's row is wrong").

Description: when the board's offense is the home team and wins by walkoff, the defending staff
records only 0–2 outs in the final inning — staff total 25 or 26 outs, e.g. `8.1` IP. That is
ordinary baseball, and the forge explicitly supports it:
[certify.py:288-294](../../forge/src/boxscore_verify/certify.py) bounds staff outs by
`3·(innings−1) ≤ outs ≤ 3·innings` *because* "the last half-inning is not always completed", and
nothing in the pool filter excludes walkoff directions (checked).

Impact: the test passes today only because none of the six reference packages happens to be a
walkoff won by the offense. The first regenerated reference set that includes one — a common game
shape — fails CI on **correct** data, and the failure message sends the reader hunting for a
defect that does not exist. A check asserting a false rule over fixtures is a time bomb rather
than a guard.

Reproduction: any direction where the offense is the home club and the game ends on a walkoff —
home wins 3–2 in the bottom of the 9th with one out: opposing staff pitched 25 outs, `25 % 3 = 1`.

Suggested fix: assert the certifier's true rule instead:
`3·(n−1) ≤ outs ≤ 3·n` with `n = lineScore.offense_by_inning.length`. Still catches a corrupt
row, and matches the forge's stated semantics instead of contradicting them.

---

## Hat 8 — Kakuro / Logic Puzzle Expert

### v36-P3-40: `_percentile` returns the maximum for any list of ten or fewer costs

Severity: P3

Location: [solver.py:360-361](../../forge/src/boxscore_forge/solver.py)
(`costs[min(int(0.9 * len(costs)), len(costs) - 1)]`).

Description: for every `n ≤ 10`, `int(0.9·n) = n−1`, so `ninetieth_percentile_resolution` and
`ninetieth_percentile_search` return the **max** — the exact degenerate value the p90 exists to
avoid ("p90, never max — the max is 8 or 9 on every board", CLAUDE.md §1). Costed steps exclude
bounding and lineup steps, so short solves genuinely have ≤10 costed steps, and the grading metric
collapses onto the max for exactly the boards it should separate. The metric grades, it does not
gate — hence P3.

Suggested fix: nearest-rank p90 (`index = ceil(0.9·n) − 1`), with a test at n = 10.

### v36-P3-41: plain-path difficulty is graded against a weaker clue surface than the player receives

Severity: P3 — possibly tracked (adjacent to the open batting-order investigation, which is about
fallback boards; this is about plain boards).

Location: [lineup_fallback.py:135](../../forge/src/boxscore_forge/lineup_fallback.py) (the plain
attempt calls `erase(...)` with no `slots`, so the grading solver never uses lineup arithmetic)
versus [verify.py:215-233](../../forge/src/boxscore_verify/verify.py) (slot references are
required in every package from schema 2, so the verifier — and the player — always see the lineup
grouping on the board).

Description: a plain board's `stalls`/chain metadata is measured by a solver that could not use
the cyclic order, but the published board prints `9a`/`9b`, and a player who knows the
divide-by-nine trick can use it wherever a slot's PA is pinned. Correctness, uniqueness and
derivability are unaffected (the verifier's stronger surface only makes certification more
lenient, which is safe); only the difficulty classification the calendar will consume is
optimistic-high on such boards.

Suggested fix: nothing unilateral — when the hand-solve pack calibrates stalls against felt
difficulty, include plain boards where lineup shortcuts exist, so the grading surface and the
player's surface are compared on the same boards.

### v36-P3-42: a bounding step's `equations_live` includes the global equations even when the bound did not need them

Severity: P3

Location: [solver.py:464-467, 505-507](../../forge/src/boxscore_forge/solver.py) — when
propagation finds nothing, `live` (measured over `system + global_equations`) is stored on the
subsequent bounding `Deduction` even when `_bounding_moves` succeeded with `needed_global=False`,
against the module's own rule that search cost is "measured over the phase that supplied the
move". Metric-only; nothing downstream reads the pair today (`search_cost` is `None` for bounding
steps).

Suggested fix: compute `live` for the phase that produced the deduction, or record `None`.

---

## Hat 9 — Docker / Containerization Expert

### v36-P3-43: python is PID 1 with no `init`, so every container stop burns the 10-second kill timeout

Severity: P3

Location: [compose.yaml:20, 35](../../compose.yaml) (exec-form `command` makes CPython PID 1;
`dev_server.py` installs no SIGTERM handler and PID 1 gets no default signal dispositions).

Description: `docker compose stop` sends SIGTERM, nothing happens, and the runtime SIGKILLs after
the grace period — a ~10-second stall on every stop/restart. Cosmetic in dev; worth one line
because a server that ignores SIGTERM is the kind of shape that silently becomes the production
path.

Suggested fix: `init: true` on the service.

### v36-P3-44: the compose comment claims the browser tooling shares port 8137; the browser tooling deliberately does not

Severity: P3

Location: [compose.yaml:30-31](../../compose.yaml) ("8137 is also what the browser tooling uses,
so there is one address and one server rather than two that can drift") versus
[run_browser_tests.py:43-52](../../tools/run_browser_tests.py) (`free_port()`, whose docstring
explains it avoids 8137 specifically so the suite can never silently test *the container's* files
instead of the working tree).

Description: two files asserting opposite facts about the same decision — the compose comment is
stale, and someone "restoring" the sharing on its strength would reintroduce the exact hazard the
tool's docstring names.

Suggested fix: rewrite the compose comment: 8137 is the host-side phone address; the browser
suite intentionally runs its own server on an ephemeral port.

---

## Hat 10 — SEO / Search Discoverability Expert

Calibrated for a pre-launch project with no production server: each finding states whether it is
a defect in what exists or a decision to record before launch.

### v36-P2-17: all three pages ship the identical, generic `<title>boxscore</title>`, hardcoded outside the string catalog

Severity: P2

Location: [index.html:4](../../serve/ui/phone/index.html), [play.html:4](../../serve/ui/phone/play.html),
[tutorial.html:4](../../serve/ui/phone/tutorial.html) — versus
[strings.js:182](../../serve/engine/strings.js) (`"landing.name": "boxscore"`).

Description: three distinct pages carry one identical one-word title, and the string is spelled in
three HTML files *and* the catalog — four copies of one user-facing string, invisible to the C11
source-scan tests because it lives in markup. The `<title>` is the most player-visible string
there is: browser tab, history, bookmarks, and the headline of every search result. No
`document.title` assignment exists anywhere in `serve/ui/phone/*.js` (verified).

Impact: duplicate titles across all URLs mean search engines pick their own or fold the pages
together; "boxscore" alone competes with a dictionary term and says nothing about the product.
The tutorial — the page most likely to rank for "how to play" queries — is indistinguishable from
the board.

Suggested fix: distinct catalog-driven titles per page — keep a minimal static `<title>` as the
pre-JS fallback and have each entry point set `document.title` from new catalog keys
(`title.landing`, `title.tutorial`, `title.board`). Three keys and three lines; restores C11's
one-definition rule.

### v36-P2-18: the landing page's entire indexable content is client-rendered *and* gated behind a successful package fetch

Severity: P2

Location: [index.html:14](../../serve/ui/phone/index.html) (the body's only content is
`<div id="landing"></div>`); [landing-main.js:35-47](../../serve/ui/phone/landing-main.js)
(`renderLanding` is called only inside the `try` after `await loadPuzzle()`; the catch renders
`package.unreadable`); [landing.js:40-55](../../serve/ui/phone/landing.js) (the `h1`, tagline and
"not trivia" line are all built after the fetch resolves).

Description: the landing HTML contains zero content. Everything — including the purely static
copy that has no data dependency at all, which `serve-flow.md` §1 treats as the first thing a
visitor must read — renders only after two network fetches succeed. If either fails at crawl or
render time, the page's whole content is one error sentence, and the anchor to `tutorial.html`
never exists, making the tutorial an orphan page.

Impact: non-JS crawlers and social scrapers see an empty page; a transient fetch failure at
Google's render time indexes the error string as the homepage's content; internal-link discovery
of `play.html` and `tutorial.html` depends entirely on JS plus data availability.

Reproduction: `curl` the landing URL — the body is one empty div; or block `manifest.json` in
devtools and reload — a single error sentence, no links.

Suggested fix: split `renderLanding` so the static block (h1, tagline, not-trivia, the tutorial
anchor) renders *before* `await loadPuzzle()`, and only the example board, the play label and the
finished state wait on the fetch — strictly better on a slow connection too, and C11 is
untouched. Whether to bake the static copy into the HTML at build time is a separate later
decision.

### v36-P2-19: `serve/tests/` ships to production under the project's own deployment rule

Severity: P2

Location: [serve/tests/](../../serve/tests/) — four HTML pages (the engine-test harness
`index.html` plus three measurement pages), the harness, the test suite, and two vector files,
all inside `serve/`; versus CLAUDE.md ("**Deployment ships `serve/` only**") and
[dev_server.py:15-17](../../tools/dev_server.py), which was deliberately placed *outside*
`serve/` for exactly this reason.

Description: the dev server got the ships-with-serve reasoning applied; the tests did not. Under
the documented rule, `https://<domain>/tests/` will serve the engine-test harness with a 200, and
the measurement pages become live, accidentally indexable URLs — thin, off-brand internal content
on the production domain. Nothing links to them, but absence of links is not exclusion.

Suggested fix (a decision to record now, enforced at deploy time): exclude `serve/tests/` from
the shipped artifact, or deny `/tests/` in nginx — and record which in `serve-brief.md`, so the
first deployment script inherits the obligation the way the calendar inherited
one-game-one-puzzle. Moving the tests out of `serve/` is not recommended: they import
`../ui/phone/*` and `../engine/*` relatively and the browser suite runs in CI.

### v36-P3-45: an unknown `?p=` silently serves the default puzzle with a 200

Severity: P3 — decision to record before launch (deliberate today as a dev convenience).

Location: [daily.js:36-37](../../serve/ui/phone/daily.js)
(`manifest.puzzles.includes(wanted) ? wanted : manifest.puzzles[0]`).

Description: any unknown `?p=` — garbage, a retired id, a future id — falls back to the first
puzzle and returns identical content with a 200: a soft-404 and an unbounded duplicate-URL
space. Once `/p/<id>` routes exist (C6), a shared link to a retired or mistyped puzzle renders *a
different puzzle* as if it were the requested one — the absence of the requested puzzle reading
as the presence of a different one, the fail-open shape by name.

Suggested fix: record beside C6 in `serve-brief.md` that an unknown id is refused (the
`package.unreadable` path client-side, a real 404 at the server), never substituted. The
fallback can stay until the route work; the decision should not be invented then.

### v36-P3-46: no `lang` attribute on any shipped page

Severity: P3

Location: [index.html:1-2](../../serve/ui/phone/index.html), `play.html:1-2`,
`tutorial.html:1-2` — each begins `<!doctype html>` followed directly by `<meta charset>`; there
is no `<html>` element, so the implied one carries no `lang`. The discovery instruments all got
this right (`lang='en'`); the three shipped pages did not.

Suggested fix: `<html lang="en">` in the three files; when the Spanish catalog ships, the entry
point that swaps the catalog also sets `document.documentElement.lang`.

### v36-P3-47: no meta description on any page, while the exact right sentences already exist in the catalog

Severity: P3

Location: the three HTML files (no `<meta name="description">` anywhere) versus
[strings.js:186-187](../../serve/engine/strings.js) (`landing.tagline` and `landing.not_trivia` —
precisely the two-sentence pitch `serve-flow.md` §1 says a visitor must meet first).

Description: with no description and no crawlable body text (v36-P2-18), the search snippet is
whatever the crawler scrapes — potentially the error string. The copy already exists; the same
mechanism as v36-P2-17 delivers it.

Suggested fix: per-page descriptions via the same catalog-driven mechanism as the titles.

### v36-P3-48: decision to record — the production URL and status-code contract, before anything gets indexed

Severity: P3

Location: [dev_server.py:71-75](../../tools/dev_server.py) (`/` answers 302 →
`/ui/phone/index.html`); [daily.js:49](../../serve/ui/phone/daily.js) (`ROUTES` are relative
`.html` filenames); CLAUDE.md seam C6.

Description: the dev server is dev-only and cannot ship, but it is currently the only executable
statement of route semantics. A launch that mirrors its shape indexes three things permanently:
the implementation path `/ui/phone/index.html` as the homepage, `.html` URLs beside the eventual
clean routes (duplicate content requiring 301s forever), and a redirected rather than 200
homepage. URLs are the one thing that cannot be renamed after indexing without a permanent
redirect layer.

Suggested fix: record in `serve-brief.md`, beside the existing nginx caching decision: `/` serves
the landing directly with 200 (rewrite, not redirect); `/p/<id>` is the canonical puzzle URL with
200; `/today` is a 302 (temporary — its target changes daily); implementation paths are never
exposed as reachable alternates. Nothing to build now; it needs to exist as the sentence the
first nginx config is written against.

### v36-P3-49: decision to record — social-sharing metadata for the share feature

Severity: P3

Location: no Open Graph / Twitter Card tags exist anywhere in `serve/` (verified).

Description: `serve-flow.md` §7b's share is a PNG posted into chats; the moment those messages
carry the site URL, every messaging platform scrapes the target page for `og:*` — and today it
would find an empty JS shell (v36-P2-18), a blank link preview at the exact top of the growth
funnel. Recorded now so the share design inherits it: static OG tags from the same catalog keys
as the titles, and an `og:image` that is **static branding, never board state** — the scraper
fetches server-side, so a dynamic image cannot reflect the sharer's board anyway, and the
no-leak rule extends to it trivially when it is static.

---

## Hat 11 — Data & Data Pipeline Quality Expert

⚠️ **This hat's review was stopped by the operator before completion.** One finding was verified
before the stop and is recorded below; the remainder of the hat's scope is not covered.

### v36-P2-20: `load()`'s `gated` flag is dead — every sample is now gated, and the docstring promises the opposite

Severity: P2

Location: [measure.py:689](../../discovery/difficulty-metrics/measure.py)
(`gate_clause = zero_density_clause(gate)` computed unconditionally) and the `eligibility()` call
below it; the `gated: bool = False` parameter at line 654 is read nowhere in the body.
Introduced by commit `ad87c50`, whose diff shows `{gate_clause if gated else ""}` replaced by
`eligibility(..., gate_clause=gate_clause)` — the conditional was dropped in the hoist.

Description: `load()`'s docstring states "`gated` applies §5's zero-density gate in SQL … Off by
default so that measurements taken before the gate existed stay comparable to themselves." Since
`ad87c50`, the gate clause is applied unconditionally: `gated` is accepted, documented, and
ignored. Verified against the current source and the commit diff.

Impact: seven instruments call `load()` without `gated=True` expecting an ungated cohort —
`board-prototype/alternations.py:52`, `board-prototype/build.py:108`,
`board-prototype/working_set.py:48`, `difficulty-metrics/compressibility.py:165`,
`difficulty-metrics/measure.py:1146`, `difficulty-metrics/off_ceiling.py:54`, and
`difficulty-metrics/zero_density_gate.py:38`. The last is the sharpest: it is the instrument that
*evaluates* the gate, and re-run today it would measure the gate on a cohort the gate has already
filtered — a baseline that removed what it was testing, the recorded instrument shape. No
already-published number is corrupted (those runs predate the commit), but any ungated re-run
since `ad87c50` silently describes a different cohort under the same script — "a discovery
result that cannot be re-run identically is not evidence" — and the comparability promise in the
docstring is false. This is also the silent-dead-parameter twin of the project's named failure
mode: the flag reads as a check and checks nothing.

Reproduction: call `load(10)` and `load(10, gated=True)` — both produce the gated cohort;
`grep gated` over the function body after line 665 returns nothing.

Suggested fix: restore the conditional (`gate_clause = zero_density_clause(gate) if gated else
""`), and add a guard in the same family as the loader's existing self-checks: a test or
assertion that an ungated call's SQL does not contain the gate clause, so the next hoist cannot
drop it silently again.

---

## Reviewed without findings

- **Identity formulas, both sides** — row identity, column sums, cross-team, global
  `PA = Outs + R + LOB`, traced against the real rules including baserunning outs, pinch runners,
  walkoffs, and the ghost runner (correctly a rejection). The verifier's restatement is
  term-for-term equivalent under its own sign conventions.
- **Batting-order constraint, three encodings** — the divmod round-robin, the monotone chain, and
  the cycle closure are mutually consistent; layer 1's distribution check makes
  `lineup_values`'s value-producing step sound.
- **Interval arithmetic** in both `bounds.py` and `reason.py` — all four sign cases, the
  ceiling-division idiom, and the v28-P2-01 one-sided-inequality fix, verified.
- **Verifier independence** — `boxscore_verify` imports only `boxscore_package`,
  `boxscore_domain`, `cryptography`, and stdlib.
- **Idempotence and determinism** — `puzzle_id` from sha256 over namespace + game + offense team;
  no `hash()`, no set-order dependence, no unseeded randomness, no naive datetimes anywhere in
  `forge/src` (also `mypy --strict` and `ruff check` clean, executed).
- **Erasure discipline** — only grid cells erasable; anchors excluded at the source;
  `publish.to_board` applies the erased set uniformly.
- **Fail-closed signing** — `secret=None` raises; `Unsigned` sentinel modes mutually exclusive;
  the certification registry is discovered, not hand-listed.
- **Clock semantics, save/load/resume, storage acquisition** (all three entry points through
  `browserStorage()`), the modal lifecycle, keypad input rules, the never-say-which-cells rule at
  every layer, play-path independence, and test-mode gating — all verified against
  `docs/serve-flow.md`.
- **XSS in product pages** — every render path in `board.js`, `finish.js`, `landing.js`,
  `tutorial.js`, `shell.js` uses DOM construction; package strings and stored values never reach
  `innerHTML`.
- **No Dockerfile exists and compose builds nothing** — bind mounts only, `forge/` never mounted,
  no `environment:` blocks, so no image-layer leak path exists today. Standing condition: the
  first Dockerfile requires a `.dockerignore` excluding `forge/`, `.env*`, key files, and
  `discovery/` before its first build.
- **CI runs what CLAUDE.md claims** — all five steps present and blocking; the coverage floor
  genuinely fires (verified in the installed pytest-cov); the ratchet's config-resolution claim
  verified against baseline rule codes; UTF-8 stream handling consistent on Windows.
- **`.gitignore`/`.gitattributes` and `git ls-files`** — no tracked secrets, staging, or
  inventory; both signing-key filename shapes covered.
- **SQL table audit over `discovery/`** — every table reference is `dbo.retro*`; no other
  collection, no unqualified `FROM`.
- **The in-flight decision instruments** — `footnote-groups` (measurements as pure functions,
  eligibility as callables, counterfactual baselines), the hand-solve packs (quotas genuinely
  asserted, ceiling-pack cache stamped and re-solved on restore), `batting-order/arms.py` and
  `confirm.py` (pre-registered, paired-by-walk, per-item movement counts), the three
  arm-comparisons (union-then-filter ordering, the confound control stated at the point of
  comparison), and the loader's positional mapping and independent anchors.

## Deduplication

- Grouped across reviewers before writing: the `narrow()` non-termination was found independently
  by two reviewers (filed once as v36-P2-01); the innings divergence by two (merged into
  v36-P2-15); the construction/parse asymmetry instances merged into v36-P2-02; the
  browser-runner robustness notes merged into v36-P3-11.
- **Not raised, already tracked:** the inning-header contrast at 2.95:1 (open in
  `open-decisions.md`, with the `--fenway` remedy computed); the void Layer-3b figures; the
  batting-order confirmation run; the historical ruff-over-`discovery` gap (the ratchet now
  exists — v36-P1-01 is a defect *in* the ratchet, which is new); the batting-order
  recommendation reversal.
- **Not raised, declined by policy in `non-issue.md`:** anything requiring a second developer, a
  shared build agent, or an adversary inside the repository; the truncated instrument digests;
  row-level certification of the unplayed reveal half.
- **Not raised, deliberate design:** no hints, no error marking, hidden timer, position-only
  labels, footnote cells given, six data columns, the tutorial being skippable, `--no-verify`
  as a documented escape hatch, branch protection unavailable on the plan.
- Neither v35 finding recurs: the probe file is gone and all three entry points acquire storage
  safely.

## Disposition

| Severity | Count | Where they cluster |
|---|---|---|
| P0 | 0 | — |
| P1 | 1 | the discovery lint ratchet fails open when ruff itself is broken |
| P2 | 20 | checks that cannot fire (hook, gate assertions, boundary tests, the dead `gated` flag) and two-copies-disagreeing (innings, walkoff rule, construction vs parsing, four copies of the title) |
| P3 | 49 | guard scope gaps, stale contracts, CWD dependence, hardening, metric edges, pre-launch SEO decisions to record |

Hat 10 also verified clean: multi-page architecture with no hash routing, real anchors on the
landing page, single-`h1` structures, and the deliberate visibility of puzzle JSON. Hat 11's
coverage is only the one finding above — its review was stopped before completion.

The highest-leverage fixes, in order: v36-P1-01 (the ratchet is the only thing holding the lint
line, in CI and in the hook), v36-P2-04/05 (the hook currently protects nothing on this machine),
v36-P2-20 (every ungated discovery re-run is silently wrong until the flag works again),
v36-P2-10 (the leak check belongs in the gate before any inventory pipeline exists),
v36-P2-08 (the one client-side gap that can brick a day), and v36-P2-15/16 (both are decisions
about which of two written rules is the real one, and both get cheaper the earlier they are
made).
