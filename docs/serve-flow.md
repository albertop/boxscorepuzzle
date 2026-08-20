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

**The player does not land on the puzzle.**

A landing page carrying, at minimum, the tutorial and a button for today's game. §8 makes the tutorial
non-skippable on first play, and a board that appears with no explanation is where §2's fragile
audience — the baseball fan who is not a puzzle person — leaves.

**It later carries social login and the subscription**, which buy the archive and the global ranking. The
page has to be laid out so those arrive without rebuilding it. That is the same discipline as seams C8,
C9 and C10: the shape is present before the feature is.

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
- **It costs no hint and is not one.** A hint hands over an answer; this hands over the rules, which §8
  teaches on first play. The difference is that §8 teaches them once and this is there when they are
  wanted.
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

This is §7's reveal. ⚠️ **It ships in every package already and is drawn nowhere.** It is the game's
payoff and it is the single thing the player currently never receives — the board is solved and then
nothing happens.

The reveal is where the names appear for the first time. Nothing during play is labelled by name (§7);
rows are positions throughout, and the boxscore at the end is the answer to *whose game was this*.

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

### The database is SQLite — decided, with the reasoning and not only the choice

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
- **Saving, pausing and resuming** — the mechanics, where §27 had only the promise (§6)
- **What the clock counts** — visibility plus a generous inactivity timeout, invisible until the end
  (§4, §5)
- **What gets measured, and retention metrics** — §8 and §10, though none of it is built

**Still open and untouched by this document:** what time the puzzle rolls over, what the share grid
encodes, and how candidates mode works without hover.

---

## Then, and not before

The implementation order stands: **persistence, then the solved state and the reveal.** Persistence
because C7 is irreversible and the piece is already written and tested; the reveal because it is the
payoff and it is the one thing the player never receives.

Neither should have been started before this document existed.
