# Record where every event-file game came from, permanently (design §32).
#
# The DGL loader concatenates every "<season>*.E??" entry into one <season>.EVE before the Chadwick
# tools run, so by the time a game reaches SQL Server the file it came from is gone and a deduced
# reconstruction is indistinguishable from a scored game. Today the distinction is recovered by
# re-reading the zips and holding a text file of ids next to whichever script needs it, which means
# every future query has to remember to do that, and one that forgets silently admits reconstructions
# into the pool.
#
# This writes the distinction into the database instead, as an additive table. Nothing existing is
# altered: `dbo.retroGameProvenance` is a new table keyed by GAME_ID, and any query that wants a
# clean pool joins it.
#
# The zips remain the source of truth — this table is rebuildable from Retrosheet's original files by
# running the script again, which is the requirement in CLAUDE.md for anything the backup does not
# cover.
#
#   .EVA / .EVN / .EVF   scored from a real scoresheet
#   .EDA / .EDN / .EDF   deduced: reconstructed from partial information, excluded from the pool
#
# Writes one table. Run with -DryRun first to see the counts without touching the database.

param(
    [string]$ZipDirectory = "C:\Users\aperd\Documents\DGLv2\retrosheet\downloads\zip\events-reg",
    [switch]$DryRun,
    [string]$ConnectionString = "DSN=LocalServer;DATABASE=DGL;Encrypt=no;TrustServerCertificate=yes"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression.FileSystem

# --- read the zips: one row per game, carrying the extension it was found under ---
$origin = @{}
$fileCount = 0
foreach ($zip in Get-ChildItem $ZipDirectory -Filter *.zip) {
    $archive = [IO.Compression.ZipFile]::OpenRead($zip.FullName)
    try {
        foreach ($entry in $archive.Entries) {
            $extension = [IO.Path]::GetExtension($entry.Name)
            if ($extension -notmatch '^(?i)\.E[VD][ANF]$') { continue }
            $fileCount++
            $reader = New-Object IO.StreamReader($entry.Open())
            try {
                while ($null -ne ($line = $reader.ReadLine())) {
                    if ($line -match '^id,(\S+)') { $origin[$Matches[1]] = $extension.ToUpper().TrimStart('.') }
                }
            }
            finally { $reader.Close() }
        }
    }
    finally { $archive.Dispose() }
}

$deduced = @($origin.Keys | Where-Object { $origin[$_].StartsWith('ED') })
Write-Output "event files read : $fileCount"
Write-Output "games found      : $($origin.Count)"
Write-Output "of them deduced  : $($deduced.Count)"

if ($DryRun) {
    Write-Output "dry run - nothing written"
    return
}

$connection = New-Object System.Data.Odbc.OdbcConnection $ConnectionString
$connection.Open()
$command = $connection.CreateCommand()
$command.CommandTimeout = 1800

try {
    # Dropped and rebuilt rather than merged. The zips are the source of truth, the table is derived
    # from them in full, and a rebuild that cannot leave a stale row behind is easier to trust than a
    # reconciliation that can.
    $command.CommandText = @"
IF OBJECT_ID('dbo.retroGameProvenance', 'U') IS NOT NULL DROP TABLE dbo.retroGameProvenance;
CREATE TABLE dbo.retroGameProvenance (
    GAME_ID     varchar(20)  NOT NULL PRIMARY KEY,
    source_type varchar(3)   NOT NULL,
    is_deduced  bit          NOT NULL,
    loaded_at   datetime2(0) NOT NULL CONSTRAINT DF_retroGameProvenance_loaded_at DEFAULT SYSUTCDATETIME()
);
"@
    [void]$command.ExecuteNonQuery()

    $keys = @($origin.Keys)
    for ($offset = 0; $offset -lt $keys.Count; $offset += 200) {
        $chunk = $keys[$offset..([Math]::Min($offset + 199, $keys.Count - 1))]
        $command.Parameters.Clear()
        $command.CommandText = "INSERT INTO dbo.retroGameProvenance (GAME_ID, source_type, is_deduced) VALUES " +
            (($chunk | ForEach-Object { "(?,?,?)" }) -join ",")
        foreach ($id in $chunk) {
            [void]$command.Parameters.Add((New-Object System.Data.Odbc.OdbcParameter("", $id)))
            [void]$command.Parameters.Add((New-Object System.Data.Odbc.OdbcParameter("", $origin[$id])))
            [void]$command.Parameters.Add((New-Object System.Data.Odbc.OdbcParameter("", [int]$origin[$id].StartsWith('ED'))))
        }
        [void]$command.ExecuteNonQuery()
    }
    $command.Parameters.Clear()

    $command.CommandText = @"
SELECT (SELECT COUNT(*) FROM dbo.retroGameProvenance) AS rows_written,
       (SELECT COUNT(*) FROM dbo.retroGameProvenance WHERE is_deduced = 1) AS deduced,
       (SELECT COUNT(*) FROM dbo.retroGamesReg g JOIN dbo.retroGameProvenance p ON p.GAME_ID = g.GAME_ID) AS matched_regular,
       (SELECT COUNT(*) FROM dbo.retroGamesReg g LEFT JOIN dbo.retroGameProvenance p ON p.GAME_ID = g.GAME_ID
          WHERE p.GAME_ID IS NULL) AS games_with_no_provenance
"@
    $reader = $command.ExecuteReader()
    while ($reader.Read()) {
        Write-Output ""
        Write-Output "rows written             : $($reader['rows_written'])"
        Write-Output "deduced                  : $($reader['deduced'])"
        Write-Output "matched in retroGamesReg : $($reader['matched_regular'])"
        Write-Output "games with no provenance : $($reader['games_with_no_provenance'])"
    }
    $reader.Close()
}
finally {
    $connection.Close()
}
