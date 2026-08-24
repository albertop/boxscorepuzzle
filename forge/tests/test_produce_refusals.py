"""What `produce()` does when it cannot produce, and why the reason matters as much as the refusal.

⚠️ **All three branches here are refusals**, which is the class `CLAUDE.md` says must be exercised: a
check that never fires is indistinguishable from one that is broken. They were the last uncovered lines
in `produce.py` and they are not decoration — **the batch producer counts by cause**, and the two causes
are different populations with different fixes:

- `erasure` — the board could not be reduced to the target. A *pool* problem: the direction is
  unsuitable at that difficulty.
- `certification` — a board was produced and the publication gate refused it. A *validation* problem.

Collapsing them into `None` is what the reference writer did, and it is why nobody knew the yield until
2026-08-22. A run reporting one number cannot tell a pool that yields nothing from one whose boards keep
failing a check.
"""

from dataclasses import dataclass, replace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from boxscore_domain import AUTOMATIC_RUNNER_FROM, MAX_INNINGS
from boxscore_forge import produce as producer
from boxscore_forge.boxscore import Direction
from boxscore_forge.pool import POSTSEASON_SOURCE, Loaded
from boxscore_forge.produce import inadmissible, produce, required_boxscore
from boxscore_forge.publish import to_board
from tests.reveals import reveal_for as fixture_reveal

_GAME, _OFFENSE, _DEFENSE = "SLN19680808", "CHN", "SLN"


def _loaded(direction: Direction) -> Loaded:
    """A `Loaded` as the loader would hand one over, built from the fixture instead of SQL.

    ⚠️ The same construction `test_the_writer_passes_its_own_gate.py` uses. Two copies of *what a loaded
    direction looks like* is a shape this project meets often; they are separate today because that file
    builds one to prove the writer's own gate accepts it and this one to prove `produce()` refuses, and
    unifying them is recorded rather than done in a coverage change.
    """
    labels = ("C",) * len(direction.batting)
    pitcher_labels = ("SP",) * len(direction.pitching)
    board = to_board(direction, None)
    fixture = fixture_reveal(board, labels=labels, pitcher_labels=pitcher_labels, offense=_OFFENSE, defense=_DEFENSE)
    return Loaded(
        game_id=_GAME,
        season=1968,
        direction=direction,
        labels=labels,
        offense_is_home=False,
        names=fixture.batter_names,
        pitcher_labels=pitcher_labels,
        offense_team=_OFFENSE,
        defense_team=_DEFENSE,
        pitcher_names=fixture.pitcher_names,
        source_type="EVN",
        official_hits=board.line_score.offense_hits,
        official_runs=board.line_score.offense_runs,
        official_at_bats=sum(line.at_bats for line in direction.batting),
        official_left_on_base=board.left_on_base,
        slots=tuple(range(1, len(direction.batting) + 1)),
        is_deduced=0,
        # ⚠⚠ **Admissible, and spelled out rather than defaulted.** `Loaded`'s four disposition fields
        # default to the *refusing* values (`docs/excluded-games.md`), so a fixture that omits them is
        # refused as a partial account -- which is the fail-closed direction and the reason the default
        # is what it is. A fixture standing in for a publishable game has to say so.
        account="Y",
        printed=fixture.boxscore,
    )


@dataclass(frozen=True, slots=True)
class _Unprinted:
    """Only the two fields `required_boxscore` reads before refusing."""

    game_id: str = "BOS19750101"
    offense_team: str = "BOS"
    defense_team: str = "OPP"
    printed: object | None = None
    direction: object = None
    slots: tuple[int, ...] = (1, 2, 3)
    labels: tuple[str, ...] = ("SS", "CF")
    pitcher_labels: tuple[str, ...] = ("SP",)
    names: tuple[str, ...] = ("A B",)
    pitcher_names: tuple[str, ...] = ("C D",)
    offense_is_home: bool = False
    season: int = 1975
    source_type: str = "EVN"
    is_deduced: int = 0
    official_at_bats: int = 30
    official_hits: int = 5
    official_runs: int = 3
    official_left_on_base: int = 8


class TestABoardWithNoPrintedBoxscore:
    def test_it_refuses_rather_than_publishing_half_a_reveal(self) -> None:
        # ⚠️ Since schema 5 the reveal prints **both** clubs. A direction whose printed boxscore never
        # arrived cannot make one, and returning `None` here would put an empty reveal in a package that
        # every other check would pass — §7's whole reward, missing, and nothing arithmetic can see it.
        with pytest.raises(SystemExit, match="no printed boxscore"):
            required_boxscore(_Unprinted())  # type: ignore[arg-type]

    def test_the_refusal_names_the_game_and_the_direction(self) -> None:
        # A batch of 150 refusing on one board is useless without knowing which, and a game is two
        # directions — naming the game alone leaves the operator to guess which half failed.
        with pytest.raises(SystemExit) as refusal:
            required_boxscore(_Unprinted(game_id="CLE19220607", offense_team="CLE"))  # type: ignore[arg-type]

        assert "CLE19220607" in str(refusal.value)
        assert "CLE" in str(refusal.value)


class TestTheTwoCauses:
    """⚠️ **A real board, and only the thing under test is faked.**

    The first version of the certification test monkeypatched eight things — the erasure, the id, the
    board, the reveal, the signature, the evidence, the gate and `Package` itself. **That is a test of
    its own stubs.** Here the direction is the 1968 fixture, the erasure runs, a real package is signed,
    and the *only* substitution is `certify_for_publication` — because a gate that refuses is the branch
    with no natural example: across roughly 1,235 real attempts it has refused nothing.
    """

    def test_an_erasure_that_reaches_nothing_is_cause_erasure(self, cubs_at_braves_1968: Direction) -> None:
        # Asking for a target no board reaches is the honest way to produce this: no stub at all.
        attempt = produce(_loaded(cubs_at_braves_1968), 400, Ed25519PrivateKey.generate(), note="test")

        assert attempt.package is None
        assert attempt.cause == "erasure"
        assert attempt.refusals == (), "an erasure failure has no gate refusals to report"

    def test_a_gate_refusal_carries_the_checks_that_refused(
        self, monkeypatch: pytest.MonkeyPatch, cubs_at_braves_1968: Direction
    ) -> None:
        """⚠️ **The refusal strings are the point, not the boolean.** `build_inventory.py` tallies them
        per check, because §22's four layers are only worth what each one individually catches — and
        across roughly 1,235 attempts the gate has refused **nothing**, which is recorded as an open
        question about the gate rather than as a clean bill of health."""
        monkeypatch.setattr(
            producer, "certify_for_publication", lambda *_a, **_k: _Certified(("layer 3: not derivable",))
        )

        attempt = produce(_loaded(cubs_at_braves_1968), 8, Ed25519PrivateKey.generate(), note="test")

        assert attempt.package is None
        assert attempt.cause == "certification"
        assert attempt.refusals == ("layer 3: not derivable",)


@dataclass(frozen=True, slots=True)
class _Certified:
    refusals: tuple[str, ...]
    publishable: bool = False


class TestTheGamesTheBoardCannotHonestlyShow:
    """`inadmissible()`, the register in `docs/excluded-games.md` at the narrowest place.

    ⚠️⚠️ **Every one of these boards balances.** Forfeits, ties and partial accounts were tested through
    `produce()` itself and **published boards §22's four layers accepted** — the layers ask whether the
    numbers agree with each other, and for these games they do. What they describe is a game the board
    cannot honestly show, and what lies is the reveal (§29).

    ⚠️ **The refusal is a named cause, not a boolean**, so a future reader meeting one on a perfect game
    can find out why rather than concluding the check is broken.
    """

    @pytest.mark.parametrize(
        ("field", "value", "cause"),
        [
            ("forfeit", "V", "forfeit"),
            ("forfeit", "T", "forfeit"),
            ("protest", "V", "protest"),
            ("protest", "Y", "protest"),
            ("completed_later", True, "completed later"),
            ("account", "P", "partial account"),
            ("account", "", "partial account"),
            ("account", "N", "partial account"),
        ],
    )
    def test_each_disposition_refuses_with_its_own_cause(
        self, cubs_at_braves_1968: Direction, field: str, value: object, cause: str
    ) -> None:
        loaded = replace(_loaded(cubs_at_braves_1968), **{field: value})

        assert inadmissible(loaded) == cause

    def test_an_ordinary_game_is_admissible(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️ The control. Without it every case above is satisfied by a function that refuses
        everything, which is the shape this project records as a check that cannot distinguish."""
        assert inadmissible(_loaded(cubs_at_braves_1968)) == ""

    def test_the_account_test_is_an_acceptance_not_an_exclusion(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️⚠️ `!= "P"` would admit every code nobody thought of — including the empty one that 297 pool
        games carry — which is the fail-open shape §32 has closed twice. Only `Y` passes."""
        for code in ("P", "N", "D", "", "y", "YES"):
            assert inadmissible(replace(_loaded(cubs_at_braves_1968), account=code)) == "partial account"
        assert inadmissible(replace(_loaded(cubs_at_braves_1968), account="Y")) == ""

    def test_a_tie_is_refused(self, cubs_at_braves_1968: Direction) -> None:
        """The reveal shows a boxscore with no winner, and the share, the streak and the reveal all read
        a game as something somebody won."""
        loaded = _loaded(cubs_at_braves_1968)
        score = loaded.direction.line_score
        tied = replace(
            loaded, direction=replace(loaded.direction, line_score=replace(score, defense_runs=score.offense_runs))
        )

        assert inadmissible(tied) == "tie"

    def test_produce_refuses_before_it_erases(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️⚠️ **The guarantee is here rather than in the query.** The pool excludes these too, but only
        to avoid building what it would discard: a `Loaded` assembled by hand never passed through a
        `WHERE`, and one query's rule is not the next query's."""
        loaded = replace(_loaded(cubs_at_braves_1968), account="P")

        attempt = produce(loaded, 8, Ed25519PrivateKey.generate(), note="test")

        assert attempt.package is None
        assert attempt.cause == "partial account"


class TestTheAutomaticRunnerBoundaryIsSettled:
    """**2020, regular season only, never the postseason. Settled by the operator on 2026-08-24.**

    ⚠️⚠️ **The season is half the rule and the tests are written so half cannot pass for the whole.**
    A floor that refuses every 2020+ extra-inning game has the right number and the wrong rule: it
    would throw away legitimate postseason boards, which have never had a placed runner in any season.
    `test_a_postseason_game_from_the_era_is_admitted` is the assertion that fails if that happens, and
    it is the one worth breaking on purpose — it was verified red by dropping the `source_type` clause
    from `inadmissible`, which reports `automatic runner` on a 2021 World Series board.

    ⚠️ **The exemption is an acceptance test.** A game escapes only by being positively known to be
    postseason; an unrecorded `source_type` is treated as regular season and refused, which is the
    fail-closed direction and the same shape as `account != "Y"`.

    ⚠️ **What this replaces.** The boundary was an open decision and the code raised loudly on any
    extra-inning game from a season nothing had measured. `AUTOMATIC_RUNNER_FLOOR` scoped that raise
    and is deleted with it — the first version of the raise fired on *every* extra-inning game and
    aborted a production run on a **1964** board, which is why the scoping existed at all.
    """

    def _extra_innings(self, direction: Direction, season: int, source_type: str = "EVN") -> Loaded:
        """An extra-inning board in a given season. **`EVN` by default: a regular-season game.**

        The default is the case the rule bites on, so a test asking about the postseason has to say so.
        """
        loaded = replace(_loaded(direction), season=season, source_type=source_type)
        score = loaded.direction.line_score
        longer = replace(
            score,
            offense_by_inning=(*score.offense_by_inning, 0),
            defense_by_inning=(*score.defense_by_inning, 1),
        )
        return replace(loaded, direction=replace(loaded.direction, line_score=longer))

    def test_the_boundary_is_the_season_mlb_introduced_the_rule(self) -> None:
        """⚠️ A rulebook fact, not a measurement: the automatic runner arrived in 2020."""
        assert AUTOMATIC_RUNNER_FROM == 2020

    def test_a_regular_season_game_from_the_era_is_refused(self, cubs_at_braves_1968: Direction) -> None:
        assert inadmissible(self._extra_innings(cubs_at_braves_1968, 2021)) == "automatic runner"

    def test_the_first_season_of_the_rule_is_inside_it(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️ `>=`, not `>`. 2020 is the first season the runner was placed, not the last without one."""
        assert inadmissible(self._extra_innings(cubs_at_braves_1968, AUTOMATIC_RUNNER_FROM)) == "automatic runner"

    def test_the_season_before_it_is_untouched(self, cubs_at_braves_1968: Direction) -> None:
        assert inadmissible(self._extra_innings(cubs_at_braves_1968, AUTOMATIC_RUNNER_FROM - 1)) == ""

    def test_a_postseason_game_from_the_era_is_admitted(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️⚠️ **The half a season floor gets wrong.** The rule has never applied to the postseason.

        Verified red by removing the `source_type` clause from `inadmissible`: this then reports
        `automatic runner` on a 2021 postseason board, which is a good board thrown away.
        """
        assert inadmissible(self._extra_innings(cubs_at_braves_1968, 2021, source_type=POSTSEASON_SOURCE)) == ""

    def test_no_postseason_season_is_touched(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️ *In any season* — so the exemption is asserted well past the boundary, not only beside it."""
        for season in (2020, 2024, 2029):
            board = self._extra_innings(cubs_at_braves_1968, season, source_type=POSTSEASON_SOURCE)
            assert inadmissible(board) == "", f"a {season} postseason board was refused"

    def test_a_game_whose_source_is_unrecorded_is_treated_as_regular_season(
        self, cubs_at_braves_1968: Direction
    ) -> None:
        """⚠️⚠️ **Fail closed.** The exemption needs positive evidence; absence is not the evidence.

        `Loaded.source_type` defaults to `""`, and a board that never learned where it came from must
        not inherit the postseason's exemption by having said nothing.
        """
        assert inadmissible(self._extra_innings(cubs_at_braves_1968, 2021, source_type="")) == "automatic runner"

    def test_a_nine_inning_game_from_the_era_is_untouched(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️ The runner is placed **to start an extra inning**. A regulation game never meets one."""
        assert inadmissible(replace(_loaded(cubs_at_braves_1968), season=2021, source_type="EVN")) == ""

    def test_a_board_past_the_inning_cap_is_refused_before_the_boundary_is_consulted(
        self, cubs_at_braves_1968: Direction
    ) -> None:
        """⚠️ Order matters: §6's cap is a fact about the screen and holds whatever the rulebook says."""
        loaded = self._extra_innings(cubs_at_braves_1968, 1950)
        score = loaded.direction.line_score
        long_game = replace(
            score,
            offense_by_inning=tuple([0] * (MAX_INNINGS + 1)),
            defense_by_inning=tuple([0] * (MAX_INNINGS + 1)),
        )

        assert inadmissible(replace(loaded, direction=replace(loaded.direction, line_score=long_game))) == "innings"
