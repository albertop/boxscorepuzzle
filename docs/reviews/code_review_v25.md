# Code Review v25

Date: 2026-08-20

## Result

Two new findings: one P2 and one P3. No P0 or P1 finding is reported.

This pass reviewed every file changed after v24: the game snapshot integration, local session store,
accumulated clock, attention follower, phone-shell wiring, and their browser tests. No Markdown file was
updated after v24, so the existing planning ledger was compared with the newly implemented behavior.

The v23 accessibility and thirds-key fixes remain closed and are not repeated. The new normal path is
coherent: a session is restored before drawing, saved after an entry and when attention stops, and its
elapsed duration excludes hidden and idle spans.

Known work already recorded in `docs/reviews/todo.md` is excluded where it remains true: reveal,
Done-time validation, routes, hints and errors in the shell, the hand-solve decisions, the remaining
six-pitcher measurements, the unexplained 8-stall coverage difference, the volume generator, and the
other unfinished product surfaces.

No tests, linters, type checks, builds, browser runs, storage simulations, or clock simulations were
performed during this review.

## Backend Architect

### v25-P2-01 - A structurally malformed saved session can prevent the board from opening

**Severity:** P2

**Locations:**

- `serve/engine/store.js:60`
- `serve/engine/store.js:64`
- `serve/engine/store.js:66`
- `serve/engine/game.js:218`
- `serve/engine/game.js:222`
- `serve/engine/game.js:223`
- `serve/engine/game.js:224`
- `serve/ui/phone/main.js:61`
- `serve/ui/phone/main.js:62`
- `serve/ui/phone/main.js:175`
- `serve/tests/engine.test.js:1059`

**Description:** `createStore.load()` treats every non-null, non-array JSON object as a valid session.
`game.restore()` assumes a much narrower shape: `entries` must support `Object.entries()`, `hinted` and
`firstWrong` must be iterable, and their contents and `elapsed` must have usable types.

The store's malformed-data test covers invalid JSON and valid JSON whose top level is not an object. It
does not cover an object with malformed fields. A value such as `{"entries":{},"hinted":7}` passes
`load()` and then throws `TypeError` in the `for...of` over `saved.hinted`. Invalid entry values can also
be installed into the game without passing the same whole-number rule as `enter()`.

The shell restores before drawing. Its top-level catch only converts `PackageError` into the catalogued
failure page; every other error clears the app and is rethrown. A malformed persisted object therefore
turns optional persistence into a boot dependency, contradicting the store's stated fail-soft boundary.

**Impact:** A bad session value can leave the player with no board at all until site data is manually
cleared. This is more severe than losing progress: the implementation explicitly chooses a playable
empty board over a persistence failure, but this shape reaches past that fallback and breaks the play
path.

**Reproduction:** Store the JSON string `{"entries":{},"hinted":7,"firstWrong":[],"elapsed":0}` under
the current puzzle's session key and reload. `store.load()` returns the object. `game.restore()` reaches
`for (const name of saved.hinted ?? [])`, attempts to iterate the number, and throws before `draw()`.
The shell clears `#app` and rethrows because the error is not a `PackageError`.

**Fix and rationale:** Validate the complete session shape before returning it or applying any part of
it. Require `entries` to be a plain object whose values are non-negative integers, require `hinted` and
`firstWrong` to be arrays of strings, and require `elapsed` to be a finite non-negative number. Let the
game continue filtering names that no longer exist. Validation must be atomic: if any field is malformed,
return `null` or refuse the restore before clearing and repopulating the current maps. Add malformed
object-field vectors, including wrong container and value types, and prove they produce a fresh playable
game rather than an exception or a partially restored session.

## QA / Reliability

### v25-P3-01 - The planning ledger still says persistence and the timer do not exist

**Severity:** P3

**Locations:**

- `docs/reviews/todo.md:2564`
- `docs/reviews/todo.md:2566`
- `docs/reviews/todo.md:2569`
- `docs/reviews/todo.md:2575`
- `serve/ui/phone/main.js:58`
- `serve/ui/phone/main.js:61`
- `serve/ui/phone/main.js:67`
- `serve/ui/phone/main.js:162`
- `serve/engine/clock.js:49`

**Description:** The current "What is actually left" section says `snapshot()` and `restore()` are
called by nothing, that there is no `localStorage` anywhere, that nothing survives a reload, and that no
clock is passed or wired. Those statements were true before the reviewed change and are false now.

The shell creates the store and clock, restores before drawing, saves after edits and attention loss,
and wires visibility plus inactivity through `followAttention()`. Other names in the same TODO item,
including `finish()`, `record()`, `hint()`, and reveal behavior, genuinely remain unwired, so leaving the
whole item unchanged hides which half is complete.

**Impact:** The project's authoritative work ledger directs the next implementation pass toward work
that is already present while obscuring the narrower tasks that remain. In a solo project this is the
practical documentation risk: the same programmer returns later and cannot tell implementation status
from the file intended to preserve it.

**Reproduction:** Read the `serve` item beginning at line 2564, then follow `boot()` in `main.js`.
Statements such as "No localStorage anywhere" and "No timer" are contradicted directly by the store,
restore, save, clock, and attention setup in the current shell.

**Fix and rationale:** Split the item by actual status. Mark snapshot restore, local saving, accumulated
duration, visibility pause, and inactivity pause complete. Leave finish/reveal, final event recording,
hints, errors, and any backend sync under remaining work. A planning ledger is useful only when a
completed seam and an unimplemented consumer are not represented by the same unchecked sentence.

## Other Personas

**Python Principal:** No Python files changed after v24, and no Python integration finding was found.

**Frontend Engineer:** The shell restores state before rendering and saves after normal keypad input.
The persistence boot failure is covered by v25-P2-01; no independent rendering finding was found.

**Security:** No practical confidentiality, authorization, credential, or code-execution finding was
found. Local storage is untrusted input, but the actionable consequence here is availability and is
covered by v25-P2-01; attack-scenario fields are not otherwise applicable.

**UX / Visual:** Normal restoration avoids a visible empty-to-filled flash, and the clock remains
invisible as required. The dead-board failure from malformed persistence is covered by v25-P2-01.

**Baseball / Boxscore:** The clock and persistence changes do not alter baseball values, innings
representation, line-score semantics, or package content. No new baseball finding was found.

**Kakuro / Logic-Puzzle:** Restored entries preserve the player's board and mistake history without
changing identities, uniqueness, or derivability. No independent puzzle-logic finding was found.

## Recommendation

Make session restoration atomic and fail-soft before relying on local persistence as part of the phone
boot path. Then update the TODO status so the next serve pass starts from the remaining reveal and event
work rather than rebuilding the store and clock that now exist.
