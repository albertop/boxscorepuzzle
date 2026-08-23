# `keep` — the data layer's API

**The surface, written before the service.** 2026-08-22. `docs/data-layer.md` is the architecture; this
is what it exposes and why each piece is shaped the way it is.

**The service is called `keep`** — one syllable, a verb, and what it does, beside `forge` and `serve`.

---

## What it is for

`serve` ships the game. `keep` holds everything about people: devices, events, and later accounts and
subscriptions. **`serve` never touches a database**, and nothing but `keep` does.

⚠️ **Its port is not published** and it accepts a shared token that must be configured or the service
does not start (`data-layer.md` §4). Every route below assumes both.

---

## ⚠️⚠️ The one thing that shapes the schema: a retry must not duplicate

**The client queues events and retries.** If `keep` received an event and the *response* was lost — a
dropped connection, a phone going to sleep, a proxy timing out — the client cannot tell that from a
request that never arrived. **It retries, and the event lands twice.**

**With events feeding streaks and percentiles, a duplicate is not harmless**: it is a second game that
never happened, at a duration that skews a distribution built from tens of players.

**The answer is a client-generated id on every event, which `keep` ignores if it already holds it.**

```
event_id   a UUID the client makes when the event is created, never when it is sent
```

⚠️ **Made at creation, not at send.** An id generated per *attempt* is a new id on every retry and
deduplicates nothing — which is the shape that looks correct and does the opposite.

⚠️⚠️ **It is in the schema from the first row because it cannot be retrofitted.** Adding it later leaves
every event written before it undeduplicable, and C7 makes that history permanent. **This is the same
argument as the device id and the claimable account field**, and it is the reason the API is written
before the service rather than after.

**Error reports carry one too.** The stakes are lower — a duplicated stack trace misleads nobody — but
two mechanisms for one problem is the duplication this project meets most often, and the second one is
free.

---

## The routes

### `POST /events`

The C7 record, as `game.record()` produces it. One event or a batch, because the queue drains in batches.

```
{ "events": [ { "event_id": "...", "device_id": "...", "account_id": null,
                "puzzle_id": "...", "calendar_date": "2026-09-01", "played_on": "2026-08-31",
                "duration_ms": 0, "hints": 0, "errors": 0, "failed_checks": 0,
                "highest_technique": null, "solved": true, "assisted": false } ] }
```

**Returns which ids it now holds**, so the client can drop exactly those from its queue:

```
{ "stored": ["...", "..."] }
```

⚠️ **`stored` rather than a count.** A count tells the client how many landed and not *which*, so a
partial success would force it to re-send everything — reintroducing the duplicate problem the id
exists to solve.

⚠️ **An id already held is `stored` too.** The client asked *is this recorded*, and it is. Reporting it
as a conflict would make the honest retry look like an error.

### `POST /errors`

Uncaught client errors (C4). Same shape of contract: an id, and `stored` back.

```
{ "errors": [ { "error_id": "...", "device_id": "...", "message": "...", "stack": "...",
                "page": "/p/abc", "viewport": "375x812", "user_agent": "..." } ] }
```

⚠️ **No IP, no geolocation** (§35). A user agent and a viewport are what reproduce a rendering fault;
anything past that is collected because it was easy.

### `GET /health`

⚠️ **Runs a real query** — `SELECT 1 FROM <a known table> LIMIT 1`. A live container with a dead database
answers exactly like a healthy one. **What is tested is that the query does not error**, not the row
count: a table legitimately empty on a fresh deployment is not an outage.

**Status and little else.** A public endpoint reporting that it cannot reach postgres at some host hands
out more than it needs to.

### ⬜ Later, and named so they are not invented ad hoc

`GET /access` for `canAccess` (beta 3), the archive endpoint that checks a subscription before returning
a past puzzle (E1b), and the metrics reads (§8). **None of them exist and none is designed here** —
naming them is so that the first person to need one finds a place rather than an absence.

---

## SQLite is a development convenience, not a supported engine — decided

⚠️ **This was left open in `data-layer.md` §2 and it belongs here, because it decides whether the
cross-engine contract suite is a promise or a courtesy.**

**Production is Postgres. SQLite exists so tests and local development need no server.** It is **not**
supported: a behavioural difference between the two is a bug **in the tests**, not in `keep`.

**What follows, and it is the honest half:**

- **The contract suite runs against both**, and a failure on SQLite means the *test* assumed something
  Postgres does not promise — or the reverse. It is a smoke alarm for the test suite, not a compatibility
  guarantee.
- ⚠️ **Local development runs on something that is not production, and that is a named risk.** Anything
  depending on Postgres behaviour — transaction isolation, `ON CONFLICT` semantics, type coercion — is
  only really exercised where Postgres runs.
- ⚠️ **So the deduplication above is tested against Postgres specifically**, because it is the one piece
  whose correctness rests on an upsert's exact semantics.

**Calling SQLite supported would be the more generous promise and the less honest one**: it would say a
green suite means the two agree, and nothing here checks that at the depth the word implies.

---

## Event retention: indefinite because nobody has decided otherwise

**Not "unlimited by design", and the distinction is the whole point.** Nothing deletes an event today:
percentiles need history and the volume at this scale is nothing.

⚠️ **Recorded as an open decision so the absence of a policy is never read as a decision to have none** —
the same shape as absence-of-a-check reading as a passing one.

**What would force one:** the table growing enough to affect query time, or a legal obligation appearing.
Neither is close.

---

## What is deliberately not in this API

- **Anything the play path waits on.** §23: the daily plays with `keep` down. Every route here is
  something the client does *after* a game, or something an operator's monitor asks.
- **Puzzle content.** `keep` holds people, `serve` holds puzzles, and the two never merge (§33).
- **Anything §35 does not list.** No real name, no IP, no geolocation, no filled cells.
