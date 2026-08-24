"""Every `${NAME}` the nginx template uses is substituted by the deployment's own filter.

⚠️⚠️ **The failure this exists for has no error message anywhere.** `envsubst` replaces only the names
`NGINX_ENVSUBST_FILTER` matches and **leaves the rest as literal text** — so a placeholder the filter
misses reaches nginx as the eight characters `${NAME}`. nginx then refuses to start, or worse accepts it
as a value, and the container is dead or subtly wrong for a reason the logs describe as a syntax error
somewhere else entirely.

**It is the shape this project meets most often**: two places that must agree — the template's
placeholders and the filter that substitutes them — with nothing checking they do. They live in
different files, in different trees, edited for different reasons.

⚠️ **`resolver ${NGINX_LOCAL_RESOLVERS}` is the instance that produced this test.** The resolver had
been the literal `127.0.0.11`, which is Docker's embedded DNS and correct **only** on a user-defined
network; on the default bridge it is something else entirely. Deriving it meant adding a placeholder,
which meant widening a filter that had been deliberately narrowed so nginx's own `$host` and `$1`
survive. **Widening it and forgetting is a 502 on `/api/` while every other route works** -- a site that
looks healthy and silently loses the event record C7 calls irreversible.

⚠️ Seen red before being believed: with the filter back at `^KEEP_`, this reports
`NGINX_LOCAL_RESOLVERS is used by the template and the filter does not match it`.
"""

import re
from pathlib import Path

from tests.conftest import NGINX_ENVIRONMENT

_TEMPLATE = Path(__file__).resolve().parents[2] / "deploy" / "nginx" / "boxscorepuzzle.conf.template"

_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
"""`${NAME}`, which is what `envsubst` acts on. A bare `$name` is nginx's own variable and is not
touched -- which is the whole reason the filter exists."""


def _used() -> set[str]:
    """The names the template asks to be substituted, from the served file rather than from memory."""
    return set(_PLACEHOLDER.findall(_TEMPLATE.read_text(encoding="utf-8")))


def test_the_template_uses_placeholders_at_all() -> None:
    """⚠️ A check over an empty set passes forever. Assert the subject is there before judging it."""
    assert _used(), f"no ${{NAME}} placeholders in {_TEMPLATE}; this test would pass over nothing"


def test_every_placeholder_is_covered_by_the_filter() -> None:
    """The deployment's filter, read from `deploy/compose.yaml`, against the template's own names."""
    pattern = re.compile(NGINX_ENVIRONMENT["NGINX_ENVSUBST_FILTER"])
    for name in sorted(_used()):
        assert pattern.match(name), (
            f"{name} is used by the template and the filter does not match it. "
            f"envsubst would leave the literal ${{{name}}} in the config nginx starts with."
        )


def test_the_local_resolver_is_derived_rather_than_written_down() -> None:
    """⚠️⚠️ **A literal address here is right where it was tested and wrong anywhere else.**

    `127.0.0.11` is Docker's embedded DNS and only exists on a user-defined network. Measured on the
    image: a user-defined network answers `127.0.0.11`, the default bridge answers something else. The
    entrypoint computes the real one from `/etc/resolv.conf`, and this asserts the template takes it.
    """
    config = _TEMPLATE.read_text(encoding="utf-8")
    resolvers = [line.strip() for line in config.splitlines() if line.strip().startswith("resolver ")]

    assert resolvers, "no resolver directive; the proxy to keep cannot resolve a name without one"
    for line in resolvers:
        assert "${NGINX_LOCAL_RESOLVERS}" in line, f"a written-down resolver address: {line}"


def test_the_entrypoint_is_told_to_compute_it() -> None:
    """⚠️ Without this the image's `15-local-resolvers.envsh` returns immediately, the variable is never
    exported, and the template keeps a literal `${NGINX_LOCAL_RESOLVERS}` that nginx refuses."""
    assert NGINX_ENVIRONMENT.get("NGINX_ENTRYPOINT_LOCAL_RESOLVERS") == "1"
