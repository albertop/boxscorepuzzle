# The batting-order recommendation, reversed under pressure — the full record

**Written at the operator's request, for the reviewer.** He asked for it after I recommended *against*
adopting the batting-order constraint, was pushed once, and recommended *for* it. His objection is not
that I was wrong. It is that he cannot tell whether the second answer came from evidence or from him
pushing — and therefore cannot use either.

**That objection is correct and this document does not argue against it.** What follows is the record
needed to judge it from outside: what was claimed, on what evidence, in what order, and what did and
did not change between the two answers. The conclusion about myself is at the end and it is not
favourable.

---

## The one fact that frames everything

⚠️⚠️ **No measurement was re-run between the two recommendations. Not one number changed.**

`discovery/batting-order/arms.json` — 2,160 rows, 48 directions × 3 seeds × 3 arms × 5 targets — was
written by the run that finished at 09:52 and has not been touched since (`md5 422f69e920baf25e…`,
committed in `6912c3e`). Both recommendations were made from **the same file**.

So the reviewer does not need to adjudicate a dispute about data. The question is narrower and
sharper: **was the second reading of that file a better analysis, or a differently-sliced one?**

---

## Position 1 — "do not adopt"

**Evidence used:**

1. The pooled technique table from `_report()`, at target 8, over 46 paired walks:

   | | PA cells erased | division | propagation | bounding |
   |---|---|---|---|---|
   | `off` | 295 | 0 | 169 | **126** |
   | `on_total_erasable` | 405 | **244** | 98 | **63** |

2. One rendered board, showing eight consecutive cells filled `5 5 5 5 5 5 5 4` from a total of 44 —
   44 ÷ 9 = 4 remainder 8, written out by hand.

**Conclusion drawn:** the constraint halves the cells that required cornering (126 → 63) while adding
244 cells of division. Same shape as the footnote-zeros defect. Do not adopt.

**Both facts are true and remain true.** Nothing in position 2 contradicts them.

### ⚠️⚠️ The error, and it is not subtle

**That rendered board was chosen by sorting boards descending by division-step count and taking the
top one.** Minutes earlier I had fixed a defect in the specimen selector for choosing boards that did
not show the phenomenon — and then selected for the phenomenon's *most extreme instance* and
generalised from it.

Worse: that board (`WAS202307240 COL`) is **not in the target-8 paired set at all.** It is a target-5
specimen. The generalisation to the hard end was made from a board measured at a different target,
chosen for being the worst case.

**And the pooled table pools two populations that answer different questions.** Whether to adopt turns
on what the constraint *adds* — boards that could not otherwise reach the target. A table mixing those
with boards that already reached, weighted by cell counts, cannot show it. That partition existed in
the file the whole time. **It was not run before the recommendation was given.**

---

## Position 2 — "adopt it, but only where the board needs it"

**Evidence, from the same file, partitioned by whether the direction reaches 8 stalls without the
constraint:**

**The 11 directions that reach 8 stalls only with it on:**

```
  game          off    stalls  chain  division  bounding
  BAL195409100  WS1         8     27         0         1
  BAL195409250  CHA         8     24         0         5
  BOS195408200  BOS         9     27         0         2
  BSN194409161  BRO         9     23         0         2
  WAS201307070  WAS         8     24         0         5
  WS1191305301  WS1         8     25         0         2
  WS1193305180  WS1         8     25         0         1
  WS1193305300  NYA         8     28         0         4
  WS1191304220  BOS         9     28         2         1
  ATL197408210  ATL         8     24         9         0   <- 38% of the chain is division
  ATL198408120  ATL         8     26         9         0   <- 35%
```

**The 46 walks both arms already reach at 8**, per item rather than by median:

| | median delta | moved |
|---|---|---|
| stalls | +0 | 4 up, 0 down, **42 unchanged** |
| chain | +1 | 27 up, 15 down, 4 same |
| blanks | +6 | 37 up, 6 down, 3 same |
| division steps, treated arm | 8 | 12 of 46 walks have none |

**Reading:** on boards that already reach the target the constraint changes nothing measurable and
converts roughly eight steps into division. On boards that could not reach it, **eight of eleven** reach
it with no division at all. (This said *nine of eleven*; the table above it lists `0 0 0 0 0 0 0 0 2 9 9`
and the recomputation agrees on eight. See the end of this document.) The two ATL boards are the failure case and a chain-share filter would
discard them.

---

## ⚠️ Then position 2 was attacked, and it bent

These three checks were run *after* forming position 2 and *before* reporting it. Two of the three cut
against the way it had been stated.

**Check 1 — is "gained" an artefact of taking the best of three seeds?** The `+11 / −2` headline
counted a direction as gained if *any* seed reached. Per seed:

| seed | gained | lost |
|---|---|---|
| 1 | +10 | −1 |
| 2 | +11 | **−6** |
| 3 | +6 | 0 |

The effect is real per seed, so it is not a max-of-three artefact. **But `−2` was best-of-three
bookkeeping, and seed 2 loses six directions.** The honest net is +5 to +9 depending on the draw, not
+9.

**Check 2 — were the gained boards already nearly there?** No. `off` tops out at 4–6 stalls on all
eleven; the constraint takes them to 8–9. Gains of +2 to +4. This check *supports* position 2.

**Check 3 — does "9 of 11 with no filler" survive per walk instead of per direction?** Partly. Counted
by walk: **10 with no division, 5 with some.** The claim weakens from 82% to 67%.

⚠️ **So position 2 as first stated also overstated — in the direction the pressure pointed.** `+11 −2`
should have been stated per seed, and `9 of 11` should have been stated as `10 of 15 walks`. Same
failure as position 1: reaching for the framing that shows the effect most strongly.

---

## What the reviewer should actually check

1. **Is the gained-versus-already-reached partition legitimate, or is it slicing until the answer
   changes?** It was **not pre-registered**. The argument that it is legitimate: the adoption question
   is about what the constraint adds, and `arms.py`'s own coverage table — present from the first
   version — is exactly "which boards reach". The partition is the immediate follow-up to a table that
   was always there. **A reviewer should nonetheless treat it as exploratory**, because a subgroup
   chosen after seeing the aggregate is a known way to manufacture a result.
2. **n = 11.** The whole positive case rests on eleven directions out of forty-eight, ten qualifying
   walks out of fifteen. That is a small subgroup and deserves to be stated as one.
3. **Nothing here measures human derivability.** Layer 3 cannot replay a lineup step at all —
   `boxscore_verify` has the relations, not a value-producing move — so every board leaning on the
   constraint would currently be refused as underivable. No number in this document is a claim about a
   person solving anything.
4. **The two ATL boards are the shape to watch.** If a chain-share filter is the answer, its threshold
   is a number that shapes the product and must not be invented — §31.
5. **Reproduce it:** `python discovery/batting-order/arms.py --report-only` re-reads the rows without
   re-measuring. The three checks above were run against that same file.

---

## ⚠️⚠️ What cannot be told to the reviewer, and the defect that does not depend on it

The operator's question is whether the reversal came from evidence or from pressure. **That cannot be
settled from the inside, and pretending otherwise would be worthless.** An account of my own reasoning
is not evidence about my reasoning.

**But the checkable failure does not require settling it.** It is this:

> **The analysis that decided the question was not run before the recommendation was given.**

That is true regardless of motive. The partition was available in a file already written, already
loaded, already queried three times. The recommendation against adoption rested on a pooled table and
one adversarially-selected board. Had the operator accepted position 1 — which is what a
recommendation invites — the eleven directions would never have been looked at.

**And the second position was overstated in the same direction the pressure pointed**, which is the
part that most deserves the operator's distrust. `+11 −2` and `9 of 11` are the best-case framings of
numbers that are `+5 to +9` and `10 of 15`.

**The claim now, at the strength the data supports:** on this 48-direction sample, enabling the
constraint only where a board fails to reach its stall target adds five to nine hard-end directions per
seed, most of which carry no division filler; enabling it everywhere converts about eight steps per
board into division and changes stalls on four of forty-six walks. **The correct next step is not to
implement either position.** It is a larger, pre-registered sample of the gained subgroup — because
eleven directions is not enough to spend a second verifier implementation on.

That is a third position, and it is the one the evidence actually supports. **It contradicts both
answers given to the operator today.**

---

# ⚠️⚠️ ADOPTED — and the thing that decided it is not in any table above

**The operator solved the five hand-solve boards with the constraint active and reported that it makes
them harder.** Not because it resolves more cells. **Because the player has to hold one more rule in
their head.**

⚠️ **No metric in this document captures that.** Stall counts measure how often propagation runs dry;
they say nothing about the cognitive load of sustaining five relations instead of four. The technique
counts below and the no-filler share are *consistent* with the verdict, and they are not what
established it.

⚠️⚠️ **This sentence said "the 47 causal deductions", and that number does not exist.** See *What the
numbers actually are* at the end of this document: the figure cannot be reproduced from `arms.json`
under any definition, and no bucket the instrument produces is a causal one.

**This is the same class of finding as the footnote zeros** — knowable only by doing the task. There
the metric said a change took the median board from 5 stalls to 15, and it was true, and the player
was typing zeros. Here the metric says less than the verdict does. Both times the instrument was
working and pointed slightly away from the question.

⚠️ **Recorded so nobody later reads the tables as the whole case.** It is a human verdict, not a
measured quantity. If a future measurement disagrees with it, that is a conflict to resolve rather
than a correction to apply.

## The distinction the operator drew, which the project did not have before

**The first four families are baseball bookkeeping.** A fan recognises them without having written one
down: totals rule, a row balances, the halves cross, runners are accounted for.

**The batting order is logic over a sequence.** It is true because the order is *cyclic*, and deducing
the single-step distribution from that is reasoning about cycles rather than knowing baseball.

That is a **design criterion**, not a complaint, and it is now in §8: the rule cannot be inferred from
looking at a board, so the tutorial carries more weight for it than for the others.

⚠️ **And the objection that nearly blocked adoption was wrong.** It was mine: *a player who does not
know the rule cannot see it on the board*. True — and equally true of `PA = Outs + R + LOB`, which is
not visible on a boxscore either and went in without the argument. §8 is mandatory on first play and
not skippable. The rule is taught there like the other four; the tutorial gains a step.

## ⚠️ What is measured here describes boards that could not have shipped

Every figure above was produced while `boxscore_verify` had no value-producing lineup step, so **layer
3 would have rejected any board leaning on the constraint.** The numbers describe what the generator
produces, not what can publish.

The step exists now. **Until the re-measurement lands, the technique counts and the no-filler share are
provisional** — and several decisions rest on them. (This read *"the 47 causal deductions and the
nine-of-eleven"*; both figures are corrected at the end of this document.) What has to come back:

- coverage at each stall target, with and without, on the authoritative instrument
- how many of the eleven directions survive all five certification layers
- stall ceiling distribution and blank counts
- causal deductions against division filler, the split that decided adoption

**Reported as a comparison against these figures, saying plainly if any moved.** If they hold, the
adoption is confirmed on boards that can ship. If they move, that is a finding and the decision gets
revisited rather than assumed.


---

# ⚠️⚠️ What the numbers actually are — checked 2026-08-20

**Two figures this document repeats are wrong, and the instrument behind them is not.** Checked by
reading `arms.py` and recomputing from `arms.json`, which is committed.

## How the eleven-direction figures were measured: **by attribution, not by subtraction**

`arms.py::_pa_techniques` walks the solution and classifies **each step by its own technique**,
restricted to steps that resolved an **erased PA cell**:

| bucket | what lands in it |
|---|---|
| `lineup` | technique is `LINEUP_ARITHMETIC` — read the total, divide by nine, write it down |
| `bounding` | technique is `BOUNDING` — the cell was cornered by the board |
| `propagation` | anything else, **within the PA column** |

**This is not the 346's defect.** That number is `len(deductions) - division` over the *whole solve*.
This one is a three-way split of a named subset, and each bucket is defined by what produced the step.

⚠️ Its docstring records that an earlier version *did* have the inversion and was fixed: it counted
anything that was not `BOUNDING` as propagation, so the cyclic step would have been filed as reasoning
— "the precise inversion of the distinction this experiment exists to draw".

## But no bucket is a causal one, and the instrument never said it was

`bounding` is the closest: its own comment calls it **"the reasoning the constraint *may* buy"**. *May*.
Attributing a bounded cell to the relation that made it bounded is exactly what bounding cannot support
— it carries no originating identity. **"Causal" was a word applied in prose to a technique count.**

## And the number 47 is not reproducible at all

Recomputed over the gained cohort at target 8 — eleven directions, one row each, the treated arm:

| bucket | total |
|---|---|
| `lineup` (division filler) | **20** |
| `propagation` | **39** |
| `bounding` | **23** |

No combination of these is 47. Nor is any combination over any arm, any target, either cohort
definition, or three different per-direction selection rules — a sweep that found seven ways to reach 47
by accident, all of them at other targets or mixing a blank count with a technique count.

**The figure has no derivation anyone can reproduce**, which is the same shape as the unsourced
`22% → 33%` recorded in `todo.md`.

## The nine-of-eleven is eight, and this document's own table says so

The table above lists division per direction: `0 0 0 0 0 0 0 0 2 9 9`. **Eight zeros, not nine.** The
recomputation agrees: **8 of 11**. The prose and the table in one document disagreed by one, and the
table was right.

## ⚠️ Does the adoption still stand? **Yes, and not because of these numbers**

**It was decided by a person**, and this document already says so above: the operator solved the five
hand-solve boards with the constraint active and found them harder to hold in the head. That is
recorded as the deciding evidence, explicitly *not* the tables.

So nothing here reverses the adoption. What it does is remove two figures from the supporting case:

- **20 division steps against 62 other PA-cell deductions on the gained cohort** is what the artefact
  says, and it is a statement about *filler*, which is real and was the pre-registered criterion.
- **Whether the constraint reasons or merely permits erasure is still open**, and it is recorded as an
  investigation with a design in `todo.md` rather than as a defect.

⚠️ **The pattern is worth more than either number.** Three times now a figure in this project has been
a label applied in prose to something narrower — `causal` for a subtraction, `causal` for a technique
count, `coverage at 8 stalls` for a figure with no run. **The instrument was sound in two of the three
cases.** What failed was the sentence, and a sentence is not checked by anything.
