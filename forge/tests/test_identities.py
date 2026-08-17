"""Layer 1 of the correctness guarantee: a boxscore that does not satisfy every identity never
reaches the pool.

These identities are also the constraint system the solver reasons over, so a mistake here
propagates into both the generator and the difficulty measurement.
"""

import dataclasses

import pytest

from boxscore_forge.boxscore import BattingLine, Direction, LineScore, PitchingLine
from boxscore_forge.identities import FAMILY_OF, Family, Identity, find_violations


class TestBalancedBoxscore:
    def test_finds_no_violations_when_the_game_is_real_and_balanced(self, cubs_at_braves_1968: Direction) -> None:
        assert find_violations(cubs_at_braves_1968) == ()


class TestColumnSums:
    @pytest.mark.parametrize(
        "column",
        ["plate_appearances", "at_bats", "runs", "hits", "walks", "strikeouts"],
        ids=lambda column: f"batting-{column}",
    )
    def test_detects_batting_total_that_disagrees_with_its_column(
        self, cubs_at_braves_1968: Direction, column: str
    ) -> None:
        inflated = dataclasses.replace(
            cubs_at_braves_1968.batting_totals, **{column: getattr(cubs_at_braves_1968.batting_totals, column) + 1}
        )

        violations = find_violations(dataclasses.replace(cubs_at_braves_1968, batting_totals=inflated))

        assert Identity.BATTING_COLUMN_SUM in {violation.identity for violation in violations}

    @pytest.mark.parametrize(
        "column",
        ["hit_by_pitch", "sacrifice_flies", "sacrifice_hits", "reached_on_interference"],
        ids=lambda column: f"footnote-{column}",
    )
    def test_detects_footnote_total_that_disagrees_with_its_column(
        self, cubs_at_braves_1968: Direction, column: str
    ) -> None:
        inflated = dataclasses.replace(
            cubs_at_braves_1968.footnote_totals, **{column: getattr(cubs_at_braves_1968.footnote_totals, column) + 1}
        )

        violations = find_violations(dataclasses.replace(cubs_at_braves_1968, footnote_totals=inflated))

        assert Identity.FOOTNOTE_COLUMN_SUM in {violation.identity for violation in violations}

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

        violations = find_violations(dataclasses.replace(cubs_at_braves_1968, pitching_totals=inflated))

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

        violations = find_violations(
            dataclasses.replace(cubs_at_braves_1968, pitching=(moved_row, second), pitching_totals=moved_total)
        )

        identities = {violation.identity for violation in violations}
        assert Identity.CROSS_TEAM_TOTAL in identities
        assert Identity.PITCHING_COLUMN_SUM not in identities


class TestRowIdentity:
    def test_accepts_the_row_whose_sacrifice_hit_makes_it_close(self, cubs_at_braves_1968: Direction) -> None:
        # The leadoff batter has five plate appearances against four at-bats and no walks. Only the
        # sacrifice hit closes that row, and it is the reason the footnote columns exist.
        assert find_violations(cubs_at_braves_1968) == ()

    def test_detects_a_row_whose_footnote_went_missing(self, cubs_at_braves_1968: Direction) -> None:
        without_the_sacrifice = dataclasses.replace(
            cubs_at_braves_1968,
            batter_footnotes=(
                dataclasses.replace(cubs_at_braves_1968.batter_footnotes[0], sacrifice_hits=0),
                *cubs_at_braves_1968.batter_footnotes[1:],
            ),
        )

        violations = find_violations(without_the_sacrifice)

        assert Identity.ROW_PLATE_APPEARANCES in {violation.identity for violation in violations}

    def test_detects_a_row_with_the_wrong_plate_appearance_count(self, cubs_at_braves_1968: Direction) -> None:
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            batting=(
                dataclasses.replace(cubs_at_braves_1968.batting[3], plate_appearances=5),
                *cubs_at_braves_1968.batting[4:],
                *cubs_at_braves_1968.batting[:3],
            ),
        )

        violations = find_violations(broken)

        assert Identity.ROW_PLATE_APPEARANCES in {violation.identity for violation in violations}

    def test_names_which_row_broke(self, cubs_at_braves_1968: Direction) -> None:
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            batter_footnotes=(
                *cubs_at_braves_1968.batter_footnotes[:4],
                dataclasses.replace(cubs_at_braves_1968.batter_footnotes[4], hit_by_pitch=1),
                *cubs_at_braves_1968.batter_footnotes[5:],
            ),
        )

        details = [
            violation.detail
            for violation in find_violations(broken)
            if violation.identity == Identity.ROW_PLATE_APPEARANCES
        ]
        assert any("batting[4]" in detail for detail in details)


class TestGlobalIdentity:
    def test_detects_left_on_base_that_breaks_the_team_count(self, cubs_at_braves_1968: Direction) -> None:
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            team_footnotes=dataclasses.replace(cubs_at_braves_1968.team_footnotes, left_on_base=7),
        )

        violations = find_violations(broken)

        assert Identity.GLOBAL_PLATE_APPEARANCES in {violation.identity for violation in violations}


class TestLineScore:
    def test_detects_offense_innings_that_do_not_sum_to_the_run_total(self, cubs_at_braves_1968: Direction) -> None:
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            line_score=dataclasses.replace(
                cubs_at_braves_1968.line_score, offense_by_inning=(1, 0, 1, 0, 0, 0, 1, 0, 0)
            ),
        )

        assert Identity.LINE_SCORE_RUNS in {violation.identity for violation in find_violations(broken)}

    def test_detects_line_score_hits_that_disagree_with_the_batting_total(self, cubs_at_braves_1968: Direction) -> None:
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            line_score=dataclasses.replace(cubs_at_braves_1968.line_score, offense_hits=10),
        )

        assert Identity.LINE_SCORE_HITS in {violation.identity for violation in find_violations(broken)}


class TestBounds:
    def test_detects_more_hits_than_at_bats(self, cubs_at_braves_1968: Direction) -> None:
        impossible = BattingLine(plate_appearances=1, at_bats=1, runs=0, hits=2, walks=0, strikeouts=0)
        broken = dataclasses.replace(cubs_at_braves_1968, batting=(impossible, *cubs_at_braves_1968.batting[1:]))

        assert Identity.HITS_WITHIN_AT_BATS in {violation.identity for violation in find_violations(broken)}

    def test_detects_at_bats_and_walks_beyond_the_plate_appearances(self, cubs_at_braves_1968: Direction) -> None:
        # The new bound the plate appearance column makes available. It narrows from the opposite
        # side to the row identity: that says what plate appearances add up to, this says what they
        # cannot fall below.
        impossible = BattingLine(plate_appearances=2, at_bats=3, runs=0, hits=0, walks=1, strikeouts=0)
        broken = dataclasses.replace(cubs_at_braves_1968, batting=(impossible, *cubs_at_braves_1968.batting[1:]))

        identities = {violation.identity for violation in find_violations(broken)}
        assert Identity.PLATE_APPEARANCES_COVER_AT_BATS_AND_WALKS in identities

    def test_detects_more_earned_runs_than_runs(self, cubs_at_braves_1968: Direction) -> None:
        impossible = PitchingLine(outs=20, hits=10, runs=1, earned_runs=4, walks=1, strikeouts=3)
        broken = dataclasses.replace(cubs_at_braves_1968, pitching=(impossible, cubs_at_braves_1968.pitching[1]))

        assert Identity.EARNED_RUNS_WITHIN_RUNS in {violation.identity for violation in find_violations(broken)}

    def test_detects_a_negative_value(self, cubs_at_braves_1968: Direction) -> None:
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            team_footnotes=dataclasses.replace(cubs_at_braves_1968.team_footnotes, left_on_base=-1),
        )

        assert Identity.NON_NEGATIVE in {violation.identity for violation in find_violations(broken)}


class TestFamilies:
    def test_every_equality_identity_belongs_to_a_family(self) -> None:
        # The family axis is one of the two things that describe a puzzle's difficulty. An identity
        # missing from the map would silently drop out of that description.
        equalities = {
            Identity.BATTING_COLUMN_SUM,
            Identity.FOOTNOTE_COLUMN_SUM,
            Identity.PITCHING_COLUMN_SUM,
            Identity.CROSS_TEAM_TOTAL,
            Identity.ROW_PLATE_APPEARANCES,
            Identity.GLOBAL_PLATE_APPEARANCES,
            Identity.LINE_SCORE_RUNS,
            Identity.LINE_SCORE_HITS,
        }

        assert equalities <= FAMILY_OF.keys()

    def test_all_four_families_are_represented(self) -> None:
        assert set(FAMILY_OF.values()) == set(Family)


class TestViolationReporting:
    def test_reports_every_broken_identity_rather_than_stopping_at_the_first(
        self, cubs_at_braves_1968: Direction
    ) -> None:
        # A boxscore is discarded, never repaired, so the value of validation is a full picture of
        # what is wrong rather than the first thing found.
        broken = dataclasses.replace(
            cubs_at_braves_1968,
            team_footnotes=dataclasses.replace(cubs_at_braves_1968.team_footnotes, left_on_base=7),
            line_score=dataclasses.replace(cubs_at_braves_1968.line_score, offense_hits=10),
        )

        identities = {violation.identity for violation in find_violations(broken)}

        assert Identity.GLOBAL_PLATE_APPEARANCES in identities
        assert Identity.LINE_SCORE_HITS in identities


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
