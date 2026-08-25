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


def test_no_join_path_is_given_more_than_two_arguments() -> None:
    """⚠️⚠️ **The guard above read the string and never asked whether the script runs.**

    `Join-Path $rootDir "deploy" "ofelia" "rotation.ini"` satisfies every assertion in this file --
    `rotation.ini` is named, it is copied to `$dockerImagesDir` -- and **Windows PowerShell 5.1 takes
    exactly two arguments**, so the script died at that line with a positional-parameter error. The
    operator hit it on the first build. *Serves the right bytes* and *works here* are different
    properties, and only one of them is what a build script is for.

    ⚠️ Checked by counting arguments rather than by running PowerShell: the suite runs on Ubuntu in CI,
    and a test that skips where it cannot run is a check that never fires on the platform it matters on.
    """
    for line in _BUILD.read_text(encoding="utf-8").splitlines():
        call = re.search(r"Join-Path\s+(.+?)\)", line)
        if call is None:
            continue
        # `$var` or a quoted string; anything past the second is what PowerShell 5.1 refuses.
        arguments = re.findall(r'"[^"]*"|\$\w+', call[1])
        assert len(arguments) <= 2, f"Join-Path takes two arguments and got {len(arguments)}: {line.strip()}"


def test_every_image_has_its_version_in_one_place() -> None:
    """⚠️⚠️ **v42-P2-02's other half, and the repair went further than the finding.**

    The finding was that the completion message told the operator to set `BXCPZE_PUBLISH_VERSION` in
    Portainer while `compose.yaml` had no such variable -- ofelia reads no environment, so the
    publisher's version was spelled by hand in `ofelia/config.ini`. The first fix branched the message.

    **The real repair came from somewhere else.** ofelia 0.3.22 always pulls when a job names an `image`,
    and every image here is local, so the rotation could never start at all -- it had never run once.
    Giving ofelia a CONTAINER declared in `compose.yaml` fixed that, and took the version with it.
    **All three images now carry their version the same way**, which is what the branch existed to work
    around.

    ⚠️ So this asserts the property rather than the workaround.
    """
    compose = _COMPOSE.read_text(encoding="utf-8")
    build = _BUILD.read_text(encoding="utf-8")

    offered = re.search(r"ValidateSet\(([^)]*)\)", build)
    assert offered, "the build script offers no images; this test would pass over nothing"
    buildable = {name.strip().strip('"').upper() for name in offered[1].split(",") if name.strip()}
    assert buildable, "no image names parsed out of the build script"

    declared = set(re.findall(r"BXCPZE_(\w+)_VERSION", compose))
    assert buildable <= declared, f"no version variable in compose for {sorted(buildable - declared)}"


def test_the_rotation_starts_a_container_and_never_names_an_image() -> None:
    """⚠️⚠️ **ofelia pulls whenever a job names an image, and every image here is local.**

    `forge/` never leaves the laptop and nothing is in a registry, so the pull fails with `repository
    does not exist` -- which reads like a missing image and is the opposite: it is there, and ofelia went
    looking elsewhere. `pull = false` is ignored by 0.3.22.

    **The rotation had therefore never run.** F3 was marked met on a manual `docker run`, which proves
    the publisher works and says nothing about the scheduler, and the first real firing was eight days
    later at 08:15 with nobody watching.
    """
    ini = (_ROOT / "deploy" / "ofelia" / "rotation.ini").read_text(encoding="utf-8")
    compose = _COMPOSE.read_text(encoding="utf-8")

    block = ini.split('[job-run "rotate"]', 1)
    assert len(block) == 2, "there is no rotate job; this test would pass over nothing"
    body = block[1].split("[", 1)[0]

    assert not re.search(r"^\s*image\s*=", body, re.MULTILINE), (
        "the rotate job names an image again; ofelia will try to pull it and every image here is local"
    )
    named = re.search(r"^\s*container\s*=\s*(\S+)", body, re.MULTILINE)
    assert named, "the rotate job starts nothing"
    assert f"container_name: {named[1]}" in compose, (
        f"{named[1]} is not declared in compose.yaml; the scheduler would start a container nobody creates"
    )
    # ⚠️ `delete = true` would work exactly once: the container is gone and tomorrow says `no such
    # container`, a day after the change that caused it.
    assert re.search(r"^\s*delete\s*=\s*false", body, re.MULTILINE), (
        "the rotate job deletes its container; there would be nothing to start tomorrow"
    )
