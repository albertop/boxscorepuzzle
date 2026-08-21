"""Where the publish path gets the signing key, and what it refuses. (v36-P3-29)

⚠️⚠️ **The document recommended persisting this key as a User-scope environment variable**, which hands
it to every process the account runs — every `npm install` postinstall, every pip build hook, every
script from every sibling project on a machine that holds several. **This is the one secret in the
project that cannot be rotated cheaply**: rotating invalidates every signature ever issued, so every
package and every manifest has to be reissued. What the permanent variable bought was avoiding
*"publish failed, you forgot to set it"* — which this script already raises loudly by design.

So the writer reads the key file at the moment of use, and no export is needed. These tests pin the
order and the refusals, because *where a secret comes from* is exactly the kind of thing that gets
loosened by a convenience patch and noticed by nobody.

⚠️ **Every key here is generated in the test.** §33: the real private key never enters a test, a
fixture, or the repository.
"""

import pathlib
import sys
from collections.abc import Iterator

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SCRIPTS = _ROOT / "forge" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import write_reference_puzzles as writer  # noqa: E402


def _material() -> str:
    """64 hex characters of a key that exists for one test and is worth nothing to anybody."""
    return Ed25519PrivateKey.generate().private_bytes_raw().hex()


@pytest.fixture
def elsewhere(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[pathlib.Path]:
    """A key file under `tmp_path`, no inherited variable, and a pin these keys can satisfy.

    ⚠️ `delenv` first and unconditionally: this suite runs on the operator's laptop, where the real
    variable **is** set, and a test that silently read it would be testing the machine rather than
    the code — passing for the wrong reason on the one machine where it matters.

    ⚠️⚠️ **`PINNED_PUBLIC_KEY` is redirected too, and that is a finding rather than a workaround.**
    The first version of this file did not, and every acquisition test failed on *"does not match the
    key serve pins"* — the outage guard doing exactly its job against a key that is not the forge's.
    Redirecting the pin is what lets these tests use a throwaway key at all; the alternative is
    putting the real private key in a test, which §33 forbids and which is the thing this item is
    about. `test_reference_batch.py` is where the *real* pin is asserted.
    """
    monkeypatch.delenv(writer.KEY_VARIABLE, raising=False)
    path = tmp_path / ".boxscorepuzzle-signing-key"
    monkeypatch.setattr(writer, "KEY_FILE", path)
    monkeypatch.setattr(writer, "PINNED_PUBLIC_KEY", tmp_path / "pinned.hex")
    yield path


def _pin(material: str) -> str:
    """Write the public half of `material` where the writer looks for the pin, and return it."""
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(material))
    writer.PINNED_PUBLIC_KEY.write_text(key.public_key().public_bytes_raw().hex(), encoding="utf-8")
    return material


class TestWhereTheKeyComesFrom:
    def test_the_file_is_enough_with_no_variable_set(self, elsewhere: pathlib.Path) -> None:
        """The point of the change: a publish needs no export, so the key need not be inherited."""
        wanted = _pin(_material())
        elsewhere.write_text(wanted + "\n", encoding="utf-8")

        key, _ = writer.key_and_destination()

        assert key.private_bytes_raw().hex() == wanted

    def test_a_deliberate_export_wins_over_the_file(
        self, elsewhere: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An export is an instruction; a file in the home directory is only where the key is kept."""
        exported = _pin(_material())
        elsewhere.write_text(_material(), encoding="utf-8")
        monkeypatch.setenv(writer.KEY_VARIABLE, exported)

        key, _ = writer.key_and_destination()

        assert key.private_bytes_raw().hex() == exported

    def test_trailing_whitespace_in_the_file_is_not_a_different_key(self, elsewhere: pathlib.Path) -> None:
        """⚠️ The generator writes with `write_text` and editors add newlines. `from_private_bytes`
        would refuse the untrimmed string with *not hexadecimal*, which names the wrong problem."""
        wanted = _pin(_material())
        elsewhere.write_text(f"  {wanted}  \r\n", encoding="utf-8")

        key, _ = writer.key_and_destination()

        assert key.private_bytes_raw().hex() == wanted


class TestWhatItRefuses:
    def test_neither_source_is_an_error_naming_both(self, elsewhere: pathlib.Path) -> None:
        """⚠️ Fail closed, and say which two places were looked at — a message naming only the
        variable is what teaches the next person to export the secret."""
        with pytest.raises(SystemExit) as refusal:
            writer.key_and_destination()

        assert writer.KEY_VARIABLE in str(refusal.value)
        assert str(elsewhere) in str(refusal.value)

    def test_an_unreadable_key_file_is_an_error_rather_than_a_missing_key(self, elsewhere: pathlib.Path) -> None:
        """⚠️⚠️ The absence of a check must not read as the check passing.

        A directory where the file should be is unreadable as text. Falling through to *no signing
        key* would report the wrong problem and invite an export as the workaround — which is the
        exposure this whole item removes.
        """
        elsewhere.mkdir()

        with pytest.raises(SystemExit) as refusal:
            writer.key_and_destination()

        assert "could not be read" in str(refusal.value)

    # ⚠️ Wanted for its side effects, not its value: the fixture clears the inherited variable and
    # redirects both paths, so this refusal is about the flag rather than about the laptop.
    @pytest.mark.usefixtures("elsewhere")
    def test_ephemeral_still_refuses_to_guess_when_the_variable_is_exported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(writer.KEY_VARIABLE, _material())

        with pytest.raises(SystemExit) as refusal:
            monkeypatch.setattr(sys, "argv", ["writer", "--ephemeral"])
            writer.key_and_destination()

        assert "--ephemeral" in str(refusal.value)

    def test_ephemeral_is_not_blocked_by_the_key_file_merely_existing(
        self, elsewhere: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """⚠️ The asymmetry, asserted rather than assumed.

        The key file exists on every machine that has a key, so weighing it the way the variable is
        weighed would make `--ephemeral` impossible exactly where it is used.
        """
        elsewhere.write_text(_material(), encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["writer", "--ephemeral"])

        key, destination = writer.key_and_destination()

        assert key.private_bytes_raw().hex() != elsewhere.read_text(encoding="utf-8").strip()
        assert destination != writer.OUT, "an ephemeral batch must not target the served directory"
