"""The two Dockerfiles build, start, and answer. **The check whose absence let a broken image ship.**

⚠️⚠️ **`deploy/serve.Dockerfile` could not be built at all and nothing noticed.** It copied
`boxscorepuzzle.conf`, which had been renamed to `.conf.template` when `${KEEP_SHARED_TOKEN}` arrived,
into `conf.d/` — which is not the path the entrypoint substitutes, so even a build that succeeded would
have handed nginx an unresolved placeholder. **v41-P1-01.**

**It survived because the nginx tests mount the template directly.** They exercise the product's
configuration by a path the product does not use, which is a working instrument aimed one question
short: *is this config right* rather than *does the thing we ship serve it*. `keep`'s image was built
and probed by hand and was fine; this one had never been built.

⚠️ **And building is not enough either.** The first build that succeeded produced a container that died
on start — the pid-path `sed` matched nothing because this image writes `/run/nginx.pid` and the pattern
said `/var/run/`. **A substitution that finds nothing is silent.** So these start the container and ask
it for pages.

⚠️ Skipped with the reason when there is no container runtime. A skip that reads like a pass is the
shape this project keeps closing.
"""

import json
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

from tests.conftest import DOCKER_PREFIX

_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC = _ROOT / "serve" / "data" / "puzzles"


def _docker(*arguments: str, check: bool = True, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    finished = subprocess.run(["docker", *arguments], capture_output=True, text=True, check=False, timeout=timeout)
    if check and finished.returncode != 0:
        message = f"docker {' '.join(arguments[:2])} failed ({finished.returncode}): {finished.stderr[-500:]}"
        raise AssertionError(message)
    return finished


def _available() -> str | None:
    try:
        finished = _docker("info", "--format", "{{.ServerVersion}}", check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"docker is not runnable here: {error}"
    if finished.returncode != 0:
        return f"docker is installed and not serving: {finished.stderr.strip()[:120]}"
    return None


def _free_port() -> int:
    import socket  # noqa: PLC0415

    with closing(socket.socket()) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _get(port: int, path: str, *, tries: int = 80) -> tuple[int, str]:
    """A real request, retried. ⚠️ Never an open socket: Docker's forwarder binds before the container
    accepts and then resets what it accepted (`CLAUDE.md`)."""
    for _attempt in range(tries):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as response:
                return response.status, response.headers.get("Cache-Control", "")
        except urllib.error.HTTPError as error:
            return error.code, error.headers.get("Cache-Control", "")
        except (urllib.error.URLError, OSError, TimeoutError):
            time.sleep(0.25)
    message = f"nothing answered {path} on {port}"
    raise AssertionError(message)


@pytest.fixture(scope="module")
def site() -> Iterator[int]:
    """`deploy/serve.Dockerfile`, built and running — **the image, not a mounted directory.**"""
    why = _available()
    if why is not None:
        pytest.skip(why)
    suffix = _free_port()
    image = name = f"{DOCKER_PREFIX}-serve-{suffix}"
    port = _free_port()
    _docker("build", "-f", str(_ROOT / "deploy" / "serve.Dockerfile"), "-t", image, str(_ROOT))
    try:
        _docker(
            "run",
            "-d",
            "--name",
            name,
            "-p",
            f"{port}:8080",
            # ⚠️ A throwaway token: the config names one, so it needs one to be valid. Nothing here
            # authenticates, and it exists inside this process for a few seconds.
            "-e",
            "KEEP_SHARED_TOKEN=0000000000000000000000000000000000000000",
            "-e",
            "NGINX_ENVSUBST_FILTER=^KEEP_",
            image,
        )
        yield port
    finally:
        _docker("rm", "-f", name, check=False, timeout=120)
        _docker("image", "rm", "-f", image, check=False, timeout=300)


def _published_id() -> str:
    manifest = json.loads((_PUBLIC / "manifest.json").read_text(encoding="utf-8"))
    ids = manifest["puzzles"]
    assert ids, "the public manifest names no puzzles"
    return str(ids[0])


class TestTheSiteImage:
    def test_it_starts_and_stays_up(self, site: int) -> None:
        """⚠️ **Stays up**, because the first working build died on start and `docker run -d` still
        exited 0. A container that has already stopped answers nothing, and *the build succeeded* says
        nothing about that."""
        status, _header = _get(site, "/")

        assert status == 200, f"the landing page answered {status}"

    def test_it_serves_every_route_the_product_links_to(self, site: int) -> None:
        """⚠️ From the image, over its own port — not from a mounted config. That difference is the whole
        reason this file exists."""
        for path in ("/", "/today", "/tutorial", f"/p/{_published_id()}"):
            status, header = _get(site, path)

            assert status == 200, f"{path} answered {status}"
            assert header == "no-store", f"{path} was served `{header}`"

    def test_the_template_was_substituted(self, site: int) -> None:
        """⚠️⚠️ **The placeholder reaching nginx unresolved is the half a build check cannot see.**
        `conf.d/` is not the path the entrypoint substitutes, so a `COPY` to the wrong destination
        builds cleanly and serves a config with `${KEEP_SHARED_TOKEN}` in it. The API route existing at
        all is what says the substitution happened — nginx refuses to start otherwise."""
        status, _header = _get(site, "/api/events")

        # No `keep` here, so 502 (upstream absent) or 403 (GET refused) both prove the block parsed.
        assert status in {403, 502}, f"the API path answered {status}, so the proxy block is not there"

    def test_engine_modules_are_not_cached(self, site: int) -> None:
        """v41-P2-02. The pages import `../../engine/…`, which resolves to a **second root** the `/ui/`
        rule never covered: a deploy could serve a new `main.js` beside a cached `game.js`."""
        status, header = _get(site, "/engine/package.js")

        assert status == 200
        assert header == "no-store", f"an engine module was served `{header}`"

    def test_implementation_paths_are_still_unreachable(self, site: int) -> None:
        status, _header = _get(site, "/ui/phone/play.html")

        assert status == 404


class TestTheDataLayerImage:
    def test_its_healthcheck_uses_something_the_image_has(self) -> None:
        """v41-P2-01. The probe called `wget` and `python:3.13-slim` ships neither wget nor curl, so a
        healthy `keep` with a live database would have been reported unhealthy **by a command that could
        not run**.

        ⚠️ Asserted against the image rather than the Dockerfile text: what matters is whether the
        executable is there, and reading the source would only tell us what was intended.
        """
        why = _available()
        if why is not None:
            pytest.skip(why)
        suffix = _free_port()
        image = f"{DOCKER_PREFIX}-keep-health-{suffix}"
        _docker("build", "-f", str(_ROOT / "deploy" / "keep.Dockerfile"), "-t", image, str(_ROOT / "keep"))
        try:
            inspected = _docker("image", "inspect", image, "--format", "{{json .Config.Healthcheck.Test}}")
            probe = json.loads(inspected.stdout.strip())
            assert probe, "the image declares no healthcheck"

            executable = probe[1] if probe[0] in {"CMD", "CMD-SHELL"} else probe[0]
            found = _docker("run", "--rm", "--entrypoint", "sh", image, "-c", f"command -v {executable}", check=False)

            assert found.returncode == 0, f"the healthcheck runs `{executable}`, which the image does not have"
        finally:
            _docker("image", "rm", "-f", image, check=False, timeout=300)
