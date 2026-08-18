# boxscorepuzzle

A daily puzzle where the player reconstructs the boxscore of a real Major League game by pure logic. Unique solution, no guessing. Think kakuro, not sudoku.

**Design document: `docs/design-boxscore-puzzle.md`. Read it before proposing architecture or product changes. Section references below (§N) point to it.**

Status: design complete at the "what and why" level. Implementation starting.

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
affecting launch. But **seam C11 is mandatory regardless: zero user-facing strings in code.** All copy
goes through the string catalog from day one, including generated reveal text and metadata. Cheap now,
expensive to retrofit.

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

---

## Repository layout

```
boxscorepuzzle/
├── CLAUDE.md
├── docs/
├── forge/     ← generator, cwbox, SQL, validation, calendar (never leaves the laptop)
└── serve/     ← app, nginx, docker, endpoints (deploys to VPS)
```

**A single private Git repository on GitHub: `boxscorepuzzle`.** One push backs up everything, which
matters because the repository's primary job is being the backup.

**The repository stays private permanently** — `forge/` holds the generator algorithm and the
human-solvability guarantee, which is trade secret (§16). Never push any part of it to a public gist,
issue, or paste service.

**No cross-imports between `forge/` and `serve/`.** They share no code and no deployment cycle. The
only thing that crosses is a signed package of validated puzzles. **Deployment ships `serve/` only** —
generator code must never reach the VPS.

**Generated puzzle inventory never goes in Git.** It lives in an ignored folder inside `forge/`.

Commit messages in English, imperative mood, one logical change per commit, prefixed with scope
(`forge:`, `serve:`, `docs:`). `main` always deployable, protected, CI must pass. Nothing pushed with
a failing test or coverage under 95%. Commit `uv.lock` — it is the reproducibility guarantee, not a
build artifact.

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

**None of these break an identity.** That is why four validation layers caught none of them.

### The rules that follow

**Validate correspondence, not only consistency.** A fabricated board and a real one both balance. Every
check that only asks "do the numbers agree with each other" is blind to the entire class of error above.
Cross-check against an **independent source** — the game log, not `retroDailyReg` again.

**One predicate, one place.** If two queries, two modules, or two documents encode the same rule, they
will drift. Share the definition or assert they agree; do not maintain two copies and hope.

**A check that never fires is indistinguishable from a check that is broken.** Test the failing case. A
threshold set by eye that rejects real data gets loosened until it says nothing, which is worse than not
having it — it gives false confidence.

**Look at the output.** Every serious defect in this project was found by rendering something and
reading it, never by computing a statistic. **Any measurement producing a distribution must also produce
a handful of rendered examples, checked by eye before the numbers are trusted.** Make it a step, not a
habit.

**Fail closed at boundaries.** Verification that passes when its secret is missing, parsing that accepts
malformed input and dies later, a driver that reports COMPLETE on a non-zero exit — all the same defect:
the absence of a check reading as the presence of a passing one.

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
| Equation family | column sums · row identity · cross-team · global identity |

*The T1–T5 ladder this section used to carry is superseded and kept only in §4, where the reasoning
lives. The short version: the 2×2 rung cannot fire on any board of this constraint family, and with
it gone the first two rungs are one operation and the last is one more equation inside it.*

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

**The verifier must not import or reuse generator code.** If it shares functions it inherits bugs and the validation is theater. Implement independently, even at the cost of duplication.

A puzzle that fails any layer is **discarded silently, never repaired.** With thousands of candidates, throwing away 30% costs nothing.

**⚠️ What the four layers do not cover.** They check that the numbers agree with each other. They cannot
tell a real boxscore from a fabricated one, and every serious data defect in this project passed all four
without a sound. Plausibility checks — assertions about how baseball works, not about arithmetic — are a
separate and equally necessary class. So is solving by hand.

**⚠️ Layer 3 does not verify human derivability.** It propagates intervals to fixed point across forty-odd
simultaneous relations, which is stronger than any person. A board can pass it and be underivable by a
human. **Solving fifty by hand is therefore a launch gate, not a review step** — it is the only real
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
- Batting: **PA, AB, R, H, BB, K.** Pitching: IP, H, R, ER, BB, K. RBI was dropped for PA: it was the only batting column with neither a cross-team counterpart nor a place in the row identity, and PA is what breaks the forest (§6).
- **The line score is always shown complete and never erased.** It is the puzzle's anchor, read-only, so it needs no touch target.
- **A footnote line gives LOB, HBP, SF, SH and CI** — read-only and never erased, like the line score. Without LOB the board cannot express the global identity at all, and without the rest the row identity does not close. Footnotes cost no column width and need no touch target, and printed boxscores publish exactly these values this way. **Attributed per batter, labelled by position** (`HBP: SS`) — never by name, which would hand the player a name before they earned the row (§7).
- **⚠️ Live footnotes must be visually prominent.** Nine rows in ten have every footnote term at zero, so players learn to stop looking — and the row where one appears is exactly the row whose arithmetic fails if they miss it.
- **Header and totals row stay pinned during scroll.** In a deduction puzzle the totals are consulted constantly.
- Never hide columns to fit a screen — every visible number is part of an equation, so hiding one erases a constraint.
- The board is identical on all screens. Desktop gets more whitespace, not more content.
- **Roster caps: ≤13 batters, ≤2 pitchers. Measured, not estimated** (§6). Rows on screen turned out not to bind — with the active section's totals pinned they never scroll away, and 70% of steps touch rows within a five-row window. Erasure percentage is superseded: the generator targets a chain length.
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

### 9. Playability survives backend failure (§23)

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
| C8 | `canAccess(puzzle, user)` — single decision point; returns true in v1 |
| C9 | Reserved, empty layout slots for future ads |
| C10 | Two-phase boot that can wait for consent |
| C11 | Zero user-facing strings in code |

**C7 is irreversible.** Storing only aggregate state loses history that can never be reconstructed. Store the event record.

---

## Data pipeline

`Retrosheet event files (SQL Server) → cwbox → quality filter → generator → 4-layer validation → calendar → signed package → VPS`

### Source rules (§32)

- **Exclude deduced event files.** They are reconstructions from partial information and will not balance.
- Offensive and pitching stats are well proofed by Retrosheet. Defensive stats (PO, A) are not — and are not used by the board anyway.
- The Chadwick Bureau person register resolves player identities for the progressive reveal.
- Chadwick tools are GPL; running them as CLI does not affect our licensing. Do not vendor their source.

### Pool quality filter (§5)

**⚠️ Rewritten after measurement — the original criterion was wrong at the root (§5).**

1. **Roster compactness** — hard filter, asymmetric and **decided**: the *offensive* team needs
   **≤13 batters**, the *defensive* team **≤2 pitchers** (§6).
2. **Zero-density gate: below 30%, decided.** It removes every shutout and the three-run games while
   keeping seven-run ones. Direct and cheap — it attacks the cause instead of scoring it.
3. **Compressibility is a viability constraint, not a ranking.** It measures how much can be removed,
   not whether what remains is worth solving: it correlates **+0.79 with zero density**, so ranking
   on it selects boredom. A board must be able to lose enough cells to be a puzzle; above that floor,
   compressing further is not better.
4. **Chain length, search cost and resolution p90** grade what survives (§31).

*Line score variety and digit range are dropped. They were proxies for compressibility, and
correlating with the wrong target is not a reason to keep a filter.*
- **Roster compactness, asymmetric — decided:** the *offensive* team needs **≤13 batters**, the *defensive* team **≤2 pitchers**. Only those appear on the board. The pitcher cap is what costs screen space and the batter cap is what costs pool, which is the opposite of the earlier provisional pair (§6).
- Line score variety
- Digit range — numbers > 3 in several columns

**Each game can yield up to two puzzles**, one per direction (A's offense vs B's pitching, and vice versa). A game may qualify in one direction and not the other. Count the pool by direction, not by game.

### Calendar construction

Difficulty is tied to the day of the week — easy Monday, hard Saturday (§31). The calendar must classify by level and shape the week. Within a level, vary which techniques are required so no two Tuesdays open the same way.

The VPS holds **five months of forward inventory** at all times; alert below three (§33).

---

## Product rules that constrain implementation

- **Progressive reveal (§7):** rows start labeled by position (C, 1B, 2B, SS...). On completing and validating a row, that player's name appears. Teams, date, and context at the end. Requires row-level validation. The name does not fit in the label column on mobile — render it elsewhere.
- **The share grid must never leak the solution or player names.**
- **Tutorial is not skippable on first play (§8).** It teaches the identities, not baseball vocabulary.
- **Everyone gets the same puzzle on the same date.** Never derive the day's puzzle from device-local state.
- **Timer runs for everyone, silently (§26).** Comparison and percentiles are the paid feature, not the timing itself.
- **No comments or forums (§28).**
- Cache only the current day's puzzle, never the week — caching ahead leaks future puzzles.

---

## User data: minimum to operate (§35)

Store: internal ID, email, OAuth provider link, created/last-seen; Paddle customer ID, status, expiry; device UUID + last seen + label; per-game event records; language and accessibility preferences.

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

## Discovery scripts are decision tools

They are throwaway code that decides non-throwaway things. Two rules follow.

**Reproducible from the script alone.** No reliance on the caller's working directory or an ambient
`PYTHONPATH`. Every runnable script computes its root and sets its own paths the same way. A discovery
result that cannot be re-run identically is not evidence.

**Fail with an explanation, not an `IndexError`.** Scripts that index fixed sample positions after
filtering must assert the sample size first, and say which filters were applied and what the minimum
was. When a gate, an era window, or a data change empties a sample, the script should say so.

**Anything acting as a launch gate is asserted, not printed.** The fifty-board hand-solve pack must
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
