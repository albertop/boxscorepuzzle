# Beta 0 — the free daily game, complete, on the VPS

**The first milestone, and it changes what counts as done.** Stated 2026-08-22.

**The whole daily loop working end to end, deployed, and given to friends and family.** Not a demo and
not a preview — **the game as it will be**, for the free daily puzzle only.

`§N` points at `docs/design-boxscore-puzzle.md`.

---

## What is in it

Landing, tutorial, board, keypad, hints, reference sheet, check, reveal, **share**, persistence, **the
event record uploading**, and **a calendar with real inventory**.

## What is not

Accounts, Stripe, subscription, archive, streaks, `canAccess()`, tablet, desktop.

**Those are the next phase and they build on top of a daily that already works, rather than beside it.**
That ordering is the point of drawing the line here: every one of them assumes a daily loop that people
actually complete, and none of them can be evaluated before one exists.

---

## What the operator already has

Domain (`boxscorepuzzle.com`), VPS, nginx already running, Postgres already running.

**So the deployment is smaller than it looked:** a Dockerfile for `serve`, one for the data layer, an
nginx server block, certbot for the certificate, and a DNS record.

---

## ⚠️ What does not exist and blocks the milestone

**1. The calendar and real inventory.** There are six reference puzzles. A daily game needs puzzles
assigned to dates with months of runway, and **the forge has never produced a batch** — generation at
volume, calendar construction, signed packaging in bulk. **This is the large piece.**

**2. The data layer, with the device UUID and event upload.** Designed (`docs/data-layer.md`), not built.

**3. The device UUID specifically**, which has asymmetric cost: **every event before it exists is
unattributable**, and C7 is irreversible.

**4. The share PNG.** Designed (`serve-flow.md` §7b), not built. The button exists and is `disabled`.

**5. The deployment itself.**

---

## The order

1. **The calendar and inventory.** Without it there is no *today's puzzle* that lasts more than a day,
   and it blocks everything else.
2. **The device UUID**, because waiting costs data that cannot be recovered.
3. **The data layer**, against the Postgres already running.
4. **Deployment.**
5. **The share**, which blocks nothing.

### ⚠️ Why 2 before 3 is not merely a priority — it preserves data

Events save to `localStorage` first and upload when they can (`serve-flow.md` §9). So a UUID that exists
while the data layer does not means events in that window are **queued, not lost**: they upload when the
layer arrives, carrying the identity they were created under. The reverse order loses them permanently.

**The ordering is doing real work, not expressing a preference.**

---

## ⚠️⚠️ Four things about the scope, raised when it was written down

None of these change the milestone. Each is something the list above does not settle, and settling them
later costs more than settling them now.

### 1. Does the fifty-board hand-solve gate apply to beta 0?

`CLAUDE.md` is unambiguous that it is a **launch gate, not a review step**: layer 3 propagates intervals
across forty-odd simultaneous relations, which is stronger than any person, so **a board can pass all four
validation layers and be underivable by a human.** Solving fifty by hand is the only verification of human
derivability that exists, and the only check the common-author risk does not touch.

**Beta 0 puts real people on real boards.** An underivable board is the one defect that cannot be
apologised for — the player concludes he is not good enough, which is the failure §31 is most afraid of,
and friends and family are exactly the audience least likely to say so.

⬜ **Not decided here.** The pack is already recorded as pending work with its own session. The question
is whether it sits inside item 1 or after item 5 — and it is a question about the gate's scope, not about
the pack.

### 2. The calendar inherits *one game, one puzzle*, over everything ever published

From schema 5 the reveal prints **both clubs**, and the other club's half **is the other direction's
board**. Publishing both gives the second one away entirely, inside the first one's reveal, before it is
played.

⚠️⚠️ **No package can enforce this and no validation layer can see it.** A file cannot know what else was
published; it is a property of the *set*, which is what a calendar is. Today the whole of the enforcement
is `write_reference_puzzles.refuse_second_direction`, which asserts it over **one batch**.

**A calendar that does not carry this check is not a calendar with a missing feature; it is one that leaks
puzzles.** It belongs in item 1, not after it.

### 3. There is no saving in generating less inventory

§33 says five months of forward inventory, alert below three. A friends-and-family beta might look like it
needs less — but generation at volume is **one batch run**, and the calendar has to be built either way.
**Generating three months instead of five saves nothing and buys a refill during the beta**, which is the
one moment nobody wants to be running the generator under time pressure.

### 4. ⚠️ What beta 0 can and cannot measure

**The event upload is inside beta 0 rather than after it, and that is right** — deploying without it means
deploying blind, and the whole point of friends and family is learning something. §20's number is the one
to watch: a thousand who try is easy, a thousand who return on day 30 is the problem.

⚠️ **But friends and family will not produce a retention rate.** The sample is small and it is
self-selected in the worst way for this measurement: people who know the operator come back out of
loyalty on day 1 and stop when the loyalty runs out, which looks exactly like a product with good
onboarding and a weak loop.

**What beta 0 can establish:** the loop works end to end, the daily rolls over correctly, events arrive
and are attributable, boards are solvable by people who are not the author, and **whether anyone comes
back at all**. Those are real answers.

**What it cannot establish is a retention curve**, and reading one off this sample would be the shape
`CLAUDE.md` records as *a working instrument pointed at the wrong thing* — correctly computed, about
nothing. The instrument is being built here so it is ready and trusted; **the number it produces gets its
meaning from a later audience.**

---

## What the deployment must not get wrong

Already decided elsewhere, gathered here because item 4 is where they all land at once:

- **The daily puzzle is served without authentication** (§23). No API key: a key in a header travels to
  the browser and protects nothing.
- **`serve` ships alone.** Generator code must never reach the VPS (§16, §33).
- **The private signing key never leaves the laptop.** The VPS holds the **public** key, to verify.
- **The data layer's port is not published to the host**, and it refuses to start without its shared token
  (`data-layer.md` §4).
- **No secrets in images. Containers unprivileged.** Rate limit per IP in nginx; do not persist IPs.
- **Cache only the current day's puzzle, never the week** — caching ahead leaks future puzzles.
