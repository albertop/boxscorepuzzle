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
import sys
from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
_TODAY = date(2026, 9, 1)


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

        builder.build(10, date(2026, 9, 2), object(), _TODAY)

        assert len(builder.read(builder.CALENDAR)) == 10

    def test_a_short_run_raises_rather_than_warning(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=4)

        with pytest.raises(SystemExit, match="unfilled"):
            builder.build(10, date(2026, 9, 2), object(), _TODAY)

    def test_a_short_run_still_keeps_the_boards_it_made(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # ⚠️⚠️ **The half that "treat a short build as failure before writing" would have broken.**
        # A2.3: a run that dies at board 400 of 450 must not start over. The failure is the exit code,
        # not the loss of the work.
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=4)

        with pytest.raises(SystemExit):
            builder.build(10, date(2026, 9, 2), object(), _TODAY)

        assert len(builder.read(builder.CALENDAR)) == 4, "the partial batch was discarded"

    def test_re_running_fills_the_gap_the_short_run_left(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # The claim the refusal message makes, asserted rather than promised: *re-running fills the gaps*.
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=4)
        with pytest.raises(SystemExit):
            builder.build(10, date(2026, 9, 2), object(), _TODAY)

        _stub(builder, monkeypatch, tmp_path, available=20)
        builder.build(10, date(2026, 9, 2), object(), _TODAY)

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
        builder.build(10, date(2026, 9, 2), object(), _TODAY)

        builder.build(10, date(2026, 9, 2), object(), _TODAY)

        assert len(builder.read(builder.CALENDAR)) == 10

    def test_a_later_window_extends_rather_than_overlapping(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=40)
        builder.build(10, date(2026, 9, 2), object(), _TODAY)

        builder.build(10, date(2026, 9, 12), object(), _TODAY)

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
            builder.build(10, _TODAY, object(), _TODAY)


class TestTheEraQuotaIsSampledRatherThanHoped:
    """⚠️⚠️ The first 150-board calendar was **34% pre-1950 against a 5% ceiling**, because `load()`
    draws *n per decade* over twelve decades and four of them are before 1950. **A flat draw cannot
    satisfy a weighted quota except by accident.**"""

    def test_the_calendar_stays_within_the_ceiling(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        builder = _builder()
        _stub(builder, monkeypatch, tmp_path, available=200)

        builder.build(100, date(2026, 9, 2), object(), _TODAY)

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
            builder.build(10, date(2026, 9, 2), object(), _TODAY)

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
            builder.build(5, date(2026, 9, 2), object(), _TODAY)
            got.append([e.puzzle_id for e in builder.read(builder.CALENDAR)])

        assert got[0] == got[1], "the same games produced different puzzle ids on a second run"
