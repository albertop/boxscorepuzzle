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

⚠️⚠️ **`slot_references` moved here on 2026-08-21 for the same reason and by the same argument**
(v36-P3-37). It produces `Package.slot_references` — **a published field the schema validates** — and
it was living in `discovery/difficulty-metrics/measure.py`, outside `mypy --strict` and inside the
ratcheted lint tree, imported by the production writer. That is the paragraph above, repeated with a
different function; a fixed defect recorded in a docstring is not a rule the next case obeys.

⚠️ The pool **loader** is still in that instrument and is not moved. It carries the SQL, the connection
and the era windows, and promoting it is the inventory pipeline's work rather than a rename — recorded
in `docs/reviews/todo.md`. What is closed here is the part that reaches a published file.

This is the generator's job rather than the verifier's. §22 forbids the verifier sharing code with the
generator, and the file format belongs to neither — so the side that *produces* a package owns the
conversion into it, and the verifier reads only what the format defines.
"""

from collections import Counter
from collections.abc import Sequence
from string import ascii_lowercase

from boxscore_forge.boxscore import Direction
from boxscore_forge.identities import BATTING_COLUMNS, FOOTNOTE_COLUMNS, PITCHING_COLUMNS, TEAM_FOOTNOTE_FIELDS
from boxscore_package.format import Board, LineScore


def _given(value: int | None) -> int:
    """Left on base, which §6 never erases. A `None` here is a generator that changed its mind."""
    if value is None:
        message = "left on base was erased; §6 gives it, and without it the global identity cannot be expressed"
        raise ValueError(message)
    return value


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
        # ⚠️ **Refused rather than passed through as `None`.** `cell()` returns `None` for an erased
        # cell, and LOB is not in the erasable set — so this is unreachable today. It is written because
        # the day somebody adds LOB to that set, the producer stops here instead of building a board
        # both readers refuse at their boundary, which is a failure three layers further from the cause.
        left_on_base=_given(
            cell(
                f"team_footnotes.{TEAM_FOOTNOTE_FIELDS[0]}",
                getattr(direction.team_footnotes, TEAM_FOOTNOTE_FIELDS[0]),
            )
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


def slot_references(slots: Sequence[int]) -> tuple[str, ...]:
    """The reference for each row: `9` when its slot holds one row, `9a`/`9b`/`9c` when it is shared.

    ⚠️ **One function, and both callers use it.** The slot cell and the footnote line apply the same
    condition — *is this slot shared* — and two places applying one condition is the defect this
    project has spent the day closing. The cell prints what this returns and the footnote prints what
    this returns, so `SH: 9b` and the cell reading `9b` cannot drift into disagreeing.

    The letter appears **only** where a slot is shared, which makes it the signal that a substitution
    happened rather than decoration on every row: nine rows numbered 1 to 9, with letters exactly where
    somebody was replaced. Never `2a` when there is no `2b`.

    Every reference carries the slot number, never a bare letter. The footnote says `9b`, so a cell
    saying `9b` makes finding the row a recognition rather than a composition — and leaves no second
    representation of the same thing to go stale.

    This applies to every slot, not only the ninth. A substituted left fielder gives `5a` and `5b`; the
    pitcher's slot dominates the examples only because it is the position most often substituted.
    """
    shared = {slot for slot in slots if list(slots).count(slot) > 1}
    seen: Counter[int] = Counter()
    references: list[str] = []
    for slot in slots:
        seen[slot] += 1
        references.append(f"{slot}{ascii_lowercase[seen[slot] - 1]}" if slot in shared else str(slot))
    return tuple(references)
