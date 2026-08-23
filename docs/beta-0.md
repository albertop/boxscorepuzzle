# Beta 0 — the free daily game, complete, on the VPS

**The first milestone, and it changes what counts as done.** Stated 2026-08-22.

**The whole daily loop working end to end, deployed, and given to friends and family.** Not a demo —
**the game as it will be**, for the free daily puzzle only.

`§N` points at `docs/design-boxscore-puzzle.md`.

---

## What is in it

Landing, tutorial, board, keypad, hints, reference sheet, check, reveal, **share**, persistence, **the
event record uploading**, and **a calendar with real inventory**.

**And ⚠️ uncaught client errors reported to the data layer.** See below — it is not on the original list
and it is the hole that produces silence rather than a complaint.

## What is not

Accounts, Stripe, subscription, archive, streaks, `canAccess()`. **Tablet and desktop get the phone UI,
provisionally** — see below; they are not *absent*, they are unstyled.

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

## ⚠️⚠️ Uncaught client errors are reported — added 2026-08-22

**Nothing in the original plan tells you the client broke on somebody's phone.** If a friend's JavaScript
throws, or the board renders wrong on his model, **nobody ever finds out.**

**For a beta whose entire purpose is discovering problems, that is a large hole** — and the failure it
misses is precisely the one that produces **silence rather than a complaint**. A player whose board did
not render does not report a bug; he closes the tab. That is the same shape as the underivable board in
scope question 1: the defects that leave no trace are the ones a beta must be built to catch, because the
ones that generate complaints will arrive anyway.

**What it is: a handler and an endpoint.** `window.onerror` and `unhandledrejection`, posted to the data
layer with the device UUID and enough context to reproduce — message, stack, page, viewport, user agent.
**Not a service and not a dependency.**

⚠️ **It rides with items 2 and 3**, because it needs the UUID to be worth anything and the endpoint to go
anywhere. An error report with no identity cannot be tied to the session that produced it.

⚠️ **And it must not become a way to break §23.** The reporter fails silently and never blocks the play
path — a client error handler that throws, or that waits on a network call, turns one broken render into a
broken game.

⚠️ **§35 applies to it like everything else.** No IP, no geolocation. A user agent and a viewport are
what reproduce a rendering bug; anything past that is being collected because it was easy.

---

## Feedback channel: none, and that is a decision — 2026-08-22

**Friends and family are controlled enough that they have the operator's phone number.** So **no contact
link and no FAQ.**

⚠️ **A FAQ written before there are users is a document answering invented questions.** The real ones will
be different, and **what people ask is what eventually becomes the FAQ** — writing it first means writing
it twice and being wrong the first time.

**Recorded as a decision rather than left as an omission**, so nobody adds one to fill a gap that was
chosen.

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

### ⚠️⚠️ The share is last and it does not get cut

**If anything slips, the last item is what gets cut.** That is what *last* usually means, and here it must
not: the share is the thing that answers the milestone's larger question, and a beta 0 without it answers
whether the game works instead of whether people pass it on.

**So the sequencing is deliberate and the priority is not read off it.** It is fifth because it depends on
a finished reveal and a real board, not because it is the least important. ⚠️ **If time runs short, what
gives is the scope of something else — never this.**

⬜ **The alternative was moving it earlier**, and it loses on a dependency rather than on importance: the
PNG draws from the finished game, so building it before the reveal is settled means building it twice.
The position stands; the exemption is what makes the position safe.

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
| How many distinct **people** played | **No** — a cleared browser is a new device, and the gap runs one way |
| Do people choose to share | **Weakly.** Friends share out of support |
| Does a recipient become a player | **No.** The recipients are also friends of friends |
| The retention curve | **No** |

### ⚠️⚠️ Recorded before the first number arrives: **a cleared browser is a new device**

A player who clears their browser data comes back with a **new device id**, and their earlier games are
orphaned. **That is unavoidable and fine** — §35 stores a random UUID and nothing derived from the
machine, precisely so there is nothing to recognise somebody by.

**What it does is inflate the unique-device count**, and beta 0 exists to read numbers off these events.
Devices are not people, and the gap runs one way: **more devices than players, never fewer.**

⚠️ **Same class as the retention caveat below, and worth naming as such: a correct measurement that means
something narrower than it appears.** Nothing is broken — the count is exactly right about devices — and
reading it as *players* is the error, which no amount of care in computing it prevents. Written down
before the first number arrives, because afterwards it reads as an excuse for a figure somebody did not
like.

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

### 1. The hand-solve gate is **inside** beta 0 — decided. ⚠️⚠️ Its size is not what any document says

**It is a gate on beta 0, not a step before launch.** Operator's decision, 2026-08-22. It is the
operator's to do and it is **still outstanding**.

⚠️⚠️ **"The fifty-board hand-solve pack" names three different activities, and one of its two numbers is
from a retired design.** Found while writing this document down.

| | what it asks | size | axis | status |
|---|---|---|---|---|
| **The gate** | are the boards humanly derivable at all | — | — | **undefined, see below** |
| **Pack A** | does the difficulty ordering correspond to felt difficulty | **16** — four each at rungs 5, 8, 11, 12 | **stalls** | designed 2026-08-21, not built |
| **The stranger's ten** | does the operator's scale agree with somebody who is not him | 10 | spread | designed, not built |

**Where *fifty* comes from, and why it is stale.** `build_pack.py`'s `audit()` asserts fifty boards with
**every rung at its quota on the chain axis** — and the generator stopped targeting chain. `todo.md` item
13 already records that the producer is the last chain-targeted one. **So the fifty carries a number and
an axis, and the axis is retired.** `CLAUDE.md`, the design document and five package-format documents all
repeat the phrase.

⚠️ **And sixteen is not the answer either, because it was never sized for this job.** Pack A is a
*calibration instrument*: four boards per rung tells you about a rung. **The gate is a confidence
statement about the generator** — that it does not produce underivable boards — and that is a sample-size
question about the whole inventory, not a per-rung one. Substituting sixteen because sixteen is what
exists would be the shape `CLAUDE.md` records under *a pack that claims to satisfy quotas and does not*.

**Decided 2026-08-22: the gate is Pack A's sixteen *plus* a derivability-only sample drawn across the
shipping inventory** — no survey, no ranking sheet, just *did it solve without guessing*. Those sheets are
far cheaper per board than a calibration sheet, which is what makes a larger N affordable. **The two
questions are separate and only one of them is a gate.**

#### ⚠️⚠️ The derivability sample is a falsification test, not a rate estimate — and that sets its shape

Writing it down changed what it is. The obvious reading is *sample n boards, estimate what fraction are
underivable*. **That is the wrong instrument**, and reaching for it would produce a number that licenses
shipping known-bad boards.

**What the gate actually tests is an assumption**: that layer 3 finishing without backtracking implies a
person can derive the board. `CLAUDE.md` states plainly that it does not follow — layer 3 propagates
intervals across forty simultaneous relations, which is stronger than any person.

**So one failure is a finding, not a data point.** A board that passes all four layers and defeats a
competent solver by hand **falsifies the assumption the entire publication rule rests on**, and the
response is to stop and understand it — not to divide it by n and call it 4%.

**And that sets the sample's shape: spread, not count.** A falsification test is sized by *giving the
assumption a real chance to fail*, so the sample is **stratified over the things that could break it**:

- **Stall rungs** across the range, weighted toward the hard end — that is where the assumption is
  weakest.
- **Era**, since §6 allows pre-1950 boards up to 5% of what a player sees and those have different roster
  shapes.
- **Roster shape**, batter-heavy against pitcher-heavy. ⚠️ The pitcher cap went 2 → 4 → 6 and that
  **changed which boards enter the pool at all**; the pitching section now contributes 45% of stalls
  against 34% at four. Boards that only became eligible under the new cap are the least-examined
  population there is.
- **Equation families**, and specifically **boards depending on the batting order** — it became the fifth
  family on 2026-08-21, it is the one relation that cannot be read off a boxscore, and no figure taken
  before that date counted it.

⚠️ **If the operator does want a rate as well, the arithmetic is standard and should be stated rather than
guessed:** n boards all passing puts the underlying rate below roughly `3/n` at 95% confidence — 30 boards
gives under 10%, 100 gives under 3%. **At 150 puzzles in five months, 3% is still four or five ruined
days**, which is the number that shows why the falsification reading is the right one: no tolerable rate
exists, so the gate is pass-or-stop.

⬜ **The exact N and the stratum quotas stay open**, and `audit()` must assert them after selection rather
than print them — the rule `CLAUDE.md` records from the weighted draw that produced zero boards at the
easiest rung and reported quotas it had not met.

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

## ⚠️ Is the site public? — a decision, not a consequence

**Friends and family on `boxscorepuzzle.com` with no authentication means anyone who finds the URL
plays.** §23 requires the daily to be served without authentication, so there is no gate on the game
itself.

**This has to be decided rather than inherited**, because if it is public **the operator no longer
controls who sees the first version** — and a first version is seen once.

**Decided 2026-08-22: public, and accepted.** No gate.

**The reason is that any gate is a gate on the thing being measured.** §23 already requires the daily to
be served without authentication, and the share — which is what this milestone exists to test — **spreads
the URL by design**. Basic auth would control who sees the first version at the price of making the share
untestable: whoever receives the image could not play.

**What is accepted along with it:** a stranger who meets a rough edge forms an opinion the operator never
gets to answer, and there is deliberately no feedback channel to hear it through (above).

⚠️ **The rejected middle is worth naming, because it looks like a compromise and is not one.** `noindex`
plus an unlisted path is **obscurity, not access control** — and the URL travels in every share, so it
reduces accidental traffic and not directed traffic. It would have bought the appearance of a private beta
while leaving the actual exposure unchanged.

---

## Tablet and desktop: the phone UI, provisionally

**They already work in the sense that matters** — the board targets 375px, so on a wide screen it renders
centred and narrow. **Ugly but playable**, and that is acceptable for beta 0.

⚠️ **The only requirement: it must not stretch.** A board built for 375px stretched to 1400px is
**broken, not provisional** — the cells lose their proportions, the label column stops being 66px of
seven characters, and §6's whole column argument is about a width that no longer holds.

**So the check is a maximum width, not a layout.** Nothing is designed for the wide screen; something has
to stop the narrow design from being scaled into a wrong one.

### ✔ Measured 2026-08-22: it does not stretch — and nothing guards that

**At 1400×900 the board holds at 375px, centred**, with the cell at 44.8px and the table at 359px: the
same numbers it has at 375×812. `#app` carries `max-width: 375px`. **Verified in a browser and in a
picture, not read off the stylesheet.** So the requirement is met today and beta 0 needs no work for it.

⚠️⚠️ **But the number is spelled three times and tested nowhere.** `board.css:74`, `board.css:599` and
`landing.css:18` each say `max-width: 375px`, and the only width assertion in the browser suite is for the
narrow-device media query. **The width every §6 column argument rests on is three copies with nothing
checking they agree** — this project's most-met defect, sitting under the one property beta 1 will change.

⬜ **Recorded in `todo.md`.** The fix is a token and a test; it is not beta 0 work, but **beta 1 is the
milestone that edits exactly this**, and finding out then that three files disagree is the expensive
order.

---

## The beta sequence

| | |
|---|---|
| **Beta 0** | the free daily, complete, on the VPS |
| **Beta 1** | **desktop** |
| **Beta 2** | **tablet** |
| **Beta 3** | Stripe, accounts, subscription |

**Desktop before tablet.** Operator's decision, 2026-08-22. **A physical keyboard is a different and
better interaction** — digits and arrow keys rather than a custom keypad — so desktop is not the phone
board on a bigger screen; it is the one platform where the input model genuinely improves. **And tablet
has the fewest unique users of the three**, since whoever has one generally also has a phone and a
computer.

⚠️ **Each milestone has its successor named so nothing drifts into the wrong one.** The failure this
prevents is the ordinary one: a desktop concern arriving during beta 0 and being fixed *there*, because
fixing it is small and the milestone boundary is invisible from inside the work.

⚠️ **`serve-brief.md` says one puzzle and three interfaces, a core that knows nothing about screens.**
The sequence is what makes that claim testable: if the engine is really screen-agnostic, beta 1 touches
`ui/` and nothing under `engine/`. **A desktop build that has to reach into the engine is the brief
failing, and it will say so.**

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
