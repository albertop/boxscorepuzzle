# The data layer

**Standing direction, the way `serve-brief.md` is for the client.** Decisions taken 2026-08-22, written
before anything was built.

## ✔ Built 2026-08-22 — `keep/`, and what the build changed

**The service exists**: `keep/` beside `forge/` and `serve/`, **no runtime dependencies**, three routes,
77 tests at 100% coverage across both engines. `docs/keep-api.md` is the surface it was built against.

**Verified against a real Postgres in Docker**, which is the whole reason the contract suite exists.

⚠⚠ **Its Postgres arm fails rather than skips, and that changed the day after it was written.** A skip
is honest about itself and was still wrong here: without a server `PostgresStore` is **80%** covered and
the suite is **92%**, under its own 95% floor **while looking green** — so the floor only held on a
machine that happened to have Docker running, which is a guarantee true where it was written and nowhere
else. The tempting repair was a fake connection; it would have reached 100% and proved nothing about
Postgres. **Postgres is production; its store is tested against Postgres.**

⚠️⚠️ **One thing the build taught that the design did not contain.** `INSERT OR REPLACE` keeps exactly
one row too, so **every count-based test passed with it** — and it overwrites the original with the
retry's values. A queued event whose clock kept running would rewrite what happened. **C7 stores what
happened and the first telling is the one that did.** There is a test for it now, pinning both engines to
the same *meaning* rather than the same row count.

⚠️ **The token is checked before the schema, and the order is asserted**: a missing token is the failure
whose absence is silent, while a wrong-shaped database at least surfaces in a query error.

⚠⚠ **v39-P2-01, closed 2026-08-22 — one bad row was an outage, and the design did not contain this
either.** A failed statement leaves the Postgres transaction *aborted*, and Postgres then refuses every
later statement on that connection. `keep` reuses one, so a single out-of-range integer took down every
upload, every error report **and the health check** — the endpoint that reports an outage was extending
one past its cause — until the process was restarted.

Every statement rolls back on failure and **re-raises**: rolling back and reporting success would make a
lost write look like a stored one, and the client would drop it from its queue on the strength of that.
The rollback repairs the *connection*; what happened to the row is still an error. The `INTEGER` range
is checked at the boundary too, so the ordinary cause never reaches the driver.

⬜ **What that still leaves open, and it is a product number rather than a bug** (§7): `CLAUDE.md` asks
for a *sanity check on client-reported durations so absurd values do not corrupt percentiles*. The
column's range is twenty-five days, so a duration far past absurd is still storable. There are no
percentiles yet. `docs/reviews/todo.md`.

✔ **Built at F1, 2026-08-24, and tested end to end:** `deploy/keep.Dockerfile` — unprivileged, no secret
in the image, `EXPOSE` without publishing — and the nginx block in `deploy/nginx/` proxying
`/api/events` and `/api/errors` with the shared token added **at the edge**, where the secret already
lives and the browser cannot see it. `forge/tests/test_the_proxy_reaches_keep.py` posts an event through
the edge and requires `keep` to report it **stored**.

⚠️ **Until it is deployed the two paths 404, and that is by design** — a 404 leaves the client's two
queues intact, so everything recorded before deployment is delivered by the first visit after it.

⬜ **What still belongs to F2**, and is absent rather than written and unverified: *reachable only on
the internal network* is a property of the running VPS rather than of any file here, so nothing in this
repository can assert it.

⚠️ **The compose file it used to say did not exist is `deploy/compose.yaml`**, written 2026-08-24.
`keep` publishes no port there and the two services share the VPS's existing `backend` network. **What
that buys is smaller than the sentence above once promised**: `backend` is shared with every other site
on the host, so the unpublished port keeps `keep` off the internet and not away from its neighbours.
The token is what stands between it and them, and it always was.

---
 Where a question is still open it says so; those are not implementation
details left to whoever writes the code first.

`§N` points at `docs/design-boxscore-puzzle.md`.

---

## 1. A third tier, in its own container

`forge` generates and never leaves the laptop. `serve` ships the game. **The data layer is the third,
beside `serve` in the same Docker network**, and it owns everything about people: accounts, devices,
subscriptions, and the event records C7 mandates.

⚠️ **This is not a new pattern being introduced.** The operator already runs applications this way with
good uptime; the arrangement is the one already in use and already understood, which is most of the
argument for it.

**What it buys, and it is not tidiness.** §33 wants three domains with independent lifecycles, and the
one that keeps breaking is the boundary between the application and the data it happens to be sitting
on. With the data behind its own service:

- **`serve` deploys without touching the data.** The application redeploys freely, which is the
  property §33 names and the one a shared process quietly removes.
- **`serve` stops being the mandatory door.** Metrics, reports, an admin tool, a future tablet or
  desktop client — each talks to the data layer directly rather than reaching through the game. A
  reporting query that has to enter through the player-facing application is a reporting query that
  will one day take the player-facing application down with it.

**It is called `keep`** — one syllable, a verb, and what it does. ⚠️ **No longer the only service** — `publish/` holds the serving side's executables since 2026-08-23 — but still **the only thing that touches a database**, which is the boundary this document is about. Decided
2026-08-22. **Its API surface is `docs/keep-api.md`**, written before the service because it decides
everything after it.

---

## 2. The database is behind an interface

**`serve` never knows which engine is underneath.** The data layer exposes one API; whether Postgres or
SQLite answers it is not a fact any caller can observe.

✔ **Built.** `keep.store.PostgresStore` and `SqliteStore` behind `Store`, one contract suite over both.

**Postgres first.** The operator already runs and maintains an instance on the VPS. That removes
SQLite's main argument — one fewer piece to administer — and it avoids a migration later, which is the
expensive half of the decision rather than the choice itself.

**SQLite stays for local development and tests**, where its simplicity is the point.

### ⚠️⚠️ Two engines behind one interface is this project's most-met defect wearing a new coat

Two implementations of one contract are **two places that should say the same thing**, and every serious
defect in this repository has been exactly that. The specific danger here is not that the two disagree —
it is that **the tests run against the one that is not in production**, so the disagreement is invisible
until a player meets it. A suite that is green on SQLite says nothing about Postgres, and it says it
convincingly.

**The rule that follows: one contract suite, run against both engines.** Not two suites. The same tests,
parameterised on the backend, so an engine that behaves differently fails rather than diverges. Postgres
is a service container in GitHub Actions and costs little — ⚠️ though note it would land in `weekly.yml`,
since the push workflows were cut back on 2026-08-22 (`docs/ci.md`); a cross-engine suite that only runs
weekly is a real gap and needs deciding when the code exists, not assumed away here.

✔ **Closed 2026-08-22 in `docs/keep-api.md`: SQLite is a development convenience, not a supported
engine.** A behavioural difference between the two is a bug in the *tests*. The reasoning below is what
the decision was taken against and is kept for it.

⬜ *Was open: whether SQLite is a supported engine or only a development convenience.* They are different
promises. If it is supported, the contract suite is mandatory on every run and a behavioural difference
is a bug. If it is a convenience, the honest statement is *local development runs on something that is
not production* — a named risk rather than a hidden one.

---

## 3. ⚠️ What must keep working when the data layer is down

**The free daily puzzle plays.** The package carries everything it needs, state lives in `localStorage`,
and events upload when they can. §23's three nines rest on this and on nothing else. **Never introduce a
data-layer dependency into the play path** — that is §23 and C1, and it does not bend.

**The subscription side cannot work and must not pretend to.** With no data layer there is no way to know
who someone is or whether they paid. `canAccess()` **returns false**: the player meets the ordinary gate,
not an error, and the daily keeps playing behind it.

### The subscriber-in-an-outage problem, decided

**A subscriber locked out by an outage is a paying customer getting nothing.** Acceptable for thirty
seconds. Not for thirty minutes.

**Decision: the subscription state travels in the access token, and no new cache is built.**

⚠️ **This invents no parameter, which is most of why it is the right shape.** `CLAUDE.md` already decides
the vehicle: *access tokens: signed, short expiry (24h), signature verified server-side; renewal is where
devices are counted.* Putting the subscription state inside that token means `canAccess()` reads a
signature `serve` already verifies, and answers without asking anyone. **The token is the cache** —
signed, expiring, already understood — rather than a second thing with its own lifetime to keep in step
with the first.

**What it costs, stated rather than discovered.** A cancellation or a failed payment does not take effect
until the token expires: **up to 24 hours of access somebody has stopped paying for.**

⚠️ **The asymmetry is deliberate and is the point.** Both errors are possible and they are not equal — a
day of free access to a leaver costs one day of one subscription; a paying subscriber shown the gate
costs the subscription. **The default must favour the person who paid.**

**The ceiling on the tolerance is the token's expiry, and that is correct.** An outage longer than 24
hours does eventually gate everyone, because renewal needs the data layer — renewal is where devices are
counted. That is the point at which `canAccess()` returning false is the honest answer rather than a
failure of the design.

⬜ **Deliberately not built: a grace renewal.** Letting a just-expired token extend itself while the data
layer is unreachable would raise the ceiling, and it would bypass the device count, which is the one
thing renewal exists to do. It is machinery against an event that has never happened here. **Build it if
a real outage crosses 24 hours**, and not before.

---

## 4. Authentication between `serve` and the data layer

**A shared token in an environment variable.** `serve` sends it, the data layer compares it, a mismatch
is rejected.

They sit on the same Docker network and both belong to the operator. **Mutual certificates would be
disproportionate** — and a mechanism nobody can rotate confidently is worse than a simpler one that gets
rotated.

**Two conditions, and neither is advisory:**

- ⚠️⚠️ **Fail closed. No token configured means the service does not start.** Never *accept everything
  because there is no token*. This is the same defect as verification that passes when its secret is
  missing, which `CLAUDE.md` records under *fail closed at boundaries* — **the absence of a check reading
  as the presence of a passing one.** It refuses at startup rather than at the first request, so a
  misconfiguration is a container that will not come up instead of an open door nobody notices.
- **The data layer's port is not published to the host.** Internal network only. The token is the second
  line of defence, not the first.

**Two things that follow and are easy to get wrong:** the comparison is constant-time, and the token
never reaches a log, a URL, or an error message. A secret in a query string is in the access log forever.

### ⚠️⚠️ The payment webhook: `serve` receives it, verifies the signature, then forwards

**Decided.** Stripe posts to `serve`. `serve` verifies the signature **before anything else happens to the
request**, and only then forwards to the data layer over the shared token.

**Unverified webhooks are the highest-value attack in this system** — a forged notification grants a free
subscription. `CLAUDE.md` already says verification fails closed: a missing or unconfigured secret is an
error, never a pass.

**The alternative was publishing a data-layer port so Stripe could reach it directly, and it loses.** The
counter-argument against this shape is real — it puts the payment secret in `serve` rather than in the
service that owns subscriptions — but **a secret inside a container is a secret; an open port is surface.**
Verifying at the edge also means the data layer only ever sees traffic already authenticated by §4.

⚠️ **Verify first, parse second.** The signature covers the raw body, so anything that re-serialises the
request before checking it is checking a different document than the one Stripe signed.

---

## 5. Health endpoints, for Uptime Kuma

Four. **They live where the thing they check lives**, which is not all in one place:

| endpoint | on | answers |
|---|---|---|
| free daily | `serve` | is the game playable |
| subscription | `serve` | is the paid side up |
| data layer | `serve`, proxied | can the data layer reach its database |
| puzzle inventory | `serve` | is there a puzzle for today, and is the runway short |

**The data layer's check is proxied because its port is not published** (§4) — Kuma cannot reach it
directly, by design. `serve` asks it and passes the answer on.

### ⚠️⚠️ The check must confirm the service reaches its database

**A live container with a dead database answers exactly like a healthy one.** So the data layer's own
health endpoint runs a real query: `SELECT 1 FROM <a known table> LIMIT 1`, against a table that always
has rows, with an index behind it.

**What is being tested is that the query does not error**, not the row count. A table that is legitimately
empty on a fresh deployment is not an outage, and a check that says it is will be muted inside a week —
which is the failure mode `CLAUDE.md` records as *a threshold set by eye that rejects real data gets
loosened until it says nothing*.

It also proves **the right database is mounted and the schema exists**, which a bare `SELECT 1` does not:
`SELECT 1` succeeds against an empty database, against the wrong database, and against one whose
migrations never ran.

### ⚠️⚠️ The proxy must not answer for a service it could not reach

If `serve` cannot reach the data layer and the handler returns 200 with *unknown*, **the check passes
during exactly the outage it exists to detect.** Unreachable is unhealthy. Same rule as §4: the absence of
an answer is never a passing one.

### Why inventory is on the list, and it is the one nobody would think of

**`serve` serves static files.** It can be perfectly up with an empty puzzle directory, or with
`today.json` naming a package that is not on the public path. **None of the other three checks would
notice**, and the first person to find out would be a player.

⚠️ **The second case was a real hole until v40-P1-01.** `publish.health.inspect()` read the pointer's
date and never its `puzzle_id`, so **zero packages was healthy** as long as a current-dated pointer
survived — the one state this endpoint exists for. Both pointers are followed to their package now.

§33 puts the alert below three months of forward inventory. **This endpoint is what Kuma watches for it.**

⚠️ **The threshold lives in one place** — the service that evaluates it, with the reason and the figure
beside it, the way every other decided constant in this project does. Kuma reads a status and holds no
number of its own; a threshold spelled in the monitor *and* in the service is two thresholds.

### Two rules for all four

**None may be expensive.** They run every minute. The inventory check reads the manifest; it does not
scan the directory.

**None exposes detail.** A public endpoint reporting that it cannot reach postgres at some host hands out
more than it needs to. **Status, and little else** — including the inventory count: *how many days remain*
is operator information and belongs in an authenticated view or a log, not on an endpoint anyone can poll.

---

## 6. The event record: claimable, and kept

### ⚠️⚠️ An event's subject is reassignable — decided, and it cannot be retrofitted

**Every event carries the device UUID, always. It carries the account identifier when one exists.** On
registration, that device's existing events are **attributed to the account without dropping the UUID**,
because the same device goes on being used signed out.

**Why it has to be designed in rather than added:** if events are not claimable, **the streak somebody
built before registering is lost at exactly the moment they become a customer** — and C7 is irreversible,
so it is lost permanently rather than recoverable from an aggregate. The one moment the product most needs
to reward is the one that would silently throw work away.

⚠️ **This is a schema property, not a feature.** An event whose subject is a single fixed column cannot
become claimable later without rewriting history, and rewriting history is the thing C7 exists to prevent.
Both identifiers, from the first row written.

⚠️ **And it does not weaken §35.** The unlinkable identifier requirement is unchanged: a GDPR deletion
breaks the link to the account while the aggregate survives. Claiming is about attaching a subject, not
about making one more identifiable.

### Events are kept indefinitely — ⬜ open, not designed

**Nothing deletes an event today**, because percentiles need history and the volume at this scale is
nothing.

⚠️ **But *grows without limit by design* and *nobody has decided yet* are different things, and this is
the second.** Recorded as an open decision so that the absence of a retention policy is not later read as
a decision to have none — the same defect as the absence of a check reading as a passing one.

**What would force one:** the table growing enough to affect query time, or a legal obligation appearing.
Neither is close.

---

## 7. Schema migrations: manual, and startup refuses a mismatch

**The data layer does not migrate on boot.** A deploy that migrates by itself can alter the database at
three in the morning with nobody having decided to — and a bad migration is the one failure on this list
that a rollback does not undo.

**But it must refuse to start against a schema it does not expect.** A version check at startup, failing
closed, exactly like the shared token in §4: the container does not come up, rather than serving against a
schema it half-understands.

⚠️ **That pair is the whole design and neither half works alone.** Manual migrations without the check
give silent drift between what the code expects and what exists. The check without manual migrations gives
a deploy the power to alter data. Together: nothing changes the database unless a person decided it, and
nothing runs against a database it did not expect.

**And it fits the health check.** `SELECT 1 FROM <a known table> LIMIT 1` (§5) proves the migrations ran —
the startup check proves the *version* is the expected one, the query proves the schema is really there.

---

## 8. Later, and worth designing for now

The data layer will grow endpoints for metrics: a cron pulling usage, retention and streaks
(`serve-flow.md` §8).

⚠️ **Keep metrics off the operational path.** A thirty-day retention query can touch the whole events
table, and **a heavy report must not be able to slow down a player uploading a result.** Concretely, when
it is built: a separate connection pool and a `statement_timeout` on the reporting side at minimum, so a
report that runs long is a report that dies rather than a queue everyone else waits behind.

⚠️⚠️ **The report does not define what gets stored.** §35 is *minimum to operate*, and it is a list of
what is **not** stored as much as of what is. When a report wants a field that does not exist, the
question is whether the field is needed at all — **not** whether to add it because a query would be
easier with it. That is how *minimum to operate* becomes *everything we might want later*, one reasonable
field at a time.

**And C7 is not negotiable by a metrics requirement.** Events reference an unlinkable user identifier so
that a GDPR deletion breaks the link while aggregate percentiles survive (§35). A report that needs the
link is a report that has to be written differently.

---

## What is open

**Four items closed on 2026-08-22** and moved to `docs/keep-api.md`: the name (`keep`), whether SQLite is
supported (**it is a development convenience, not a supported engine**), where the contract suite runs,
and the API surface itself. EU VAT was closed the same day — no European is subscribing to a baseball
puzzle.


- ⬜ **Event retention** (§6). Kept indefinitely because nobody has decided otherwise, which is not the
  same as by design.
- ⬜ **A second payment processor — undecided, not rejected** (§10). One processor means one source of
  truth about who has paid and one webhook signature to verify, and §35 calls that webhook the
  highest-value attack here. **The evidence that would reopen it is a blocked customer**: someone who
  tries to pay and cannot, seen in support or in a failed-checkout pattern.

**Nothing gets built until this has been read.**
