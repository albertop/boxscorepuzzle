"""Is this a real baseball game, or merely a consistent one?

⚠️ **This is the class of check that was missing, and its absence cost two decisions.** The loader put
non-batting pitchers on the board as rows of noughts. Every identity still balanced — a row of zeros
adds nothing to any sum — so all four layers of §22 passed it in silence, and it was found by a human
reading a printed board.

Everything else in this package tests **internal consistency**. A fabricated board and a real one
both satisfy the identities. These test **correspondence to reality**: each assertion is about how
baseball actually works, and none of them can be derived from §3.

They are deliberately loose. The job is to catch a board that could not have happened, not to encode
a model of the game — a check that rejects a real boxscore is worse than no check, because it will be
loosened until it says nothing.
"""

from dataclasses import dataclass

from boxscore_package.format import BATTING_COLUMNS, PITCHING_COLUMNS, Board, Package

OUTS_PER_INNING = 3
MIN_BATTERS = 9
"""Nine men bat. A board with fewer is missing rows, whatever its arithmetic says."""

MAX_PLATE_APPEARANCES_PER_OUT = 2.2
"""A ceiling on how much a lineup can bat per out recorded, **read off the pool rather than guessed**.

Measured over 480 directions: median 1.54, p90 1.74, p99 1.96, maximum 2.12. A first version guessed
1.9 and flagged 1.9% of perfectly real games — a check that rejects real boxscores gets loosened
until it says nothing, so the number comes from the distribution with a little headroom above it.
"""


@dataclass(frozen=True, slots=True)
class Implausible:
    what: str
    detail: str


def faults(board: Board, *, max_batters: int = 13) -> list[Implausible]:
    """Everything about this board that could not have happened in a game.

    Runs on a complete board — a source boxscore, or a solved puzzle. A partly erased board has
    unknowns, and "this cell is blank" is not implausible.
    """
    found: list[Implausible] = []
    found += _batting_row_faults(board)
    found += _roster_faults(board, max_batters)
    found += _volume_faults(board)
    return found


def _batting_row_faults(board: Board) -> list[Implausible]:
    found: list[Implausible] = []
    # ⚠️ Deliberately *not* "every row has a plate appearance". A pinch runner comes in, scores, and
    # never bats — PA of nought and a run beside it — and a filter that required a plate appearance
    # dropped him and his run with him. That was the second defect of the same afternoon, and the
    # game-log cross-check caught it because the loader sums its own totals and could not.
    #
    # The true invariant is that a row on the board **contributed something**.
    for index, row in enumerate(board.batting):
        if all(value == 0 for value in row if value is not None) and any(value is not None for value in row):
            found.append(Implausible("a batting row that is entirely nought", f"row {index}"))
    for index, row in enumerate(board.pitching):
        if all(value == 0 for value in row if value is not None) and any(value is not None for value in row):
            found.append(Implausible("a pitching row that is entirely nought", f"row {index}"))
    return found


def _roster_faults(board: Board, max_batters: int) -> list[Implausible]:
    found: list[Implausible] = []
    if len(board.batting) < MIN_BATTERS:
        found.append(Implausible("too few batting rows", f"{len(board.batting)} rows, and nine men have to bat"))
    if len(board.batting) > max_batters:
        found.append(Implausible("too many batting rows", f"{len(board.batting)} rows against a cap of {max_batters}"))
    if not board.pitching:
        found.append(Implausible("no pitching rows", "somebody pitched"))
    if len(board.footnotes) != len(board.batting):
        found.append(
            Implausible(
                "the footnote line does not match the lineup",
                f"{len(board.footnotes)} footnote rows against {len(board.batting)} batters",
            )
        )
    return found


def _volume_faults(board: Board) -> list[Implausible]:
    """Plate appearances against outs recorded — the two are tied by how baseball ends an inning."""
    found: list[Implausible] = []
    plate = board.batting_totals[BATTING_COLUMNS.index("plate_appearances")]
    outs = board.pitching_totals[PITCHING_COLUMNS.index("outs")]
    if plate is None or outs is None:
        return found
    if outs < 1:
        found.append(Implausible("no outs recorded", "a completed game records outs"))
        return found
    if plate < outs:
        # Every out is made by a batter or a runner who reached, so a lineup cannot come to the plate
        # fewer times than the opposing pitchers recorded outs.
        found.append(Implausible("fewer plate appearances than outs", f"{plate} plate appearances against {outs} outs"))
    if plate > outs * MAX_PLATE_APPEARANCES_PER_OUT:
        found.append(
            Implausible(
                "implausibly many plate appearances for the outs recorded",
                f"{plate} against {outs} outs, over {MAX_PLATE_APPEARANCES_PER_OUT} per out",
            )
        )
    innings = len(board.line_score.offense_by_inning)
    if innings and outs > innings * OUTS_PER_INNING + OUTS_PER_INNING:
        found.append(
            Implausible(
                "more outs than the innings allow",
                f"{outs} outs across {innings} innings on the line score",
            )
        )
    return found


PLACEHOLDERS = frozenset({"OPP", "TBD", "???", ""})
"""Values that mean "not filled in yet" and must never reach a player."""


def reveal_faults(package: Package) -> list[Implausible]:
    """The reveal is the payoff and nothing was validating it.

    ⚠️ Found by reading six generated files and recognising a lineup: four of them named the wrong
    club, because the team code was taken from the game identifier — which holds the *home* team —
    while the names came from the roster. It coincides whenever the home side batted, and lies
    otherwise. **No verifier layer could see it**: a wrong team name breaks no equation.

    These are the cheap checks a package can make about itself. The expensive one — does this roster
    actually belong to this club — needs the person register and lives in the loader sweep.
    """
    found: list[Implausible] = []
    reveal = package.reveal
    if reveal is None:
        return [Implausible("no reveal", "§7 shows teams, date and context at the end; there is none")]

    if len(reveal.batter_names) != len(package.puzzle.batting):
        found.append(
            Implausible(
                "the reveal does not name every batter",
                f"{len(reveal.batter_names)} names against {len(package.puzzle.batting)} rows",
            )
        )
    if len(reveal.pitcher_names) != len(package.puzzle.pitching):
        # §7's progressive reveal names a pitching row on completion exactly as it names a batting
        # row. A short list means the pitching section reveals nothing.
        found.append(
            Implausible(
                "the reveal does not name every pitcher",
                f"{len(reveal.pitcher_names)} names against {len(package.puzzle.pitching)} rows",
            )
        )
    for field, value in (
        ("offense_team", reveal.offense_team),
        ("defense_team", reveal.defense_team),
    ):
        if value.strip().upper() in PLACEHOLDERS:
            found.append(Implausible(f"{field} is a placeholder", f"{value!r} would reach a player"))
    if reveal.offense_team and reveal.offense_team == reveal.defense_team:
        found.append(Implausible("both teams are the same club", reveal.offense_team))
    placeholder_names = [name for name in (*reveal.batter_names, *reveal.pitcher_names) if not name.strip()]
    if placeholder_names:
        found.append(Implausible("a row would reveal an empty name", f"{len(placeholder_names)} of them"))
    if not reveal.played_on.strip():
        found.append(Implausible("no date on the reveal", "§7 shows the date at the end"))
    return found
