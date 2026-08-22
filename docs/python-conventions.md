# Python 3.13 Project Conventions

## Language

**All artifacts are in English. Discussion is in Spanish.**

The operator discusses, explains, and reasons in Spanish. Everything that ends up in the repository
is English:

- Identifiers: variables, functions, classes, modules, files, directories
- Comments and docstrings
- Documentation, including design documents and READMEs
- Commit messages, branch names, issue titles
- Log messages and exception messages
- Database schema: table names, column names
- Configuration keys and environment variable names

No mixed-language identifiers (`get_juego`, `calendario_builder`). No Spanish comments explaining
English code. If a domain term has no clean English equivalent, use the English baseball term —
this is a baseball project and the vocabulary is already English.

**Rationale:** a single language in the codebase avoids maintaining two vocabularies for the same
concept, keeps the project legible to anyone who joins or reviews it later, and matches the
product's own interface language and legal documents.

---

## Principles

- **Test-first (TDD) is mandatory.** Write the test BEFORE the implementation. Red → Green →
  Refactor: (1) write a failing test that specifies the behavior, (2) write the minimum code to
  pass it, (3) refactor with the test as safety net. **No feature or bugfix code is written
  without a failing test first.**
- **Everything has a test.** No feature, endpoint, view, model method, management command, or bug
  fix ships without a test that covers it. If it's hard to test, the design is wrong — fix the
  design (inject dependencies, keep I/O at the edges), don't skip the test.
- Write code that is obvious to read, not clever to write.
- Every function does one thing. If you need the word "and" to describe it, split it.
- Fail fast, fail loud. No silent swallowing of errors.
- Design for testability: inject dependencies, keep I/O at the edges.
- **Do not reinvent the wheel.** Order of preference: the standard library first, then an
  established and widely known third-party library, and only then new code of our own. Writing a
  hand-rolled version of something the stdlib or a well-known library already does is a defect, not
  a shortcut — it carries bugs the alternative fixed years ago. Adding the dependency is still a
  decision, not a reflex; see Dependencies.
- **Correctness beats convenience.** Where a rule below conflicts with shipping faster, the rule wins.

---

## Style & Structure

- PEP 8 enforced via `ruff`. Max line length: 120. Target: `py313`.
- **Formatting via `ruff format`.** Not negotiable per-file, not configurable per-developer. Run it
  in the pre-push hook and in CI. (There is no pre-commit hook; see *GitHub configuration*.)
- Naming: no single-letter variable names. Use descriptive names that convey intent (`result` not
  `r`, `directory` not `d`). **Exception:** conventional indices in tight numeric loops (`i`, `j`)
  and standard math notation where a longer name would obscure the formula.
- Trailing commas in all multi-line structures.
- Absolute imports only. No wildcard imports. No unused imports.
- Remove dead code — no commented-out blocks, no `TODO` without a linked issue.
- Project layout: source in `src/<package>/`, tests in `tests/` mirroring `src`, shared fixtures in
  `conftest.py`.
- **`pathlib` over `os.path`.** No string concatenation for paths.

---

## Type Hints (Mandatory on all public interfaces)

- Modern 3.13 syntax only: `list[str]`, `X | None`, type aliases, inline generics
  `def f[T](x: T) -> T:`.
- No legacy imports from `typing` for builtins (`List`, `Dict`, `Optional`, `Tuple`).
- **`from __future__ import annotations`: not used by default.** Modern syntax works natively on
  3.10+ without it. It is still permitted in a single case: forward references to a class from
  inside its own body, where the alternative is quoted annotations. **Do not add it to modules
  using Pydantic or any library that introspects annotations at runtime** — deferred annotations
  break runtime introspection.
- Use `TypeIs` over `TypeGuard`. Use `TypeVar` defaults where appropriate.
- `# type: ignore` must include error code: `# type: ignore[attr-defined]`. Every one needs a
  comment explaining why, or it gets removed at review.
- **`Decimal` for money. Never `float`.** Anything touching prices, refunds, or billing.
- **Prefer integers over floats for domain quantities that are inherently discrete.** Baseball
  innings pitched are thirds of an inning — store outs as `int`, format as `x.y` only at the
  presentation edge. Floats in arithmetic identities will produce puzzles that fail validation for
  no visible reason.

---

## Determinism (project-critical)

The generator must be idempotent: the same input always produces the same output with the same ID.
These are the ways Python breaks that silently.

- **Never use `hash()` for anything persisted or compared across processes.** String hashing is
  salted per interpreter run (`PYTHONHASHSEED`), so `hash("BOS197408120")` differs between runs.
  Use `hashlib` (`sha256`) for stable IDs.
- **Never iterate a `set` where output order matters.** Set iteration order is not guaranteed
  across runs. Sort explicitly, or use a list.
- **No unseeded randomness in the pipeline.** If a step needs randomness, take an explicit seed
  parameter derived from stable input. `random` module global state is not reproducible.
- **All datetimes timezone-aware.** No naive `datetime.now()`. A daily puzzle rolling over across
  timezones is exactly where naive datetimes cause bugs that only appear in production. Enforced
  by ruff `DTZ`.
- **Sort before writing.** Any generated file, JSON key order, or manifest must be deterministic
  so the same run produces byte-identical output. Makes diffs and signature verification useful.
- **Pin the toolchain.** A rebuild on a new machine must produce the same artifacts. See
  Dependencies below.

---

## Functions & Design

- ≤20 lines per function as a **smell threshold**, not a hard limit. Over 20, justify in a comment.
  Return early to reduce nesting.
- 3+ parameters → keyword-only args (`*`). For 2-param functions, use `*` when argument order is
  non-obvious or types are identical. Exceptions require a comment.
- **Boolean parameters are keyword-only, always.** `validate(puzzle, strict=True)` not
  `validate(puzzle, True)`. Enforced by ruff `FBT`.
- Never use mutable defaults. Use `None` and assign inside.
- Google-style docstrings on public functions. Don't restate type hints in docstrings.
- Pure functions where possible. Keep I/O and side effects at the boundaries.
- Prefer composition over inheritance. `@dataclass(frozen=True, slots=True)` or Pydantic models
  for data containers. **Default to frozen** — mutable data containers passed through a validation
  pipeline are a source of action-at-a-distance bugs.
- Anything common and repetitive across functions gets extracted.

---

## Constants

### No magic numbers outside a constants module

A value that encodes a **domain decision** or a **presentation budget** lives in one place. Anywhere
else it is a literal, and literals drift. This project has already paid for three definitions of the
erasable set, two copies of the accepted-sources list, and a roster cap written as a call argument in
twenty-five places — so when the measurement behind that cap turned out to be invalid, the number was
in twenty-six places and the reason was in none of them.

**Two modules, and they are never shared:**

| Module | Holds |
|---|---|
| `forge/src/boxscore_domain/` | Roster caps, pool gates, stall targets, era quotas, forward inventory |
| `serve/ui/phone/tokens.css` | Design width, touch target, column widths, colours, keypad height |

§33 keeps them apart: the forge knows nothing about screens and the service knows nothing about
generating. **A single shared constants module would be imported by both sides for the convenience of
one**, and that boundary is the thing being protected. When the client genuinely needs a domain value —
a test asserting published packages respect the caps — it crosses as **data**, in the shared JSON both
readers already load, with a forge test asserting the two still agree.

**Local values with no meaning outside their function are not constants** and do not belong there. A
loop bound, a buffer size, a retry count used once — leave them where they are. The test is whether
someone could reasonably want to change the value *as a decision*.

### Every constant records why, not only what

**The value is the smallest part of what needs recording.** Each one carries:

- **The reason it holds that value.**
- **The measurement that set it**, where one exists — **with the figures and with the file that holds
  them**, not a reference to a conversation or a commit.
  `81% of directions reach 8 stalls against 60% plain (discovery/batting-order/confirm.json)`, not
  "measured in the batting-order run".

  ⚠️⚠️ **The example here used to be `22% -> 33% coverage at 8 stalls`, and that number is in no output
  file.** The rule asked for figures rather than a reference to a commit, and its own illustration was
  a figure nobody can reproduce — searched across every committed result and every run log in the tree.
  Figures alone were not enough: a number quoted from memory looks exactly like a number quoted from a
  run. **Name the artefact**, and if there is not one, the measurement did not happen in a form anyone
  can check.
- **Whether it is provisional**, explicitly and in the same place, when it was chosen rather than
  measured.

A file presenting a measured cap and an eyeballed threshold in the same typeface hides which are safe
to touch. Six months on, *which of these can I change* has to be answerable from the file alone.

⚠️ Write the note as a **string literal directly below the assignment**, never as an f-string. An
f-string there is a discarded expression rather than an attributed docstring: it renders as
documentation to a reader and no tool ever sees it — the same shape as a check that looks like a check.

### Superseded values stay visible

When a constant changes, **the previous value and why it was wrong stay in the comment.** Not a
changelog entry, not a commit message: the file.

**A regeneration that overturns a decision and one that confirms it are equally worth recording.** What
gets reused is the reasoning, not the number — and the failure modes repeat. The pitcher cap says it
was `4`, that the screen-cost argument had been retired for the batter cap and never re-derived for
pitchers, and that the comparison favouring `4` ran on a scale counting zero-fills that biased it
against pitcher-heavy boards. Anyone proposing to move it again meets both traps before they step in
one.

### A guard, because one definition is not self-enforcing

Giving the erasable set a single definition did not remove its copies — nothing stopped them existing,
so they went on existing. **A convention nobody can violate by accident is worth more than one everybody
agrees with.**

So: a check that domain constants do not appear as literals outside their module, in the same family as
the AST guard rejecting decisions made by inspecting a label's formatting
(`forge/tests/test_no_label_formatting_decisions.py`), **with its own test proving it fires on a
re-introduced literal.**

Two things such a guard must get right, both learned by getting them wrong:

- **It must not fire on the same digit doing another job.** A check firing on every `6` in the tree
  carries no information and gets ignored — the same outcome as one that never fires. Match the *shape*
  that means the constant: a keyword argument named for it, an **ordering** comparison against a length.
  A width is asked with `==`; a bound is asked with `<=`.
- **Exemptions are listed by path, never by basename.** Exempting `__init__.py` exempts every package
  in the tree. And an instrument whose *published results* were measured at the old value keeps its
  literal — rewriting it would make a recorded number unreproducible and silently reattribute it.

---

## Error Handling & Logging

- Catch specific exceptions only. No bare `except:`. No `except Exception: pass`.
- Chain with `from e` when wrapping. Handle errors at one layer, not multiple.
- **Define a project exception hierarchy** rooted at a single base class. Callers should be able to
  catch the project's errors without catching everything.
- `logging` module only, never `print()`. Lazy formatting: `logger.info("user %s", uid)` — no
  f-strings in log calls. Both enforced by ruff (`T20`, `G`).
- Never log secrets, tokens, or credentials. Sanitize before logging.
- **Log at the boundary, raise in the core.** Library code raises; the entry point logs. Avoid
  log-and-reraise, which produces duplicate stack traces.

---

## Async

- `asyncio.run()` as entry point. Never manage loops manually.
- Prefer `TaskGroup` over `gather()`. Be aware: if one task raises, `TaskGroup` cancels all
  remaining tasks before re-raising — unlike `gather(return_exceptions=True)`, which lets all tasks
  run to completion. Choose accordingly.
- `asyncio.timeout()` on all network calls.
- `asyncio.to_thread()` for blocking I/O. Never call blocking code inside `async def`.
- Re-raise `CancelledError` after cleanup. Use `except*` for `ExceptionGroup`.
- **Async is not the default.** Use it where there is real concurrent I/O. A batch generator that
  runs CPU-bound work on one machine does not need it, and adding it costs testability.

---

## Data Access

- **Parameterized queries only.** No f-strings, no `%`, no `.format()` in SQL. Ever, including in
  throwaway scripts and notebooks.
- Connections and cursors via context managers.
- Long-running batch queries: explicit timeouts, and stream results rather than materializing
  millions of rows.
- Keep SQL out of business logic. Query functions return domain objects, not cursors or raw tuples.

---

## Security & Config

- All secrets via environment variables or `.env`. Never hardcode. Never commit `.env`.
- Validate config at startup with `os.environ["KEY"]` (fails loud) — not deep in call stacks.
  Prefer a single typed settings object built once at boot.
- Don't use `assert` for runtime validation — stripped with `-O`. Use `if`/`raise ValueError`.
- **Verify webhook signatures** on every inbound payment callback, using
  `hmac.compare_digest`. Never `==` for comparing secrets or signatures — it leaks timing.
- `secrets` module for tokens and IDs, never `random`.
- `.gitignore`: `.env`, `__pycache__/`, `*.pyc`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`,
  `htmlcov/`, `.coverage`, `dist/`, and the generated inventory directory.

---

## Dependencies

- **`uv` with `pyproject.toml` and a committed lockfile.** Not a bare `requirements.txt`.
  Unpinned transitive dependencies mean a rebuild on a new machine produces a different
  environment, which defeats disaster recovery and breaks reproducible output.
- Pin the Python version in `.python-version`.
- Adding a dependency is a decision, not a reflex: check maintenance status and whether the stdlib
  already covers it.

---

## Testing

- **TDD workflow (non-negotiable):** for every feature/bugfix, first write a **failing test** that
  specifies the intended behavior, then implement until it passes, then refactor. Reviews should
  show the test alongside or before the implementation.
- **Arrange → Act → Assert**, separated by blank lines.
- Name: `test_<does_what>_when_<condition>`. Group related tests in classes.
- Mock at boundaries (external services, I/O), never internal implementation.
- `AsyncMock` for async functions. Inject dependencies rather than patching globally.
- `pytest.raises(SpecificError, match="...")` for exception tests.
- `@pytest.mark.parametrize` with `ids=` for multiple cases.
- Test error paths, edge cases, and empty inputs — not just the happy path.
- Don't test stdlib behavior: no tests for plain dataclass constructors, frozen immutability,
  `StrEnum` values, or type assignments when the model has no custom logic.
- Never use `==` for float comparison — use `pytest.approx()`.
- Shared fixtures in `conftest.py`. Factory fixtures for test data with variations.
- **Coverage floor: 95%. Target: 100%.** Below 95% is a **stop condition** — halt feature work and
  write the missing tests before continuing. This is not a CI-only gate to be worked around; it is a
  signal that untested code is accumulating and it gets addressed immediately.
- **Branch coverage, not just line coverage.** `branch = true` is set. 95% of lines with no branch
  measurement can still leave half the conditionals unexercised — a nominal 95% that isn't one.
- **Reaching 95%+ is done by excluding what shouldn't be tested, never by writing hollow tests.**
  The rule against testing stdlib behavior still holds. Where code is genuinely not worth testing,
  mark it explicitly:

  ```python
  if TYPE_CHECKING:  # pragma: no cover
  ```

  Every `pragma: no cover` needs a reason, and gets challenged at review the same as a
  `type: ignore`. A file full of pragmas is worse than a low number, because it hides the gap
  instead of showing it.
- `asyncio_mode = "auto"` is set globally — do not add `@pytest.mark.asyncio` to individual tests.
- **Coverage is not in default `addopts`.** It slows every local run and interferes with
  breakpoints. Run it via a separate command in CI.
- **Property-based tests for invariants.** Where a function must preserve a mathematical property
  — an identity balances, a round-trip is lossless, an operation is idempotent — use `hypothesis`.
  Example-based tests confirm the cases you thought of; property tests find the ones you didn't.
  This is the highest-value testing investment for validation and generator code.
- **Golden-file tests for generated artifacts.** Pin known-good output and diff against it. Catches
  accidental format changes that no unit test would notice.

---

## Test scope — the operator decides

**Default: make the change, report it, stop. Do not run tests unprompted.**

The operator often makes several changes in sequence. Validating after the first one is premature by
definition — there are two more coming. Running tests between them wastes the operator's time and
interrupts their train of thought.

**Never run the full test suite unprompted. Not once.**

### Some changes have no tests to run

A background color, a copy tweak, a CSS value, a comment, a log message, a config default. There is
nothing meaningful to validate. Change it, say what changed, and wait for the next instruction.
Running anything here is pure waste.

### When testing is appropriate

- **The operator asks.** "run the tests", "check it", "does it pass"
- **The operator signals they're done:** "that's it", "commit this", "ready", or moves on to a
  different topic
- **TDD on real logic:** when writing behavior in the constraint engine, generator, validator, or
  calendar, the failing test comes first and gets run as part of the red→green cycle. That is the
  loop working as intended, not an interruption.

Even then, prefer targeted runs:

```
pytest tests/test_calendar.py                          # the affected module
pytest tests/test_calendar.py::TestBuild::test_ordering # a single test
pytest -k "idempotence"                                 # by name match
pytest --lf                                             # last failures only
```

### When the operator signals they're done

Then, and only then: run the targeted tests, report what ran and the result, and **ask** whether to
run the full suite.

The full suite runs when the operator asks for it, and in CI on every push — always, automatically,
with coverage. **That is the regression net and it stays intact.** It just doesn't live in the
operator's editing loop.

### Coverage below 95% is a stop condition

When the full suite runs and branch coverage is under 95%, **stop feature work and report it.** Name
the files and lines that are uncovered and write the missing tests before continuing.

Target is 100%; 95% is the floor, not the goal. Do not close the gap with hollow tests — close it
with real tests, or with a justified `pragma: no cover`.

### Flag wide blast radius

If a change touches the constraint engine, the identity definitions, the puzzle schema, or anything
imported across modules, say so and recommend the full suite. The operator still decides, but a
change with wide reach shouldn't pass in silence.

### What this does not change

TDD is unchanged: no feature or bugfix code without a failing test first, and nothing ships
untested. This rule governs **when tests are executed**, not whether they are written.

---

## Version Control

**Git, with a single private repository on GitHub: `boxscorepuzzle`.**

One repository containing `forge/`, `serve/`, and `docs/`. Rationale: one `git push` backs up
everything, which matters when the repository's primary job is being the backup. The separation
between forge and serve is enforced where it actually matters — in deployment and in the import rules
— not by repository boundaries.

**The repository stays private permanently.** `forge/` holds the generator algorithm and the T1–T5
solvability guarantee, the one genuinely hard-to-replicate piece of the product and a trade secret
(§16). Never push any part of it to a public gist, issue, or paste service.

**Deployment ships `serve/` only.** Generator code must never reach the VPS. This is a deployment
configuration concern, not a repository concern.

**No cross-imports between `forge/` and `serve/`.** They share no code. The only thing that crosses
between them is a signed package of validated puzzles.

### Commits

- **Commit messages in English**, like everything else.
- Imperative mood, present tense: `Add uniqueness proof for erasure candidates`, not `Added` or
  `Adding`.
- Subject line under 72 characters. Body when the *why* isn't obvious from the diff — the diff shows
  what changed, the message explains why it needed to.
- **One logical change per commit.** A background color and a solver fix are two commits.
- **Prefix the scope** so a single repository's history stays readable: `forge: add erasure ordering`,
  `serve: fix keypad layout on 375px`, `docs: record calendar freeze rule`.
- Never commit a broken state to `main`.
- **Nothing pushed with a failing test or coverage under 95%.**

### Branches

- `main` is always deployable.
- Work on short-lived branches, named `<type>/<short-description>`: `feat/calendar-builder`,
  `fix/lob-identity-off-by-one`, `chore/bump-ruff`.
- Merge back promptly. A branch alive for weeks is a merge problem being deferred.

### What never enters Git

- `.env` and any secret, token, key, or credential — including in commit history. A secret pushed
  once is compromised even after removal; rotate it, don't just delete it.
- **Generated puzzle inventory.** Thousands of files growing indefinitely, and not code. Ignored
  directory inside `forge/`, transferred to the VPS separately.
- The processed Retrosheet database. Too large, and reproducible from source — see Backup below.
- `__pycache__/`, `*.pyc`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `htmlcov/`,
  `.coverage`, `dist/`, `.venv/`.

**Commit the lockfile.** `uv.lock` is not a build artifact — it is the reproducibility guarantee.

### GitHub configuration

⚠⚠ **This section described a repository that cannot exist on the current plan.** It required branch
protection, a red CI that blocks merge, and a pre-commit gate; none of the three is in place and the
first two are **not available**. GitHub gates branch protection *and* rulesets behind a paid plan for
**private** repositories, and this one is private permanently (§16) because `forge/` holds the generator
and the human-solvability guarantee. Both API calls return `403 Upgrade to GitHub Pro or make this
repository public`.

A normative document prescribing a state the operator cannot reach hides **which check is actually
load-bearing**, which is worse than describing a weaker arrangement honestly. What is true:

- **CI runs on pushes and pull requests to `main`, and is a report, not a gate.** Three workflows on
  Ubuntu: `ci-forge.yml` (ruff, ruff format, the `discovery/` ratchet, mypy strict, the suite),
  `ci-browser.yml` (the browser suite, headless) and `weekly.yml` (all of it, with the coverage floor).
  **Nothing stops a red commit reaching `main`.** `docs/ci.md` explains the split and what it cost.
- **`.githooks/pre-push` is the primary runner, and it is not enabled by default.** Turn it on with
  `git config core.hooksPath .githooks`. It runs everything CI runs, **with coverage**, before a push
  to `main` — which is why the push workflows no longer measure coverage themselves (`docs/ci.md`).
- **`git push --no-verify` skips it**, and that is an acknowledged escape hatch rather than a hole to
  be closed: on one laptop with one developer the hook guards against forgetting, not against intent.
  **It is not branch protection and must not be described as any.**
- **There is no pre-commit hook.** There was never one; the line requiring it described nothing.

**What would change this:** a GitHub Pro plan. The required checks would then be
`forge (ubuntu-latest)`, `forge (windows-latest)` and `browser`.

- Branch protection on `main`: CI must pass before merge. **Not available — see above.**
- **GitHub Actions runs the full suite with coverage on every push.** This is the regression net;
  it does not depend on anyone remembering to run it.
- Path filters so a `serve/` change doesn't run the forge suite and vice versa.
- Dependabot or equivalent enabled for security advisories.
- Secrets in GitHub Actions secrets, never in workflow files.

### Backup — this is load-bearing

§33 identifies the laptop as a single point of failure: if it dies, the pipeline and the ability to
produce puzzles are lost. **GitHub is that backup**, which means pushing is not optional hygiene —
it is the disaster recovery plan. Push at the end of every working session, not when a feature
happens to be finished.

**What GitHub does not cover, and how each is handled:**

| Asset | Coverage |
|---|---|
| Generated puzzle inventory | **The VPS is already a second copy.** Five months stay served even if the laptop dies |
| Processed Retrosheet database | **Not backed up — the loader is.** The database is rebuildable from Retrosheet's original files, so what belongs in Git is a reproducible load script, not the data |

That second row is the design rule: **make the pipeline reproducible rather than backing up its
output.** The backup is the code.

---

## Tooling

```toml
[project]
requires-python = "==3.13.*"

[tool.ruff]
line-length = 120
target-version = "py313"

[tool.ruff.lint]
select = [
    "E", "F", "W",    # pycodestyle, pyflakes
    "I",              # isort
    "N",              # pep8-naming
    "UP",             # pyupgrade — catches legacy typing imports
    "ANN",            # type annotations on public interfaces
    "B",              # bugbear
    "SIM",            # simplify
    "RUF",            # ruff-specific
    "S",              # bandit — security; catches hardcoded secrets, weak hashes, SQL injection
    "T20",            # no print()
    "G",              # no f-strings in logging calls
    "LOG",            # logging misuse
    "TRY",            # exception antipatterns
    "EM",             # exception messages not inline literals
    "RET",            # return simplification — supports "return early"
    "ERA",            # commented-out code
    "DTZ",            # naive datetime — critical for daily rollover correctness
    "PTH",            # pathlib over os.path
    "FBT",            # boolean trap — forces keyword-only booleans
    "C4",             # comprehensions
    "ARG",            # unused arguments
    "PL",             # pylint subset
    "ISC",            # implicit string concat
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "PLR2004"]   # asserts and magic numbers are fine in tests

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --strict-markers --strict-config --tb=short"
asyncio_mode = "auto"
filterwarnings = ["error"]

[tool.coverage.run]
branch = true
source = ["src"]

[tool.coverage.report]
fail_under = 95
show_missing = true
skip_covered = true
exclude_also = [
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "@overload",
]

[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
warn_unreachable = true
enable_error_code = ["ignore-without-code", "redundant-expr", "truthy-bool"]
```

Coverage runs separately:

```
pytest --cov=src --cov-report=term-missing --cov-report=html
```

CI runs the full suite plus coverage on every push.

⚠️ **A red CI does not block anything, and there is no pre-commit hook.** This paragraph used to say
both. See *GitHub configuration* above for what is actually enforced and why the server-side gate is
unavailable: the local `.githooks/pre-push` is the whole of it, it is opt-in, and `--no-verify` skips
it. Keeping the stronger sentence made the document read as a guarantee and left nobody able to say
which check was load-bearing."

---

## Reference

Library-specific patterns and gotchas: see `library-guidelines.md`
