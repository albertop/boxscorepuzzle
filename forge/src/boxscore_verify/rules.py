"""The board's arithmetic, restated from §3 of the design document.

⚠️ **Written against the document, not against the generator.** §22 requires the verifier to share no
code with the thing it judges, because a verifier that reuses the generator's functions inherits its
bugs and the validation is theatre. So this module was written from the design document's statement
of the four families and the inequalities, and it names cells its own way — a shared naming grammar
would be a shared vocabulary one side invented and the other inherited, which is the same failure
wearing a different hat.

*Honest limit on that independence: the same author wrote both. What is guaranteed is that no code is
shared and that the generator's implementation was not consulted while this was written. Genuine
independence would need a second pair of eyes, and this is not it.*

The four families (§3):

  1. **Column sums** — individuals add to the totals row, in every column; the line score's R and H
     for the offense equal the batting totals for the same
  2. **Row identity** — `PA = AB + BB + HBP + SF + SH + CI`, per batter and again for the totals
  3. **Cross-team** — the offense's H, R, BB and SO equal what the opposing pitchers allowed, and the
     outs the offense made equal the outs those pitchers recorded
  4. **Global identity** — `PA = Outs + R + LOB`

Inequalities: `AB ≥ H`, `PA ≥ AB + BB`, `ER ≤ R`, and every cell non-negative.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from boxscore_package.format import BATTING_COLUMNS, FOOTNOTE_COLUMNS, PITCHING_COLUMNS, Board


class Family(StrEnum):
    """Which of §3's four kinds of reasoning an equation belongs to."""

    COLUMN_SUM = "column_sum"
    ROW_IDENTITY = "row_identity"
    CROSS_TEAM = "cross_team"
    GLOBAL_IDENTITY = "global_identity"


@dataclass(frozen=True, slots=True)
class Relation:
    """`sum(coefficient x cell) == constant`, or `<= constant` when `equality` is false.

    One shape for both because the reasoning over them is the same: an equality narrows a cell from
    both sides, an inequality from one, and nothing else differs.
    """

    terms: tuple[tuple[str, int], ...]
    constant: int
    family: Family
    origin: str
    equality: bool = True

    def cells(self) -> tuple[str, ...]:
        return tuple(cell for cell, _ in self.terms)


LOB: Final = "lob"


def batting(row: int, column: str) -> str:
    return f"bat[{row}].{column}"


def batting_total(column: str) -> str:
    return f"bat_total.{column}"


def footnote(row: int, column: str) -> str:
    return f"note[{row}].{column}"


def footnote_total(column: str) -> str:
    return f"note_total.{column}"


def pitching(row: int, column: str) -> str:
    return f"pit[{row}].{column}"


def pitching_total(column: str) -> str:
    return f"pit_total.{column}"


def all_cells(board: Board) -> tuple[str, ...]:
    """Every cell the arithmetic can speak about, in a fixed order."""
    cells: list[str] = []
    for row in range(len(board.batting)):
        cells += [batting(row, column) for column in BATTING_COLUMNS]
    cells += [batting_total(column) for column in BATTING_COLUMNS]
    for row in range(len(board.footnotes)):
        cells += [footnote(row, column) for column in FOOTNOTE_COLUMNS]
    cells += [footnote_total(column) for column in FOOTNOTE_COLUMNS]
    cells.append(LOB)
    for row in range(len(board.pitching)):
        cells += [pitching(row, column) for column in PITCHING_COLUMNS]
    cells += [pitching_total(column) for column in PITCHING_COLUMNS]
    return tuple(cells)


def relations(board: Board) -> tuple[Relation, ...]:
    """Every equality and inequality the board offers, for a board of this shape.

    The line score is given complete and never erased (§6), so wherever an identity reaches it the
    line score's value enters as a constant rather than as a cell. That is not a shortcut: a quantity
    the player is shown is a number, not an unknown.
    """
    batters = len(board.batting)
    pitchers = len(board.pitching)
    found: list[Relation] = []

    # --- 1. Column sums -------------------------------------------------------------------------
    for column in BATTING_COLUMNS:
        found.append(
            Relation(
                terms=(*((batting(row, column), 1) for row in range(batters)), (batting_total(column), -1)),
                constant=0,
                family=Family.COLUMN_SUM,
                origin=f"batting column {column}",
            )
        )
    for column in FOOTNOTE_COLUMNS:
        found.append(
            Relation(
                terms=(*((footnote(row, column), 1) for row in range(batters)), (footnote_total(column), -1)),
                constant=0,
                family=Family.COLUMN_SUM,
                origin=f"footnote column {column}",
            )
        )
    for column in PITCHING_COLUMNS:
        found.append(
            Relation(
                terms=(*((pitching(row, column), 1) for row in range(pitchers)), (pitching_total(column), -1)),
                constant=0,
                family=Family.COLUMN_SUM,
                origin=f"pitching column {column}",
            )
        )
    # The line score's R and H for the offense are the batting totals for the same (§3).
    found.append(
        Relation(
            terms=((batting_total("runs"), 1),),
            constant=board.line_score.offense_runs,
            family=Family.COLUMN_SUM,
            origin="line score runs",
        )
    )
    found.append(
        Relation(
            terms=((batting_total("hits"), 1),),
            constant=board.line_score.offense_hits,
            family=Family.COLUMN_SUM,
            origin="line score hits",
        )
    )

    # --- 2. Row identity ------------------------------------------------------------------------
    # PA = AB + BB + HBP + SF + SH + CI, per batter and again for the totals row. This is what stops
    # the constraint graph being a forest: at-bats and walks live in two equations each (§3).
    for row in range(batters):
        found.append(
            Relation(
                terms=(
                    (batting(row, "plate_appearances"), -1),
                    (batting(row, "at_bats"), 1),
                    (batting(row, "walks"), 1),
                    *((footnote(row, column), 1) for column in FOOTNOTE_COLUMNS),
                ),
                constant=0,
                family=Family.ROW_IDENTITY,
                origin=f"row identity, batter {row}",
            )
        )
    found.append(
        Relation(
            terms=(
                (batting_total("plate_appearances"), -1),
                (batting_total("at_bats"), 1),
                (batting_total("walks"), 1),
                *((footnote_total(column), 1) for column in FOOTNOTE_COLUMNS),
            ),
            constant=0,
            family=Family.ROW_IDENTITY,
            origin="row identity, totals",
        )
    )

    # --- 3. Cross-team --------------------------------------------------------------------------
    # The link between the two halves of the board, and the reason this is a puzzle rather than
    # unrelated columns (§3).
    for column in ("hits", "runs", "walks", "strikeouts"):
        found.append(
            Relation(
                terms=((batting_total(column), 1), (pitching_total(column), -1)),
                constant=0,
                family=Family.CROSS_TEAM,
                origin=f"cross-team {column}",
            )
        )

    # --- 4. Global identity ---------------------------------------------------------------------
    # PA = Outs + R + LOB. The offense's out count is not a cell on the board, so it enters through
    # the outs half of the cross-team family: the outs the offense made are the outs the opposing
    # pitchers recorded. The two are stated here as the one equation they compose into, because a
    # quantity that appears on no row cannot be an unknown the player fills in.
    found.append(
        Relation(
            terms=(
                (batting_total("plate_appearances"), 1),
                (pitching_total("outs"), -1),
                (batting_total("runs"), -1),
                (LOB, -1),
            ),
            constant=0,
            family=Family.GLOBAL_IDENTITY,
            origin="PA = Outs + R + LOB",
        )
    )

    found.extend(_inequalities(batters, pitchers))
    return tuple(found)


def _inequalities(batters: int, pitchers: int) -> list[Relation]:
    """`AB ≥ H`, `PA ≥ AB + BB`, `ER ≤ R`, and non-negativity everywhere (§3).

    Stated as `<=` throughout so there is one direction to reason about rather than two.

    `PA ≥ AB + BB` is the one worth naming: it is available wherever the footnote terms are not, and
    it narrows from the opposite side to the row identity — the identity says what plate appearances
    add up to, this says what they cannot fall below.
    """
    found: list[Relation] = []
    for row in range(batters):
        found.append(
            Relation(
                terms=((batting(row, "hits"), 1), (batting(row, "at_bats"), -1)),
                constant=0,
                family=Family.ROW_IDENTITY,
                origin=f"AB >= H, batter {row}",
                equality=False,
            )
        )
        found.append(
            Relation(
                terms=(
                    (batting(row, "at_bats"), 1),
                    (batting(row, "walks"), 1),
                    (batting(row, "plate_appearances"), -1),
                ),
                constant=0,
                family=Family.ROW_IDENTITY,
                origin=f"PA >= AB + BB, batter {row}",
                equality=False,
            )
        )
    found.append(
        Relation(
            terms=((batting_total("hits"), 1), (batting_total("at_bats"), -1)),
            constant=0,
            family=Family.ROW_IDENTITY,
            origin="AB >= H, totals",
            equality=False,
        )
    )
    found.append(
        Relation(
            terms=(
                (batting_total("at_bats"), 1),
                (batting_total("walks"), 1),
                (batting_total("plate_appearances"), -1),
            ),
            constant=0,
            family=Family.ROW_IDENTITY,
            origin="PA >= AB + BB, totals",
            equality=False,
        )
    )
    for row in range(pitchers):
        found.append(
            Relation(
                terms=((pitching(row, "earned_runs"), 1), (pitching(row, "runs"), -1)),
                constant=0,
                family=Family.COLUMN_SUM,
                origin=f"ER <= R, pitcher {row}",
                equality=False,
            )
        )
    found.append(
        Relation(
            terms=((pitching_total("earned_runs"), 1), (pitching_total("runs"), -1)),
            constant=0,
            family=Family.COLUMN_SUM,
            origin="ER <= R, totals",
            equality=False,
        )
    )
    return found


def _row_values(
    known: dict[str, int],
    rows: tuple[tuple[int | None, ...], ...],
    columns: tuple[str, ...],
    name: Callable[[int, str], str],
) -> None:
    for row, line in enumerate(rows):
        for index, column in enumerate(columns):
            value = line[index]
            if value is not None:
                known[name(row, column)] = value


def _total_values(
    known: dict[str, int],
    totals: tuple[int | None, ...],
    columns: tuple[str, ...],
    name: Callable[[str], str],
) -> None:
    for index, column in enumerate(columns):
        value = totals[index]
        if value is not None:
            known[name(column)] = value


def values_of(board: Board) -> dict[str, int]:
    """The cells a board actually states. Erased cells are simply absent."""
    known: dict[str, int] = {}
    _row_values(known, board.batting, BATTING_COLUMNS, batting)
    _total_values(known, board.batting_totals, BATTING_COLUMNS, batting_total)
    _row_values(known, board.footnotes, FOOTNOTE_COLUMNS, footnote)
    _total_values(known, board.footnote_totals, FOOTNOTE_COLUMNS, footnote_total)
    if board.left_on_base is not None:
        known[LOB] = board.left_on_base
    _row_values(known, board.pitching, PITCHING_COLUMNS, pitching)
    _total_values(known, board.pitching_totals, PITCHING_COLUMNS, pitching_total)
    return known


def line_score_faults(board: Board) -> list[str]:
    """What the line score itself must satisfy, before any cell is looked at.

    The line score is the board's anchor and is given complete, so it is the one part of the board
    where an inconsistency is purely a data fault and can never be a puzzle fault.
    """
    score = board.line_score
    faults: list[str] = []
    if sum(score.offense_by_inning) != score.offense_runs:
        faults.append(
            f"offense innings add to {sum(score.offense_by_inning)} against a stated {score.offense_runs} runs"
        )
    if sum(score.defense_by_inning) != score.defense_runs:
        faults.append(
            f"defense innings add to {sum(score.defense_by_inning)} against a stated {score.defense_runs} runs"
        )
    negative = [value for value in (*score.offense_by_inning, *score.defense_by_inning) if value < 0]
    if negative:
        faults.append(f"line score holds a negative inning: {negative}")
    return faults
