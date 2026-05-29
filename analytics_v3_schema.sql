SET statement_timeout = 0;
SET lock_timeout = 0;
SET maintenance_work_mem = '1GB';
SET work_mem = '256MB';

DROP MATERIALIZED VIEW IF EXISTS mv_bench_pain_hall;
DROP MATERIALIZED VIEW IF EXISTS mv_weekly_explosions;
DROP MATERIALIZED VIEW IF EXISTS mv_rank_race_top50;
DROP MATERIALIZED VIEW IF EXISTS mv_scatter_lab_sample;
DROP MATERIALIZED VIEW IF EXISTS mv_club_gameweek_profile;
DROP TABLE IF EXISTS mv_bench_pain_hall;
DROP TABLE IF EXISTS mv_weekly_explosions;
DROP TABLE IF EXISTS mv_rank_race_top50;
DROP TABLE IF EXISTS mv_scatter_lab_sample;
DROP TABLE IF EXISTS mv_club_gameweek_profile;
DROP TYPE IF EXISTS mv_club_gameweek_profile CASCADE;
DROP TABLE IF EXISTS manager_club_assignment;

CREATE UNLOGGED TABLE manager_club_assignment AS
SELECT
    entry,
    COALESCE(NULLIF(raw->>'favourite_team', '')::integer, 0) AS team_id
FROM managers;

CREATE UNIQUE INDEX idx_manager_club_assignment_entry ON manager_club_assignment (entry);
CREATE INDEX idx_manager_club_assignment_team ON manager_club_assignment (team_id);
ANALYZE manager_club_assignment;

CREATE MATERIALIZED VIEW mv_bench_pain_hall AS
SELECT
    entry,
    entry_name,
    player_name,
    rank,
    total,
    bench_points,
    avg_bench_points,
    avg_points,
    volatility,
    transfer_cost,
    archetype
FROM mv_manager_metrics
ORDER BY bench_points DESC NULLS LAST, rank ASC
LIMIT 500;

CREATE UNIQUE INDEX idx_mv_bench_pain_hall_entry ON mv_bench_pain_hall (entry);

CREATE MATERIALIZED VIEW mv_weekly_explosions AS
SELECT
    mgh.event,
    mgh.entry,
    ks.entry_name,
    ks.player_name,
    ks.rank AS final_rank,
    ks.total,
    mgh.points,
    mgh.points_on_bench,
    mgh.event_transfers_cost,
    mgh.value / 10.0 AS team_value
FROM manager_gw_history mgh
JOIN kenya_standings ks ON ks.entry = mgh.entry AND ks.league_id = 131
ORDER BY mgh.points DESC, ks.rank ASC
LIMIT 500;

CREATE INDEX idx_mv_weekly_explosions_points ON mv_weekly_explosions (points DESC);
CREATE INDEX idx_mv_weekly_explosions_event ON mv_weekly_explosions (event);

CREATE MATERIALIZED VIEW mv_rank_race_top50 AS
SELECT
    ks.entry,
    ks.entry_name,
    ks.player_name,
    ks.rank AS final_rank,
    mgh.event,
    mgh.total_points,
    mgh.points
FROM kenya_standings ks
JOIN manager_gw_history mgh ON mgh.entry = ks.entry
WHERE ks.league_id = 131 AND ks.rank <= 50
ORDER BY ks.rank, mgh.event;

CREATE UNIQUE INDEX idx_mv_rank_race_top50_entry_event ON mv_rank_race_top50 (entry, event);

CREATE MATERIALIZED VIEW mv_scatter_lab_sample AS
SELECT
    entry,
    entry_name,
    player_name,
    rank,
    total,
    avg_points,
    volatility,
    bench_points,
    transfer_cost,
    avg_team_value,
    max_team_value,
    consistency_ratio,
    points_per_million,
    archetype
FROM mv_manager_metrics
WHERE rank <= 1000
   OR entry % 197 = 0
ORDER BY rank ASC
LIMIT 3500;

CREATE UNIQUE INDEX idx_mv_scatter_lab_sample_entry ON mv_scatter_lab_sample (entry);

CREATE MATERIALIZED VIEW mv_club_gameweek_profile AS
WITH named AS (
    SELECT
        mc.team_id,
        COALESCE(fts.team_name, 'No club declared') AS team_name,
        COALESCE(fts.short_name, 'NONE') AS short_name,
        mgh.event,
        mgh.points,
        mgh.points_on_bench,
        mgh.event_transfers_cost
    FROM manager_club_assignment mc
    JOIN manager_gw_history mgh ON mgh.entry = mc.entry
    LEFT JOIN mv_favorite_team_summary fts ON fts.team_id = mc.team_id
)
SELECT
    team_id,
    team_name,
    short_name,
    event,
    count(*)::integer AS managers,
    round(avg(points), 2) AS avg_points,
    round(avg(points_on_bench), 2) AS avg_bench_points,
    round(avg(event_transfers_cost), 2) AS avg_transfer_cost
FROM named
GROUP BY team_id, team_name, short_name, event
ORDER BY team_id, event;

CREATE UNIQUE INDEX idx_mv_club_gameweek_profile_team_event ON mv_club_gameweek_profile (team_id, event);

ANALYZE mv_bench_pain_hall;
ANALYZE mv_weekly_explosions;
ANALYZE mv_rank_race_top50;
ANALYZE mv_scatter_lab_sample;
ANALYZE mv_club_gameweek_profile;
