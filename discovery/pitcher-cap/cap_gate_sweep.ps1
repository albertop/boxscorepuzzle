# What each roster cap and gate combination leaves in the pool, and whether the era quota survives.
#
# §5 now carries a calendar quota rather than a pool filter: **pre-1950 boards must not exceed 5% of
# what the player sees**, roughly eighteen puzzles a year. The pool may stay as old as it likes; the
# calendar builder rations it. That moves the binding constraint from "how many directions survive"
# to "how many directions from 1950 onwards survive", because with pre-1950 capped at one puzzle in
# twenty, everything else has to come from the modern half.
#
# The years of calendar a cell can supply is therefore:
#
#     post-1950 directions / 0.95 / 674 per year
#
# The ≤2 pitcher cap is under review (§6). Its justification was screen cost, and that argument was
# retired by the working-set measurement without the cap being revisited. The sweep runs to ≤5.
#
# Requires dbo.retroGameProvenance. Read-only; session temp tables only.

param(
    [string]$ConnectionString = "DSN=LocalServer;DATABASE=DGL;Encrypt=no;TrustServerCertificate=yes"
)

$ErrorActionPreference = "Stop"

$connection = New-Object System.Data.Odbc.OdbcConnection $ConnectionString
$connection.Open()
$command = $connection.CreateCommand()
$command.CommandTimeout = 3600

function Invoke-NonQuery([string]$sql) {
    $script:command.CommandText = $sql
    [void]$script:command.ExecuteNonQuery()
}

function Invoke-Report([string]$sql, [string]$label) {
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
    Invoke-NonQuery @"
SELECT GAME_ID, TEAM_ID,
       SUM(CASE WHEN B_G = 1 AND B_PA > 0 THEN 1 ELSE 0 END) AS batters,
       SUM(CASE WHEN P_G = 1 THEN 1 ELSE 0 END) AS pitchers,
       SUM(CASE WHEN B_G = 1 AND B_PA > 0 THEN
            CASE WHEN B_PA = 0 THEN 1 ELSE 0 END + CASE WHEN B_AB = 0 THEN 1 ELSE 0 END +
            CASE WHEN B_R  = 0 THEN 1 ELSE 0 END + CASE WHEN B_H  = 0 THEN 1 ELSE 0 END +
            CASE WHEN B_BB = 0 THEN 1 ELSE 0 END + CASE WHEN B_SO = 0 THEN 1 ELSE 0 END
           ELSE 0 END) AS batting_zeros,
       SUM(CASE WHEN P_G = 1 THEN
            CASE WHEN P_OUT = 0 THEN 1 ELSE 0 END + CASE WHEN P_H  = 0 THEN 1 ELSE 0 END +
            CASE WHEN P_R   = 0 THEN 1 ELSE 0 END + CASE WHEN P_ER = 0 THEN 1 ELSE 0 END +
            CASE WHEN P_BB  = 0 THEN 1 ELSE 0 END + CASE WHEN P_SO = 0 THEN 1 ELSE 0 END
           ELSE 0 END) AS pitching_zeros,
       SUM(CASE WHEN B_G = 1 AND B_PA > 0 THEN B_PA ELSE 0 END) AS t_pa, SUM(CASE WHEN B_G = 1 AND B_PA > 0 THEN B_AB ELSE 0 END) AS t_ab,
       SUM(CASE WHEN B_G = 1 AND B_PA > 0 THEN B_R  ELSE 0 END) AS t_r,  SUM(CASE WHEN B_G = 1 AND B_PA > 0 THEN B_H  ELSE 0 END) AS t_h,
       SUM(CASE WHEN B_G = 1 AND B_PA > 0 THEN B_BB ELSE 0 END) AS t_bb, SUM(CASE WHEN B_G = 1 AND B_PA > 0 THEN B_SO ELSE 0 END) AS t_so,
       SUM(CASE WHEN P_G = 1 THEN P_OUT ELSE 0 END) AS t_out, SUM(CASE WHEN P_G = 1 THEN P_H  ELSE 0 END) AS t_ph,
       SUM(CASE WHEN P_G = 1 THEN P_R   ELSE 0 END) AS t_pr,  SUM(CASE WHEN P_G = 1 THEN P_ER ELSE 0 END) AS t_per,
       SUM(CASE WHEN P_G = 1 THEN P_BB  ELSE 0 END) AS t_pbb, SUM(CASE WHEN P_G = 1 THEN P_SO ELSE 0 END) AS t_pso
INTO #side
FROM dbo.retroDailyReg
GROUP BY GAME_ID, TEAM_ID
"@
    Invoke-NonQuery "CREATE UNIQUE CLUSTERED INDEX ix_side ON #side (GAME_ID, TEAM_ID)"

    Invoke-NonQuery @"
SELECT DISTINCT gameId AS GAME_ID, teamId AS TEAM_ID, type AS side
INTO #discrepancy
FROM dbo.retroDiscrepancies
WHERE gameId IS NOT NULL AND LTRIM(RTRIM(gameId)) <> '' AND type IN ('O','P')
  AND statType IN ('AB','R','H','RBI','BB','SO','IP','ER','BFP','G')
"@
    Invoke-NonQuery "CREATE UNIQUE CLUSTERED INDEX ix_discrepancy ON #discrepancy (GAME_ID, TEAM_ID, side)"

    Invoke-NonQuery @"
SELECT g.SEASON, o.batters AS off_batters, d.pitchers AS def_pitchers,
       CAST(
         o.batting_zeros + d.pitching_zeros
         + CASE WHEN o.t_pa  = 0 THEN 1 ELSE 0 END + CASE WHEN o.t_ab  = 0 THEN 1 ELSE 0 END
         + CASE WHEN o.t_r   = 0 THEN 1 ELSE 0 END + CASE WHEN o.t_h   = 0 THEN 1 ELSE 0 END
         + CASE WHEN o.t_bb  = 0 THEN 1 ELSE 0 END + CASE WHEN o.t_so  = 0 THEN 1 ELSE 0 END
         + CASE WHEN d.t_out = 0 THEN 1 ELSE 0 END + CASE WHEN d.t_ph  = 0 THEN 1 ELSE 0 END
         + CASE WHEN d.t_pr  = 0 THEN 1 ELSE 0 END + CASE WHEN d.t_per = 0 THEN 1 ELSE 0 END
         + CASE WHEN d.t_pbb = 0 THEN 1 ELSE 0 END + CASE WHEN d.t_pso = 0 THEN 1 ELSE 0 END
         AS float) / (6.0 * (o.batters + 1) + 6.0 * (d.pitchers + 1)) AS zero_density
INTO #kept
FROM dbo.retroGamesReg g
JOIN #side o ON o.GAME_ID = g.GAME_ID
JOIN #side d ON d.GAME_ID = g.GAME_ID AND d.TEAM_ID <> o.TEAM_ID
JOIN dbo.retroGameProvenance p ON p.GAME_ID = g.GAME_ID
LEFT JOIN #discrepancy disc_off ON disc_off.GAME_ID = g.GAME_ID AND disc_off.TEAM_ID = o.TEAM_ID AND disc_off.side = 'O'
LEFT JOIN #discrepancy disc_def ON disc_def.GAME_ID = g.GAME_ID AND disc_def.TEAM_ID = d.TEAM_ID AND disc_def.side = 'P'
WHERE p.is_deduced = 0 AND p.source_type <> 'EVR'
  AND disc_off.GAME_ID IS NULL AND disc_def.GAME_ID IS NULL
  AND o.batters <= 15 AND d.pitchers <= 5
"@
    Invoke-NonQuery "CREATE CLUSTERED INDEX ix_kept ON #kept (off_batters, def_pitchers, zero_density)"

    # 674 directions a year (§31). Under the 5% quota the pre-1950 half cannot carry the calendar, so
    # the supply is what 1950 onwards can feed: post_1950 / 0.95 puzzles in total.
    Invoke-Report @"
SELECT b.cap AS max_batters, p.cap AS max_pitchers, g.gate,
       COUNT(k.SEASON) AS directions,
       SUM(CASE WHEN k.SEASON >= 1950 THEN 1 ELSE 0 END) AS from_1950_on,
       CAST(100.0 * SUM(CASE WHEN k.SEASON < 1950 THEN 1 ELSE 0 END) / NULLIF(COUNT(k.SEASON), 0) AS decimal(5,1))
         AS pre_1950_pct,
       CAST(SUM(CASE WHEN k.SEASON >= 1950 THEN 1 ELSE 0 END) / 0.95 / 674.0 AS decimal(6,1)) AS years_under_quota
FROM (VALUES (13),(14),(15)) b(cap)
CROSS JOIN (VALUES (2),(3),(4),(5)) p(cap)
CROSS JOIN (VALUES (0.30),(0.35),(0.40)) g(gate)
LEFT JOIN #kept k ON k.off_batters <= b.cap AND k.def_pitchers <= p.cap AND k.zero_density < g.gate
GROUP BY b.cap, p.cap, g.gate
ORDER BY g.gate, b.cap, p.cap
"@ "CAP AND GATE SWEEP - years_under_quota is the number that binds"

    Invoke-Report @"
SELECT p.cap AS max_pitchers, (k.SEASON/10)*10 AS decade, COUNT(*) AS directions
FROM (VALUES (2),(3),(4),(5)) p(cap)
JOIN #kept k ON k.def_pitchers <= p.cap AND k.off_batters <= 13 AND k.zero_density < 0.30
WHERE k.SEASON >= 1950
GROUP BY p.cap, (k.SEASON/10)*10 ORDER BY p.cap, decade
"@ "WHERE THE MODERN POOL COMES FROM (batters <= 13, gate 30%)"

    Invoke-Report @"
SELECT p.cap AS max_pitchers, (k.SEASON/10)*10 AS decade, COUNT(*) AS directions
FROM (VALUES (2),(3),(4),(5)) p(cap)
JOIN #kept k ON k.def_pitchers <= p.cap AND k.off_batters <= 13 AND k.zero_density < 0.35
WHERE k.SEASON >= 1950
GROUP BY p.cap, (k.SEASON/10)*10 ORDER BY p.cap, decade
"@ "THE SAME AT A 35% GATE"

    # How much of the board the pitching section would occupy, and how many directions each exact
    # pitcher count contributes. An extra row that almost never appears is not worth a cap change.
    Invoke-Report @"
SELECT def_pitchers, COUNT(*) AS directions,
       SUM(CASE WHEN SEASON >= 1950 THEN 1 ELSE 0 END) AS from_1950_on,
       SUM(CASE WHEN SEASON >= 1980 THEN 1 ELSE 0 END) AS from_1980_on,
       CAST(AVG(zero_density) AS decimal(5,3)) AS mean_zero_density
FROM #kept WHERE off_batters <= 13 GROUP BY def_pitchers ORDER BY def_pitchers
"@ "WHAT EACH EXACT PITCHER COUNT CONTRIBUTES (before the gate)"
}
finally {
    $connection.Close()
}
