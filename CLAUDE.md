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

**The repository stays private permanently** — `forge/` holds the generator algorithm and the T1–T5
guarantee, which is trade secret (§16). Never push any part of it to a public gist, issue, or paste
service.

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

## Non-negotiable constraints

Violating any of these is a defect, not a tradeoff.

### 1. Human-solvability guarantee (§4)

A puzzle ships only if a solver implementing **exclusively** techniques T1–T5 solves it **without backtracking**. If it needs to guess even one cell, discard it or give a cell back as a hint.

| Level | Technique |
|-------|-----------|
| T1 | Equation with a single unknown → direct solve |
| T2 | T1 propagated to fixed point |
| T3 | Two equations sharing unknowns → 2×2 system |
| T4 | Bounding by inequality (AB ≥ H, ER ≤ R, non-negativity) |
| T5 | Global team identity: PA = Outs + R + LOB |

**⚠️ T3 is unreachable and no column set changes that (§4).** Every identity is a sum over a row or
over a column, so two of them share at most the one cell where a row crosses a column — never the
two that a 2×2 needs. The working ladder is **T1, T2, T4, T5**.

**⚠️ The consequence is bigger than the missing rung.** A tree-like constraint graph has no middle
difficulty: one blank per equation is a subtraction, two blanks in one equation are usually
*ambiguous* rather than hard, and §22 discards them. The generator therefore converges on trivial
puzzles — nine independent subtractions, no chaining. **The ceiling is topological, not algorithmic;
do not try to fix it in the erasure algorithm.** The fix under consideration is putting plate
appearances on the board so each row gains its own identity (§4, §6). **The column set is an open
decision — do not treat the current six as settled, and do not run the compressibility measurement
until it is.**

Uniqueness alone is **not** sufficient. A puzzle can have exactly one solution and still be humanly underivable — that is the worst failure mode because it looks correct.

### 2. Layered validation with independent code (§22)

Four layers, each able to reject on its own:

1. Validate the boxscore against all identities before admitting it to the pool
2. Prove solution uniqueness
3. Require the T1–T5 solver to finish without guessing
4. End-to-end: take the published puzzle, solve from scratch, compare against the original boxscore

**The verifier must not import or reuse generator code.** If it shares functions it inherits bugs and the validation is theater. Implement independently, even at the cost of duplication.

A puzzle that fails any layer is **discarded silently, never repaired.** With thousands of candidates, throwing away 30% costs nothing.

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
- Batting: AB, R, H, RBI, BB, K. Pitching: IP, H, R, ER, BB, K.
- **The line score is always shown complete and never erased.** It is the puzzle's anchor, read-only, so it needs no touch target.
- **A footnote line gives LOB, HBP, SF and SH** — read-only and never erased, like the line score. Without LOB the board cannot express T5 at all, and without HBP/SF/SH the batter identity does not close. Footnotes cost no column width and need no touch target, and printed boxscores publish exactly these values this way. **Open: whether they are attributed per team or per player** — that decides whether the batter identity is a per-row equation or a single team-level one (§6).
- **Header and totals row stay pinned during scroll.** In a deduction puzzle the totals are consulted constantly.
- Never hide columns to fit a screen — every visible number is part of an equation, so hiding one erases a constraint.
- The board is identical on all screens. Desktop gets more whitespace, not more content.
- **⚠️ Row counts, roster caps (≤10 batters / ≤3 pitchers), and erasure percentage are PROVISIONAL
  estimates, not decisions.** They are blocked on measurement: the real height budget from a browser
  prototype, and compressibility + technique distribution across the pool. Do not treat them as fixed
  and do not build them into code as constants without flagging it.

### 7. Puzzle quality outranks everything (§31, §22)

If a measurement shows the board is too small to produce puzzles that require T3–T5, **the board
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

- Compressibility — max % of cells removable while preserving uniqueness (expensive; run last)
- Zero density — penalize; forced-by-zero cells are not puzzles
- **Roster compactness, asymmetric:** the *offensive* team needs ≤10 batters, the *defensive* team ≤3 pitchers. Only those appear on the board.
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
- Access tokens: signed, short expiry (24h), signature verified server-side. Renewal is where devices are counted.
- Validate OAuth `state`. Magic links: single use, short lifetime.
- Sanity-check client-reported durations before storing, so absurd values don't corrupt percentiles.
- Rate limit per IP in nginx; do not persist IPs.
- No secrets in Docker images. Containers unprivileged.

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
