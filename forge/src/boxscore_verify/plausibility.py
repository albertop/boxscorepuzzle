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

from boxscore_domain import (
    BATTER_CAP,
    MAX_PLATE_APPEARANCES_PER_OUT,
    MIN_BATTERS,
    PITCHER_CAP,
)
from boxscore_package.format import BATTING_COLUMNS, PITCHING_COLUMNS, Board, Package

OUTS_PER_INNING = 3
"""Not a domain constant with a decision behind it — it is how baseball works, and it stays here.

⚠️ The line between this and `boxscore_domain` is worth stating: that module holds values somebody
*chose*, which is why each carries its reason and its measurement. Three outs was not chosen and has no
measurement, so filing it there would put a rule of the sport among decisions that can be revisited.
"""


@dataclass(frozen=True, slots=True)
class Implausible:
    what: str
    detail: str


def faults(board: Board, *, max_batters: int = BATTER_CAP, max_pitchers: int = PITCHER_CAP) -> list[Implausible]:
    """Everything about this board that could not have happened in a game.

    Runs on a complete board — a source boxscore, or a solved puzzle. A partly erased board has
    unknowns, and "this cell is blank" is not implausible.
    """
    found: list[Implausible] = []
    found += _batting_row_faults(board)
    found += _roster_faults(board, max_batters, max_pitchers)
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


def _roster_faults(board: Board, max_batters: int, max_pitchers: int) -> list[Implausible]:
    found: list[Implausible] = []
    if len(board.batting) < MIN_BATTERS:
        found.append(Implausible("too few batting rows", f"{len(board.batting)} rows, and nine men have to bat"))
    if len(board.batting) > max_batters:
        found.append(Implausible("too many batting rows", f"{len(board.batting)} rows against a cap of {max_batters}"))
    if not board.pitching:
        found.append(Implausible("no pitching rows", "somebody pitched"))
    # ⚠️ **The batter cap was checked here and the pitcher cap was not**, for as long as this file has
    # existed. §5 states both, and only one was enforced anywhere outside a SQL filter in a discovery
    # script — so "≤4 pitchers" was a rule the publication path could not see, held up entirely by
    # whichever `load()` call happened to pass the right argument. Raising the cap to 6 without closing
    # this would have been documentation rather than a change.
    #
    # It cannot fire on a board the pool filter produced, because that filter caps at the same number.
    # That is the reason to write it rather than to skip it: this runs on any package reaching the
    # publication gate, including one that never went through the filter.
    if len(board.pitching) > max_pitchers:
        found.append(
            Implausible("too many pitching rows", f"{len(board.pitching)} rows against a cap of {max_pitchers}")
        )
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

    # ⚠️⚠️ **Five checks stood here and none of them could fire.** Deleted 2026-08-21, not disabled.
    #
    # They asked whether the reveal names every batter, names every pitcher, carries a placeholder team
    # code, gives both clubs the same code, or reveals an empty name. **`Package.__post_init__` calls
    # `check_reveal_agrees` and refuses every one of those packages before this function can run** —
    # `Reveal.boxscore` is a required field, so the agreement check has something to compare against on
    # every package that exists. Verified by construction, case by case, rather than by reading:
    # each of the five raises `PackageError` from the constructor.
    #
    # **One predicate, two places, and the stricter copy runs first** — so the weaker one was dead code
    # wearing the shape of a safety net. *A check that never fires is indistinguishable from a check
    # that is broken*, and this file's own purpose is to catch what the arithmetic cannot; a reader
    # counting its checks would have credited it with five it did not perform.
    #
    # The guarantee is not lost, it is somewhere better: `forge/tests/verify/test_reveal_agreement.py`
    # asserts the constructor refuses each case. Deleted rather than left with a `no cover` marker,
    # which is what this project did with the footnote-erasure machinery and with `traversal()`'s
    # unreachable branch.
    if not reveal.played_on.strip():
        found.append(Implausible("no date on the reveal", "§7 shows the date at the end"))
    return found
