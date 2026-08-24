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
import re
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

from tests.conftest import DOCKER_PREFIX, nginx_environment_flags

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
            *nginx_environment_flags(),
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


class TestTheRotationCanWriteWhatTheSiteServes:
    """⚠️⚠️ **The uid that writes the published path is spelled in two Dockerfiles, and they must agree.**

    `serve` is nginx over the published tree and only reads it. `publish` is the daily rotation and is
    its only writer. **Docker takes a new named volume's ownership from the image path it populates it
    from**, and that path is `serve`'s -- so if the two name different uids, the rotation fails with
    `PermissionError` the first time it runs, on a deployment that looks completely healthy until then.

    ⚠️ **Found by running the rotation, not by reading either file.** `publish.Dockerfile` said in a
    comment that the public path was *"mounted writable and owned by this uid"* and nothing made it so.
    A comment asserting a property nothing establishes is this project's most-recorded defect, and it
    survived being written by the person who had just written the same warning three files away.
    """

    def _dockerfile(self, name: str) -> str:
        return (_ROOT / "deploy" / f"{name}.Dockerfile").read_text(encoding="utf-8")

    def test_publish_runs_as_a_uid_it_states(self) -> None:
        """⚠️ Assert the subject is there before judging it: a regex over a file that stopped naming a
        uid would otherwise find nothing and pass."""
        assert re.search(r"--uid\s+(\d+)\s+publish", self._dockerfile("publish")), (
            "deploy/publish.Dockerfile no longer creates a user with an explicit uid"
        )

    def test_serve_hands_the_published_path_to_the_uid_that_writes_it(self) -> None:
        writer = re.search(r"--uid\s+(\d+)\s+publish", self._dockerfile("publish"))
        assert writer is not None
        owner = re.search(r"chown -R (\d+):(\d+) /srv/serve/data/puzzles", self._dockerfile("serve"))

        assert owner is not None, (
            "deploy/serve.Dockerfile does not chown the published path. A new named volume inherits its "
            "ownership from this image, so the rotation would be unable to write to it."
        )
        assert owner.group(1) == writer.group(1), (
            f"serve hands the published path to uid {owner.group(1)} and publish runs as "
            f"{writer.group(1)}. The rotation cannot write, and nothing says so until it runs."
        )
