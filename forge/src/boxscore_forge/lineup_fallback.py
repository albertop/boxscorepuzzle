"""The batting-order constraint as a fallback, tried only when a board cannot reach its target.

✅ **ADOPTED. This is the production erasure path.** `write_reference_puzzles.py` builds through it
and the boards it produces publish.

⚠⚠ **This said `EXPERIMENTAL. NOT ADOPTED. NOTHING HERE MAY REACH PUBLICATION` for one commit
after production started calling it** — v29-P3-01. The caller said extend this path and the module
said restore the fence, so **a later correction could have undone the adoption while honestly
following the repository.** A module contract is not archived prose: it is the instruction anyone
reads before touching the file. The history is dated in `batting-order-reversal.md`; the current
statement lives here, and there is one of it.

`docs/reviews/batting-order-reversal.md` records what is and is not established — a recommendation
given, reversed under one push, and overstated in both directions. Read it before citing any number
from this module, and note that **every figure in it was measured before the verifier could certify
these boards.**

**Why a fallback rather than a switch.** On the 46 walks that already reach eight stalls without the
constraint, turning it on changes stalls on four of them and converts a median of eight steps into
division filler — a `batting_order` step reads the team total, divides by nine, and writes the answer
down. On the eleven directions that reach eight stalls *only* with it on, nine carry no division at
all. **So the constraint is worth something exactly where the board cannot get there without it, and
costs something everywhere else.** Trying the ordinary path first is what separates the two.

**What the verifier can do, which is what made adoption possible.** `lineup_values()` in
`boxscore_verify/reason.py` is the independent, value-producing step §22 requires, and **every layer
that can speak about the batting order reads it** — identities, uniqueness, derivability, the weak
solver and end-to-end. Layers 2 and 4 did not for one commit, which meant a board unique *because of*
the batting order was refused as ambiguous before layer 3 ever ran: adoption that was true in the
imports and false in the outcome. `test_lineup_fallback_is_adopted.py` takes a real fallback board
through the publication gate, and reverting layer 2 makes it fail with `MULTIPLE_SOLUTIONS`.

✅ **The pre-registered confirmation ran on 2026-08-20 and all three criteria held.**
`discovery/batting-order/confirm.py`, 48 directions by 3 seeds by 5 targets by 3 arms, every board through
the publication gate rather than through the arithmetic layers alone. Coverage at 8 stalls went 29/48
to 39/48; arm A lost 34 directions in total, which is the proof that a loss can be expressed at all;
division filler on the gained cohort was 0.6%. The figures and their caveats are in
`docs/reviews/batting-order-plan.md`.

⚠️ **What this module does NOT establish, after the confirmation.**

- **The filler figure is not a causal one.** The denominator is every non-division deduction in the
  solve, not deductions the constraint enabled — it was labelled `causal` and that asserted the thing
  the adoption question turns on. The share is a real measure of *filler* and it is what the criterion
  asked for; it is not evidence that the rest of the solve used the cyclic order. A causal figure needs
  a counterfactual solve, which is not run and not scheduled. v30-P1-01.
- **n = 11 is what the *original* subgroup rested on**, and that subgroup was not pre-registered. The
  confirmation was, which is what makes the result usable — the pre-confirmation caveat is preserved
  in `batting-order-reversal.md`, where it remains true of the run it describes.
- **That eight stalls corresponds to felt difficulty.** Nothing here measures a person. The one human
  verdict on record is the operator's, in `batting-order-reversal.md`, and it is about the constraint
  making boards harder to hold in the head rather than about any stall count.
- **The filler ratio's unit is itself provisional.** See `division_against_chain`.

⚠⚠ **The bullet above about the verifier sat inside this list for a commit** — a positive claim filed
under *does not establish*, because its text was replaced without checking the heading it lived under.
v29-P3-01. **A list is a claim about every item in it**, and editing one item is editing that claim.
"""

from boxscore_domain import LINEUP_DIVISION_SHARE_CAP
from boxscore_forge.boxscore import Direction
from boxscore_forge.erasure import DEFAULT_ORDERING, Puzzle, erase
from boxscore_forge.solver import Technique


def division_against_chain(puzzle: Puzzle) -> float:
    """Division steps per unit of chain length — **the ratio the cap was actually measured with**.

    ⚠️⚠️ **v27-P2-13: this divided by `len(deductions)` and the threshold came from `chain_length`.**
    They are not the same number and not close. `chain_length` is the *longest run of steps each
    waiting on the one before it* — a depth — while `len(deductions)` counts every cell recovered. On
    one specimen they are 20 and 37. So a cap derived as 9/24 = 38% was being applied to 9/37 = 24%,
    and **the two boards the cap exists to discard would have passed it.** A provisional threshold may
    be soft; its unit may not.

    ⚠️ **It is a ratio, not a share, and it is not bounded by 1.** The numerator counts steps and the
    denominator is a depth, so eight lineup steps sharing one depth on a short chain can exceed 1.0.
    That is a real weakness of the unit, not of this implementation — the number `0.20` was read off
    two boards measured this way, and changing the unit here would silently move the threshold.

    **The confirmation ran and did not settle it**: it reported filler against the whole solve, a
    different denominator from this one. So `0.20` against `chain_length` is still the value two boards
    produced and still provisional, as is whether the threshold belongs at 0.20 at all.

    ⚠⚠ **This said "zero on every board the production path produces", and adoption made that false**
    — v29-P3-01. It was true while the constraint was fenced off: `LINEUP_ARITHMETIC` cannot fire
    without a batting order on the shape, and production never put one there. **Now the fallback does,
    on exactly the boards the plain path could not reach**, and this function exists to put a ceiling
    on how much of their chain those steps may be. A sentence claiming the value is always zero, inside
    the function whose whole purpose is to bound a non-zero one, is the contradiction the reviewer
    named.

    What is true now: **zero on every board the *plain* attempt produced**, which is most of them,
    because no batting order reached the shape. Non-zero is possible only on a fallback board, and
    `LINEUP_DIVISION_SHARE_CAP` is what decides how much is too much.

    ⚠️ Both halves of this docstring's correction are the same defect: text that was accurate when
    written and silently false after a decision changed around it. **A statement is not made safe by
    having been checked once.**
    """
    chain = puzzle.solution.chain_length
    if chain == 0:
        # No step waited on another, so there is no chain to be a fraction of. A board with nothing
        # deduced carries no filler either, and 0.0 keeps the caller's comparison meaningful.
        return 0.0
    division = sum(1 for step in puzzle.solution.deductions if step.technique is Technique.LINEUP_ARITHMETIC)
    return division / chain


def erase_with_lineup_fallback(
    direction: Direction,
    slots: tuple[int, ...],
    *,
    target_stalls: int,
    seed: int,
    ordering: str = DEFAULT_ORDERING,
) -> tuple[Puzzle | None, str]:
    """Try without the constraint; fall back to it only if the target was not reached.

    Returns the puzzle and **why it is the puzzle** — `"plain"`, `"fallback"`, `"discarded_filler"` or
    `"unreachable"`. The reason is returned rather than inferred, because a caller that has to work out
    which path produced a board will eventually work it out wrongly, and every measurement comparing
    these boards needs to know which population each one is in.

    ⚠️ **The same seed and the same ordering in both attempts.** The two attempts must differ in
    *treatment* and not in *trajectory*; re-seeding the retry would vary two things at once and the
    report would read exactly as clean as an honest one.
    """
    plain = erase(direction, target_stalls=target_stalls, seed=seed, ordering=ordering)
    if plain is not None:
        # ⚠️ The board never sees the constraint, so it cannot pay the filler cost. This is the branch
        # that takes 46 of 57 directions in the sample, and it is why this is a fallback.
        return plain, "plain"

    fallback = erase(direction, target_stalls=target_stalls, seed=seed, ordering=ordering, slots=slots)
    if fallback is None:
        return None, "unreachable"
    if division_against_chain(fallback) > LINEUP_DIVISION_SHARE_CAP:
        # Discarded, never repaired: §22 throws candidates away rather than relaxing a rule to reach a
        # number, and with thousands of candidates the cost of discarding is nothing.
        return None, "discarded_filler"
    return fallback, "fallback"
