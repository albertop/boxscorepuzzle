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

## ⚠⚠ What clock defines the day — **UTC−8, fixed; the day rolls at 08:00 UTC.** Decided 2026-08-23

**§36 carried *what time the puzzle rolls over: local midnight or UTC* as an open item and nothing could
be built on top of it.** `date` above is the key of every entry and the subject of every §21 rule, and
until this sentence existed it did not name a clock.

### It is one question, not two — the client's clock was never available

The obvious framing is *server's clock or client's clock*. **The second one is already closed**, by
`CLAUDE.md`: *everyone gets the same puzzle on the same date; never derive the day's puzzle from
device-local state.*

⚠️ **And the reason it is closed is stronger than the one usually given.** *Two players in the same house
could see different puzzles* is true and is the mild version. The hard version is that **a device clock is
something the player sets**: deriving the day from it makes changing a phone setting a way to fetch
tomorrow's board — the archive leak of §9, reached from the client instead of from a URL. So the design
question is only **which single clock**, and *local midnight* was never one of the answers.

### Which clock, and one constraint decides it

**The rollover must not land while people are playing.** Everything else — tidiness, neutrality, matching
the operator's own day — is preference; this one costs somebody their board mid-game.

| clock | when it lands in the US | |
|---|---|---|
| **UTC** | **20:00 Eastern**, 17:00 Pacific | ❌ The worst answer available. A player who sits down at 19:45 Eastern loses the board fifteen minutes later, every night, forever |
| **Midnight US Eastern** | 00:00 Eastern, **21:00 Pacific** | ❌ Splits the West Coast evening in half |
| **UTC−8** | **03:00 Eastern, 00:00 Pacific** (winter); 04:00 and 01:00 (summer) | ✔ Nobody in the contiguous states is at a board |

### ⚠️ A fixed offset rather than a named zone, and that is deliberate

`UTC−8` is an offset, **not `America/Los_Angeles`**. A named zone observes DST, which buys one hour of
alignment and costs a 23-hour day, a 25-hour day, an ambiguous local time twice a year, and a timezone
database on both sides.

**The hour it would buy is between 03:00 and 04:00 Eastern.** Both are hours nobody is playing, so the
drift the DST zone exists to prevent **has nothing to prevent** — and the arithmetic becomes
`(utc_now − 8h).date()`, which has no edge cases to get wrong.

### ⚠⚠ What this rests on, because it is the third thing resting on it

**§10's premise that the audience is US baseball fans.** That premise already carries the payments
decision (Stripe rather than a merchant of record) and the English-first decision, and `CLAUDE.md` says
those two *are not independent any more — an argument for a Caribbean market would have to move both or
neither.* **This is now the third.**

⚠️ If the audience premise ever moves, this moves with it — and the rule is to **re-derive the reason in
the new place rather than carry the conclusion across.** A rollover at 03:00 Eastern is 08:00 in Santo
Domingo and 10:00 in Madrid: correct here, and silently wrong there.

### The consequence for the two dates on the event, which is the same question asked twice

C2 put **two dates on every C7 record**, on two different clocks, and this is what makes them disagree:

| | clock | example |
|---|---|---|
| `calendar_date` | **this one.** Which puzzle it was | `2026-08-23` |
| `played_on` | the **player's**, from `localDate()`. When somebody sat down | `2026-08-24` |

**A player on the East Coast at 01:00 on the 24th is still on the 23rd's puzzle**, and both statements
are true at once. Neither is recoverable from the other once the row is written, which is why there are
two of them rather than one.

⚠️ **And the streak falls out of it rather than needing a rule.** A streak hangs off `calendar_date`, so
the night owl at 01:00 keeps the streak alive on the day they believe it is — they have not slept, so
they have not had a new day. That is a property of the choice, not a concession added to it.

### ⚠⚠ The forge has to compute the same date, and it was computing a different one

`build_inventory.py` used `date.today()` — **the local day of whoever ran the build** — to decide which
dates are frozen (§21: at or before today cannot be assigned or replaced).

**That was safe, and safe for a reason that is not a guarantee**: Madrid is nine or ten hours ahead of
UTC−8, so the forge's boundary was always *ahead* of the serving day and it froze conservatively. **It
is a fact about where the operator is sitting.** Run the same build from a laptop in Los Angeles at
23:00 and the boundary falls behind the serving day — and the command that refuses to touch the past
would let you replace a puzzle already being served.

The forge computes the serving date now, from the same rule.

⚠️ **Two implementations of one rule, and that is the prescribed arrangement rather than an
oversight.** §33 forbids `forge` and `serve` sharing code, and `CLAUDE.md`'s constants rule says a
decided value lives in **one module per tree, never one module shared**, *because §33 is exactly the
boundary a shared one would break.* So the guard is that each side names this section as its source.

⚠⚠ **No test can compare them**, and that limit is named here rather than discovered: `ci-forge.yml`
ignores `serve/**` and `ci-browser.yml` ignores `forge/**`, so a change on one side does not even run
the other's suite. It is the same limit already recorded for the event's field list, and the same
answer: the reminder goes red on the side where the change is made.

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

## ⚠️⚠️ The access model: static delivery and paid access are in tension — decided 2026-08-22

**Read this before the section below it.** That section solves a smaller problem and was written first;
this one is the reason the shape is what it is.

### The tension, and both halves are decided

**§23: the day's puzzle is a static file.** That is what makes the three nines true — with the backend
down, the file carries everything and the game still plays. Nothing decides whether to serve it.

**§9: the free tier is today's puzzle; the archive is what a subscription buys.** That is the business.

**A static file on a public path cannot be sold.** Anyone can request `/p/<old-id>.json` and get it — no
server is asked. **And the manifest listed every id**, so nothing even had to be guessed.

⚠️⚠️ **`canAccess()` is in the client, and a lock in the client over public files is not a lock.**

**The archive could not be sold, because it was already published.**

### ⚠️ And my framing of A4.2 was too narrow

The section below worried about **the future** leaking — tomorrow's id in a public manifest. True, and the
smaller half. **The past is the product**, and it was fully public with a list pointing at it. Fixing the
manifest's forward half would have left the whole business model unenforceable and looked like a fix.

### The decision: two puzzles on a public path, today's and yesterday's

**Nothing else.** The resolution is **two paths rather than one**, which lets the two decided properties
coexist:

- **Today and yesterday are static files**, on a public path, unauthenticated. §23 holds: the daily plays
  with the backend down.
- **Everything else is on no public path at all.** A past puzzle is requested from an endpoint that
  checks the subscription before returning the file. §9 holds: the archive is served *because* it is
  controlled.

**The daily is static because it needs no control; the archive is served because it does.**

### Why yesterday, and why that is not generosity

**Someone who starts at eleven at night and does not finish loses their work at midnight.** With two days
they finish it. **And two days is not an archive** — it does not compete with what the subscription
sells.

### ⚠️⚠️ The rotation is the enforcement, and it has to actually happen

When today's puzzle arrives, **the day before yesterday's must leave the public path.** A rotation that
fails once leaves that puzzle reachable, and **the archive leaks one day at a time** — slowly enough that
nobody notices, and permanently, since anything fetched once is gone.

**So it is checked rather than trusted:** the inventory health endpoint asserts **the public path never
holds more than two packages**, and Uptime Kuma watches it (`beta-0.md`, F3). ⚠️ A rotation is a moving
part whose failure is silent; the check is what makes it loud.

### ⚠️⚠️ `canAccess()` decides what the interface offers, not what the server returns

**Someone reading `canAccess()` later could reasonably assume it gates access. It does not and cannot.**
It runs in the browser, over files the browser can already fetch. What it decides is what the interface
*shows* — whether the archive button is there, whether a date is offered.

**The enforcement is which files exist on a public path.** That sentence is the whole access model, and
it lives in the deployment rather than in the code. C8 in `CLAUDE.md` calls it *a single decision point*,
which is true about presentation and would be a dangerous thing to believe about access.

### ⚠️⚠️ Yesterday is playable and does **not** count for the streak — decided 2026-08-22

**Playable and counting are not the same thing.** Yesterday's board can be opened and solved; solving it
does not keep a streak alive. §27 carries the same decision beside the grace day, and **the two rules
have to be read together** — this window is meaningless without knowing what it does to a streak, and the
grace day is meaningless if the window quietly provides a second one.

**Two forgiveness mechanisms stacked make the streak nearly unbreakable, and an unbreakable streak means
nothing.** §27 already provides one: a free grace day each month. *"Yesterday is always available and it
counts"* on top removes the last way to lose.

⚠️ **The second day answers a different question.** It exists so somebody who starts at eleven at night
can finish — **a rollover boundary, not a second grace day.** From outside they look identical, and that
resemblance is why leaving it implicit would have granted a grace day nobody decided to give.

---

## What the client is allowed to see — decided 2026-08-22

⚠️ `manifest.json` lists **every** published puzzle, is public, and is never cached. With six reference
packages that is harmless. **With a calendar behind it, listing tomorrow's id is handing out tomorrow's
puzzle.**

### ⚠️⚠️ The tension, because the obvious fix breaks something the manifest exists for

`sign_manifest`'s own docstring states it: *"altering it breaks no package signature — omit ids, point at
a retained generation, point at nothing, and every package the client does receive still checks out. A
signature on each puzzle says each puzzle is genuine; **only this says the set is.**"*

So the two requirements pull opposite ways. **A manifest that lists everything protects the set and
leaks the future. A manifest listing only today leaks nothing and protects nothing.**

### The split, and it is principled rather than a compromise

**Ask what set-integrity protects against, and the answer differs by audience.**

- **The client** needs one guarantee: *this is the puzzle for this date, and the forge says so.* A
  **signed pointer per date** gives exactly that. Substituting another genuine package for today fails
  its signature; omitting today is an error the player sees.
- **The operator and `serve`** need the other one: *this deployed generation is complete and
  unmodified.* That is the full manifest — **a deployment check, not a browser fetch.**

| artefact | who reads it | says |
|---|---|---|
| `manifest.json` | `serve` and the operator, **never the browser** | the generation is whole |
| `days/<date>.json` | the browser, one at a time | this id is this date's, **and this is the generation it lives in**, signed |
| `<generation>/<id>.json` | the browser | the puzzle, immutable, cached a year |

### ⚠⚠ A pointer names the generation that owns its package — not the one that wrote the pointer

**The two differ the moment there is a top-up**, which is the second build rather than an exotic case.
Every build writes a complete pointer schedule over the whole calendar, so the newest generation's
`days/` is the rotation's source — an older one was written before the later dates existed and has no
pointer for them. But **the packages stay where they were made**, and `Entry.assigned` is what records
that.

⚠️ **This was wrong until 2026-08-22 (v39-P1-01).** `write_pointers` stamped the generation it was
currently writing onto every date, so the first top-up would have pointed generation-A dates into B —
where their file does not exist. A 404 on a legitimately assigned date, **signed by the forge**, so the
wrong pairing read as authoritative rather than being caught. The parameter is gone now: the pointer
reads `entry.assigned` and there is no way to pass a different answer.

**What follows for the deploy:** every generation the calendar names must still be on the VPS, not just
the newest one. `docs/runbook-inventory.md` §6c is the check.

### ⚠️ Dates are guessable, so the pointers cannot simply be served

`days/2026-09-02.json` is not a secret name. **Something has to know what day it is**, and there are two
ways:

1. **A daily job copies today's pointer into the served root** as `today.json`. Nothing served can name
   a future date, because only one exists.
2. **nginx serves `days/<date>.json` only when the date is not in the future.** No daily job, but one
   configuration rule stands between the whole calendar and the world.

**Decided: the daily copy.** Not because it is simpler — it is a moving part and the other is not — but
because **its failure is visible and the other's is silent.** A job that does not run leaves yesterday's
puzzle in place, which players notice within hours and the inventory health check (F3) can catch by
comparing the pointer's date to the actual one. A misconfigured location block publishes five months of
answers and looks exactly like a working server.

⚠️ **The job needs no key.** All 150 pointers are signed at generation; the daily step is a copy. The
private key stays on the laptop (§16, §33).

### ⚠️ And the naming is what makes any of this work

**Package files are named by their opaque id, never by date.** §7 chose that so a player could not look
the *game* up — and it turns out to be the same property that stops anyone enumerating the *future*. A
board at `2026-09-02.json` would be readable by anyone who can add a day to a date, whatever the
manifest said.

**So the id is load-bearing twice, for two unrelated reasons, and only one of them is written down.**
That is exactly the shape `CLAUDE.md` records about mechanisms acquiring hidden dependents — recorded
here so that a future change to how packages are named meets both reasons rather than one.

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
