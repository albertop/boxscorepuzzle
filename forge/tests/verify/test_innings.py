"""Innings pitched round-trip, with the boundaries written out rather than generated.

`13 outs → "4.1" → 13` is the whole contract. It is worth golden values because the failure is
silent: a conversion that loses a third turns a valid board into one whose pitching column no longer
adds up to the defensive innings, and nothing upstream says why.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from boxscore_package.innings import InningsError, enterable_fractions, from_display, to_display


class TestTheGoldenValues:
    @pytest.mark.parametrize(
        ("outs", "printed"),
        [
            (0, "0.0"),
            (1, "0.1"),
            (2, "0.2"),
            (3, "1.0"),
            (13, "4.1"),  # four innings and one out
            (26, "8.2"),
            (27, "9.0"),  # a complete game
            (40, "13.1"),  # extra innings
        ],
    )
    def test_outs_print_as_the_board_shows_them(self, outs: int, printed: str) -> None:
        assert to_display(outs) == printed

    @pytest.mark.parametrize(
        ("outs", "printed"),
        [(0, "0.0"), (1, "0.1"), (2, "0.2"), (3, "1.0"), (13, "4.1"), (26, "8.2"), (27, "9.0")],
    )
    def test_and_read_back_to_the_same_outs(self, outs: int, printed: str) -> None:
        assert from_display(printed) == outs

    def test_a_whole_inning_keeps_its_trailing_zero(self) -> None:
        # A column where some rows read "4.1" and others read "4" does not line up, and the trailing
        # digit is the part carrying the information.
        assert to_display(12) == "4.0"


class TestItRefusesWhatBaseballDoesNotWrite:
    @pytest.mark.parametrize("text", [".3", "4.3", "4.7", "0.9"])
    def test_a_fraction_of_three_outs_or_more(self, text: str) -> None:
        # Three outs is a whole inning, so `.3` is not a hard value to reach — it does not exist.
        with pytest.raises(InningsError):
            from_display(text)

    @pytest.mark.parametrize("text", ["", "four", "4.1.2", "-1", "4,1", "4.10"])
    def test_anything_that_is_not_innings_at_all(self, text: str) -> None:
        with pytest.raises(InningsError):
            from_display(text)

    def test_negative_outs_have_no_printed_form(self) -> None:
        with pytest.raises(InningsError):
            to_display(-1)

    def test_a_bare_whole_number_is_accepted_as_whole_innings(self) -> None:
        # Not required of the keypad, which always sends a fraction, but a value arriving from
        # anywhere else should mean the obvious thing rather than be refused on a technicality.
        assert from_display("4") == 12


class TestTheKeypadDomain:
    def test_it_offers_two_fractions_and_no_decimal_point(self) -> None:
        # A decimal-point key would let `.3` through `.9` be typed and then rejected. Two explicit
        # keys make the domain visible and wrong values unenterable rather than merely refused.
        assert enterable_fractions() == (".1", ".2")


class TestTheRoundTripHolds:
    @given(outs=st.integers(0, 200))
    def test_every_out_count_survives_the_journey(self, outs: int) -> None:
        assert from_display(to_display(outs)) == outs
