# Retrosheet coverage funnel for the boxscore puzzle pool.
#
# Answers the first open data item in design §36: how many candidate puzzles actually survive the
# hard filters, counted by DIRECTION rather than by game. A direction is one team's offense against
# the opposing team's pitching; a single game can yield up to two of them, and can qualify in one
# direction while failing in the other (design §5).
#
# Steps:
#   0. Regular-season games with an event file, and the two directions each one implies
#   1. Minus deduced games (see extract_deduced_game_ids.ps1)
#   2. Minus directions whose roster does not fit the board: the offensive team must use at most
#      10 batters and the defensive team at most 3 pitchers (design §6 — six data columns and a
#      phone-sized board)
#   3. Minus directions touched by a Retrosheet/official discrepancy in a stat the board uses.
#      Not requested by the funnel, but it is failure type 1 of §22 ("the historical boxscore does
#      not balance at source") and it is cheap to measure here.
#
# Read-only against DGL. Creates session temp tables only; nothing is written to the database.

param(
    [string]$DeducedGameIdsFile = "deduced_game_ids.txt",
    [string]$ConnectionString = "DSN=LocalServer;DATABASE=DGL;Encrypt=no;TrustServerCertificate=yes"
)

$ErrorActionPreference = "Stop"

# Board columns: batting AB R H RBI BB K, pitching IP H R ER BB K. G and BFP are included because a
# wrong appearance count changes the roster shape and BFP anchors the PA identity.
$BoardStatTypes = @('AB', 'R', 'H', 'RBI', 'BB', 'SO', 'IP', 'ER', 'BFP', 'G')

$connection = New-Object System.Data.Odbc.OdbcConnection $ConnectionString
$connection.Open()
$command = $connection.CreateCommand()
$command.CommandTimeout = 1800

function Invoke-NonQuery([string]$sql) {
    $script:command.Parameters.Clear()
    $script:command.CommandText = $sql
    [void]$script:command.ExecuteNonQuery()
}

function Invoke-Report([string]$sql, [string]$label) {
    $script:command.Parameters.Clear()
    $script:command.CommandText = $sql
    $reader = $script:command.ExecuteReader()
    Write-Output ""
    Write-Output "=== $label ==="
    $columns = @(); for ($i = 0; $i -lt $reader.FieldCount; $i++) { $columns += $reader.GetName($i) }
    Write-Output ($columns -join "`t")
    while ($reader.Read()) {
        $values = @(); for ($i = 0; $i -lt $reader.FieldCount; $i++) { $values += $reader[$i] }
        Write-Output ($values -join "`t")
    }
    $reader.Close()
}

try {
    # --- deduced game ids, loaded parameterized and batched ---
    Invoke-NonQuery "CREATE TABLE #deduced (GAME_ID varchar(20) PRIMARY KEY)"
    $ids = Get-Content $DeducedGameIdsFile
    for ($offset = 0; $offset -lt $ids.Count; $offset += 200) {
        $chunk = $ids[$offset..([Math]::Min($offset + 199, $ids.Count - 1))]
        $command.Parameters.Clear()
        $command.CommandText = "INSERT INTO #deduced (GAME_ID) VALUES " + (($chunk | ForEach-Object { "(?)" }) -join ",")
        foreach ($id in $chunk) {
            [void]$command.Parameters.Add((New-Object System.Data.Odbc.OdbcParameter("", $id)))
        }
        [void]$command.ExecuteNonQuery()
    }
    $command.Parameters.Clear()

    Invoke-Report @"
SELECT COUNT(*) AS deduced_loaded,
       (SELECT COUNT(*) FROM dbo.retroGamesReg g JOIN #deduced d ON d.GAME_ID = g.GAME_ID) AS matched_in_games
FROM #deduced
"@ "deduced load check"

    # --- roster shape per (game, team) ---
    Invoke-NonQuery @"
SELECT GAME_ID, TEAM_ID,
       SUM(CASE WHEN B_G = 1 THEN 1 ELSE 0 END) AS batters,
       SUM(CASE WHEN P_G = 1 THEN 1 ELSE 0 END) AS pitchers
INTO #shape
FROM dbo.retroDailyReg
GROUP BY GAME_ID, TEAM_ID
"@
    Invoke-NonQuery "CREATE UNIQUE CLUSTERED INDEX ix_shape ON #shape (GAME_ID, TEAM_ID)"

    # --- board-relevant discrepancies per (game, team, side) ---
    $statList = ($BoardStatTypes | ForEach-Object { "'$_'" }) -join ","
    Invoke-NonQuery @"
SELECT DISTINCT gameId AS GAME_ID, teamId AS TEAM_ID, type AS side
INTO #discrepancy
FROM dbo.retroDiscrepancies
WHERE gameId IS NOT NULL AND LTRIM(RTRIM(gameId)) <> ''
  AND type IN ('O','P')
  AND statType IN ($statList)
"@
    Invoke-NonQuery "CREATE UNIQUE CLUSTERED INDEX ix_discrepancy ON #discrepancy (GAME_ID, TEAM_ID, side)"

    # --- one row per direction ---
    Invoke-NonQuery @"
SELECT g.GAME_ID, g.SEASON,
       offense.TEAM_ID AS off_team, defense.TEAM_ID AS def_team,
       offense.batters AS off_batters, defense.pitchers AS def_pitchers,
       CASE WHEN d.GAME_ID IS NULL THEN 0 ELSE 1 END AS is_deduced,
       CASE WHEN disc_off.GAME_ID IS NULL AND disc_def.GAME_ID IS NULL THEN 0 ELSE 1 END AS has_discrepancy
INTO #direction
FROM dbo.retroGamesReg g
JOIN #shape offense ON offense.GAME_ID = g.GAME_ID
JOIN #shape defense ON defense.GAME_ID = g.GAME_ID AND defense.TEAM_ID <> offense.TEAM_ID
LEFT JOIN #deduced d ON d.GAME_ID = g.GAME_ID
LEFT JOIN #discrepancy disc_off ON disc_off.GAME_ID = g.GAME_ID AND disc_off.TEAM_ID = offense.TEAM_ID AND disc_off.side = 'O'
LEFT JOIN #discrepancy disc_def ON disc_def.GAME_ID = g.GAME_ID AND disc_def.TEAM_ID = defense.TEAM_ID AND disc_def.side = 'P'
"@

    Invoke-Report @"
SELECT
  (SELECT COUNT(*) FROM dbo.retroGamesReg)                                 AS s0_games_raw,
  (SELECT COUNT(*) FROM #direction)                                        AS s0_directions_raw,
  (SELECT COUNT(*) FROM #direction WHERE is_deduced = 0)                   AS s1_after_deduced,
  (SELECT COUNT(*) FROM #direction WHERE is_deduced = 0
     AND off_batters <= 10 AND def_pitchers <= 3)                          AS s2_after_roster,
  (SELECT COUNT(*) FROM #direction WHERE is_deduced = 0
     AND off_batters <= 10 AND def_pitchers <= 3 AND has_discrepancy = 0)  AS s3_after_discrepancy
"@ "FUNNEL (counted by direction)"

    Invoke-Report @"
SELECT directions_kept, COUNT(*) AS games FROM (
  SELECT GAME_ID,
         SUM(CASE WHEN is_deduced = 0 AND off_batters <= 10 AND def_pitchers <= 3 THEN 1 ELSE 0 END) AS directions_kept
  FROM #direction GROUP BY GAME_ID) t
GROUP BY directions_kept ORDER BY 1
"@ "directions yielded per game, after the roster filter"

    Invoke-Report @"
SELECT off_batters, COUNT(*) AS directions FROM #direction WHERE is_deduced = 0 GROUP BY off_batters ORDER BY 1
"@ "batters used by the offensive team"

    Invoke-Report @"
SELECT def_pitchers, COUNT(*) AS directions FROM #direction WHERE is_deduced = 0 GROUP BY def_pitchers ORDER BY 1
"@ "pitchers used by the defensive team"

    Invoke-Report @"
SELECT (SEASON/10)*10 AS decade,
       SUM(CASE WHEN is_deduced = 0 THEN 1 ELSE 0 END) AS after_deduced,
       SUM(CASE WHEN is_deduced = 0 AND off_batters <= 10 AND def_pitchers <= 3 THEN 1 ELSE 0 END) AS after_roster,
       SUM(CASE WHEN is_deduced = 0 AND off_batters <= 10 AND def_pitchers <= 3 AND has_discrepancy = 0 THEN 1 ELSE 0 END) AS after_discrepancy
FROM #direction GROUP BY (SEASON/10)*10 ORDER BY 1
"@ "DECADE DISTRIBUTION (directions)"
}
finally {
    $connection.Close()
}
