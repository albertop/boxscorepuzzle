"""Layer 1 of the correctness guarantee: a boxscore that does not satisfy every identity never
reaches the pool.

These identities are also the constraint system the T1-T5 solver reasons over, so a mistake here
propagates into both the generator and the difficulty measurement.
"""

import dataclasses

import pytest

from boxscore_forge.boxscore import BattingLine, Direction, LineScore, PitchingLine
from boxscore_forge.identities import Identity, find_violations


class TestBalancedBoxscore:
    def test_finds_no_violations_when_the_game_is_real_and_balanced(self, cubs_at_braves_1968: Direction) -> None:
        violations = find_violations(cubs_at_braves_1968)

        assert violations == ()


class TestColumnSums:
    @pytest.mark.parametrize(
        "column",
        ["at_bats", "runs", "hits", "runs_batted_in", "walks", "strikeouts"],
        ids=lambda column: f"batting-{column}",
    )
    def test_detects_batting_total_that_disagrees_with_its_column(
        self, cubs_at_braves_1968: Direction, column: str
    ) -> None:
        inflated = dataclasses.replace(
            cubs_at_braves_1968.batting_totals, **{column: getattr(cubs_at_braves_1968.batting_totals, column) + 1}
        )
        broken = dataclasses.replace(cubs_at_braves_1968, batting_totals=inflated)

        violations = find_violations(broken)

        assert Identity.BATTING_COLUMN_SUM in {violation.identity for violation in violations}

    @pytest.mark.parametrize(
        "column",
        ["outs", "hits", "runs", "earned_runs", "walks", "strikeouts"],
        ids=lambda column: f"pitching-{column}",
    )
    def test_detects_pitching_total_that_disagrees_with_its_column(
        self, cubs_at_braves_1968: Direction, column: str
    ) -> None:
        inflated = dataclasses.replace(
            cubs_at_braves_1968.pitching_totals, **{column: getattr(cubs_at_braves_1968.pitching_totals, column) + 1}
        )
        broken = dataclasses.replace(cubs_at_braves_1968, pitching_totals=inflated)

        violations = find_violations(broken)

        assert Identity.PITCHING_COLUMN_SUM in {violation.identity for violation in violations}


class TestCrossTeamConstraint:
    @pytest.mark.parametrize("column", ["hits", "runs", "walks", "strikeouts"])
    def test_detects_pitching_total_that_disagrees_with_the_offense(
        self, cubs_at_braves_1968: Direction, column: str
    ) -> None:
        # Move one unit in both the pitcher's row and the pitching total, so the column sum still
        # balances and only the cross-team link breaks.
        first, second = cubs_at_braves_1968.pitching
        moved_row = dataclasses.replace(first, **{column: getattr(first, column) + 1})
        moved_total = dataclasses.replace(
            cubs_at_braves_1968.pitching_totals, **{column: getattr(cubs_at_braves_1968.pitching_totals, column) + 1}
        )
        broken = dataclasses.replace(cubs_at_braves_1968, pitching=(moved_row, second), pitching_totals=moved_total)

        violations = find_violations(broken)

        identities = {violation.identity for violation in violations}
        assert Identity.CROSS_TEAM_TOTAL in identities
        assert Identity.BATTING_COLUMN_SUM not in identities
        assert Identity.PITCHING_COLUMN_SUM not in identities


class TestPlateAppearanceIdentity:
    def test_detects_left_on_base_that_breaks_the_team_identity(self, cubs_at_braves_1968: Direction) -> None:
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            footnotes=dataclasses.replace(cubs_at_braves_1968.footnotes, left_on_base=7),
        )

        violations = find_violations(broken)

        assert Identity.PLATE_APPEARANCES in {violation.identity for violation in violations}

    def test_accepts_a_batter_who_reached_on_defensive_interference(self, cubs_at_braves_1968: Direction) -> None:
        # Reaching on catcher's interference is a plate appearance that is not an at-bat and not
        # any of the other four categories. Verified against the whole Retrosheet database: with it
        # the forward count of plate appearances balances in all 407,816 team-games, and without it
        # 1,933 of them break.
        #
        # Turn one at-bat that made an out into an interference: the batter is no longer charged an
        # at-bat, one fewer out is recorded, and he is left on base instead.
        balanced = dataclasses.replace(
            cubs_at_braves_1968,
            batting=(
                dataclasses.replace(cubs_at_braves_1968.batting[0], at_bats=3),
                *cubs_at_braves_1968.batting[1:],
            ),
            batting_totals=dataclasses.replace(cubs_at_braves_1968.batting_totals, at_bats=35),
            pitching=(
                dataclasses.replace(cubs_at_braves_1968.pitching[0], outs=19),
                cubs_at_braves_1968.pitching[1],
            ),
            pitching_totals=dataclasses.replace(cubs_at_braves_1968.pitching_totals, outs=26),
            footnotes=dataclasses.replace(cubs_at_braves_1968.footnotes, left_on_base=9, reached_on_interference=1),
        )

        assert find_violations(balanced) == ()

    def test_detects_interference_left_out_of_the_count(self, cubs_at_braves_1968: Direction) -> None:
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            footnotes=dataclasses.replace(cubs_at_braves_1968.footnotes, reached_on_interference=1),
        )

        violations = find_violations(broken)

        assert Identity.PLATE_APPEARANCES in {violation.identity for violation in violations}

    def test_detects_missing_sacrifice_hit(self, cubs_at_braves_1968: Direction) -> None:
        # The Cubs' one sacrifice hit is what makes 36 at-bats plus 2 walks reach 39 plate
        # appearances. Drop it and the identity stops closing.
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            footnotes=dataclasses.replace(cubs_at_braves_1968.footnotes, sacrifice_hits=0),
        )

        violations = find_violations(broken)

        assert Identity.PLATE_APPEARANCES in {violation.identity for violation in violations}


class TestLineScore:
    def test_detects_offense_innings_that_do_not_sum_to_the_run_total(self, cubs_at_braves_1968: Direction) -> None:
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            line_score=dataclasses.replace(
                cubs_at_braves_1968.line_score, offense_by_inning=(1, 0, 1, 0, 0, 0, 1, 0, 0)
            ),
        )

        violations = find_violations(broken)

        assert Identity.LINE_SCORE_RUNS in {violation.identity for violation in violations}

    def test_detects_defense_innings_that_do_not_sum_to_the_run_total(self, cubs_at_braves_1968: Direction) -> None:
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            line_score=dataclasses.replace(
                cubs_at_braves_1968.line_score, defense_by_inning=(0, 0, 0, 1, 0, 0, 0, 0, 0)
            ),
        )

        violations = find_violations(broken)

        assert Identity.LINE_SCORE_RUNS in {violation.identity for violation in violations}

    def test_detects_line_score_hits_that_disagree_with_the_batting_total(self, cubs_at_braves_1968: Direction) -> None:
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            line_score=dataclasses.replace(cubs_at_braves_1968.line_score, offense_hits=10),
        )

        violations = find_violations(broken)

        assert Identity.LINE_SCORE_HITS in {violation.identity for violation in violations}


class TestBounds:
    def test_detects_more_hits_than_at_bats(self, cubs_at_braves_1968: Direction) -> None:
        impossible = BattingLine(at_bats=1, runs=0, hits=2, runs_batted_in=0, walks=0, strikeouts=0)
        broken = dataclasses.replace(cubs_at_braves_1968, batting=(impossible, *cubs_at_braves_1968.batting[1:]))

        violations = find_violations(broken)

        assert Identity.HITS_WITHIN_AT_BATS in {violation.identity for violation in violations}

    def test_detects_more_earned_runs_than_runs(self, cubs_at_braves_1968: Direction) -> None:
        impossible = PitchingLine(outs=20, hits=10, runs=1, earned_runs=4, walks=1, strikeouts=3)
        broken = dataclasses.replace(cubs_at_braves_1968, pitching=(impossible, cubs_at_braves_1968.pitching[1]))

        violations = find_violations(broken)

        assert Identity.EARNED_RUNS_WITHIN_RUNS in {violation.identity for violation in violations}

    def test_detects_more_runs_batted_in_than_runs(self, cubs_at_braves_1968: Direction) -> None:
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            batting_totals=dataclasses.replace(cubs_at_braves_1968.batting_totals, runs_batted_in=5),
        )

        violations = find_violations(broken)

        assert Identity.RUNS_BATTED_IN_WITHIN_RUNS in {violation.identity for violation in violations}

    def test_detects_a_negative_value(self, cubs_at_braves_1968: Direction) -> None:
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            footnotes=dataclasses.replace(cubs_at_braves_1968.footnotes, left_on_base=-1),
        )

        violations = find_violations(broken)

        assert Identity.NON_NEGATIVE in {violation.identity for violation in violations}


class TestViolationReporting:
    def test_reports_every_broken_identity_rather_than_stopping_at_the_first(
        self, cubs_at_braves_1968: Direction
    ) -> None:
        # A boxscore is discarded, never repaired, so the value of validation is a full picture of
        # what is wrong rather than the first thing found.
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            footnotes=dataclasses.replace(cubs_at_braves_1968.footnotes, left_on_base=7),
            line_score=dataclasses.replace(cubs_at_braves_1968.line_score, offense_hits=10),
        )

        identities = {violation.identity for violation in find_violations(broken)}

        assert Identity.PLATE_APPEARANCES in identities
        assert Identity.LINE_SCORE_HITS in identities

    def test_names_the_column_that_broke(self, cubs_at_braves_1968: Direction) -> None:
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            batting_totals=dataclasses.replace(cubs_at_braves_1968.batting_totals, walks=9),
        )

        violations = find_violations(broken)

        column_sum_details = [
            violation.detail for violation in violations if violation.identity == Identity.BATTING_COLUMN_SUM
        ]
        assert any("walks" in detail for detail in column_sum_details)


class TestLineScoreErrors:
    def test_ignores_errors_because_no_identity_uses_them(self, cubs_at_braves_1968: Direction) -> None:
        # Retrosheet proofs defensive statistics far less closely, and the board shows E only
        # because a line score has an E column. Nothing deduces from it.
        with_absurd_errors = dataclasses.replace(
            cubs_at_braves_1968,
            line_score=dataclasses.replace(cubs_at_braves_1968.line_score, offense_errors=9, defense_errors=9),
        )

        assert find_violations(with_absurd_errors) == ()


class TestLineScoreShape:
    def test_accepts_a_home_team_that_did_not_bat_in_the_ninth(self, cubs_at_braves_1968: Direction) -> None:
        # The home team leading after the top of the ninth does not bat. The line score is then
        # shorter on that side, and the identities must not read the missing half-inning as a zero
        # that breaks a sum.
        walk_off = dataclasses.replace(
            cubs_at_braves_1968,
            line_score=LineScore(
                offense_by_inning=(1, 0, 1, 0, 0, 0, 2, 0, 0),
                defense_by_inning=(0, 0, 0, 0, 0, 0, 0, 0),
                offense_runs=4,
                offense_hits=11,
                offense_errors=0,
                defense_runs=0,
                defense_hits=3,
                defense_errors=0,
            ),
        )

        assert find_violations(walk_off) == ()
