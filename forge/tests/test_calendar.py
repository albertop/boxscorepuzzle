"""The calendar extends, never rewrites, and spends each game exactly once.

`docs/calendar.md` is the artefact; this is the red half of building it. Every rule here is one §21 or
§7 makes, and each is tested by the **refusal** rather than by the happy path — a guard that has only
ever been watched succeeding is indistinguishable from one that cannot fail.
"""

import json
from dataclasses import asdict
from dataclasses import replace as with_fields
from datetime import date
from pathlib import Path

import pytest

from boxscore_forge.calendar import (
    CalendarError,
    Entry,
    extend,
    for_serving,
    read,
    replace,
    void,
    write,
)

TODAY = date(2026, 9, 1)
LATER = date(2026, 9, 30)


def an_entry(day: int, *, game: str = "SLN19680808", direction: str = "CHN", puzzle: str = "") -> Entry:
    return Entry(
        date=f"2026-09-{day:02d}",
        puzzle_id=puzzle or f"p{day:04x}0000{day:04x}",
        game_id=game,
        direction=direction,
        status="active",
        assigned="gen0001",
    )


@pytest.fixture
def book() -> tuple[Entry, ...]:
    """Three assigned days, all in the future, each on its own game."""
    return tuple(an_entry(day, game=f"SLN1968080{day}") for day in (2, 3, 4))


class TestItExtendsAndNeverRewrites:
    def test_a_second_run_over_the_same_dates_adds_nothing(self, book: tuple[Entry, ...]) -> None:
        # §21's idempotence, and the whole of the extension mechanism: the builder writes only dates
        # that have no entry, so running it twice is running it once.
        once = extend((), book, today=TODAY)
        twice = extend(once, book, today=TODAY)

        assert twice == once

    def test_an_existing_entry_is_never_replaced_by_extending(self, book: tuple[Entry, ...]) -> None:
        # ⚠️⚠️ **This asserted `next(...)` and could not fail.** Written as
        # `kept = next(e for e in after if e.date == ...)`, it found the *first* match — and `sorted()`
        # is stable, so the original always came first. Removing the skip in `extend()` left the
        # calendar holding **two entries for one date** and this test stayed green. Caught by mutating
        # the implementation and counting which tests turned red, not by rereading the assertion.
        different = (an_entry(2, game="BOS19750101", puzzle="somethingelse"),)
        after = extend(extend((), book, today=TODAY), different, today=TODAY)

        kept = [entry for entry in after if entry.date == "2026-09-02"]
        assert len(kept) == 1, f"one date, {len(kept)} entries — extending appended instead of skipping"
        assert kept[0].puzzle_id == book[0].puzzle_id, "extending overwrote a date that already had one"

    def test_no_operation_leaves_two_entries_on_one_date(self, book: tuple[Entry, ...]) -> None:
        # The invariant the test above learned the hard way, asserted over every write path rather than
        # over the one that broke. A date with two puzzles is not a bad calendar; it is not a calendar.
        published = extend((), book, today=TODAY)
        after = void(
            replace(extend(published, book, today=TODAY), an_entry(4, game="CLE19220607"), today=TODAY),
            "2026-09-03",
        )

        dates = [entry.date for entry in after]
        assert len(dates) == len(set(dates)), f"a date is assigned twice: {sorted(dates)}"

    def test_today_is_refused(self) -> None:
        # ⚠️ The boundary is *today*, not *played*: asking whether somebody played means asking the data
        # layer, which §23 keeps out of this side entirely.
        with pytest.raises(CalendarError, match="past"):
            extend((), (with_fields(an_entry(1), date="2026-09-01"),), today=TODAY)

    def test_a_date_before_today_is_refused(self) -> None:
        with pytest.raises(CalendarError, match="past"):
            extend((), (with_fields(an_entry(1), date="2026-08-31"),), today=TODAY)


class TestOneGameOnePuzzle:
    def test_the_other_direction_of_a_published_game_is_refused(self, book: tuple[Entry, ...]) -> None:
        # ⚠️⚠️ The reveal prints both clubs, so the other direction's board travels inside this one's
        # reveal. No package can see this and no validation layer can either.
        published = extend((), book, today=TODAY)
        other_way = an_entry(9, game="SLN19680802", direction="SLN")

        with pytest.raises(CalendarError, match="already"):
            extend(published, (other_way,), today=TODAY)

    def test_the_check_is_over_the_whole_history_and_not_the_batch(self, book: tuple[Entry, ...]) -> None:
        # The batch being added is clean on its own. `refuse_second_direction` passes here and is not
        # enough, which is the entire reason this lives in the calendar.
        published = extend((), book, today=TODAY)
        later_batch = (an_entry(10, game="NYA19990101"), an_entry(11, game="SLN19680803", direction="SLN"))

        with pytest.raises(CalendarError, match="already"):
            extend(published, later_batch, today=TODAY)

    def test_a_batch_cannot_contain_both_directions_of_one_game(self) -> None:
        both = (an_entry(20, game="DET19840505", direction="DET"), an_entry(21, game="DET19840505", direction="MIN"))

        with pytest.raises(CalendarError, match="already"):
            extend((), both, today=TODAY)

    def test_voiding_does_not_return_the_game_to_the_pool(self, book: tuple[Entry, ...]) -> None:
        # ⚠️ A voided date still spent its game: the reveal was shown to whoever played it that day.
        published = void(extend((), book, today=TODAY), "2026-09-02")
        # ⚠️ October, not September: `LATER` is the 30th, so a September date would be refused for being
        # in the past and the test would pass on the wrong refusal. It did, on the first run.
        other_way = with_fields(an_entry(2, game="SLN19680802", direction="SLN"), date="2026-10-15")

        with pytest.raises(CalendarError, match="already"):
            extend(published, (other_way,), today=LATER)


class TestVoidAndReplace:
    def test_voiding_keeps_the_assignment(self, book: tuple[Entry, ...]) -> None:
        # §21: a defective past date is marked void and excluded from streaks — the assignment stays,
        # because deleting it rewrites history.
        after = void(extend((), book, today=TODAY), "2026-09-02")

        entry = next(e for e in after if e.date == "2026-09-02")
        assert entry.status == "void"
        assert entry.puzzle_id == book[0].puzzle_id

    def test_replacing_a_future_date_is_allowed(self, book: tuple[Entry, ...]) -> None:
        published = extend((), book, today=TODAY)
        after = replace(published, an_entry(4, game="CLE19220607"), today=TODAY)

        assert next(e for e in after if e.date == "2026-09-04").game_id == "CLE19220607"

    def test_replacing_a_past_date_is_refused(self, book: tuple[Entry, ...]) -> None:
        published = extend((), book, today=TODAY)

        with pytest.raises(CalendarError, match="past"):
            replace(published, an_entry(2, game="CLE19220607"), today=LATER)

    def test_replacing_frees_the_game_it_dropped(self, book: tuple[Entry, ...]) -> None:
        # The replaced puzzle was never played — nobody saw its reveal — so its game is spendable again.
        # ⚠️ This is the one case where a game comes back, and it is exactly the case voiding is not.
        published = replace(extend((), book, today=TODAY), an_entry(4, game="CLE19220607"), today=TODAY)
        after = extend(published, (an_entry(12, game="SLN19680804", direction="SLN"),), today=TODAY)

        assert any(e.date == "2026-09-12" for e in after)


class TestWhatDeploys:
    def test_the_served_calendar_carries_no_game_id(self, book: tuple[Entry, ...]) -> None:
        # ⚠️⚠️ A `game_id` reaching the VPS is not untidiness, it is the answer (§7).
        published = extend((), book, today=TODAY)
        text = str(for_serving(published))

        for entry in published:
            assert entry.game_id not in text, f"{entry.game_id} would deploy"

    def test_the_served_calendar_agrees_with_the_source_on_every_date(self, book: tuple[Entry, ...]) -> None:
        # Two files stating one mapping is this project's most-met defect. They are generated from one
        # source, and this is the check that says so.
        published = extend((), book, today=TODAY)

        assert for_serving(published) == {e.date: e.puzzle_id for e in published if e.status == "active"}

    def test_a_voided_date_is_not_served(self, book: tuple[Entry, ...]) -> None:
        published = void(extend((), book, today=TODAY), "2026-09-02")

        assert "2026-09-02" not in for_serving(published)


class TestItSurvivesADiskRoundTrip:
    def test_what_is_written_is_what_is_read(self, tmp_path: Path, book: tuple[Entry, ...]) -> None:
        published = extend((), book, today=TODAY)
        path = tmp_path / "calendar.json"
        write(path, published)

        assert read(path) == published

    def test_reading_an_absent_calendar_is_an_empty_one(self, tmp_path: Path) -> None:
        # The first run has no calendar to read, and that is not an error — but it must be the *only*
        # thing that produces an empty one, so a misspelled path cannot look like a fresh start.
        assert read(tmp_path / "calendar.json") == ()

    def test_a_malformed_calendar_is_refused_rather_than_half_read(self, tmp_path: Path) -> None:
        # ⚠️ Validate at the boundary. A calendar that half-parses is a calendar that silently forgets
        # assignments, and §21 says those can never be recomputed.
        path = tmp_path / "calendar.json"
        path.write_text('[{"date": "2026-09-02"}]', encoding="utf-8")

        with pytest.raises(CalendarError):
            read(path)


class TestTheRefusalsThatHadNoTest:
    """⚠️ Every branch below is a `raise` that nothing exercised — 81% coverage, and the fifteen missing
    lines were all refusals. `CLAUDE.md`: a check that never fires is indistinguishable from one that is
    broken. These are the ones that never fired."""

    def test_voiding_a_date_with_no_assignment_is_refused(self, book: tuple[Entry, ...]) -> None:
        with pytest.raises(CalendarError, match="no assignment"):
            void(extend((), book, today=TODAY), "2026-09-20")

    def test_replacing_a_date_with_no_assignment_is_refused(self, book: tuple[Entry, ...]) -> None:
        # ⚠️ Not the same as extending. A `replace` that quietly added a date would be an append wearing
        # the name of an edit, and the operator would have no way to tell which happened.
        with pytest.raises(CalendarError, match="no assignment"):
            replace(extend((), book, today=TODAY), an_entry(20, game="CLE19220607"), today=TODAY)

    def test_replacing_with_an_already_published_game_is_refused(self, book: tuple[Entry, ...]) -> None:
        # §7 applies to replacements too: filling 09-04 with 09-02's game gives 09-02's board away.
        published = extend((), book, today=TODAY)
        collision = with_fields(an_entry(4, game="SLN19680802", direction="SLN"), date="2026-09-04")

        with pytest.raises(CalendarError, match="already"):
            replace(published, collision, today=TODAY)

    def test_a_calendar_that_is_not_a_list_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "calendar.json"
        path.write_text('{"2026-09-02": "somepuzzle"}', encoding="utf-8")

        with pytest.raises(CalendarError, match="expected a list"):
            read(path)

    def test_an_entry_that_is_not_an_object_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "calendar.json"
        path.write_text('["2026-09-02"]', encoding="utf-8")

        with pytest.raises(CalendarError, match="expected an object"):
            read(path)

    def test_unknown_fields_are_refused_rather_than_ignored(self, tmp_path: Path) -> None:
        # ⚠️⚠️ **Refused, not ignored, and that direction is the point.** A field this reader does not
        # know is either a newer format or a typo — `puzzel_id` beside a real `puzzle_id`, say. Ignoring
        # it means loading a calendar that means something else and saying nothing, then writing it back
        # without the field. §21 makes that unrecoverable.
        path = tmp_path / "calendar.json"
        entry = an_entry(2)
        # ⚠️ Built from the dataclass rather than from a literal list of names: a field added to `Entry`
        # and not to `_FIELDS` should fail the round-trip test, not slip past this one.
        row = asdict(entry)
        path.write_text(json.dumps([{**row, "difficulty": "monday"}]), encoding="utf-8")

        with pytest.raises(CalendarError, match="unknown fields"):
            read(path)

    def test_broken_json_says_so_rather_than_dying_inside_the_parser(self, tmp_path: Path) -> None:
        path = tmp_path / "calendar.json"
        path.write_text("[{,]", encoding="utf-8")

        with pytest.raises(CalendarError, match="not readable JSON"):
            read(path)
