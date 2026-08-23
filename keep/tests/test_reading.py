"""What the reader refuses, and why the refusal names the field.

⚠️ Every test here is a refusal path. They were the uncovered lines when the service was first written,
and they are the ones that matter: `CLAUDE.md` puts *validate at the boundary, not downstream* in its own
rule, and a boundary whose refusals are untested is one nobody has watched refuse.
"""

import pytest

from keep.reading import LARGEST_STORED_INTEGER, MalformedError, read_batch, read_error, read_event


def an_event() -> dict[str, object]:
    return {
        "event_id": "e-1", "device_id": "d-1", "account_id": None, "puzzle_id": "p-1",
        "calendar_date": None, "played_on": None, "duration_ms": 1, "hints": 0,
        "errors": 0, "failed_checks": 0, "highest_technique": None, "solved": True, "assisted": False,
    }  # fmt: skip


class TestTheEnvelope:
    def test_a_body_that_is_not_an_object_is_refused(self) -> None:
        with pytest.raises(MalformedError, match="expected an object"):
            read_batch(["events"], "events", read_event)

    def test_a_key_that_is_not_a_list_is_refused(self) -> None:
        with pytest.raises(MalformedError, match="expected a list"):
            read_batch({"events": {"event_id": "e-1"}}, "events", read_event)

    def test_a_missing_key_is_refused_by_name(self) -> None:
        # ⚠️ `{"event": [...]}` — singular — is the likeliest client typo, and it must not read as an
        # empty batch that succeeds.
        with pytest.raises(MalformedError, match="events"):
            read_batch({"event": []}, "events", read_event)

    def test_an_empty_list_is_fine(self) -> None:
        assert read_batch({"events": []}, "events", read_event) == []


class TestOneRow:
    def test_a_row_that_is_not_an_object_is_refused(self) -> None:
        with pytest.raises(MalformedError, match="expected an object"):
            read_event("e-1")

    def test_an_error_report_that_is_not_an_object_is_refused(self) -> None:
        with pytest.raises(MalformedError, match="expected an object"):
            read_error(["x-1"])

    def test_an_empty_string_is_not_a_present_field(self) -> None:
        # An id of `""` is a client bug that would otherwise become a primary key nothing can retry.
        with pytest.raises(MalformedError, match="event_id"):
            read_event({**an_event(), "event_id": ""})

    def test_a_negative_duration_is_refused(self) -> None:
        with pytest.raises(MalformedError, match="duration_ms"):
            read_event({**an_event(), "duration_ms": -1})

    def test_a_number_past_what_the_column_holds_is_refused(self) -> None:
        """⚠⚠ v39-P2-01. It was accepted here and rejected by the `INTEGER` column three layers later.

        That is the shape `CLAUDE.md` names — *validate at the boundary, not downstream* — and here it
        had a cost beyond a confusing message: the failed statement aborted the transaction, and on the
        single reused connection **every later request failed until the process was restarted.**
        """
        with pytest.raises(MalformedError, match="duration_ms"):
            read_event({**an_event(), "duration_ms": 2**31})

    def test_the_ceiling_applies_to_every_number_and_not_only_the_duration(self) -> None:
        # ⚠️ Four fields share the check, and testing one of them would leave three that could still do
        # it. They are all `INTEGER` in the same schema.
        for field in ("duration_ms", "hints", "errors", "failed_checks"):
            with pytest.raises(MalformedError, match=field):
                read_event({**an_event(), field: 2**31})

    def test_the_largest_value_the_column_holds_is_still_accepted(self) -> None:
        # ⚠️ **The other side of the boundary.** A check that refuses one value too many is a check that
        # rejects legitimate data, and off-by-one at a limit is how that happens.
        assert read_event({**an_event(), "duration_ms": LARGEST_STORED_INTEGER}).duration_ms == LARGEST_STORED_INTEGER

    def test_a_non_boolean_flag_is_refused(self) -> None:
        # `"true"` from a client that stringified its JSON twice: truthy, and not a boolean.
        with pytest.raises(MalformedError, match="solved"):
            read_event({**an_event(), "solved": "true"})

    def test_a_well_formed_row_survives_intact(self) -> None:
        # ⚠️ The control. Without it every refusal above is consistent with a reader that refuses
        # everything, which would pass each of them and store nothing.
        event = read_event(an_event())

        assert (event.event_id, event.duration_ms, event.solved) == ("e-1", 1, True)
