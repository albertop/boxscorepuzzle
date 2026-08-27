#!/bin/bash
#
# Load the boxscorepuzzle site image on the VPS, from the tar brought over in docker_images/.
#
# ⚠️ **One image, on purpose.** `publish` and `keep` carry independent version numbers: most changes
# touch one of them, and rebuilding the other to bump a shared number is work that changes nothing.
# `deploy_bxcpze_serve_image.sh` is the other one. When the `/api/` contract between them moves, both get built and
# both get loaded -- that is a decision to take, not a coupling to enforce here.
#
# Runs on the SERVER. `tools\create_docker_image.ps1 -Image publish` produces the tar, on the laptop,
# where the repository is -- and that split is the point rather than a convenience:
#
#   ⚠️⚠️ `forge/` MUST NEVER REACH THE VPS. It holds the generator and the human-solvability
#   guarantee, which is trade secret (CLAUDE.md sections 16 and 33). A Docker BUILD CONTEXT is a copy:
#   `docker build` ships the whole context to the daemon, so building the image here would put the
#   repository on this machine even though the image itself carries only `publish/`.

set -e

IMAGE="bxcpze-publish"

if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

read -p "Enter the version of $IMAGE to load in format x.y.z (e.g., 1.2026.1): " VERSION

if [ -z "$VERSION" ]; then
    echo "Error: The version cannot be empty."
    exit 1
fi
# Validate the format, not only that it is non-empty -- the value is half of a filename below, and a
# stray character turns "not found" into a puzzle about which file was actually looked for.
if ! printf '%s' "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "Error: Invalid format '$VERSION'. Expected x.y.z (for example 1.2026.1)."
    exit 1
fi

# ⚠️ ONE variable for the directory. This script is shipped INSIDE docker_images/, so the tar is
# beside it -- and a script that says "expected in docker_images/" while looking somewhere else sends
# the reader to the wrong folder.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAR_FILE="$SCRIPT_DIR/images/$IMAGE-$VERSION.tar"

if [ ! -f "$TAR_FILE" ]; then
    echo "Error: Tar file not found at $TAR_FILE"
    echo "Expected file: $IMAGE-$VERSION.tar, beside this script."
    exit 1
fi

echo ""
echo "======================================"
echo "boxscorepuzzle -- loading $IMAGE:$VERSION"
echo "======================================"
echo "File size: $(du -h "$TAR_FILE" | cut -f1)"
echo ""

docker load -i "$TAR_FILE"

# ⚠️⚠️ ASK DOCKER, do not trust the exit code. `docker load` finishing says the command ran; it does
# not say the tag being deployed is now present -- a tar built under a different tag loads perfectly
# and leaves the name Portainer is about to ask for missing. This project has recorded cases of a tool
# reporting success about a subject it was never given.
echo ""
if ! docker images "$IMAGE:$VERSION" --format "{{.Repository}}:{{.Tag}}" | grep -q "^$IMAGE:$VERSION$"; then
    echo "Error: $IMAGE:$VERSION is not present after loading. Do not redeploy."
    exit 1
fi

echo "  verified  $IMAGE:$VERSION   $(docker images "$IMAGE:$VERSION" --format '{{.Size}}')"
# ⚠️⚠️ **THIS USED TO INSPECT THE SCHEDULER'S CONFIG, AND THE CHECK OUTLIVED WHAT IT CHECKED.**
#
# It required an `image = bxcpze-publish:<tag>` line in `config.ini` and exited 1 without one -- correct
# while ofelia created the container from an image named there. **The container design removed that line
# on purpose** (`rotation.ini`, and `compose.yaml`'s `publish` service), so this script refused a
# CORRECT deployment, and its remediation told the operator to add back the exact setting that makes
# ofelia pull a local-only image from a registry and fail.
#
# ⚠️⚠️ **A check that outlives its subject does not go quiet; it starts failing the right answer.**
# That is what separates it from an ordinary stale comment: it is load-bearing, it exits non-zero, and
# the fix it prints is the defect. v43-P2-01.
#
# **`publish` finishes like the other two loaders now**: the version is `BXCPZE_PUBLISH_VERSION` in
# Portainer, one place, with nothing left to fall behind and nothing here to compare.
CONFIG="/srv/boxscorepuzzle/ofelia/config.ini"

echo ""
echo "======================================"
echo "The scheduler's config"
echo "======================================"
echo ""

# ⚠️⚠️ **Existence only, and that is the whole of what is left to check here.** The INI carries the
# schedule and the container name; it carries no version, so there is nothing that can fall behind it and
# nothing to compare against the tag just loaded. **What it can still be is ABSENT** -- on a fresh VPS
# ofelia comes up with no bind-mounted config, the daily rotation never starts, and a manual first
# rotation makes launch day look correct while the puzzle stops changing the next morning. v42-P2-02.
if [ ! -f "$CONFIG" ]; then
    echo "  MISSING: $CONFIG"
    echo ""
    echo "  Nothing is scheduled until it exists. Install it from this bundle:"
    echo ""
    echo "    sudo install -D -m 644 $SCRIPT_DIR/rotation.ini $CONFIG"
    echo "    docker restart bxcpze-scheduler"
else
    # ⚠️ Named out loud rather than passed over in silence, so a present config is a reported fact
    # rather than the absence of a complaint.
    echo "  present   $CONFIG"
    echo ""
    # ⚠⚠ No backticks inside a double-quoted echo: bash runs what is between them. The first draft of
    # this very line wrote 'an `image =` line' and would have executed `image =` on every run -- a fix
    # introducing the class of defect it was written to remove, caught by reading the line rather than by
    # `bash -n`, which accepts command substitution happily.
    echo "  ⚠ It must name a container, never an image. A config still carrying an image line predates"
    echo "  the container design, and ofelia will try to pull from a registry -- reinstall it from here:"
    echo ""
    echo "    grep -n 'image\|container' $CONFIG"
fi

echo ""
echo "======================================"
echo "Tell the stack to use it"
echo "======================================"
echo ""
echo "  Portainer -> Stacks -> boxscorepuzzle -> BXCPZE_PUBLISH_VERSION=$VERSION -> redeploy."
echo ""
echo "  Redeploying recreates the stopped bxcpze-publish container on the new tag and runs one"
echo "  rotation immediately. The scheduler starts that same container at 08:15 UTC every day."
echo ""
echo "  ⚠ Confirm it rather than assuming the variable took:"
echo ""
echo "    docker inspect -f '{{.Config.Image}}' bxcpze-publish"
echo ""
echo "  It must print bxcpze-publish:$VERSION. Anything else means the stack did not redeploy."

echo ""
echo "======================================"
echo "Run it once by hand"
echo "======================================"
echo ""
echo "  Rather than waiting for 08:15 UTC:"
echo ""
echo "    docker start -a bxcpze-publish"
echo ""
echo "  ⚠⚠ THE CONTAINER, never a hand-built docker run. That is a different job wearing the same"
echo "  image: it misses the backend network, so the health verdict cannot fetch the deployed client"
echo "  and reports on one it never read -- and the rotation skips its refusal to publish a package"
echo "  the client cannot parse. With --rm it also leaves the image unreferenced, which is how a"
echo "  prune on this shared host took it once already."
echo ""
echo "  It prints what it published, what is public now, and WHAT IT RETIRED, then reads the health"
echo "  verdict itself. A non-zero exit means the public path is not what it should be."
echo ""
echo "  ⚠ The retired line is the one to read. Two packages public and nothing else is the whole of"
echo "  the access model: everything past yesterday is sold, not served."
echo ""
