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
from pathlib import Path
from typing import Any

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
_TODAY = date(2026, 9, 1)


def _builder() -> Any:
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


def _stub(builder: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, available: int) -> None:
    """A pool of `available` distinct games, each producing a board, and nothing touching a database."""
    monkeypatch.setattr(builder, "CALENDAR", tmp_path / "calendar.json")
    monkeypatch.setattr(builder, "_ROOT", tmp_path)
    monkeypatch.setattr(
        builder, "load", lambda *_args, **_kwargs: [_Loaded(f"CHN2026090{n:04d}") for n in range(available)]
    )
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
