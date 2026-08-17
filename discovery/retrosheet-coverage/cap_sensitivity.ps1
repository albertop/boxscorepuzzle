# Pool size as a function of the roster caps, instead of at one assumed pair of caps.
#
# coverage_funnel.ps1 answers "how big is the pool at <=10 batters and <=3 pitchers". Those caps are
# provisional estimates (design §6), so that answer is only valid for a board nobody has measured
# yet. This script removes the assumption: it reports the surviving directions across a grid of
# caps, and against the total row budget, so that when a browser prototype produces the real row
# ceiling the pool size can be read off directly rather than re-measured.
#
# The height budget constrains batters and pitchers TOGETHER — the board is one scrolling column of
# rows — so the board_rows table is the one that maps onto a measured row ceiling. The grid matters
# for the split between the two sections once that ceiling is known.
#
# Read-only against DGL. Creates session temp tables only.

param(
    [string]$DeducedGameIdsFile = "deduced_game_ids.txt",
    [string]$ConnectionString = "DSN=LocalServer;DATABASE=DGL;Encrypt=no;TrustServerCertificate=yes"
)

$ErrorActionPreference = "Stop"

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

    Invoke-NonQuery @"
SELECT GAME_ID, TEAM_ID,
       SUM(CASE WHEN B_G = 1 THEN 1 ELSE 0 END) AS batters,
       SUM(CASE WHEN P_G = 1 THEN 1 ELSE 0 END) AS pitchers
INTO #shape
FROM dbo.retroDailyReg
GROUP BY GAME_ID, TEAM_ID
"@
    Invoke-NonQuery "CREATE UNIQUE CLUSTERED INDEX ix_shape ON #shape (GAME_ID, TEAM_ID)"

    # Non-deduced directions only. The discrepancy filter is left out here: it is orthogonal to the
    # caps and would just scale every cell by roughly the same factor.
    Invoke-NonQuery @"
SELECT g.SEASON,
       offense.batters AS off_batters,
       defense.pitchers AS def_pitchers
INTO #direction
FROM dbo.retroGamesReg g
JOIN #shape offense ON offense.GAME_ID = g.GAME_ID
JOIN #shape defense ON defense.GAME_ID = g.GAME_ID AND defense.TEAM_ID <> offense.TEAM_ID
WHERE NOT EXISTS (SELECT 1 FROM #deduced d WHERE d.GAME_ID = g.GAME_ID)
"@
    Invoke-NonQuery "CREATE CLUSTERED INDEX ix_direction ON #direction (off_batters, def_pitchers)"

    Invoke-Report @"
WITH batter_caps AS (SELECT v FROM (VALUES (9),(10),(11),(12),(13),(14),(15),(16)) t(v)),
     pitcher_caps AS (SELECT v FROM (VALUES (1),(2),(3),(4),(5),(6)) t(v))
SELECT b.v AS batters_cap, p.v AS pitchers_cap, COUNT(*) AS directions
FROM batter_caps b
CROSS JOIN pitcher_caps p
JOIN #direction d ON d.off_batters <= b.v AND d.def_pitchers <= p.v
GROUP BY b.v, p.v
ORDER BY b.v, p.v
"@ "GRID: directions surviving by cap pair"

    Invoke-Report @"
SELECT board_rows,
       directions,
       SUM(directions) OVER (ORDER BY board_rows ROWS UNBOUNDED PRECEDING) AS cumulative
FROM (
  SELECT off_batters + def_pitchers AS board_rows, COUNT(*) AS directions
  FROM #direction GROUP BY off_batters + def_pitchers) t
ORDER BY board_rows
"@ "ROW BUDGET: directions by total data rows (batters + pitchers), cumulative"

    Invoke-Report @"
SELECT (SEASON/10)*10 AS decade,
       SUM(CASE WHEN off_batters + def_pitchers <= 11 THEN 1 ELSE 0 END) AS rows_le_11,
       SUM(CASE WHEN off_batters + def_pitchers <= 13 THEN 1 ELSE 0 END) AS rows_le_13,
       SUM(CASE WHEN off_batters + def_pitchers <= 15 THEN 1 ELSE 0 END) AS rows_le_15,
       SUM(CASE WHEN off_batters + def_pitchers <= 17 THEN 1 ELSE 0 END) AS rows_le_17
FROM #direction GROUP BY (SEASON/10)*10 ORDER BY 1
"@ "ERA SKEW as a function of the row budget"
}
finally {
    $connection.Close()
}
