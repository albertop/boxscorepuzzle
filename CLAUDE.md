# boxscorepuzzle

A daily puzzle where the player reconstructs the boxscore of a real Major League game by pure logic. Unique solution, no guessing. Think kakuro, not sudoku.

**Design document: `docs/design-boxscore-puzzle.md`. Read it before proposing architecture or product changes. Section references below (§N) point to it.**

**Engine brief: `docs/serve-brief.md`. Read it before touching `serve/`.** It is the standing direction for the client — one puzzle and three interfaces, a core that knows nothing about screens, phone first — and it is where `serve` decisions get recorded as they are taken, rather than in commit messages.

**Player flow: `docs/serve-flow.md`. Read it with the brief.** The brief says how the engine is shaped; this says **what the game does** — the landing page, what happens on an error, why there are no hints, what the clock counts and when it is visible, what persists and where, the reveal at the end, and what gets measured. It closes the §36 items that had been open for months rather than deciding beside them. ⚠️ **Its §9 is superseded** — the SQLite decision was overturned on 2026-08-22 and the section is now the record of it, not the direction.

**Package format: `docs/package-format-v6.md`, and read it before changing anything either tree
serialises.** ⚠⚠ **It is the only contract between `forge` and `serve`**, which share no code and no
deployment cycle (§33) — a signed package is the one thing that crosses. `forge/tests/verify/test_schema_document.py`
checks it against the code field by field, **keyed off `SCHEMA_VERSION` rather than a typed number**, so
a version bump cannot leave the test asserting the old document.

⚠️ **v1 to v4 are history and are deliberately not checked.** A document tested against code that no
longer produces it has to be edited to stay green, which is how history gets rewritten to match the
present. Each opens with a banner saying so.

⚠️ **This pointer was missing until 2026-08-23**, and the file being unnamed here read as the file not
existing. The other eight standing documents were listed; the contract between the two trees was not.

**Data layer: `docs/data-layer.md`, and its API surface `docs/keep-api.md`. Read both before touching
anything that stores a person.** The service is called **`keep`**. ⚠️ **Every event carries a
client-generated `event_id` made when the event is created, never when it is sent** — a retry after a
lost response would otherwise duplicate a game into the streaks and percentiles, and an id generated per
*attempt* deduplicates nothing while looking like it does. The third
tier, in its own container beside `serve` — accounts, devices, subscriptions and the C7 event records,
behind an interface that hides the engine. It carries the Postgres decision and what overturned the
SQLite one, what `canAccess()` does when the layer is unreachable and why the answer rides in the access
token, the shared-token rule that fails closed at startup, and the four health endpoints — including the
one nobody would think of, because `serve` can be perfectly up with an empty puzzle directory.

⚠️ **Two rules in it are easy to break by accident and expensive to undo.** The board **never** says which cells are wrong or how many — marking makes probing beat deducing, and a count is a binary search over the board. And the stored clock is an **accumulated duration, never a start timestamp**, because the clock pauses when the page is hidden.

**First milestone: `docs/beta-0.md`. Read it to know what counts as done.** The free daily game,
complete, on the VPS, given to friends and family — landing, tutorial, board, check, reveal, share,
persistence, event upload, and **a calendar with real inventory**. No accounts, no Stripe, no archive, no
streaks, no `canAccess()`. ⚠️ **The large piece is the one that has never been run: generation at volume,
calendar construction, signed packaging in bulk** — **five months of inventory, not three** (§33), because
it is the same batch run either way. The calendar carries a guard for *one game, one puzzle* over
everything ever published, which no package and no validation layer can enforce. ⚠️⚠️ **The hand-solve gate
is a gate on beta 0**, not a step before launch: an impossible board does not read as a
fault in the game, it reads as not being good enough, and the person who concludes that leaves without
telling anyone. ⚠️ **And the share has to work perfectly** — it is the only growth mechanism the product
has, and beta 0 is the one chance to test it before a paying product rests on it.

**The route there: `docs/beta-0-plan.md`.** Seven groups, A to G, against the repository as it actually
stands. **It is the authority on progress; the table below is a pointer, not a second copy of it.**

---

## Where the work is — last checked **2026-08-24**

⚠️ **The date is detection, not prevention.** This line read *"design complete at the 'what and why'
level, implementation starting"* long after four groups were built, and a cold session reading it
concluded nothing existed. A date does not stop that happening again; it lets the next reader tell
whether to trust the rest of the row. **Keep it short — a paragraph per group is how it goes stale.**

| | | |
|---|---|---|
| **A** inventory and calendar | ✔ complete | the batch, the calendar, the runbook |
| **B** the hand-solve gate | ▶ B1 and B2 done, **B2 answered: the ladder does not order**; **B3's first half passed — 16/16 solved, none guessed**; ⬜ **B3's stratified sample**, ⬜ B4 | ⚠⚠ **still what blocks beta 0** — three strata almost untested |
| **C** client identity, events, errors | ✔ complete | device id, the C7 record, the upload queue, error reports |
| **D** the data layer | ✔ complete | `keep/`, its own container |
| **E** serving for real | ✔ complete | the two public paths, the routes over them, and the server block; ⤴ E2 folded into E3. ⬜ its untestable half is F's |
| **F** deployment | ✔ **met 2026-08-24** | the three images, the site live over TLS, and the rotation with its own scheduler. `docs/runbook-inventory.md` §5b is the deployment |
| **G** the share | ✔ **met 2026-08-24** | the masked board, the PNG, the sheet, the `POST /shares` record — and **G3: sent through WhatsApp, iMessage and X from a real phone, and it arrived intact**. It was exempt from being cut and it did not have to be |

⚠⚠ **The milestone is waiting on one thing and it is not code.** The hand-solve pack is **the operator's**,
and it is the only verification of human derivability that exists: layer 3 propagates intervals to a fixed
point over forty-odd simultaneous relations, which is stronger than any person, so a board can pass every
check and still be underivable. **One board failing by hand stops everything**, and its N is still open.

⬜ **Also the operator's, and neither blocks E:** B3's N and stratum quotas, and a plausible ceiling on a
client-reported duration (`docs/reviews/todo.md`).

---

## Conventions

**All artifacts are in English. Discussion with the operator is in Spanish.**

The operator explains and reasons in Spanish. Everything committed to the repository is English:
identifiers, comments, docstrings, documentation, commit messages, branch names, log and exception
messages, database table and column names, config keys, and environment variable names.

No mixed-language identifiers (`get_juego`, `calendario_builder`). No Spanish comments on English
code. Where a domain term needs care, use the English baseball term — the vocabulary is already
English.

The UI ships in English. **Spanish is a nice-to-have, not a must-have** (§13) — it can slip without
affecting launch. ⚠️ **The payments decision now rests on the same premise** (§10, 2026-08-22: Stripe
rather than a merchant of record, because the audience is US baseball fans). An argument for a Caribbean
market would have to move both or neither; they are not independent any more. But **seam C11 is mandatory regardless: zero user-facing strings in code.** All copy
goes through the string catalog from day one, including generated reveal text and metadata. Cheap now,
expensive to retrofit.

---

## Never suggest stopping

**Do not propose pausing, stopping for the day, continuing tomorrow, or deferring work to a later
session. Not once, in any form.**

This includes the softened versions: "this is substantial, I'd rather not start it half-finished",
"the session is getting long", "better to pick this up fresh", "shall we leave it here". All of it.

**The operator decides when work stops.** Nobody else raises the question.

If a task genuinely cannot be completed correctly in one pass — a boundary that would be worse
half-built than absent, a migration that must be atomic — **say what the constraint is and let the
operator decide.** State the technical fact: "an incomplete `certify_for_publication()` looks like a
gate and isn't one." That is a fact about the work. "Let's do it tomorrow" is a decision about the
operator's time, and it is not yours to make or to suggest.

The same applies to reading a stop into what someone else said. If another party says they would
rather not start something, that is their report, not a decision — do not relay it as one.

---

## Test scope — the operator decides

**Default: make the change, report it, stop. Do not run tests unprompted. Never run the full suite
unprompted.**

The operator often makes several changes in sequence. Validating after the first one is premature —
there are two more coming. Running tests between them interrupts their work.

**Some changes have nothing to validate:** a background color, a copy tweak, a CSS value, a comment,
a log message, a config default. Change it, say what changed, wait for the next instruction.

**Run tests when:**

- The operator asks ("run the tests", "check it", "does it pass")
- The operator signals they're done ("that's it", "commit this", "ready") or changes topic
- TDD on real logic — the failing test comes first in the red→green cycle for the constraint engine,
  generator, validator, or calendar. That loop is intended, not an interruption.

Prefer targeted runs: the affected module, a single test, `-k` by name, `--lf`.

When the operator signals they're done: run the targeted tests, report what ran and the result, then
**ask** whether to run the full suite.

**Flag wide blast radius.** If a change touches the constraint engine, the identity definitions, the
puzzle schema, or anything imported across modules, say so and recommend the full suite. The
operator still decides.

This governs **when tests execute**, not whether they're written. TDD is unchanged; CI runs the full
suite with coverage on every push.

**Coverage floor: 95% branch coverage. Target: 100%.** When the full suite runs and coverage is under
95%, that is a **stop condition** — halt feature work, report which files and lines are uncovered,
and write the missing tests before continuing. Close the gap with real tests or a justified
`pragma: no cover`, never with hollow tests written to move the number.

Full Python style, typing, testing, and tooling rules: `docs/python-conventions.md`.

**Read its *Constants* section before writing a number that encodes a decision.** A value that carries
a domain decision or a presentation budget lives in one module and is never spelled anywhere else —
domain constants in `forge/src/boxscore_domain/`, presentation constants in `serve/ui/phone/tokens.css`,
**never one module shared**, because §33 is exactly the boundary a shared one would break. Each records
the reason it holds that value, the measurement that set it with the figures, and whether it is
**provisional**; a superseded value and why it was wrong stay in the comment rather than in a commit
message. A guard enforces it — the convention is not left to memory, because giving the erasable set
one definition did not stop its copies existing.

---

## Repository layout

```
boxscorepuzzle/
├── CLAUDE.md
├── docs/
├── forge/     ← generator, cwbox, SQL, validation, calendar (never leaves the laptop)
├── serve/     ← the client: browser engine, phone UI, static packages (deploys to VPS)
├── publish/   ← the serving side's executables: the daily rotation (deploys to VPS)
├── deploy/    ← what the VPS needs and cannot run: the nginx server block (deploys to VPS)
└── keep/      ← the data layer: devices, events, later accounts (deploys to VPS, port unpublished)
```

⚠⚠ **`deploy/` arrived 2026-08-24 with E3's server block, and neither of the two obvious homes works.**
Not `serve/`: that is the **served root**, so a configuration file inside it is a configuration file nginx
hands to anybody who asks for it — the same argument that keeps `tools/dev_server.py` out of it. Not
`publish/`: that tree is *the serving side's **executables***, and a config is not one. Stretching that
sentence to cover it is the exact trap `publish/`'s own creation recorded — **a sentence that stays true
by wording while changing in substance is worse than one that visibly needs rewriting.**

⚠️ **It holds nothing executable and has no package**, so there is no fifth CI workflow: what checks it
is `forge/tests/test_nginx_serves_what_is_declared.py`, which starts the config over `serve/` in a
container and compares it against the two tables that declare what it must do.

**A single private Git repository on GitHub: `boxscorepuzzle`.** One push backs up everything, which
matters because the repository's primary job is being the backup.

**The repository stays private permanently** — `forge/` holds the generator algorithm and the
human-solvability guarantee, which is trade secret (§16). Never push any part of it to a public gist,
issue, or paste service.

**No cross-imports between `forge/`, `serve/`, `publish/` and `keep/`.** ⚠️ **Four code trees**, and
the rule that kept two apart is what keeps four apart: they share no code and no deployment cycle.
`deploy/` is a fifth directory and holds **no code at all**, which is why the rule names four — there is
nothing in it to import.

⚠⚠ **`publish/` arrived 2026-08-23 and it is the serving side's executables** — the daily rotation now,
the health endpoints at F3, the archive endpoint at beta 3, and the ingest step `serve/data/README.md`
already anticipates. **It is a sibling rather than a directory inside `serve/`**, and the deciding
argument is worth keeping: inside `serve/`, the sentence *deployment ships `serve/` only* would have
survived by wording while its meaning changed silently from *static assets* to *assets plus a service*.
As a sibling it becomes visibly false and has to be rewritten. **A sentence that stays true by wording
while changing in substance is worse than one that visibly needs rewriting.**

⚠️ **The relationship it needs is the one `forge` already has**: `write_reference_puzzles.py` writes
packages into `serve/data/puzzles/` from outside `serve/` and never needed to live inside it. §33
forbids cross-*imports*; the only thing that crosses is a signed package, which is what §33 permits. `keep` has **no
runtime dependency — the PostgreSQL driver** — three routes, no ORM, no framework, no templating and no
cross-import from the other trees — and `forge` never learns that users exist (§33).

⚠️ **This said *no runtime dependencies at all* until 2026-08-24, and F1 made it false.** `psycopg` moved
out of the development group because `keep` cannot start without a database, which is the classification
that had already produced a container unable to import its own driver. **Leaving the old claim in the
guide invites the cleanup in reverse** — somebody moves it back because the guide says no runtime package
belongs there. v41-P3-01. They share no code and no deployment cycle. The
only thing that crosses is a signed package of validated puzzles.

### ⚠️⚠️ What deployment ships — **split rather than rewritten, because half of it never expired**

**Permanent, and the reason §33 exists: `forge/` must never reach the VPS.** It holds the generator and
the human-solvability guarantee, which is trade secret (§16). No image, no build stage, no runbook step
copies it — not for a lockfile, not for a shared module, not for convenience. **That half is unchanged
and is not up for discussion.**

**Expired 2026-08-24: *deployment ships `serve/` only*.** It was true when `serve/` was the only thing
there was, and **three directories reach the VPS now**:

| | what it is | why it goes |
|---|---|---|
| `serve/` | the client and the two public packages | it is the site |
| `publish/` | the daily rotation and the health verdict | the rotation runs *there*; a job on the laptop cannot rotate a VPS |
| `deploy/` | the nginx template and the two Dockerfiles | the server block describes how `serve/` is served |

⚠️ **`publish/` and `deploy/` are not a softening of the rule.** Neither is the generator, neither holds
a private key, and neither can produce a puzzle. **What the rule protects is the generator**, and it is
exactly as protected as it was.

⚠️⚠️ **The old sentence was kept unedited for a day on purpose and that was the right call.**
`docs/beta-0-plan.md` F1.5 recorded it as landing with F, because editing it earlier would have described
a deployment that did not exist — and §5 of the runbook has already reintroduced the archive hole once by
being followed literally. **A sentence that is false in a document people follow is worse than one marked
as owed.** This is F, so it is now split rather than left marked.

**Generated puzzle inventory never goes in Git.** It lives in an ignored folder inside `forge/`.

⚠️⚠️ **The calendar is the exception, and it is committed.** `docs/calendar.md` carries the reasoning; the
short version is that the rule above exists for packages — large, secret (§16), and **reproducible from
the game**. §21 makes the date → puzzle assignment *fixed and never recomputed*, which means there is
nothing to recompute it from: **it is the one artefact in this project that cannot be regenerated**, and
§33 names Git as the backup for a laptop that is a single point of failure. Losing it loses every past
date's assignment, which is what streaks, shared results and stats hang from. A puzzle id is a hash and
names nothing without its package.

Commit messages in English, imperative mood, one logical change per commit, prefixed with scope
(`forge:`, `serve:`, `docs:`). `main` always deployable. Nothing pushed with a failing test or
coverage under 95%. Commit `uv.lock` — it is the reproducibility guarantee, not a build artifact.

### ⚠️⚠️ CI runs. `main` is **not** protected, and this paragraph used to say it was.

**CI exists now, in three workflows, and `docs/ci.md` is where the whole arrangement is explained** —
what runs where, what each decision cost, and what would reverse it. Do not re-derive it here or
anywhere else. The short version:

| `.github/workflows/` | when | what |
|---|---|---|
| `ci-forge.yml` | push and PR to `main`, unless only `serve/` or documents changed | ruff, ruff format, the `discovery/` ratchet, mypy strict, the suite **without coverage** |
| `ci-browser.yml` | push and PR to `main`, unless only `forge/`, `discovery/` or documents changed | the browser suite, headless |
| `weekly.yml` | Monday 06:00 UTC, and by hand | all of it, **with the 95% coverage floor** |

**Ubuntu only since 2026-08-22** — Windows was 39% of the Actions bill and the platform it covered is
the laptop, which runs the whole suite through the hook before every push. The cp1252 class it existed
for is guarded by `test_reports_survive_a_redirected_stream.py`, a static check over every `print`
argument that runs anywhere, and that is what caught the two instances of it that appeared the same
day.

⚠️⚠️ **The hook is the primary runner and CI is the safety net — the reversal is deliberate.** One
developer, one machine: the hook runs everything with coverage before a push reaches `main`, so a full
CI run per push was re-executing a result already in hand, at roughly twice the free allowance. What CI
still buys is the thing the laptop cannot test — **a `--frozen` install from nothing**, where the warm
venv of months cannot fail — plus pull requests, a record, and the weekly run, which answers the one
question the hook cannot ask about itself.

⚠️ **The argument that CI must be primary because `--no-verify` exists was mine and it was wrong.** It
assumed a team. Here the "somebody" who bypasses the hook is the operator, and he can ignore a red badge
just as easily since nothing gates on it — *a justification is scoped, and it does not travel*.

**Branch protection does not and cannot exist on this repository.** GitHub gates branch protection
*and* rulesets behind a paid plan for **private** repositories, and this repository is private
permanently (§16) because `forge/` holds the generator and the human-solvability guarantee. Both API
calls return `403 Upgrade to GitHub Pro or make this repository public`. The two ways out are a paid
plan or publishing the repository, and the second one is not available.

So **CI is a report, not a gate**: nothing stops a red commit reaching `main`. Two things follow, and
they are not optional.

⚠️⚠️ **Re-checked on 2026-08-22 rather than taken from this paragraph, and both endpoints still refuse.**
`branches/main/protection` and `rulesets` each answer `403 Upgrade to GitHub Pro or make this repository
public`. The account is on the free plan and the repository is private permanently. **Nothing has
changed and nothing can be set.**

⚠️ **And CI narrowed on the same day, which moves where the gap is.** It runs on pushes to `main` and on
pull requests only — not on every push to every branch. So on a working branch **the hook is the only
check there is**, and `--no-verify` leaves that code unlooked-at until it reaches `main`.

**On `main` itself the position is better than it sounds and worse than a gate.** A `--no-verify` push
to `main` still triggers CI, so it is *seen* — the badge goes red — and it is not *stopped*. **Detection
without prevention**, which is the whole of what a free private repository allows. The difference
matters when reasoning about it: the failure mode is a red `main` nobody has looked at yet, not an
unchecked commit nobody can ever discover.

⚠️ **A step-level `if` does not save Actions minutes**, and it is the obvious wrong turn from here. The
runner starts, checks out and installs before it reaches the condition, so a skipped *step* bills the
same as a run one. Only a skipped **job** or a skipped **workflow** saves anything — which is why the
saving lives in `paths-ignore` at the trigger. Splitting `forge` and `browser` into jobs with their own
`paths` would save more; it is a restructure and is deliberately not done here.

⚠️ **This section is the correction, not the claim.** For every commit until now this paragraph read
*"`main` always deployable, protected, CI must pass"* and none of the three was enforced by anything —
there was no `.github/` directory at all. **The document that defines this project's rules was
asserting a guarantee it did not have**, which is the exact shape being closed in the code all week,
sitting in the file the rules come from. A rule stated in the place people go to learn the rules is
the worst place for one that is false.

⚠️ **`.githooks/pre-push` is the nearest available thing and is deliberately not called protection.**
It runs what CI runs, before a push to `main`, on the laptop. Enable it with
`git config core.hooksPath .githooks`. It guards against forgetting and not against intent:
`git push --no-verify` skips it, it cannot see what the other platform would find, and it is one
machine checking itself. **Do not let it be described as branch protection anywhere**, including here.

**What would change this:** a GitHub Pro plan on the account. If that happens, the required checks are
`forge (ubuntu-latest)`, `forge (windows-latest)` and `browser`, and this section gets rewritten to
say what is then true.

**Pushing is the disaster recovery plan**, not just hygiene: §33 identifies the laptop as a single
point of failure and GitHub is the backup. Push at the end of every session. The processed Retrosheet
database is not backed up — **the loader script is**, so keep the load process reproducible from
Retrosheet's original files.

---

## The failure mode this project actually has

Every serious defect found so far has been the same shape: **two places that should say the same thing,
saying different things — with nothing checking that they agree.** Not a logic error, not a bad
algorithm. An implicit contract nobody validated.

The record:

| What happened | The two places |
|---|---|
| Deduced event files loaded unmarked | The download wildcard `<season>*.E??` and the intent to load only `.EV?` |
| Phantom batting rows on the board | `B_G = 1` meaning "appeared" and the code assuming "batted" |
| Pinch runner's run deleted | The shape query's "contributed anything" and the row query's `PA > 0` |
| Board totals still balanced while wrong | The loader summing its own totals instead of an independent source |
| CI abbreviation wrong for weeks | A term adopted in conversation and never checked against baseball notation |
| Watchdog slept eight hours | A grep for `"hardest day"` against a file saying `HARDEST DAY` |
| Three hours of compute lost | A patched script never parsed, and a driver that ignored a non-zero exit |
| **1,015 major-league games missing from the pool for months** | **Retrosheet's own two names for one club** — the 1955–67 Athletics are `KC1` in event files and `OAK` in game logs, so a `GAME_ID` built from the home club differs between tables and the join finds no partner |

**None of these break an identity.** That is why four validation layers caught none of them.

⚠️⚠️ **The last one is the shape at its purest and it is worth the extra line: neither side is wrong.**
`retroGamesReg` is right that the club is `KC1`; `retroGameLogs` is right that the franchise is `OAK`.
Every row in both tables is correct, every count is plausible, and **the only symptom is a join that
quietly returns fewer rows than it should** — 1,029 games, a fifth of a season of inventory, absent from
the pool by nobody's decision. **It was found by asking why an exclusion had a suspiciously round
count**, not by any check. *Two places that should say the same thing* does not require either place to
be mistaken.

### The rules that follow

**Validate correspondence, not only consistency.** A fabricated board and a real one both balance. Every
check that only asks "do the numbers agree with each other" is blind to the entire class of error above.
Cross-check against an **independent source** — the game log, not `retroDailyReg` again.

**One predicate, one place.** If two queries, two modules, or two documents encode the same rule, they
will drift. Share the definition or assert they agree; do not maintain two copies and hope.

**A check that never fires is indistinguishable from a check that is broken.** **And a rule applied
outward does not automatically apply inward.** Two guards written in the same session that recorded
this rule do not fire: a parameterised test calls `_position` with three arguments, so the branch it
was written to protect never runs, and a "these two agree" test assigns both names from one
expression, staying green if either consumer stops calling the helper at all. The failure is not that
the rule was unknown — it was being applied to other people's code the same day. **Check your own
guard by asking what change it would let through**, not by rereading what it asserts. Test the failing case. A
threshold set by eye that rejects real data gets loosened until it says nothing, which is worse than not
having it — it gives false confidence.

**Any comparison between configurations states, in the script and at the point of comparison, how it
keeps the ordering stable — or it does not run.** Twice in one day a comparison filtered its candidate
list and then ordered what was left, so the configurations differed in trajectory as well as in
treatment. The second time, the fix was written down in the same file where the finding was recorded.
That is not ignorance: **a lesson filed as something to apply going forward is not a check performed
while writing the next comparison.** And note what unanimity is worth here — if one configuration's
ordering is systematically worse, every item moves the same way, so a 47-of-47 result is consistent
with the confound rather than evidence against it.

**A confound has no signature in the results, so looking at the output cannot catch it.** Every other
defect recorded here was found by rendering something and reading it — the zero-heavy board, the
phantom rows, the wrong club, the mislabelled positions. A confound is different in kind: a ladder
whose rungs mix boards with very different headroom varies two things at once, and its report reads
**exactly as clean as one that varies only the intended thing**. No number in the output distinguishes
them. **It can only be prevented while the instrument is being designed** — by asking, before building,
what else changes when the variable changes. Looking harder afterwards is not a weaker version of this
check; it is not the same check at all.

**A chain of measurements has to end at a decision, not at the next question.** Several runs in a row
each opened the one after it, and every one was justified on its own — which is exactly why the chain
is hard to see from inside it. The discipline is not doubting any single measurement. It is asking,
**before starting one, what would be built differently depending on the result**. If the answer is
"nothing", it does not run. Some open questions will keep imperfect numbers, and that is the correct
state to build in.

**A metric can be correctly computed and still measure something the player never encounters.** Every
other measurement defect recorded here was a *broken* instrument — a metric that could not vary, a
baseline that removed what it was testing, a denominator chosen by a heading string. This one was a
**working instrument pointed at the wrong thing**, and that is a different failure with a different cure.

The footnote cells were opened because a measurement said they took the median board from 5 stalls to
15. They did — the solver deduced every erased footnote value, correctly, and recorded each as a step.
But when `HBP`, `SF`, `SH` and `CI` are all zero for a batter the row identity is `PA = AB + BB`: those
terms contribute nothing *because they did not happen*. On the reference fixture **35 of 36 footnote
cells are zero**. The solver stalled sixteen times filling in zeros; a person never met one.

**It was found by a human solving a board and noticing the numbers did not match his experience** — a
19-stall board that was hard with the footnotes visible, which meant the difficulty was there without
them. No test could have caught it: the solver was working, the values were genuinely unknown to it, and
the arithmetic was right. The check that exists for this is not a test. **It is asking, of every metric,
what the player does when the number goes up** — and if the answer is "types a zero", the metric is
measuring the board rather than the game.

⚠️ **And the correction is a correction, not a new result.** The earlier figures were not noisy. They
were counting the wrong thing, and everything derived from them inherits the error: the stall ceiling
and its 27% convergence, the coverage percentages, the 5-versus-15 gap, the ladder's rungs, and the
blanks per target. **The pool run closed it.** Coverage with the cells erasable and with them given is
the same at every target; pair by pair the two are identical on every field in 91% of trials, and the
rest differ only in the blank count. **96% of the pool's footnote terms are zero.** The cells are given
again, and everything built for the open case — the cell drawing, the per-board cap, the large-group
constraint, the erased-attribution design — was **deleted rather than disabled**.

⚠️ **The check that would have caught it is the one that did.** Not a test, not a review: a person doing
the task and comparing the feeling against the number. It survived several reviews because nothing about
it was wrong — so **for every metric, ask what the player does when the number goes up.** If the answer
is "types a zero", the metric is measuring the board rather than the game.

**⚠️⚠️ An instrument can measure its own output instead of the thing it is pointed at, and nothing about
it is broken.** This is finer than every shape above, and it survived a full pass of checks.

The reveal was rebuilt as a printed boxscore and inspected two ways. The numeric checks asked the
browser the right questions — is any cell's `scrollWidth` past its `clientWidth`, does any table
overflow its box, does the document scroll sideways — and answered **no clipped cell, no horizontal
overflow, on six packages at 375px and at 320px**. All true. Then a text dump of the same panel was
printed to read by eye, and it looked like a boxscore.

**It looked like a boxscore because the dump was padding the columns itself.** `padEnd(23)` and
`padStart(5)`, written to make the text line up in a terminal. The page had `padding: 1px 0` on every
numeric cell and no horizontal separation at all, so a row of single digits rendered as `40 1` — four
at-bats, no runs, one hit, printed as forty-and-one. And `.clipping-grid td` out-specifies a bare
`.clipping-who`, so every name in the boxscore sat flush against the at-bats column. **The sheet was
unreadable and both instruments said it was fine**, because one was asking about overflow — which
there was none of — and the other was supplying the very property under test.

**The distinguishing feature: the instrument was correct.** The width checks were reading the real
DOM, in the real browser, at the real viewport, and their answers were true. The dump was reading the
real DOM too. Neither was a metric that could not vary, a baseline that removed what it was testing, a
denominator chosen by a heading string, or a working instrument aimed at the wrong question. It was a
working instrument aimed at the **right** question, whose *rendering* of the answer replaced the
property being judged.

**The check that exists for this: ask what the instrument adds.** Before trusting a rendered sample,
name every property of the output that the *harness* is supplying rather than the system — spacing,
alignment, ordering, colour, truncation. Each one is invisible to that sample by construction. If the
property under judgement is on the list, the sample cannot judge it, however carefully it is read.

⚠️ **And the corollary, which is the cheap version: a screenshot is not a slower text dump.** Both
defects were obvious in the first screenshot taken and neither was visible in any number or any dump
produced before it. `computer{action:"screenshot"}` is the instrument that adds nothing. **Any change
to how something looks is verified with a picture of it**, not with an assertion about it and not with
text assembled from it — and that is a step, not a habit.

**⚠️⚠️ A test that asserts a response's bytes has not asked whether the page works.** `/p/<id>` shipped
as a blank screen and the route test passed on it, every run, because it compared the served bytes
against `play.html` and they matched **exactly, always, by construction of the rewrite.** The assertion
was true and the page was dead: `main.js` was named relatively, resolved to `/p/main.js`, and the prefix
rewrite answered *that* with `play.html` too — so the browser was handed HTML where it asked for a
module, refused it on MIME, and drew an empty `#app` with no stylesheet.

**The question it should have asked is what the artefact needs in order to function**, not what it is
made of. For a page that is: *does everything this page names resolve, from the address the player is
at?* The test reads the modules and stylesheets out of the served HTML now and requires each to answer
200 with something that is not markup. **`serves the right bytes` and `works here` are different
properties, and only one of them is what the URL is for.**

**⚠️⚠️ And the fix that was half-applied is the other half of the lesson.** `daily.js`'s data path was
made absolute at E1 **for exactly this reason** — the board page is served at two addresses, so a
relative path depends on which one — and **the HTML was not carried with it.** Two things named files;
one was repaired.

**That is the family the five constructor guards belong to**, where the sixth field was missed and
shipped a package the forge's own reader refuses. The repair is correct, the reasoning is written down,
and it is applied to the instance in hand rather than to the *set*. **When a fix is about a category —
things that name files, fields checked on construction, callers of a renamed symbol — enumerate the
category before closing it**, and put the enumeration in the commit rather than in the intention.

⚠️ **One instance found by accident means the class was never swept**, and the sweep found a second
immediately: `ROUTES` held `play.html`, `index.html`, `tutorial.html`. Linked from `/`, those resolve to
`/play.html` and `/tutorial.html` — **both landing buttons dead, on the address every visit lands at**,
and the tutorial had no production URL at all. ⚠️⚠️ **The test that checked them fetched
`../ui/phone/${file}`, prefixing the directory whose absence was the defect** — an instrument supplying
the property under judgement, which is the padded text dump one more time.

### ⚠️⚠️ The near-neighbour class is **not mechanically detectable**, and that is the finding

Three instances in one day, all written by somebody who had just recorded the rule twice: a test
comparing a response's bytes and never asking whether the page worked; a fetch that supplied the
directory whose absence *was* the defect; a readiness probe asking whether the port was open rather than
whether nginx answered.

**They share one shape.** Each asserts a property **P** when the property that matters is **Q**, where P
is *necessary but not sufficient* — and **P is true in the broken state.** The bytes matched while the
board was dead; the file existed while the link was dead; the socket accepted while nginx answered
nothing.

**Detecting that requires knowing Q, and Q is intent.** No analysis derives it from the code: a test
asserting a necessary condition is indistinguishable from one asserting the right condition, because
*being sufficient* is not a property of the text. **So there is no check to write, and saying so is
worth more than a check that passes forever.** What follows are the three things that do work, and each
one names what it cannot do.

**⚠️⚠️ A new test is not finished until it has been seen red for the reason it exists.** Not *consider
whether it could fail* — **break the thing and watch it go red**, then say in the test what was broken.

**The evidence is one day's worth and it is one-sided.** The guards that held were the ones broken on
purpose first: the workflow deleted and nothing turned red, the delete removed to see which case
noticed, the config broken four ways and each failure named. The three that failed were the three
believed without being broken.

⚠️ **Nothing enforces this and it is written as an action for that reason.** A question on a checklist is
answered by the person who already believes the answer; a step that produces a red run either happened
or did not. **It is still a discipline, not a gate** — the honest statement is that this class is caught
by doing that, or it is not caught.

**⚠️ A wait loop's success condition is a real request to the thing the caller actually needs.**
Instruction-shaped, with nothing to decide: if code waits for a service, it waits for **that** service to
*answer*.

⚠⚠ **The second half was added after the rule was broken by the code written to demonstrate it.** A
fixture starting nginx and `keep` waited for **nginx** — which answers a static file the instant it
starts — and the first request into `keep` met a data layer that was not listening yet. **Green in
isolation, red in the full run**, and the hook is what caught it. *Waiting for a service* was satisfied
by waiting for the wrong one, which is the near-neighbour shape one level in.

**That is four instances in one day**, the last inside the fix for the third. **Knowing the rule does not
apply it** — this file has said so since the fourth regex, and the evidence keeps arriving. Docker's port
forwarder binds before the container accepts and then resets what it accepted, so a connect proves the
forwarder is up and nothing else.

⚠️⚠️ **And there is no static rule to be had here, which is worth stating because the rule looks
obvious.** `forge/tests/test_dev_server_routes.py` waited on a socket and was **correct** — a plain
Python server binds and starts accepting with nothing in between. A check on the pattern would fire on
that, and a threshold that rejects real data gets loosened until it says nothing. *(The instance was
changed anyway: `compose.yaml` exists, and the day that suite runs against a containerised dev server it
breaks the same way. Fixing the instance is not the same as having a rule.)*

**⚠️ One narrow guard exists and it is the only part of this that can fail.** No served HTML names an
asset relatively, and no `ROUTES` value is a filename — static, decidable, and **proved to fire**: with
the filenames restored, the nginx test reports *the client links to play.html and nginx answers 400*.
**It covers two instances and not the class**, and it is written down that way so nobody reads it as the
class being closed.

**⚠️ Automated mutation testing is rejected for this, and the reason is specific rather than general.**
Today's three mutations were **HTML, a data literal and a startup condition**. No mutation tool
generates any of them — they operate on expressions and operators in source. It would run, report
coverage, and have caught none of the three: work with the appearance of coverage.

### ⚠️⚠️ A validator reports on the subject it was given, and cannot tell you it was given the wrong one

**Three times in a row, in ten minutes, `nginx -t` printed *configuration file test is successful* about
a config that was not under test.** Three different mechanisms, one shape:

| | what was actually validated |
|---|---|
| the edit script raised before writing, so the template did not exist | the stock config that ships in the image |
| `docker run -v` with a missing source **created a directory** where a file was meant | the stock config again |
| a custom command (`sh -c`) meant the image's entrypoint never ran, so the template was never substituted into `conf.d/` | the stock config a third time |

**`nginx -t` cannot distinguish *this config is valid* from *I validated a different config*, and neither
can most tools of that shape** — a type checker given no files, a test run that collected nothing, a
linter pointed at a directory that does not exist. **They report on their subject, and the subject being
absent is not something they are built to notice.** Every one of them says the same thing about an empty
input as about a clean one.

**⚠️⚠️ What caught all three was reading the output rather than the exit code.** The status was 0 every
time. What did not add up was *what the output said*: a substituted `Authorization` line that was not
there, a `ls` showing `conf.d/default.conf` at 1072 bytes and dated months earlier, a `grep` for a token
returning nothing. **The exit code was true and useless.**

**⚠️ That is the third shape of this kind in one day and the repetition is the finding, not the
instances.** A `| tail` swallowing a non-zero exit; a `; echo EXIT=$?` reporting the echo's status; and
now a validator reporting on nothing. **The common rule: an exit code answers *did this command finish*,
never *did it do the thing you wanted*.** For anything whose job is to check something, **read what it
says about the subject and confirm the subject was there** — a byte count, a filename, a line that
should have changed.

**⚠️⚠️ Nothing stopped a fourth, and for the general case there is still no check to write.** The same
argument as the near-neighbour class above: knowing whether a tool was pointed at the right subject
requires knowing what the right subject was, which is intent. What exists is the habit of asking a
verifier for something it can only produce from the real subject — *print the line that should have
changed* — and that is a discipline rather than a gate.

⚠️ **This paragraph said *there is no check to write* full stop, and the fourth instance produced one for
a narrow slice of it.** The slice is below. The general claim stands; the sentence that implied nothing
could ever be written did not.

### ⚠️⚠️ A file can be written successfully and contain the tool's own error page

**`serve/favicon.svg` was 98 bytes of Chromium's XML parse-error screen, rasterised.** The comment
block held em dashes written as `--`, which XML forbids inside a comment, so the browser refused the
file and rendered *This page contains the following errors* — and the rasteriser screenshotted **that**,
saved it as an icon, and reported `wrote favicon.ico (98 bytes)`.

**Every signal was green.** The write succeeded. The exit code was zero. 98 bytes is small but an icon
is small. **The only thing that said anything was opening the picture**, where the error page was in
plain red text.

⚠️ **It is the family this section is about, one level further in.** `nginx -t` reported on a config it
was never given; `gh run list` reported on a commit it never matched; this reported on a document that
was an error message. **In all three the tool did exactly what it was asked and could not say the
subject was broken** — and here the subject was broken *by the file's own comments*, which no schema, no
linter and no size check would look at.

⚠️ **What caught it is the standing rule and not a new one:** *any change to how something looks is
verified with a picture of it.* The picture was taken because the rule says to take it, not because
anything looked wrong.

### ⚠️⚠️ The fourth arrived the same day, and this one DOES have a check

**`gh run list --commit 7cc0518` returns nothing.** Not an error, not a warning, not a non-zero exit —
an empty list, because `--commit` wants the full forty-character SHA and silently matches nothing on a
short one. A watcher built on it polled for twenty minutes and would have reported **"still running"
about four workflows that had been green the whole time.**

**That is the same family as the three `nginx -t` approvals — a tool reporting on a subject it was never
given — with one new wrinkle worth naming separately:**

> **An empty result and a genuine "nothing matched" are the same bytes, and the tool does not say
> which.** A filter that matches nothing, a glob over a mistyped directory, a `--jq` selecting an absent
> field, a database query with a stale id: every one returns an empty set that reads as a finding.

⚠️⚠️ **So the check exists here, and it is narrow and mechanical**, which is what distinguishes it from
the "no check to write" above:

> **Any query used as a status check must assert it found something.**

Not *look at whether it found something* — assert it, so the empty case fails loudly instead of being
interpreted. `forge/tests/test_hand_solve_keys_are_ignored.py::test_the_sweep_finds_keys_to_check` is
what it looks like: before asking whether every key is ignored, it asserts there are keys.

⚠️ **And the timing is the finding, not the instance.** That test was written **one hour before** the
watcher, by the same author, and its docstring says in as many words that a check over an empty set
passes forever. **Knowing the rule does not apply it** — this file has said so since the fourth regex,
and today it earned the sentence twice more. What separates the guard that held from the watcher that
did not is that one was written as a test and the other as a throwaway one-liner. **The discipline is
that the assertion goes in by default, including in code that will be deleted in an hour.**

⚠️ **The residual is unchanged and is worth restating so this does not read as the class being closed.**
This covers a query *used as a status check*, which is decidable by looking at what the result is used
for. It does not cover the general case — whether a tool was pointed at the right subject is still
intent, and still not derivable from the code.

**Look at the output.** Every serious defect in this project was found by rendering something and
reading it, never by computing a statistic. **Twice now this has been the only thing that
could have worked.** The first was a board carrying rows of noughts, from a flag meaning *appeared*
rather than *batted*. The second was a lineup with three centre fielders — the row labels came from
"played here at some point" flags resolved by a fixed priority, so a pinch hitter who took the field
became a fielder and three men who each spent an inning there became `CF-1`, `CF-2`, `CF-3`. Both
balanced perfectly. Both passed all four layers. Both were found by a person reading a printed page.
**A label sits outside the arithmetic, which is exactly why nothing arithmetic can check it** — and
when a footnote is attributed to a mislabelled row, the arithmetic breaks somewhere the column totals
still agree. **Any measurement producing a distribution must also produce
a handful of rendered examples, checked by eye before the numbers are trusted.** Make it a step, not a
habit.

**Fail closed at boundaries.** Verification that passes when its secret is missing, parsing that accepts
malformed input and dies later, a driver that reports COMPLETE on a non-zero exit — all the same defect:
the absence of a check reading as the presence of a passing one.

**⚠️⚠️ A comment can assert a property nothing establishes, and it reads exactly like one that does.**
This is the cheapest defect in the register to create and among the hardest to see, because the reviewer
reads the sentence and the sentence is reasonable.

`deploy/publish.Dockerfile` said the published path was *"mounted writable and owned by this uid"*. **No
line anywhere made it so.** Docker takes a new named volume's ownership from the image that first
populates it — `serve` — and `serve` left it root-owned, so the rotation died with `PermissionError` the
first time it ran. **The comment was written three files away from this register's own warning about
claims nothing checks**, by somebody who had recorded that warning the same afternoon.

⚠️ **Reading either Dockerfile could not have found it**, and that is what separates this from an
ordinary oversight: each file is internally consistent and neither states the other's half. **Running the
rotation found it in one attempt.**

**What closes it here is a guard, because the fact lives in two files:** a uid spelled in two Dockerfiles
is two places encoding one thing. `forge/tests/test_the_images_build.py` asserts they agree, and it was
**seen red both ways** — the numbers made to differ, and the `chown` removed entirely, each naming what
it found. ⚠️ The guard covers this instance, not the class: *a comment claiming what nothing establishes*
is not decidable from the text, for the same reason the near-neighbour class is not.

**⚠️⚠️ A contract between two images that are pushed separately has no safe order, only a window.** A
package schema is one: §33 gives `forge` and `serve` no shared code and no shared deployment cycle, so
the client's `READABLE` and the packages' `schema` are two spellings in two images. **Push either one
alone and every board dies** — the reader refuses its own site's packages, in whichever direction the
mismatch runs.

⚠️ **The repository can be perfectly consistent while the VPS is one image behind**, and on 2026-08-24 it
was: schema 6 in the tree, schema 5 served by a client reading 5. Nothing was broken and nothing asserted
that it would stay that way. **It held because the deployment had not happened yet**, which is not a
property of the system.

**What can check it is the health verdict and only the health verdict**, because the served root is the
one place both halves exist at once — a test in `forge` cannot see what is deployed and neither can one
in `serve`. `publish.health` reads the `READABLE` literal out of the served `engine/package.js` and
compares it against every public package. ⚠️ **A missing reader is a fault rather than a skip**: packages
published into a directory with no client beside them is a deployment, not a pass.

**⚠️⚠️ Two writers of one document drift the day either one changes, and each file stays internally
consistent while they do.** This is the two-Dockerfiles-and-a-uid shape again, and it recurred on
2026-08-24 in the tree that records it.

`forge` has two scripts that write a dated pointer: `build_inventory` dates the calendar,
`write_reference_puzzles` dates six development boards from a fixed day. **Their own docstrings say the
*dating* is deliberately not shared, and that is correct.** The field set and the version are not the
dating — and when the pointer gained a field, only the calendar writer was changed. The development
batch kept writing the old shape, **which is the batch the dev server and the browser suite read**, so a
browser test named *the real pointers still read* was reading a document production no longer produces,
green the whole time.

⚠️ **Reading either script could not have found it.** Each is right about its own half and neither
states the other's. What found it was **trying to photograph the feature and getting a page without
it**.

**The repair is the one the uid got: the fact lives in two files, so it lives in neither.**
`boxscore_package.format.pointer` builds the body and both writers call it;
`forge/tests/test_the_two_pointer_writers_agree.py` refuses a writer that spells a pointer field itself,
and was seen red by putting the literal back.

⚠️⚠️ **And the exactness guard fired correctly and still had to be rewritten.** A test asserting the
pointer's field set *by name* is the leak guard — a pointer that grew a `puzzles` array would be the
manifest again, served to the browser — so it going red on a new field is the guard working. But a
hand-written set means every legitimate addition edits it, and the edited test then asserts only what
its editor already believed. **It takes the expected keys from the body helper now and asserts separately
that no value is a collection**, which is the property it was actually protecting.

**⚠️⚠️ A remedy that makes a symptom rarer is confirmed by the same evidence as one that removes it.**
This is the hardest wrong answer in the register to detect, and it was one decision away from being
taken on 2026-08-23.

The browser suite stopped finishing in headless. The evidence said *a budget*: the hang moved when tests
were added or removed, it never reproduced in an ordinary browser, and every isolated probe passed. The
structural answer followed — **the runner drives one page, so split the suite across two.** It would have
worked. **It was wrong.** The cause was the runner starting the development server with
`stdout=subprocess.PIPE` and reading it only in the teardown: the server writes a line per request, the
64 KB pipe fills at about a thousand of them, and the *server* blocks inside `write()` and stops
answering. Two pages make the same requests against the same unread pipe — **the ceiling moves and the
next thousand find it again, with the identical disguise.**

**Splitting would have produced a green suite and a report saying the problem was fixed.** Nothing in
that outcome distinguishes it from a real fix, which is what makes this different from every other shape
here: the others are caught by looking at the output, and this one *survives* looking at the output.

**The check that exists for it: a remedy aimed at a threshold has to name the resource.** *The suite got
too big* is not a cause, it is a restatement of the symptom — and a remedy built on a restatement can
only move it. Ask what runs out, in units. If the answer is not a number of bytes, sockets, threads or
descriptors, the cause is not known yet and the fix is a guess wearing an argument.

**And what found it was bisecting on difference, not on suspicion.** Three tests were investigated and
cleared in turn, which is bisecting on suspicion and cost an afternoon. What worked was writing a probe
that ran **the same suite** and finished, then adding the runner's features to the probe one at a time
until only one difference was left. ⚠️ **The last difference standing was the one nobody would have
listed as a feature** — how each started the subprocess.

⚠️ **The instrument that reproduces a threshold has to cross it.** Every isolated probe — eighty fetches,
twenty loads, every page — passed, because a hundred requests never fill a buffer. A probe that stays
below the limit reports health at any size of limit, which is a check that cannot fire.

⚠️⚠️ **And the fix is not the opposite of the defect.** The pipe existed because **discarding the output
was the previous defect** (v36-P3-11): both streams went to `DEVNULL`, so a stolen port or a crash in the
server presented as a bare `ERR_CONNECTION_REFUSED` with the one explanation thrown away. Going back to
`DEVNULL` would trade one silent failure for another. **Keeping the output *and* reading it is what
neither version did** — when a fix reintroduces the thing an earlier fix removed, the answer is usually
the property both versions were missing rather than either version.

**⚠️⚠️ A rule that acts on arrival cannot say anything about what is already there.** A filter in a
`WHERE` clause and a refusal in a producer both stop a bad thing entering, and **neither leaves anything
behind that can be asked afterwards**. So a rule discovered later — which is the ordinary case, since the
inventory always predates the register — has no way to reach the inventory built before it. A
seventeen-inning board sat in the published calendar for a week, signed, certified and dated, and was
found **by accident** when a different tool tried to read it.

**Every rule about what may exist needs a third place: something that asks the population.**
`docs/excluded-games.md` names all three — the query avoids work, `produce()` is the narrowest place
nothing can walk around, and `audit()` is the only one that can read what is on disk and say whether the
set is clean. ⚠️ **And it must refuse a board that carries no answer**, not skip it: *the absence of the
evidence must not read as the evidence.*

**⚠️⚠️ An open decision must not be enforced as though the answer were always yes.** The automatic-runner
boundary is a rulebook fact nobody here may invent, so the code was wired to fail loudly when it was
reached — and the first version reached on **every** extra-inning game, aborting a production run on a
1964 board. That is not failing closed on the case in question; it is halting everything for a question
about a different era. **Scope the loud failure to where the answer could actually differ**, and say what
the scope rests on: here, the last season anybody has measured. ⚠️ And check whether the open decision is
load-bearing at all — the placed runner is caught **per game** by the global identity, so the boundary
buys work avoided, not correctness. *A question that blocks everything is worth asking what it is for.*

⚠️ **The decision itself was settled on 2026-08-24 — 2020, regular season only, never the postseason —
and the lesson above is about the interim, not about an open question.** It is kept because the shape
recurs; `docs/excluded-games.md` §2 is where the ruling lives. ⚠️⚠️ **And it stayed marked open in four
documents after he had answered it**, which is why it was put to him a second time. **A stale open
marking costs the person who already decided**, and closing one is part of taking the decision, not
tidying afterwards.

**Never propose pausing, stopping for the day, continuing tomorrow, or deferring to a later session
— in any form, including softened ones.** The operator decides when work stops; nobody else raises the
question. A true technical fact about the work is welcome — "an incomplete publication gate looks like
a gate and is not one" — but it is a reason to finish the thing, not a reason to postpone it. State
the constraint, then do the work.

**A defect noticed in passing gets written down before continuing.** Even when it is not fixed then,
even when it seems small, even mid-investigation. The conversation is not a tracking system: a defect
mentioned in prose and not recorded is a defect nobody will find again until a review finds it. This
rule exists because the fabricated hit anchor — a line score total summed from the very rows it is
supposed to verify — was spotted in passing, described out loud, and left in place. It went to
`docs/reviews/todo.md` only after a static review found it hours later.

**And each of the failure forms above must fail on its own.** Writing the pattern down was not enough:
fresh instances of all four appeared afterwards. An anchor derived from what it verifies needs a test
asserting every total is loaded independently, per field. A filter that passes on absence gets written
as `EXISTS` over an acceptance list, never `NOT EXISTS` over an exclusion list, with a test that an
absent row is *rejected*. A function defined twice is caught by lint — enable the rule rather than
trusting review, and keep discovery inside the lint scope, because that is where it happened. A check
that exists but is never called needs a test asserting the publication boundary invokes every
implemented check, so adding one without wiring it in fails.

**A sample that evaluates the board is rendered with the board's renderer.** If a variant is needed to
compare two forms, it is a **parameter of the real renderer**, never a copy of it. A comparison page
written with its own `grid()` twice showed something other than what it was evaluating — once carrying
suffixes while its own text said there were none, once missing the totals row that anchors every
column — and both times the judgement would have been made on a board that does not exist. This is the
three-definitions defect and the two-copies-of-a-rule defect wearing different clothes, and the rule is
stronger than "check the output before sending it" because it does not depend on remembering.

**A mechanism kept past the problem it solved becomes a constraint on everything added after it.** **And a
hidden dependency of it.** Nobody declared the row-label suffix a contract; it became one by habit,
read by three decisions that were really about the lineup slot — whether to indent a row, whether a
board carries a substitution, which board to pick. All three broke in the commit that removed it, one
of them silently until a pack refused to build. **When a mechanism is removed, look for who was
reading it, not only who was writing it** — here one place wrote the suffix and three interpreted it. The
row-label suffix was introduced for one reason: footnote references had to name a unique row. A second
grouping — indentation by lineup slot — arrived later, and the two partition the rows differently, so
which row carries the number is arbitrary and the number reads as a claim it is not making. Every fix
attempted was about *which row deserves the number*, and the question was whether the number needed to
be on a row at all: move the footnote reference off the label and the suffix has no reason to exist.
**When a mechanism collides with something new, ask what it was for before asking how to reconcile it.**

**⚠️⚠️ A partial fix reads exactly like a complete one, and the 2026-08-22 instance is the clearest yet.**
Asked what the client may see, I closed the *forward* half: a public manifest listing every id hands out
tomorrow's puzzle, so the manifest stopped listing the future. True, and the smaller half. **The past is
the product** — §9 sells the archive — and it was entirely public, as static files, with a list pointing
at every one of them. **Fixing only the forward half would have left the business model unenforceable
while looking fixed**, which is worse than not fixing it, because a closed finding stops being looked at.

⚠️ **What distinguishes this instance:** the partial fix was not a shortcut or an oversight. It was a
complete answer *to the question I had framed*, and the framing was the defect. **Ask what the mechanism
is protecting before asking whether the protection holds** — the manifest was guarding a schedule, and
the thing worth guarding was the inventory.

**A fix that solves most of a problem reads like one that solves all of it.** The slot column was
proposed to kill three things at once: positions repeated across different slots, the lost
slot-grouping relationship, and footnote ambiguity. It kills the first two. It does nothing for rows
*sharing* a slot — three `P` rows in slot 9 leave `HBP: 9` pointing at three candidates — and the
whole width argument depended on the label being free to shrink once the suffix was gone. The
remaining case is the one nobody checks, because the proposal is already carrying a win. **Enumerate
what a fix claims and test each claim separately**; a claim bundled with two that hold is the one that
gets waved through.

**A justification is scoped, and it does not travel.** The contradiction is easy to see when two
places state opposite rules. The finer defect is a justification that is *true where it was written*
and silently false where it was reused. `narrow` declined to withhold the global identity, reasoning
that which puzzles needed it is recorded on the family axis. True of propagation, where every
deduction names its identity. False of bounding, which names none — so the global relation could
decide a cell on a board that reported never having touched it. Nothing disagreed with anything; the
reason simply stopped applying. **When a rule is reused, re-derive its reason in the new place rather
than carrying the conclusion across.**

**A null result needs the per-item count, not only the aggregate.** "Nothing moved" read off medians
is not a null: two items moving in opposite directions leave every summary statistic untouched. A
before-and-after must say how many individual items changed, and a comparison that cannot name the
items it compared is not a comparison. This is the same defect as a check that never fires — an
instrument that cannot distinguish, reporting as though it had.

**A regular expression over code cannot tell a name from the tail of another name.** `sign\(` matched
inside `verify_signature(` and produced code that signed with the *public* key — from a pattern that
looked specific. Second instance in this project, after the `sed` that renamed a dataclass field.
**Rewrites across call sites are verified by running, never by reading the diff**, and a pattern that
anchors on a bare identifier needs a word boundary in front of it or it is matching substrings.

⚠⚠ **Fourth instance, 2026-08-23, and the setting is the point: it was in an instrument built during
work whose subject was this exact failure.** A watcher polling a push log for completion matched
`failed` — **inside `1 xfailed`** — and reported the push finished while the browser suite still had to
run. Written in the same session that fixed `"keep"` matching `keeps` and while auditing the `sign(`
case, by someone who had just written the rule down twice.

**So knowing the rule does not apply it.** All four instances are the same shape and the first three
were all *known* when the fourth was written. What distinguishes the ones that were caught is not
knowledge but **anchoring**: a word boundary around `failed` costs nothing, and the two guards written deliberately that
day — `(?<![\w-])` around a tree name, an `ast.ImportFrom` walk — both survived mutation, while the
throwaway one-liner did not. **The discipline is not remembering the rule; it is that a pattern gets an
anchor by default, including in code that will be deleted in an hour.**

**Verify against the real artifact, not against what you believe you wrote.** Parse the file before
running three hours of compute against it.

---

## Non-negotiable constraints

Violating any of these is a defect, not a tradeoff.

### 1. Human-solvability guarantee (§4)

A puzzle ships only if the solver (propagation, then bounding) solves it **without backtracking**. If it needs to guess even one cell, discard it or give a cell back as a hint.

**What the solver reports:**

| Axis | Values |
|---|---|
| Technique | propagation · propagation plus bounding |
| Equation family | column sums · row identity · cross-team · global identity · **batting order** |

*The T1–T5 ladder this section used to carry is superseded and kept only in §4, where the reasoning
lives. The short version: the 2×2 rung cannot fire on any board of this constraint family, and with
it gone the first two rungs are one operation and the last is one more equation inside it.*

⚠️⚠️ **The batting order became the fifth family on 2026-08-21, and every figure taken before that
date was measured against four.** The player was already being taught five — the reference sheet and
the tutorial both present it as a relation, because it is the one family that cannot be read off a
boxscore — while `FAMILY_OF` mapped no identity to it, so `families_used` excluded every lineup step
and no package could say a board depended on one. **Not adding it did not avoid the mismatch; it hid
it**, and it left no way to ask how much of the inventory leans on the rule.

**The old figures are marked, not re-run.** They were not wrong; they were counting a smaller set,
which is the same treatment and the same reason as the zero-fill correction. A figure that names the
four-family axis stays comparable with itself.

**And three numbers that describe the solution path** (§31), independent of each other and of zero
density when measured off the compressibility ceiling:

| Number | Measures |
|---|---|
| Chain length | Effort. **The generator's control variable** — its input is a target chain, not a cell count |
| Search cost | How hard the next move is to find |
| Resolution p90 | How much arithmetic a step demands. **p90, never max** — the max is 8 or 9 on every board |

**The publication rule is unchanged:** a puzzle ships only if the solver finishes without
backtracking.

**⚠️ Read the metrics off the ceiling, never at it.** A board erased to its compressibility limit has
a maximally hard step somewhere, so every board scores alike and the numbers look broken. That error
nearly cost the whole approach.

**⚠️ The board's difficulty ceiling is topological.** A constraint graph that is a forest has no
middle difficulty — one blank per equation is a subtraction, two in one equation are usually
*ambiguous* rather than hard, and §22 discards them. The row identity `PA = AB + BB + HBP + SF + SH +
CI` is what breaks the forest, taking independent cycles from 0 to 16. **Do not try to buy difficulty
in the erasure algorithm; it is not there to buy.** A forge test guards the cycle count.

Uniqueness alone is **not** sufficient. A puzzle can have exactly one solution and still be humanly underivable — that is the worst failure mode because it looks correct.

### 2. Layered validation with independent code (§22)

Four layers, each able to reject on its own:

1. Validate the boxscore against all identities before admitting it to the pool
2. Prove solution uniqueness
3. Require the human-technique solver to finish without guessing
4. End-to-end: take the published puzzle, solve from scratch, compare against the original boxscore

⚠️⚠️ **Layer 4 compared against the package's own solution until 2026-08-21, and that made the list
above a list of three.** The solution is written by the same producer in the same pass as the puzzle,
so the fourth layer asked whether a file agreed with itself: **a generator writing the answer wrong got
all four layers agreeing with it.** The worked example this section uses to justify a fourth layer —
two batters' hits exchanged, every identity intact, unique solution, different game — travels in both
halves of a corrupted artefact and passed.

`verify()` now takes `source`, the original boxscore, and it has no default for the reason `secret` has
none: **the absence of the comparison must not read as the comparison passing.** The swapped-hits case
is a test again and it is caught. ⚠️ What this buys is independence between *the file* and *the game in
memory*; a defect in the loader that produced both is the residual risk this section already records
under the common-author heading.

⚠️⚠️ **The strong form of layer 4 can only run at generation, and that is by construction.** §7 strips
`game_id` from a published package, so nothing holding a published file can reload the direction it
came from — **the only source available to a check run over `serve/data/puzzles/` is the package's own
solution.** Running layer 4 there is the self-referential comparison again.

**Say what such a run establishes and what it does not**: it confirms every published puzzle solves back
to the answer travelling with it. **It cannot say whether the generator wrote that answer correctly.**
A future reader who sees that check pass and takes it for the end-to-end one has been misled by a true
result, which is the most durable way to be misled. The end-to-end check runs where the source is —
inside the writer, against the direction it loaded — and nowhere else.

**The verifier must not import or reuse generator code.** If it shares functions it inherits bugs and the validation is theater. Implement independently, even at the cost of duplication.

⚠️⚠️ **The two sides name cells differently, and mixing them fails as SILENCE rather than as an error.**
The verifier says `bat[0].hits`; the forge says `batting[0].hits`. An instrument that reads a package
with one side's helper and reasons with the other's gets **no exception and no missing key** — it gets
a dictionary whose keys match nothing, so the solver deduces nothing and returns an **empty result**.

**An empty result reads as a real zero.** A measurement built that way answered *no published board
uses the batting order, 0 of 6* — a plausible number, correctly formatted, about nothing. It was caught
because the family list was empty for **every** board, which is the tell this project already records:
a metric that cannot vary is broken rather than informative.

The independence that makes §22 worth having is exactly what produces the silence: there is no shared
symbol to raise on, because sharing one is the thing being prevented. **Anyone writing an instrument
that touches both sides asserts it deduced something before believing what it deduced.**

A puzzle that fails any layer is **discarded silently, never repaired.** With thousands of candidates, throwing away 30% costs nothing.

**⚠️ What the four layers do not cover.** They check that the numbers agree with each other. They cannot
tell a real boxscore from a fabricated one, and every serious data defect in this project passed all four
without a sound. Plausibility checks — assertions about how baseball works, not about arithmetic — are a
separate and equally necessary class. So is solving by hand.

**⚠️ Layer 3 does not verify human derivability.** It propagates intervals to fixed point across forty-odd
simultaneous relations, which is stronger than any person. A board can pass it and be underivable by a
human. **Solving boards by hand is therefore a launch gate, not a review step** — it is the only real
verification of human derivability that exists, and the only check the common-author risk does not touch.

**⚠️ Independence has a limit worth stating.** The verifier shares no code with the generator and was
written without reading it, but the same author wrote both. A misreading of §3 would be made twice and
would agree with itself. Recorded as residual risk, not resolved.

### 3. Double idempotence (§21)

- **Puzzle:** the same Retrosheet game always yields the same puzzle with the same ID. Regenerating creates no duplicates.
- **Calendar:** the date → puzzle assignment is fixed and never recomputed.

**Puzzle IDs derive from the game, never from the date.** Any batch or calendar process must be safe to run twice.

### 4. The calendar extends, never rewrites (§21)

Once a date's puzzle has been played, that date cannot change — streaks, shared results, and stats hang from it.

- Future date, defective puzzle → replace it
- Past date, defective puzzle → mark void, exclude from streaks and stats, **leave the assignment**

### 5. Environment separation (§33)

**The forge knows nothing about users. The service knows nothing about generating.**

- No user data, accounts, streaks, or rankings in `forge/` — ever
- No puzzle generation or validation logic in `serve/` — it only serves what it received
- Three domains with independent lifecycles: puzzles/calendar (forge writes), application (deploys freely), user data (VPS only)

Changing the app must never require touching puzzle inventory, and loading inventory must never require touching the app.

### 6. Mobile defines the board (§6)

- **Six data columns maximum.** 375px minus margins, 44px minimum touch target, ~70px label column. A seventh column does not fit and cannot be added.
- Batting: **PA, AB, R, H, BB, SO.** Pitching: IP, H, R, ER, BB, SO. RBI was dropped for PA: it was the only batting column with neither a cross-team counterpart nor a place in the row identity, and PA is what breaks the forest (§6).
- **The line score is always shown complete and never erased.** It is the puzzle's anchor, read-only, so it needs no touch target.
- **A footnote line gives LOB, HBP, SF, SH and CI.** ⚠⚠ **Every one of them is given and read-only — the per-batter cells, the totals row and LOB alike.** They are needed because without LOB the board cannot express the global identity at all and without the rest the row identity does not close; they cost no column width and need no touch target, and printed boxscores publish exactly these values this way. **Attributed per batter, labelled by position** (`HBP: SS`) — never by name, which would hand the player a name before they earned the row (§7).
  - ⚠⚠ **This bullet said the per-batter cells were erasable, and it said so for weeks after that was reversed** (v39-P3-01). The pool run closed it: 96% of the pool's footnote terms are zero, coverage is identical with the cells open and given, and everything built for the open case was **deleted rather than disabled**. The 5-to-15 figure it cited is the corrected one — see *A metric can be correctly computed and still measure something the player never encounters* above, which is where that reasoning lives and stays.
  - ⚠️ **The contradiction was inside one document, which is what made it dangerous.** A reader who found the correction was still given a direct instruction, in the authoritative board section, to restore a retired interaction and the difficulty scale behind it. This project already records that *a rule stated in the place people go to learn the rules is the worst place for one that is false* — and the instance that produced that sentence was in this file too.
- **⚠️ Live footnotes must be visually prominent.** Nine rows in ten have every footnote term at zero, so players learn to stop looking — and the row where one appears is exactly the row whose arithmetic fails if they miss it.
- **Header and totals row stay pinned during scroll.** In a deduction puzzle the totals are consulted constantly.
- Never hide columns to fit a screen — every visible number is part of an equation, so hiding one erases a constraint.
- The board is identical on all screens. Desktop gets more whitespace, not more content.
- **Roster caps: ≤13 batters, ≤6 pitchers. Measured, not estimated** (§6). **The values live in `forge/src/boxscore_domain/`, with the reason and the measurement beside each one, and a test forbids spelling them anywhere else.** Rows on screen turned out not to bind — with the active section's totals pinned they never scroll away, and 70% of steps touch rows within a five-row window. That freed the batter cap from 10 to 13. **⚠️ The pitcher cap went 2 → 4 → 6, and both earlier values were wrong for the same two reasons.** The screen argument was retired by the working-set finding and then left standing for pitchers because nobody re-derived it there — a justification reused rather than re-derived. And the difficulty comparison favouring fewer pitchers was run while stalls counted the solver deducing footnote zeros: **a pitching row carries no footnote terms**, so pitcher-heavy boards had fewer zeros inflating their scores and the comparison was biased against exactly what it judged. At ≤6, coverage at 8 stalls goes 22% → 33%, the pitching section's share of stalls 34% → 45%, the pool grows 41% and reaches the 1990s and 2000s, and both equation families move toward the range that separates boards. The median ceiling stays at 5, so the ladder's range does not move — what moves is how much of the pool reaches it comfortably. Erasure percentage is superseded, and so is chain length: **the generator targets a stall count**.
- **The label column is 66px, seven characters, fixed.** Never full names truncated only where they overflow. **Disambiguation by first initial is mandatory** — 6.64% of boards carry two genuinely identical surnames, so it is not a truncation artefact (§7).

### 7. Puzzle quality outranks everything (§31, §22)

If a measurement shows the board is too small to produce puzzles that require the cross-team and global identities, **the board
changes.** Screen budget constrains the board; it does not get to make the puzzle trivial.

**Do not invent numeric parameters that shape the product.** Cell counts, thresholds, percentages,
caps — if a value affects puzzle difficulty, pool size, or player experience and it is not derived
from a measurement, present it as a proposal and let the operator decide. Label estimates as
estimates.

### 8. You can never lose (§27)

There is no fail state. No error limit, no clock that kills the game. The puzzle stays open all day, saves itself, and at midnight closes for streak purposes only — it remains playable from the archive.

### 9. Playability survives backend failure (§23) — ⚠️ and it is in tension with §9

⚠️⚠️ **Static delivery and paid access pull opposite ways, and both are decided.** §23 makes the day's
puzzle a static file so the game survives the backend being down; §9 sells the archive. **A static file
on a public path cannot be sold** — anyone can request it and no server is asked.

**The resolution is two paths rather than one** (`docs/calendar.md`): **today's and yesterday's packages
are public static files**, and **everything else is on no public path at all**, served by an endpoint
that checks the subscription first. The daily is static because it needs no control; the archive is
served because it does.

**Yesterday is deliberate**: somebody who starts at eleven at night loses their work at midnight
otherwise, and two days is not an archive. ⚠️ **The rotation is the enforcement** — when today arrives,
the day before yesterday must leave — and a rotation that fails once leaks the archive one day at a
time, permanently. The inventory health endpoint asserts the public path never holds more than two.



The day's puzzle is a static file, validation is client-side, and events are stored locally first (C7). If the backend is down, login and sync fail but **the game still works.** Never introduce a backend dependency into the play path.

The daily puzzle is served **without authentication** — no API key. A key in a header travels to the browser and protects nothing while adding a fragile dependency.

---

## Architectural seams

Present in v1 even when the corresponding feature is not built. Do not remove them as "unused."

| # | Seam |
|---|------|
| C1 | Three sealed layers: generator → data → client. Zero puzzle logic in the client |
| C2 | Puzzle = pure data, immutable ID, versioned schema |
| C3 | Rich metadata on every puzzle even when unused (year, teams, flags, difficulty, techniques required) |
| C4 | The engine does not know what day it is; a loader decides |
| C5 | Engine carries no chrome or branding; themeable via CSS variables |
| C6 | Per-puzzle routes: `/p/<id>` canonical, `/today` redirects |
| C7 | **Store events, not state**: puzzle_id, date, duration, hints, errors, highest technique |
| C8 | `canAccess(puzzle, user)` — ⚠️⚠️ **a display decision, not an enforcement point.** It runs in the browser over files the browser can already fetch, so it decides what the interface *offers*; it cannot decide what the server returns. **The enforcement is which files exist on a public path** — today's and yesterday's, and nothing else (`docs/calendar.md`). Returns true in v1 |
| C9 | Reserved, empty layout slots for future ads. **Three places, and ⚠️ none during play** — §10 says where and why, including the rule that resolves *renders nothing* against *does not shift the layout*: a slot goes where nothing the player might be about to touch sits below it. **No ad code, no network, no decision to run ads** |
| C10 | Two-phase boot that can wait for consent |
| C11 | Zero user-facing strings in code |

**C7 is irreversible.** Storing only aggregate state loses history that can never be reconstructed. Store the event record.

---

## Data pipeline

`Retrosheet event files (SQL Server) → cwbox → quality filter → generator → 4-layer validation → calendar → signed package → VPS`

### Source rules (§32)

- ⚠️⚠️ **Only `dbo.retro*`. Never a table from another collection, for any reason.** The database holds
  several: `bdb*` is Lahman, `fg*` is FanGraphs, `mlb*` and `dgl*` are others again. They disagree with
  Retrosheet about player identifiers, about which games exist and about what a season is — so a board
  drawing on two of them **balances perfectly and corresponds to nothing**, which §22's four layers
  cannot see.

  **This has happened.** The loader joined `dbo.regPeople` for names and resolved 98.4% of identifiers;
  a join that resolves most rows looks exactly like one that resolves all of them, and the 316 it missed
  shipped under a fabricated `Unknown`. `forge/tests/test_only_retrosheet_tables.py` enforces it — every
  `dbo.X` in a query must be `dbo.retroX`, and an unqualified `FROM someTable` is refused too, since
  that is the same defect with the schema left off.
- ⚠️⚠️ **Only games the visiting club batted first — an acceptance test, decided 2026-08-22.** 49
  regular-season games have the home club leading off the first (neutral sites, rescheduled dates); the
  postseason has none today and carries the same rule preventively. **A construction rule, not data
  quality:** Retrosheet describes something real and the *board* is what cannot represent it — the `x`
  for a half-inning never played, which side is `AWAY BATTING`, and the outs for a home team that wins
  without batting in the ninth all assume the visitor bats first.

  **`EXISTS` over the visitor batting, never `NOT EXISTS` over the 49**: an exclusion list admits a game
  with no event rows, which is the fail-open shape this section already closed for provenance. Coverage
  measured before relying on it — 100% of games carry a first event, both seasons. ⚠️ **No validation
  layer can see this**; such a board balances every identity and is wrong only about which team is
  which. `forge/tests/test_the_visitor_bats_first.py`.
- **Exclude deduced event files.** They are reconstructions from partial information and will not balance.
- Offensive and pitching stats are well proofed by Retrosheet. Defensive stats (PO, A) are not — and are not used by the board anyway.
- The Chadwick Bureau person register resolves player identities for the final reveal (§7).
- Chadwick tools are GPL; running them as CLI does not affect our licensing. Do not vendor their source.

### Pool quality filter (§5)

**⚠️ Rewritten after measurement — the original criterion was wrong at the root (§5).**

1. **Roster compactness** — hard filter, asymmetric and **decided**: the *offensive* team needs
   **≤13 batters**, the *defensive* team **≤6 pitchers** (§6). Both are `boxscore_domain.BATTER_CAP`
   and `PITCHER_CAP` — never a literal, and a test enforces that.
2. **Zero-density gate: below 30%, decided.** It removes every shutout and the three-run games while
   keeping seven-run ones. Direct and cheap — it attacks the cause instead of scoring it.
3. **Compressibility is a viability constraint, not a ranking.** It measures how much can be removed,
   not whether what remains is worth solving: it correlates **+0.79 with zero density**, so ranking
   on it selects boredom. A board must be able to lose enough cells to be a puzzle; above that floor,
   compressing further is not better.
4. **Chain length, search cost and resolution p90** grade what survives (§31).

*Line score variety and digit range are dropped. They were proxies for compressibility, and
correlating with the wrong target is not a reason to keep a filter.*
- **Roster compactness, asymmetric — decided:** the *offensive* team needs **≤13 batters**, the *defensive* team **≤6 pitchers**. Only those appear on the board. **⚠️ The pitcher cap was said to cost screen space and it does not** — the board scrolls, the totals stay pinned, and raising it *raises* difficulty: the pitching section contributes 45% of stalls at six against 34% at four (§6).
- Line score variety
- Digit range — numbers > 3 in several columns

**Each game can yield up to two puzzles**, one per direction (A's offense vs B's pitching, and vice versa). A game may qualify in one direction and not the other. Count the pool by direction, not by game.

⚠️⚠️ **But only one of the two may ever be published — see *One game, one puzzle* below.** The pool is
counted by direction; the *calendar* spends a whole game per board. Both statements are true and they
are about different things, which is why they sit together.

### Calendar construction

Difficulty is tied to the day of the week — easy Monday, hard Saturday (§31). The calendar must classify by level and shape the week. Within a level, vary which techniques are required so no two Tuesdays open the same way.

The VPS holds **five months of forward inventory** at all times; alert below three (§33).

#### ⚠️⚠️ One game, one puzzle — mandatory, and the calendar is the only thing that can enforce it

**Never publish both directions of the same game.** From package schema 5 the reveal prints the
**complete boxscore, both clubs** — which is the whole reason it is worth drawing — and the other
club's half **is the other direction's board**. Publishing both gives the second one away, entirely,
inside the first one's reveal, before it is played.

**It costs nothing.** The pool is 400,000+ directions; spending a whole game on each board is not a
measurable loss of inventory.

⚠️ **No package can enforce this and no validation layer can see it.** A file cannot know what else
was published — this is a property of the *set*, which is what a calendar is. `write` refuses nothing
here; `write_reference_puzzles.refuse_second_direction` asserts it over a batch, which is the whole of
the enforcement that exists today. **The calendar inherits the obligation the moment it is built**, and
it inherits it over everything ever published rather than over one batch. A calendar that does not
carry this check is not a calendar with a missing feature; it is one that leaks puzzles.

⚠️ Related but not the same as §21's rule that the calendar extends and never rewrites. That is about
a date not changing once played. This is about two dates never drawing on one game.

---

## Product rules that constrain implementation

- **No names during play (§7).** Rows are labelled by position throughout — `CF`, `SS`, `LF-1`, `LF-2` — and **the real boxscore is drawn complete at the end**, with names, teams and date. *Progressive reveal was dropped: knowing a name mid-solve helps nobody deduce anything and costs width.* Row-level validation stops being mandatory with it, since it existed only to know when to reveal.
- **The share grid must never leak the solution or player names.**
- **⚠️ Tutorial: five steps, one per relation family, and *skippable* — this reverses §8**
  (`docs/serve-flow.md` §1b). It teaches the identities, not baseball vocabulary, and it is reachable
  from the landing page at any time. **A compulsory tutorial is a barrier in front of someone who has
  not decided whether they are interested**, and the visitors who do not want it leave before seeing a
  board — the outcome the rule existed to prevent, one screen earlier. It stopped being load-bearing
  when the reference sheet (§3b) put all five relations one button away *during* play; when §8 was
  written the tutorial was the only place the rules were ever stated.
- **Every visit lands on the landing page, not only the first** (`docs/serve-flow.md` §1). The archive,
  the streak and the subscription live there when they exist, so a player routed past it would never
  meet them.
- **Everyone gets the same puzzle on the same date.** Never derive the day's puzzle from device-local state.
- **Timer runs for everyone, silently (§26).** Comparison and percentiles are the paid feature, not the timing itself.
- **No comments or forums (§28).**
- ⚠⚠ **What keeps future puzzles unreachable is that their id is not public — the cache rule is the
  belt, not the buckle.** A package is named by an opaque id and only today's and yesterday's are listed
  anywhere a client can read, so **nobody can request tomorrow's puzzle because nobody can name it**, and
  no browser, proxy or CDN can prefetch a URL it cannot construct. **Cache only the current day's
  puzzle, never the week** — caching ahead would put a nameable future puzzle in an intermediary.

  ⚠️ **Stated in this order on purpose.** Written the other way round, the cache header reads as the
  thing holding the line, and a later reader relaxes it for a good reason — a slow first load, a CDN
  default — believing the exposure is a cache setting. It is not: it is which ids exist publicly.

---

## User data: minimum to operate (§35)

Store: internal ID, email, OAuth provider link, created/last-seen; Stripe customer ID, status, expiry; device UUID + last seen + label; per-game event records; language and accessibility preferences.

Do **not** store: real name, photo, date of birth, IP address, geolocation, in-site browsing history, filled puzzle cells, or card/billing data.

**Events must reference an unlinkable user identifier** so GDPR deletion is satisfied by breaking the link while aggregate percentiles survive.

---

## Security notes

- **Verify webhook signatures on payment callbacks.** Unverified webhooks are the highest-value attack in this system — a forged notification grants a free subscription.
- **Signature verification fails closed.** A missing or unconfigured secret is an error, never a pass. Explicit unsigned verification exists only for test and discovery call sites; any publish or import path errors out when the secret is absent. A check that silently disables itself on misconfiguration is worse than no check.
- **Validate at the boundary, not downstream.** Package JSON is checked for exact row widths, integer-or-null cells, complete line score fields, and object-shaped metadata *before* any arithmetic. A malformed package must produce a controlled rejection, not an uncontrolled `TypeError` three layers later.
- Access tokens: signed, short expiry (24h), signature verified server-side. Renewal is where devices are counted.
- Validate OAuth `state`. Magic links: single use, short lifetime.
- Sanity-check client-reported durations before storing, so absurd values don't corrupt percentiles.
- Rate limit per IP in nginx; do not persist IPs.
- No secrets in Docker images. Containers unprivileged.
- **Escape or DOM-render any interpolated value in generated HTML**, including discovery instruments. Database labels and notes reach `innerHTML`; a measurement page that executes markup can mislead a decision or run code in the operator's browser.

---

## ⚠️⚠️ Dead code, or code held in reserve — one question tells them apart

An instrument that builds a configuration the product does not have is either a **record**, a **trap**,
or **the only way a decision could be reopened**. From outside all three look identical: source that
constructs something no longer real. Deleting the third is a product decision disguised as tidying;
keeping the second reprints a corrected error in the format of a current result.

**The test, and it needs no knowledge of anyone's intent:**

> **If tomorrow the answer flipped, would this instrument be the thing that told us?**

- **Yes, and it already did it once** → a **record**. Keep it exactly as it is, with the losing arm
  present and *named as losing*. `discovery/zero-footnotes/` keeps arms `all`, `non_zero` and `given`
  and says in its own header that the 5-to-15 result *"is a correction, not a new result"*. **Keeping
  the wrong arm and naming it wrong is what makes a file evidence instead of a trap.**
- **Yes, because nothing has been measured yet** → **held in reserve**. Keep it, and **say in the file
  why**, because the next sweep meets the same evidence and can reach the opposite conclusion.
  `discovery/rbi-and-hr/` builds a seventh batting column that does not exist — §6 records the
  eight-column order as *decided and deliberately unbuilt*, so the column is missing for want of a
  measurement rather than because one rejected it.
- **No, it presupposes the answer that lost** → **retire it**. Not delete: the machinery is usually
  correct and the file is the record of how the question was asked. It must stop being a *tool*.

### ⚠️ The worked example, because an abstract rule gets applied wrongly the first time it matters

**`footnotes-open-or-given` and `footnote-grouping` fall in the same category and want different
repairs**, and nothing on their surface distinguishes them:

| | machinery | question | repair |
|---|---|---|---|
| `footnotes-open-or-given` | **correct** — open against given, paired per board on the canonical list | still meaningful; running it reproduces the settling numbers | **one sentence.** Only its status line was stale, claiming the comparison had never been repeated |
| `footnote-grouping` | **equally correct** — one footnote column against four | **gone.** The footnote line is given, so there is no unknown to group — and its stated motivation is the *corrected* 5-to-15 figure | **retired**, refusing to run with the reason |

**One has working machinery and a stale sentence; the other has working machinery and no question.**
A note on the second leaves something nobody should run and somebody will.

**Retirement is a refusal in `main()`**, not a deletion and not a move: the file stays where its tests
and its history are, and running it raises with the reason and a pointer to what settled the question.
`footnote-groups` and `scoreboard-blanks` were retired the same way — ⚠️ **and for a different reason
worth keeping separate: they do not assume the losing answer, they simply have no subject any more.**

## Discovery scripts are decision tools

They are throwaway code that decides non-throwaway things. Two rules follow.

**Reproducible from the script alone.** No reliance on the caller's working directory or an ambient
`PYTHONPATH`. Every runnable script computes its root and sets its own paths the same way. A discovery
result that cannot be re-run identically is not evidence.

**Fail with an explanation, not an `IndexError`.** Scripts that index fixed sample positions after
filtering must assert the sample size first, and say which filters were applied and what the minimum
was. When a gate, an era window, or a data change empties a sample, the script should say so.

⚠️⚠️ **"The fifty-board pack" named three different things and one of its numbers came from a retired
design.** Resolved 2026-08-22, and the three are separate work with separate sizes:

| | asks | size | axis |
|---|---|---|---|
| **the gate** | are these boards derivable by a person at all | **Pack A's sixteen plus a derivability-only sample over the shipping inventory**; ⬜ that sample's N is open | stalls |
| **Pack A** | does the difficulty ordering match felt difficulty | **16** — four each at rungs 5, 8, 11, 12 | stalls |
| **the stranger's ten** | does the operator's scale agree with somebody who is not him | 10 | spread |

**Where *fifty* came from:** `build_pack.py`'s `audit()` asserts fifty boards with every rung at its
quota **on the chain axis**, and the generator stopped targeting chain. The number and the axis are both
from the superseded design. ⚠️ **Sixteen is not the answer either** — Pack A is a calibration instrument
and four boards per rung says something about a rung, not about the generator. `docs/beta-0.md` carries
the reasoning and the open N.

**Anything acting as a launch gate is asserted, not printed.** The hand-solve pack must
assert its quotas after selection — chain rungs, era allowance, uncertified share, one board per game —
not report them and be believed. A pack that claims to satisfy quotas and does not invalidates the
experiment silently, which has already happened once when weighted sampling produced zero boards at the
easiest rung.

---

## Anti-goals — do not build these

- **Trivia or knowledge questions.** A puzzle is deduction or guessing, not both. This is the line separating the product from Immaculate Grid.
- Play-by-play reconstruction (no unique solution exists)
- Stats querying or analysis tools
- Profiles, walls, forums, or a global public leaderboard
- A native app for the paid tier (§9)
- Achievements, coins, or events to paper over difficulty problems (§31)

---

## When in doubt

The generator and the difficulty curve carry the product. Retention rests on habit and puzzle quality, not on features. If a proposed change trades puzzle correctness or derivability for anything else, the answer is no.
