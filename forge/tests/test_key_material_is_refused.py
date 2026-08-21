"""What `signing.py` refuses, and what `verifying_key` is for. (coverage of the rejection paths)

⚠️⚠️ **These were the least-covered lines in the tree — 85% — and they are all rejections.** That is
the worst place for a gap: this project's standing rule is that **the absence of a check reads as the
presence of a passing one**, and an untested rejection path is a check nobody has watched fail. A
`raise` that was deleted, or narrowed to a condition that never holds, would leave every test green
and every malformed key accepted.

⚠️ **`verifying_key` had no test at all.** It is the function `serve` uses, and the asymmetry it
carries — verify, never sign — is §33's whole argument for a key pair over an HMAC. It was covered by
nothing.

⚠️ Every key here is generated or hand-built in the test. The real private key never enters a test,
a fixture, or the repository (§33).
"""

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from boxscore_package.signing import (
    KEY_BYTES,
    SignatureError,
    signing_key,
    verify_manifest,
    verifying_key,
)


def _pair() -> tuple[str, str]:
    """A throwaway pair as the two hex strings the loaders take."""
    private = Ed25519PrivateKey.generate()
    return private.private_bytes_raw().hex(), private.public_key().public_bytes_raw().hex()


class TestTheTwoHalvesLoadAndDoDifferentThings:
    def test_the_public_half_verifies_what_the_private_half_signed(self) -> None:
        private_hex, public_hex = _pair()
        signed = signing_key(private_hex).sign(b"a package")

        verifying_key(public_hex).verify(signed, b"a package")

    def test_the_public_half_cannot_sign(self) -> None:
        """⚠️⚠️ The property §33 chose a key pair for, asserted rather than described.

        Every verifier of an HMAC is also a signer, so a shared secret on the VPS **was** the forge's
        signing authority. This is what makes the deployed key harmless if it leaks.
        """
        _, public_hex = _pair()
        key = verifying_key(public_hex)

        assert isinstance(key, Ed25519PublicKey)
        assert not hasattr(key, "sign")

    def test_the_two_loaders_refuse_each_other_s_half(self) -> None:
        """A private key where a public one is expected is 32 bytes of valid hex, so nothing about the
        *material* catches it — only the curve does."""
        private_hex, public_hex = _pair()

        assert verifying_key(public_hex).public_bytes_raw().hex() == public_hex
        assert signing_key(private_hex).private_bytes_raw().hex() == private_hex


class TestMalformedKeyMaterialIsRefused:
    @pytest.mark.parametrize("load", [signing_key, verifying_key])
    def test_material_that_is_not_hexadecimal_is_refused(self, load: object) -> None:
        with pytest.raises(SignatureError, match="not hexadecimal"):
            load("zz" * KEY_BYTES)  # type: ignore[operator]

    @pytest.mark.parametrize("load", [signing_key, verifying_key])
    @pytest.mark.parametrize("length", [KEY_BYTES - 1, KEY_BYTES + 1, 0])
    def test_material_of_the_wrong_length_is_refused(self, load: object, length: int) -> None:
        """⚠️ Both directions and zero. A guard written as `> KEY_BYTES` would pass a short key, and a
        short key is the one an accidental truncation produces."""
        with pytest.raises(SignatureError, match=f"is {length} bytes, expected {KEY_BYTES}"):
            load("ab" * length)  # type: ignore[operator]

    @pytest.mark.parametrize(("load", "which"), [(signing_key, "signing"), (verifying_key, "verifying")])
    def test_the_refusal_names_which_key_it_was(self, load: object, which: str) -> None:
        """⚠️ The label is the only thing distinguishing two identical messages, and an operator
        reading *the key is not hexadecimal* needs to know which of the two they mistyped."""
        with pytest.raises(SignatureError, match=f"the {which} key"):
            load("nothex")  # type: ignore[operator]

    def test_bytes_and_str_are_the_same_material(self) -> None:
        """The environment hands over `str` and a file read as bytes hands over `bytes`."""
        private_hex, _ = _pair()

        assert signing_key(private_hex).private_bytes_raw() == signing_key(private_hex.encode()).private_bytes_raw()

    def test_surrounding_whitespace_is_not_a_different_key(self) -> None:
        """A key file written with a trailing newline is the ordinary case, not an edge one."""
        private_hex, _ = _pair()

        assert signing_key(f"  {private_hex}\n").private_bytes_raw().hex() == private_hex


class TestAManifestWithoutASignatureIsRefused:
    """⚠️⚠️ **Only the manifest says the *set* is genuine.**

    A signature per puzzle says each puzzle is real; altering the manifest — omitting ids, pointing at
    a retained generation, pointing at nothing — breaks no package signature at all. So a manifest that
    arrives unsigned must be a refusal rather than a skipped check.
    """

    def test_a_manifest_carrying_no_signature_is_refused(self) -> None:
        _, public_hex = _pair()

        with pytest.raises(SignatureError, match="carries no signature"):
            verify_manifest({"generation": "abc", "puzzles": []}, verifying_key(public_hex))

    @pytest.mark.parametrize("signature", [None, 1, [], {}])
    def test_a_signature_that_is_not_a_string_is_refused(self, signature: object) -> None:
        """⚠️ `if not signature` would accept `0` and reject a genuine empty-but-present field for the
        wrong reason. The check is about the type, and these are what a malformed document holds."""
        _, public_hex = _pair()

        with pytest.raises(SignatureError, match="carries no signature"):
            verify_manifest({"puzzles": [], "signature": signature}, verifying_key(public_hex))
