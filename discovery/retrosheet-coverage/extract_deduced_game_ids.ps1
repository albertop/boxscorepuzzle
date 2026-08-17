# Extract the GAME_IDs of Retrosheet deduced games.
#
# Retrosheet ships deduced play-by-play in files with an .EDA / .EDN / .EDF extension, packaged
# inside the same <season>eve.zip as the regular .EVA / .EVN / .EVF files. The DGL loader
# concatenates every "<season>*.E??" file into one <season>.EVE before running the Chadwick tools,
# so by the time the data reaches SQL Server the file of origin is gone and deduced games are
# indistinguishable from the rest.
#
# The zips are therefore the only place where that distinction still exists. This script reads the
# .ED? entries without unpacking them and writes one GAME_ID per line.
#
# Deduced games must be excluded from the puzzle pool: they are reconstructions from partial
# information, and reconstructions are where boxscores that do not balance show up (design §32).

param(
    [string]$ZipDirectory = "C:\Users\aperd\Documents\DGLv2\retrosheet\downloads\zip\events-reg",
    [string]$OutputFile = "deduced_game_ids.txt"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression.FileSystem

$gameIds = New-Object System.Collections.Generic.List[string]
$deducedFileCount = 0

foreach ($zip in Get-ChildItem $ZipDirectory -Filter *.zip) {
    $archive = [IO.Compression.ZipFile]::OpenRead($zip.FullName)
    try {
        foreach ($entry in $archive.Entries) {
            if ([IO.Path]::GetExtension($entry.Name) -notmatch '^(?i)\.ED[ANF]$') { continue }
            $deducedFileCount++
            $reader = New-Object IO.StreamReader($entry.Open())
            try {
                while ($null -ne ($line = $reader.ReadLine())) {
                    if ($line -match '^id,(\S+)') { $gameIds.Add($Matches[1]) }
                }
            }
            finally { $reader.Close() }
        }
    }
    finally { $archive.Dispose() }
}

$unique = $gameIds | Sort-Object -Unique
$unique | Set-Content -Path $OutputFile -Encoding ascii

Write-Output "deduced event files read : $deducedFileCount"
Write-Output "deduced game ids         : $($unique.Count)"
Write-Output "written to               : $OutputFile"
