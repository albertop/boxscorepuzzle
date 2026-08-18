# Era distribution of the pool AFTER the zero-density gate (design §5).
#
# The funnel measured how the decades survive the roster caps. The gate came later, and a gate that
# throws out boards made mostly of noughts is not era-neutral by construction: a dead-ball afternoon
# with three hits and no runs is exactly the board it removes, and those are not spread evenly across
# a century. If the gate empties an era the calendar was counting on, that is a pool problem, and it
# is cheaper to find out here than after the inventory is built.
#
# Zero density is computed the way the board defines it — over the erasable grid only, which is the
# batting rows plus their totals and the pitching rows plus theirs. The line score and the footnotes
# are given, never erased, and so cannot make a board boring to fill in.
#
# The caps are the ones the browser prototype settled on: at most 13 batters for the offensive team
# and at most 2 pitchers for the defensive team (§6).
#
# Requires dbo.retroGameProvenance — run load_provenance.ps1 first. Deduced games and Negro Leagues
# games are excluded through it.
#
# Read-only against DGL. Creates session temp tables only; nothing is written to the database.

param(
    [int]$MaxBatters = 13,
    [int]$MaxPitchers = 2,
    [string]$ConnectionString = "DSN=LocalServer;DATABASE=DGL;Encrypt=no;TrustServerCertificate=yes"
)

$ErrorActionPreference = "Stop"

$connection = New-Object System.Data.Odbc.OdbcConnection $ConnectionString
$connection.Open()
$command = $connection.CreateCommand()
$command.CommandTimeout = 3600

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
    # Provenance comes from the table now, not from a text file loaded into a temp table. Deduced
    # games are reconstructions from partial information; Negro Leagues games are newspaper box
    # scores that balance every identity and are still not trustworthy — load_provenance.ps1 carries
    # the measurement behind both exclusions.
    Invoke-Report @"
SELECT (SELECT COUNT(*) FROM dbo.retroGameProvenance) AS provenance_rows,
       (SELECT COUNT(*) FROM dbo.retroGamesReg g LEFT JOIN dbo.retroGameProvenance p ON p.GAME_ID = g.GAME_ID
          WHERE p.GAME_ID IS NULL) AS games_with_no_provenance
"@ "PROVENANCE CHECK - a game with no row would leave the funnel silently"

    Invoke-NonQuery @"
SELECT GAME_ID INTO #excluded FROM dbo.retroGameProvenance
WHERE is_deduced = 1 OR source_type = 'EVR'
"@
    Invoke-NonQuery "CREATE UNIQUE CLUSTERED INDEX ix_excluded ON #excluded (GAME_ID)"

    # --- per (game, team): roster shape, zeros in the six board columns, and the column sums ---
    # The sums are here so a totals row can be counted as a zero cell too. A totals cell is nought
    # exactly when every row above it is, which is the shutout column the gate exists to catch.
    Invoke-NonQuery @"
SELECT GAME_ID, TEAM_ID,
       SUM(CASE WHEN B_G = 1 AND (B_PA > 0 OR B_R > 0 OR B_H > 0 OR B_BB > 0 OR B_SO > 0 OR B_HP > 0 OR B_SF > 0 OR B_SH > 0 OR B_XI > 0) THEN 1 ELSE 0 END) AS batters,
       SUM(CASE WHEN P_G = 1 THEN 1 ELSE 0 END) AS pitchers,
       SUM(CASE WHEN B_G = 1 AND (B_PA > 0 OR B_R > 0 OR B_H > 0 OR B_BB > 0 OR B_SO > 0 OR B_HP > 0 OR B_SF > 0 OR B_SH > 0 OR B_XI > 0) THEN
            CASE WHEN B_PA = 0 THEN 1 ELSE 0 END + CASE WHEN B_AB = 0 THEN 1 ELSE 0 END +
            CASE WHEN B_R  = 0 THEN 1 ELSE 0 END + CASE WHEN B_H  = 0 THEN 1 ELSE 0 END +
            CASE WHEN B_BB = 0 THEN 1 ELSE 0 END + CASE WHEN B_SO = 0 THEN 1 ELSE 0 END
           ELSE 0 END) AS batting_zeros,
       SUM(CASE WHEN P_G = 1 THEN
            CASE WHEN P_OUT = 0 THEN 1 ELSE 0 END + CASE WHEN P_H  = 0 THEN 1 ELSE 0 END +
            CASE WHEN P_R   = 0 THEN 1 ELSE 0 END + CASE WHEN P_ER = 0 THEN 1 ELSE 0 END +
            CASE WHEN P_BB  = 0 THEN 1 ELSE 0 END + CASE WHEN P_SO = 0 THEN 1 ELSE 0 END
           ELSE 0 END) AS pitching_zeros,
       SUM(CASE WHEN B_G = 1 AND (B_PA > 0 OR B_R > 0 OR B_H > 0 OR B_BB > 0 OR B_SO > 0 OR B_HP > 0 OR B_SF > 0 OR B_SH > 0 OR B_XI > 0) THEN B_PA ELSE 0 END) AS t_pa,
       SUM(CASE WHEN B_G = 1 AND (B_PA > 0 OR B_R > 0 OR B_H > 0 OR B_BB > 0 OR B_SO > 0 OR B_HP > 0 OR B_SF > 0 OR B_SH > 0 OR B_XI > 0) THEN B_AB ELSE 0 END) AS t_ab,
       SUM(CASE WHEN B_G = 1 AND (B_PA > 0 OR B_R > 0 OR B_H > 0 OR B_BB > 0 OR B_SO > 0 OR B_HP > 0 OR B_SF > 0 OR B_SH > 0 OR B_XI > 0) THEN B_R  ELSE 0 END) AS t_r,
       SUM(CASE WHEN B_G = 1 AND (B_PA > 0 OR B_R > 0 OR B_H > 0 OR B_BB > 0 OR B_SO > 0 OR B_HP > 0 OR B_SF > 0 OR B_SH > 0 OR B_XI > 0) THEN B_H  ELSE 0 END) AS t_h,
       SUM(CASE WHEN B_G = 1 AND (B_PA > 0 OR B_R > 0 OR B_H > 0 OR B_BB > 0 OR B_SO > 0 OR B_HP > 0 OR B_SF > 0 OR B_SH > 0 OR B_XI > 0) THEN B_BB ELSE 0 END) AS t_bb,
       SUM(CASE WHEN B_G = 1 AND (B_PA > 0 OR B_R > 0 OR B_H > 0 OR B_BB > 0 OR B_SO > 0 OR B_HP > 0 OR B_SF > 0 OR B_SH > 0 OR B_XI > 0) THEN B_SO ELSE 0 END) AS t_so,
       SUM(CASE WHEN P_G = 1 THEN P_OUT ELSE 0 END) AS t_out,
       SUM(CASE WHEN P_G = 1 THEN P_H   ELSE 0 END) AS t_ph,
       SUM(CASE WHEN P_G = 1 THEN P_R   ELSE 0 END) AS t_pr,
       SUM(CASE WHEN P_G = 1 THEN P_ER  ELSE 0 END) AS t_per,
       SUM(CASE WHEN P_G = 1 THEN P_BB  ELSE 0 END) AS t_pbb,
       SUM(CASE WHEN P_G = 1 THEN P_SO  ELSE 0 END) AS t_pso
INTO #side
FROM dbo.retroDailyReg
GROUP BY GAME_ID, TEAM_ID
"@
    Invoke-NonQuery "CREATE UNIQUE CLUSTERED INDEX ix_side ON #side (GAME_ID, TEAM_ID)"

    # --- board-relevant discrepancies, so the counts line up with the funnel's last step ---
    Invoke-NonQuery @"
SELECT DISTINCT gameId AS GAME_ID, teamId AS TEAM_ID, type AS side
INTO #discrepancy
FROM dbo.retroDiscrepancies
WHERE gameId IS NOT NULL AND LTRIM(RTRIM(gameId)) <> '' AND type IN ('O','P')
  AND statType IN ('AB','R','H','RBI','BB','SO','IP','ER','BFP','G')
"@
    Invoke-NonQuery "CREATE UNIQUE CLUSTERED INDEX ix_discrepancy ON #discrepancy (GAME_ID, TEAM_ID, side)"

    # --- one row per surviving direction, with its zero density ---
    Invoke-NonQuery @"
SELECT g.GAME_ID, g.SEASON, o.TEAM_ID AS off_team, d.TEAM_ID AS def_team,
       CAST(
         o.batting_zeros + d.pitching_zeros
         + CASE WHEN o.t_pa  = 0 THEN 1 ELSE 0 END + CASE WHEN o.t_ab  = 0 THEN 1 ELSE 0 END
         + CASE WHEN o.t_r   = 0 THEN 1 ELSE 0 END + CASE WHEN o.t_h   = 0 THEN 1 ELSE 0 END
         + CASE WHEN o.t_bb  = 0 THEN 1 ELSE 0 END + CASE WHEN o.t_so  = 0 THEN 1 ELSE 0 END
         + CASE WHEN d.t_out = 0 THEN 1 ELSE 0 END + CASE WHEN d.t_ph  = 0 THEN 1 ELSE 0 END
         + CASE WHEN d.t_pr  = 0 THEN 1 ELSE 0 END + CASE WHEN d.t_per = 0 THEN 1 ELSE 0 END
         + CASE WHEN d.t_pbb = 0 THEN 1 ELSE 0 END + CASE WHEN d.t_pso = 0 THEN 1 ELSE 0 END
         AS float) / (6.0 * (o.batters + 1) + 6.0 * (d.pitchers + 1)) AS zero_density,
       o.t_r AS offense_runs,
       CASE WHEN disc_off.GAME_ID IS NULL AND disc_def.GAME_ID IS NULL THEN 0 ELSE 1 END AS has_discrepancy
INTO #kept
FROM dbo.retroGamesReg g
JOIN #side o ON o.GAME_ID = g.GAME_ID
JOIN #side d ON d.GAME_ID = g.GAME_ID AND d.TEAM_ID <> o.TEAM_ID
LEFT JOIN #excluded x ON x.GAME_ID = g.GAME_ID
LEFT JOIN #discrepancy disc_off ON disc_off.GAME_ID = g.GAME_ID AND disc_off.TEAM_ID = o.TEAM_ID AND disc_off.side = 'O'
LEFT JOIN #discrepancy disc_def ON disc_def.GAME_ID = g.GAME_ID AND disc_def.TEAM_ID = d.TEAM_ID AND disc_def.side = 'P'
WHERE x.GAME_ID IS NULL AND o.batters <= $MaxBatters AND d.pitchers <= $MaxPitchers
"@

    Invoke-Report @"
SELECT COUNT(*) AS after_roster,
       SUM(CASE WHEN has_discrepancy = 0 THEN 1 ELSE 0 END) AS after_discrepancy,
       SUM(CASE WHEN has_discrepancy = 0 AND zero_density < 0.30 THEN 1 ELSE 0 END) AS after_gate_30,
       SUM(CASE WHEN has_discrepancy = 0 AND zero_density < 0.35 THEN 1 ELSE 0 END) AS after_gate_35,
       SUM(CASE WHEN has_discrepancy = 0 AND zero_density < 0.40 THEN 1 ELSE 0 END) AS after_gate_40
FROM #kept
"@ "FUNNEL FROM THE ROSTER CAPS ONWARDS"

    Invoke-Report @"
SELECT 'min' AS point, MIN(zero_density) AS value FROM #kept
UNION ALL SELECT 'p10', MAX(zero_density) FROM (SELECT TOP 10 PERCENT zero_density FROM #kept ORDER BY zero_density) a
UNION ALL SELECT 'p25', MAX(zero_density) FROM (SELECT TOP 25 PERCENT zero_density FROM #kept ORDER BY zero_density) b
UNION ALL SELECT 'p50', MAX(zero_density) FROM (SELECT TOP 50 PERCENT zero_density FROM #kept ORDER BY zero_density) c
UNION ALL SELECT 'p75', MAX(zero_density) FROM (SELECT TOP 75 PERCENT zero_density FROM #kept ORDER BY zero_density) d
UNION ALL SELECT 'p90', MAX(zero_density) FROM (SELECT TOP 90 PERCENT zero_density FROM #kept ORDER BY zero_density) e
UNION ALL SELECT 'max', MAX(zero_density) FROM #kept
"@ "ZERO DENSITY ACROSS THE WHOLE POOL"

    Invoke-Report @"
SELECT (SEASON/10)*10 AS decade,
       COUNT(*) AS after_roster,
       SUM(CASE WHEN zero_density < 0.30 THEN 1 ELSE 0 END) AS after_gate_30,
       SUM(CASE WHEN zero_density < 0.35 THEN 1 ELSE 0 END) AS after_gate_35,
       CAST(100.0 * SUM(CASE WHEN zero_density < 0.30 THEN 1 ELSE 0 END) / COUNT(*) AS decimal(5,1)) AS survival_30_pct,
       CAST(AVG(zero_density) AS decimal(5,3)) AS mean_zero_density,
       CAST(AVG(CAST(offense_runs AS float)) AS decimal(4,2)) AS mean_runs
FROM #kept GROUP BY (SEASON/10)*10 ORDER BY 1
"@ "DECADE DISTRIBUTION AFTER THE GATE"

    # Composition, not counts. The question is whether the gate changes which eras the pool is made
    # of, and a decade can shrink in absolute terms while holding its share of what is left.
    Invoke-Report @"
SELECT (SEASON/10)*10 AS decade,
       CAST(100.0 * COUNT(*) / (SELECT COUNT(*) FROM #kept) AS decimal(5,2)) AS share_before_pct,
       CAST(100.0 * SUM(CASE WHEN zero_density < 0.30 THEN 1 ELSE 0 END)
            / NULLIF((SELECT COUNT(*) FROM #kept WHERE zero_density < 0.30), 0) AS decimal(5,2)) AS share_after_pct
FROM #kept GROUP BY (SEASON/10)*10 ORDER BY 1
"@ "DOES THE GATE CHANGE WHAT THE POOL IS MADE OF"
}
finally {
    $connection.Close()
}
