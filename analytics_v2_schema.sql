SET statement_timeout = 0;
SET lock_timeout = 0;
SET maintenance_work_mem = '1GB';
SET work_mem = '256MB';

DROP MATERIALIZED VIEW IF EXISTS mv_manager_metrics;
DROP MATERIALIZED VIEW IF EXISTS mv_gameweek_extremes;
DROP MATERIALIZED VIEW IF EXISTS mv_rank_band_gameweeks;
DROP MATERIALIZED VIEW IF EXISTS mv_percentile_ladder;
DROP MATERIALIZED VIEW IF EXISTS mv_favorite_team_summary;
DROP TABLE IF EXISTS mv_manager_metrics;
DROP TABLE IF EXISTS mv_gameweek_extremes;
DROP TABLE IF EXISTS mv_rank_band_gameweeks;
DROP TABLE IF EXISTS mv_percentile_ladder;
DROP TABLE IF EXISTS mv_favorite_team_summary;

CREATE MATERIALIZED VIEW mv_manager_metrics AS
WITH metrics AS (
    SELECT
        ks.entry,
        ks.entry_name,
        ks.player_name,
        ks.rank,
        ks.total,
        avg(mgh.points)::numeric AS avg_points,
        stddev_pop(mgh.points)::numeric AS volatility,
        max(mgh.points)::integer AS best_week,
        min(mgh.points)::integer AS worst_week,
        sum(mgh.points_on_bench)::integer AS bench_points,
        avg(mgh.points_on_bench)::numeric AS avg_bench_points,
        sum(mgh.event_transfers_cost)::integer AS transfer_cost,
        avg(mgh.value) / 10.0 AS avg_team_value,
        max(mgh.value) / 10.0 AS max_team_value,
        count(*)::integer AS weeks
    FROM kenya_standings ks
    JOIN manager_gw_history mgh ON mgh.entry = ks.entry
    WHERE ks.league_id = 131
    GROUP BY ks.entry, ks.entry_name, ks.player_name, ks.rank, ks.total
)
SELECT
    *,
    CASE
        WHEN volatility <= 10 AND rank <= 10000 THEN 'Steady elite'
        WHEN best_week >= 100 AND volatility >= 18 THEN 'Boom hunter'
        WHEN bench_points >= 300 THEN 'Bench leaker'
        WHEN transfer_cost >= 80 THEN 'Hit addict'
        WHEN rank <= 4457 THEN 'Top one percent'
        WHEN volatility <= 9 THEN 'Low-noise grinder'
        ELSE 'Season survivor'
    END AS archetype,
    round((avg_points / NULLIF(volatility, 0))::numeric, 3) AS consistency_ratio,
    round((total / NULLIF(avg_team_value, 0))::numeric, 2) AS points_per_million
FROM metrics;

CREATE UNIQUE INDEX idx_mv_manager_metrics_entry ON mv_manager_metrics (entry);
CREATE INDEX idx_mv_manager_metrics_rank ON mv_manager_metrics (rank);
CREATE INDEX idx_mv_manager_metrics_archetype ON mv_manager_metrics (archetype);
CREATE INDEX idx_mv_manager_metrics_consistency ON mv_manager_metrics (consistency_ratio DESC);
CREATE INDEX idx_mv_manager_metrics_efficiency ON mv_manager_metrics (points_per_million DESC);
CREATE INDEX IF NOT EXISTS idx_manager_gw_history_event_bench ON manager_gw_history (event, points_on_bench DESC);

CREATE MATERIALIZED VIEW mv_gameweek_extremes AS
WITH events AS (
    SELECT generate_series(1, 38) AS event
),
score_json AS (
    SELECT
        events.event,
        jsonb_agg(
            jsonb_build_object(
                'entry', ranked.entry,
                'entry_name', ranked.entry_name,
                'player_name', ranked.player_name,
                'final_rank', ranked.final_rank,
                'points', ranked.points
            )
            ORDER BY ranked.points DESC, ranked.final_rank ASC
        ) AS top_scores
    FROM events
    CROSS JOIN LATERAL (
        SELECT
            mgh.entry,
            ks.entry_name,
            ks.player_name,
            ks.rank AS final_rank,
            mgh.points
        FROM manager_gw_history mgh
        JOIN kenya_standings ks ON ks.entry = mgh.entry AND ks.league_id = 131
        WHERE mgh.event = events.event
        ORDER BY mgh.points DESC, ks.rank ASC
        LIMIT 10
    ) ranked
    GROUP BY events.event
),
bench_json AS (
    SELECT
        events.event,
        jsonb_agg(
            jsonb_build_object(
                'entry', ranked.entry,
                'entry_name', ranked.entry_name,
                'player_name', ranked.player_name,
                'final_rank', ranked.final_rank,
                'points_on_bench', ranked.points_on_bench
            )
            ORDER BY ranked.points_on_bench DESC, ranked.final_rank ASC
        ) AS bench_pain
    FROM events
    CROSS JOIN LATERAL (
        SELECT
            mgh.entry,
            ks.entry_name,
            ks.player_name,
            ks.rank AS final_rank,
            mgh.points_on_bench
        FROM manager_gw_history mgh
        JOIN kenya_standings ks ON ks.entry = mgh.entry AND ks.league_id = 131
        WHERE mgh.event = events.event
        ORDER BY mgh.points_on_bench DESC, ks.rank ASC
        LIMIT 10
    ) ranked
    GROUP BY events.event
)
SELECT
    COALESCE(score_json.event, bench_json.event) AS event,
    score_json.top_scores,
    bench_json.bench_pain
FROM score_json
FULL JOIN bench_json ON bench_json.event = score_json.event
ORDER BY event;

CREATE UNIQUE INDEX idx_mv_gameweek_extremes_event ON mv_gameweek_extremes (event);

CREATE MATERIALIZED VIEW mv_rank_band_gameweeks AS
WITH base AS (
    SELECT
        ks.entry,
        CASE
            WHEN ks.rank <= 100 THEN 'Top 100'
            WHEN ks.rank <= 1000 THEN 'Top 1K'
            WHEN ks.rank <= ceil(445629 * 0.01) THEN 'Top 1%'
            WHEN ks.rank <= ceil(445629 * 0.05) THEN 'Top 5%'
            WHEN ks.rank <= ceil(445629 * 0.10) THEN 'Top 10%'
            WHEN ks.rank BETWEEN floor(445629 * 0.45) AND ceil(445629 * 0.55) THEN 'Median'
            ELSE NULL
        END AS band
    FROM kenya_standings ks
    WHERE ks.league_id = 131
)
SELECT
    base.band,
    mgh.event,
    count(*)::integer AS managers,
    round(avg(mgh.points), 2) AS avg_points,
    round(avg(mgh.points_on_bench), 2) AS avg_bench_points,
    round(avg(mgh.event_transfers_cost), 2) AS avg_transfer_cost,
    round(avg(mgh.value) / 10.0, 2) AS avg_team_value
FROM base
JOIN manager_gw_history mgh ON mgh.entry = base.entry
WHERE base.band IS NOT NULL
GROUP BY base.band, mgh.event;

CREATE UNIQUE INDEX idx_mv_rank_band_gameweeks_band_event ON mv_rank_band_gameweeks (band, event);

CREATE MATERIALIZED VIEW mv_percentile_ladder AS
SELECT *
FROM (
    SELECT 'Champion' AS label, 1::numeric AS percentile, max(total)::integer AS points FROM kenya_standings WHERE league_id = 131
    UNION ALL SELECT 'Top 0.1%', 0.999, percentile_cont(0.999) WITHIN GROUP (ORDER BY total)::integer FROM kenya_standings WHERE league_id = 131
    UNION ALL SELECT 'Top 1%', 0.99, percentile_cont(0.99) WITHIN GROUP (ORDER BY total)::integer FROM kenya_standings WHERE league_id = 131
    UNION ALL SELECT 'Top 5%', 0.95, percentile_cont(0.95) WITHIN GROUP (ORDER BY total)::integer FROM kenya_standings WHERE league_id = 131
    UNION ALL SELECT 'Top 10%', 0.90, percentile_cont(0.90) WITHIN GROUP (ORDER BY total)::integer FROM kenya_standings WHERE league_id = 131
    UNION ALL SELECT 'Median', 0.50, percentile_cont(0.50) WITHIN GROUP (ORDER BY total)::integer FROM kenya_standings WHERE league_id = 131
    UNION ALL SELECT 'Bottom 10%', 0.10, percentile_cont(0.10) WITHIN GROUP (ORDER BY total)::integer FROM kenya_standings WHERE league_id = 131
) ladder;

CREATE UNIQUE INDEX idx_mv_percentile_ladder_label ON mv_percentile_ladder (label);

CREATE MATERIALIZED VIEW mv_favorite_team_summary AS
WITH latest AS (
    SELECT payload
    FROM fpl_bootstrap_snapshots
    ORDER BY fetched_at DESC
    LIMIT 1
),
teams AS (
    SELECT
        (team->>'id')::integer AS team_id,
        team->>'name' AS team_name,
        team->>'short_name' AS short_name
    FROM latest
    CROSS JOIN LATERAL jsonb_array_elements(payload->'teams') AS team
),
base AS (
    SELECT
        NULLIF(m.raw->>'favourite_team', '')::integer AS team_id,
        ks.entry,
        ks.rank,
        ks.total,
        mm.avg_points,
        mm.volatility,
        mm.bench_points,
        mm.transfer_cost
    FROM managers m
    JOIN kenya_standings ks ON ks.entry = m.entry AND ks.league_id = 131
    LEFT JOIN mv_manager_metrics mm ON mm.entry = m.entry
)
SELECT
    COALESCE(teams.team_id, 0) AS team_id,
    COALESCE(teams.team_name, 'No club declared') AS team_name,
    COALESCE(teams.short_name, 'NONE') AS short_name,
    count(*)::integer AS managers,
    round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS share_pct,
    round(avg(base.total), 2) AS avg_total,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY base.total)::numeric(10,2) AS median_total,
    min(base.rank)::integer AS best_rank,
    round(avg(base.avg_points), 2) AS avg_weekly_points,
    round(avg(base.volatility), 2) AS avg_volatility,
    round(avg(base.bench_points), 2) AS avg_bench_points,
    round(avg(base.transfer_cost), 2) AS avg_transfer_cost
FROM base
LEFT JOIN teams ON teams.team_id = base.team_id
GROUP BY COALESCE(teams.team_id, 0), COALESCE(teams.team_name, 'No club declared'), COALESCE(teams.short_name, 'NONE')
ORDER BY managers DESC;

CREATE UNIQUE INDEX idx_mv_favorite_team_summary_team ON mv_favorite_team_summary (team_id);

ANALYZE mv_manager_metrics;
ANALYZE mv_gameweek_extremes;
ANALYZE mv_rank_band_gameweeks;
ANALYZE mv_percentile_ladder;
ANALYZE mv_favorite_team_summary;
