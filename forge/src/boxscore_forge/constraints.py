"""The identities restated as a linear system over named cells.

The solver reasons about equations, not about batting rows. Writing the techniques directly against
the board's shape would mean rewriting them for every rule; over a linear system, "an equation with
one unknown" is one implementation.

Every equation carries the identity it came from, and through it the family. That is what lets the
solver withhold the global identity until propagation has stalled, and what lets a solved puzzle
report which kinds of reasoning it actually demanded.

Equations depend on the board's *shape* and never on its values. A cell being erased must not erase
a constraint along with it.

There is no 2x2 rule anywhere here, and none is missing. Every identity in this system is a sum over
a row or over a column, so two of them meet at most at the single cell where one row crosses one
column — never at the two a 2x2 needs. Reaching that rung would take a different family of
constraint, not a different column set.
"""

import functools
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass

from boxscore_forge.boxscore import Direction
from boxscore_forge.identities import (
    BATTING_COLUMNS,
    CROSS_TEAM_COLUMNS,
    FAMILY_OF,
    FOOTNOTE_COLUMNS,
    LINE_SCORE_FIELDS,
    PITCHING_COLUMNS,
    TEAM_FOOTNOTE_FIELDS,
    Family,
    Identity,
)

# The one identity a solver must not be allowed to use early. It is the technique a player reaches
# for only when nothing else moves, so admitting it to the general pool would misreport difficulty.
GLOBAL_IDENTITY = Identity.GLOBAL_PLATE_APPEARANCES


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
class Inequality:
    """`sum(coefficient * cell) >= 0`, tagged with where it came from."""

    terms: tuple[Term, ...]
    origin: Identity


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


def footnote_cell(index: int, column: str) -> str:
    return f"footnotes[{index}].{column}"


def footnote_total_cell(column: str) -> str:
    return f"footnote_totals.{column}"


def pitching_cell(index: int, column: str) -> str:
    return f"pitching[{index}].{column}"


def pitching_total_cell(column: str) -> str:
    return f"pitching_totals.{column}"


def team_footnote_cell(field: str) -> str:
    return f"team_footnotes.{field}"


def line_score_cell(field: str) -> str:
    return f"line_score.{field}"


def inning_cell(side: str, index: int) -> str:
    return f"line_score.{side}_by_inning[{index}]"


def cell_values(direction: Direction) -> dict[str, int]:
    """Every cell on the board with its value, keyed the same way the equations name them."""
    values: dict[str, int] = {}
    values.update(
        _row_values(direction.batting, direction.batting_totals, BATTING_COLUMNS, batting_cell, batting_total_cell)
    )
    values.update(
        _row_values(
            direction.batter_footnotes,
            direction.footnote_totals,
            FOOTNOTE_COLUMNS,
            footnote_cell,
            footnote_total_cell,
        )
    )
    values.update(
        _row_values(direction.pitching, direction.pitching_totals, PITCHING_COLUMNS, pitching_cell, pitching_total_cell)
    )
    for field in TEAM_FOOTNOTE_FIELDS:
        values[team_footnote_cell(field)] = getattr(direction.team_footnotes, field)
    for field in LINE_SCORE_FIELDS:
        values[line_score_cell(field)] = getattr(direction.line_score, field)
    for side, innings in (
        ("offense", direction.line_score.offense_by_inning),
        ("defense", direction.line_score.defense_by_inning),
    ):
        for index, runs in enumerate(innings):
            values[inning_cell(side, index)] = runs
    return values


def _row_values(
    rows: tuple[object, ...],
    totals: object,
    columns: tuple[str, ...],
    cell_of: Callable[[int, str], str],
    total_of: Callable[[str], str],
) -> dict[str, int]:
    """One block of the board — its rows and their totals — read into cell names."""
    values = {cell_of(index, column): getattr(row, column) for index, row in enumerate(rows) for column in columns}
    values.update({total_of(column): getattr(totals, column) for column in columns})
    return values


def all_cells(shape: BoardShape) -> frozenset[str]:
    """Every cell a board of this shape has, named without needing any of its values."""
    return frozenset(
        [
            *(batting_cell(index, column) for index in range(shape.batter_count) for column in BATTING_COLUMNS),
            *(batting_total_cell(column) for column in BATTING_COLUMNS),
            *(footnote_cell(index, column) for index in range(shape.batter_count) for column in FOOTNOTE_COLUMNS),
            *(footnote_total_cell(column) for column in FOOTNOTE_COLUMNS),
            *(pitching_cell(index, column) for index in range(shape.pitcher_count) for column in PITCHING_COLUMNS),
            *(pitching_total_cell(column) for column in PITCHING_COLUMNS),
            *(team_footnote_cell(field) for field in TEAM_FOOTNOTE_FIELDS),
            *(line_score_cell(field) for field in LINE_SCORE_FIELDS),
            *(inning_cell("offense", index) for index in range(shape.offense_innings)),
            *(inning_cell("defense", index) for index in range(shape.defense_innings)),
        ]
    )


@functools.cache
def equations(shape: BoardShape) -> tuple[Equation, ...]:
    """The full equality system for a board of this shape.

    Cached because the solver rebuilds the system on every pass and there are only a handful of
    distinct board shapes in a whole run. Safe to cache: the result is a function of the shape
    alone, which is the same reason erasing a cell cannot erase a constraint.
    """
    return (
        *_column_sum_equations(shape),
        *_cross_team_equations(),
        *_row_identity_equations(shape),
        *_line_score_equations(shape),
        _global_identity_equation(),
    )


def _column_sum_equations(shape: BoardShape) -> Iterator[Equation]:
    for columns, cell_of, total_of, count, identity in (
        (BATTING_COLUMNS, batting_cell, batting_total_cell, shape.batter_count, Identity.BATTING_COLUMN_SUM),
        (FOOTNOTE_COLUMNS, footnote_cell, footnote_total_cell, shape.batter_count, Identity.FOOTNOTE_COLUMN_SUM),
        (PITCHING_COLUMNS, pitching_cell, pitching_total_cell, shape.pitcher_count, Identity.PITCHING_COLUMN_SUM),
    ):
        for column in columns:
            terms = tuple(Term(cell_of(index, column), 1) for index in range(count))
            yield Equation((*terms, Term(total_of(column), -1)), 0, identity)


def _cross_team_equations() -> Iterator[Equation]:
    for column in CROSS_TEAM_COLUMNS:
        yield Equation(
            (Term(batting_total_cell(column), 1), Term(pitching_total_cell(column), -1)),
            0,
            Identity.CROSS_TEAM_TOTAL,
        )


def _row_identity_equations(shape: BoardShape) -> Iterator[Equation]:
    """`PA = AB + BB + HBP + SF + SH + XI`, once per batter and once for the totals row.

    This is what gives an individual cell a second equation to live in. Without it at-bats and walks
    appear only in their column sums, no cycle exists anywhere in the board, and the only puzzles
    that survive validation are rows of unconnected subtractions.
    """
    for index in range(shape.batter_count):
        yield Equation(
            (
                Term(batting_cell(index, "plate_appearances"), 1),
                Term(batting_cell(index, "at_bats"), -1),
                Term(batting_cell(index, "walks"), -1),
                *(Term(footnote_cell(index, column), -1) for column in FOOTNOTE_COLUMNS),
            ),
            0,
            Identity.ROW_PLATE_APPEARANCES,
        )
    yield Equation(
        (
            Term(batting_total_cell("plate_appearances"), 1),
            Term(batting_total_cell("at_bats"), -1),
            Term(batting_total_cell("walks"), -1),
            *(Term(footnote_total_cell(column), -1) for column in FOOTNOTE_COLUMNS),
        ),
        0,
        Identity.ROW_PLATE_APPEARANCES,
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


def _global_identity_equation() -> Equation:
    """Counting the team's plate appearances backward, from outs, runs and runners left on base."""
    return Equation(
        (
            Term(batting_total_cell("plate_appearances"), 1),
            Term(pitching_total_cell("outs"), -1),
            Term(batting_total_cell("runs"), -1),
            Term(team_footnote_cell("left_on_base"), -1),
        ),
        0,
        GLOBAL_IDENTITY,
    )


@functools.cache
def inequalities(shape: BoardShape) -> tuple[Inequality, ...]:
    """The bounds a player can reason with. Nothing here computes a value; they only rule some out."""
    return (*_non_negativity(shape), *_batting_bounds(shape), *_pitching_bounds(shape))


def _non_negativity(shape: BoardShape) -> Iterator[Inequality]:
    for cell in sorted(all_cells(shape)):
        yield Inequality((Term(cell, 1),), Identity.NON_NEGATIVE)


def _batting_bounds(shape: BoardShape) -> Iterator[Inequality]:
    """A batter cannot have more hits than at-bats, nor more at-bats and walks than trips to the plate.

    The second one is available wherever the footnote terms are not, and it narrows from the
    opposite side to the row identity: the identity says what plate appearances add up to, this says
    what they cannot fall below.
    """
    for index in range(shape.batter_count):
        yield Inequality(
            (Term(batting_cell(index, "at_bats"), 1), Term(batting_cell(index, "hits"), -1)),
            Identity.HITS_WITHIN_AT_BATS,
        )
        yield Inequality(
            (
                Term(batting_cell(index, "plate_appearances"), 1),
                Term(batting_cell(index, "at_bats"), -1),
                Term(batting_cell(index, "walks"), -1),
            ),
            Identity.PLATE_APPEARANCES_COVER_AT_BATS_AND_WALKS,
        )
    yield Inequality(
        (Term(batting_total_cell("at_bats"), 1), Term(batting_total_cell("hits"), -1)),
        Identity.HITS_WITHIN_AT_BATS,
    )
    yield Inequality(
        (
            Term(batting_total_cell("plate_appearances"), 1),
            Term(batting_total_cell("at_bats"), -1),
            Term(batting_total_cell("walks"), -1),
        ),
        Identity.PLATE_APPEARANCES_COVER_AT_BATS_AND_WALKS,
    )


def _pitching_bounds(shape: BoardShape) -> Iterator[Inequality]:
    """No more of a pitcher's runs can be earned than he gave up."""
    for index in range(shape.pitcher_count):
        yield Inequality(
            (Term(pitching_cell(index, "runs"), 1), Term(pitching_cell(index, "earned_runs"), -1)),
            Identity.EARNED_RUNS_WITHIN_RUNS,
        )
    yield Inequality(
        (Term(pitching_total_cell("runs"), 1), Term(pitching_total_cell("earned_runs"), -1)),
        Identity.EARNED_RUNS_WITHIN_RUNS,
    )


def constrained_cells(shape: BoardShape) -> frozenset[str]:
    """Cells that appear in at least one equation, and so can be deduced when they are missing.

    The rest — the error columns, and the defending team's hit total — are printed and never
    reasoned about. Erasing one of those would produce a puzzle with no answer.
    """
    return frozenset(term.cell for equation in equations(shape) for term in equation.terms)


def independent_cycles(shape: BoardShape) -> int:
    """How tangled the constraint graph is, counted on the bipartite cell/equation graph.

    Zero means a forest, and a forest is what caps a board at trivial puzzles: with every cell in
    exactly one equation, one blank is a subtraction and two blanks in the same equation are
    ambiguous rather than hard, so validation throws them away and the generator has nowhere to go.
    This is the number that has to stay above zero, not the overlap between equations — that can
    never exceed one, because every identity here is a sum over a row or a column.
    """
    system = equations(shape)
    cells = {term.cell for equation in system for term in equation.terms}
    parent: dict[str, str] = {**{cell: cell for cell in cells}, **{f"#{i}": f"#{i}" for i in range(len(system))}}

    def root(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for index, equation in enumerate(system):
        for term in equation.terms:
            left, right = root(term.cell), root(f"#{index}")
            if left != right:
                parent[left] = right

    edges = sum(len(equation.terms) for equation in system)
    nodes = len(cells) + len(system)
    components = len({root(node) for node in parent})
    return edges - nodes + components


def cells_in_family(shape: BoardShape, family: Family) -> frozenset[str]:
    """Which cells a given kind of reasoning can reach at all."""
    return frozenset(
        term.cell
        for equation in equations(shape)
        if FAMILY_OF.get(equation.origin) == family
        for term in equation.terms
    )
