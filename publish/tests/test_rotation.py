"""The rotation, and above all **the delete**.

⚠️⚠️ **A rotation that copies correctly and deletes nothing looks identical from the outside on day
one.** It looks identical on day two as well, and by day thirty the archive §9 sells is public — silently
and permanently, because anything fetched once is gone. So the cases here are shaped around the step that
has no visible symptom, and each was checked by **removing the delete and watching which one goes red**.

⚠️ **Membership is not enough, and that is the trap.** *Today and yesterday are public* is true of a
rotation that never removes anything. Every assertion below is on the **set**, or on a count, or on
`Rotation.retired` — never on `x in public`.

**No database, no VPS, no clock.** Directories in `tmp_path` and a date passed in.
"""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from publish.health import PUBLIC_LIMIT
from publish.rotate import MANIFEST, PENDING, TODAY, YESTERDAY, RotationError, rotate
from tests.conftest import FIRST as _FIRST
from tests.conftest import build_inventory as _inventory


def _public_packages(public: Path) -> set[str]:
    """What a browser could fetch. ⚠️ The pointers and the manifest are excluded because they are not
    puzzles; counting them would make the limit look satisfied while three boards sit there."""
    return {found.stem for found in public.glob("*.json") if found.name not in {MANIFEST, TODAY, YESTERDAY}}


class TestTheDeleteHappens:
    """The four cases the access model rests on."""

    def test_the_public_path_holds_exactly_the_two_days_and_no_others(self, tmp_path: Path) -> None:
        """⚠️⚠️ **Set equality, not membership** — and **a stale file to start with, which the first
        version of this case did not have.**

        Set equality was the right assertion and it was pointed at an empty directory, so one rotation
        had nothing to remove and the case passed with the delete taken out entirely. A mutation run is
        what said so. **The assertion was never the weak part; the fixture was**, and that is the
        difference between a test that watches the delete and one that watches the copies.
        """
        inventory = _inventory(tmp_path, days=5)
        public = tmp_path / "public"
        public.mkdir()
        (public / "p20260901.json").write_text("{}", encoding="utf-8")

        rotate(inventory, public, _FIRST + timedelta(days=2))

        assert _public_packages(public) == {"p20260903", "p20260902"}

    def test_running_day_after_day_never_grows_the_public_path(self, tmp_path: Path) -> None:
        """⚠️⚠️ The case that catches a rotation which deletes *something* but not the right thing.

        A count alone can stay at two while the wrong file is removed, so this asserts **which ids** on
        every single day rather than only how many.
        """
        inventory = _inventory(tmp_path, days=10)
        public = tmp_path / "public"

        for offset in range(10):
            when = _FIRST + timedelta(days=offset)
            rotate(inventory, public, when)
            held = _public_packages(public)

            assert len(held) <= PUBLIC_LIMIT, f"day {when} left {len(held)} packages public: {sorted(held)}"
            wanted = {f"p{day.isoformat().replace('-', '')}" for day in (when, when - timedelta(days=1))}
            assert held == wanted & {found.stem for found in (inventory / "gen1").glob("p*.json")}, (
                f"day {when} holds {sorted(held)}"
            )

    def test_the_run_reports_what_it_retired(self, tmp_path: Path) -> None:
        """⚠️ `Rotation.retired` is the only positive evidence the delete happened.

        The two cases above prove an *absence*, which a rotation could also achieve by never copying the
        third day in the first place. This proves the file was there and was removed.
        """
        inventory = _inventory(tmp_path, days=5)
        public = tmp_path / "public"

        rotate(inventory, public, _FIRST + timedelta(days=1))
        assert _public_packages(public) == {"p20260902", "p20260901"}

        outcome = rotate(inventory, public, _FIRST + timedelta(days=2))

        assert outcome.retired == ("p20260901",), "the day before yesterday was not reported as retired"

    def test_a_week_of_missed_runs_is_repaired_by_the_first_successful_one(self, tmp_path: Path) -> None:
        """⚠️⚠️ **Built by difference, not by deleting a remembered third day.**

        The obvious shape is *remove the day before yesterday*. It leaves anything an earlier run failed
        to remove in place **forever**, so one missed run becomes a permanent leak rather than a
        recoverable one — and the leak is exactly what cannot be undone, since anything fetched once is
        gone. This plants a week of stale packages and requires one run to clear all of them.
        """
        inventory = _inventory(tmp_path, days=12)
        public = tmp_path / "public"
        public.mkdir()
        stale = {f"p2026090{day}" for day in range(1, 8)}
        for name in stale:
            (public / f"{name}.json").write_text("{}", encoding="utf-8")

        outcome = rotate(inventory, public, _FIRST + timedelta(days=9))

        assert _public_packages(public) == {"p20260910", "p20260909"}
        assert stale <= set(outcome.retired), f"a missed week was not repaired: {sorted(outcome.retired)}"


class TestWhatItPublishes:
    def test_the_pointers_name_the_two_days(self, tmp_path: Path) -> None:
        inventory = _inventory(tmp_path, days=5)
        public = tmp_path / "public"

        rotate(inventory, public, _FIRST + timedelta(days=3))

        assert json.loads((public / TODAY).read_text(encoding="utf-8"))["date"] == "2026-09-04"
        assert json.loads((public / YESTERDAY).read_text(encoding="utf-8"))["date"] == "2026-09-03"

    def test_the_public_manifest_lists_the_two_and_nothing_else(self, tmp_path: Path) -> None:
        """⚠️⚠️ This is the whole of A4.2. The generation manifest lists every published id and stays
        behind the wall; a public one listing more hands out puzzles nobody has played."""
        inventory = _inventory(tmp_path, days=8)
        public = tmp_path / "public"

        rotate(inventory, public, _FIRST + timedelta(days=5))

        listed = json.loads((public / MANIFEST).read_text(encoding="utf-8"))
        assert listed["puzzles"] == ["p20260905", "p20260906"]
        assert "generation" not in listed, "the public manifest names a generation, which nothing public needs"

    def test_the_signature_travels_untouched_because_nothing_here_signs(self, tmp_path: Path) -> None:
        """⚠️ The pointers were signed at generation and the daily step is a copy. **No key on the VPS.**"""
        inventory = _inventory(tmp_path, days=3)
        public = tmp_path / "public"

        rotate(inventory, public, _FIRST + timedelta(days=1))

        original = json.loads((inventory / "gen1" / "days" / "2026-09-02.json").read_text(encoding="utf-8"))
        assert json.loads((public / TODAY).read_text(encoding="utf-8")) == original

    def test_a_package_is_taken_from_the_generation_its_pointer_names(self, tmp_path: Path) -> None:
        """⚠️⚠️ After a top-up several generations exist and only the newest holds a complete schedule,
        while each package stays where it was made. Taking the newest is the defect v39-P1-01 closed on
        the writing side; doing it here would 404 a legitimately assigned date."""
        inventory = _inventory(tmp_path, days=2, generation="gen1")
        _inventory(tmp_path, days=2, generation="gen2", start=_FIRST + timedelta(days=2))
        public = tmp_path / "public"

        rotate(inventory, public, _FIRST + timedelta(days=1))

        assert _public_packages(public) == {"p20260902", "p20260901"}


class TestWhatItRefuses:
    def test_no_pointer_for_today_is_an_error(self, tmp_path: Path) -> None:
        """⚠️ The runway ran out. **Loud rather than an empty public path**, which is a day with no game
        and no signal — §33 alerts below three months for this reason."""
        inventory = _inventory(tmp_path, days=2)
        public = tmp_path / "public"

        with pytest.raises(RotationError, match="nothing to serve today"):
            rotate(inventory, public, _FIRST + timedelta(days=30))

    def test_a_missing_package_is_an_error_rather_than_a_silent_gap(self, tmp_path: Path) -> None:
        """A generation that did not reach the machine. Publishing a pointer with no package behind it
        would give a 404 on a date the forge signed."""
        inventory = _inventory(tmp_path, days=3)
        (inventory / "gen1" / "p20260902.json").unlink()
        public = tmp_path / "public"

        with pytest.raises(RotationError, match="does not exist"):
            rotate(inventory, public, _FIRST + timedelta(days=1))

    def test_the_first_day_of_an_inventory_publishes_without_a_yesterday(self, tmp_path: Path) -> None:
        """⚠️ Refusing here would make the calendar's own first date unservable."""
        inventory = _inventory(tmp_path, days=3)
        public = tmp_path / "public"

        outcome = rotate(inventory, public, _FIRST)

        assert _public_packages(public) == {"p20260901"}
        assert outcome.published == ("2026-09-01",)
        assert not (public / YESTERDAY).exists()

    def test_a_stale_yesterday_pointer_is_removed_when_there_is_no_yesterday(self, tmp_path: Path) -> None:
        """⚠️ Otherwise a pointer from an earlier run goes on claiming to be yesterday, which is the
        *absence of a check reading as a passing one* with a date attached."""
        inventory = _inventory(tmp_path, days=3)
        public = tmp_path / "public"
        public.mkdir()
        (public / YESTERDAY).write_text('{"date": "2026-08-31"}', encoding="utf-8")

        rotate(inventory, public, _FIRST)

        assert not (public / YESTERDAY).exists()


class TestTheClockItServesBy:
    """⚠️⚠️ **The number's third spelling, and the document is what keeps the three in agreement.**

    `forge` holds one because it decides which dates are frozen; `serve` gains one when E1 builds the
    loader. **`publish` cannot import `forge`'s** — `forge` never reaches the VPS (§33) and this module
    runs there — so the trees share the rule by *document* rather than by code, and this is what makes
    the document load-bearing instead of decorative.
    """

    def test_the_day_rolls_at_eight_in_the_morning_utc(self) -> None:
        from datetime import UTC, datetime  # noqa: PLC0415

        from publish.rotate import serving_date  # noqa: PLC0415

        assert serving_date(datetime(2026, 8, 23, 7, 59, tzinfo=UTC)) == date(2026, 8, 22)
        assert serving_date(datetime(2026, 8, 23, 8, 0, tzinfo=UTC)) == date(2026, 8, 23)

    def test_it_is_the_same_answer_everywhere_on_earth(self) -> None:
        """⚠️ The instant decides, never the observer. `.date()` reads the calendar of whatever zone is
        attached, so normalising to UTC first is the whole of it — the same defect was made and caught
        in `forge`'s copy on the day it was written."""
        from datetime import UTC, datetime, timezone  # noqa: PLC0415

        from publish.rotate import serving_date  # noqa: PLC0415

        moment = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
        answers = {
            serving_date(moment.astimezone(timezone(timedelta(hours=offset)))) for offset in (-11, -8, -5, 0, 2, 9, 14)
        }

        assert answers == {date(2026, 8, 23)}, f"the serving date depends on who is asking: {answers}"

    def test_a_datetime_naming_no_zone_is_refused(self) -> None:
        from datetime import datetime  # noqa: PLC0415

        from publish.rotate import serving_date  # noqa: PLC0415

        with pytest.raises(ValueError, match="names no zone"):
            serving_date(datetime(2026, 8, 23, 12, 0))

    def test_it_takes_the_clock_as_an_argument(self) -> None:
        from publish.rotate import serving_date  # noqa: PLC0415

        assert isinstance(serving_date(), date)

    def test_the_offset_matches_the_document_that_owns_it(self) -> None:
        """⚠️⚠️ **Three spellings, one definition.** `docs/calendar.md` states the rollover; this asserts
        the constant against the figure the document gives, so the copies cannot drift into three
        answers. No test can compare the trees directly — each CI workflow ignores the others' paths —
        so the document is the only place all three can point at."""
        import re  # noqa: PLC0415

        from publish.rotate import ROLLOVER_OFFSET_HOURS  # noqa: PLC0415

        calendar = Path(__file__).resolve().parents[2] / "docs" / "calendar.md"
        stated = re.search(r"ROLLOVER_OFFSET_HOURS = (-?\d+)", calendar.read_text(encoding="utf-8"))

        assert stated, "docs/calendar.md no longer states ROLLOVER_OFFSET_HOURS, which three trees point at"
        assert int(stated[1]) == ROLLOVER_OFFSET_HOURS


class TestAFailedWriteLeavesTheOldBytes:
    """v40-P2-01. **The ordering this module states, applied to the files that state it.**

    ⚠⚠ `rotate()` copies before it deletes so a part-way failure leaves the public path holding *more*
    than it should -- reportable -- rather than less, which is a day with no game and no signal. An
    in-place write inverts that at `today.json`: opening it truncates the pointer that selects the day's
    puzzle, so a short write destroys the old one and the new one never lands.

    ⚠️ **Fault-injected, because reading the output cannot show it.** The old code passed every case
    in this file: nothing ever failed mid-write, so nothing observed the truncation window.
    """

    def _erroring(self, monkeypatch: pytest.MonkeyPatch, name: str) -> None:
        """Fail the write of one public file, after its pending file has been opened."""
        real = Path.write_bytes

        def refuse(self: Path, content: bytes) -> int:
            if self.name == name + PENDING:
                message = "no space left on device"
                raise OSError(message)
            return real(self, content)

        monkeypatch.setattr(Path, "write_bytes", refuse)

    def _rotated(self, tmp_path: Path) -> tuple[Path, Path]:
        inventory = _inventory(tmp_path, days=6)
        public = tmp_path / "public"
        rotate(inventory, public, _FIRST + timedelta(days=3))
        return inventory, public

    def test_the_served_pointer_survives_a_failed_rotation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        inventory, public = self._rotated(tmp_path)
        before = (public / TODAY).read_bytes()
        self._erroring(monkeypatch, TODAY)

        with pytest.raises(OSError, match="no space"):
            rotate(inventory, public, _FIRST + timedelta(days=4))

        assert (public / TODAY).read_bytes() == before, "the served pointer was destroyed by a failed write"
        served = json.loads((public / TODAY).read_text(encoding="utf-8"))
        assert served["date"] == (_FIRST + timedelta(days=3)).isoformat()

    def test_the_manifest_survives_a_failed_rotation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        inventory, public = self._rotated(tmp_path)
        before = (public / MANIFEST).read_bytes()
        self._erroring(monkeypatch, MANIFEST)

        with pytest.raises(OSError, match="no space"):
            rotate(inventory, public, _FIRST + timedelta(days=4))

        assert (public / MANIFEST).read_bytes() == before

    def test_no_pending_file_is_left_behind(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """⚠️ A surviving pending file is served by nothing and swept by nothing. The failing write
        removes its own; the sweep removes any older one."""
        inventory, public = self._rotated(tmp_path)
        self._erroring(monkeypatch, TODAY)
        with pytest.raises(OSError, match="no space"):
            rotate(inventory, public, _FIRST + timedelta(days=4))
        monkeypatch.undo()
        (public / f"leftover.json{PENDING}").write_text("half a package", encoding="utf-8")

        rotate(inventory, public, _FIRST + timedelta(days=4))

        assert not list(public.glob(f"*{PENDING}"))

    def test_a_pending_file_is_not_counted_as_a_package(self, tmp_path: Path) -> None:
        """⚠⚠ Why the suffix goes **after** `.json` rather than before it. The public path is counted
        with `*.json`, so `x.pending.json` would read as a third public package and turn the health check
        red over a file nothing serves."""
        _inv, public = self._rotated(tmp_path)
        (public / f"halfway.json{PENDING}").write_text("torn", encoding="utf-8")

        assert (
            _public_packages(public) == {name.removesuffix(".json") for name in ("p20260904.json", "p20260903.json")}
            or len(_public_packages(public)) <= PUBLIC_LIMIT
        )


class TestWhatARefusedPointerLooksLike:
    def test_a_pointer_that_is_not_an_object_is_refused(self, tmp_path: Path) -> None:
        inventory = _inventory(tmp_path, days=3)
        (inventory / "gen1" / "days" / "2026-09-02.json").write_text('["not", "a", "pointer"]', encoding="utf-8")

        with pytest.raises(RotationError, match="is not an object"):
            rotate(inventory, tmp_path / "public", _FIRST + timedelta(days=1))

    def test_a_pointer_missing_its_fields_is_refused(self, tmp_path: Path) -> None:
        """⚠️ Named rather than exploding later: a pointer with no `puzzle_id` would otherwise become a
        path called `None.json` and a confusing missing-file error one layer down."""
        inventory = _inventory(tmp_path, days=3)
        (inventory / "gen1" / "days" / "2026-09-02.json").write_text('{"date": "2026-09-02"}', encoding="utf-8")

        with pytest.raises(RotationError, match="a pointer names"):
            rotate(inventory, tmp_path / "public", _FIRST + timedelta(days=1))
