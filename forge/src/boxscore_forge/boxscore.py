"""The board's data model: one direction of a real boxscore.

A direction is one team's offense against the opposing team's pitching. A game yields up to two,
and may qualify as a puzzle in one direction and not the other.

Every quantity is an integer. Innings pitched are stored as outs rather than the printed `x.y`
form: thirds of an inning are not decimals, and floating point in an arithmetic identity produces
puzzles that fail validation for no visible reason.

Containers are frozen because they travel through a validation pipeline, where a mutable value is
action at a distance waiting to happen.

Plate appearances are a column, and that decision is what the whole board hangs on. Without it no
individual cell takes part in a second equation, the constraint graph is a forest, and the only
puzzles that survive validation are rows of independent subtractions. With it, every batter row
carries its own identity and deduction can chain.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BattingLine:
    """One batter's row, or the batting totals row. Six columns, which is the board's width limit."""

    plate_appearances: int
    at_bats: int
    runs: int
    hits: int
    walks: int
    strikeouts: int


@dataclass(frozen=True, slots=True)
class BatterFootnotes:
    """What a printed boxscore prints below the grid, attributed to one batter.

    These are given and never erased, like the line score. They are what makes the row identity
    close: `PA = AB + BB + HBP + SF + SH + CI`.

    They are zero on roughly nine rows in ten, which is a presentation hazard rather than a reason
    to drop them — a player who has seen nothing but zeros will stop looking, and the row where one
    finally appears is exactly the row whose arithmetic fails without it.
    """

    hit_by_pitch: int
    sacrifice_flies: int
    sacrifice_hits: int
    catcher_interference: int


@dataclass(frozen=True, slots=True)
class TeamFootnotes:
    """Footnotes that belong to the team rather than to any batter.

    Runners left on base are counted for the side, not charged to whoever was stranded, and the
    global identity cannot be stated without them.
    """

    left_on_base: int


@dataclass(frozen=True, slots=True)
class PitchingLine:
    """One pitcher's row, or the pitching totals row.

    `outs` is what the board prints as IP. Three outs to an inning; the conversion belongs at the
    presentation edge, not here.
    """

    outs: int
    hits: int
    runs: int
    earned_runs: int
    walks: int
    strikeouts: int


@dataclass(frozen=True, slots=True)
class LineScore:
    """Runs per inning for both teams plus the R/H/E summary. Given complete and never erased.

    The per-inning tuples can differ in length: a home team leading after the top of the ninth does
    not bat, and extra innings lengthen both. Nothing here assumes nine.

    Errors are carried because a line score has an E column, but no identity uses them — Retrosheet
    proofs defensive statistics far less closely, and the board deduces nothing from them.
    """

    offense_by_inning: tuple[int, ...]
    defense_by_inning: tuple[int, ...]
    offense_runs: int
    offense_hits: int
    offense_errors: int
    defense_runs: int
    defense_hits: int
    defense_errors: int


@dataclass(frozen=True, slots=True)
class Direction:
    """One team's offense against the opposing team's pitching: everything the board shows."""

    batting: tuple[BattingLine, ...]
    batting_totals: BattingLine
    batter_footnotes: tuple[BatterFootnotes, ...]
    footnote_totals: BatterFootnotes
    team_footnotes: TeamFootnotes
    pitching: tuple[PitchingLine, ...]
    pitching_totals: PitchingLine
    line_score: LineScore
