"""Hypothesis strategies that build boxscores which satisfy every identity by construction.

The generator deliberately does not aim for realistic baseball. It aims for arithmetic consistency
across the whole space the identities allow, including shapes no real game ever produced. A
strategy tuned to look like real games would only ever exercise the region the example-based tests
already cover.
"""

from hypothesis import strategies as st
from hypothesis.strategies import DrawFn

from boxscore_forge.boxscore import (
    BatterFootnotes,
    BattingLine,
    Direction,
    LineScore,
    PitchingLine,
    TeamFootnotes,
)

LINEUP_SLOTS = 9
"""A batting order is nine places — the shape of the game, not a parameter."""


def _split(draw: DrawFn, total: int, parts: int) -> list[int]:
    """Split a non-negative total into `parts` non-negative integers that add back to it.

    Biased towards putting more in the earlier parts, which is acceptable: shrinking still reaches
    the interesting cases, and the identities are symmetric in row order anyway.
    """
    remaining = total
    values = []
    for _ in range(parts - 1):
        taken = draw(st.integers(min_value=0, max_value=remaining))
        values.append(taken)
        remaining -= taken
    values.append(remaining)
    return values


@st.composite
def valid_directions(draw: DrawFn) -> Direction:
    """A boxscore that balances: every identity holds, by construction rather than by luck."""
    batting, footnotes = _draw_batting(draw)
    batting_totals = _sum_batting(batting)
    footnote_totals = _sum_footnotes(footnotes)

    # Outs plus runs plus runners left on base must account for every plate appearance, so once the
    # runners left on base are chosen the number of outs is forced.
    left_on_base = draw(
        st.integers(min_value=0, max_value=max(batting_totals.plate_appearances - batting_totals.runs, 0))
    )
    outs = batting_totals.plate_appearances - batting_totals.runs - left_on_base
    pitching = _draw_pitching(draw, batting_totals, outs)

    return Direction(
        batting=batting,
        batting_totals=batting_totals,
        batter_footnotes=footnotes,
        footnote_totals=footnote_totals,
        team_footnotes=TeamFootnotes(left_on_base=left_on_base),
        pitching=pitching,
        pitching_totals=_sum_pitching(pitching),
        line_score=_draw_line_score(draw, batting_totals),
    )


def _draw_batting(draw: DrawFn) -> tuple[tuple[BattingLine, ...], tuple[BatterFootnotes, ...]]:
    """A lineup, not nine independent rows.

    ⚠⚠ **Plate appearances are dealt round the order, because that is what makes a boxscore a
    boxscore.** This drew each row's components freely and let the total fall out, which satisfies
    every arithmetic identity and produces a distribution no game can reach: a lineup bats in a cycle
    and never skips, so the places differ by at most one before substitutions are counted.

    That was invisible while the batting-order family was unused. The moment layer 3 could see it, the
    property test asserting "a board built from the identities passes every layer" started failing —
    correctly. **The identities never implied the cyclic distribution; the generator was producing
    boards that balance and could not have happened.** Fixed here rather than by dropping the slot
    references, because a fixture that declines to claim a lineup is a fixture that stops testing one.

    So the total is drawn first, dealt out by the cycle, and each row's components are drawn to fit
    the appearances it is owed.
    """
    batter_count = draw(st.integers(min_value=9, max_value=12))
    # Enough to give every place at least a couple of turns, and few enough to stay a plausible game.
    team_total = draw(st.integers(min_value=27, max_value=54))
    complete, over = divmod(team_total, LINEUP_SLOTS)
    per_slot = [complete + (1 if slot <= over else 0) for slot in range(1, LINEUP_SLOTS + 1)]

    # Rows beyond the ninth are substitutes: they share a place with the man they replaced, so the
    # place's appearances are split between them rather than added to the team's.
    # ⚠️ The ninth place, because that is where the slot references put them. `refs()` labels rows
    # beyond the ninth `9a`, `9b`, `9c`, so a strategy that split some other place would build a board
    # whose appearances and whose declared lineup disagree — and the disagreement surfaces as an
    # unexplained layer-3 rejection rather than as a wrong fixture.
    per_row = list(per_slot)
    last = LINEUP_SLOTS - 1
    for _ in range(batter_count - LINEUP_SLOTS):
        taken = draw(st.integers(min_value=0, max_value=per_row[last]))
        per_row[last] -= taken
        per_row.append(taken)

    lines = []
    footnotes = []
    for appearances in per_row:
        # Every appearance is one of: a walk, a footnote term, or an at-bat. Drawn in that order so
        # what is left over is the at-bats, which keeps `PA = AB + BB + HBP + SF + SH + CI` exact by
        # construction rather than by arithmetic afterwards.
        walks = draw(st.integers(min_value=0, max_value=min(appearances, 3)))
        room = appearances - walks
        row_footnotes = BatterFootnotes(
            hit_by_pitch=draw(st.integers(min_value=0, max_value=min(room, 1))),
            sacrifice_flies=0,
            sacrifice_hits=0,
            catcher_interference=0,
        )
        room -= row_footnotes.hit_by_pitch
        if room:
            row_footnotes = BatterFootnotes(
                hit_by_pitch=row_footnotes.hit_by_pitch,
                sacrifice_flies=draw(st.integers(min_value=0, max_value=min(room, 1))),
                sacrifice_hits=0,
                catcher_interference=0,
            )
            room -= row_footnotes.sacrifice_flies
        at_bats = room
        hits = draw(st.integers(min_value=0, max_value=at_bats))
        strikeouts = draw(st.integers(min_value=0, max_value=at_bats - hits))
        runs = draw(st.integers(min_value=0, max_value=hits + walks))
        lines.append(
            BattingLine(
                plate_appearances=appearances,
                at_bats=at_bats,
                runs=runs,
                hits=hits,
                walks=walks,
                strikeouts=strikeouts,
            )
        )
        footnotes.append(row_footnotes)
    return tuple(lines), tuple(footnotes)


def _draw_pitching(draw: DrawFn, batting_totals: BattingLine, outs: int) -> tuple[PitchingLine, ...]:
    """Distribute exactly the offense's totals across the pitchers, which is the cross-team link."""
    pitcher_count = draw(st.integers(min_value=1, max_value=4))
    per_pitcher_outs = _split(draw, outs, pitcher_count)
    per_pitcher_hits = _split(draw, batting_totals.hits, pitcher_count)
    per_pitcher_runs = _split(draw, batting_totals.runs, pitcher_count)
    per_pitcher_walks = _split(draw, batting_totals.walks, pitcher_count)
    per_pitcher_strikeouts = _split(draw, batting_totals.strikeouts, pitcher_count)
    per_pitcher_earned = [draw(st.integers(min_value=0, max_value=runs)) for runs in per_pitcher_runs]

    return tuple(
        PitchingLine(outs=outs_, hits=hits, runs=runs, earned_runs=earned, walks=walks, strikeouts=strikeouts)
        for outs_, hits, runs, earned, walks, strikeouts in zip(
            per_pitcher_outs,
            per_pitcher_hits,
            per_pitcher_runs,
            per_pitcher_earned,
            per_pitcher_walks,
            per_pitcher_strikeouts,
            strict=True,
        )
    )


def _draw_line_score(draw: DrawFn, batting_totals: BattingLine) -> LineScore:
    innings = draw(st.integers(min_value=8, max_value=12))
    defense_runs = draw(st.integers(min_value=0, max_value=15))
    return LineScore(
        offense_by_inning=tuple(_split(draw, batting_totals.runs, innings)),
        # The home team does not bat in the last inning when it is already ahead, so the two sides
        # of a line score need not be the same length.
        defense_by_inning=tuple(
            _split(draw, defense_runs, draw(st.integers(min_value=innings - 1, max_value=innings)))
        ),
        offense_runs=batting_totals.runs,
        offense_hits=batting_totals.hits,
        offense_errors=draw(st.integers(min_value=0, max_value=5)),
        defense_runs=defense_runs,
        defense_hits=draw(st.integers(min_value=0, max_value=20)),
        defense_errors=draw(st.integers(min_value=0, max_value=5)),
    )


def _sum_batting(batting: tuple[BattingLine, ...]) -> BattingLine:
    return BattingLine(
        plate_appearances=sum(line.plate_appearances for line in batting),
        at_bats=sum(line.at_bats for line in batting),
        runs=sum(line.runs for line in batting),
        hits=sum(line.hits for line in batting),
        walks=sum(line.walks for line in batting),
        strikeouts=sum(line.strikeouts for line in batting),
    )


def _sum_pitching(pitching: tuple[PitchingLine, ...]) -> PitchingLine:
    return PitchingLine(
        outs=sum(line.outs for line in pitching),
        hits=sum(line.hits for line in pitching),
        runs=sum(line.runs for line in pitching),
        earned_runs=sum(line.earned_runs for line in pitching),
        walks=sum(line.walks for line in pitching),
        strikeouts=sum(line.strikeouts for line in pitching),
    )


def _sum_footnotes(footnotes: tuple[BatterFootnotes, ...]) -> BatterFootnotes:
    return BatterFootnotes(
        hit_by_pitch=sum(row.hit_by_pitch for row in footnotes),
        sacrifice_flies=sum(row.sacrifice_flies for row in footnotes),
        sacrifice_hits=sum(row.sacrifice_hits for row in footnotes),
        catcher_interference=sum(row.catcher_interference for row in footnotes),
    )
