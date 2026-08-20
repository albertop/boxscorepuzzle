# The batting-order plan, as agreed — and what has been built against it

**Companion to `batting-order-reversal.md`**, which is the record of how a recommendation was given,
reversed under one push, and overstated in both directions. This file is the plan agreed afterwards
and the state of the build against it.

**The ordering principle the operator set:** cheap isolated code → hand-solve → reconcile coverage →
larger confirmation → verifier → publication.

⚠️ **The verifier is the irreversible spend, and there is no urgency**, because boards leaning on the
constraint cannot publish without it. **Waiting creates no product risk.** That is the load-bearing
fact of the whole plan: every step before the verifier is reversible, and the gate holds itself shut
while they run.

---

## ✅ ADOPTED — the plan below is the record of how it got here

**The operator adopted the constraint.** Steps 1 and 2 are unfrozen and in production, step 3's
verdict is in, and step 4 — the verifier's lineup step — is written. What remains is step 6, the
re-measurement, and it matters: **every figure that decided this was measured while layer 3 could not
certify a board leaning on the constraint.**

The decisive evidence is not in any table: the operator solved the five hand-solve boards with it
active and reported that it makes them harder — not because it resolves more cells, but because the
player has to hold one more rule in their head. Recorded in `batting-order-reversal.md`, with the note
that it is a human verdict rather than a measured quantity.

## Step 1 and 2 — BUILT, then frozen

**Conditional retry.** `boxscore_forge.lineup_fallback.erase_with_lineup_fallback()` tries the ordinary
path first and retries with the batting order only when the target is missed. **Boards that already
reach their target never see the constraint**, so they never pay the division-filler cost. Same seed
and same ordering in both attempts — the two differ in treatment, never in trajectory.

It returns the puzzle **and why it is the puzzle**: `plain`, `fallback`, `discarded_filler` or
`unreachable`. Returned rather than inferred, because `plain` and `fallback` are different populations
and that distinction is the entire finding; a caller made to work it out will work it out wrongly.

**The filler cap.** `LINEUP_DIVISION_SHARE_CAP = 0.20`, `PROVISIONAL`, in `boxscore_domain` with its
origin recorded: **it came from looking at two boards, not from a measurement.** Nine of the eleven
gained directions carry no division at all; two carry 38% and 35%. The cap separates those groups and
nothing more. The gap between 2% and 35% is wide enough that any threshold inside it would do the same
job on this sample — which is precisely why the sample cannot justify `0.20` over `0.25`.

⚠⚠ **And the first implementation applied it to the wrong quantity** (v27-P2-13). The `0.38` and
`0.35` are division steps over **chain length**; the code divided by the **deduction count**, which on
one specimen is 37 against a chain of 20. So the cap would have kept both boards it exists to discard.
Fixed as `division_against_chain()`, with a test that changes its verdict when the denominator changes.
⚠️ **The unit itself is provisional**: it is a ratio, not a share, and not bounded by 1, since the
numerator counts steps and the denominator is a depth. Settling the unit is on step 6's list.

**Publication stays disabled, and it is a check rather than an intention.**
`test_lineup_fallback_cannot_publish.py` scans every first-party module for one whose dependency
closure reaches **both** the experimental fallback and `certify_for_publication`, walks every call to
`erase()` across the tree and refuses `slots` outside the experimental module, and fails if
`LINEUP_ARITHMETIC` ever appears in `boxscore_verify` — that last one **on purpose**, so that writing
the verifier's lineup step is a deliberate decision rather than something that happens on the way to
something else.

⚠⚠ **Two of the first four guards could not fail, and the mutation check agreed with them.** v27-P2-14
and v27-P2-15. The production guard looked for a *keyword* named `slots` while the real call passes it
positionally, and the publication guard walked imports **outward** from certification while a forbidden
path runs the other way — a producer importing the fallback *and* certification. **The mutations used
to "verify" them were the changes those guards could see, not the risks they name.**

Replaced, and re-checked against the real wiring: a production module actually calling
`erase(..., slots=lineup)`, and a third module actually bridging the fallback to
`certify_for_publication`. Both fail the suite. The bridge test now scans every first-party module for
one whose dependency closure reaches **both** endpoints.

⚠️ **A graph guard survives only until someone refactors imports.** The durable form is making
experimental provenance **unrepresentable** as an ordinary publishable result — a distinct result type
that only research code accepts, so the safety property does not depend on the shape of the import
graph. **Not built**, because the freeze is at steps 1 and 2; recorded here so it is a decision rather
than an omission.

**The verifier's lineup step is not written.** Layer 3 cannot replay a `batting_order` move, so any
board leaning on the constraint is refused as underivable. **That is the gate, and it is holding.**

### Frozen here

No regenerating of final inventory. Nothing presented as adopted. `erase()` gained an optional `slots`
parameter that defaults to empty, and production keeps omitting it — a parameter rather than a second
erasure function, because a walk that exists twice drifts.

---

## Step 3 — hand-solve. ⚠️ The question is narrower than the plan first stated

The plan said the five-board pack determines "whether 5 is hard and whether 8 is a useful level." It
does not. **Three boards are at 5 and two are at 8.**

- **The primary question is whether 5 stalls is already hard.** Three boards can say something about
  that.
- **Two boards cannot settle whether 8 is a useful rung.** They can suggest. When the sheets come back,
  anything about 8 is a **hint, not an answer**, and must be written down that way.

⚠️ **If 5 turns out hard, the gate closes and nothing about 8 needs answering at all** — and with it,
the whole batting-order question goes away, since its only established value is at the hard end.

### ✅ The verdict came back, and it decided the adoption

The operator solved the five with the constraint active. **It makes them harder**, and the reason is
not one this instrument can see: the player has to hold one more rule in their head. Stall counts
measure how often propagation runs dry; they say nothing about sustaining five relations instead of
four.

⚠️ **The same class of finding as the footnote zeros** — knowable only by doing the task, and pointing
slightly away from what the metric measures. There the number said 5 stalls to 15 and the player was
typing zeros; here the number says less than the verdict does.

---

## Step 4 — reconciliation, then an authoritative instrument. ⚠️ Not a plan B

The plan made the authoritative instrument conditional on the reconciliation failing. **It is not
conditional. Build it either way.**

Coverage at eight stalls currently has three values — **33%, 50%, 79%** — from three instruments.
Three numbers for one quantity means **nobody knows what it is**, and decisions have already been taken
on it. More comparisons are coming: the ladder, the pitcher-cap re-verification, whatever follows.
They need a measure that can be trusted, and one does not exist today.

The reconciliation table still comes first, because knowing *why* the three differ is what tells you
what the authoritative instrument has to control for.

---

## Step 5 — the decision gate

Unchanged.

## Step 6 — the confirmation run, pre-registered

⚠️ **The pre-registration is the part that matters most.** `gained`, `lost` and `common` are defined
**before the run**, in writing, along with what result would count as adoption and what would not.

Defining the categories before seeing the result is what stops it being read in favour — and **this
project has had two results read that way already**, including one this week where a subgroup chosen
after seeing the aggregate produced the answer the pressure pointed at.

## ✅ Step 7 — the verifier, written

`lineup_values()` in `boxscore_verify/reason.py`, derived from the rule rather than from the
generator, and value-aware because narrowing the relations to a fixed point still leaves every slot a
range. Both derivability layers read the lineup off the package.

⚠⚠ **Two things surfaced the moment it existed.** The batting-order relations had never been
generated — `relations()` took a `slots` argument and every call site passed nothing. And both board
strategies were building lineups no game can reach, because the arithmetic identities never implied
the cyclic distribution and nothing could see the difference while the family was unused.

⚠️ **It also catches the phantom row of noughts**, which is the defect that produced the plausibility
layer. That does not make plausibility redundant: a version 1 package carries no slot references and
applies no batting-order relation, and three centre fielders in one lineup balances every identity and
every place.
