"""The check that makes a silent failure loud.

⚠️⚠️ **Two failures, two questions, and neither question catches the other's.** A rotation that stops
deleting leaves a correct today and yesterday and a growing directory; a rotation that stops running
leaves exactly two packages, both stale. **A count passes the second and a date passes the first**, so
the check asks both — and these cases prove each question fires on its own failure and only on its own.
"""

import json
from datetime import date, timedelta
from pathlib import Path

from publish.health import PUBLIC_LIMIT, inspect
from publish.rotate import TODAY, YESTERDAY, rotate
from tests.conftest import FIRST as _FIRST
from tests.conftest import build_inventory as _inventory


def _rotated(tmp_path: Path, *, days: int = 6, offset: int = 3) -> tuple[Path, date]:
    """A public path in the state a working rotation leaves it in."""
    inventory = _inventory(tmp_path, days=days)
    public = tmp_path / "public"
    when = _FIRST + timedelta(days=offset)
    rotate(inventory, public, when)
    return public, when


class TestWhatItPasses:
    def test_a_freshly_rotated_path_is_healthy(self, tmp_path: Path) -> None:
        public, when = _rotated(tmp_path)

        verdict = inspect(public, when)

        assert verdict.healthy, verdict.faults
        assert verdict.faults == ()

    def test_the_first_day_is_healthy_with_only_one_package(self, tmp_path: Path) -> None:
        """⚠️ The limit is a ceiling, not a quota. One package is the calendar's first date, not a fault."""
        inventory = _inventory(tmp_path, days=3)
        public = tmp_path / "public"
        rotate(inventory, public, _FIRST)

        assert inspect(public, _FIRST).healthy


class TestTheDeleteThatDidNotHappen:
    def test_a_planted_third_package_turns_it_red(self, tmp_path: Path) -> None:
        """⚠️⚠️ **The case that proves the check fires at all.** Without it the health function is a
        thing that returns `healthy` and has never been observed doing anything else — which is
        indistinguishable from one that cannot fail."""
        public, when = _rotated(tmp_path)
        (public / "p20260830.json").write_text("{}", encoding="utf-8")

        verdict = inspect(public, when)

        assert not verdict.healthy
        assert any("packages are public" in fault for fault in verdict.faults), verdict.faults

    def test_the_fault_names_the_extra_package(self, tmp_path: Path) -> None:
        """*Three packages* sends the operator looking. A third id tells them which run failed and when."""
        public, when = _rotated(tmp_path)
        (public / "p20260830.json").write_text("{}", encoding="utf-8")

        assert any("p20260830" in fault for fault in inspect(public, when).faults)

    def test_the_limit_is_the_documented_two(self, tmp_path: Path) -> None:
        """⚠️ Not a number this file invents: today's and yesterday's, and a third day is the archive
        leaking one day at a time (`docs/calendar.md`)."""
        assert PUBLIC_LIMIT == 2

        public, when = _rotated(tmp_path)
        for extra in range(PUBLIC_LIMIT + 1):
            (public / f"x{extra}.json").write_text("{}", encoding="utf-8")

        assert not inspect(public, when).healthy


class TestTheRunThatDidNotHappen:
    def test_a_stale_today_pointer_turns_it_red(self, tmp_path: Path) -> None:
        """⚠️⚠️ **The failure a count cannot see.** The job stops running, the directory keeps exactly two
        packages, and yesterday's board is served as today's. Players notice within hours; this notices
        first."""
        public, when = _rotated(tmp_path)

        verdict = inspect(public, when + timedelta(days=1))

        assert not verdict.healthy
        assert any("has not run" in fault for fault in verdict.faults), verdict.faults

    def test_the_fault_names_both_dates(self, tmp_path: Path) -> None:
        public, when = _rotated(tmp_path)

        faults = inspect(public, when + timedelta(days=2)).faults

        assert any(when.isoformat() in fault and (when + timedelta(days=2)).isoformat() in fault for fault in faults)

    def test_a_missing_pointer_turns_it_red(self, tmp_path: Path) -> None:
        public, when = _rotated(tmp_path)
        (public / TODAY).unlink()

        assert any("is missing" in fault for fault in inspect(public, when).faults)

    def test_an_unreadable_pointer_turns_it_red_rather_than_passing(self, tmp_path: Path) -> None:
        """⚠️ Fail closed. A pointer that will not parse must not read as *the date is fine*."""
        public, when = _rotated(tmp_path)
        (public / TODAY).write_text("{not json", encoding="utf-8")

        assert any("not a readable pointer" in fault for fault in inspect(public, when).faults)

    def test_a_pointer_that_is_not_an_object_turns_it_red(self, tmp_path: Path) -> None:
        public, when = _rotated(tmp_path)
        (public / TODAY).write_text('["2026-09-04"]', encoding="utf-8")

        assert any("not a readable pointer" in fault for fault in inspect(public, when).faults)


class TestThePointerIsFollowed:
    """v40-P1-01. **The state F3 exists for: `serve` up, inventory empty.**

    ⚠⚠ **This was green.** `inspect()` read the pointer's date and never its `puzzle_id`, and the
    package check is an *at most* -- so zero packages behind a current-dated pointer satisfied both
    halves while `/today` led the only game the product has to a 404.

    ⚠️ The two halves were each true. What was missing was the question joining them, which is why
    neither existing test could fail.
    """

    def test_a_pointer_naming_a_package_that_is_gone_turns_it_red(self, tmp_path: Path) -> None:
        public, when = _rotated(tmp_path)
        named = json.loads((public / TODAY).read_text(encoding="utf-8"))["puzzle_id"]
        (public / f"{named}.json").unlink()

        verdict = inspect(public, when)

        assert not verdict.healthy
        assert any(named in fault and "404" in fault for fault in verdict.faults)

    def test_an_empty_path_behind_a_current_pointer_turns_it_red(self, tmp_path: Path) -> None:
        """The whole of the outage, reproduced: nothing but a pointer, dated today."""
        public, when = _rotated(tmp_path)
        for package in public.glob("*.json"):
            if package.name != TODAY:
                package.unlink()

        assert not inspect(public, when).healthy

    def test_a_pointer_with_no_puzzle_id_turns_it_red(self, tmp_path: Path) -> None:
        public, when = _rotated(tmp_path)
        pointer = json.loads((public / TODAY).read_text(encoding="utf-8"))
        del pointer["puzzle_id"]
        (public / TODAY).write_text(json.dumps(pointer), encoding="utf-8")

        assert any("names no puzzle" in fault for fault in inspect(public, when).faults)

    def test_yesterday_is_followed_too(self, tmp_path: Path) -> None:
        public, when = _rotated(tmp_path)
        named = json.loads((public / YESTERDAY).read_text(encoding="utf-8"))["puzzle_id"]
        (public / f"{named}.json").unlink()

        assert any(named in fault for fault in inspect(public, when).faults)

    def test_a_first_day_with_no_yesterday_stays_green(self, tmp_path: Path) -> None:
        """⚠️ The other direction, and the reason the yesterday check is guarded. §9's two days are a
        **ceiling**: the calendar's first day legitimately has one, and a check that read that as an
        outage would be red on the day the product launches."""
        public, when = _rotated(tmp_path, offset=0)

        assert not (public / YESTERDAY).is_file()
        assert inspect(public, when).healthy

    def test_an_unreadable_yesterday_turns_it_red(self, tmp_path: Path) -> None:
        """⚠️ Yesterday's pointer gets the same two questions as today's. A pointer that will not parse
        is a fault there too -- the archive's one public day, unserved and unreported."""
        public, when = _rotated(tmp_path)
        (public / YESTERDAY).write_text("{not json", encoding="utf-8")

        assert any(YESTERDAY in fault and "not a readable pointer" in fault for fault in inspect(public, when).faults)

    def test_a_pointer_whose_date_is_not_a_string_is_unreadable(self, tmp_path: Path) -> None:
        """⚠️ An object with a numeric `date` parses and answers nothing. Fail closed: *unreadable*,
        not *the date is fine*."""
        public, when = _rotated(tmp_path)
        (public / TODAY).write_text('{"date": 20260904, "puzzle_id": "x"}', encoding="utf-8")

        assert any("not a readable pointer" in fault for fault in inspect(public, when).faults)


class TestTheTwoQuestionsAreIndependent:
    """⚠️⚠️ Each question must fire on its own failure **and stay quiet on the other's**, or one of them
    is redundant and the pair is a single check wearing two names."""

    def test_the_count_is_quiet_when_only_the_date_is_wrong(self, tmp_path: Path) -> None:
        public, when = _rotated(tmp_path)

        faults = inspect(public, when + timedelta(days=1)).faults

        assert not any("packages are public" in fault for fault in faults), faults

    def test_the_date_is_quiet_when_only_the_count_is_wrong(self, tmp_path: Path) -> None:
        public, when = _rotated(tmp_path)
        (public / "p20260830.json").write_text("{}", encoding="utf-8")

        faults = inspect(public, when).faults

        assert not any("has not run" in fault for fault in faults), faults


class TestWhatItLooksAt:
    def test_the_pointers_and_the_manifest_are_not_counted_as_packages(self, tmp_path: Path) -> None:
        """⚠️ Counting them would put the total at four on a perfectly healthy path — and worse, a
        check tuned to pass at four would then pass with two real boards too many."""
        public, when = _rotated(tmp_path)

        assert {found.name for found in public.glob("*.json")} > {TODAY, YESTERDAY}
        assert inspect(public, when).healthy

    def test_a_missing_public_directory_is_a_fault_rather_than_an_exception(self, tmp_path: Path) -> None:
        """A health endpoint that raises reports nothing; it has to answer."""
        verdict = inspect(tmp_path / "never-created", _FIRST)

        assert not verdict.healthy
        assert any("not a directory" in fault for fault in verdict.faults)
