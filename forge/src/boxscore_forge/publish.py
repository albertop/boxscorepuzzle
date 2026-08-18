"""Turning a generated direction into the package the player receives.

⚠️ **This lived in `discovery/verifier/rejection_rates.py` and the production path imported it from
there** — a research experiment supplying the conversion for the artefact that ships. It is here now.

**And it silently dropped footnote erasures.** The batting and pitching rows consulted the erased set;
the footnote rows copied every value unconditionally. So the generator could erase a footnote cell,
measure a solution path that used it as an unknown, and the conversion would hand the value back — the
verifier then validating an easier board than the one that was graded, with the metadata describing
neither. The omission was specific and silent, which is why it survived.

The erased set is applied **uniformly** here, to every section including the footnote line and the team
footnote, so a future decision to open any of them cannot reintroduce the same gap. §6 currently gives
the footnote line complete, so nothing is erased there today; the code does not depend on that.

This is the generator's job rather than the verifier's. §22 forbids the verifier sharing code with the
generator, and the file format belongs to neither — so the side that *produces* a package owns the
conversion into it, and the verifier reads only what the format defines.
"""

from boxscore_forge.boxscore import Direction
from boxscore_forge.identities import BATTING_COLUMNS, FOOTNOTE_COLUMNS, PITCHING_COLUMNS, TEAM_FOOTNOTE_FIELDS
from boxscore_package.format import Board, LineScore


def to_board(direction: Direction, erased: frozenset[str] | None = None) -> Board:
    """The board as the player meets it. `erased` names cells the generator's way.

    Pass `None` for the complete board — the solution half of the package, and the source layer 4
    compares against.
    """
    blanks = erased or frozenset()

    def cell(name: str, value: int) -> int | None:
        """One rule for every section. The bug this module exists for was a section with its own."""
        return None if name in blanks else value

    def row(prefix: str, index: int, line: object, columns: tuple[str, ...]) -> tuple[int | None, ...]:
        return tuple(cell(f"{prefix}[{index}].{column}", getattr(line, column)) for column in columns)

    def totals(prefix: str, line: object, columns: tuple[str, ...]) -> tuple[int | None, ...]:
        return tuple(cell(f"{prefix}.{column}", getattr(line, column)) for column in columns)

    score = direction.line_score
    return Board(
        batting=tuple(row("batting", index, line, BATTING_COLUMNS) for index, line in enumerate(direction.batting)),
        batting_totals=totals("batting_totals", direction.batting_totals, BATTING_COLUMNS),
        footnotes=tuple(
            row("footnotes", index, note, FOOTNOTE_COLUMNS) for index, note in enumerate(direction.batter_footnotes)
        ),
        footnote_totals=totals("footnote_totals", direction.footnote_totals, FOOTNOTE_COLUMNS),
        left_on_base=cell(
            f"team_footnotes.{TEAM_FOOTNOTE_FIELDS[0]}",
            getattr(direction.team_footnotes, TEAM_FOOTNOTE_FIELDS[0]),
        ),
        pitching=tuple(row("pitching", index, line, PITCHING_COLUMNS) for index, line in enumerate(direction.pitching)),
        pitching_totals=totals("pitching_totals", direction.pitching_totals, PITCHING_COLUMNS),
        # The line score is the board's anchor and is never erased (§6), so it is copied whole rather
        # than passed through `cell` — a blank here would be malformed, not difficult.
        line_score=LineScore(
            offense_by_inning=score.offense_by_inning,
            defense_by_inning=score.defense_by_inning,
            offense_runs=score.offense_runs,
            offense_hits=score.offense_hits,
            offense_errors=score.offense_errors,
            defense_runs=score.defense_runs,
            defense_hits=score.defense_hits,
            defense_errors=score.defense_errors,
        ),
    )


__all__ = ["to_board"]
