"""Anything that rebuilds a `Package` carries **every** field, including ones added later.

⚠️ **The defect this exists for.** `offense_is_home` was added to the dataclass, and `sign()` rebuilt the
package from a hand-written list of the fields it knew about — so the signer silently dropped it and the
package that got signed was not the package it was handed. Nothing failed at the boundary, because a
signature over a package missing a field is a perfectly valid signature over a different package.

It is the removed-mechanism defect inverted. That rule says: *when a mechanism is removed, look for who
was reading it.* This is the other direction — **when a field is added, look for who rebuilds the
object** — and a hand-written field list is a copy of the dataclass that nobody updates.

Both rebuilders now use `dataclasses.replace`, which carries fields that do not exist yet. These tests
are derived from `dataclasses.fields`, so a field added tomorrow is covered without anyone remembering.
"""

from dataclasses import fields

import pytest

from boxscore_package.format import LEAKING_METADATA, Board, LineScore, Package
from boxscore_package.signing import sign, signing_key

KEY = signing_key(bytes(range(32)).hex())


@pytest.fixture
def package() -> Package:
    line = LineScore(
        offense_by_inning=(0, 0, 1),
        defense_by_inning=(0, 0, 0),
        offense_runs=1,
        offense_hits=1,
        offense_errors=0,
        defense_runs=0,
        defense_hits=0,
        defense_errors=0,
    )
    board = Board(
        batting=((1, 1, 1, 1, 0, 0),),
        batting_totals=(1, 1, 1, 1, 0, 0),
        footnotes=((0, 0, 0, 0),),
        footnote_totals=(0, 0, 0, 0),
        left_on_base=0,
        pitching=((3, 1, 1, 1, 0, 0),),
        pitching_totals=(3, 1, 1, 1, 0, 0),
        line_score=line,
    )
    return Package(
        puzzle_id="000000000000000f",
        puzzle=board,
        solution=board,
        labels=("CF",),
        pitcher_labels=("SP",),
        slot_references=("1",),
        offense_is_home=True,
        metadata={"seed": 1, "game_id": "SLA191308170"},
    )


def carried(before: Package, after: Package, *, changed: set[str]) -> None:
    """Every field either survives untouched or is one the caller said would change."""
    for field in fields(Package):
        if field.name in changed:
            continue
        assert getattr(after, field.name) == getattr(before, field.name), (
            f"{field.name} did not survive the rebuild; a hand-written field list has gone stale"
        )


class TestSigningChangesTheSignatureAndNothingElse:
    def test_every_other_field_survives(self, package: Package) -> None:
        carried(package, sign(package, KEY), changed={"signature"})

    def test_the_field_the_defect_dropped_is_among_them(self, package: Package) -> None:
        # Named explicitly as well as covered by the sweep: the sweep proves the class is closed, this
        # proves the instance that opened it is closed, and a future reader can see what happened.
        assert sign(package, KEY).offense_is_home is True

    def test_a_signature_over_a_dropped_field_would_still_have_verified(self, package: Package) -> None:
        """⚠️ Why nothing caught it. A signature over a package missing a field is a valid signature —
        over a *different* package. The boundary had nothing to compare against, so the only place this
        could be caught is here, at the rebuild."""
        from dataclasses import replace  # noqa: PLC0415

        without = replace(package, offense_is_home=False)
        assert sign(without, KEY).signature != sign(package, KEY).signature, (
            "two packages differing only in which side batted last produced one signature"
        )


class TestPublishingFiltersMetadataAndNothingElse:
    def test_every_other_field_survives(self, package: Package) -> None:
        carried(package, package.published(), changed={"metadata"})

    def test_the_leaking_keys_go_and_the_rest_stays(self, package: Package) -> None:
        # A rebuilder that dropped everything would satisfy the sweep above by changing nothing it was
        # asked about, so the thing `published` is *for* is asserted separately.
        published = package.published()
        assert set(published.metadata) == set(package.metadata) - LEAKING_METADATA
        assert published.metadata["seed"] == 1


class TestTheSweepWouldNoticeAStaleList:
    def test_a_rebuilder_that_forgets_a_field_is_caught(self, package: Package) -> None:
        """The guard stated as what it forbids.

        A rebuild that drops one field is exactly the shape of the original defect, and `carried` has to
        fail on it — otherwise the sweep is a loop that asserts nothing, which this project has produced
        eight times.
        """
        from dataclasses import replace  # noqa: PLC0415

        forgetful = replace(package, offense_is_home=False)
        with pytest.raises(AssertionError, match="offense_is_home did not survive"):
            carried(package, forgetful, changed={"signature"})

    def test_the_sweep_covers_every_field_the_dataclass_has(self, package: Package) -> None:
        # Derived from `fields`, so a field added tomorrow is covered without anyone remembering to.
        assert {field.name for field in fields(Package)} >= {
            "puzzle_id",
            "puzzle",
            "solution",
            "labels",
            "pitcher_labels",
            "slot_references",
            "offense_is_home",
            "reveal",
            "metadata",
            "schema",
            "signature",
        }
        assert sign(package, KEY) is not package, "sign must not mutate its input"


class TestTheTestTreesOwnRebuilderCarriesEveryFieldToo:
    """⚠️⚠️ This file existed for exactly this defect, and two fresh instances of it stood in the test
    tree the whole time — in the helpers the rule is enforced *from*.

    `conftest.swapped()` and a byte-identical `test_layers.replacing()` each named all eight `Board`
    fields by hand (v36-P3-08). Both are the shape the module docstring above describes, and neither
    was covered, because the sweep looks at `Package` rebuilders in `boxscore_package` and these
    rebuild a `Board` in `forge/tests`.

    **A rule applied outward does not automatically apply inward** — `CLAUDE.md` records that as its
    own failure mode, and this is an instance of it sitting inside the guard written against it.
    """

    def test_a_rebuild_with_nothing_changed_returns_an_equal_board(self, package: Package) -> None:
        """⚠️ The one assertion a hand-written field list fails.

        It cannot fail for a field the list *names*; it fails the moment a field is added to `Board`
        and the list is not updated — which is the failure nobody is present for. Derived from
        `dataclasses.fields` so tomorrow's field is covered without anyone remembering.
        """
        from tests.verify.conftest import swapped  # noqa: PLC0415

        board = package.solution
        rebuilt = swapped(board)

        assert rebuilt == board
        for field in fields(Board):
            assert getattr(rebuilt, field.name) == getattr(board, field.name), (
                f"{field.name} did not survive a rebuild that changed nothing"
            )

    def test_the_rebuilder_changes_what_it_is_asked_to_and_nothing_else(self, package: Package) -> None:
        from tests.verify.conftest import swapped  # noqa: PLC0415

        board = package.solution
        rebuilt = swapped(board, left_on_base=7)

        assert rebuilt.left_on_base == 7
        for field in fields(Board):
            if field.name != "left_on_base":
                assert getattr(rebuilt, field.name) == getattr(board, field.name), f"{field.name} was disturbed"
