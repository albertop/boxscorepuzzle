"""Everything the server needs travels in `docker_images/`, because that is what the script promises.

⚠️⚠️ **v42-P2-02.** `create_docker_image.ps1` says one transfer of `docker_images/` brings everything the
server needs, and copied the three load scripts into it -- **but not `deploy/ofelia/rotation.ini`**. The
publish load script then tells the operator to install the scheduler from `deploy/ofelia/rotation.ini`,
a path that was never in the transfer. On a fresh VPS ofelia comes up with no bind-mounted config, the
daily rotation never starts, and a manual first rotation makes launch day look correct while the puzzle
stops changing the next morning.

**Two files, each internally consistent, neither stating the other's half** -- the shape `CLAUDE.md`
records for the two Dockerfiles and the uid. So a guard asserts they agree.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_BUILD = _ROOT / "tools" / "create_docker_image.ps1"
_LOADER = _ROOT / "tools" / "deploy_bxcpze_publish_image.sh"
_COMPOSE = _ROOT / "deploy" / "compose.yaml"


def _copied_into_the_bundle() -> list[str]:
    """The basenames `create_docker_image.ps1` copies into `docker_images/`."""
    found = re.findall(r'Copy-Item .*?"([^"]+)"\)? +-Destination \$dockerImagesDir', _BUILD.read_text(encoding="utf-8"))
    assert found, "no Copy-Item into the bundle was found; this test would pass over nothing"
    return [name.split("\\")[-1].split("/")[-1] for name in found]


def test_every_file_the_loader_tells_the_operator_to_install_is_in_the_bundle() -> None:
    """⚠️ Read out of the loader's own instruction, not from a list kept here.

    A hand-written list beside the script is the defect one level along: it would agree with itself
    while the instruction changed.
    """
    told = re.findall(r"sudo install -D -m \d+ (\S+)", _LOADER.read_text(encoding="utf-8"))
    assert told, "the loader gives no install instruction; this test would pass over nothing"

    bundle = _copied_into_the_bundle()
    for source in told:
        assert "$SCRIPT_DIR" in source, f"the loader points at {source}, which is not in the transferred bundle"
        assert source.split("/")[-1] in bundle, f"{source} is named but never copied into docker_images/"


def test_the_scheduler_config_travels() -> None:
    """The instance, named, so a rename that keeps the shape still has to face this."""
    assert "rotation.ini" in _copied_into_the_bundle()


def test_the_publisher_is_not_advertised_as_a_portainer_variable() -> None:
    """⚠️⚠️ The other half of v42-P2-02, and it is a *true-looking* instruction rather than a missing file.

    The completion message told the operator to set `BXCPZE_PUBLISH_VERSION` in Portainer. `compose.yaml`
    has no such variable -- ofelia reads no environment and the publisher's version lives in
    `rotation.ini` -- so following it is a successful-looking action that changes nothing about the image
    the scheduler runs.
    """
    compose = _COMPOSE.read_text(encoding="utf-8")
    build = _BUILD.read_text(encoding="utf-8")

    declared = set(re.findall(r"BXCPZE_(\w+)_VERSION", compose))
    assert declared, "compose declares no version variables; this test would pass over nothing"
    assert "PUBLISH" not in declared, "compose grew a publish version; this test is now the stale half"

    advertised = re.search(r"BXCPZE_\$\(\$Image\.ToUpper\(\)\)_VERSION", build)
    assert advertised, "the completion message no longer names a version variable; check this guard"
    # The generic line must be reachable only for the images that actually have one.
    assert 'if ($Image -eq "publish")' in build, (
        "the completion message is unconditional again; a publish build is told to set a variable compose does not have"
    )
