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

HMAC-SHA256 with a shared secret rather than a public-key signature: both ends are ours, one key
lives on the laptop and one on the VPS, and there is no third party who needs to verify anything.
"""

import hmac
import json
from hashlib import sha256
from typing import Final

from boxscore_package.format import Package

_ENCODING: Final = "utf-8"


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


def sign(package: Package, secret: bytes) -> Package:
    """Return the package carrying its signature. The original is left alone."""
    digest = hmac.new(secret, canonical_bytes(package), sha256).hexdigest()
    return type(package)(
        puzzle_id=package.puzzle_id,
        puzzle=package.puzzle,
        solution=package.solution,
        labels=package.labels,
        pitcher_labels=package.pitcher_labels,
        reveal=package.reveal,
        metadata=package.metadata,
        schema=package.schema,
        signature=digest,
    )


def verify(package: Package, secret: bytes) -> None:
    """Raise unless the package still matches its signature.

    Raises rather than returning a boolean on purpose: a caller can ignore a `False` by forgetting to
    look at it, and this is the check standing between a corrupted transfer and a served puzzle.
    """
    if package.signature is None:
        message = f"puzzle {package.puzzle_id} carries no signature"
        raise SignatureError(message)
    expected = hmac.new(secret, canonical_bytes(package), sha256).hexdigest()
    # Constant-time comparison. The threat here is corruption rather than forgery, but a timing-safe
    # compare costs nothing and the habit is worth more than the reasoning about whether it matters.
    if not hmac.compare_digest(expected, package.signature):
        message = f"puzzle {package.puzzle_id} does not match its signature"
        raise SignatureError(message)
