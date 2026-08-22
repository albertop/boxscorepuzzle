# The route to beta 0

**The chart map.** `beta-0.md` says what beta 0 *is* and what counts as done; this says **how to get
there from here**, in groups and subtasks, with what each one depends on and what makes it finished.

Written 2026-08-22, against the repository as it actually stands rather than as the documents describe
it. ⚠️ Where the two differ, this file says so.

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

### A1. Promote the loader out of `discovery/`

- **A1.1** Move `Loaded` and `load()` into `forge/src/boxscore_forge/` (a `pool` module), with the SQL,
  the era windows, the provenance predicate and the caps.
- **A1.2** Fix the signature that lies: `gated: bool = False` while the gate always applied. It is
  recorded in the docstring; make the parameter mean what it says or delete it.
- **A1.3** Bring it under `mypy --strict` and un-ratchet those lines from the discovery baseline.
- **A1.4** Leave `discovery/` importing the promoted module, **not a copy.** Every discovery script that
  calls `load()` must keep working — that is the regression surface.
- **Done when:** `write_reference_puzzles.py` has no `sys.path` insert into `discovery/`, the suite is
  green, and the discovery scripts that load still run.

### A2. Batch generation

- **A2.1** A producer that takes *how many boards, at what stall targets, over what era spread* and
  returns validated packages. `build()` in the writer is the per-board core and already certifies.
- **A2.2** ⚠️ **Yield is unknown at volume.** The gate keeps 11% of the pool, erasure fails, layers
  reject. Measure the survival rate on a small run **before** launching a five-month batch, so the batch
  is sized from a number rather than from hope.
- **A2.3** Resumability. A run that dies at board 400 of 450 must not start over.
- **A2.4** ⚠️ **Idempotence (§21):** the same game must yield the same puzzle id. Assert it by running a
  slice twice and comparing ids, not by trusting `puzzle_id()`.
- **Done when:** one command produces N validated packages with a recorded survival rate, and running it
  twice produces no duplicates.

### A3. The calendar

- **A3.1** The date → puzzle assignment, persisted, **extends and never rewrites** (§21). A played date
  cannot change; a future defective puzzle is replaced, a past one is marked void and left in place.
- **A3.2** Difficulty by weekday — easy Monday, hard Saturday (§31) — and vary which relation families a
  level opens with, so no two Tuesdays start the same way.
- **A3.3** ⚠️⚠️ **The one-game-one-puzzle guard, over everything ever published.** Not over a batch.
  `refuse_second_direction` is per-run and is not enough. **This needs the whole published history as
  input, so it is a property of the calendar's state.** A calendar without it leaks puzzles: the reveal
  prints both clubs and the other club's half *is* the other direction's board.
- **A3.4** The pre-1950 allowance: at most 5% of what a player sees (§6).
- **A3.5** Assert the quotas after construction, never print them and believe them — the rule
  `CLAUDE.md` records from the weighted draw that produced zero boards at the easiest rung.
- **Done when:** five months of dates are assigned, the guard rejects a second direction of a published
  game, and re-running the builder changes nothing.

### A4. Packaging in bulk

- **A4.1** Generation directory and manifest at 150+ puzzles. The manifest is schema 1 and lists every
  id; check that shape still makes sense at scale, since the client fetches it uncached on every load.
- **A4.2** ⚠️ **The manifest must not leak the future.** It currently lists every published puzzle. With
  a calendar, listing tomorrow's id is handing out tomorrow's puzzle — the file is public and
  unauthenticated (§23). **Decide what the client is allowed to see.**
- **A4.3** Signing at volume; the private key never leaves the laptop.
- **Done when:** a generation of five months is written, signed, and verifies from a clean checkout.

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
