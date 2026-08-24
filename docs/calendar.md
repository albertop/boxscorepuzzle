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
whatever clock the build happens to run on — is preference; this one costs somebody their board mid-game.

| clock | when it lands in the US | |
|---|---|---|
| **UTC** | **19:00 Eastern** in winter, **20:00** in summer; 16:00 / 17:00 Pacific | ❌ The worst answer available. A player who sits down a quarter of an hour before it loses the board mid-game, every night, forever |
| **Midnight US Eastern** | 00:00 Eastern, **21:00 Pacific** | ❌ Splits the West Coast evening in half |
| **UTC−8** | **03:00 Eastern, 00:00 Pacific** (winter); 04:00 and 01:00 (summer) | ✔ Nobody in the contiguous states is at a board |

### ⚠⚠ The value, stated once, because three trees have to spell it

```
ROLLOVER_OFFSET_HOURS = -8
```

**`forge` holds a copy** because it decides which dates are frozen; **`publish` holds one** because it
runs the rotation on the VPS; ⬜ **`serve` gains one** when E1 builds the loader. §33 forbids them sharing
code — and `forge` must never reach the VPS at all — so **they share the rule by pointing here.**

⚠️ **Two of the three assertions exist today** (`forge/tests/test_inventory_build.py`,
`publish/tests/test_rotation.py`), and both were verified by changing the number above and watching them
go red. **`serve` owes the third**, recorded at E1.2 in the plan — and `forge`'s was a hardcoded `== -8`
until 2026-08-23, which is a third copy of the number wearing the clothes of a pointer.

⚠️ **This line is load-bearing, not decoration.** Each tree asserts its constant against the number
written above, so three spellings cannot become three answers. **No test can compare the trees to each
other**: each CI workflow ignores the others' paths, so a change on one side would not even run the
other's suite. The document is the only place all three can point at, which is what makes it the
definition rather than a description of one.

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
the new place rather than carry the conclusion across.**

### ⚠⚠ One constituency decides this, and the other zones are informative

**US Eastern and Pacific decide it, and nothing else does.** The argument above is a US argument and
should be read as one: 19:00 or 20:00 Eastern takes the board from somebody who sat down a quarter of an
hour earlier, and 03:00 or 04:00 Eastern catches almost nobody mid-board. **`UTC-8` is chosen because
the contiguous states span UTC-4 to UTC-8.** That is the whole of it.

The zones below are **translations, not constituencies.** A future reader weighing a clock change should
find one interest here, not three.

| zone | when the rollover lands | weight |
|---|---|---|
| **US Eastern / Pacific** | 03:00 / 00:00 winter, 04:00 / 01:00 summer | ✔ **decides it** |
| Santo Domingo | **04:00, year-round** (UTC-4, no daylight saving) | informative — see below |

### ⚠️ Santo Domingo was a target market at conception and is not one now — settled 2026-08-23

**Baseball is king there, and that is why it was considered.** The target is the United States. **A
player from Santo Domingo is welcome; Santo Domingo does not weigh on a decision.**

**The figure stays and is correct at 04:00.** Keeping it records that the market was once considered,
which is the same reason the superseded package-format documents are kept rather than deleted — a
history that is erased cannot be re-examined, and this one is exactly what a future argument for a
Caribbean market would need to pick up.

⚠️ **What was corrected on the way**: an earlier version of this section said *08:00 in Santo Domingo*,
which is simply wrong — that zone is UTC-4 and the rollover lands at 04:00, asleep like the mainland. **So
the figure never carried the argument even when the market was a target.** The reasoning does, and the
check is to re-derive it rather than to notice whether a number looks late.

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

**That was safe, and safe for a reason that is not a guarantee: the machine happened to be east of
UTC−8.** Anywhere east of the serving clock, the local day runs *ahead* of the serving day, so the
boundary froze more than it had to — conservative, and harmless. **It is a fact about where the build is
run, not about the code.**

⚠️ **At or west of UTC−8 it inverts.** Run the same build from Los Angeles at 23:00 and the local day is
*behind* the serving day — so the command that refuses to touch the past would let you replace a puzzle
already being served.

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

### ✔ The three commands beside `--days`, built 2026-08-23

All three live in `build_inventory.py` rather than beside it. **One producer, one audit, one manifest
path** — a second script would be a second ordering to get wrong, and the ordering *audit, then sign* is
the one thing that must not have two versions.

| | what it does | when |
|---|---|---|
| `--replace <dates>` | withdraws a future date's board and draws another | a rule found later disqualifies a board already assigned |
| `--restamp` | rebuilds every package that predates a fact the audit now needs, **asserts it is identical**, and writes it back | new metadata the population has to carry |
| `--republish` | re-signs the newest generation's manifest and every date's pointer; produces nothing | a run wrote boards and then failed its audit |

⚠️⚠️ **`--replace` inherits the era of the board it withdraws.** Four of the five boards withdrawn on
2026-08-23 were pre-1950, and §6 allows seven in a 150-day calendar. Drawing their replacements from the
modern half would satisfy the *ceiling* while spending the early allowance on nothing — and `spread()`
had already placed those four where the gap rule wanted them. Inheriting the era keeps both properties
without re-deriving either.

⚠️⚠️ **`--restamp` is a re-signing pass and must never become a regeneration.** `produce()` is
deterministic, so the same game at the same target yields the same board: no date changes, no puzzle id
moves. **Every field of the rebuilt package is compared against the published one before it is written**,
and a board that came back different stops the run as a finding about the producer. Writing it either way
would be an unlogged regeneration of the artefact this document opens by calling irreproducible.

⚠️ **`--republish` exists because the failure it recovers from actually happened.** The 2026-08-23
replacement wrote five packages and five calendar entries and was then refused — correctly — because 145
*other* boards carried no admissibility metadata. That left a generation on disk with no manifest and no
pointers: servable content nothing points at. **Recovery is a command rather than a repair by hand**,
because the alternative signs those two documents outside the one place that audits first.

⚠️ **A generation directory is `gen<hex seconds>` with a letter appended if that is taken.** Two runs in
one second is not a name clash: the manifest is built from *the files on disk*, so the second run would
sign a document claiming the first run's packages are its own.

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

### ✔ The rotation is the enforcement, and it exists — `publish/`, built 2026-08-23

When today's puzzle arrives, **the day before yesterday's must leave the public path.** A rotation that
fails once leaves that puzzle reachable, and **the archive leaks one day at a time** — slowly enough that
nobody notices, and permanently, since anything fetched once is gone.

`publish.rotate.rotate(inventory, public, when)` is the code. **The date is an argument, never read from
a clock inside it**, so a test controls the day without touching the machine; the 08:00 UTC boundary is
above, and `publish.rotate.serving_date()` is what a caller uses.

⚠⚠ **It is built by difference rather than by deleting a remembered third day**, and that is the
decision inside it worth stating. *Remove the day before yesterday* leaves anything an earlier run
failed to remove in place **forever** — so one missed run becomes a permanent leak instead of a
recoverable one. It computes the set that should be public and removes whatever else it finds, so a
rotation broken for a week repairs the whole week the first time it succeeds.

**So it is checked rather than trusted:** `publish.health.inspect()` asserts the public path holds no
more than two packages **and** that `today.json` names the date it actually is. ⚠⚠ **Two questions,
because neither catches the other's failure:** a rotation that stops deleting leaves a correct pair and
a growing directory; one that stops running leaves exactly two, both stale. A count passes the second
and a date passes the first. Uptime Kuma watches the endpoint that exposes it (`beta-0.md`, F3), and
**that endpoint is F** — the verdict is a function today.

⚠️ **Three of the rotation's tests were checked by removing the delete and watching which went red.** The
first version of the set-equality case pointed at an empty directory, so one run had nothing to remove
and it passed with the delete taken out entirely. **The assertion was never the weak part; the fixture
was.**

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

### ✔ That table is true as of E1, 2026-08-23. The marking is removed with it

**It read *E1b's end state; today the browser reads `manifest.json`* for one day.** `serve/ui/phone/daily.js`
fetched the manifest from the browser on both player pages and followed it to `<generation>/<id>.json`,
picking the id from the query string. **None of that is left.**

**What the code does now:** `daily.js` fetches `today.json` — and `yesterday.json`, which may legitimately
be absent — validates each through `readPointer`, and follows the one it wants to `<id>.json` on the flat
public path. `/p/<id>` takes the id from `location.pathname` and is refused unless it is one of the two
public days. `?p=` is gone.

⚠️⚠️ **The generation is in the pointer and the browser does not use it.** The *rotation* needs it to
find the package in the private inventory; the public path is flat. A reader who sees the field and
concludes the served layout is `<generation>/<id>.json` has the private shape in mind.

⚠️ **Three copies of a status were three things to remember to un-mark**, and the whole reason this
section owned the fact was that the forgotten one is the one somebody believes. All three came off
together: this, `docs/runbook-inventory.md` §5, and `write_manifest`'s docstring. **A fourth was found
while doing it and had been stale for a day** — `docs/serve-flow.md` §6 still carried *what time midnight
is is still open*, settled the previous day. It was not on the list because it was never marked: the
three that were tracked were tracked *because somebody wrote them down as owed*, and the one that went
stale by itself is exactly the one no list could hold.

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
   a future date, because only one exists. ✔ **This is what `publish/` does**, and it writes `yesterday.json`
   beside it for the rollover-boundary window. ✔ **And since E1 the browser reads exactly those two
   files** — `serve/ui/phone/daily.js`, validated through `readPointer` before either is trusted to name
   a package.
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

## ⬜ The cache rule per document — **a specification, not something in force**

⚠️⚠️ **Nothing enforces any of this today, and that is stated first on purpose.** Cache headers are a
server's, there is no server, and `tools/dev_server.py` is not deployed — it turns caching off entirely,
which is correct for development and is the **opposite** shape to production. This is the table **E3
implements**, written here rather than in the plan because `docs/calendar.md` already owns the access
model and one definition is the whole point.

⚠️ **E2 was folded into E3 for exactly this reason** (`docs/beta-0-plan.md`): a rule with no
implementation and nothing to verify it against is a sentence in a document, and this project has
recorded what becomes of those.

| document | rule | why |
|---|---|---|
| `today.json`, `yesterday.json` | **`no-store`** | they change daily, and **a stale pointer is indistinguishable from a rotation that did not run** |
| `<id>.json` | **`public, max-age=31536000, immutable`** | a package cannot change: a different board gets a different id |
| `manifest.json` (public) | **`no-store`** | written from the files actually placed; no browser reads it today, but it is on the public path and it names what is |
| `/today` | **`no-store`** | it is the same pointer wearing a URL (`docs/serve-brief.md`, v36-P3-48) |
| `/`, `/p/<id>`, the modules and CSS | **`no-store`**, or a short revalidation | they are the application, and a stale copy has twice refuted a change that was correct |

⚠️⚠️ **The reasoning is what survives a rename, and it had to.** E2.1 was written as *`manifest.json`
never cached, `<generation>/<id>.json` cached for a year*, and **since E1 the public path is flat and the
browser reads neither of those files**. The rule was unchanged by that because it was never about the
names: **what makes a document cacheable is whether it can change.** A rule stated against files that do
not exist is what E3 would have implemented.

### ⚠️⚠️ Order matters here, and it is not decoration

**The enforcement is the absent id. The cache rule is the belt.**

A package is named by an opaque id and **only two ids are public**, so tomorrow's puzzle cannot be
requested by anyone who cannot name it — and no intermediary or CDN can prefetch a URL it cannot
construct. **That is true today, with no code and no header.** *Cache only the current day, never the
week* sits on top of it.

⚠️ **Written the other way round, the cache header reads as the thing holding the line**, and the next
person to meet a slow first load relaxes it believing the exposure is a cache setting. It is not: it is
which ids exist publicly.

### ⬜ What must assert it, when E3 exists

**Nothing can today** — there is no configuration to compare against. When there is, the check is the
one the route set already has in a weaker form: **this table is the single definition, and something
reads it and the server block and requires them to agree.** ⚠️ Until then a check would be one that
cannot fire, and a check that cannot fire is indistinguishable from one that is broken — so the way it
fails matters: *there is no configuration yet* and *the configuration disagrees* must not look alike.

⚠️ **Nothing goes into `tools/dev_server.py`.** Production headers in a server whose entire purpose is
to switch caching off would be two opposite rules in one file, and the development rule exists for two
real ghost bugs — a regenerated generation served stale, and a prototype reported as *not rendering*
that was the cache.

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
