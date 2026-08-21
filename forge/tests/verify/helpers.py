"""What every verify test needs, defined once. (v36-P3-08)

⚠️⚠️ **`refs()` stood in seven files, byte for byte, and its own docstring records that it once carried
a defect.** It invented a tenth batting-order slot — `"10"`, `"11"` — which is not a reference a lineup
can have, and only the stricter constructor noticed that the fixtures had been carrying impossible
values. **With seven copies the next such fix has to land seven times**, and the six that were missed
would go on producing boards the format forbids while their tests stayed green.

The key pair stood in four of the same files. It is generated per run rather than checked in, and one
pair for the session is one fact rather than four.

⚠️ **Imported rather than turned into fixtures**, which the review suggested and which would be the
more idiomatic pytest. `refs()` has 42 call sites; a fixture means editing 42 test signatures to gain
nothing the import does not already give — one definition, one place to fix it. `tests.strategies` and
`tests.reveals` are shared the same way.
"""

from string import ascii_lowercase

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

_KEY = Ed25519PrivateKey.generate()

SECRET = _KEY
"""⚠️ **A key pair, not a shared secret.** The forge signs with the private half and `serve` verifies
with the public one, which is the property a MAC cannot express: every verifier of an HMAC is also a
signer, so the verification key on the VPS *was* the signing authority (§33). Generated per run — a
test key checked into the repository is a key anybody can sign with."""

PUBLIC = _KEY.public_key()

_LINEUP_SLOTS = 9
"""Nine places in a batting order. Not a roster cap — the rows above nine are men who followed one
another in a slot, which is what the letter distinguishes."""


def refs(board: object) -> tuple[str, ...]:
    """One slot reference per batting row, in the shape the format actually allows.

    ⚠️ **This produced `"10"`, `"11"`… and those are not references.** A lineup has nine slots; a
    thirteen-row board carries thirteen references drawn from those nine, and what distinguishes rows
    inside a slot is the letter. The helper invented a tenth slot, and only the stricter constructor
    noticed — the fixtures had been carrying impossible values.
    """
    return tuple(
        str(index + 1) if index < _LINEUP_SLOTS else f"9{ascii_lowercase[index - _LINEUP_SLOTS]}"
        for index in range(len(board.batting))  # type: ignore[attr-defined]
    )
