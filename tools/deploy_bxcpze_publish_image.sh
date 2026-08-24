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
TAR_FILE="$SCRIPT_DIR/$IMAGE-$VERSION.tar"

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
# ⚠️⚠️ **THE SCHEDULER'S CONFIG IS CHECKED, AND THIS REFUSES RATHER THAN CORRECTS.**
#
# Ofelia does not interpolate environment variables into an INI, so `publish`'s version is written out
# in `config.ini` -- unlike `serve` and `keep`, whose versions are Portainer variables. **A deploy that
# loads a new image and does not edit that line keeps running the old rotation: successfully, printing
# normally, exiting zero, with last month's code.** It is the one thing in this deployment that can fall
# behind with no signal at all.
#
# ⚠️⚠️ **It does not rewrite the file, and that is the decision rather than an omission.** A load that
# silently changed what production runs is the opposite of a deploy: the image arriving on the host and
# the host being told to use it are two acts, and collapsing them means nobody ever chose the second.
#
# ⚠️ **WHAT THIS COVERS AND WHAT IT DOES NOT.** It covers this script. Editing the INI by hand, loading
# an image another way, or copying a tar and running `docker load` directly all bypass it completely.
# **It makes forgetting loud on the path used almost every time; it does not close the class.** The
# design that would close it is recorded in `deploy/ofelia/rotation.ini` under "the option not taken".
CONFIG="/srv/boxscorepuzzle/ofelia/config.ini"

echo ""
echo "======================================"
echo "The scheduler's config"
echo "======================================"
echo ""

if [ ! -f "$CONFIG" ]; then
    # ⚠️ Not an error: the config is installed once, and the first load of this image legitimately
    # happens before it exists. Said out loud so its absence is not read as a passing check.
    echo "  $CONFIG does not exist yet."
    echo "  Install it before the scheduler can run anything:"
    echo ""
    echo "    sudo install -D -m 644 deploy/ofelia/rotation.ini $CONFIG"
    echo ""
    echo "  Then set its image line to bxcpze-publish:$VERSION and start the stack."
else
    # ⚠️ Anchored and asserted. A grep that matched nothing would leave CONFIGURED empty, and an empty
    # string compared against a version is a mismatch reported for the wrong reason -- so the absence of
    # the line is its own message rather than a confusing inequality.
    CONFIGURED=$(grep -E '^[[:space:]]*image[[:space:]]*=[[:space:]]*bxcpze-publish:' "$CONFIG" | head -1 | sed 's/.*bxcpze-publish://; s/[[:space:]]*$//')

    if [ -z "$CONFIGURED" ]; then
        echo "  ERROR: $CONFIG names no bxcpze-publish image."
        echo "  The scheduler cannot run the rotation. Add:"
        echo ""
        echo "    image = bxcpze-publish:$VERSION"
        exit 1
    fi

    if [ "$CONFIGURED" != "$VERSION" ]; then
        echo "  ERROR: the scheduler would run a different version than the one just loaded."
        echo ""
        echo "    loaded here : bxcpze-publish:$VERSION"
        echo "    $CONFIG : bxcpze-publish:$CONFIGURED"
        echo ""
        echo "  Nothing has been changed. Loading an image and telling the host to use it are two"
        echo "  separate acts, and this script does not take the second one for you."
        echo ""
        echo "    sudo sed -i 's|^\([[:space:]]*image[[:space:]]*=[[:space:]]*\)bxcpze-publish:.*|\1bxcpze-publish:$VERSION|' $CONFIG"
        echo "    grep -n 'bxcpze-publish' $CONFIG"
        echo "    docker restart bxcpze-scheduler"
        echo ""
        echo "  READ the grep. A sed that matches nothing exits zero and leaves the old tag."
        exit 1
    fi

    echo "  $CONFIG names bxcpze-publish:$CONFIGURED -- the version just loaded."
    echo "  Restart the scheduler so it picks up a changed config:"
    echo ""
    echo "    docker restart bxcpze-scheduler"
fi

echo ""
echo "======================================"
echo "Run it once by hand"
echo "======================================"
echo ""
echo "  Rather than waiting for 08:15 UTC:"
echo ""
echo "    docker run --rm \\"
echo "      -v /srv/boxscorepuzzle/inventory:/srv/inventory:ro \\"
echo "      -v boxscorepuzzle_puzzles:/srv/public \\"
echo "      bxcpze-publish:$VERSION"
echo ""
echo "  It prints what it published, what is public now, and WHAT IT RETIRED, then reads the health"
echo "  verdict itself. A non-zero exit means the public path is not what it should be."
echo ""
echo "  ⚠ The retired line is the one to read. Two packages public and nothing else is the whole of"
echo "  the access model: everything past yesterday is sold, not served."
echo ""
