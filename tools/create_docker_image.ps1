# Build ONE boxscorepuzzle image and save it to docker_images/ for transfer to the VPS.
#
#   .\tools\create_docker_image.ps1 -Image serve                     asks for the version
#   .\tools\create_docker_image.ps1 -Image keep -Version 1.2026.1    receives it
#
# ⚠️ **One image per run, and the two carry independent version numbers.** `serve` is the client --
# pages, engine, fonts, nginx config -- and `keep` is the data layer. Most changes touch one of them,
# and rebuilding the other to bump a shared number is work that changes nothing. The contract between
# them is two `/api/` routes and a bearer token; it moves rarely, and when it does **both are built and
# both version numbers change**, which is a decision to take rather than a coupling to enforce here.
#
# ⚠️⚠️ THIS RUNS ON THE LAPTOP AND THAT IS THE POINT, not a convenience.
#
# `forge/` must never reach the VPS: it holds the generator and the human-solvability guarantee, which
# is trade secret (CLAUDE.md sections 16 and 33). **A Docker build context is a copy** -- `docker build`
# ships the whole context to the daemon -- so building `deploy/serve.Dockerfile` on the server would put
# the repository there even though the image itself carries only `serve/`. Building here and shipping
# the finished tar is what keeps that rule true. `tools/deploy_bxcpze_serve_image.sh` and
# `tools/deploy_bxcpze_keep_image.sh` are the other half, one per image for the same reason as above.

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("serve", "keep")]
    [string]$Image,

    [string]$Version
)

# The version can be passed as a parameter. With a bare Read-Host the script only works with a person
# in front of it: any non-interactive run fails with "PowerShell is in NonInteractive mode".
if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = Read-Host "Enter the version for the bxcpze-$Image image in format x.y.z (e.g., 1.2026.1)"
}

# Validate the format, not only that it is non-empty. The value ends up in an image tag AND in a
# filename, so a space or an odd character breaks one of the two later, once the image is already built.
if ([string]::IsNullOrWhiteSpace($Version)) {
    Write-Error "The version cannot be empty."
    exit 1
}
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    Write-Error "Invalid format: '$Version'. Expected x.y.z (for example 1.2026.1)."
    exit 1
}

# Ask Docker instead of asking the user. A "is Docker running? (yes/no)" prompt answered wrongly moves
# the failure into the middle of the build.
Write-Host ""
Write-Host "Checking that Docker responds..."
docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker is not responding. Start Docker Desktop and try again."
    exit 1
}

$rootDir = Split-Path -Parent $PSScriptRoot
$dockerImagesDir = Join-Path $rootDir "docker_images"

# name, dockerfile, build context -- each Dockerfile documents its own pair in its header.
$builds = @{
    serve = @{ Dockerfile = "deploy\serve.Dockerfile"; Context = $rootDir }
    keep  = @{ Dockerfile = "deploy\keep.Dockerfile";  Context = (Join-Path $rootDir "keep") }
}

$build = $builds[$Image]
$imageName = "bxcpze-$Image`:$Version"
$dockerfile = Join-Path $rootDir $build.Dockerfile
$outputPath = Join-Path $dockerImagesDir "bxcpze-$Image-$Version.tar"

if (-not (Test-Path $dockerfile)) {
    Write-Error "Dockerfile not found at $dockerfile"
    exit 1
}

if (-not (Test-Path $dockerImagesDir)) {
    Write-Host "Creating docker_images directory at $dockerImagesDir"
    New-Item -ItemType Directory -Path $dockerImagesDir -Force | Out-Null
}

# ⚠️⚠️ The serve build context is the repository root, so without the acceptance list it carries
# `forge/`. Refuse rather than build it. The local daemon would not care, and that is exactly why this
# check exists: a missing .dockerignore is invisible here and is the one condition under which the rule
# at the top stops being enforced by anything at all.
if ($Image -eq "serve") {
    $dockerIgnore = Join-Path $rootDir ".dockerignore"
    if (-not (Test-Path $dockerIgnore)) {
        Write-Error ".dockerignore is missing. The serve build context is the repository root, so without it the context carries forge/. Restore it before building."
        exit 1
    }
}

# Do not silently overwrite a version already published: the tars in docker_images/ are what gets
# transferred to the VPS, so overwriting one changes what is deployed without anybody noticing.
if (Test-Path $outputPath) {
    Write-Host ""
    Write-Warning "Already exists: $outputPath"
    $overwrite = Read-Host "Overwrite that version? (yes/no)"
    if ($overwrite -ne "yes" -and $overwrite -ne "y") {
        Write-Host "Cancelled. Use a different version number."
        exit 1
    }
}

try {
    Push-Location $rootDir

    Write-Host ""
    Write-Host "Building Docker image: $imageName"
    Write-Host "Output will be saved to: $outputPath"
    Write-Host ""

    docker build --no-cache -t $imageName -f $dockerfile $build.Context
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker build failed with exit code $LASTEXITCODE"
        exit 1
    }

    Write-Host ""
    Write-Host "Image built successfully: $imageName"
    Write-Host "Saving image to $outputPath..."

    docker save -o $outputPath $imageName
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker save failed with exit code $LASTEXITCODE"
        exit 1
    }

    # ⚠️ Ask the filesystem, do not trust the exit code. `docker save` finishing says the command ran;
    # a truncated tar loads as a confusing failure an hour later, on the far side of an upload.
    $size = (Get-Item $outputPath).Length
    if ($size -lt 1MB) {
        Write-Error "$outputPath is only $size bytes. Do not upload it."
        exit 1
    }

    Write-Host "Image saved successfully!"
    Write-Host "Output file: $outputPath"
    Write-Host "Image size: $([math]::Round($size / 1MB, 2)) MB"
}
catch {
    Write-Error "An error occurred: $_"
    exit 1
}
finally {
    Pop-Location
}

# Both load scripts travel with the tars, so one transfer of docker_images/ brings everything the
# server needs. Their source of truth stays in tools/; these are copies for transport.
Copy-Item (Join-Path $PSScriptRoot "deploy_bxcpze_serve_image.sh") -Destination $dockerImagesDir -Force
Copy-Item (Join-Path $PSScriptRoot "deploy_bxcpze_keep_image.sh")  -Destination $dockerImagesDir -Force

Write-Host ""
Write-Host "Docker image creation completed successfully!"
Write-Host ""
Write-Host "  1. Transfer docker_images/ to the VPS (only the tars you rebuilt need to travel)."
Write-Host "  2. On the server:  chmod +x deploy_bxcpze_$($Image)_image.sh && ./deploy_bxcpze_$($Image)_image.sh"
Write-Host "  3. Portainer -> Stacks -> bxcpze -> BXCPZE_$($Image.ToUpper())_VERSION=$Version -> redeploy."
Write-Host ""
