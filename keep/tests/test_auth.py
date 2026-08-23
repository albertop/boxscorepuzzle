"""The shared token, and the refusals that make it worth having.

⚠️⚠️ **Every test here is a refusal**, which is the class `CLAUDE.md` says must be exercised: a check
that never fires is indistinguishable from one that is broken. The one that matters most is the first —
**no token configured means the service does not start**, never *accept everything*.
"""

import pytest

from keep.auth import MINIMUM_LENGTH, TOKEN_VARIABLE, MisconfiguredError, accepted, configured_token, presented

GOOD = "b" * MINIMUM_LENGTH


class TestStartingUp:
    def test_a_configured_token_is_returned(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(TOKEN_VARIABLE, GOOD)

        assert configured_token() == GOOD

    def test_no_token_refuses_to_start(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # ⚠️⚠️ **The whole point.** A service that accepted everything because none was configured is
        # verification passing when its secret is missing — the absence of a check reading as the
        # presence of a passing one, which CLAUDE.md puts at the top of the list.
        monkeypatch.delenv(TOKEN_VARIABLE, raising=False)

        with pytest.raises(MisconfiguredError, match="does not start"):
            configured_token()

    def test_an_empty_token_is_the_same_as_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # `KEEP_SHARED_TOKEN=` in a compose file is the likeliest way to arrive here, and it must not be
        # a quieter mode than leaving the variable out.
        monkeypatch.setenv(TOKEN_VARIABLE, "")

        with pytest.raises(MisconfiguredError, match="does not start"):
            configured_token()

    def test_a_short_token_refuses_to_start(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # ⚠️ The floor is not theatre: this refusal is the only thing between an unpublished port and
        # whatever else ends up on that network, and a four-character token passes every other check.
        monkeypatch.setenv(TOKEN_VARIABLE, "short")

        with pytest.raises(MisconfiguredError, match="characters"):
            configured_token()

    def test_the_refusal_names_the_variable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A container that will not come up is only useful if the log says which variable to set.
        monkeypatch.delenv(TOKEN_VARIABLE, raising=False)

        with pytest.raises(MisconfiguredError, match=TOKEN_VARIABLE):
            configured_token()


class TestReadingTheHeader:
    def test_a_bearer_token_is_taken(self) -> None:
        assert presented(f"Bearer {GOOD}") == GOOD

    def test_the_scheme_is_case_insensitive(self) -> None:
        # `bearer` is what some clients send and it is the same scheme.
        assert presented(f"bearer {GOOD}") == GOOD

    @pytest.mark.parametrize("header", [None, "", GOOD, f"Basic {GOOD}", "Bearer"])
    def test_anything_else_yields_nothing(self, header: str | None) -> None:
        # ⚠️ Absent, malformed and wrong-scheme all become `""`, which `accepted` rejects. They are not
        # distinguished in the response either: telling a caller *which* way it was wrong tells an
        # attacker how close they are.
        assert presented(header) == ""


class TestComparing:
    def test_the_right_token_is_accepted(self) -> None:
        assert accepted(GOOD, GOOD) is True

    def test_a_wrong_token_is_not(self) -> None:
        assert accepted("c" * MINIMUM_LENGTH, GOOD) is False

    def test_an_empty_offer_is_not(self) -> None:
        # ⚠️ The case that would matter if the expected token were ever empty: `compare_digest("", "")`
        # is true, so an empty offer against an empty expectation would let everyone in. `configured_token`
        # refuses to start in that situation and this refuses independently — two layers, and the outer
        # one is not a substitute for the inner.
        assert accepted("", "") is False

    def test_a_prefix_of_the_right_token_is_not_accepted(self) -> None:
        assert accepted(GOOD[:-1], GOOD) is False
