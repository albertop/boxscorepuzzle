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
#   .EVA / .EVN / .EVF   scored from a real scoresheet, American / National / Federal
#   .EVR                 Negro Leagues — recorded, and excluded from the pool (see below)
#   .EDA / .EDN / .EDF   deduced: reconstructed from partial information, excluded from the pool
#
# Two source types are excluded from the puzzle pool, and the table exists so that the exclusion is a
# join rather than a thing every query has to remember:
#
#     WHERE p.is_deduced = 0 AND p.source_type <> 'EVR'
#
# The Negro Leagues exclusion is a data-trust decision, not an identity one. Those 1,872 games
# balance every identity the board uses — 3,744 directions, zero mismatches on the row identity and
# on all four cross-team sums, cleaner than the contemporary control. They are still box scores
# transcribed from newspapers rather than scored games, and a column such as strikeouts is blank in
# the source and nought in the data: 93.7% of their batter rows carry K = 0 against 74.2% in
# 1935-1949 regular play. A board that balances and is wrong is the failure mode §22 calls the worst,
# because nothing downstream can catch it.
#
# Every E?? entry is read rather than a list of known extensions, and the extension is stored
# verbatim. The first version of this script matched `.E[VD][ANF]` and silently lost all 1,872 Negro
# Leagues games — which is precisely the failure the table exists to prevent, so it does not get to
# happen twice through a second hardcoded list.
#
# Writes one table. Run with -DryRun first to see the counts without touching the database.

param(
    [string]$ZipDirectory = "C:\Users\aperd\Documents\DGLv2\retrosheet\downloads\zip\events-reg",
    [switch]$DryRun,
    # ⚠⚠ **v28-P2-02: a rebuild that found nothing used to publish nothing.** The table was
    # dropped and recreated before the first insert, with no precondition and no transaction, so an
    # empty or mistyped -ZipDirectory replaced the canonical table with an empty one and reported zero
    # rows as a result rather than as a failure. Every cohort in this project inner-joins this table,
    # and an empty one reads as "no game has admissible provenance" - the filter passing on absence,
    # which is the shape this project keeps meeting.
    #
    # ShrinkTolerance refuses a load materially smaller than what is already there: a rebuild adds
    # seasons, it does not lose them. 0.02 absorbs the noise of a re-download and stops a half-read
    # directory. PROVISIONAL - chosen rather than measured, and -Force is the deliberate override.
    [double]$ShrinkTolerance = 0.02,
    [switch]$Force,
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
            if ($extension -notmatch '^(?i)\.E[A-Z]{2}$') { continue }
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
Write-Output ""
Write-Output "by source type:"
$origin.Values | Group-Object | Sort-Object Name | ForEach-Object { "  $($_.Name.PadRight(4)) $($_.Count)" }

# ⚠️ Checked before the connection is opened, so a refusal cannot leave the database touched at all.
# The cheapest guarantee available is the one where nothing has happened yet.
if ($fileCount -eq 0) {
    throw "no .E?? entries under $ZipDirectory - nothing to load, and the existing table is untouched"
}
if ($origin.Count -eq 0) {
    throw "$fileCount event files held no 'id,' line - the parse is wrong, and the existing table is untouched"
}
$types = @($origin.Values | Sort-Object -Unique)
if (($types -notcontains 'EVA') -and ($types -notcontains 'EVN')) {
    throw "no EVA or EVN games among [$($types -join ', ')] - this is not a regular-season event set"
}

if ($DryRun) {
    Write-Output "dry run - nothing written"
    return
}

$connection = New-Object System.Data.Odbc.OdbcConnection $ConnectionString
$connection.Open()
$command = $connection.CreateCommand()
$command.CommandTimeout = 1800

# ⚠️ How many rows the table holds today, read before anything is written. A rebuild that loses most
# of the pool is a broken input, not a smaller season set.
$command.CommandText = "SELECT CASE WHEN OBJECT_ID('dbo.retroGameProvenance','U') IS NULL THEN -1 " +
    "ELSE (SELECT COUNT(*) FROM dbo.retroGameProvenance) END"
$existing = [int]$command.ExecuteScalar()
if ($existing -ge 0) { Write-Output "existing table holds     : $existing" }
else { Write-Output "existing table           : none, this is a first load" }

if (($existing -gt 0) -and ($origin.Count -lt ($existing * (1 - $ShrinkTolerance))) -and (-not $Force)) {
    $connection.Close()
    throw ("this load has $($origin.Count) games against the existing $existing, a drop of " +
        "$([Math]::Round((1 - $origin.Count / $existing) * 100, 1))% - refusing. " +
        "Check -ZipDirectory, or pass -Force if the shrink is intended. The table is untouched.")
}

$transaction = $connection.BeginTransaction()
$command.Transaction = $transaction
try {
    # ⚠⚠ **Built beside the canonical table, never in place of it.** The old code dropped the
    # real table and then inserted, so every failure between those two points - a bad path, a dropped
    # connection, an interrupted batch - left the project's admissibility filter empty or half full,
    # and nothing downstream can tell a truncated provenance table from a small one. Staging plus a
    # transactional swap means the canonical table is only ever replaced by one already known good.
    $command.CommandText = @"
IF OBJECT_ID('dbo.retroGameProvenanceStaging', 'U') IS NOT NULL DROP TABLE dbo.retroGameProvenanceStaging;
CREATE TABLE dbo.retroGameProvenanceStaging (
    GAME_ID     varchar(20)  NOT NULL PRIMARY KEY,
    source_type varchar(3)   NOT NULL,
    is_deduced  bit          NOT NULL,
    -- ⚠⚠ **Unnamed on purpose (v28-P2-04).** A named default constraint made this loader work
    -- exactly once: sp_rename renames the table and not its constraints, so the canonical table kept
    -- DF_retroGameProvenanceStaging_loaded_at, and the next rebuild's CREATE TABLE collided with it --
    -- constraint names are schema-scoped, not table-scoped. Every later refresh then failed
    -- deterministically before staging a row. The transaction meant provenance was never corrupted,
    -- which is exactly why it would have gone unnoticed until someone needed a rebuild.
    -- Letting the server generate the name keeps it unique per creation, and nothing reads it.
    loaded_at   datetime2(0) NOT NULL DEFAULT SYSUTCDATETIME()
);
"@
    [void]$command.ExecuteNonQuery()

    $keys = @($origin.Keys)
    for ($offset = 0; $offset -lt $keys.Count; $offset += 200) {
        $chunk = $keys[$offset..([Math]::Min($offset + 199, $keys.Count - 1))]
        $command.Parameters.Clear()
        $command.CommandText = "INSERT INTO dbo.retroGameProvenanceStaging (GAME_ID, source_type, is_deduced) VALUES " +
            (($chunk | ForEach-Object { "(?,?,?)" }) -join ",")
        foreach ($id in $chunk) {
            [void]$command.Parameters.Add((New-Object System.Data.Odbc.OdbcParameter("", $id)))
            [void]$command.Parameters.Add((New-Object System.Data.Odbc.OdbcParameter("", $origin[$id])))
            [void]$command.Parameters.Add((New-Object System.Data.Odbc.OdbcParameter("", [int]$origin[$id].StartsWith('ED'))))
        }
        [void]$command.ExecuteNonQuery()
    }
    $command.Parameters.Clear()

    # ⚠️ The staged rows are checked before the swap, inside the same transaction, so a failure here
    # rolls back to the table that was already there. Every count is what was intended to be written.
    $command.CommandText = "SELECT COUNT(*) FROM dbo.retroGameProvenanceStaging"
    $staged = [int]$command.ExecuteScalar()
    if ($staged -ne $origin.Count) {
        throw "staged $staged rows of $($origin.Count) parsed - the insert lost rows, rolling back"
    }
    $command.CommandText = "SELECT COUNT(*) FROM dbo.retroGameProvenanceStaging WHERE is_deduced = 0"
    if ([int]$command.ExecuteScalar() -eq 0) {
        throw "every staged game is deduced - a set with no playable source is not the pool, rolling back"
    }

    $command.CommandText = @"
IF OBJECT_ID('dbo.retroGameProvenance', 'U') IS NOT NULL DROP TABLE dbo.retroGameProvenance;
EXEC sp_rename 'dbo.retroGameProvenanceStaging', 'retroGameProvenance';
"@
    [void]$command.ExecuteNonQuery()
    $transaction.Commit()
    $command.Transaction = $null
    Write-Output "swapped in $staged rows"
}
catch {
    # ⚠️ Rolled back, then said out loud. A loader that fails quietly is how the table became empty.
    $transaction.Rollback()
    $command.Transaction = $null
    Write-Output "ROLLED BACK - the previous table is intact"
    throw
}

try {
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
