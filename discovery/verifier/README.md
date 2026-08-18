# What the verifier rejects, over real generator output

Run date: 2026-08-17. Script: `rejection_rates.py`. 60 gated directions at the decided caps, five per
decade, erased at five chain targets — **298 puzzles**.

## Every layer is silent on real output, and that is worth stating carefully

| | Result |
|---|---|
| Accepted by all four layers | **298 of 298 (100%)** |
| Rejected by any layer | 0 |
| Layer 4 catching what layers 1–3 passed | **none** |

Each layer was asked separately rather than only the first to object, because *a layer that never
fires cannot be told apart from a layer that is never reached*. All five — including the signature
check — fired zero times on this sample.

**That is the expected result and it is not reassuring on its own.** The generator stops erasing at
the same publication rule layer 3 enforces, so the two agree by construction; a batch where they
disagreed would mean one of them was broken. What it does mean is that **on real traffic the layers
are exercised only by the deliberately broken boards in the test suite**, and their value is
insurance rather than day-to-day filtering.

The one number that would change this is layer 4 catching something the others missed. It has not
happened yet. If it ever does it belongs in §22 as loudly as the run can print it.

## The finding: layer 3 is a machine's derivability, not a person's

Layer 3 runs interval propagation to a fixed point across every relation at once. A narrowing found
in the pitching column is instantly available to a row identity twelve rows up. **Nobody solves like
that**, so a board can pass layer 3 and still be underivable by hand.

Layer 3b is the other end of the bracket: one relation in view at a time, never carrying a narrowed
range from one relation to the next. An equality with a single unknown is a subtraction; a single
relation read against non-negativity is the bounding step §4 describes, done the way a person does it
rather than to a fixed point.

| Chain target | Published boards | Also derivable one relation at a time |
|---:|---:|---:|
| 5 | 60 | **100%** |
| 7 | 60 | 98% |
| 9 | 60 | 93% |
| 11 | 60 | 80% |
| **13 — Saturday** | 58 | **71%** |
| overall | 298 | 89% |

**The gap is real and concentrates exactly where the week peaks.** A person is somewhere between the
two solvers, so the honest statement is that at Saturday's target the derivability of 29% of boards
is *unknown* rather than absent.

The earlier search that found no unique-but-underivable board — 24,000 erasures over 400 boards —
was measured with the strong solver, and this is why it proved less than it looked: it says
uniqueness implies derivability *at that bounding strength*, which is a fact about the propagator.

**Whether 3b becomes a gate is not decided.** For: 29% is inside the 30% discard §22 already calls
free. Against: the weak solver is a caricature in the other direction, and gating on it would discard
boards a player would solve comfortably.

## The adapter lives here, on purpose

The verifier shares no code with the generator, so something has to turn generator output into the
package format — the generator names a cell `batting[0].hits`, the verifier calls it `bat[0].hits`,
and the format names nothing at all and stores arrays. That translation is in this script and in
neither package, which is the only place the two vocabularies are allowed to meet.
