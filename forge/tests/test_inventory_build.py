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
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import pairwise
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from boxscore_forge.calendar import void

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

    def draw(_limit: int, *, window: tuple[int, int] = (1910, 2029), **_kwargs: object) -> list[_Loaded]:
        year = window[0] + 1
        return [_Loaded(f"CHN{year}09{n:04d}") for n in range(available)]

    monkeypatch.setattr(builder, "load", draw)
    monkeypatch.setattr(
        builder,
        "_hardest_target",
        lambda item, _key, counts, _refusals: (counts.update(["published"]), _Package(f"p{item.game_id}"))[1],
    )
    monkeypatch.setattr(builder, "write_package", lambda path, _package: path.write_text("{}", encoding="utf-8"))


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

        assert set(pointer) == {"date", "puzzle_id", "generation", "schema", "signature"}

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
