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
# Which games the pool may draw from (§32)
# ---------------------------------------------------------------------------------------------------

POSTSEASON_SEASON_FLOOR: Final = 1969
"""Earliest postseason season the pool admits. **Measured, and it arrives from two directions.**

The postseason is a second source of boards. It needs a floor because the pool's source rule (§32)
excludes deduced reconstructions and Negro Leagues games, and the regular season establishes that per
game through `dbo.retroGameProvenance`. **No such table exists for the postseason and none is needed**
— all 121 `events-post` zips hold 403 files and every one is `.EVE`: 1,878 games, not one deduced, no
league letter. There is nothing there to exclude.

So the floor is not doing the work the provenance table does. It is protection against Retrosheet
publishing something later that would need excluding — a Negro Leagues postseason, a reconstruction —
and it is set where two independent facts meet:

  the first LCS is 1969        before it the postseason was the World Series alone, and a
                               multi-round postseason is what makes a modern one
  the last deduced game is 1968  across the whole database, regular season included

Neither was derived from the other: one is about how baseball was organised, the other about how
Retrosheet reconstructed missing scoresheets. Divisional play begins and the mound is lowered the same
year, so the line is explicable to a player as well.

⚠️ **A floor is a weaker guarantee than the provenance table, and the difference is the reason this
docstring exists.** The table asserts *this game came from a scored file*. A floor asserts *no game in
this era came from one that was not*, which is a claim about Retrosheet's future behaviour rather than
about a row. `discovery/retrosheet-coverage/check_postseason_sources.ps1` is what re-establishes it
against a new download; without that it is an assumption that ages silently.

**What it admits:** 572 directions — LCS 233, DVS 179, WS 141, WCG 19 — against the regular season's
102,228. ⚠️ **The postseason is not a pool argument at 0.6%**, and it was not adopted as one: postseason
boards survive §5's gate *worse* than regular boards of the same decade (14.1% against 23.2% in the
2010s), because October means deeper bullpens and less scoring. It is here for §7's reveal, where a
board resolving to a World Series game is a different payoff from a Tuesday in June.

**⚠️ The regular season is untouched by this.** It keeps every game it has, back to 1910, and keeps the
provenance table that admits them. The floor applies to the postseason and nowhere else — a change
here must never become a change to what the pool already contains.

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
# Batting-order constraint — ADOPTED (docs/reviews/batting-order-plan.md; history in -reversal.md)
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

MAX_INNINGS: Final = 12
"""The longest game the board will draw. **Decided by the operator, inside a measured width limit.**

⚠️ **This is the one place the screen genuinely decides.** The grid's column budget was argued from
width twice and retired twice, because the board scrolls and the totals stay pinned. Here it binds:
the line score is one piece and cannot be split, and §6 makes it the anchor the player consults
constantly. An anchor that must be scrolled stops being one.

**What binds, measured in the browser with the real renderer and the real typeface.** Not the inning
headers — **a two-digit R or H in the body**, which is ordinary in a long game. The figure is the
whitespace left around the glyph once the fixed layout divides the width; that gap is what separates
two numbers, and below about 3px `11 16 2` reads as `1116 2`.

| innings | 375px @ 13px | 320px @ 11px |
|---|---|---|
| 9 | 11.6px | 9.1px |
| 11 | 7.6px | 6.1px |
| **12** | **6.4px** | **4.9px** |
| 13 | 5.2px | 3.9px |
| 14 | 4.0px | 2.9px |
| 15 | 3.0px | 2.1px — merged |

**14 was the width limit; 12 is the cap.** Twelve sits well inside it rather than at its edge, which is
the point of choosing it: a twelve-inning game is baseball rather than an edge case (§2 commits to the
canonical format), and a board that only ever showed nine would teach the player to expect nine.

⚠⚠ **The half-inning marker does NOT bind, and the record says so because the opposite was proposed.**
The `x` matters — it says the home side did not bat, which makes their outs 24 rather than 27 and feeds
the global identity, so a marker the player cannot read is a **lost given, not a cosmetic flaw**. But it
is not width that threatens it: the glyph is **5.1px in a 14.8px column even at 14 innings on 320px**,
a 9.8px margin against the digits' 2.9px. **It is the roomiest character on the board.** Anyone
measuring digit widths later would be right, and a note here claiming otherwise would be the wrong
answer preserved in the one place meant to prevent that.

⚠️ **What does threaten the marker is contrast, and the cap does not fix it.** `.unplayed` renders at
**2.21:1** against the scoreboard ground against a played digit's 4.51:1 — below WCAG's 3.0 floor for
any content, at every inning count including nine. That is recorded as its own defect; it is not a
reason for this number.

⚠️ **The R/H/E block cannot pay for width either.** Narrowing it moves the problem rather than solving
it, and at 13px there is nowhere to move it from: `R` and `H` need two digits (hits reach 33) and so
does `E` in 7 sides across the window (errors reach 11), so a one-digit column would silently clip a
real board. The block is already at its minimum.

**What the pool loses, as context and not as justification** — the cap is set on screen and this figure
did not move it. Of 200,452 gated directions, games of 13 or more are **1,776, or 0.89%**. The whole
11-to-14 band is under 1%. For scale, capping at 9 would cost 6.26%.
"""
