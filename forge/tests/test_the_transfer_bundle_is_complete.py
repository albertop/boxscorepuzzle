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
_INI = _ROOT / "deploy" / "ofelia" / "rotation.ini"
_RUNBOOK = _ROOT / "docs" / "runbook-inventory.md"


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


def _demanded_by_compose() -> set[str]:
    """The variables `compose.yaml` refuses to start without -- the `:?` ones, never the defaulted ones.

    ⚠️ **Read out of compose rather than listed here.** A list in this file would be the seventh instance
    of a hand-maintained list beside its source of truth, in the test written to close the sixth.
    """
    demanded = set(re.findall(r"\$\{([A-Z_]+):\?", _COMPOSE.read_text(encoding="utf-8")))
    assert demanded, "no required variable found in compose.yaml; this test would pass over nothing"
    return demanded


def test_the_runbook_lists_every_variable_the_stack_cannot_start_without() -> None:
    """⚠️⚠️ **v43-P2-01, and this is the half of it that stops a deployment rather than misleading one.**

    The runbook's stack section listed four variables and `compose.yaml` demands five. Every one is
    spelled `:?`, so the missing `BXCPZE_PUBLISH_VERSION` is not a degraded stack -- **Portainer refuses
    the deploy**, naming a variable the runbook says does not exist. The list was written when `publish`
    was not a service and was never revisited when it became one.

    ⚠️ Both directions. A variable dropped from compose but left in the runbook sends the operator to set
    something nothing reads, which is the same defect facing outward.
    """
    # ⚠️⚠️ **The variable BLOCK, never the whole document.** The first version searched the entire
    # runbook and passed with the list shortened back to four -- because the paragraph EXPLAINING the
    # omission names the missing variable. **The instrument was supplying the property under judgement**,
    # which is this project's padded-text-dump shape, here inside the guard written to close it.
    section = _RUNBOOK.read_text(encoding="utf-8")
    # ⚠️ Split rather than matched: the marker is a heading, and a regex
    # spanning blank lines reads worse here than two splits.
    assert "Paste `deploy/compose.yaml`." in section, "the stack section was not found; this would pass over nothing"
    after = section.split("Paste `deploy/compose.yaml`.", 1)[1].split("###", 1)[0]
    # ⚠⚠ **The INDENTED lines of that section, not the section.** Cutting at the next heading still swallowed
    # the paragraph that EXPLAINS the omission -- which names the missing variable, so the list could be shortened
    # back to four and the guard stayed green. Second time in this one test that the instrument supplied the
    # property under judgement; the block the operator copies is the indented one.
    block = "".join(line for line in after.splitlines(keepends=True) if line.startswith("    "))
    listed = set(re.findall("(BXCPZE_[A-Z_]+|KEEP_[A-Z_]+)", block))
    assert listed, "the stack section names no variable at all"
    demanded = _demanded_by_compose()

    assert demanded <= listed, f"the runbook never names {sorted(demanded - listed)}; the stack will not deploy"
    stale = {name for name in listed if name.startswith("BXCPZE_") and name.endswith("_VERSION")} - demanded
    assert not stale, f"the runbook names {sorted(stale)}, which compose does not use"


def test_no_operator_facing_path_asks_for_an_ofelia_image_line() -> None:
    """⚠️⚠️ **A check that outlives its subject does not go quiet; it starts failing the right answer.**

    `rotation.ini` stopped naming an image and started naming a container. The publish loader kept
    inspecting the removed line and **exited 1 on a correct deployment**; its remediation printed the
    exact `image =` setting that makes ofelia pull a local-only image from a registry and fail. The build
    script and the runbook repeated it. Three operator-facing paths implementing a design the two
    authoritative files had already replaced.

    ⚠️ **The subject is instructions, not comments.** Both files explain the old design at length in prose
    -- deliberately, because it is the history of why the container design exists -- so this reads only
    the lines that tell the operator to do something: a shell `echo`, a PowerShell `Write-Host`, and an
    indented command block in the runbook.

    ⚠️ Seen red by restoring `echo "    image = bxcpze-publish:$VERSION"` to the loader.
    """
    assert "container = " in _INI.read_text(encoding="utf-8"), "the INI no longer names a container; this test is stale"

    said: list[tuple[str, str]] = []
    for where, pattern in (
        (_LOADER, r'^\s*echo "(.*)"'),
        (_BUILD, r'^\s*Write-Host "(.*)"'),
        (_RUNBOOK, r"^ {4}(\S.*)$"),
    ):
        said += [(where.name, line) for line in re.findall(pattern, where.read_text(encoding="utf-8"), re.MULTILINE)]
    assert said, "no operator-facing instruction was found anywhere; this test would pass over nothing"

    offending = [(name, line) for name, line in said if re.search(r"image\s*=\s*bxcpze-publish", line)]
    assert not offending, f"an operator-facing path still asks for an ofelia image line: {offending}"


def test_the_publisher_is_deployed_by_the_same_step_as_the_other_two() -> None:
    """⚠️ The positive half. The test above forbids the old instruction; this requires the new one.

    Without it, deleting the offending lines and printing nothing at all passes -- and the operator is
    then told how to load the image and never told how to make the stack use it. **A refusal is not an
    instruction**, which is the shape where removing a wrong answer is mistaken for giving a right one.
    """
    # ⚠️ **What it PRINTS, not what it contains.** Both files explain in comments why the version moved
    # to Portainer, and those comments name the variable -- so a substring search over the file passes on
    # a script whose every instruction was deleted. Same defect as the runbook case above.
    for where, pattern in ((_LOADER, r'^\s*echo "(.*)"'), (_BUILD, r'^\s*Write-Host "(.*)"')):
        printed = re.findall(pattern, where.read_text(encoding="utf-8"), re.MULTILINE)
        assert printed, f"{where.name} prints nothing; this test would pass over nothing"
        assert any("BXCPZE_PUBLISH_VERSION" in line for line in printed), (
            f"{where.name} never TELLS the operator how to select the version"
        )


def test_the_hand_run_starts_the_declared_container() -> None:
    """⚠️⚠️ **A hand-built `docker run` is a different job wearing the same image**, and the loader printed
    one for months.

    It missed `--network`, so `--client` could not resolve `bxcpze-serve` and the health verdict reported
    on a client it never read -- the *validator given the wrong subject* shape. It also carried `--rm`,
    which leaves the image unreferenced, **which is how a prune on this shared host deleted it once**. The
    container `compose.yaml` declares has the volumes, the command and the network on it.
    """
    # ⚠️⚠️ **The loader AND the runbook, and reading only the loader was v44-P2-01.** The first version
    # of this test inspected `_LOADER` alone, so it was green while §5c of the runbook printed the exact
    # `docker run` it forbids -- **the operator follows the runbook, not the script's echoes.** A fix
    # applied to the instance in hand rather than to the category, in the commit that closed v43-P2-01 for
    # being the same mistake.
    printed = re.findall(r'^\s*echo "(.*)"', _LOADER.read_text(encoding="utf-8"), re.MULTILINE)
    assert printed, "the loader prints nothing; this test would pass over nothing"
    # ⚠️ **Command lines only.** The loader EXPLAINS why `docker run` is wrong, in prose, on a line
    # containing those two words -- so a bare substring search over everything it prints fails on the
    # warning written to prevent the thing. The commands are the indented lines.
    commands = [line.strip() for line in printed if line.startswith("    ")]

    # ⚠️ **The publisher's own commands, not every `docker run` in the runbook.** §5 legitimately runs
    # `alpine` against the puzzles volume three times to check ownership; a guard that fired on those would
    # be a threshold rejecting real data, which gets loosened until it says nothing.
    runbook = [line.strip() for line in _RUNBOOK.read_text(encoding="utf-8").splitlines() if line.startswith("    ")]
    runbook += re.findall(r"^(docker .*)$", _RUNBOOK.read_text(encoding="utf-8"), re.MULTILINE)
    assert runbook, "the runbook shows no indented command; this test would pass over nothing"
    commands += [line for line in runbook if "bxcpze-publish" in line or "bxcpze_publish" in line]
    assert not [line for line in commands if line.startswith("docker run")], (
        f"an operator-facing path still prints a hand-built docker run: {commands}"
    )
    started = [line for line in commands if line.startswith("docker start")]
    assert started, "nothing says how to run a rotation by hand"
    assert any("bxcpze-publish" in line for line in started), "the hand run does not name the declared container"

    # ⚠️ `bxcpze_publish` with an underscore was in §5b for two days and names nothing that exists. Docker
    # answers *no such container*, which reads like the stack being down rather than like a typo.
    assert not [line for line in commands if "bxcpze_publish" in line], (
        "an operator-facing command names bxcpze_publish; the container is bxcpze-publish"
    )
    # ⚠️ `docker exec` into a container whose healthy state is STOPPED cannot work, ever.
    assert not [line for line in commands if line.startswith("docker exec") and "bxcpze-publish" in line], (
        "an operator-facing command execs into the publisher, which is stopped when it is healthy"
    )
