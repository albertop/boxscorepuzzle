"""A printed boxscore for tests whose subject is not the printed boxscore.

⚠️⚠️ **This derives the shared half from the board, and that is the whole point.** From schema 5 the
reveal restates the board's own numbers for the half the two share, and `check_reveal_agrees` refuses a
package where they disagree. A test about erasure or about certification has no opinion about the
reveal and should not have to hand-copy thirty numbers to say so — it would copy them wrongly, the
check would fire, and the failure would name the reveal in a test about something else.

⚠️ **So no test that uses this can be evidence that the agreement check works.** It cannot fail here:
the two halves come from one source. The check is exercised in `tests/verify/test_reveal_agreement.py`,
which builds them apart on purpose and asserts the mismatch is refused — including the case of a
package assembled in memory, because the constructor is the boundary and `from_json` is not the only
way in.

⚠⚠ **The unshared half is derived from the line score, and it used to be invented.** `offense.pitching`
and `defense.batting` appear nowhere else in the *board*, so the first version filled them with one
all-zero row named `Not A Real Player` — and `test_a_sound_package_is_publishable` expected the
publication gate to accept that. It did, because the check `format.py` delegated the unshared half to
did not exist. v30-P1-02.

`check_printed_boxscore_corresponds` exists now, so these rows have to satisfy the anchors the line
score provides: the defence's batters scored the defence's runs and made its hits, and the offence's
staff allowed the same events from the other side and recorded the outs the innings imply. Derived
here rather than typed, for the same reason the shared half is.

⚠️ **The names stay obviously synthetic and no gate looks at them, deliberately.** The unshared grids
were not used for the game; they are on the finished sheet because a boxscore shows both teams, and
they are offered as-is — v30-P1-02, retracted on that ground. So `INVENTED` marks the part of these
rows nothing checks, and a test that starts depending on *which* fake batter had the hits is depending
on nothing.
"""

from boxscore_package.format import (
    BATTING_COLUMNS,
    PITCHING_COLUMNS,
    Board,
    PrintedBatter,
    PrintedBoxscore,
    PrintedPitcher,
    PrintedSide,
    Reveal,
)

PLAYED_ON = "1968-08-08"
"""One date for every fixture. Nothing in these tests turns on which day it was."""

INVENTED = "Not A Real Player"
"""The name on every row of the half no package can check. See the module docstring."""


def _cell(row: tuple[int | None, ...], columns: tuple[str, ...], column: str) -> int:
    value = row[columns.index(column)]
    # A solution board is complete by `check_profile`, so this cannot be None on the path that matters.
    return 0 if value is None else value


def _printed_from(
    solution: Board,
    labels: tuple[str, ...],
    roles: tuple[str, ...],
    names: tuple[tuple[str, ...], tuple[str, ...]],
    teams: tuple[str, str],
) -> PrintedBoxscore:
    """The sheet a package with this solution would carry, agreeing with it by construction."""
    batter_names, pitcher_names = names
    offense, defense = teams
    return PrintedBoxscore(
        offense=PrintedSide(
            code=offense,
            city="Testville",
            nickname="Fixtures",
            batting=tuple(
                PrintedBatter(
                    name=batter_names[index],
                    position=labels[index],
                    at_bats=_cell(row, BATTING_COLUMNS, "at_bats"),
                    runs=_cell(row, BATTING_COLUMNS, "runs"),
                    hits=_cell(row, BATTING_COLUMNS, "hits"),
                    # Runs batted in are on no board, so there is nothing to derive one from.
                    runs_batted_in=0,
                    walks=_cell(row, BATTING_COLUMNS, "walks"),
                    strikeouts=_cell(row, BATTING_COLUMNS, "strikeouts"),
                )
                for index, row in enumerate(solution.batting)
            ),
            pitching=(_staff_for(solution),),
        ),
        defense=PrintedSide(
            code=defense,
            city="Otherton",
            nickname="Placeholders",
            batting=(_lineup_for(solution),),
            pitching=tuple(
                PrintedPitcher(
                    name=pitcher_names[index],
                    role=roles[index],
                    outs=_cell(row, PITCHING_COLUMNS, "outs"),
                    hits=_cell(row, PITCHING_COLUMNS, "hits"),
                    runs=_cell(row, PITCHING_COLUMNS, "runs"),
                    earned_runs=_cell(row, PITCHING_COLUMNS, "earned_runs"),
                    walks=_cell(row, PITCHING_COLUMNS, "walks"),
                    strikeouts=_cell(row, PITCHING_COLUMNS, "strikeouts"),
                )
                for index, row in enumerate(solution.pitching)
            ),
        ),
    )


def reveal_for(
    solution: Board,
    *,
    labels: tuple[str, ...],
    pitcher_labels: tuple[str, ...],
    offense: str = "AAA",
    defense: str = "BBB",
) -> Reveal:
    """A complete, self-consistent reveal for a board — names included, so nothing has to be paired."""
    batter_names = tuple(f"Batter {index + 1}" for index in range(len(solution.batting)))
    pitcher_names = tuple(f"Pitcher {index + 1}" for index in range(len(solution.pitching)))
    return Reveal(
        batter_names=batter_names,
        pitcher_names=pitcher_names,
        offense_team=offense,
        defense_team=defense,
        played_on=PLAYED_ON,
        boxscore=_printed_from(solution, labels, pitcher_labels, (batter_names, pitcher_names), (offense, defense)),
    )


def _lineup_for(solution: Board) -> PrintedBatter:
    """The defence's whole batting order as one row, carrying the runs and hits the line score says.

    One row rather than nine: the gate compares club totals, and inventing a distribution across nine
    fake men would be adding detail nothing can check — which is what the fixture is here to avoid.
    """
    score = solution.line_score
    return PrintedBatter(
        name=INVENTED,
        position="C",
        at_bats=score.defense_hits,
        runs=score.defense_runs,
        hits=score.defense_hits,
        runs_batted_in=score.defense_runs,
        walks=0,
        strikeouts=0,
    )


def _staff_for(solution: Board) -> PrintedPitcher:
    """The offence's staff as one line, allowing what the defence scored and recording the outs it made."""
    score = solution.line_score
    return PrintedPitcher(
        name=INVENTED,
        role="SP",
        # Three per completed inning. The bound the gate applies allows the last one to be short; the
        # fixture takes the simple case where it was not.
        outs=3 * len(score.defense_by_inning),
        hits=score.defense_hits,
        runs=score.defense_runs,
        earned_runs=score.defense_runs,
        walks=0,
        strikeouts=0,
    )
