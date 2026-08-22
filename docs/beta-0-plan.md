# The route to beta 0

**The chart map.** `beta-0.md` says what beta 0 *is* and what counts as done; this says **how to get
there from here**, in groups and subtasks, with what each one depends on and what makes it finished.

Written 2026-08-22, against the repository as it actually stands rather than as the documents describe
it. ⚠️ Where the two differ, this file says so.

---

## The seven deliverables, in one table

Each group ends with an artefact somebody can point at. **If a group finishes and there is nothing to
point at, it did not finish.**

| | deliverable |
|---|---|
| **A** | five months of dated, signed inventory, **and the runbook that produces the next five** |
| **B** | a verdict on whether the inventory is humanly solvable, and a difficulty scale that means something |
| **C** | a client producing a complete, identified event and surviving its own failures, with no backend |
| **D** | a running service that stores events and refuses to run wrong |
| **E** | the real routes and the real caching contract, running locally |
| **F** | `boxscorepuzzle.com` serving today's puzzle, monitored |
| **G** | an image a player sends in one tap that survives the trip and gives nothing away |

⚠️ **Each deliverable also says what it does *not* give**, in its own section. That half is the one that
gets skipped, and it is where the milestone's honest limits live — deliverable B does not produce a
difficulty threshold, F does not answer whether anyone passes it on, G does not produce a recruitment
rate.

---

## Where we actually are

| | state |
|---|---|
| **Client** | landing, tutorial, board, keypad, hints, reference sheet, check, reveal, persistence — **built and tested** (236 browser tests) |
| **Packages** | schema 5, signed, four validation layers, `certify_for_publication()` — **built** |
| **Inventory** | **six reference puzzles**, one generation, hand-picked |
| **Calendar** | **does not exist** |
| **Batch generation** | **does not exist.** `write_reference_puzzles.py` publishes a hand-chosen set |
| **`/today`** | **does not exist.** `daily.js` reads the manifest and takes an id from the query string |
| **Device UUID** | **does not exist** |
| **Event upload** | **does not exist.** `game.record()` produces the C7 event; nothing sends it |
| **Data layer** | **does not exist.** Designed in `data-layer.md` |
| **Share PNG** | **does not exist.** The button is drawn and `disabled` |
| **Deployment** | **does not exist.** `compose.yaml` is a dev server on a mounted tree, no image, no nginx |

### ⚠️⚠️ Three facts about the current code that shape the plan

**1. The publication path imports its loader from `discovery/`.** `write_reference_puzzles.py` does
`from measure import Loaded, load` — the SQL, the connection string, the era windows and the provenance
predicate all live in `discovery/difficulty-metrics/measure.py`, outside `mypy --strict` and inside the
ratcheted lint tree. The deferral is recorded in the file with its reason: **moving it is building the
inventory pipeline, not renaming a module.** That is group A, and it is the first subtask rather than a
cleanup at the end.

**2. `game.record()` has no date.** C7 in `CLAUDE.md` lists *puzzle_id, date, duration, hints, errors,
highest technique*. The record has `puzzle_id, duration_ms, hints, errors, failed_checks,
highest_technique, solved, assisted` — **no date of any kind.** A streak hangs off the calendar date and
an archive play is a different date from the puzzle's; neither is recoverable later, and C7 is
irreversible. **This is a group C subtask and it is cheap now.**

**3. `build_pack.py` still targets chain and asserts fifty.** The generator targets a stall count; the
pack producer is the last chain-targeted code in the tree. Group B cannot start against it as it stands.

---

## Group A — inventory and calendar

**Blocks everything.** Nothing downstream can be tested against one day's puzzle.

### ✔ A1. Promote the loader out of `discovery/` — **done 2026-08-22**

- **A1.1** Move `Loaded` and `load()` into `forge/src/boxscore_forge/` (a `pool` module), with the SQL,
  the era windows, the provenance predicate and the caps.
- **A1.2** Fix the signature that lies: `gated: bool = False` while the gate always applied. It is
  recorded in the docstring; make the parameter mean what it says or delete it.
- **A1.3** Bring it under `mypy --strict` and un-ratchet those lines from the discovery baseline.
- **A1.4** Leave `discovery/` importing the promoted module, **not a copy.** Every discovery script that
  calls `load()` must keep working — that is the regression surface.
- **Done when:** `write_reference_puzzles.py` has no `sys.path` insert into `discovery/`, the suite is
  green, and the discovery scripts that load still run.

✔ **Done.** `boxscore_forge.pool`; `measure.py` re-exports and 33 scripts are untouched;
`test_the_shim_exports_what_is_imported.py` parses every `from measure import` in the tree and asserts
each name resolves *and is the same object* the pool holds. It caught a real break on its first run —
`ruff --fix` had removed `ZERO_DENSITY_GATE` from `measure.py`, correctly, and one script imported it
through there.

⚠️ **What `mypy --strict` found once the code was in `src/`, invisible in `discovery/` for months:**
`_sum` was annotated `-> object` and fed three `Direction` arguments expecting `BattingLine`,
`BatterFootnotes` and `PitchingLine`. **The annotation was hiding three real type errors rather than
passing them.**

⚠️ **A1.2 resolved by counting first: 37 call sites, all `gated=True`, none `False`.** The default is
`True` now — an omitted argument must not silently widen the population to nine parts unshippable
boards. Deleting the parameter is recorded as a deferral with its price (37 call sites in scripts that
need a database), not as an oversight.

### A2. Batch generation

- ✔ **A2.1 done 2026-08-22.** `boxscore_forge.produce.produce()` is the per-board core — promoted out
  of `write_reference_puzzles.py` so both producers share one definition — and
  `scripts/build_inventory.py` is the batch driver. `boxscore_forge.publication_key` holds where the
  signing key comes from, for the same reason.
- ✔ **A2.2 done 2026-08-22 — and the answer removes work rather than adding it.** Two samples, 48
  directions, **48 boards: the pipeline loses none.** So the batch does not over-sample and needs no
  retry machinery. **~22 minutes for 150 boards.** What sizes the draw is duplicate games — `load()`
  returns both directions of one game about 10% of the time and the calendar refuses the second (§7) —
  so **draw ~1.15× the dates**. ⚠️ **235 attempts and the publication gate refused none**, recorded in
  `todo.md` as an open question about the gate rather than a clean bill of health.

  **✔ Confirmed at volume 2026-08-22:** the real 150-board run spent 566 more attempts and the gate
  refused **none of them**. Roughly **716 attempts, zero certification refusals**, which stops being a
  small-sample result.
- ⚠️ **A2.3 NOT done, and the successful run hides it.** `build()` writes the calendar **once, after the
  loop**. A crash at board 140 of 150 leaves 140 signed packages on disk and **loses every assignment**,
  because nothing was written yet. What works today is the *short-run* case — the run finishes, keeps its
  work, and exits non-zero (v38-P2-01) — which is not the same thing as surviving a crash. **Checkpoint
  the calendar as it goes.**
- ⬜ **A2.4 not asserted.** §21 needs the same game to yield the same puzzle id, and nothing runs a slice
  twice and compares. Trusting `puzzle_id()` is the thing the item says not to do.
- **Done when:** one command produces N validated packages with a recorded survival rate, and running it
  twice produces no duplicates.

### ✔ A3 (core). The calendar module — **done 2026-08-22**

`boxscore_forge.calendar`, written test-first, 26 tests, **100% coverage**, and every rule tested by its
refusal. `docs/calendar.md` is the artefact it implements. §21's two requirements turn out to be one
mechanism, and *one game, one puzzle* runs over the whole calendar including voided entries.

⚠️ **A guard of mine could not fail, and mutation is what found it.**
`test_an_existing_entry_is_never_replaced` used `next(...)` over a sorted list, so with the skip removed
from `extend()` the calendar held two entries for one date and the test stayed green — `sorted` is
stable and the original came first. Six mutations checked in total; all six now go red.

**What is left of A3** is the builder that feeds it: the weekday curve (deferred, see below), the
pre-1950 allowance, and the quota assertions.

### A3. The calendar

- **A3.1** The date → puzzle assignment, persisted, **extends and never rewrites** (§21). A played date
  cannot change; a future defective puzzle is replaced, a past one is marked void and left in place.
- ⬜ **A3.2 deferred — operator's decision 2026-08-22: build the calendar with no curve.** Nobody knows
  which rung is Monday until the hand-solve pack comes back, and §21 makes applying a curve later a
  *reordering of future dates* rather than a rebuild. The `difficulty` field is absent rather than
  guessed (§7). Originally: difficulty by weekday — easy Monday, hard Saturday (§31) — and vary which relation families a
  level opens with, so no two Tuesdays start the same way.
- ✔ **A3.3 done.** `extend()` refuses a game the calendar has already spent, over the whole book and
  including voided entries. Verified on the real batch: **150 dates, 150 distinct games.**
- ❌ **A3.4 NOT implemented — and the inventory built on 2026-08-22 violates it by seven times.**

  §6 is explicit and still decided: *pre-1950 boards must not exceed 5% of what the player sees*,
  roughly eighteen a year, so that Ruth is an **event rather than the scenery**. The batch is
  **51 of 150 pre-1950 — 34%, against a ceiling of 8.**

  ⚠️⚠️ **It is not bad luck, it is the sampler.** `load()` draws *n per decade* over twelve decades, so
  a stratified draw **guarantees** the pre-war half is over-represented: 1910s through 1940s is four
  decades of twelve, and the quota allows one board in twenty. **A calendar built from a decade-flat
  draw can never satisfy a decade-weighted quota by accident.**

  ⚠️ **Nothing caught it.** Not the gate, not the four layers, not the calendar's own refusals — a
  board from 1913 is perfectly valid and so is a calendar full of them. It was found by printing the
  decade distribution and reading it, which is the only thing that has ever found this class here.
- ⬜ **A3.5 not implemented, and its absence is exactly why A3.4 went unnoticed.** The item says assert
  the quotas after construction rather than print them and believe them. There is no assertion, so the
  run reported `assigned 150 of 150` and was wrong about what it had assigned.
- **Done when:** five months of dates are assigned **within every quota**, the guard rejects a second
  direction of a published game, and re-running the builder changes nothing.

### A4. Packaging in bulk

- **A4.1** Generation directory and manifest at 150+ puzzles. The manifest is schema 1 and lists every
  id; check that shape still makes sense at scale, since the client fetches it uncached on every load.
- **A4.2** ⚠️ **The manifest must not leak the future.** It currently lists every published puzzle. With
  a calendar, listing tomorrow's id is handing out tomorrow's puzzle — the file is public and
  unauthenticated (§23). **Decide what the client is allowed to see.**
- ✔ **A4.3 done.** 150 packages signed with the pinned key; `boxscore_forge.publication_key` refuses to
  return a key `serve` would not accept, and never prints private material.
- ⬜ **A4.1 partial.** The generation directory exists (`forge/inventory/<gen>`, 1.4 MB, median 9.7 KB a
  package). **No manifest is written**, and A4.2 has to be decided before one can be.
- **Done when:** a generation of five months is written, signed, and verifies from a clean checkout.

⚠️ **A4 is not the end of group A.** What A1–A4 produce is one batch, built by whoever had the whole
pipeline in their head that week. **A5 is what makes it a process.**

### A5. The runbook — `docs/runbook-inventory.md`

**How to add new games to the app**, written for the person who will actually run it: **the operator,
three months later, having forgotten all of it.** That is not a rhetorical framing — §33 alerts below
three months of runway, so **the interval between two runs is measured in months by design**, and
whatever is obvious today will not be obvious then.

- **A5.1 Preconditions**, each one checkable before anything starts: the Retrosheet database reachable,
  the signing key present (⚠️ and **where it is not** — never in the repository), a clean working tree,
  and how much runway is left right now.
- **A5.2 The commands, in order**, with **what each one prints when it is working.** A step whose success
  looks like silence is a step nobody can tell failed.

  ⚠️ **Three instances of exactly that, all from the first measurement run, all before it produced a
  number.** They belong in the runbook because each one cost minutes of not knowing whether anything was
  happening:

  1. **Python buffers stdout when it is not a terminal**, so the run printed nothing for eight minutes
     while working. Every line flushes now.
  2. **`load(n)` is `n` per decade**, over twelve decades — `--directions 12` asked for about 144
     directions. The option is `--per-decade` now. ⚠️ *A name that misdescribes a scale factor of twelve
     is the same defect as `gated: bool = False`: read far more often than it is passed.*
  3. **Piping a live run through `tail` withholds all of it until the process exits.** An instrumentation
     mistake rather than a script one, and the runbook has to say *do not pipe this* or the operator will
     conclude the command hangs.
- **A5.3 What to check before publishing**: the survival rate, the era share, the weekday spread, and
  ⚠️ **the one-game-one-puzzle guard's report** — the check no package can perform on itself.
- **A5.4 What to do when the yield is short.** The likely outcome, not the exceptional one: the gate keeps
  11% of the pool. Say whether to widen the era window, lower the target, or run again — and ⚠️ **what
  must never be done, which is quietly dropping a rung to fill a quota.**
- **A5.5 How to deploy the new generation**, and **how to roll back.** ⚠️ Not near the daily rollover.
- **A5.6 Why re-running is safe.** §21: puzzle ids derive from the game, the calendar extends and never
  rewrites, so a run that half-finished is resumed rather than cleaned up. **State it explicitly** —
  somebody who is unsure whether a second run will duplicate things will hesitate at exactly the moment
  the runway is short.

⚠️⚠️ **A runbook that has never been followed literally is a guess.** It gets executed once, from a clean
checkout, by doing exactly what it says and nothing the author remembers — and corrected wherever it was
wrong. **The same rule as every other instrument here: the version that has not been run is not evidence.**

⚠️ **And it will drift from the code**, because prose and commands are two places saying one thing. The
cheapest defence is that the commands it names are the ones a test invokes; at minimum, the runbook names
the scripts by path so a rename breaks a grep rather than nothing.

### ⚠️⚠️ Status 2026-08-22: the batch ran and **Deliverable A is not met**

**What exists:** 150 dates, 2026-09-01 to 2027-01-28, one game each, 150 signed packages, 25.1 minutes
from 168 directions. Verified against the artefacts rather than the run's own summary — contiguous, no
holes, every date has a package, **zero game ids survive into what deploys**.

**What the difficulty spread looks like**, which matters because a later curve has to have material to
reorder: stalls 1–13 with a median of 9, and all twelve rungs represented. 39% of boards needed the
lineup clue. **11 of 150 (7%) depend on the batting-order family** — the first time that number has been
answerable at all, since `FAMILY_OF` gained the fifth family the day before.

**Why it is still not met, in order of weight:**

1. ❌ **34% pre-1950 against §6's 5% ceiling** (A3.4). The calendar has to be rebuilt or reweighted.
2. ⚠️ **No quota assertion** (A3.5), which is why the run said `150 of 150` and was wrong about what it
   had assigned.
3. ⚠️ **No crash resumability** (A2.3): the calendar is written once at the end.
4. ⬜ **No manifest** (A4.1/A4.2), **no idempotence assertion** (A2.4), **no runbook** (A5).

⚠️ **The 150 dates are assigned and committed, and that is deliberate.** §21 lets a *future* date be
replaced, so reweighting the eras replaces entries rather than rebuilding the file — and the calendar is
the one artefact here that cannot be recomputed, so having it on disk and in Git beats having it correct
and only in memory.

### ▶ Deliverable A — **five months of dated, signed inventory, and the runbook that produces the next five**

**Two things, and the second is what makes the first repeatable.**

**The inventory:** a generation directory and a calendar — roughly 150 validated packages, each assigned
to a date, signed, verifying from a clean checkout, with the one-game-one-puzzle guard refusing a second
direction over **everything ever published**.

**The runbook** (`docs/runbook-inventory.md`): how to add new games to the app, **followed literally once
before it is believed.**

⚠️ **The runbook is not documentation of the deliverable; it is half of it.** Five months of inventory
with no repeatable way to make more is a product with a five-month expiry date — and the moment it needs
running is the moment the inventory health check goes amber (F3), which is precisely when nobody wants to
be rediscovering how the generator is invoked. **§33's three-month alert is only useful if there is
something to do about it.**

**What it makes possible that nothing before it did:** every other group can be tested against a daily
game that lasts more than a day. Group B has an inventory to draw a sample from; E has something to
route `/today` at; F has something to deploy. **And the product stops having an expiry date.**

⚠️ **What it does not give:** any evidence that a person can solve these boards. Four validation layers
say the numbers agree with each other. **That is group B, and it is a gate rather than a follow-up.**

---

## Group B — the hand-solve gate

**Depends on A.** It draws from the shipping inventory. **It is a gate on beta 0** (`beta-0.md`), and it
is pass-or-stop rather than a rate.

### B1. Re-axis the pack producer

- **B1.1** `build_pack.py` targets chain and `audit()` speaks in chain rungs. Move both to stalls.
- **B1.2** Keep `audit()` asserting rather than printing, and keep its seven rejecting tests.
- **Done when:** the producer builds a stall-targeted pack and the audit rejects a missing rung.

### B2. Pack A — calibration, sixteen boards

- Rungs 5, 8, 11, 12, four each. Stall count off the page and in the sealed key. Formula strip with all
  five relations. Survey box with the 1–6 scale, the *how many times did you stop* line, and separate
  columns for **had to guess**, **tedious**, **boring**. Randomised order asserted by `audit()`. One
  board per game. Footnote line given. A final ranking sheet.
- ⚠️ **If rung 12 does not yield four boards, that is the finding** — reported, never quietly
  substituted with a lower target.
- ⚠️ **Not built at the end of a long run.** It gets a fresh session: the instrument is a person, the key
  is sealed, and a board printed wrong is an afternoon spent on the wrong thing.

### B3. The derivability sample — the gate

- **B3.1** Sheets with no survey and no ranking: *did it solve without guessing*. Cheap per board, which
  is what makes a larger N affordable.
- **B3.2** Stratify over what could break the assumption: stall rungs weighted hard, era, roster shape
  (⚠️ especially boards that only became eligible when the pitcher cap went to six), and boards that
  depend on the **batting order** family.
- **B3.3** ⬜ **N and the stratum quotas are open**, and `audit()` asserts them after selection.
- **Done when:** every board in the sample solved by hand without guessing. **One failure stops the
  milestone** — it falsifies the assumption the publication rule rests on.

### B4. The stranger's ten

- Ten boards across the curve, solved by somebody who knows baseball and nothing about this project. It
  is the one contrast the operator cannot give himself. **Calibration, not a gate.**

### ▶ Deliverable B — **a verdict on whether the inventory is humanly solvable, and a difficulty scale that means something**

Two artefacts. **The gate's verdict:** every board in the stratified sample solved by hand without
guessing — or a stop, with the board that failed. **And Pack A's sheets plus the ranking**, which is the
only thing that tests whether the stall scale corresponds to felt difficulty.

**What it makes possible:** shipping at all. Until this exists, *the puzzle is solvable* is an assumption
the four layers cannot check.

⚠️ **What it does not give:** a difficulty threshold. The operator is a sample of one with complete
command of the identities; what he finds easy will be easy for very few. **The absolute question is
answered by beta 0's own event records**, which is group C.

---

## Group C — the client: identity, the event, and errors

**Can start in parallel with A.** ⚠️ **C1 is the one thing with an asymmetric cost — every event before
it exists is unattributable, and C7 is irreversible.**

### C1. The device UUID

- **C1.1** A random UUID in `localStorage`, created once, surviving reloads.
- **C1.2** ⚠️ Its own key and its own lifetime — **not inside the per-puzzle session**, which is keyed
  `boxscorepuzzle.session.v1.<id>` and is disposable.
- **C1.3** ⚠️ Survive the storage failing. `browserStorage()` already handles a refused storage; a device
  with no storage plays anonymously rather than not at all (§23).
- **Done when:** the UUID persists across reloads and across finishing a puzzle, and a blocked storage
  does not break the game.

### C2. The event record gains what C7 promised

- **C2.1** ⚠️ **Add the date.** C7 lists it and `record()` has none. Both the puzzle's calendar date and
  the date it was played — they differ for archive play and neither is recoverable later.
- **C2.2** Add the device UUID, and the account field as `null` — the schema is claimable from the first
  row (`data-layer.md` §6), and that cannot be retrofitted.
- **Done when:** a finished game produces a record carrying identity and both dates, asserted in a test.

### C3. Upload, queued and offline-first

- **C3.1** Write to `localStorage` first, always. **Nothing in the play path waits on the network** (§23).
- **C3.2** A queue that drains when there is a connection and survives a reload mid-flight.
- **C3.3** Idempotent on the receiving side: a retried upload must not double-count.
- **Done when:** finishing with the network off, then restoring it, delivers exactly one event.

### C4. Uncaught client errors

- **C4.1** `window.onerror` and `unhandledrejection`, posted with the device UUID, message, stack, page,
  viewport and user agent. **No IP, no geolocation** (§35).
- **C4.2** ⚠️ **Fails silently and never blocks.** A reporter that throws or waits turns one broken
  render into a broken game.
- **C4.3** Rate-limit itself, so a render loop does not post ten thousand times.
- **Done when:** a deliberately thrown error arrives at the endpoint and the board still plays with the
  endpoint refused.

### ▶ Deliverable C — **a client that produces a complete, identified event and survives its own failures, with no backend at all**

A finished game yields a C7 record carrying the device UUID, an account field that is `null` and
claimable, and **both dates**. It queues in `localStorage`, drains when there is a connection, and
delivers exactly one event across a reload mid-flight. Uncaught errors report themselves and can never
block the play path.

**What it makes possible:** the moment a data layer exists, **events recorded before it existed still
arrive**, carrying the identity they were created under. That is the whole reason this group precedes D.

⚠️ **What it does not give:** anywhere for the events to go. They accumulate locally until D exists —
which is the design working, not a gap.

---

## Group D — the data layer

**Depends on C for its shape and on nothing else.** Designed in `data-layer.md`; this is building it.

### D1. The service

- **D1.1** One API, engine behind an interface. Postgres in production, SQLite for development and tests.
- **D1.2** ⚠️ **One contract suite parameterised on the backend**, not two suites. A suite green on
  SQLite says nothing about Postgres and says it convincingly.
- **D1.3** Shared-token auth that **fails closed at startup** — no token, no service. Constant-time
  comparison; the token never in a log or a URL.

### D2. Schema and migrations

- **D2.1** Events, devices, and the claimable subject: device UUID always, account when one exists.
- **D2.2** ⚠️ **Migrations are manual; startup refuses an unexpected schema version.** Neither half works
  alone — manual without the check gives silent drift, the check without manual gives a deploy the power
  to alter data at 3am.
- **D2.3** §35 only: no real name, no IP, no geolocation, no filled cells.

### D3. Endpoints

- **D3.1** Event upload. **D3.2** Client error reports. **D3.3** Health, running
  `SELECT 1 FROM <a known table> LIMIT 1` — ⚠️ testing that the query does not error, **not** the row
  count.
- **Done when:** the contract suite passes on both engines, the service refuses to start without a token
  and against a wrong schema version, and health goes red when the database is stopped.

### ▶ Deliverable D — **a running service that stores events and refuses to run wrong**

The data layer, against the Postgres already on the VPS, with a contract suite **green on both engines**.
It will not start without its shared token, will not start against an unexpected schema version, and its
health endpoint goes red when the database is stopped rather than when the container dies.

**What it makes possible:** the events from deliverable C have a destination, and the error reports have
one — so beta 0 stops being deployable-blind.

⚠️ **What it does not give:** any of the subscription side. No accounts, no `canAccess()`, no Stripe.
Those are beta 3 and the schema is shaped so they are an addition rather than a migration.

---

## Group E — serving for real

**Depends on A** (there is a calendar to serve) **and on D** (there is somewhere to post).

### E1. `/today` and `/p/<id>`

- **E1.1** C6: `/p/<id>` canonical, `/today` redirects. `daily.js` currently takes an id from the query
  string — that is development scaffolding and it goes.
- **E1.2** ⚠️ **The engine still does not know what day it is** (C4). A loader decides, server-side.
- **E1.3** Everyone gets the same puzzle on the same date — **never derived from device-local state.**

### E2. The caching contract

- **E2.1** `manifest.json` never cached; `<generation>/<id>.json` cached for a year (it is immutable).
- **E2.2** ⚠️ **Cache only the current day, never the week** — caching ahead leaks future puzzles.

### E3. nginx

- Server block, TLS via certbot, rate limit per IP **without persisting IPs**, and the data layer
  reachable only on the internal network.

### ▶ Deliverable E — **the real routes and the real caching contract, running locally**

`/p/<id>` canonical and `/today` redirecting, with the day decided **server-side** and never from
device-local state — everyone gets the same puzzle on the same date. `manifest.json` never cached,
`<generation>/<id>.json` cached for a year, and **only the current day cached ahead**.

**What it makes possible:** what runs on the laptop is now the shape that will run on the VPS, so
deployment is moving a known-good thing rather than discovering the difference in production.

⚠️ **What it does not give:** a live site. Everything here is still on `localhost`.

---

## Group F — deployment

### F1. Images

- **F1.1** A Dockerfile for `serve` — ⚠️ **`serve/` only.** Generator code must never reach the VPS.
- **F1.2** A Dockerfile for the data layer.
- **F1.3** No secrets in images. Containers unprivileged. The data layer's port **not published**.
- **F1.4** ⚠️ The VPS holds the **public** signing key. The private key never leaves the laptop.

### F2. The VPS

- DNS record, certbot, compose file, the existing nginx and Postgres. ⚠️ **Do not deploy near the daily
  rollover**, and have a rollback that is one command.

### F3. Health checks in Uptime Kuma

- Free daily · subscription · data layer (proxied — ⚠️ **unreachable is unhealthy**, never 200 with
  *unknown*) · **puzzle inventory**, which is the one nobody would think of: `serve` can be perfectly up
  with an empty directory. Threshold in one place, status only, no detail.

### ▶ Deliverable F — **boxscorepuzzle.com serving today's puzzle, monitored**

The site live over TLS on the operator's domain, `serve` and the data layer in their own containers on
the existing Docker network, the data layer's port unpublished, and **four Uptime Kuma checks** — the
free daily, the subscription side, the data layer proxied, and the puzzle inventory's runway.

**What it makes possible:** friends and family can play. This is the first moment the product exists
outside the laptop.

⚠️ **What it does not give:** the answer to the milestone's larger question. At this point beta 0 can
tell you whether people play and whether they come back. **Whether they pass it on is group G**, and it
is why G cannot be cut for time.

---

## Group G — the share

**Last to build, and ⚠️ it does not get cut** (`beta-0.md`). Fifth is a dependency — the PNG draws from
the finished game — not a priority.

### G1. The image

- **G1.1** ⚠️⚠️ **It is not a picture of the reveal.** The reveal prints names, teams and date;
  screenshotting it publishes the whole answer. §7: never the solution, never player names.
- **G1.2** ⚠️ **Replace the values first, then blur.** The blur is typography, not security — deblurring
  is solved and the glyph set is ten digits in a known typeface. An implementation that blurs real values
  is broken and looks identical to one that is not.
- **G1.3** The time and the failed-check count, **using the same catalogue keys as the reveal** — one
  number must not have two names in the artefact whose purpose is comparison.

### G2. One tap

- `navigator.share` where it exists, clipboard where it does not. **Any friction here is friction on the
  only growth mechanism the product has.**

### G3. ⚠️ Verified by sending, not by generating

- **G3.1** Send it through **WhatsApp, iMessage and X**, open it on a real phone, look at what arrived.
- **G3.2** ⚠️ **A local harness supplies the compression, the colour profile, the aspect ratio and the
  scaling** — every property under test. Generate-and-inspect is what every other visual check in this
  project has failed at.
- **Done when:** the image survives all three apps intact and a recipient who has not played learns
  nothing about the board.

### ▶ Deliverable G — **an image a player sends in one tap that survives the trip and gives nothing away**

A PNG carrying the grid, the time and the failed-check count in the reveal's own words — **not a picture
of the reveal**, with values replaced before any blur — shared through `navigator.share` in one tap, and
**verified by being sent through WhatsApp, iMessage and X and opened on a real phone.**

**What it makes possible:** beta 0 answers the question it exists for. §20 calls the shared grid the main
growth channel, and this is the only chance to test it before a paying product rests on it.

⚠️ **What it does not give:** a recruitment rate. The recipients are friends of friends. *Does the
artefact survive the trip* is fully answered here; *does it recruit* is not, and the two must not be
reported as one verdict.

---

## The order, and what can overlap

```
A ──────────────────────────────► B (gate)
│                                  │
├─► C (client) ──► D (data layer) ─┤
│                     │            │
│                     ▼            ▼
└──────────────► E (serving) ──► F (deploy) ──► G (share)
```

- **A is the critical path.** B, E and F all wait on it.
- **C can start today** and should, because C1's cost is asymmetric.
- **D depends on C** only for the event's shape.
- **G is last and exempt from cutting.**

⚠️ **Two things gate the milestone rather than merely being in it:** B3 — one board failing by hand stops
everything — and G, which cannot be dropped for time.

---

## What is open before starting

- ⬜ **B3's N and stratum quotas** (`beta-0.md` scope question 1).
- ⬜ **A4.2 — what the manifest may reveal**, now that a calendar means there is a future to leak.
- ⬜ **The data layer's name.** `keep` proposed.
- ⬜ **Whether SQLite is supported or only convenient** (`data-layer.md` §2).
- ⬜ **The API surface**, which no document has written down yet.
