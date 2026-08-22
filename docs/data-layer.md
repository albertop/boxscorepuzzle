# The data layer

**Standing direction, the way `serve-brief.md` is for the client.** Decisions taken 2026-08-22, written
before anything is built. Where a question is still open it says so; those are not implementation
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

⚠️ **It has no name yet.** `keep` is proposed — one syllable, a verb, and what it does, beside `forge`
and `serve`. Not decided; this document says *the data layer* throughout so that nothing depends on the
choice.

---

## 2. The database is behind an interface

**`serve` never knows which engine is underneath.** The data layer exposes one API; whether Postgres or
SQLite answers it is not a fact any caller can observe.

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

⬜ **Open: whether SQLite is a supported engine or only a development convenience.** They are different
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

**`serve` serves static files.** It can be perfectly up with an empty puzzle directory, or with a manifest
pointing at a generation that no longer exists. **None of the other three checks would notice**, and the
first person to find out would be a player.

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

## 6. Later, and worth designing for now

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

- ⬜ **The service's name.** `keep` proposed.
- ⬜ **Whether SQLite is supported or only a development convenience** (§2). Different promises, different
  obligations on the contract suite.
- ⬜ **Where the cross-engine contract suite runs**, given the push workflows no longer carry the full run
  (`docs/ci.md`). One that only runs weekly is a real gap.
- ⬜ **The API surface itself.** Nothing here says what the endpoints are. That is the next document, or
  the first commit, and it should not be invented in passing.

**Nothing gets built until this has been read.**
