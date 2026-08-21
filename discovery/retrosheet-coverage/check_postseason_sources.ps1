# Re-establish the fact the postseason floor rests on.
#
# The regular season proves per game that it came from a scored event file: `dbo.retroGameProvenance`
# carries a row saying so, and the pool's CROSS APPLY drops a game without one. THE POSTSEASON HAS NO
# SUCH TABLE AND NEEDS NONE, because every postseason event file carries a single extension — `.EVE`,
# with no league letter and no deduced twin — so there is nothing to exclude per game.
#
# That is a fact about a download, not a property of the data model. `POSTSEASON_SEASON_FLOOR` is the
# protection against Retrosheet publishing something later that would need excluding: a Negro Leagues
# postseason, a reconstruction of a game whose scoresheet was lost. The floor is set at 1969 because
# the last deduced game anywhere in the database is 1968 and the first LCS is 1969.
#
# ⚠️ A floor is a weaker guarantee than a provenance row, and this script is the difference. It says
# what is true of the download in front of it; without running it after a new one, the floor is an
# assumption that ages silently. Run it whenever the Retrosheet dataset is reloaded
# (docs/reloading-retrosheet.md).
#
# ⚠️ ASSERTS RATHER THAN REPORTS. A launch-time fact that is printed and believed is the shape this
# project keeps meeting; a non-zero exit is the only thing a caller cannot ignore by accident.

param(
    [string]$ZipDirectory = "C:\Users\aperd\Documents\DGLv2\retrosheet\downloads\zip\events-post",
    [int]$SeasonFloor = 1969,
    [string]$Expected = "EVE"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression.FileSystem

if (-not (Test-Path $ZipDirectory)) {
    throw "no such directory: $ZipDirectory - pass -ZipDirectory to point at the postseason download"
}

$byExtension = @{}
$offenders = New-Object System.Collections.Generic.List[string]
$fileCount = 0

foreach ($zip in Get-ChildItem $ZipDirectory -Filter *.zip) {
    $archive = [IO.Compression.ZipFile]::OpenRead($zip.FullName)
    try {
        foreach ($entry in $archive.Entries) {
            $extension = [IO.Path]::GetExtension($entry.Name)
            # ⚠️ `.E??` and not a list of known kinds. A guard that enumerates what it expects cannot
            # see a kind nobody has met, which is the entire thing being checked for here.
            if ($extension -notmatch '^(?i)\.E[A-Z]{2}$') { continue }
            $fileCount++
            $kind = $extension.ToUpper().TrimStart('.')
            $byExtension[$kind] = 1 + $byExtension[$kind]

            if ($kind -ne $Expected) {
                # Which seasons it touches decides whether the floor still covers it.
                $reader = New-Object IO.StreamReader($entry.Open())
                try {
                    $seasons = @{}
                    while ($null -ne ($line = $reader.ReadLine())) {
                        if ($line -match '^id,\S{3}(\d{4})') { $seasons[[int]$Matches[1]] = $true }
                    }
                } finally { $reader.Close() }
                $above = @($seasons.Keys | Where-Object { $_ -ge $SeasonFloor })
                $where = if ($above.Count) { "seasons $($above -join ', ')" } else { "all below the floor" }
                $offenders.Add("$($zip.Name)/$($entry.Name) is .$kind - $where")
            }
        }
    } finally { $archive.Dispose() }
}

Write-Output "postseason event files read: $fileCount"
Write-Output "by extension:"
$byExtension.GetEnumerator() | Sort-Object Name | ForEach-Object { "  .$($_.Key.PadRight(4)) $($_.Value)" }
Write-Output ""

# ⚠️ Checked before anything is concluded. An empty directory would otherwise produce "no offenders"
# and read as a pass — the absence of a check reading as the presence of a passing one.
if ($fileCount -eq 0) {
    throw "no .E?? entries under $ZipDirectory - nothing was checked, and a check of nothing is not a pass"
}

if ($offenders.Count) {
    Write-Output "FAILED - the postseason download is no longer a single kind of file:"
    $offenders | ForEach-Object { "  $_" }
    Write-Output ""
    Write-Output "What this means: POSTSEASON_SEASON_FLOOR admits postseason games at $SeasonFloor and"
    Write-Output "above on the strength of there being nothing to exclude. That is no longer true."
    Write-Output "Either the floor moves above every season listed, or the postseason needs a"
    Write-Output "provenance table of its own - the same shape the regular season already has."
    throw "$($offenders.Count) postseason event files are not .$Expected"
}

Write-Output "PASS - every postseason event file is .$Expected"
Write-Output "  no league letter, so no Negro Leagues file to separate"
Write-Output "  no .ED? twin, so no deduced reconstruction to exclude"
Write-Output "  the floor at $SeasonFloor therefore has nothing to protect against in this download"
