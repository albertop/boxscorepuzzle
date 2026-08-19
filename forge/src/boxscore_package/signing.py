"""Signing the package, so a corrupted or truncated one is caught rather than served.

§22 requires every published puzzle to be signed and the signature checked before serving, against
post-generation corruption. §33 widens that: the laptop is the only machine that can produce puzzles
and the transfer to the VPS is a file copy, so **an interrupted upload has to be as loud as a
tampered file**. A truncated JSON document usually fails to parse; one that happens to stay parseable
is exactly the case a signature catches and nothing else does.

**Signed over canonical bytes, not over the file.** Two files can hold the same package with
different whitespace or key order, and a signature over raw bytes would reject the innocent case
while a signature over a re-serialisation of the parsed content accepts it. The canonical form is
compact JSON with sorted keys, so it is reproducible from the parsed package alone.

**The signature covers the published half.** That is what travels and what serve holds, so that is
what a receiver can check; the source boxscore never leaves the forge and is excluded on purpose —
including it would make the signature unverifiable at the only place it matters.

⚠️ **HMAC is the wrong primitive here, and the reason it was chosen answers a question nobody asked.**
The note this replaces said a public-key signature was unnecessary because both ends are ours and
there is no third party who needs to verify anything. That is about *who needs to verify*. The
property §33 actually needs is about *who can produce*: the forge laptop is the only machine allowed
to make inventory and the service may only serve what it received.

A MAC cannot express that. Every verifier of an HMAC is also a signer, so the verification secret on
the VPS **is** the forge's signing authority. Read access to a deployment backup, a diagnostic dump or
the environment is enough to mint a package with altered answers, altered reveal text or altered
metadata that the service cannot tell from a real one.

Nothing is wrong with SHA-256 or `compare_digest`. The defect is authority placement, and the fix is
an asymmetric signature — Ed25519, private key on the forge, public key deployed to `serve`, with a
key id in the signed envelope so it can be rotated.

**Done.** Ed25519: the forge holds the private key, `serve` holds the public one and cannot sign, and
the signature is 128 hex characters. The manifest is signed as well as the packages.
"""

import json
from typing import Final

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from boxscore_package.format import Package

_ENCODING: Final = "utf-8"
KEY_BYTES: Final = 32
"""An Ed25519 key is 32 bytes, so 64 hex characters. Signatures are 64 bytes, 128 hex."""


class SignatureError(Exception):
    """The package is not what it was when it was signed, or was never signed."""


def canonical_bytes(package: Package) -> bytes:
    """The exact bytes the signature covers: the published half, compact, keys sorted.

    ⚠️ **The solution and the reveal are inside it now.** They used to be stripped before signing,
    because the published half did not carry them — and §23 has since put them in the file, since a
    client with the backend down cannot fetch a name when a row is completed. Anything that travels
    is signed; a solution outside the signature would be a board a corrupted transfer could alter
    without the check noticing, which is exactly what §33 wants caught.
    """
    document = package.published().as_json()
    document.pop("signature", None)
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode(_ENCODING)


def signing_key(raw: str | bytes) -> Ed25519PrivateKey:
    """The forge's private key, from 64 hex characters. **Never leaves the laptop** (§33)."""
    return Ed25519PrivateKey.from_private_bytes(_key_bytes(raw, "signing"))


def verifying_key(raw: str | bytes) -> Ed25519PublicKey:
    """The public key `serve` holds. It verifies and **cannot sign**, which is the whole point."""
    return Ed25519PublicKey.from_public_bytes(_key_bytes(raw, "verifying"))


def _key_bytes(raw: str | bytes, which: str) -> bytes:
    text = raw.decode(_ENCODING) if isinstance(raw, bytes) else raw
    try:
        material = bytes.fromhex(text.strip())
    except ValueError as error:
        message = f"the {which} key is not hexadecimal"
        raise SignatureError(message) from error
    if len(material) != KEY_BYTES:
        message = f"the {which} key is {len(material)} bytes, expected {KEY_BYTES}"
        raise SignatureError(message)
    return material


def sign(package: Package, key: Ed25519PrivateKey) -> Package:
    """Return the package carrying its signature. The original is left alone."""
    signature = key.sign(canonical_bytes(package)).hex()
    return type(package)(
        puzzle_id=package.puzzle_id,
        puzzle=package.puzzle,
        solution=package.solution,
        labels=package.labels,
        pitcher_labels=package.pitcher_labels,
        reveal=package.reveal,
        slot_references=package.slot_references,
        metadata=package.metadata,
        schema=package.schema,
        signature=signature,
    )


def verify(package: Package, key: Ed25519PublicKey) -> None:
    """Raise unless the package still matches its signature.

    Raises rather than returning a boolean on purpose: a caller can ignore a `False` by forgetting to
    look at it, and this is the check standing between a corrupted transfer and a served puzzle.
    """
    if package.signature is None:
        message = f"puzzle {package.puzzle_id} carries no signature"
        raise SignatureError(message)
    try:
        key.verify(bytes.fromhex(package.signature), canonical_bytes(package))
    except (InvalidSignature, ValueError) as error:
        message = f"puzzle {package.puzzle_id} does not match its signature"
        raise SignatureError(message) from error


def sign_manifest(document: dict[str, object], key: Ed25519PrivateKey) -> dict[str, object]:
    """The manifest signed the same way the packages are.

    ⚠️ **The manifest is what decides the delivery**, and altering it breaks no package signature: omit
    ids, point at a retained generation, point at nothing, and every package the client does receive
    still checks out. A signature on each puzzle says each puzzle is genuine; only this says the *set*
    is.
    """
    body = {key_: value for key_, value in document.items() if key_ != "signature"}
    signed = dict(body)
    signed["signature"] = key.sign(_canonical(body)).hex()
    return signed


def verify_manifest(document: dict[str, object], key: Ed25519PublicKey) -> None:
    signature = document.get("signature")
    if not isinstance(signature, str):
        message = "the manifest carries no signature"
        raise SignatureError(message)
    body = {key_: value for key_, value in document.items() if key_ != "signature"}
    try:
        key.verify(bytes.fromhex(signature), _canonical(body))
    except (InvalidSignature, ValueError) as error:
        message = "the manifest does not match its signature"
        raise SignatureError(message) from error


def _canonical(document: dict[str, object]) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode(_ENCODING)
