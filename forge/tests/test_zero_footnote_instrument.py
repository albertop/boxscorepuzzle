"""The instrument deciding whether erasable footnotes survive, tested before it is believed.

⚠️ **It had no tests, and it is not a formatting script** — it is deciding whether a board feature is
kept or reversed, on an hour of database time. A one-line change could compare different trajectories,
put the zeros in the wrong arm, or move a denominator, and nothing would go red. The scoreboard
instrument's `v19-P1-01` is the same class in the same week: it deleted its own strongest evidence and
no test noticed.

What is tested here is the part that can be wrong without looking wrong: **which cells each arm may
erase**, and **that all three arms walk one order**. The database half is not tested and does not need
to be — it is `load()`, which every other instrument shares.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import cell_values, footnote_cell
from boxscore_forge.erasure import SCOREBOARD_DUPLICATES
from boxscore_forge.identities import FOOTNOTE_COLUMNS

_ROOT = Path(__file__).resolve().parents[2]


def _instrument() -> object:
    for extra in (_ROOT / "discovery" / "difficulty-metrics", _ROOT / "forge" / "src"):
        if str(extra) not in sys.path:
            sys.path.insert(0, str(extra))
    spec = importlib.util.spec_from_file_location(
        "zero_footnotes", _ROOT / "discovery" / "zero-footnotes" / "measure.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def instrument() -> object:
    return _instrument()


class TestEachArmOffersWhatItClaims:
    def test_all_offers_every_footnote_cell(self, instrument: object, cubs_at_braves_1968: Direction) -> None:
        offered = instrument._candidates(cubs_at_braves_1968, "all")
        every = {footnote_cell(i, c) for i in range(len(cubs_at_braves_1968.batting)) for c in FOOTNOTE_COLUMNS}

        assert every <= offered, "the `all` arm is not the world the old figures were measured in"

    def test_non_zero_offers_the_live_terms_and_no_others(
        self, instrument: object, cubs_at_braves_1968: Direction
    ) -> None:
        """⚠️ Stated as the pair it must separate, because inverting this predicate is the single most
        damaging one-character change available and it would still produce a plausible report."""
        values = cell_values(cubs_at_braves_1968)
        offered = instrument._candidates(cubs_at_braves_1968, "non_zero")
        footnotes = {footnote_cell(i, c) for i in range(len(cubs_at_braves_1968.batting)) for c in FOOTNOTE_COLUMNS}

        live = {name for name in footnotes if values[name] != 0}
        zeros = {name for name in footnotes if values[name] == 0}

        assert live, "this board has no live term, so the test proves nothing"
        assert zeros, "this board has no zero, so the test proves nothing"
        assert live <= offered, "a live term was excluded"
        assert not (zeros & offered), f"{len(zeros & offered)} zeros were offered"

    def test_given_offers_no_footnote_cell_at_all(self, instrument: object, cubs_at_braves_1968: Direction) -> None:
        offered = instrument._candidates(cubs_at_braves_1968, "given")

        assert not any(name.startswith("footnotes") for name in offered)

    def test_the_three_arms_are_nested_and_distinct(self, instrument: object, cubs_at_braves_1968: Direction) -> None:
        """`given` ⊂ `non_zero` ⊂ `all`, and none of them equal.

        If two arms came out identical the comparison would report a null it could not have detected —
        an instrument that cannot distinguish, reporting as though it had.
        """
        arms = {arm: instrument._candidates(cubs_at_braves_1968, arm) for arm in instrument.ARMS}

        assert arms["given"] < arms["non_zero"] < arms["all"], (
            f"sizes {[len(arms[a]) for a in instrument.ARMS]} are not strictly nested"
        )

    def test_no_arm_offers_a_scoreboard_duplicate(self, instrument: object, cubs_at_braves_1968: Direction) -> None:
        # The production exclusion has to hold inside the instrument too, or the arms measure a
        # generator nobody ships.
        for arm in instrument.ARMS:
            offered = instrument._candidates(cubs_at_braves_1968, arm)
            assert not (offered & set(SCOREBOARD_DUPLICATES)), f"the {arm} arm offers a scoreboard total"


class TestTheThreeArmsWalkOneOrder:
    def test_a_shared_cell_keeps_its_relative_position_in_every_arm(
        self, instrument: object, cubs_at_braves_1968: Direction
    ) -> None:
        """⚠️ The confound that has no signature in the output.

        If each arm ordered its own candidate list, the arms would differ in *trajectory* as well as in
        *treatment* and the report would read exactly as clean as an honest one. It cannot be checked
        afterwards by reading the numbers — only here, by construction.

        ⚠️ **And this asks the instrument, rather than rebuilding the filtering.** The first version of
        this test constructed the walks itself and passed while the instrument sorted each arm
        separately — a guard that rebuilds what it guards is testing itself.
        """
        walks = instrument.walks(cubs_at_braves_1968, seed=301)

        narrowest = walks["given"]
        for arm, walk in walks.items():
            kept = [cell for cell in walk if cell in set(narrowest)]
            assert kept == narrowest, f"the {arm} arm reorders cells the `given` arm also has"

    def test_the_walk_is_reproducible_and_a_second_seed_measures_something_new(
        self, instrument: object, cubs_at_braves_1968: Direction
    ) -> None:
        # §21's idempotence one level down: the same seed has to give the same experiment, or a rerun is
        # a different experiment wearing the same name.
        again = instrument.walks(cubs_at_braves_1968, seed=301)["all"]
        other = instrument.walks(cubs_at_braves_1968, seed=302)["all"]

        assert again == instrument.walks(cubs_at_braves_1968, seed=301)["all"]
        assert again != other, "two seeds produce one walk, so the second seed measures nothing new"


class TestTheReportKeepsWhatDidNotReach:
    def test_a_target_no_arm_reaches_still_produces_its_rows(
        self, instrument: object, cubs_at_braves_1968: Direction
    ) -> None:
        """⚠️ Failing to reach a target is the strongest evidence an arm can produce.

        The scoreboard instrument dropped those rows and would have summarised the survivors and called
        it a null. Driven here with an eraser that always fails, so the claim is about the instrument's
        row-building rather than about a `Row` constructed by the test.
        """
        rows = instrument._measure(cubs_at_braves_1968, "X", 301, erase=lambda *_, **__: None)

        assert len(rows) == len(instrument.ARMS) * len(instrument.TARGETS), "rows went missing"
        assert all(row.reached is False for row in rows), "a failed erasure was recorded as reached"

    def test_a_reachable_target_is_recorded_as_reached(
        self, instrument: object, cubs_at_braves_1968: Direction
    ) -> None:
        # An instrument that recorded everything as unreached would satisfy the test above.
        rows = instrument._measure(cubs_at_braves_1968, "X", 301)

        assert any(row.reached for row in rows), "no arm reached any target on a real board"
        assert instrument.Row.__slots__, "the result record is not slotted"
