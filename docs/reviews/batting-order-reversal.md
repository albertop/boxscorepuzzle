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
converts roughly eight steps into division. On boards that could not reach it, nine of eleven reach it
with **no division at all**. The two ATL boards are the failure case and a chain-share filter would
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
