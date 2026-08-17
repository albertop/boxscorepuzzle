"""Shared fixtures.

The balanced boxscore is a real game, not invented numbers: Chicago Cubs at Atlanta Braves,
8 August 1968, Retrosheet game ATL196808080. The Cubs' offense against the Braves' pitching is one
direction of that game, and it passes the roster caps with 9 batters and 2 pitchers.

Invented test data cannot catch an identity that is stated wrongly, because the data would be built
to satisfy the wrong statement. A real game can.
"""

from datetime import timedelta

import pytest
from hypothesis import settings

from boxscore_forge.boxscore import BattingLine, Direction, Footnotes, LineScore, PitchingLine

# Composite generation of a whole balanced boxscore is not fast, and a per-example deadline tuned
# for trivial strategies turns into a flaky failure that says nothing about the code.
settings.register_profile("forge", deadline=timedelta(seconds=2))
settings.load_profile("forge")


@pytest.fixture
def cubs_at_braves_1968() -> Direction:
    """Chicago Cubs offense against Atlanta Braves pitching, 8 August 1968. Cubs won 4-0."""
    batting = (
        BattingLine(at_bats=4, runs=1, hits=1, runs_batted_in=0, walks=0, strikeouts=0),
        BattingLine(at_bats=5, runs=0, hits=2, runs_batted_in=1, walks=0, strikeouts=1),
        BattingLine(at_bats=4, runs=1, hits=2, runs_batted_in=2, walks=1, strikeouts=0),
        BattingLine(at_bats=4, runs=0, hits=1, runs_batted_in=1, walks=0, strikeouts=1),
        BattingLine(at_bats=4, runs=0, hits=0, runs_batted_in=0, walks=0, strikeouts=1),
        BattingLine(at_bats=3, runs=0, hits=2, runs_batted_in=0, walks=1, strikeouts=0),
        BattingLine(at_bats=4, runs=0, hits=1, runs_batted_in=0, walks=0, strikeouts=0),
        BattingLine(at_bats=4, runs=0, hits=1, runs_batted_in=0, walks=0, strikeouts=0),
        BattingLine(at_bats=4, runs=2, hits=1, runs_batted_in=0, walks=0, strikeouts=2),
    )
    pitching = (
        PitchingLine(outs=20, hits=10, runs=4, earned_runs=4, walks=1, strikeouts=3),
        PitchingLine(outs=7, hits=1, runs=0, earned_runs=0, walks=1, strikeouts=2),
    )
    return Direction(
        batting=batting,
        batting_totals=BattingLine(at_bats=36, runs=4, hits=11, runs_batted_in=4, walks=2, strikeouts=5),
        pitching=pitching,
        pitching_totals=PitchingLine(outs=27, hits=11, runs=4, earned_runs=4, walks=2, strikeouts=5),
        footnotes=Footnotes(
            left_on_base=8, hit_by_pitch=0, sacrifice_flies=0, sacrifice_hits=1, reached_on_interference=0
        ),
        line_score=LineScore(
            offense_by_inning=(1, 0, 1, 0, 0, 0, 2, 0, 0),
            defense_by_inning=(0, 0, 0, 0, 0, 0, 0, 0, 0),
            offense_runs=4,
            offense_hits=11,
            offense_errors=0,
            defense_runs=0,
            defense_hits=3,
            defense_errors=0,
        ),
    )
