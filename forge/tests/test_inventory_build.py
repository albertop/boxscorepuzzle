"""The inventory build never reports a short calendar as a finished one.

⚠️⚠️ **v38-P2-01: it did.** `build()` produced whatever it could, wrote those entries into
`forge/calendar.json`, printed `WARNING: n dates unfilled` and **exited zero** — so a run that filled 130
of 150 dates looked exactly like one that filled all of them. The calendar is the artefact §21 makes
irreproducible and everything downstream reads as serving truth.

⚠️ **The repair is not "refuse to write".** A2.3 requires a run that dies at board 400 of 450 not to
start over, and `extend()` only adds dates with no entry — so a partial batch is **resumable by
construction** and discarding it throws away twenty minutes of signing plus every package on disk. The
boards are kept, the assignments are kept, and the *run* fails.

**No database here.** These drive `build()` with a stubbed loader and producer, because the defect is in
the bookkeeping and a test that needs a DSN is a test that never runs in CI.
"""

import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from itertools import pairwise
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from boxscore_forge.calendar import CalendarError, void
from boxscore_package.format import SCHEMA_VERSION
from boxscore_package.format import pointer as pointer_body

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
_TODAY = date(2026, 9, 1)


def _key() -> object:
    """A throwaway signing pair. ⚠️ The real key never enters a test (§33) and nothing here needs it:
    a signature is verified against the public half of whatever signed it."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: PLC0415

    return Ed25519PrivateKey.generate()


def _generation(tmp_path: Path) -> Path:
    """The one generation directory this run wrote."""
    generations = sorted((tmp_path / "forge" / "inventory").iterdir())
    assert len(generations) == 1, f"expected one generation, found {[g.name for g in generations]}"
    return generations[0]


def _builder() -> ModuleType:
    """Load the script fresh, so patching one test's stubs cannot leak into another."""
    spec = importlib.util.spec_from_file_location("build_inventory", _SCRIPTS / "build_inventory.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_inventory"] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True, slots=True)
class _Loaded:
    game_id: str
    offense_team: str = "CHN"
    season: int = 1951
    """⚠️ The replacement path prints it. A stub that omits a field the real `Loaded` has fails as an
    `AttributeError` in whichever test happens to touch it, which is what happened here."""


@dataclass(frozen=True, slots=True)
class _Package:
    puzzle_id: str


def _stub(builder: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, available: int) -> None:
    """A pool of `available` distinct games per era, each producing a board, and no database.

    ⚠️ The stub honours `window`, because the real `load()` does — a stub that ignored it would let an
    era test pass while the builder drew flat, which is the defect these tests exist for.
    """
    monkeypatch.setattr(builder, "CALENDAR", tmp_path / "calendar.json")
    monkeypatch.setattr(builder, "_ROOT", tmp_path)

    def draw(
        _limit: int, *, window: tuple[int, int] = (1910, 2029), also: tuple[str, ...] = (), **_kwargs: object
    ) -> list[_Loaded]:
        year = window[0] + 1
        # The named games come back as themselves. A stub that ignored `also` would make every restamp
        # look like a game the rules had removed, which is a real refusal wearing a stub's clothes.
        return [_Loaded(game) for game in also] + [_Loaded(f"CHN{year}09{n:04d}") for n in range(available)]

    monkeypatch.setattr(builder, "load", draw)
    monkeypatch.setattr(
        builder,
        "_hardest_target",
        lambda item, _key, counts, _refusals: (counts.update(["published"]), _Package(f"p{item.game_id}"))[1],
    )
    # ⚠⚠ **An admissible package, because `audit()` now reads these back.** A stub writing `{}` would
    # make every board in every test look like one produced before the facts were recorded, and the
    # honest reading of that is a refusal -- so the stub has to write what `produce()` writes.
    #
    # ⚠️⚠️ **And it fell behind anyway, one field later.** `schema` was missing here when the format
    # moved to 6, so `restamp` read every stubbed board as written under an older schema and tried to
    # rebuild boards that were never stale. **The comment above predicted this exact failure and did
    # not prevent it** -- a stub that mirrors a writer is two places holding one shape, and the stub is
    # the half nobody edits when the writer changes.
    #
    # ⚠️ `SCHEMA_VERSION` from the format, never the number: spelling it here is how it falls behind
    # the next time.
    monkeypatch.setattr(
        builder,
        "write_package",
        lambda path, package: path.write_text(
            json.dumps(
                {
                    "puzzle_id": package.puzzle_id,
                    "schema": SCHEMA_VERSION,
                    "metadata": {"target_stalls": 8, **_FACTS},
                }
            ),
            encoding="utf-8",
        ),
    )


_FACTS = {"innings": 9, "account": "Y", "disposition": ""}
"""The admissibility facts `produce()` records on a board that may ship: regulation length, a complete
game account, no administrative disposition."""


"""The admissibility facts `produce()` records on a board that may ship: regulation length, a complete
game account, no administrative disposition."""


class TestTheCalendarIsAuditedAgainstTheRegister:
    """`docs/excluded-games.md` over the **population**, read from disk before the manifest is written.

    ⚠⚠ **The pool's `WHERE` and `produce()`'s refusal leave nothing behind that can be asked
    afterwards.** They stop a game entering; they cannot say whether one already did. A seventeen-inning
    board sat in the published calendar on 2026-11-01, signed and certified, until something happened to
    read it -- so the check that would have caught it is one that asks what is *there*, not one that
    filters what arrives.
    """

    def _built(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, metadata: object) -> Path:
        """Build a clean five-day calendar, then rewrite one board's metadata and audit again."""
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=20)
        builder.build(5, date(2026, 9, 2), _key(), _TODAY)

        calendar = builder.read(builder.CALENDAR)
        entry = calendar[0]
        package = tmp_path / "forge" / "inventory" / entry.assigned / f"{entry.puzzle_id}.json"
        package.write_text(json.dumps({"metadata": metadata}), encoding="utf-8")
        return package

    @pytest.mark.parametrize(
        ("metadata", "expected"),
        [
            ({"innings": 17, "account": "Y", "disposition": ""}, "17 innings"),
            ({"innings": 9, "account": "P", "disposition": ""}, "game account"),
            ({"innings": 9, "account": "Y", "disposition": "forfeited to the visiting team"}, "forfeit"),
            ({}, "no admissibility metadata"),
            ({"innings": 9}, "no admissibility metadata"),
        ],
    )
    def test_an_inadmissible_board_in_the_calendar_refuses_the_build(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, metadata: dict[str, object], expected: str
    ) -> None:
        self._built(monkeypatch, tmp_path, metadata)

        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=20)
        with pytest.raises(SystemExit, match=expected):
            builder.build(5, date(2026, 9, 2), _key(), _TODAY)

    def test_the_audit_refuses_an_extra_inning_board_from_the_automatic_runner_era(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """**The boundary is 2020 and settled**, so this asserts the audit acts on it.

        ⚠️⚠️ **This check is deliberately blunter than `produce()`'s and the difference is recorded
        rather than hidden.** `inadmissible()` exempts the postseason, which never had a placed runner;
        the audit reads a package's metadata and **the metadata does not say whether a game was
        postseason**, so it applies the regular-season rule to everything. That is sound only because
        this producer draws no postseason games at all, and `build_inventory.audit` says so at the line.

        The stub's games are all from 1911, so the boundary is moved down to reach them rather than
        fabricating a 2021 fixture -- the same technique the dormant version used.
        """
        extra = {"innings": 11, "account": "Y", "disposition": ""}
        self._built(monkeypatch, tmp_path, extra)

        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=20)
        assert builder.AUTOMATIC_RUNNER_FROM == 2020

        # 1911 is far below 2020, so the same board passes the audit as it stands.
        builder.build(5, date(2026, 9, 2), _key(), _TODAY)

        monkeypatch.setattr(builder, "AUTOMATIC_RUNNER_FROM", 1900)
        with pytest.raises(SystemExit, match="automatic-runner era"):
            builder.build(5, date(2026, 9, 2), _key(), _TODAY)

    def test_a_calendar_entry_whose_package_is_gone_is_not_read_as_clean(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠⚠ **Nothing else on this path catches it.** With the window already full the build returns
        before it writes a manifest or compares what was written against what was assigned, so a
        calendar entry whose package has been deleted is seen by this check and by nothing else."""
        package = self._built(monkeypatch, tmp_path, {"innings": 9, "account": "Y", "disposition": ""})
        package.unlink()

        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=20)
        with pytest.raises(SystemExit, match="has no package"):
            builder.build(5, date(2026, 9, 2), _key(), _TODAY)


class TestBoardsProducedBeforeTheRulesExisted:
    """`--restamp`: record the admissibility facts on the boards that predate them.

    ⚠⚠ **This is a re-signing pass and it must not become a regeneration.** The board is rebuilt from
    the same game at the same target, compared field by field against the published package, and only
    then written back. §21 calls the calendar irreproducible; a pass that silently wrote a *different*
    board under the same puzzle id would be the quietest possible way to lose it.
    """

    def _stale(self, builder: ModuleType, tmp_path: Path) -> list[Path]:
        """Strip the admissibility facts from every package, as a pre-rules generation has them."""
        stripped = []
        for entry in builder.read(builder.CALENDAR):
            path = tmp_path / "forge" / "inventory" / entry.assigned / f"{entry.puzzle_id}.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["metadata"] = {"target_stalls": 8}
            path.write_text(json.dumps(document), encoding="utf-8")
            stripped.append(path)
        return stripped

    def _restampable(self, builder: ModuleType, monkeypatch: pytest.MonkeyPatch, **extra: object) -> None:
        """Make `write_package` write a document carrying the facts, as the real writer now does."""
        monkeypatch.setattr(
            builder,
            "write_package",
            lambda path, package: path.write_text(
                json.dumps({"puzzle_id": package.puzzle_id, "metadata": {"target_stalls": 8, **_FACTS, **extra}}),
                encoding="utf-8",
            ),
        )

    def _built(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ModuleType:
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=20)
        builder.build(5, date(2026, 9, 2), _key(), _TODAY)
        return builder

    def test_a_clean_inventory_restamps_every_board_and_audits(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        builder = self._built(monkeypatch, tmp_path)
        self._stale(builder, tmp_path)
        self._restampable(builder, monkeypatch)

        builder.restamp(_key())

        for entry in builder.read(builder.CALENDAR):
            path = tmp_path / "forge" / "inventory" / entry.assigned / f"{entry.puzzle_id}.json"
            assert json.loads(path.read_text(encoding="utf-8"))["metadata"]["account"] == "Y"

    def test_a_board_that_comes_back_different_stops_the_run(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠⚠ **The whole reason this is safe.** Without the comparison, a producer that had drifted
        would overwrite every published package with a *near* board and report success."""
        builder = self._built(monkeypatch, tmp_path)
        for path in self._stale(builder, tmp_path):
            document = json.loads(path.read_text(encoding="utf-8"))
            document["solution"] = "what the board used to be"
            path.write_text(json.dumps(document), encoding="utf-8")
        self._restampable(builder, monkeypatch)

        with pytest.raises(SystemExit, match="a different board"):
            builder.restamp(_key())

    def test_a_metadata_change_beyond_the_facts_stops_the_run(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠️ The narrower half, and the one a `!=` over the whole document could not express: the
        three admissibility facts may appear, and **nothing else in `metadata` may move**."""
        builder = self._built(monkeypatch, tmp_path)
        self._stale(builder, tmp_path)
        self._restampable(builder, monkeypatch, target_stalls=11)

        with pytest.raises(SystemExit, match="metadata"):
            builder.restamp(_key())

    def test_a_game_the_rules_now_exclude_names_the_date_to_replace(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠⚠ **The pool refusing to hand a game back is the answer, not a gap.** A board published
        from a forfeit or a partial account simply stops being loadable, and the run must say which date
        needs `--replace` rather than passing over it."""
        builder = self._built(monkeypatch, tmp_path)
        self._stale(builder, tmp_path)
        self._restampable(builder, monkeypatch)
        monkeypatch.setattr(builder, "load", lambda *_a, **_k: [])

        with pytest.raises(SystemExit, match="--replace 2026-09-0"):
            builder.restamp(_key())

    def test_nothing_to_do_is_not_a_failure(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        builder = self._built(monkeypatch, tmp_path)

        builder.restamp(_key())


class TestAGenerationCanBeSignedWithoutProducing:
    """`--republish`, for the run that wrote boards and then failed its audit.

    ⚠️ Not hypothetical: the 2026-08-23 replacement wrote five packages and five calendar entries and
    was then refused because 145 *other* boards carried no admissibility metadata. The generation was
    left on disk with no manifest and no pointers -- servable content nothing points at."""

    def test_it_signs_the_newest_generation_over_the_whole_calendar(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=40)
        builder.build(5, date(2026, 9, 2), _key(), _TODAY)
        builder.replace_dates(["2026-09-03"], _key(), _TODAY)
        newest = sorted((tmp_path / "forge" / "inventory").iterdir())[-1]
        (newest / "manifest.json").unlink()
        for pointer in (newest / "days").iterdir():
            pointer.unlink()

        builder.republish(_key())

        assert (newest / "manifest.json").is_file()
        assert sorted(path.stem for path in (newest / "days").iterdir()) == sorted(
            entry.date for entry in builder.read(builder.CALENDAR)
        )

    def test_the_manifest_does_not_list_itself_when_a_generation_is_signed_twice(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠⚠ **It did, and only on the second write.** `write_manifest` globs `*.json` and
        `manifest.json` matches it, so the signed document listed **`manifest` as a puzzle id**. On a
        first write the file does not exist yet, which is why every test over a fresh directory passed
        and why `--republish` was what produced it.

        ⚠️ A signed claim about the set, wrong about the set, reachable only by running twice.
        """
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=20)
        builder.build(5, date(2026, 9, 2), _key(), _TODAY)

        builder.republish(_key())
        builder.republish(_key())

        for generation in (tmp_path / "forge" / "inventory").iterdir():
            listed = json.loads((generation / "manifest.json").read_text(encoding="utf-8"))["puzzles"]
            assert "manifest" not in listed
            assert sorted(listed) == sorted(path.stem for path in generation.glob("*.json") if path.stem != "manifest")

    def test_it_re_signs_every_generation_not_only_the_newest(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠⚠ A manifest says *this generation is whole*. `--replace` deletes the withdrawn board, so the
        **older** generation is the one whose manifest stops being true — and re-signing only the newest
        would leave that standing."""
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=40)
        builder.build(5, date(2026, 9, 2), _key(), _TODAY)
        first = sorted((tmp_path / "forge" / "inventory").iterdir())[0]
        builder.replace_dates(["2026-09-03"], _key(), _TODAY)
        # The board that lost its date. `replace_dates` leaves the file; withdrawing it is the operator's
        # step, and the manifest is what has to stop naming it.
        assigned = {entry.puzzle_id for entry in builder.read(builder.CALENDAR)}
        withdrawn = next(path for path in first.glob("*.json") if path.stem not in assigned | {"manifest"})
        withdrawn.unlink()

        builder.republish(_key())

        listed = json.loads((first / "manifest.json").read_text(encoding="utf-8"))["puzzles"]
        assert withdrawn.stem not in listed

    def test_it_refuses_rather_than_signing_a_calendar_that_fails_its_audit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠⚠ The ordering `_publish` exists to keep: a manifest is a signed claim that a set is whole,
        so it is never written over a calendar that has just failed."""
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=20)
        builder.build(5, date(2026, 9, 2), _key(), _TODAY)
        entry = builder.read(builder.CALENDAR)[0]
        package = tmp_path / "forge" / "inventory" / entry.assigned / f"{entry.puzzle_id}.json"
        package.write_text(json.dumps({"metadata": {"innings": 17, "account": "Y", "disposition": ""}}), "utf-8")

        with pytest.raises(SystemExit, match="17 innings"):
            builder.republish(_key())


class TestADefectiveFutureDateIsReplaced:
    """§21's *future date, defective puzzle → replace it*, exercised rather than described.

    ⚠⚠ **Five boards needed this on 2026-08-23** — four partial game accounts and one seventeen-inning
    board — and there was no way to do it. The register that says which games may not ship
    (`docs/excluded-games.md`) arrived after 150 dates had been assigned, which is the ordinary case
    rather than an unlucky one: a rule found later applies to inventory built earlier.
    """

    def _built(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ModuleType:
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=40)
        builder.build(5, date(2026, 9, 2), _key(), _TODAY)
        return builder

    def test_the_date_keeps_its_place_and_the_board_changes(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        builder = self._built(monkeypatch, tmp_path)
        before = {entry.date: entry for entry in builder.read(builder.CALENDAR)}

        builder.replace_dates(["2026-09-03"], _key(), _TODAY)

        after = {entry.date: entry for entry in builder.read(builder.CALENDAR)}
        assert set(after) == set(before), "replacing changed which dates are assigned"
        assert after["2026-09-03"].puzzle_id != before["2026-09-03"].puzzle_id
        assert after["2026-09-03"].game_id != before["2026-09-03"].game_id
        untouched = {when: entry for when, entry in after.items() if when != "2026-09-03"}
        assert untouched == {when: entry for when, entry in before.items() if when != "2026-09-03"}

    def test_the_replacement_lives_in_its_own_generation_and_the_pointer_says_so(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠️ The v39-P1-01 shape from the other side: the new pointer must name the **new** generation
        while every other date's still names the old one."""
        builder = self._built(monkeypatch, tmp_path)
        first = builder.read(builder.CALENDAR)[0].assigned

        builder.replace_dates(["2026-09-03"], _key(), _TODAY)

        calendar = {entry.date: entry for entry in builder.read(builder.CALENDAR)}
        second = calendar["2026-09-03"].assigned
        assert second != first
        inventory = tmp_path / "forge" / "inventory"
        assert (inventory / second / f"{calendar['2026-09-03'].puzzle_id}.json").is_file()
        for when, entry in calendar.items():
            pointer = json.loads((inventory / second / "days" / f"{when}.json").read_text(encoding="utf-8"))
            assert pointer["generation"] == entry.assigned
            assert pointer["puzzle_id"] == entry.puzzle_id

    def test_the_withdrawn_game_cannot_come_back(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """⚠⚠ **The guarantee is upstream, and this asserts the seam rather than the outcome.**

        A withdrawn board is withdrawn for a reason the calendar knows nothing about, and `replace()`
        deliberately returns the game to the pool. So what stops it being drawn again on the next line is
        `produce()` refusing it — and a replacement that quietly re-published the same game would look
        exactly like a successful one.
        """
        builder = self._built(monkeypatch, tmp_path)
        going = {entry.date: entry for entry in builder.read(builder.CALENDAR)}["2026-09-03"]
        refused = going.game_id
        real = builder._hardest_target
        monkeypatch.setattr(
            builder,
            "_hardest_target",
            lambda item, key, counts, refusals: None if item.game_id == refused else real(item, key, counts, refusals),
        )

        builder.replace_dates(["2026-09-03"], _key(), _TODAY)

        calendar = {entry.date: entry for entry in builder.read(builder.CALENDAR)}
        assert calendar["2026-09-03"].game_id != refused

    def test_a_date_with_no_assignment_is_refused(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        builder = self._built(monkeypatch, tmp_path)

        with pytest.raises(SystemExit, match="nothing to replace"):
            builder.replace_dates(["2026-12-25"], _key(), _TODAY)

    def test_a_date_that_has_been_played_is_refused(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """§21's other half. The refusal comes from `calendar.replace()`, and this asserts that the
        script reaches it rather than screening it off with a check of its own."""
        builder = self._built(monkeypatch, tmp_path)

        with pytest.raises(CalendarError, match="2026-09-03"):
            builder.replace_dates(["2026-09-03"], _key(), date(2026, 9, 20))

    def test_a_pool_with_nothing_to_offer_fails_loudly(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """⚠️ A replacement that found nothing must not leave the defective board in place and exit
        zero — the shape v38-P2-01 closed for a short build."""
        builder = self._built(monkeypatch, tmp_path)
        monkeypatch.setattr(builder, "_hardest_target", lambda *_a: None)

        with pytest.raises(SystemExit, match="none produced a board"):
            builder.replace_dates(["2026-09-03"], _key(), _TODAY)


class TestAShortRunIsAFailure:
    def test_a_full_run_writes_every_date_and_returns(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # ⚠️ The control. Without it, the refusal below is consistent with a build that never succeeds.
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=20)

        builder.build(10, date(2026, 9, 2), _key(), _TODAY)

        assert len(builder.read(builder.CALENDAR)) == 10

    def test_a_short_run_raises_rather_than_warning(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=4)

        with pytest.raises(SystemExit, match="unfilled"):
            builder.build(10, date(2026, 9, 2), _key(), _TODAY)

    def test_a_short_run_still_keeps_the_boards_it_made(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # ⚠️⚠️ **The half that "treat a short build as failure before writing" would have broken.**
        # A2.3: a run that dies at board 400 of 450 must not start over. The failure is the exit code,
        # not the loss of the work.
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=4)

        with pytest.raises(SystemExit):
            builder.build(10, date(2026, 9, 2), _key(), _TODAY)

        assert len(builder.read(builder.CALENDAR)) == 4, "the partial batch was discarded"

    def test_re_running_fills_the_gap_the_short_run_left(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # The claim the refusal message makes, asserted rather than promised: *re-running fills the gaps*.
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=4)
        with pytest.raises(SystemExit):
            builder.build(10, date(2026, 9, 2), _key(), _TODAY)

        _stub(builder, monkeypatch, tmp_path, available=20)
        builder.build(10, date(2026, 9, 2), _key(), _TODAY)

        assert len(builder.read(builder.CALENDAR)) == 10


class TestTheWindowIsIdempotent:
    """⚠️ `--days N --from D` means *those N days are covered*, not *add N more*.

    Found by the re-run test above, which expected 10 and got 14: the first reading filled the next `N`
    **unassigned** dates, so a short run followed by a retry overshot — and the retry is exactly what the
    runbook tells the operator to do. §21 wants the same call safe twice; a window makes that exact.
    """

    def test_a_second_full_run_over_the_same_window_adds_nothing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=40)
        builder.build(10, date(2026, 9, 2), _key(), _TODAY)

        builder.build(10, date(2026, 9, 2), _key(), _TODAY)

        assert len(builder.read(builder.CALENDAR)) == 10

    def test_a_later_window_extends_rather_than_overlapping(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=40)
        builder.build(10, date(2026, 9, 2), _key(), _TODAY)

        builder.build(10, date(2026, 9, 12), _key(), _TODAY)

        assert len(builder.read(builder.CALENDAR)) == 20


class TestTheDrawIsAFloorAndNotARounding:
    @pytest.mark.parametrize(("days", "expected"), [(150, 15), (149, 15), (12, 2), (1, 1)])
    def test_the_margin_never_rounds_below_itself(self, days: int, expected: int) -> None:
        """⚠️⚠️ **This asserted `ceil(days * DRAW_MARGIN / 12)` and could not fail.**

        It recomputed the answer in the assertion, so it was testing `math.ceil` — with `round()` still
        in the builder it passed. **The instrument was supplying the property under test**, which
        `CLAUDE.md` records as the failure that survives a full pass of checks. Found by mutating `ceil`
        back to `round` and watching nothing turn red; the fix was to give the builder a function worth
        calling.
        """
        builder = _builder()

        assert builder.draw_size(days) == expected


class TestItRefusesToTouchThePast:
    def test_a_first_date_at_or_before_today_is_refused(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # §21: the calendar extends and never rewrites, and the boundary is *today* rather than *played*.
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=20)

        with pytest.raises(SystemExit, match="extends and never rewrites"):
            builder.build(10, _TODAY, _key(), _TODAY)


class TestTheEraQuotaIsSampledRatherThanHoped:
    """⚠️⚠️ The first 150-board calendar was **34% pre-1950 against a 5% ceiling**, because `load()`
    draws *n per decade* over twelve decades and four of them are before 1950. **A flat draw cannot
    satisfy a weighted quota except by accident.**"""

    def test_the_calendar_stays_within_the_ceiling(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=200)

        builder.build(100, date(2026, 9, 2), _key(), _TODAY)

        cal = builder.read(builder.CALENDAR)
        pre = [e for e in cal if int(e.game_id[3:7]) < builder.DIVIDE]
        allowed, _rest = builder.era_quota(len(cal))
        assert len(pre) <= allowed, f"{len(pre)} pre-1950 of {len(cal)}, ceiling {allowed}"

    def test_the_quota_is_a_ceiling_and_never_rounds_up(self) -> None:
        builder = _builder()

        assert builder.era_quota(150) == (7, 143), "150 * 5% is 7.5; a ceiling floors it"
        assert builder.era_quota(19) == (0, 19), "under twenty days there is no room for one"

    def test_the_pre_war_boards_are_spread_rather_than_bunched(self) -> None:
        # ⚠️⚠️ **Counting is not placing.** §6 asks for one every three weeks so Ruth is an event; seven
        # on seven consecutive days meets the count and defeats the intent, and a quota implemented as a
        # tally would have passed its own assertion.
        builder = _builder()
        slots = sorted(builder.spread(150, 7))

        gaps = [b - a for a, b in pairwise(slots)]
        assert min(gaps) >= 20, f"pre-1950 boards land {min(gaps)} days apart: {slots}"

    def test_the_audit_refuses_a_calendar_over_the_ceiling(self) -> None:
        # A3.5: asserted after construction, never printed and believed. The run that produced the 34%
        # calendar reported `assigned 150 of 150` and was right about the count.
        builder = _builder()
        over = tuple(
            builder.Entry(f"2026-09-{n + 1:02d}", f"p{n}", f"CHN1913{n:04d}", "CHN", "active", "gen1")
            for n in range(20)
        )

        with pytest.raises(SystemExit, match="pre-1950"):
            builder.audit(over)

    def test_the_audit_refuses_a_repeated_game(self) -> None:
        builder = _builder()
        twice = (
            builder.Entry("2026-09-01", "pa", "CHN19800001", "CHN", "active", "gen1"),
            builder.Entry("2026-09-02", "pb", "CHN19800001", "SLN", "active", "gen1"),
        )

        with pytest.raises(SystemExit, match="repeated"):
            builder.audit(twice)

    @staticmethod
    def _draws(builder: ModuleType, monkeypatch: pytest.MonkeyPatch, *, early: int, modern: int) -> None:
        """A pool with a different depth on each side of 1950, and **no game repeated between calls.**

        ⚠️ The default stub returns the same ids every time, so a second pass would find every one of
        them already spent and fill nothing — the run would be short forever and the test would be
        measuring the stub. Each call gets its own block of ids.
        """
        call = iter(range(1, 1000))

        def draw(_limit: int, *, window: tuple[int, int] = (1910, 2029), **_kwargs: object) -> list[_Loaded]:
            block = next(call) * 1000
            year = window[0] + 1
            count = early if window[0] < builder.DIVIDE else modern
            return [_Loaded(f"CHN{year}09{block + n:04d}") for n in range(count)]

        monkeypatch.setattr(builder, "load", draw)

    def test_a_retry_does_not_grant_itself_a_second_historical_allowance(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠️⚠️ v39-P1-02. The quota was computed from the *gaps* rather than from the window.

        So the runbook's own recovery path — *re-run it if it comes up short* — was the way to exceed
        §6's ceiling: a window that had already spent its full early allowance got a fresh
        `floor(remaining * 5%)` on the retry. And the audit could not see it, because it reads the whole
        calendar: an older window with unused allowance leaves room for a malformed one to pass, and
        `_fill` has written every assignment to disk by the time it runs.

        The first pass here spends the whole historical allowance and comes up short on the modern arm,
        which is exactly the shape the runbook tells the operator to re-run. The retry must add **no**
        further pre-1950 boards.
        """
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=40)
        self._draws(builder, monkeypatch, early=40, modern=20)

        with pytest.raises(SystemExit):
            builder.build(150, date(2026, 9, 2), _key(), _TODAY)
        first = builder.read(builder.CALENDAR)
        allowed, _rest = builder.era_quota(150)
        spent = [entry for entry in first if builder._is_early(entry)]
        assert len(spent) == allowed, f"the premise is wrong: the first pass spent {len(spent)} of {allowed}"
        assert len(first) < 150, "the premise is wrong: the first pass was not short"

        with pytest.raises(SystemExit):
            builder.build(150, date(2026, 9, 2), _key(), _TODAY)

        after = [entry for entry in builder.read(builder.CALENDAR) if builder._is_early(entry)]
        assert len(after) == allowed, (
            f"the retry took the window from {len(spent)} pre-1950 boards to {len(after)}, "
            f"against §6's ceiling of {allowed}"
        )

    def test_the_historical_slots_keep_their_original_offsets_across_a_retry(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠️ The other half of v39-P1-02, and the one the ceiling cannot see.

        Spacing computed over the gaps moves with them, so boards meant to arrive three weeks apart can
        end up next to each other while the count stays perfectly legal. **Counting is not placing** —
        which is why `spread()` exists at all.
        """
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=40)
        # ⚠️ **The same shape as the test above, deliberately.** An earlier version of this used a deep
        # modern pool, and under the original defect it produced *four* early boards, perfectly spaced —
        # so it passed against the code it was written to catch. **A test that cannot fail is the same
        # defect as a check that never fires**, and the scenario is what decides which it is: bunching
        # needs a retry whose first gap sits next to a slot the previous pass already filled.
        self._draws(builder, monkeypatch, early=40, modern=20)

        with pytest.raises(SystemExit):
            builder.build(150, date(2026, 9, 2), _key(), _TODAY)
        with pytest.raises(SystemExit):
            builder.build(150, date(2026, 9, 2), _key(), _TODAY)

        cal = builder.read(builder.CALENDAR)
        early = sorted(date.fromisoformat(entry.date) for entry in cal if builder._is_early(entry))
        gaps = [(after - before).days for before, after in pairwise(early)]
        assert gaps and all(gap >= builder.MINIMUM_EARLY_GAP for gap in gaps), (
            f"pre-1950 boards landed {gaps} days apart; §6 asks for one every three weeks"
        )

    def test_an_overlapping_window_counts_the_early_boards_already_inside_it(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠️⚠️ The half of the era plan the retry tests cannot reach, and it needed its own case.

        A retry over the *same* window is protected by the planned offsets alone: the slots the first
        pass filled are no longer gaps, so a second allowance has nowhere to go. Mutating the
        reconciliation away therefore changed nothing there — **a guard defended by its neighbour is
        indistinguishable from one that does nothing**, which is this project's named shape.

        An **overlapping** window is where it is load-bearing. A top-up starting inside an existing
        window computes its own planned offsets, and the early boards already sitting in the overlap are
        at none of them. Without subtracting what the window already holds, the second build adds its
        full allowance on top of theirs — and the audit reads the whole calendar, so an under-filled
        stretch elsewhere leaves room for the overlap to pass.
        """
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=40)
        self._draws(builder, monkeypatch, early=40, modern=20)

        with pytest.raises(SystemExit):
            builder.build(150, date(2026, 9, 2), _key(), _TODAY)

        # ⚠️ **Shifted by a week, not by half the window.** A window that overlaps almost entirely has
        # almost no gaps, so it has almost no open planned slots and the cap never binds — an earlier
        # version of this case was exactly that, and it passed with the reconciliation removed. What
        # makes the cap load-bearing is a window holding several early boards *and* several open slots.
        shifted = date(2026, 9, 9)
        overlap = {(shifted + timedelta(days=offset)).isoformat() for offset in range(150)}
        inside = [
            entry for entry in builder.read(builder.CALENDAR) if builder._is_early(entry) and entry.date in overlap
        ]
        allowed, _rest = builder.era_quota(150)
        assert len(inside) >= allowed - 1, f"the premise is wrong: only {len(inside)} early boards in the overlap"

        with pytest.raises(SystemExit):
            builder.build(150, shifted, _key(), _TODAY)

        after = [
            entry for entry in builder.read(builder.CALENDAR) if builder._is_early(entry) and entry.date in overlap
        ]
        assert len(after) <= allowed, (
            f"the 150 days from {shifted} hold {len(after)} pre-1950 boards against a ceiling of "
            f"{allowed}; {len(inside)} of them were already there before the top-up ran"
        )

    def test_the_audit_refuses_bunched_historical_boards(self) -> None:
        """⚠️⚠️ The count had an assertion and the placement did not.

        Seven early boards on seven consecutive days meet the ceiling and defeat exactly what it is for.
        This is the audit's own rule — any composition property the pipeline cannot see needs an
        assertion here — turned on the one property it was missing.
        """
        builder = _builder()
        bunched = tuple(
            builder.Entry(
                date=f"2026-09-{day:02d}",
                puzzle_id=f"p{day}",
                # Two adjacent pre-1950 boards among enough modern ones to stay under the ceiling.
                game_id=f"CHN{1930 if day < 3 else 1990}09{day:04d}",
                direction="CHN",
                status="active",
                assigned="gen1",
            )
            for day in range(1, 31)
        )

        with pytest.raises(SystemExit, match="closer than"):
            builder.audit(bunched)


class TestTheCalendarIsCheckpointed:
    def test_a_crash_midway_keeps_the_assignments_already_made(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠️⚠️ **A2.3.** The calendar was written once after the loop, so a crash at board 140 of 150
        left 140 signed packages and **lost every assignment** — the work survived and the record of it
        did not. The short-run case working was a different thing, and a successful run hid the gap."""
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=200)
        real = builder._hardest_target
        made = {"n": 0}

        def explode(*args: object, **kwargs: object) -> object:
            made["n"] += 1
            if made["n"] > 3:
                raise KeyboardInterrupt
            return real(*args, **kwargs)

        monkeypatch.setattr(builder, "_hardest_target", explode)
        with pytest.raises(KeyboardInterrupt):
            builder.build(10, date(2026, 9, 2), _key(), _TODAY)

        assert len(builder.read(builder.CALENDAR)) == 3, "the crash lost assignments already made"


class TestItIsDeterministic:
    def test_the_same_game_yields_the_same_puzzle_id_twice(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠️ **A2.4, §21's double idempotence, asserted rather than trusted.** The rule is that a
        puzzle id derives from the game and never from the date or the run — so the same slice built
        into two different calendars must produce the same ids, in the same order."""
        first, second = tmp_path / "a", tmp_path / "b"
        got = []
        for where in (first, second):
            where.mkdir()
            builder = _builder()
            _stub(builder, monkeypatch, tmp_path, available=20)
            monkeypatch.setattr(builder, "CALENDAR", where / "calendar.json")
            monkeypatch.setattr(builder, "_ROOT", where)
            builder.build(5, date(2026, 9, 2), _key(), _TODAY)
            got.append([e.puzzle_id for e in builder.read(builder.CALENDAR)])

        assert got[0] == got[1], "the same games produced different puzzle ids on a second run"


class TestWhatTheClientMaySee:
    """⚠️⚠️ **A4.2.** `manifest.json` listed every published puzzle, was public and never cached. With
    six reference packages that was harmless; **with a calendar behind it, listing tomorrow's id hands
    out tomorrow's puzzle.**

    The split is in `docs/calendar.md`: the manifest says *this generation is whole* and is read by
    `serve`, never the browser; a **signed pointer per date** says *this id is this date's*, which is the
    one guarantee the client needs. Dropping the list without the pointers would have left a swapped but
    genuine package undetectable — `sign_manifest`'s own docstring says only the manifest proves the set.
    """

    def test_every_active_date_gets_a_signed_pointer(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=40)
        builder.build(10, date(2026, 9, 2), _key(), _TODAY)

        cal = builder.read(builder.CALENDAR)
        days = _generation(tmp_path) / builder.DAYS
        for entry in cal:
            pointer = json.loads((days / f"{entry.date}.json").read_text(encoding="utf-8"))
            assert pointer["puzzle_id"] == entry.puzzle_id
            assert pointer["signature"], "a pointer without a signature proves nothing about the pairing"

    def test_a_pointer_carries_one_date_and_never_a_list(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # ⚠️ The whole point. A pointer that grew a `puzzles` array would be the manifest again, served
        # to the browser, with the leak restored and nothing to notice it.
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=40)
        builder.build(10, date(2026, 9, 2), _key(), _TODAY)

        days = _generation(tmp_path) / builder.DAYS
        pointer = json.loads(next(days.glob("*.json")).read_text(encoding="utf-8"))

        # ⚠️⚠️ **Named against `format.pointer` rather than spelled again**, and the spelled version is
        # what fired when `next_rotation` arrived. That firing was correct -- this is the leak guard and
        # a new field is exactly what it must notice -- but a hand-written set means every legitimate
        # addition edits a test that then asserts nothing it did not already know. Taking the expected
        # keys from the one place the body is built keeps the assertion about *the pointer not growing a
        # list*, which is what it is for, while the signature is the only thing the writer adds.
        assert set(pointer) == set(pointer_body(day="2026-09-02", puzzle_id="x", generation="y", offset_hours=-8)) | {
            "signature"
        }
        # ⚠️ And the half that a derived set cannot carry: whatever the fields are, none of them is a
        # collection. A pointer that grew a `puzzles` array would be the manifest again, served to the
        # browser, with the leak restored and nothing to notice it.
        for name, value in pointer.items():
            assert not isinstance(value, (list, dict)), f"{name} is a collection; a pointer names one day"

    def test_a_pointer_names_the_generation_that_owns_its_package(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠️⚠️ v39-P1-01. The whole calendar was stamped with the generation currently being written.

        A top-up therefore rewrote generation-A dates claiming their packages lived in B, and
        `genB/<old-id>.json` does not exist — the second run only produced the second run's boards. The
        runbook says several generations after a top-up are normal, so this was the *second* run rather
        than an edge case, and the signature made the wrong pairing read as authoritative.
        """
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=40)
        # ⚠️ **A clock this test moves**, because the generation directory is named by the second and two
        # builds this fast share one — which would make the premise below false and the test vacuous.
        ticks = iter([1_700_000_000, 1_700_000_060])
        monkeypatch.setattr(builder, "time", SimpleNamespace(time=lambda: next(ticks), monotonic=lambda: 0.0))
        builder.build(10, date(2026, 9, 2), _key(), _TODAY)
        builder.build(10, date(2026, 9, 12), _key(), _TODAY)

        generations = sorted((tmp_path / "forge" / "inventory").iterdir())
        assert len(generations) == 2, f"the premise of this test is wrong: {[g.name for g in generations]}"
        cal = builder.read(builder.CALENDAR)
        assert len({entry.assigned for entry in cal}) == 2, "both windows landed in one generation"

        # ⚠️⚠️ **The newest generation, and only it, holds a complete schedule** — an older one was
        # written before the later dates existed and has no pointer for them. That is what makes the
        # newest generation the rotation's source, and it is why a stale pointer tree cannot be used.
        newest = generations[-1]
        for entry in cal:
            pointer = json.loads((newest / builder.DAYS / f"{entry.date}.json").read_text(encoding="utf-8"))
            assert pointer["generation"] == entry.assigned, (
                f"{entry.date} points at {pointer['generation']} and its package was made in {entry.assigned}"
            )
            # ⚠️ The property the pointer exists for, not only the field it carries: the file it names
            # has to be there. A pointer that resolves to nothing is a 404 on a legitimately assigned date.
            package = tmp_path / "forge" / "inventory" / pointer["generation"] / f"{pointer['puzzle_id']}.json"
            assert package.exists(), f"{entry.date} points at {package}, which does not exist"

    def test_a_voided_date_gets_no_pointer(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # There is nothing to serve on a date whose puzzle was withdrawn, and writing one would make a
        # withdrawn assignment fetchable.
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=40)
        builder.build(10, date(2026, 9, 2), _key(), _TODAY)
        cal = builder.read(builder.CALENDAR)
        gone = cal[0].date

        # ⚠️ `void` comes from the calendar module, not through the script. Importing it into
        # `build_inventory` so a test could reach it would put a name in production code whose only
        # caller is a test — and ruff would call it unused, correctly.
        builder.write_pointers(void(cal, gone), _generation(tmp_path), _key())

        assert not (_generation(tmp_path) / builder.DAYS / f"{gone}.json").exists()

    def test_the_manifest_is_read_from_disk_and_not_from_the_calendar(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠️ Built from the files present, deliberately. The calendar says what was *assigned* and the
        manifest says what was *written*; generating both from one list would make them agree by
        construction and check nothing about the deployment."""
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=40)
        builder.build(10, date(2026, 9, 2), _key(), _TODAY)
        out = _generation(tmp_path)
        (out / "an-extra-package.json").write_text("{}", encoding="utf-8")

        builder.write_manifest("gen", out, _key())

        listed = json.loads((out / "manifest.json").read_text(encoding="utf-8"))["puzzles"]
        assert "an-extra-package" in listed, "the manifest describes the calendar rather than the disk"

    def test_the_manifest_never_carries_a_date(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # ⚠️ The manifest is the generation's integrity record. A date in it would make the *file the
        # browser must not read* the only place the schedule lives, which is the leak wearing a new hat.
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=40)
        builder.build(10, date(2026, 9, 2), _key(), _TODAY)

        text = (_generation(tmp_path) / "manifest.json").read_text(encoding="utf-8")
        for entry in builder.read(builder.CALENDAR):
            assert entry.date not in text, f"{entry.date} is in the manifest"


class TestWhichDateIsBeingServed:
    """⚠️⚠️ The clock that defines the day, decided 2026-08-23 in `docs/calendar.md`.

    §21 freezes any date at or before today, so this boundary decides whether a puzzle already in front
    of players can be replaced. It was `date.today()` — **the local day of whoever ran the build** — and
    it was safe only because the machine happened to be east of UTC-8, so the boundary was always
    *ahead* of the serving day. **That is a fact about where the operator is sitting, not a guarantee**,
    and every case below fails on the old code from somewhere on earth while passing from Spain.
    """

    def test_the_day_rolls_at_eight_in_the_morning_utc(self) -> None:
        builder = _builder()

        just_before = datetime(2026, 8, 23, 7, 59, tzinfo=UTC)
        just_after = datetime(2026, 8, 23, 8, 0, tzinfo=UTC)

        assert builder.serving_date(just_before) == date(2026, 8, 22)
        assert builder.serving_date(just_after) == date(2026, 8, 23)

    def test_it_is_the_same_answer_everywhere_on_earth(self) -> None:
        # ⚠️ The whole point of a single clock: the instant decides, not the observer. `CLAUDE.md` —
        # everyone gets the same puzzle on the same date.
        moment = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)

        builder = _builder()
        answers = {
            builder.serving_date(moment.astimezone(timezone(timedelta(hours=offset))))
            for offset in (-11, -8, -5, 0, 2, 9, 14)
        }

        assert answers == {date(2026, 8, 23)}, f"the serving date depends on who is asking: {answers}"

    def test_a_west_coast_evening_is_not_already_tomorrow(self) -> None:
        """⚠️⚠️ The case the old code got wrong, and it needs a laptop outside Spain to see.

        23:00 in Los Angeles on the 23rd is 06:00 UTC on the 24th. `date.today()` there answers **the
        24th**, so a build would have treated the 24th as frozen — while the server is still serving the
        23rd, and the 24th is a future date somebody may still need to replace. The boundary was behind
        the truth in one direction and ahead of it in the other, depending on the operator's longitude.
        """
        builder = _builder()
        pacific_evening = datetime(2026, 8, 24, 6, 0, tzinfo=UTC)

        assert builder.serving_date(pacific_evening) == date(2026, 8, 23)
        # The local calendar there says the 23rd too; it is UTC that has moved on. Both agree, and the
        # old code agreed with neither because it read the machine's zone rather than the rule.
        assert pacific_evening.astimezone(timezone(timedelta(hours=-7))).date() == date(2026, 8, 23)

    def test_a_datetime_naming_no_zone_is_refused(self) -> None:
        # ⚠️ Fail closed. A naive datetime means *whatever zone this machine is in*, which is the exact
        # ambiguity this function exists to remove — assuming one would put the operator's longitude
        # back into the answer through a different door.
        builder = _builder()

        with pytest.raises(ValueError, match="names no zone"):
            builder.serving_date(datetime(2026, 8, 23, 12, 0))  # noqa: DTZ001 - the point of the case

    def test_the_offset_matches_the_document_that_owns_it(self) -> None:
        """⚠⚠ **Against `docs/calendar.md`, not against a literal — and it was a literal.**

        This read `== -8`, which is a **third copy of the number** wearing the clothes of a check. The
        rule is shared by *pointing at a document* because §33 forbids the trees sharing code and `forge`
        must never reach the VPS at all; a pointer that is really a copy makes the arrangement read as
        covered while adding one more place to drift.

        `publish` asserts the same line. ⬜ **`serve` will spell it a third time when E1 builds the
        loader, and owes the same assertion** — recorded in the plan at E1.2, because a shared-by-pointing
        rule with two of three pointers is worse than three honest copies.
        """
        builder = _builder()
        calendar = _SCRIPTS.parents[1] / "docs" / "calendar.md"
        stated = re.search(r"ROLLOVER_OFFSET_HOURS = (-?\d+)", calendar.read_text(encoding="utf-8"))

        assert stated, "docs/calendar.md no longer states ROLLOVER_OFFSET_HOURS, which the trees point at"
        assert int(stated[1]) == builder.ROLLOVER_OFFSET_HOURS

    def test_the_function_uses_the_constant_rather_than_a_literal(self) -> None:
        # ⚠️ The other half, and the reason the case above is not a tautology: a hardcoded 8 inside
        # `serving_date` would leave the constant correct and unread.
        builder = _builder()
        moment = datetime(2026, 8, 23, 8, 0, tzinfo=UTC)
        shifted = moment - timedelta(hours=builder.ROLLOVER_OFFSET_HOURS)

        assert builder.serving_date(moment) == date(2026, 8, 23)
        assert builder.serving_date(shifted - timedelta(minutes=1)) == date(2026, 8, 23)

        moment = datetime(2026, 8, 23, 8, 0, tzinfo=UTC)
        shifted = moment - timedelta(hours=builder.ROLLOVER_OFFSET_HOURS)

        assert builder.serving_date(moment) == date(2026, 8, 23)
        assert builder.serving_date(shifted - timedelta(minutes=1)) == date(2026, 8, 23)

    def test_it_takes_the_clock_as_an_argument_so_this_suite_is_not_about_today(self) -> None:
        # ⚠️ A function reading the wall clock can only be tested against the day the suite runs, which
        # is a test that reports the environment — the same shape as the timezone case in the browser
        # suite. The default exists for `main()`; every case here supplies the instant.
        builder = _builder()

        assert isinstance(builder.serving_date(), date)

    def test_nothing_in_the_script_asks_the_machine_what_day_it_is(self) -> None:
        """⚠️⚠️ The wiring, which the cases above cannot reach.

        Every one of them calls `serving_date()` directly, so all of them stay green while `main()` goes
        back to `date.today()` — and `main()` is where the defect actually was. A mutation run showed
        exactly that: three caught, and the one that reintroduces the bug survived.

        ⚠️ **An AST walk, not a regular expression.** This project has twice been bitten by a pattern
        matching the tail of another name — `sign(` inside `verify_signature(`, and `keep` inside
        `keeps`. `date.today` as a parsed attribute access cannot match anything else.

        There is no legitimate call: the boundary is `serving_date()` and the wall clock enters through
        `datetime.now(tz=UTC)` inside it, where the zone is named.
        """
        import ast  # noqa: PLC0415 - only this case needs it

        source = (_SCRIPTS / "build_inventory.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        offences = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "today"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "date"
        ]

        assert not offences, (
            f"build_inventory.py calls date.today() at lines {offences}. The calendar's boundary is the "
            f"serving date (docs/calendar.md), not the local day of whoever ran the build."
        )
