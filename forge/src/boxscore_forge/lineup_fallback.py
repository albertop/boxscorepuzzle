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

⚠️ **What this module does not establish.**

- **n = 11.** The whole case rests on eleven directions out of forty-eight, ten qualifying walks out of
  fifteen, in a subgroup that was **not pre-registered**. A subgroup chosen after seeing the aggregate
  is a known way to manufacture a result, and this one has not survived a confirmation run.
- **The verifier can now replay it.** `lineup_values()` in `boxscore_verify/reason.py` is the
  independent, value-producing step §22 requires, and **all five layers read the lineup**. Layers 2
  and 4 did not for one commit, which meant a board unique *because of* the batting order was
  refused as ambiguous before layer 3 ever ran — adoption that was true in the imports and false in
  the outcome. `test_lineup_fallback_is_adopted.py` now takes a real fallback board through every
  layer, and reverting layer 2 makes it fail with `MULTIPLE_SOLUTIONS`.
- **The filler ratio's unit is itself provisional.** See `division_against_chain`.
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
    two boards measured this way, and changing the unit here would silently move the threshold. **The
    unit is on the list the pre-registered confirmation run has to settle**, together with whether the
    threshold belongs at 0.20 at all.

    Zero on every board the production path produces, because `LINEUP_ARITHMETIC` cannot fire without
    a batting order on the shape.
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
