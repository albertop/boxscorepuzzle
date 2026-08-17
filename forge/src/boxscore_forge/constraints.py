"""The identities restated as a linear system over named cells.

The solver reasons about equations, not about batting rows. Writing the technique ladder directly
against the board's shape would mean rewriting it for every rule; over a linear system, "an equation
with one unknown" and "two equations sharing two unknowns" are one implementation each.

Every equation carries the identity it came from, which is what lets the solver withhold the global
team identity until the lower techniques have stalled. Without that, the solver would crack the
hardest step in the puzzle with the easiest rule and report the puzzle as trivial.

Equations depend on the board's *shape* and never on its values. A cell being erased must not erase
a constraint along with it.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from boxscore_forge.boxscore import Direction
from boxscore_forge.identities import (
    BATTING_COLUMNS,
    CROSS_TEAM_COLUMNS,
    FOOTNOTE_FIELDS,
    LINE_SCORE_FIELDS,
    PITCHING_COLUMNS,
    Identity,
)

# The one identity a solver must not be allowed to use early. It is the technique a player reaches
# for only when nothing else moves, so admitting it to the general pool would misreport difficulty.
GLOBAL_IDENTITY = Identity.PLATE_APPEARANCES


@dataclass(frozen=True, slots=True)
class Term:
    cell: str
    coefficient: int


@dataclass(frozen=True, slots=True)
class Equation:
    """`sum(coefficient * cell) == constant`, tagged with where it came from."""

    terms: tuple[Term, ...]
    constant: int
    origin: Identity

    @property
    def is_global(self) -> bool:
        return self.origin == GLOBAL_IDENTITY

    def residual(self, values: Mapping[str, int]) -> int:
        """How far the equation is from balancing. Zero means satisfied."""
        return sum(term.coefficient * values[term.cell] for term in self.terms) - self.constant

    def unknowns(self, known: Mapping[str, int]) -> tuple[str, ...]:
        return tuple(term.cell for term in self.terms if term.cell not in known)


@dataclass(frozen=True, slots=True)
class BoardShape:
    """Everything the equation system needs to know about a board, and nothing about its values."""

    batter_count: int
    pitcher_count: int
    offense_innings: int
    defense_innings: int


def shape_of(direction: Direction) -> BoardShape:
    return BoardShape(
        batter_count=len(direction.batting),
        pitcher_count=len(direction.pitching),
        offense_innings=len(direction.line_score.offense_by_inning),
        defense_innings=len(direction.line_score.defense_by_inning),
    )


def batting_cell(index: int, column: str) -> str:
    return f"batting[{index}].{column}"


def batting_total_cell(column: str) -> str:
    return f"batting_totals.{column}"


def pitching_cell(index: int, column: str) -> str:
    return f"pitching[{index}].{column}"


def pitching_total_cell(column: str) -> str:
    return f"pitching_totals.{column}"


def footnote_cell(field: str) -> str:
    return f"footnotes.{field}"


def line_score_cell(field: str) -> str:
    return f"line_score.{field}"


def inning_cell(side: str, index: int) -> str:
    return f"line_score.{side}_by_inning[{index}]"


def cell_values(direction: Direction) -> dict[str, int]:
    """Every cell on the board with its value, keyed the same way the equations name them."""
    values: dict[str, int] = {}
    for index, line in enumerate(direction.batting):
        for column in BATTING_COLUMNS:
            values[batting_cell(index, column)] = getattr(line, column)
    for column in BATTING_COLUMNS:
        values[batting_total_cell(column)] = getattr(direction.batting_totals, column)
    for index, pitching_line in enumerate(direction.pitching):
        for column in PITCHING_COLUMNS:
            values[pitching_cell(index, column)] = getattr(pitching_line, column)
    for column in PITCHING_COLUMNS:
        values[pitching_total_cell(column)] = getattr(direction.pitching_totals, column)
    for field in FOOTNOTE_FIELDS:
        values[footnote_cell(field)] = getattr(direction.footnotes, field)
    for field in LINE_SCORE_FIELDS:
        values[line_score_cell(field)] = getattr(direction.line_score, field)
    for side, innings in (
        ("offense", direction.line_score.offense_by_inning),
        ("defense", direction.line_score.defense_by_inning),
    ):
        for index, runs in enumerate(innings):
            values[inning_cell(side, index)] = runs
    return values


def constrained_cells(shape: BoardShape) -> frozenset[str]:
    """Cells that appear in at least one equation, and so can be deduced when they are missing.

    The rest — the error columns, and the defending team's hit total — are printed and never
    reasoned about. Erasing one of those would produce a puzzle with no answer.
    """
    return frozenset(term.cell for equation in equations(shape) for term in equation.terms)


def equations(shape: BoardShape) -> tuple[Equation, ...]:
    """The full equality system for a board of this shape."""
    return (
        *_column_sum_equations(shape),
        *_cross_team_equations(),
        *_line_score_equations(shape),
        _plate_appearance_equation(shape),
    )


def _column_sum_equations(shape: BoardShape) -> Iterator[Equation]:
    for column in BATTING_COLUMNS:
        terms = tuple(Term(batting_cell(index, column), 1) for index in range(shape.batter_count))
        yield Equation((*terms, Term(batting_total_cell(column), -1)), 0, Identity.BATTING_COLUMN_SUM)

    for column in PITCHING_COLUMNS:
        terms = tuple(Term(pitching_cell(index, column), 1) for index in range(shape.pitcher_count))
        yield Equation((*terms, Term(pitching_total_cell(column), -1)), 0, Identity.PITCHING_COLUMN_SUM)


def _cross_team_equations() -> Iterator[Equation]:
    for column in CROSS_TEAM_COLUMNS:
        yield Equation(
            (Term(batting_total_cell(column), 1), Term(pitching_total_cell(column), -1)),
            0,
            Identity.CROSS_TEAM_TOTAL,
        )


def _line_score_equations(shape: BoardShape) -> Iterator[Equation]:
    for side, innings, total in (
        ("offense", shape.offense_innings, "offense_runs"),
        ("defense", shape.defense_innings, "defense_runs"),
    ):
        terms = tuple(Term(inning_cell(side, index), 1) for index in range(innings))
        yield Equation((*terms, Term(line_score_cell(total), -1)), 0, Identity.LINE_SCORE_RUNS)

    yield Equation(
        (Term(line_score_cell("offense_runs"), 1), Term(batting_total_cell("runs"), -1)),
        0,
        Identity.LINE_SCORE_RUNS,
    )
    yield Equation(
        (Term(line_score_cell("offense_hits"), 1), Term(batting_total_cell("hits"), -1)),
        0,
        Identity.LINE_SCORE_HITS,
    )


def _plate_appearance_equation(shape: BoardShape) -> Equation:
    """Counting plate appearances forward from at-bats against counting them backward from outs.

    The `shape` argument is unused because the identity is stated over team totals, which exist
    whatever the roster size. It is taken anyway so every builder here has one signature.
    """
    _ = shape
    forward = (
        Term(batting_total_cell("at_bats"), 1),
        Term(batting_total_cell("walks"), 1),
        Term(footnote_cell("hit_by_pitch"), 1),
        Term(footnote_cell("sacrifice_flies"), 1),
        Term(footnote_cell("sacrifice_hits"), 1),
        Term(footnote_cell("reached_on_interference"), 1),
    )
    backward = (
        Term(pitching_total_cell("outs"), -1),
        Term(batting_total_cell("runs"), -1),
        Term(footnote_cell("left_on_base"), -1),
    )
    return Equation((*forward, *backward), 0, GLOBAL_IDENTITY)
