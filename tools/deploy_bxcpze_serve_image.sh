#!/bin/bash
#
# Load the boxscorepuzzle site image on the VPS, from the tar brought over in docker_images/.
#
# ⚠️ **One image, on purpose.** `serve` and `keep` carry independent version numbers: most changes
# touch one of them, and rebuilding the other to bump a shared number is work that changes nothing.
# `deploy_bxcpze_keep_image.sh` is the other one. When the `/api/` contract between them moves, both get built and
# both get loaded -- that is a decision to take, not a coupling to enforce here.
#
# Runs on the SERVER. `tools\create_docker_image.ps1 -Image serve` produces the tar, on the laptop,
# where the repository is -- and that split is the point rather than a convenience:
#
#   ⚠️⚠️ `forge/` MUST NEVER REACH THE VPS. It holds the generator and the human-solvability
#   guarantee, which is trade secret (CLAUDE.md sections 16 and 33). A Docker BUILD CONTEXT is a copy:
#   `docker build` ships the whole context to the daemon, so building the image here would put the
#   repository on this machine even though the image itself carries only `serve/`.

set -e

IMAGE="bxcpze-serve"

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
echo ""
echo "======================================"
echo "Next"
echo "======================================"
echo ""
echo "  Portainer -> Stacks -> bxcpze -> BXCPZE_SERVE_VERSION=$VERSION -> redeploy."
echo ""
echo "  Then check the site answers on the port nginx proxies to:"
echo "    curl -sI http://127.0.0.1:3005/"
echo ""
echo "  The stack also needs, and neither has a default:"
echo "    KEEP_SHARED_TOKEN   openssl rand -hex 32, the same value for both services"
echo "    KEEP_DATABASE_URL   postgresql://<user>:<pass>@postgres-postgres-1:5432/bxcpze_keep"
echo ""
