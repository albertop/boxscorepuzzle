# Beta 0 — the free daily game, complete, on the VPS

**The first milestone, and it changes what counts as done.** Stated 2026-08-22.

**The whole daily loop working end to end, deployed, and given to friends and family.** Not a demo —
**the game as it will be**, for the free daily puzzle only.

`§N` points at `docs/design-boxscore-puzzle.md`.

---

## What is in it

Landing, tutorial, board, keypad, hints, reference sheet, check, reveal, **share**, persistence, **the
event record uploading**, and **a calendar with real inventory**.

## What is not

Accounts, Stripe, subscription, archive, streaks, `canAccess()`, tablet, desktop.

**Those are the next phase and they build on top of a daily that already works, rather than beside it.**
Every one of them assumes a daily loop people actually complete, and none can be evaluated before one
exists.

---

## ⚠️⚠️ The share is not a nice-to-have in this milestone

**It has to work perfectly.** Operator's requirement, and the reason is structural rather than aesthetic.

**Friends and family is not a test of whether the game works — it is a test of whether people pass it
on.** §20 calls the shared grid the main growth channel, and beta 0 is the first and only chance to find
out whether it does anything **before there is a paying product resting on it.**

**A broken or ugly share means the milestone answers the smaller question and not the larger one.**

### What *perfectly* has to mean here

- **The PNG renders correctly on a real phone**, not only in devtools — and gets checked on one.
- **It survives the apps people actually use.** WhatsApp, iMessage and X each treat images differently;
  an image that looks right locally and arrives cropped or recompressed **is a broken share**.
- **The random digits and the blur do what they are for**: someone receiving it before playing learns
  nothing about the board.
- **The time and the failed-check count are on it**, since that is what makes two results comparable.
- **It is one tap.** Any friction here is friction on the only growth mechanism the product has.

### ⚠️ Test it by sending it, not by generating it

**Generate-and-inspect is what every other visual check in this project has failed at.** The rule
`CLAUDE.md` records is *ask what the instrument adds* — and a local harness supplies exactly the
properties under test here: the compression, the colour profile, the aspect ratio, the scaling. A PNG
inspected where it was made cannot answer whether WhatsApp will recompress it.

**Send it. Open it on the phone. Look at what arrived.**

### ⚠️⚠️ Three traps in the share, and the first one is the obvious implementation

**1. The share is not a picture of the reveal.** The reveal prints the complete boxscore with **names,
teams and date** (§7) — that is the whole reward and it is exactly what must never leave. §7 is explicit:
*the share grid must never leak the solution or player names.* **Screenshotting the reveal would publish
the entire answer to everyone the player sends it to**, and it is the first implementation anybody would
reach for because the reveal is right there and already looks good.

**2. The blur is not what protects it — the random digits are** (`serve-flow.md` §7b). This is easy to
get backwards and the consequence is a leak. Deblurring is solved, the image is small, the glyph set is
ten digits in a known typeface and the grid positions are fixed. **Values are replaced first**, so anyone
who reverses the blur perfectly recovers noise *and cannot tell it is noise*. The blur is typography, not
security. **An implementation that blurs real values is broken even though it looks identical.**

**3. The figures must be named the same way they are named on the reveal.** The reveal says
`Checks failed` and prints `None` at zero (2026-08-22). A share saying anything else gives one number two
names, in the one artefact whose purpose is comparing two results. Same catalogue keys, per C11.

---

## What the operator already has

Domain (`boxscorepuzzle.com`), VPS, nginx already running, Postgres already running.

**So the deployment is smaller than it looked:** a Dockerfile for `serve`, one for the data layer, an
nginx server block, certbot for the certificate, and a DNS record.

---

## ⚠️ The large missing piece: calendar and inventory

There are six reference puzzles. A daily game needs puzzles assigned to dates with months of runway, and
**the forge has never produced a batch** — generation at volume, calendar construction, signed packaging
in bulk.

**Without it there is no *today's puzzle* that lasts more than a day, and it blocks everything else.**

Also missing: **the data layer** with the device UUID and event upload (designed in `data-layer.md`, not
built), **the device UUID** specifically, **the share PNG** (designed in `serve-flow.md` §7b; the button
exists and is `disabled`), and **the deployment**.

---

## The order

1. **Calendar and inventory** — blocks everything.
2. **Device UUID** — asymmetric cost; every event before it exists is unattributable, and C7 is
   irreversible.
3. **The data layer**, against the Postgres already running.
4. **Deployment.**
5. **The share** — last to build, **held to the same standard as everything else in the milestone.**

### ⚠️ Why 2 before 3 is not merely a priority — it preserves data

Events save to `localStorage` first and upload when they can (`serve-flow.md` §9). A UUID that exists
while the data layer does not means events in that window are **queued, not lost**: they upload when the
layer arrives, carrying the identity they were created under. The reverse order loses them permanently.

**The ordering is doing real work, not expressing a preference.**

---

## What the milestone is for

**Finding out whether people play it, come back, and pass it on.**

That is why event upload and minimum metrics are inside beta 0 rather than after it — deploying without
them means deploying blind. §20's number is the one that matters: **a thousand who try is easy, a thousand
who return on day 30 is the problem.**

### ⚠️⚠️ What this sample can and cannot answer

The instruments belong in beta 0 so they are built and trusted. **Some of the numbers they produce get
their meaning from a later audience**, and saying which is which now is what stops a small sample being
read as a result.

| question | can beta 0 answer it |
|---|---|
| Does the loop close end to end, does the daily roll over, do events arrive attributable | **Yes.** Fully. |
| Are boards solvable by people who are not the author | **Yes**, and it is the only way to find out |
| Does the shared image survive WhatsApp, iMessage and X intact | **Yes.** Pure engineering, and the sample size is irrelevant |
| Does anyone come back at all | **Yes**, as a yes-or-no |
| Do people choose to share | **Weakly.** Friends share out of support |
| Does a recipient become a player | **No.** The recipients are also friends of friends |
| The retention curve | **No** |

### ⚠️⚠️ Recorded before the first number arrives: **beta 0 does not produce a retention curve**

Operator's decision that this goes in writing, and the timing is the point — **written now, before any
number exists**, because afterwards it reads as an excuse for a disappointing figure rather than as a
property of the sample.

Friends and family are self-selected in the worst possible way for this measurement: **someone who knows
the operator returns on day 1 out of loyalty and keeps going until the loyalty runs out, which looks
identical to a product with good onboarding and a weak loop.** The two are indistinguishable in the data,
and no amount of care in computing the number separates them.

**§20's whole argument rests on that number meaning something**, so a number that does not mean anything
is worse here than no number. Reading a curve off this sample is *a correct instrument pointed at the
wrong thing* — the failure `CLAUDE.md` records as the one that survives every review, because nothing
about it is broken.

⚠️ **And the share decomposes rather than passing or failing as one thing.** *Does the artefact survive
the trip* is answerable now and completely. *Does it recruit* is not, and the two would otherwise be
reported as one verdict on the growth channel.

---

## ⚠️⚠️ Three scope questions, raised when this was written down and **decided the same day**

### 1. The fifty-board hand-solve pack is **inside** beta 0 — decided

**It is a gate on beta 0, not a step before launch.** Operator's decision, 2026-08-22. It is the
operator's to do and it is **still outstanding**.

`CLAUDE.md` is unambiguous that it is a **launch gate, not a review step**: layer 3 propagates intervals
across forty-odd simultaneous relations, which is stronger than any person, so **a board can pass all four
validation layers and be underivable by a human.** Solving fifty by hand is the only verification of human
derivability that exists, and the only check the common-author risk does not touch.

**Beta 0 puts real people on real boards**, and an underivable board is the one defect that cannot be
apologised for — the player concludes he is not good enough, which is what §31 is most afraid of. Friends
and family are the audience least likely to say so.

⚠️ **What makes it a gate rather than a strong preference:** someone who meets an impossible board
**does not come back and does not tell you why.** There is no support ticket for it, no error in a log,
and nothing in the event record distinguishes it from a hard board someone gave up on. It is the one
defect that leaves no trace of itself.

### 2. *One game, one puzzle* is built into the calendar at point 1 — decided

From schema 5 the reveal prints **both clubs**, and the other club's half **is the other direction's
board**. Publishing both gives the second one away entirely, inside the first one's reveal, before it is
played.

⚠️⚠️ **No package can enforce this and no validation layer can see it.** A file cannot know what else was
published; it is a property of the *set*, which is what a calendar is. Today the whole of the enforcement
is `write_reference_puzzles.refuse_second_direction`, over **one batch**.

**A calendar that does not carry this check is not a calendar with a missing feature; it is one that leaks
puzzles.**

**The requirement: a guard that fails if both directions of a game are ever scheduled** — over everything
ever published, not over one batch. ⚠️ Note what that implies about where the check can live: it needs the
whole published history as its input, so it is a property of the calendar's *state*, not of the run that
extends it. A guard that only sees today's batch is the enforcement that already exists and is not enough.

### 3. Five months of inventory, not three — decided

§33 asks for five. **Generate five.** Generation at volume is **one batch run** and the calendar has to be
built either way, so generating less saves nothing and buys a reload in the middle of the beta — the one
moment nobody wants to be running the generator in a hurry.

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
