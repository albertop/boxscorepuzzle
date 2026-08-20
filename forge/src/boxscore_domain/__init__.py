"""Decided values for the puzzle domain — what a board may contain and what the pool must satisfy.

**Configuration, not a bag of numbers.** Every value here carries the reason it holds that value and,
where one exists, the measurement that set it. A file of twenty bare numbers is a file where nobody
knows which are safe to touch, and this project has already shipped one rule that outlived its
justification because the justification was written in a commit message and the number was written in
twenty-five call sites.

⚠️ **`PROVISIONAL` marks the ones that were chosen rather than measured.** Presenting a measured cap and
an eyeballed threshold in the same typeface hides the difference, and a threshold set by eye that
rejects real data gets loosened until it says nothing.

⚠️ **Nothing about screens is in here, and nothing here is in `serve/`.** §33 keeps the forge ignorant
of presentation and the service ignorant of generation; a single shared constants module imported by
both sides for the convenience of one is the first thing that would break it. The presentation
constants live in `serve/ui/phone/tokens.css` and the two files never import each other.

⚠️ **These may not be spelled as literals anywhere else.** `forge/tests/test_constants_are_not_copied.py`
walks the source trees and fails on a re-introduced literal, because one definition was not enough on
its own the last time: nothing stopped the copies from existing, and they came back.
"""

from typing import Final

PROVISIONAL = "PROVISIONAL"
"""The word every unmeasured value is marked with, so `grep PROVISIONAL` lists what is still soft.

⚠️ Spelled into the docstrings rather than interpolated into them. An f-string after an assignment is
a discarded expression, not an attributed docstring — it renders as documentation to a reader and no
tool ever sees it, which is the same shape as a check that looks like a check.
"""

# ---------------------------------------------------------------------------------------------------
# Roster caps — what fits on a board and what the pool filter admits (§5, §6)
# ---------------------------------------------------------------------------------------------------

BATTER_CAP: Final = 13
"""The offensive team's batting rows. **Measured.**

Raised from 10 when the browser prototype's working-set measurement showed that rows on screen do not
bind: with the active section's totals pinned they never scroll away, and 70% of steps touch rows
within a five-row window. The cap costs pool, not screen.
"""

PITCHER_CAP: Final = 6
"""The defensive team's pitching rows. **Measured. Raised from 4, and the 4 was wrong twice over.**

At ≤6 against ≤4:

  coverage at 8 stalls          22% -> 33%
  pitching share of stalls      34% -> 45%
  directions in the pool        +41%, and the 1990s and 2000s become reachable
  global identity required      55% -> 70%
  cross-team identity required  88% -> 80%
  median ceiling                5, unchanged

The extra rows are not filler: the pitching section participates more than proportionally, which is the
mechanism rather than an inference from the coverage number.

⚠️ **The ≤4 decision rested on a measurement the zero-fill correction invalidated.** Stalls then counted
the solver deducing footnote terms worth zero, and **a pitching row carries no footnote terms at all**,
so pitcher-heavy boards had fewer zeros inflating their scores. The comparison was biased against
exactly the boards it was judging, and no number in its output could have revealed that — it is the
confound that has no signature in the results.

⚠️ **And the screen argument was wrong twice.** It was retired for the batter cap by the working-set
finding above, then left standing for pitchers because nobody re-derived it there — a justification
reused rather than re-derived in the new place. The board already scrolls; a row of screen was never
the cost it was said to be.
"""

MIN_BATTERS: Final = 9
"""Nine men bat. A board with fewer is missing rows, whatever its arithmetic says."""

# ---------------------------------------------------------------------------------------------------
# Pool quality (§5)
# ---------------------------------------------------------------------------------------------------

ZERO_DENSITY_GATE: Final = 0.30
"""Maximum share of the board's cells that are zero, above which the direction is discarded. **Measured.**

It removes every shutout and the three-run games while keeping seven-run ones. Chosen over ranking on
compressibility, which correlates +0.79 with zero density and therefore selects boredom: compressibility
says how much can be removed, not whether what remains is worth solving.
"""

MAX_PLATE_APPEARANCES_PER_OUT: Final = 2.2
"""Plausibility ceiling on how much a lineup can bat per out recorded. **Measured, with headroom.**

Over 480 directions: median 1.54, p90 1.74, p99 1.96, maximum 2.12. A first version guessed 1.9 and
flagged 1.9% of perfectly real games — a check that rejects real boxscores gets loosened until it says
nothing, so the number comes from the distribution rather than from judgement.
"""

# ---------------------------------------------------------------------------------------------------
# Difficulty (§31)
# ---------------------------------------------------------------------------------------------------

MEDIAN_STALL_CEILING: Final = 5
"""What the median board in the pool can reach. **Measured, and unchanged by the pitcher cap change.**

The cap moved how much of the pool reaches the top rung comfortably; it did not move the range. A
6-stall board went from the top third of the pool to about half of it.
"""

STALL_TARGETS: Final = (1, 2, 3, 4, 5, 7)
"""The rungs the reference packages are generated at. **PROVISIONAL.**

⚠️ These are a format sample, not the ladder. The ladder's rungs depend on what the five-board pack
says about whether the corrected scale corresponds to felt difficulty, and **nothing is labelled easy,
medium or hard until it comes back**. Five stalls was an example the operator gave, not a standard.
"""

ERA_QUOTA: Final = 1
"""Minimum boards from each decade a hand-solve pack must contain. **PROVISIONAL.**

Stratification exists because the pool is not spread evenly across eras and a sample landing in one
decade describes that decade's roster habits rather than the board. The specific quota was chosen.
"""

# ---------------------------------------------------------------------------------------------------
# Operations (§33)
# ---------------------------------------------------------------------------------------------------

FORWARD_INVENTORY_MONTHS: Final = 5
"""Months of published puzzles the VPS holds at all times. **PROVISIONAL.**

Set against the laptop being a single point of failure: the inventory is the buffer between a dead
generator and a dead product.
"""

INVENTORY_ALERT_MONTHS: Final = 3
"""Alert below this. **PROVISIONAL.** Two months of slack to notice and rebuild."""

# ---------------------------------------------------------------------------------------------------
# Batting-order constraint — experimental, not adopted (docs/reviews/batting-order-reversal.md)
# ---------------------------------------------------------------------------------------------------

LINEUP_DIVISION_SHARE_CAP: Final = 0.20
"""Discard a fallback board with more than this many division steps per unit of chain length.
**PROVISIONAL, and its unit is provisional too.**

⚠⚠ **v27-P2-13: the number was read off `chain_length` and the code divided by the deduction
count.** Those are not the same quantity — `chain_length` is the longest run of steps each waiting on
the one before, a depth; the deduction count is every cell recovered. On one specimen they are 20 and
37. A cap derived as 9/24 = 38% was being applied to 9/37 = 24%, so **the two boards this cap exists
to discard would have passed it.** A provisional threshold may be soft; its unit may not.

⚠️ **It is a ratio, not a share.** The numerator counts steps and the denominator is a depth, so it
is not bounded by 1. The name is kept because the constant may not be spelled twice and renaming it is
a change to make when the unit is settled, not while it is in doubt — but `division_against_chain()`
carries the accurate name at the call site.

A `batting_order` step reads the team's plate-appearance total, divides by nine, and writes the result
down. It costs nothing to find and combines no terms: on one measured board, eight consecutive cells
were filled `5 5 5 5 5 5 5 4` from a total of 44. **The player experiences that as typing**, which is
the same thing the footnote cells turned out to be, and the metric counting those steps is measuring
the board rather than the game.

⚠️⚠️ **This number came from looking at two boards. It is not a measurement and must not be cited as
one.** Of the eleven directions that reach eight stalls only with the constraint on, nine carry no
division at all and two carry 38% and 35% of their chain as division. The cap is set to separate those
two groups and nothing more; it was not fitted, and no board was tested near the boundary. The gap
between 2% and 35% is wide enough that any threshold in it would do the same job on this sample, which
is exactly why the sample cannot justify 0.20 over 0.25.

⚠️ **§31 forbids inventing numeric parameters that shape the product.** This one shapes which boards
enter the pool, so it stays `PROVISIONAL` until the pre-registered confirmation run measures where the
distribution actually splits — or until the hand-solve pack closes the question above it, in which case
this constant is deleted rather than measured.
"""

# ---------------------------------------------------------------------------------------------------
# The line score's width (§2, §6)
# ---------------------------------------------------------------------------------------------------

MAX_INNINGS: Final = 14
"""The longest game the board can draw. **Measured in the browser, on the real page, with the real renderer.**

⚠️ **This is the one place the screen genuinely decides.** The grid's column budget was argued from
width twice and retired twice, because the board scrolls and the totals stay pinned — width was never
the real limit there. Here it is: **the line score is one piece and cannot be split**, and §6 makes it
the puzzle's anchor, consulted constantly. An anchor that has to be scrolled stops being one.

**What was measured.** The tightest cell in the table at every inning count, at 375px and 320px —
where "tightest" is the whitespace left around the glyph once the fixed layout has divided the width.
The binding cell is **not** an inning header: it is a **two-digit R or H in the body**, which is
ordinary in a long game. The gap between two numbers is that slack, and below about 3px they stop
reading as two numbers — `11 16 2` becomes `1116 2`.

| innings | 375px @ 13px | 320px @ 11px |
|---|---|---|
| 9 | 11.6px | 9.1px |
| 12 | 6.4px | 4.9px |
| 13 | 5.2px | 3.9px |
| **14** | **4.0px** | **2.9px** |
| 15 | 3.0px | 2.1px — merged |
| 16 | 2.1px — merged | — |

**Where the line was drawn, and it is a judgement rather than an arithmetic result.** Fourteen was read
off rendered boards, not off the table: at 320px its header row is tight but every pair separates,
while **at fifteen the row reads as one run of digits** and the R/H block closes up. Fourteen is the
largest count that works at *both* widths, so it is the cap. At 375px fifteen would still be readable;
the smallest device decides, because it is the same puzzle.

⚠⚠ **Three separate ways the instrument disagreed with the product, none visible in its output.**
Every one produced boards that looked like boards and numbers that looked like numbers.

1. The page carried `padding: 16px` on its body, so a 320px "device" held 288px of content.
2. It set `font-family: system-ui` on `body` — and `board.css` puts the product's face on `html, body`,
   so **every board was drawn in the wrong typeface.** IBM Plex Sans Condensed is narrower; the gaps
   came out about a pixel tight and the boards rendered for judgement were not the boards. The page
   also never linked `fonts.css`. The neighbouring instrument, `footnote-height.html`, had both right,
   which is how the difference was found.
3. Its captions were computed synchronously, before the webfont arrived, so the printed figure was
   stale beside a correct board — **the page disagreeing with itself**, which is worse than either
   error alone because nothing says which half to believe.

The figures above are from the corrected page and agree with the running application, measured
independently. **An earlier draft of this constant said 13 on the strength of the broken page.**

⚠️ **Neither the side column nor the R/H/E block can pay for a fifteenth inning.** The side column is
52px and holds `AWAY`, which is 39.5px at 13px plus 8px of padding — 44px already clips it, so
narrowing needs a different label and that is a separate decision.

The R/H/E block was measured as a variant of the real renderer rather than argued about. Giving it
less than an inning's width **moves the problem instead of solving it**: at 320px and 14 innings the
block goes from 2.9px to 7.1px while the inning headers fall from 2.9px to 2.4px. And it cannot be
taken from `E` alone — errors reach **11**, in 7 sides across the whole 1910-2029 window, so a
one-digit column would silently clip a real board. `R` and `H` genuinely need two digits: hits reach
33. **The block is already at its minimum.**

**What the pool loses, as context and not as justification** — the cap is set by the screen and these
figures did not move it. Of 200,452 gated directions, games of **15 or more are 232, or 0.12%**. The
whole 11-to-14 band is under 1%. For scale, capping at 9 would cost 6.26%.

⚠️ **A twelve-inning game is not an edge case to be justified — it is baseball**, and §2 commits to the
canonical format. A board that only ever showed nine innings would teach the player to expect nine.
"""
