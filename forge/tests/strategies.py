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
    batter_count = draw(st.integers(min_value=9, max_value=12))
    lines = []
    footnotes = []
    for _ in range(batter_count):
        at_bats = draw(st.integers(min_value=0, max_value=6))
        hits = draw(st.integers(min_value=0, max_value=at_bats))
        strikeouts = draw(st.integers(min_value=0, max_value=at_bats - hits))
        walks = draw(st.integers(min_value=0, max_value=3))
        runs = draw(st.integers(min_value=0, max_value=hits + walks))
        # Footnote terms are rare in a real boxscore, and drawn rare here so the common shape stays
        # common while the exceptional row still gets generated.
        row_footnotes = BatterFootnotes(
            hit_by_pitch=draw(st.integers(min_value=0, max_value=1)),
            sacrifice_flies=draw(st.integers(min_value=0, max_value=1)),
            sacrifice_hits=draw(st.integers(min_value=0, max_value=1)),
            catcher_interference=draw(st.integers(min_value=0, max_value=1)),
        )
        lines.append(
            BattingLine(
                plate_appearances=at_bats
                + walks
                + row_footnotes.hit_by_pitch
                + row_footnotes.sacrifice_flies
                + row_footnotes.sacrifice_hits
                + row_footnotes.catcher_interference,
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
