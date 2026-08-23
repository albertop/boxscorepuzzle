"""The parts of the pool that do not need a database.

⚠️⚠️ **These were never measured until 2026-08-22.** The loader lived in `discovery/`, which coverage
does not read, so promoting it into `src/` put ~940 lines under the 95% floor for the first time and the
pre-push hook refused the next push at 92.78%. **The code did not get worse; it started counting.**

⚠️ **`_a_number` is the one that should sting.** It is the guard that stops a non-number reaching a SQL
string, written today — and it was verified by hand in a throwaway script and never turned into a test.
**A check verified once by hand is not a check**, which is the rule this project already records about
guards that cannot fire.

**`load()` is covered too, in `tests/test_pool_loading.py`**, driven off a fake driver rather than
excluded — a blanket pragma was written on it first and reverted, because the line between *needs a
server* and *needs rows* is not *touches the database*. This file is its helpers.
"""

import pytest

from boxscore_domain import ZERO_DENSITY_GATE
from boxscore_forge.pool import (
    _a_number,
    _batting_labels,
    _parse_line_score,
    _pitcher_labels,
    _position,
    _sum,
    team_name,
    zero_density_clause,
)


class TestNumbersThatReachSql:
    """⚠️ `gate` and the roster caps are interpolated into a query. The annotations were the only guard
    and an annotation is not one — every caller is a script."""

    @pytest.mark.parametrize("value", ["0.3", None, [], object()])
    def test_a_value_that_is_not_a_number_is_refused(self, value: object) -> None:
        with pytest.raises(TypeError, match="must be a number"):
            _a_number("gate", value, low=0.0, high=1.0)

    def test_bool_is_refused_although_it_is_an_int(self) -> None:
        # ⚠️ The one that would have slipped through a plain `isinstance(value, int)`: `True` is an int
        # in Python, and `zero_density_clause(True)` would have produced `< True`, which SQL accepts.
        # ⚠️ Bound first because ruff refuses a bare boolean positional — and the rule is right about the
        # general case even though this call is *about* passing a bool.
        truthy: object = True
        with pytest.raises(TypeError, match="bool"):
            _a_number("gate", truthy, low=0.0, high=1.0)

    @pytest.mark.parametrize("value", [-0.1, 1.5, 300])
    def test_a_number_outside_the_range_is_refused(self, value: float) -> None:
        with pytest.raises(ValueError, match="must be between"):
            _a_number("gate", value, low=0.0, high=1.0)

    def test_a_number_in_range_survives_as_a_float(self) -> None:
        assert _a_number("max_batters", 13, low=0, high=100) == 13.0

    def test_the_clause_carries_the_gate_and_no_lint_directive(self) -> None:
        """⚠️ **The gate is imported, and this file spelled it `0.30` until the hook refused the push.**

        `test_constants_are_not_copied.py` caught it — the guard extended earlier the same day to watch
        for exactly this, firing on a file written hours later by the person who extended it. **A value
        that carries a decision has one home**, and a *test* spelling it is the worst copy of all: it
        would keep passing after the decision changed, and assert the old number while doing it.
        """
        clause = zero_density_clause(ZERO_DENSITY_GATE)

        assert clause.strip().endswith(f"< {ZERO_DENSITY_GATE}")
        assert "noqa" not in clause, "a suppression written inside the string would be sent to the server"


class TestTheLineScoreParser:
    """Retrosheet writes a ten-run inning as `(10)` and everything else as one digit."""

    def test_one_digit_per_inning(self) -> None:
        assert _parse_line_score("000102000") == (0, 0, 0, 1, 0, 2, 0, 0, 0)

    def test_a_double_figure_inning_is_bracketed(self) -> None:
        # ⚠️ The case a naive per-character parser turns into a 1 and a 0 — two innings that never
        # happened, and a line score that still sums to something plausible.
        assert _parse_line_score("00(10)3") == (0, 0, 10, 3)

    def test_the_home_half_never_played_is_not_an_inning(self) -> None:
        # `x` marks the ninth a winning home team did not bat. It is not a zero: a zero would say they
        # batted and did not score, which is the distinction the board's `x` exists to keep.
        assert _parse_line_score("10100000x") == (1, 0, 1, 0, 0, 0, 0, 0)

    def test_extra_innings_are_however_many_there_were(self) -> None:
        assert len(_parse_line_score("0000000001000")) == 13


class TestTheRowLabels:
    def test_the_starter_is_sp_and_relievers_are_numbered(self) -> None:
        assert _pitcher_labels([1, 0, 0]) == ("SP", "RP-1", "RP-2")

    def test_a_bare_p_is_never_produced(self) -> None:
        # ⚠️ The pitcher who batted also appears as `P` in the batting section, and one label meaning
        # two things in two sections is worse than no label.
        assert "P" not in _pitcher_labels([1, 0, 0, 0])

    def test_every_pitcher_gets_a_label(self) -> None:
        assert len(_pitcher_labels([1, 0, 0, 0, 0, 0])) == 6

    def test_a_position_the_man_never_occupied_falls_back_to_how_he_arrived(self) -> None:
        assert _position("PH", None, 11, None) == "PH"

    def test_a_designated_hitter_who_started_is_dh(self) -> None:
        assert _position("DH", None, None, 10) == "DH"

    def test_nothing_recorded_at_all_is_a_question_mark(self) -> None:
        # ⚠️ Not an empty label: a blank row label on the board is indistinguishable from a rendering
        # fault, and a `?` says the loader had nothing rather than that the board lost it.
        assert _position("", None, None, None) == "?"

    def test_the_batting_labels_are_the_positions(self) -> None:
        assert _batting_labels(["SS", "CF", "1B"]) == ("SS", "CF", "1B")


class TestTotallingRows:
    def test_columns_are_summed_into_the_same_model(self) -> None:
        class _Line:
            def __init__(self, hits: int, walks: int) -> None:
                self.hits, self.walks = hits, walks

        total = _sum(_Line, (_Line(2, 1), _Line(0, 3)), ("hits", "walks"))

        assert (total.hits, total.walks) == (2, 4)


class _Cursor:
    """The two calls `team_name` makes on a connection, and nothing else."""

    def __init__(self, rows: list[tuple[str, str]]) -> None:
        self._rows, self.queries = rows, 0

    def cursor(self) -> "_Cursor":
        return self

    def execute(self, *_args: object) -> "_Cursor":
        self.queries += 1
        return self

    def fetchall(self) -> list[tuple[str, str]]:
        return self._rows


class TestNamingAClub:
    def test_a_single_match_is_the_club(self) -> None:
        assert team_name(_Cursor([("Boston", "Red Sox")]), {}, "BOS", 1913) == ("Boston", "Red Sox")

    def test_an_ambiguous_or_absent_match_names_nobody(self) -> None:
        # ⚠️ `None` rather than a guess. §7 draws the real boxscore at the end; a club named wrongly
        # there is the mislabelled-team defect, which balances every identity and is still wrong.
        assert team_name(_Cursor([]), {}, "XXX", 1913) is None
        assert team_name(_Cursor([("A", "B"), ("C", "D")]), {}, "XXX", 1913) is None

    def test_a_known_spelling_is_corrected(self) -> None:
        assert team_name(_Cursor([("St.Louis", "Browns")]), {}, "SLA", 1923) == ("St. Louis", "Browns")

    def test_the_cache_spares_the_second_query(self) -> None:
        # A game asks for the same two clubs on every row; without the cache that is two queries a board.
        connection = _Cursor([("Boston", "Red Sox")])
        cache: dict[tuple[str, int], tuple[str, str] | None] = {}
        team_name(connection, cache, "BOS", 1913)
        team_name(connection, cache, "BOS", 1913)

        assert connection.queries == 1
