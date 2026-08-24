# `keep` — the data layer's API

**The surface, written before the service.** 2026-08-22. `docs/data-layer.md` is the architecture; this
is what it exposes and why each piece is shaped the way it is.

**The service is called `keep`** — one syllable, a verb, and what it does. ⚠️ **It is no longer the only service:** `publish/` arrived 2026-08-23 with the serving side's executables. `keep` remains the only thing that touches a database, which is the boundary that matters here.

---

## What it is for

`serve` ships the game. `keep` holds everything about people: devices, events, and later accounts and
subscriptions. **`serve` never touches a database**, and nothing but `keep` does.

⚠️ **Its port is not published** and it accepts a shared token that must be configured or the service
does not start (`data-layer.md` §4). Every route below assumes both.

### ⚠⚠ What the browser actually posts to — added 2026-08-22, when the client was built

**The browser never reaches `keep`.** It posts to **`/api/events`**, **`/api/errors`** and
**`/api/shares`** on `serve`, which proxies them and adds the token at the edge — the same arrangement
as the health check and the payment webhook, and for the same reason: *a secret inside a container is a
secret; an open port is surface.*

✔ **All three exist**: the proxy since F1, 2026-08-24, tested against a real `keep` and Postgres
(`deploy/nginx/boxscorepuzzle.conf.template`), and `/api/shares` since G on the same day. ⚠️ **The
client's own `Authorization` header is discarded rather than merged**, so a browser cannot influence
what `keep` sees; the edge decides every time.

### ⚠️ The case that shaped the retry rule, and no longer occurs

**Before the proxy existed these paths answered 404**, and that is what the client's retry rule was
written around: **a 404 leaves the queue intact.** Everything a player recorded while the route was
missing was delivered by their first visit after it appeared, and nothing had to be thrown away in the
meantime.

**The rule outlives the case and is why it is kept here rather than deleted.** `outbox.js` still treats
404 as *a route that does not exist **yet***, never as *this item will never be accepted* — deliberately
not "any 4xx". The distinction is what makes adding a fourth route safe: a client shipped before it
keeps whatever it recorded, instead of discarding it on the first attempt.

⚠️⚠️ **This paragraph said *those two paths do not exist yet, so today they 404* until 2026-08-24** —
directly beneath the line saying the proxy exists, added above it and never reconciled. **A superseded
sentence surviving under its own replacement is the shape this project keeps meeting**, and the reason
it was not simply deleted is that it carried the retry rule's whole justification.

---

## ⚠️⚠️ The one thing that shapes the schema: a retry must not duplicate

**The client queues events and retries.** If `keep` received an event and the *response* was lost — a
dropped connection, a phone going to sleep, a proxy timing out — the client cannot tell that from a
request that never arrived. **It retries, and the event lands twice.**

**With events feeding streaks and percentiles, a duplicate is not harmless**: it is a second game that
never happened, at a duration that skews a distribution built from tens of players.

**The answer is a client-generated id on every event, which `keep` ignores if it already holds it.**

```
event_id   an id the client makes when the event is created, never when it is sent
```

⚠️ **Made at creation, not at send.** An id generated per *attempt* is a new id on every retry and
deduplicates nothing — which is the shape that looks correct and does the opposite.

⚠⚠ **The client makes it from the device and the puzzle, not as a UUID — and this line said "a UUID"
until the client existed.** `${device_id}:${puzzle_id}` satisfies *made at creation* more strongly than
a random one does: a board reopened after a reload, or a reveal shown twice, produces **the same id**,
so the duplicate is impossible rather than deduplicated after the fact. It needs no ledger of what has
already been queued and no extra field in the saved session, both of which would be a second mechanism
for one problem.

⚠️ **What it costs, stated because a reader will otherwise assume it costs nothing:** a device records
exactly one event per puzzle, ever, so a deliberate replay of an archived board is silently discarded.
Nothing in §27 says a replay should count — yesterday's board does not count for the streak either — so
the safer direction is the one taken. **If replays are ever meant to record, this is the line that
changes**, into a fresh id per play, and `serve/engine/outbox.js` carries the same note.

**Error reports keep a random id**, because there the occurrence *is* the thing: two stack traces from
one render loop are two events, not one retried.

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

### `POST /shares`

One press of *Share* on a finished game. Same contract again: a client-made id, and `stored` back.

```
{ "shares": [ { "share_id": "...", "device_id": "...", "puzzle_id": "...",
                "event_id": "..." | null, "channel": "native" | "clipboard",
                "shared_on": "2026-08-31" | null } ] }
```

#### ⚠️⚠️ Why this is a route and not a field on the event

**The share happens after the game is uploaded**, and `keep`'s insert is `ON CONFLICT DO NOTHING` —
which is the whole reason a client retry is free. So a `shared` field on the event could never be
filled in afterwards: re-sending the event with it set would be **ignored, silently**. The two ways
around that are both worse — waiting for a share before uploading the event delays every upload for
something most players never do and loses the event when the tab closes.

**A share is an event, which is what C7 says to store.**

#### ⚠️⚠️ What this measures: intent, never reach

**The browser cannot tell whether a share was delivered.** `navigator.share` resolves when the sheet
closes — on some platforms whether or not anything was sent — and a clipboard copy says nothing about
whether it was ever pasted. A row here means *the player pressed Share and the mechanism responded*.

**Read later as "how many people shared", it is a metric correctly computed and measuring something
else** — the shape `CLAUDE.md` records under *what the player does when the number goes up*. Whoever
reports on this table states the limit with the figure or the figure is misleading.

#### ⚠️⚠️ A second press does not make a second row, and `channel` is therefore the FIRST channel

`share_id` is `<device_id>:<puzzle_id>` — **the device and the puzzle, and nothing else.** With
`ON CONFLICT DO NOTHING` behind it, that means a player who presses *Share* three times leaves **one
row**, and the `channel` on it is whichever mechanism answered the **first** time. A player who copies
to the clipboard and then shares natively is recorded as `clipboard`.

**Three surfaces can now produce that press** and all three go through one function
(`serve/ui/phone/share-result.js`), so this holds wherever it is pressed:

| | |
|---|---|
| the reveal | the screen the player reaches by finishing |
| the landing, on a day already solved | added with the exit, because a player who leaves the reveal must still be able to tell somebody |
| a reopened board's reveal | the same screen again, on a later visit |

**So the column means *shared at least once*, and it is deliberately not a count.** A counter would be
the honest alternative and it costs the free retry: `POST /shares` is retried after a lost response, and
a counter cannot tell a retry from a second press — it would inflate the one number the growth mechanism
has, in the direction that flatters it. Idempotence is worth more here than the second press.

⚠️ **Whoever reports on `channel` states this**, or the split reads as a preference when it is a record
of which sheet opened first.

#### The two fields that carry decisions

| | |
|---|---|
| `channel` | **required**, `native` or `clipboard`, an **acceptance list**. The two have different semantics and a combined figure erases the only distinction that lets the number be read. A third channel arrives by being added to `SHARE_CHANNELS`, not by a client sending a word nobody has seen |
| `event_id` | **present and null**, never absent — the rule `account_id` follows on an event. **No foreign key**: events and shares travel in separate batches and the share can land first, or the event can be lost. Refusing the share would discard the growth mechanism's only measurement to protect a reference nothing reads |

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

### ⚠⚠ An obligation the metric reads inherit: **yesterday does not count for the streak**

**Decided 2026-08-22** (`docs/calendar.md`, and §27 beside the grace day): yesterday's board is playable
and **does not keep a streak alive.** Two forgiveness mechanisms stacked make a streak nearly
unbreakable, and an unbreakable streak stops being worth keeping.

**It is written here because this is where the code lands.** A game finished on yesterday's board records
its event like any other — C7 stores what happened — so **the exclusion belongs to whatever computes the
streak, and that is a read over many events, which only `keep` has.** The client knows one game, its own.

⚠️ **Recorded at the destination rather than only at the origin.** `beta-0-plan.md` carried this as
E1b.5 and E cannot build it; taking it off E's ledger without writing it onto this one is how a
decided-but-unbuilt rule goes missing — the origin stops counting it and the destination never starts.

✔ **Nothing new has to be stored for it.** The event already carries **both dates** (C2):
`calendar_date` says which puzzle, `played_on` says when somebody sat down. A streak hangs off
`calendar_date`, and the exclusion is a comparison the stored row already supports.

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
