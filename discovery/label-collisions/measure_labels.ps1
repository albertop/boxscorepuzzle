# How often two batting rows carry the same position label, and whether it matters.
#
# Rows start labelled by position (§7) and a footnote is attributed the same way — `HBP: SS`. If two
# rows are labelled `SS`, the player cannot tell which of them was hit by the pitch, and the row
# identity for both becomes unusable until something else settles it. That is the ambiguity §5
# records as a constraint on erasure rather than on the pool.
#
# The obvious collision is `P`: in a game without a designated hitter the pitcher bats, and if he is
# lifted for a pinch hitter the replacement pitcher bats in the same slot and is labelled `P` too.
# Pinch hitters and defensive replacements produce others.
#
# This matters more at the new caps: ≤4 pitchers admits games with more substitutions than ≤2 did,
# so the run reports both pools side by side rather than only the one that ships.
#
# Requires dbo.retroGameProvenance. Read-only; session temp tables only.

param(
    [int]$MaxBatters = 13,
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
    # Same label expression the loader uses, so the collisions counted here are the ones a player
    # would actually see on the board.
    Invoke-NonQuery @"
SELECT d.GAME_ID, d.TEAM_ID, d.PLAYER_ID,
       CASE WHEN d.F_P_G=1 THEN 'P' WHEN d.F_C_G=1 THEN 'C' WHEN d.F_1B_G=1 THEN '1B'
            WHEN d.F_2B_G=1 THEN '2B' WHEN d.F_3B_G=1 THEN '3B' WHEN d.F_SS_G=1 THEN 'SS'
            WHEN d.F_LF_G=1 THEN 'LF' WHEN d.F_CF_G=1 THEN 'CF' WHEN d.F_RF_G=1 THEN 'RF'
            WHEN d.B_G_DH=1 THEN 'DH' WHEN d.B_G_PH=1 THEN 'PH' WHEN d.B_G_PR=1 THEN 'PR'
            ELSE '?' END AS label,
       CASE WHEN d.B_HP > 0 OR d.B_SF > 0 OR d.B_SH > 0 OR d.B_XI > 0 THEN 1 ELSE 0 END AS carries_footnote
INTO #row
FROM dbo.retroDailyReg d
WHERE d.B_G = 1
"@
    Invoke-NonQuery "CREATE CLUSTERED INDEX ix_row ON #row (GAME_ID, TEAM_ID, label)"

    Invoke-NonQuery @"
SELECT GAME_ID, TEAM_ID,
       SUM(CASE WHEN B_G=1 THEN 1 ELSE 0 END) AS batters,
       SUM(CASE WHEN P_G=1 THEN 1 ELSE 0 END) AS pitchers,
       SUM(CASE WHEN B_G=1 THEN
            CASE WHEN B_PA=0 THEN 1 ELSE 0 END + CASE WHEN B_AB=0 THEN 1 ELSE 0 END +
            CASE WHEN B_R=0 THEN 1 ELSE 0 END + CASE WHEN B_H=0 THEN 1 ELSE 0 END +
            CASE WHEN B_BB=0 THEN 1 ELSE 0 END + CASE WHEN B_SO=0 THEN 1 ELSE 0 END ELSE 0 END) AS bz,
       SUM(CASE WHEN P_G=1 THEN
            CASE WHEN P_OUT=0 THEN 1 ELSE 0 END + CASE WHEN P_H=0 THEN 1 ELSE 0 END +
            CASE WHEN P_R=0 THEN 1 ELSE 0 END + CASE WHEN P_ER=0 THEN 1 ELSE 0 END +
            CASE WHEN P_BB=0 THEN 1 ELSE 0 END + CASE WHEN P_SO=0 THEN 1 ELSE 0 END ELSE 0 END) AS pz,
       SUM(CASE WHEN B_G=1 THEN B_PA ELSE 0 END) AS t_pa, SUM(CASE WHEN B_G=1 THEN B_AB ELSE 0 END) AS t_ab,
       SUM(CASE WHEN B_G=1 THEN B_R ELSE 0 END) AS t_r, SUM(CASE WHEN B_G=1 THEN B_H ELSE 0 END) AS t_h,
       SUM(CASE WHEN B_G=1 THEN B_BB ELSE 0 END) AS t_bb, SUM(CASE WHEN B_G=1 THEN B_SO ELSE 0 END) AS t_so,
       SUM(CASE WHEN P_G=1 THEN P_OUT ELSE 0 END) AS t_out, SUM(CASE WHEN P_G=1 THEN P_H ELSE 0 END) AS t_ph,
       SUM(CASE WHEN P_G=1 THEN P_R ELSE 0 END) AS t_pr, SUM(CASE WHEN P_G=1 THEN P_ER ELSE 0 END) AS t_per,
       SUM(CASE WHEN P_G=1 THEN P_BB ELSE 0 END) AS t_pbb, SUM(CASE WHEN P_G=1 THEN P_SO ELSE 0 END) AS t_pso
INTO #side
FROM dbo.retroDailyReg GROUP BY GAME_ID, TEAM_ID
"@
    Invoke-NonQuery "CREATE UNIQUE CLUSTERED INDEX ix_side ON #side (GAME_ID, TEAM_ID)"

    Invoke-NonQuery @"
SELECT g.SEASON, o.GAME_ID, o.TEAM_ID AS off_team, d.pitchers AS def_pitchers
INTO #direction
FROM dbo.retroGamesReg g
JOIN #side o ON o.GAME_ID = g.GAME_ID
JOIN #side d ON d.GAME_ID = g.GAME_ID AND d.TEAM_ID <> o.TEAM_ID
JOIN dbo.retroGameProvenance p ON p.GAME_ID = g.GAME_ID
WHERE p.is_deduced = 0 AND p.source_type <> 'EVR'
  AND o.batters <= $MaxBatters AND d.pitchers <= 4
  AND CAST(o.bz + d.pz
      + CASE WHEN o.t_pa=0 THEN 1 ELSE 0 END + CASE WHEN o.t_ab=0 THEN 1 ELSE 0 END
      + CASE WHEN o.t_r=0 THEN 1 ELSE 0 END + CASE WHEN o.t_h=0 THEN 1 ELSE 0 END
      + CASE WHEN o.t_bb=0 THEN 1 ELSE 0 END + CASE WHEN o.t_so=0 THEN 1 ELSE 0 END
      + CASE WHEN d.t_out=0 THEN 1 ELSE 0 END + CASE WHEN d.t_ph=0 THEN 1 ELSE 0 END
      + CASE WHEN d.t_pr=0 THEN 1 ELSE 0 END + CASE WHEN d.t_per=0 THEN 1 ELSE 0 END
      + CASE WHEN d.t_pbb=0 THEN 1 ELSE 0 END + CASE WHEN d.t_pso=0 THEN 1 ELSE 0 END AS float)
      / (6.0 * (o.batters + 1) + 6.0 * (d.pitchers + 1)) < 0.30
"@
    Invoke-NonQuery "CREATE CLUSTERED INDEX ix_direction ON #direction (GAME_ID, off_team)"

    # A group is a label used by two or more rows on the same side. A group *matters* when at least
    # one of its rows carries a footnote term, because that is when the attribution is ambiguous.
    Invoke-NonQuery @"
SELECT r.GAME_ID, r.TEAM_ID, r.label, COUNT(*) AS rows_sharing,
       SUM(r.carries_footnote) AS with_footnote
INTO #group
FROM #row r
JOIN #direction x ON x.GAME_ID = r.GAME_ID AND x.off_team = r.TEAM_ID
GROUP BY r.GAME_ID, r.TEAM_ID, r.label
HAVING COUNT(*) > 1
"@

    Invoke-Report @"
SELECT (SELECT COUNT(*) FROM #direction) AS directions,
       (SELECT COUNT(DISTINCT CAST(GAME_ID AS varchar(20)) + TEAM_ID) FROM #group) AS with_a_collision,
       (SELECT COUNT(DISTINCT CAST(GAME_ID AS varchar(20)) + TEAM_ID) FROM #group WHERE with_footnote > 0)
         AS collision_carrying_a_footnote,
       (SELECT COUNT(*) FROM #group) AS collision_groups
"@ "HOW OFTEN TWO BATTING ROWS SHARE A LABEL (gated, <=$MaxBatters batters, <=4 pitchers)"

    Invoke-Report @"
SELECT label, COUNT(*) AS groups_,
       SUM(rows_sharing) AS rows_involved,
       SUM(CASE WHEN with_footnote > 0 THEN 1 ELSE 0 END) AS groups_with_a_footnote,
       MAX(rows_sharing) AS worst_group
FROM #group GROUP BY label ORDER BY COUNT(*) DESC
"@ "WHICH LABELS COLLIDE"

    Invoke-Report @"
SELECT x.def_pitchers,
       COUNT(DISTINCT CAST(x.GAME_ID AS varchar(20)) + x.off_team) AS directions,
       COUNT(DISTINCT CASE WHEN g.GAME_ID IS NOT NULL
             THEN CAST(x.GAME_ID AS varchar(20)) + x.off_team END) AS with_a_collision
FROM #direction x
LEFT JOIN #group g ON g.GAME_ID = x.GAME_ID AND g.TEAM_ID = x.off_team
GROUP BY x.def_pitchers ORDER BY x.def_pitchers
"@ "DOES THE PITCHER CAP BRING MORE COLLISIONS (by the defence's pitcher count)"

    Invoke-Report @"
SELECT (x.SEASON/10)*10 AS decade,
       COUNT(DISTINCT CAST(x.GAME_ID AS varchar(20)) + x.off_team) AS directions,
       COUNT(DISTINCT CASE WHEN g.GAME_ID IS NOT NULL
             THEN CAST(x.GAME_ID AS varchar(20)) + x.off_team END) AS with_a_collision
FROM #direction x
LEFT JOIN #group g ON g.GAME_ID = x.GAME_ID AND g.TEAM_ID = x.off_team
GROUP BY (x.SEASON/10)*10 ORDER BY 1
"@ "COLLISIONS BY DECADE"
}
finally {
    $connection.Close()
}
