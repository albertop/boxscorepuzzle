"""The shared token between `serve` and `keep`, and the refusals that make it worth having.

**`docs/data-layer.md` §4.** They sit on the same Docker network and both belong to the operator, so
mutual certificates would be disproportionate — and a mechanism nobody can rotate confidently is worse
than a simpler one that gets rotated.

⚠️⚠️ **Two conditions, and neither is advisory:**

- **Fail closed. No token configured means the service does not start.** Never *accept everything
  because there is no token* — that is verification passing when its secret is missing, which
  `CLAUDE.md` puts at the top of the list: **the absence of a check reading as the presence of a passing
  one.** It refuses at startup rather than at the first request, so a misconfiguration is a container
  that will not come up instead of an open door nobody notices.
- **The port is not published to the host.** The token is the second line, not the first.
"""

import hmac
import os

# The *name* of an environment variable is not a secret, whatever a pattern matcher thinks.
TOKEN_VARIABLE = "KEEP_SHARED_TOKEN"  # noqa: S105

MINIMUM_LENGTH = 32
"""Short enough to type and long enough not to be guessed. ⚠️ A length floor is not security theatre
here: the refusal below is the only thing standing between an unpublished port and whatever else ends up
on that Docker network, and a four-character token would pass every other check in this file."""


class MisconfiguredError(RuntimeError):
    """The service cannot start. **Raised at startup, never turned into a permissive default.**"""


def configured_token() -> str:
    """The token this service will accept, or a refusal to start.

    ⚠️ **Read once at startup rather than per request.** A token read per request means a service whose
    security posture changes when somebody edits the environment of a running container — and, worse,
    that an empty variable turns into *accept nothing* silently rather than *do not start* loudly.
    """
    token = os.environ.get(TOKEN_VARIABLE, "")
    if not token:
        message = (
            f"{TOKEN_VARIABLE} is not set. keep does not start without it: a service that accepted "
            f"everything because no token was configured would be an open door that looks like a "
            f"working deployment."
        )
        raise MisconfiguredError(message)
    if len(token) < MINIMUM_LENGTH:
        message = f"{TOKEN_VARIABLE} is {len(token)} characters; at least {MINIMUM_LENGTH} are needed."
        raise MisconfiguredError(message)
    return token


def presented(header: str | None) -> str:
    """The token out of an `Authorization: Bearer ...` header, or the empty string.

    ⚠️ An absent header, a malformed one and a wrong scheme all return `""`, which the comparison below
    rejects. **They are not distinguished in the response either**: telling a caller *which* way it was
    wrong tells an attacker how close they are.
    """
    if not header:
        return ""
    scheme, _, value = header.partition(" ")
    return value.strip() if scheme.lower() == "bearer" else ""


def accepted(offered: str, expected: str) -> bool:
    """Whether the caller may proceed.

    ⚠️ **`compare_digest`, not `==`.** A plain comparison returns as soon as two bytes differ, so how
    long it takes says how much of the token was right — recoverable one character at a time over enough
    requests. The service is on an internal network, which makes the attack unlikely and not impossible,
    and the correct comparison costs one import.
    """
    return bool(offered) and hmac.compare_digest(offered, expected)
