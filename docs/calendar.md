# The calendar artefact

**Written before the code, as the thing the code has to satisfy.** 2026-08-22, `docs/beta-0-plan.md`
group A. `§N` points at `docs/design-boxscore-puzzle.md`.

---

## What it is

**A date maps to exactly one puzzle, and that mapping is a decision rather than a computation.**

§21 says the assignment is *fixed and never recomputed*. So the calendar is **stored, not derived**:
there is no function from a date to a puzzle. There is a file that records what was decided, and a
builder that only ever adds to it.

That single sentence settles most of the format. A derived calendar could be regenerated from the pool
and a seed; a stored one has to survive, be extended without rewriting, and be checkable.

---

## ⚠️⚠️ It is the one artefact in this project that cannot be regenerated — and today's rules would not back it up

`.gitignore` holds `forge/inventory/`, and `CLAUDE.md` says **generated puzzle inventory never enters
Git**. That rule is right for packages: they are large, they are reproducible from the game, and §16
keeps the generator secret.

**The calendar is not that.** It is a few thousand bytes of decisions, and §21 makes it
**irreproducible by construction** — "fixed and never recomputed" means there is nothing to recompute
it from. §33 names the laptop as the single point of failure and Git as the backup.

**So: the calendar is committed.** It is an assignment table, not puzzle content, and the rule it looks
like it violates exists for a different reason than the one that would apply here.

⚠️ **It leaks nothing.** A puzzle id is a hash; without the package it names nothing. The repository is
private permanently in any case (§16).

⚠️ **Losing it is worse than losing the packages.** Packages regenerate from the same games. A lost
calendar means every past date's assignment is gone — and past dates are what streaks, shared results
and stats hang from (§21). **Nothing else in this repository has that property.**

---

## Two files, and one of them is derived

⚠️⚠️ **The calendar must carry `game_id` and the deployed one must not.** §7 strips `game_id` from a
published package precisely so a player cannot look the game up. But *one game, one puzzle* can only be
checked against the game — so the source of truth needs the very field the artefact is forbidden to
carry.

| | `forge/calendar.json` | what the VPS gets |
|---|---|---|
| holds | date, puzzle id, **game id**, direction, status, when it was assigned | date → puzzle id, and nothing else |
| lives | committed to Git | deployed with the generation |
| written by | the builder, append-only | **derived**, never hand-maintained |

⚠️ **Derived, with a test that they agree on every date.** Two files stating one mapping is this
project's most-met defect; the defence is that one is generated from the other and a check asserts the
agreement, rather than two things maintained in parallel.

⚠️ **A `game_id` reaching the VPS is a leak, not a tidiness problem.** It is the answer.

---

## The record

One entry per date. Enough to make every §21 rule checkable and nothing more:

- **`date`** — the calendar date, the key.
- **`puzzle_id`** — what is played that day.
- **`game_id` and `direction`** — the two fields *one game, one puzzle* needs, and the two that never
  deploy.
- **`status`** — `active` or `void`. §21: a defective **past** date is marked void and excluded from
  streaks and stats, **with the assignment left in place**. Deleting the entry would rewrite history,
  which is the thing forbidden.
- **`assigned`** — the generation this entry came from, so a board can be traced to the run that made
  it.
- ⬜ **`difficulty`** — the weekday curve (§31), **absent for now**. See the open question below.

---

## How it extends without rewriting

**The builder reads the calendar first and only writes dates that have no entry.** That is the whole
mechanism, and it makes the two §21 requirements the same requirement:

- **Idempotent** — running it twice adds nothing the second time, because every date it would write
  already has an entry.
- **Extends rather than rewrites** — it has no code path that touches an existing entry.

⚠️ **The immutability boundary is *today*, not *played*.** A date at or before today is frozen, full
stop. Trying to detect whether a puzzle was actually played means asking the data layer — which §23
forbids the play path from depending on, and which would make the forge know that users exist (§33).
**Today's date is a boundary the forge can evaluate alone.**

**Replacing a future date is the one write that is not an append**, and it is what §21 allows: a future
date whose puzzle turns out defective is replaced, because nobody has played it. It is a separate
command from the builder, it refuses any date at or before today, and it records the replacement rather
than overwriting silently.

---

## ⚠️⚠️ One game, one puzzle — the check the calendar exists to make possible

**The reveal prints both clubs** (schema 5). The other club's half **is the other direction's board**.
Publishing both directions of a game gives the second one away entirely, inside the first one's reveal,
before anyone plays it.

**No package can enforce this and no validation layer can see it.** Each file is individually perfect.
It is a property of the *set*, and the calendar is the only thing that holds the set.

**So the check runs against the whole calendar, every time, before anything is written**: no `game_id`
may appear twice, whatever its direction and whatever generation it came from.

⚠️ **What exists today is `write_reference_puzzles.refuse_second_direction`, and it is per-batch.** It
asks whether *this run* published both directions. The requirement is over everything ever published.
**A guard that only sees today's boards is the enforcement that already exists and is not enough.**

⚠️ **It also has to survive a void.** A voided past date still spent its game — the reveal was shown.
So the check reads every entry regardless of status, and voiding a date does **not** return its game to
the pool.

---

## What the client is allowed to see

⚠️ `manifest.json` currently lists **every** published puzzle, is public, and is never cached. With a
calendar behind it, **listing tomorrow's id is handing out tomorrow's puzzle** (A4.2, open).

The shape that follows: the client asks for *today* and the server answers with one id. The mapping is
server-side. **Nothing the client can fetch may enumerate the future** — which also means the deployed
calendar is read by the server, not served as a file.

---

## ⬜ The open question: the difficulty curve

§31 wants easy Monday and hard Saturday. **Nobody knows yet which rung is which** — that is what the
hand-solve pack measures, and the pack is unsolved.

**The format is designed so the answer can arrive late.** §21 freezes past dates and lets future ones be
replaced, so **applying a curve later is reordering future assignments** — a supported operation, not a
rebuild. The `difficulty` field is absent rather than guessed; a curve invented now would be a number
shaping the product with no measurement behind it (§7).

**Which of the two routes to take is the operator's**, and it is the next thing to decide:

1. **Build the calendar with no curve now.** Deploys sooner; the curve is applied to future dates when
   the pack comes back.
2. **Solve the pack first**, then build with the curve already in. Avoids the reordering pass.

**Either way the format is the same**, which is the point of writing it down first.
