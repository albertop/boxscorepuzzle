# The player's flow

**What the player meets, from landing on the site to the boxscore at the end — and what is kept, when, and where.**

`docs/serve-brief.md` is the standing direction for the client: one puzzle, three interfaces, a core that
knows nothing about screens. This is the other half — **what the interfaces are for**. The brief says how
the engine is shaped; this says what the game does.

⚠️ **Written before the wiring, and that is the point.** Connecting `snapshot()` to `localStorage` is half
an hour. *What* is saved, *when* it is saved and what a returning player sees is not a half hour, it is a
set of decisions — and decisions invented while implementing end up in commit messages instead of in a
document. Several §36 items had been open for months; this closes them rather than inventing beside them.

⚠️ **Persistence lives here and not in a file of its own.** It is half of this document's questions —
what happens on pause, on return, on finish. Split across two files they would have to be read together,
and this project has a record of what happens when one decision lives in two places.

---

## 1. The landing page

**The player does not land on the puzzle. ⚠️ And not only the first time — every visit lands here.**

That is the decision, and it is worth stating as one because *land the newcomer, then send returning
players straight to the board* is the obvious alternative and it is wrong. **The archive, the streak and
the subscription all live on this page when they exist**, and a player routed past it would never meet
any of them. A landing page only the newcomer sees is a landing page for a product with no second week.

### What it carries

- **The name, and one line saying what this is.** Something like *"Rebuild a real baseball boxscore
  using nothing but logic."* ⚠️ **It has to say what it is *and what it is not*** — not trivia, not
  guessing. That is the line separating this from Immaculate Grid and it is the first thing a visitor
  gets wrong about it.
- **A small static example board.** The green scoreboard and a grid with holes. **Explaining a visual
  puzzle in words is worse than showing it**, and this project has spent a day proving the same thing
  in the other direction: no description of a board substitutes for a picture of one.
- **A large button for today's puzzle, with the date.**
- **A secondary link, *how to play*, opening the tutorial.**

### ⚠️ The button changes when today is already played

*See the boxscore* rather than *Play* — or the time achieved. Otherwise a returning player is offered a
puzzle he has already solved, **every day**, which reads as the product not knowing who he is. The state
is already there: §6 persists the finished session and §7 reopens it read-only, so this is a label
reading state that exists rather than new machinery.

### Nothing else yet

Archive, subscription and streak arrive here when they exist. **The page is laid out so they can be
added without rebuilding it** — the same discipline as seams C8, C9 and C10: the shape is present before
the feature is.

---

## 1b. The tutorial — five steps, and ⚠️ **it is not mandatory**

### The reversal, and the reasoning rather than only the decision

**⚠️⚠️ This reverses §8, which made the tutorial non-skippable on first play.** The old rule is kept
below as superseded rather than deleted, because it was right about the risk and wrong about the remedy.

**A compulsory tutorial is a barrier placed in front of someone who does not yet know whether they are
interested.** It is spent on the visitor who has not decided, and the ones who do not want it leave
before seeing a board — which is the same outcome the rule existed to prevent, arriving one screen
earlier. **If someone is brave enough to try without it, let them.**

**And the game no longer depends on it to be solvable.** §3b put the reference sheet one button away
during play, and it carries all five relations and the bounds. Anyone who dives in and gets stuck has
the formulas there. When §8 was written that button did not exist and the tutorial was the *only* place
the rules were ever stated — the rule was load-bearing then and is not now.

⚠️ **Note what did not change: the tutorial still has to be good.** Making it skippable is not a reason
to make it thinner, and *"they can always open the reference sheet"* is not a design for onboarding. The
sheet is a reminder for someone who has met the rules; the tutorial is where they meet them.

#### The superseded rule, kept

> **Mandatory on first play.** The tutorial is not skippable on the first game. It's short, and it's the
> only guarantee that nobody reaches the real puzzle without understanding the mechanics.

It stopped being the only guarantee on 2026-08-20, when the reference sheet shipped.

### The shape: a five-step wizard

**One step per relation family.** Next and previous, and **a visible skip** — visible, because a skip
the visitor has to hunt for is a mandatory tutorial wearing a disguise.

- **Progress shown** — *step 3 of 5*. Five is a number someone will finish; an unbounded sequence is one
  they abandon.
- **A small invented boxscore, not a real one.** Four batters, one pitcher, three columns. ⚠️ **Say that
  it is invented** — *"a made-up boxscore, smaller than the real ones"* — so nobody spends a step
  wondering why it looks wrong. A real board here would be six columns and thirteen rows and would
  teach the relation and the crowding at the same time.
- **One hole per step**, so the player watches the relation *fill a cell* rather than reading it as an
  equation. The relation is a thing that does something; an equation on a slide is a thing to nod at.

### The order, and why the last one is last

1. **Row identity** — `PA = AB + BB + HBP + SF + SH + CI`, one row, self-contained
2. **Column totals**
3. **The cross between batting and pitching**
4. **The global identity**
5. **The batting order**

⚠️ **The batting order is last because it is the only one that cannot be inferred from looking at a
board.** The other four are visible in the grid: a row, a column, two facing sections, the line score.
Nothing on screen announces that the plate appearances divide nine ways around the lineup. It needs the
most setup and it gets the player who has already seen four relations work.

### At the end

**The reference sheet**, so the player leaves knowing the button exists during play — a sheet nobody
knows about is a sheet nobody opens. **Then the way to today's puzzle.**

### Repeatable

**Reachable from the landing page at any time.** Someone who plays once a month will have forgotten, and
a tutorial that can only ever be seen once is built for a player who does not exist.

### ⚠️ What is deliberately not built into it

**No account. No tracking of tutorial progress. No persistence of which step someone reached.** It is a
page with five steps and two buttons.

Every piece of machinery added here is machinery **on the path between a stranger and their first
board**. Remembering that someone reached step 3 requires storage, a key, an identity to key it by, and
a decision about what happens when it is stale — all of it spent on a visitor who has not yet seen a
puzzle, and none of it visible to them as anything but delay.

---

## 2. Errors: validation only on *done*

**No immediate marking. No count of wrong cells. The player fills the board, presses done, and is told it
balances or it does not — never where, never how many.**

Both alternatives were considered and both were rejected for one reason: **they turn the board into an
oracle.**

⚠️ **This board is not sudoku, and that is exactly what makes immediate marking dangerous.** Every cell
sits inside an identity, so the client can tell the instant a value breaks one. Cheap to implement — and
it means a player can type 1, 2, 3, 4 and watch for the red to go away. **Probing beats deducing**, and
the product is deduction or it is nothing (§1's anti-goals).

**A count of wrong cells is worse than marking them.** Change one cell, watch the number move, and you
have a binary search over the whole board. A number that says *how many* is a stronger oracle than a
colour that says *which*.

### What the player gets instead

**Unlimited attempts, and the clock does not stop.**

- §27 forbids a fail state, so **limiting attempts is not available** — it is not a design choice that was
  passed over, it is ruled out.
- The disincentive against probing is therefore **the clock**, not a rule. An error costs time, and time
  is what is measured and what is shared.

⚠️ **The honest cost, named rather than glossed:** a player who presses done and is wrong has to re-check
the whole board with no idea where the fault is. That is the price of not being an oracle, and it is
deliberate. If it turns out to drive people away, the thing to revisit is the board or the difficulty
curve — **not** the feedback, because feedback is the thing that destroys the game.

---

## 3. Three hints, and they are shared with the time

**Reversed on 2026-08-20, after playtesting with a real player.** This section said *no hints*. The
superseded reasoning is kept below, because it was not wrong — it was answering a different question.

### How it works

- **Three per game.** Few enough that spending one is a decision, enough that being stuck twice does
  not end the game. Chosen, not measured: the fifty-board hand-solve is what will say if it is right.
- **The hint reveals the *selected* cell.** The player picks where they are stuck and presses it.
- **A hinted cell is drawn in a third colour** — neither the given black nor the entered blue — so the
  finished board shows which cells the player did not deduce.
- **The count sits beside the time on the reveal**, so a shared result carries both.
- It records in the C7 event (`hints`), which is what a shared or compared result means.

### ⚠️⚠️ What the reversal turned on, which is not that the old reasoning was wrong

**A hint does not corrupt a comparison if it is shared alongside the time.** One minute with three
hints and one minute with none are two different results, and every reader takes them as two. That is
the crossword's answer and the original argument never considered it — it reasoned entirely about
whether a board *needs* a hint, and concluded correctly that it does not.

**Both things are true at once.** §22's guarantee still holds: every published board is solvable by
propagation and bounding without a guess, and if one ever needed a hint the answer is still to fix the
generator. A hint is not an escape from an unsolvable board. It is an escape from **this player, on
this board, today** — and being stuck is a fact about a person, not a defect in a puzzle.

### ⚠️ Why the selected cell rather than a random one

**A random cell is a lottery.** It might hand over the one the player was about to get, or the one that
unlocks the whole board, and the player controls neither — so the same spend is worth wildly different
amounts depending on where it lands.

Revealing the cell they chose **rewards knowing where you are stuck**, which is part of solving rather
than a way around it. It is also what sudoku does.

### The superseded reasoning, kept

> **Not primarily because they would ruin a shared time, though they would.**
>
> §22 guarantees that every published board is solvable by propagation and bounding **without a single
> guess**. A hint is an escape from being stuck with no way forward — and by design that state cannot
> happen. **If a board needed a hint, the guarantee failed**, and the answer is to fix the generator,
> not to hand the player a way around it.
>
> **Without hints, the only exit from being stuck is to give up.** That is a real cost and it is
> covered by §27's existing protections rather than by anything new: the free monthly grace day,
> streak insurance in the paid tier, and the puzzle staying playable from the archive after midnight.

⚠️ **Recorded rather than deleted, and the distinction is the point.** The first sentence of it is the
tell: it set the comparison argument aside as secondary and then never returned to it. A decision
overturned by an argument it never engaged with is worth keeping visible, because the same shape will
happen again — and a document that quietly says the opposite of what it said last month teaches nobody
anything.

The §27 protections above are unchanged and still the answer to giving up. Hints are not a replacement
for them: three cells do not rescue a board nobody can finish.

---

## 3b. A reference sheet, opened from a button

**Also from the playtest: the player could not remember the formulas mid-game.** That is friction
rather than difficulty — a game measuring memory as well as deduction, and only one of those is the
product.

**It is worse now than when this was first considered.** There are five families, and the batting order
is the one that **cannot be inferred from looking at a board**. The operator lost a solve to exactly
that on the day it was adopted.

- **Contents: the five relations and the bounds** — the set the printed strip on the hand-solve pack
  carries, plus the batting order, which that strip predates.
- **It costs no hint and is not one.** A hint hands over an answer; this hands over the rules, which
  the tutorial teaches. The difference is that the tutorial teaches them once and this is there when
  they are wanted.
  ⚠️ **This read "which §8 teaches on first play", and the load has since reversed.** The sheet was
  justified by the tutorial having already taught the rules; now the tutorial is skippable (§1b) *because
  this sheet exists*. Whichever way the sentence is written, exactly one of the two may be optional —
  and the sheet is the one that cannot be, since a player who skipped the tutorial has nothing else.
- **A button rather than permanent**, because on 375px there is no room for a permanent strip. On paper
  there is, and that is exactly what the pack does.
- **In the board's chrome, not in the keypad.** Both were rendered: *The relations* wraps onto two lines
  inside a 66px pad key. It also has to stay reachable on a finished board, where there is no keypad.

---

## 4. The clock is invisible until the end

§26 decided the timer runs for everyone, silently. **Taken to its clean form: the player never sees it
during play.**

**A visible clock changes how the game is played, not only what is seen afterwards.** §26 says this about
tiers — *if the clock runs you rush, if not you savour* — and it is just as true of a counter on the
screen. And §2's audience are baseball fans who may not be puzzle people: **a number climbing in the
corner is what makes that person quit.**

**The time appears at the end**, where it cannot pressure anyone and where it does the one job it has:
being shared.

---

## 5. What stops the clock

It must count **only time with the board open**. A player who pauses for lunch and comes back to an
absurd number has a time that means nothing, and sharing a meaningless number is worse than sharing none.

**Two signals, together:**

| signal | what it catches |
|---|---|
| **Page visibility** | app switch, minimise, screen lock. Stops immediately, resumes on return |
| **An inactivity timeout** | the tab left open on a desk |

⚠️ **The timeout is generous — five minutes or so — and the reason matters more than the number.** In a
deduction puzzle it is normal to stare at the board without touching anything, and **that staring is
play**. A short timeout would discount exactly the thinking the game is about. If the number is wrong it
should be wrong in this direction.

### The honest limit

**None of this is tamper-proof.** Someone can stop the clock and go on thinking, and the accumulated time
sits in `localStorage` where anyone can edit it.

That is acceptable because of what the time is for. §26 already dropped the public global leaderboard,
and one of its two reasons was exactly this: *the solution lives in the client and so does the timer, so a
public ranking is trivially manipulable.* The time is **shared between friends, not ranked**. It has to be
reasonable, not inviolable — and building server-side verification would fight the static architecture
§23 depends on, at high cost, for the most fragile feature there is.

---

## 6. Persistence

**`localStorage`, not cookies.**

Cookies travel to the server on **every request**, which is wasteful for data the server does not want,
and they are size-limited in a way a board of filled cells will meet. C7 already requires events to be
stored locally first. There is no case for cookies here.

### What persists

| | |
|---|---|
| **The filled cells** | so the board comes back as it was left |
| **The accumulated time** | see the warning below |
| **The event record** | C7's shape, uploaded when there is a connection |

⚠️ **Accumulated time, never a start timestamp.** The clock pauses, so a start time would count the pause
— which is the whole thing §5 exists to prevent. The stored value is a duration that grows; it is never
`now − started`.

### The day

The puzzle **stays open all day and saves itself** (§27). At midnight it closes for streak purposes and
remains playable from the archive. **Tomorrow is a different puzzle**, with its own saved state — nothing
is carried across.

*What time midnight is — local or UTC — is still open (§36) and does not block any of this.*

---

## 7. Finishing

**A screen effect, then a transition to the official boxscore of the game: names, teams, date, the real
thing.**

This is §7's reveal, and it is **built**. A successful *Check* draws it, and a finished session that is
reopened draws it again from the frozen record rather than from a fresh reading of the clock.

⚠️ **This read "it ships in every package already and is drawn nowhere — the single thing the player
never receives".** That was true when this document was written and it is history now. Kept as history
rather than deleted, because the sentence records why the reveal was built before anything else in the
finish path: it was the payoff, and it was shipping unopened in every file.

**It is a printed boxscore, not a results card.** Both clubs, `AB R H RBI BB SO`, the clubs' real names,
the footnote line and the line score — package schema 5 exists to carry it. The first attempt drew the
board's own six columns with the names attached, which is the board relabelled rather than the object
the player reconstructed.

The reveal is where the names appear for the first time. Nothing during play is labelled by name (§7);
rows are positions throughout, and the boxscore at the end is the answer to *whose game was this*.

---

## 7b. The share is a PNG of the board — decided, not built

**The board itself, as an image. The cells the player filled in are replaced with random digits and
then blurred; the given cells show their real values.** With it go **the time, the hints used and the
tries**, because §26's comparison rests on them and a result carrying one without the others cannot be
compared to anything.

⚠️⚠️ **Tries is shared, and that is a decision rather than a consequence.** It appears on the reveal,
the share carries what the reveal shows, so it would have arrived in the image whether or not anybody
chose it. **Said here so it is chosen.**

The argument is the one that admitted hints: *a hint does not corrupt a shared result if it is shared
alongside the time*. **A time reached on the first attempt and the same time reached after fifteen is
two different results**, and every reader takes them as two — so hiding the count would make the time
mean less, not more.

⚠️ **What it counts and what it is called are different on purpose.** The C7 record stores
`failed_checks`: presses of *Check* on a **completely filled** board that did not balance. An
incomplete board is never counted — that is a mistake about the state rather than an attempt at the
answer. The reveal shows **Tries**, which is that plus the one that worked, so a clean solve reads
`1` rather than `0`.

⚠️ **The label is not "failed checks", and §27 is the reason.** The game cannot be lost; a tally of a
player's failures on the screen celebrating their finish argues the other way. What the number
measures is attempts, and it says attempts.

**What it is for**: pseudo brute force. A player who fills the board, checks, fails and checks again
without changing much is probing; one who fails, reviews and corrects is not. `errors` cannot see the
difference — it is a **set** of first-wrong cells, so twenty presses look identical to one. **Two or
three tries says nothing; twenty does**, and the separation is at the tail.

### ⚠️ The blur is not what protects the puzzle — the random digits are

This is the whole design and it is easy to get backwards. A blur is concealment, and concealment
invites reversal: deblurring is a solved problem, the image is small, the glyph set is ten digits in a
known typeface, and the grid positions are fixed. A blurred *real* board is a puzzle waiting for
someone with a deconvolution script.

**Replace the values first and the attack has nothing to reach.** Anyone who reverses the blur
perfectly recovers **noise**, and — this is the part that matters — **has no way to tell it is noise**.
The identities do not balance, but they do not balance in the same way a wrong guess does not balance,
and the recipient cannot distinguish "I recovered the answer" from "I recovered garbage that looks like
an answer". It stops being concealment and becomes publishing garbage, which is not an attack surface.

⚠️ **So the blur is doing a different job: it is typography, not security.** It makes the image read as
a finished boxscore at a glance instead of as a wall of arbitrary numbers, and it signals *these were
mine* against *these were given*. If the blur were removed entirely the design would still be safe and
would simply look wrong.

### Why an image at all

**A boxscore cannot be represented in characters the way Wordle's rows can.** Five squares in three
colours are a shareable line of text; a grid of ten rows and six columns with a totals row, a line
score and a footnote line is not. Any text encoding of it is either enormous or an abstraction that
throws away the one thing worth sharing.

And the abstraction loses the point. **The board should read as full and finished — the way a
reconstructed boxscore looks — rather than as a lattice of squares.** The product's claim is *I rebuilt
a real game from arithmetic*; the artefact has to look like the thing that was rebuilt.

### What was considered and rejected, with the reason each fails

Recorded so none of the three returns as an obvious improvement.

| Rejected | Why |
|---|---|
| **Marking which cells were blank** | Tells the recipient exactly where the holes are — the shape of the erasure *is* the puzzle, and a heat map of it is a solution aid handed out for free |
| **A text-only line** | Safe, and says nothing about what the player actually did. It carries a time and a verdict and no evidence of a board, so it markets nothing |
| **Blur without random digits** | ⚠️ **A blurred digit keeps its shape.** `1` does not look like `8` at any radius that still reads as a boxscore, and stroke density survives blurring — so a blurred real board leaks the answer to anyone patient, and leaks it *correctly*, which is the difference between this and the accepted design |

### ⚠️ What has to come before it, and this is an ordering decision rather than a preference

**The tutorial and the landing page ship before the share.** Today the game drops straight onto the
board, and a board that appears with no explanation is where §2's fragile audience leaves.

⚠️ This argument used to rest on §8 making the tutorial compulsory. It does not any more (§1b) and the
ordering is unchanged — **skippable is not the same as absent.** A share that lands a stranger on a
board with no way to learn the rules is the problem, and whether the newcomer is *forced* through the
door has nothing to do with whether the door is built.

**There are now five relation families, and one of them cannot be inferred from looking at the board.**
The batting order relation is not visible in any row or column the way the column sums and the row
identity are — a player who starts cold is being asked to deduce using a rule nobody told him about.
The reference sheet (§3b) states it, and a sheet the player has no reason to open is not onboarding.

So the share is the growth channel and it would be **sharing a game the first-time visitor cannot
understand**. Building it first optimises the funnel's top while the step below it is missing. The
onboarding has to work before the thing that brings people to it.

### ⚠️ The button exists and does nothing — deliberately, since 2026-08-22

The reveal carries a *Share* button beside *Back to the board*, `disabled`, with the three-node web
share mark. Operator's instruction: **place it in the UX now, before it works.**

**The reason it is worth drawing early** is that the reveal is where the decision to show anyone gets
made, so where the button sits changes what the rest of that screen can be. Discovering that after the
grid is built moves every other control on the screen.

⚠️ **`disabled`, not merely unwired.** A button that looks pressable and does nothing makes the player
doubt whether the result was recorded — which is the one thing the reveal exists to tell them. Disabled
says *not yet* in the language every platform already speaks.

**Nothing above this heading is relaxed by it.** The ordering still holds: the grid does not get built
before the onboarding, and the grid must still never leak the solution or a player's name (§7). What
exists today is a shape on a screen.

---

## 8. Statistics — for the operator, not the player

C7's per-game record already carries the essentials: **starts, completions, duration, errors, and the
highest technique required.** From those: how many start and finish each day, how long they take, and
**which days people abandon** — which is the real difficulty signal, more honest than any metric the
generator computes about itself.

### What does not exist yet and is needed

- **Retention** — how many return the next day, at seven days, at thirty. §20 is explicit that a thousand
  people who try is easy and a thousand who return on day 30 is the problem.
- **Streak distribution, and how many break a streak and never return.** §27 warns that guilt expels;
  without this number that warning stays an assumption.
- **Conversion**, once there is a paywall.

⚠️ **And nothing beyond what will actually be looked at.** §35's *minimum to operate* applies to analytics
exactly as it applies to identity: every extra field is leak surface and compliance work. A metric nobody
reads is a liability with no upside.

---

## 9. Where it lives

**In the VPS's database** (§33). User data is written only by the serving tier; the laptop never sees it,
and the forge never learns that users exist.

### ⚠️⚠️ Superseded 2026-08-22: it is Postgres, behind an interface, in its own service

**`docs/data-layer.md` is the standing decision and this section is the record of the one before it.**
The user data now lives behind a third service beside `serve` in the same Docker network, and `serve`
never learns which engine is underneath.

**What changed is not an argument below — it is a fact none of them had.** The operator already runs and
maintains a Postgres instance on the VPS. Every reason SQLite won was some form of *one fewer piece to
administer*, and that reason evaluates to nothing when the other piece is already there and already
being administered. **Postgres stopped being a piece to stand up and became a piece to use.**

⚠️ **So the two invalidating conditions below are not what invalidated it**, and that is the part worth
keeping. They were the right conditions — more than one server, genuinely concurrent writes — and
neither has happened. The decision was overturned by a **third** thing the list did not contain, which is
the ordinary way a well-reasoned decision dies: not by one of its stated conditions firing, but by a
premise quietly ceasing to hold. A conditions list is not a tripwire around every way of being wrong.

⚠️ **`Do not stand up Postgres now "just in case"` was right when it was written and is not being
reversed as an error.** Nothing is being stood up. The instance exists.

**SQLite is not gone**: it stays for local development and tests, which is where its simplicity was always
the strongest part of the case. ⚠️ That leaves two engines behind one interface — two places that should
say the same thing — and `data-layer.md` §2 carries the obligation that follows, plus the open question of
whether SQLite is *supported* or only *convenient*.

**Everything below this heading is the superseded reasoning, kept because it was not silly and because
the WAL and backup notes still apply to the development database.**

---

**The real load is tiny.** Puzzles are static files served by nginx, so the database only sees token
refresh, device registration and event upload. At nine thousand accounts that is tens of thousands of
operations a day.

**The writes are spread out.** SQLite's weak point is concurrent writing, and events arrive one at a time
as people finish — not in bursts.

**It is a file.** Backing it up is copying it, and that is one fewer piece to administer on the VPS. §23
asks for availability from **having fewer pieces rather than bigger ones**, and this is that argument
applied.

### Two things it needs done right

- ⚠️ **WAL mode from the start**, or reads block while a write is in progress.
- ⚠️ **Backups through SQLite's own online backup API, never `cp` on a file being written.** A copy taken
  mid-write is a corrupt database that looks like a file until the day it is needed.

### The two conditions that would invalidate the choice

Written now so the decision can be revisited without rebuilding the reasoning:

1. **More than one server.**
2. **Genuinely concurrent writes.**

Neither is close. Migrating to Postgres later is known work that only becomes necessary at a scale that
would pay for it.

⚠️ **Do not stand up Postgres now "just in case."** That is one more piece that can fall over at three in
the morning, bought against a load that does not exist.

### Uploading

**The event saves to `localStorage` first and uploads when there is a connection.** That ordering is what
makes §23 true: with the backend down, login and sync fail and **the game still works**. Nothing in the
play path may wait on the network.

---

## 10. Players without an account

**Events upload under the device UUID §11 already creates.**

Decided, and the reason is not convenience: **otherwise the retention numbers would cover subscribers
only** — and the retention of people who do not pay is what decides whether this grows at all (§20).

### One detail that is cheap now and expensive later

⚠️ **When an anonymous player registers, their earlier events must be attachable to the new account.**

- The event carries **the device UUID always**, and the account identifier when one exists.
- On registration, that device's events are attributed to the account.
- **Without dropping the UUID** — the same device may keep being used signed out, and the link has to keep
  working in both directions.

Retrofitting this means either losing every pre-registration event or reconstructing an association
nobody recorded. It costs one column now.

⚠️ **The honest limit:** a shared device conflates two players into one series. Nothing here detects that,
and nothing should try — detecting it would mean fingerprinting, which §35 rules out. The retention
numbers are approximate at the edges and that is the correct trade.

**§35 is amended to state that anonymous statistics are inside the minimum to operate**, with this
reasoning, so a later reading does not treat them as data kept "just in case".

---

## What this closes in §36

- **Error handling** — validation on *done* only; no limit, because §27 forbids a fail state (§2 above)
- **What a hint is** — three per game, revealing the selected cell, shared alongside the time (§3).
  ⚠️ This read *"there are none, and §22's guarantee is why"* until 2026-08-20; the guarantee is intact
  and was never the question a hint answers
- **The reference sheet** — the five relations on a button, costing no hint (§3b)
- **The landing page and the tutorial** — every visit lands, the tutorial is five steps and **skippable**
  (§1, §1b). ⚠️ The skippability reverses §8, on the reasoning that a compulsory tutorial is a barrier in
  front of someone who has not decided yet, and that the reference sheet removed the tutorial's status as
  the only place the rules are stated
- **Saving, pausing and resuming** — the mechanics, where §27 had only the promise (§6)
- **What the clock counts** — visibility plus a generous inactivity timeout, invisible until the end
  (§4, §5)
- **What gets measured, and retention metrics** — §8 and §10, though none of it is built

- **What the share encodes** — a PNG of the board, the player's own cells replaced with random digits
  and blurred, the given cells real, carrying the time and the hints used (§7b). ⚠️ Decided and **not
  built**, and deliberately not built first: it ships after the tutorial and the landing page

**Still open and untouched by this document:** what time the puzzle rolls over, and how candidates mode
works without hover.

---

## Then, and not before

The implementation order was: **persistence, then the solved state and the reveal.** Persistence
because C7 is irreversible; the reveal because it was the payoff and, at the time, the one thing the
player never received.

⚠️ **Both are done.** Persistence survives a reload and a completed board reopens finished, read-only,
with its earned time unchanged. The reveal is a printed boxscore. This section is kept as the record of
the order the work was taken in, and it is no longer a plan.

Neither should have been started before this document existed.
