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

from dataclasses import dataclass

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from boxscore_forge import produce as producer
from boxscore_forge.boxscore import Direction
from boxscore_forge.pool import Loaded
from boxscore_forge.produce import produce, required_boxscore
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
