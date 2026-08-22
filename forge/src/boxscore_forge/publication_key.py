"""Getting the forge's private key, and refusing to sign with the wrong one.

**One definition, because two producers now need it.** `write_reference_puzzles.py` held this inside
`key_and_destination()`, which also chose a destination and handled `--ephemeral`; the batch producer
that fills the calendar needs the key half and nothing else, and a second copy of *where the key comes
from* is the one duplication in this repository that fails as a five-month outage rather than as a bug.

⚠️⚠️ **It never returns a key that `serve` would refuse.** Self-verification uses the public half of the
key that just signed, which proves the batch is internally consistent and **nothing about whether the
deployed reader will accept it** — a valid Ed25519 key that is not *the* key produces exactly the same
outage, by accident. So the offered key is checked against the one `serve` pins, before anything is
written.

⚠️ **Fail closed.** No key is an error, never a quiet fallback to a generated one: `CLAUDE.md` puts
verification that passes when its secret is missing at the top of the list, because *the absence of a
check reads as the presence of a passing one*. A throwaway key is something a caller asks for
explicitly and writes somewhere `serve` does not read.

⚠️ **Nothing here prints key material.** The public half is printable and the private half never is —
not in an error, not in a log, not truncated.
"""

import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from boxscore_package.signing import signing_key

_ROOT = Path(__file__).resolve().parents[3]

KEY_VARIABLE = "BOXSCORE_SIGNING_KEY"
KEY_FILE = Path.home() / ".boxscorepuzzle-signing-key"
"""⚠️ Outside the repository, and outside any directory a deploy copies. An exported variable is
inherited by every process on the machine; a file read at the moment it is needed is not."""

PINNED_PUBLIC_KEY = _ROOT / "serve" / "data" / "signing-public-key.hex"
"""What the client verifies against. **The authority on which key is the right one** — a producer that
checked against its own public half would be agreeing with itself."""


def publication_key() -> Ed25519PrivateKey:
    """The key `serve` pins, or a refusal that says which half is missing.

    Reads `BOXSCORE_SIGNING_KEY` first, then the key file. **Both absent is an error**, and so is a key
    that does not match the pinned public half.
    """
    material = os.environ.get(KEY_VARIABLE, "")
    if not material and KEY_FILE.exists():
        try:
            material = KEY_FILE.read_text(encoding="utf-8").strip()
        except OSError as error:
            message = f"{KEY_FILE} exists and could not be read: {error}"
            raise SystemExit(message) from error
    if not material:
        message = (
            f"no signing key: {KEY_VARIABLE} is unset and {KEY_FILE} does not exist. Publishing needs "
            "the forge's private key, 64 hex characters."
        )
        raise SystemExit(message)

    key = signing_key(material)
    pinned = PINNED_PUBLIC_KEY.read_text(encoding="utf-8").strip()
    offered = key.public_key().public_bytes_raw().hex()
    if offered != pinned:
        message = (
            f"the key offered does not match the key serve pins in {PINNED_PUBLIC_KEY.name}. "
            f"Publishing with it would produce inventory serve refuses, which is an outage rather "
            f"than a rejected file. Offered {offered[:16]}..., pinned {pinned[:16]}..."
        )
        raise SystemExit(message)
    return key
