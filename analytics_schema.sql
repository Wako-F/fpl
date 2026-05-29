SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET maintenance_work_mem = '1GB';
SET work_mem = '256MB';
SET synchronous_commit = off;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

DROP MATERIALIZED VIEW IF EXISTS mv_rank_band_summary;
DROP MATERIALIZED VIEW IF EXISTS mv_points_distribution;
DROP MATERIALIZED VIEW IF EXISTS mv_gameweek_summary;
DROP TABLE IF EXISTS manager_gw_history_new;

CREATE UNLOGGED TABLE manager_gw_history_new (
    entry INTEGER NOT NULL,
    event INTEGER NOT NULL,
    points INTEGER,
    total_points INTEGER,
    rank INTEGER,
    rank_sort INTEGER,
    overall_rank INTEGER,
    percentile_rank INTEGER,
    bank INTEGER,
    value INTEGER,
    event_transfers INTEGER,
    event_transfers_cost INTEGER,
    points_on_bench INTEGER
);

INSERT INTO manager_gw_history_new (
    entry,
    event,
    points,
    total_points,
    rank,
    rank_sort,
    overall_rank,
    percentile_rank,
    bank,
    value,
    event_transfers,
    event_transfers_cost,
    points_on_bench
)
SELECT
    mh.entry,
    (gw.value->>'event')::integer,
    (gw.value->>'points')::integer,
    (gw.value->>'total_points')::integer,
    (gw.value->>'rank')::integer,
    (gw.value->>'rank_sort')::integer,
    (gw.value->>'overall_rank')::integer,
    NULLIF(gw.value->>'percentile_rank', '')::integer,
    (gw.value->>'bank')::integer,
    (gw.value->>'value')::integer,
    (gw.value->>'event_transfers')::integer,
    (gw.value->>'event_transfers_cost')::integer,
    (gw.value->>'points_on_bench')::integer
FROM manager_history mh
CROSS JOIN LATERAL jsonb_array_elements(mh.raw->'current') AS gw(value);

ALTER TABLE manager_gw_history_new
    ADD CONSTRAINT manager_gw_history_new_pkey PRIMARY KEY (entry, event);

CREATE INDEX idx_manager_gw_history_new_event ON manager_gw_history_new (event);
CREATE INDEX idx_manager_gw_history_new_event_points ON manager_gw_history_new (event, points);
CREATE INDEX idx_manager_gw_history_new_entry_event_total ON manager_gw_history_new (entry, event, total_points);
CREATE INDEX idx_kenya_standings_entry_rank ON kenya_standings (entry, rank);
CREATE INDEX IF NOT EXISTS idx_kenya_standings_entry_name_trgm ON kenya_standings USING gin (entry_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_kenya_standings_player_name_trgm ON kenya_standings USING gin (player_name gin_trgm_ops);

ANALYZE manager_gw_history_new;
ANALYZE kenya_standings;

DROP TABLE IF EXISTS manager_gw_history_old;
ALTER TABLE IF EXISTS manager_gw_history RENAME TO manager_gw_history_old;
ALTER TABLE manager_gw_history_new RENAME TO manager_gw_history;

CREATE MATERIALIZED VIEW mv_gameweek_summary AS
SELECT
    event,
    count(*)::integer AS managers,
    round(avg(points), 2) AS avg_points,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY points)::numeric(10,2) AS median_points,
    max(points)::integer AS max_points,
    min(points)::integer AS min_points,
    round(stddev_pop(points), 2) AS volatility,
    round(avg(points_on_bench), 2) AS avg_bench_points,
    round(avg(event_transfers_cost), 2) AS avg_transfer_cost,
    percentile_cont(0.9) WITHIN GROUP (ORDER BY points)::numeric(10,2) AS p90_points,
    percentile_cont(0.1) WITHIN GROUP (ORDER BY points)::numeric(10,2) AS p10_points
FROM manager_gw_history
GROUP BY event
ORDER BY event;

CREATE UNIQUE INDEX idx_mv_gameweek_summary_event ON mv_gameweek_summary (event);

CREATE MATERIALIZED VIEW mv_points_distribution AS
SELECT
    width_bucket(total, 0, 2800, 56) AS bucket,
    min(total)::integer AS min_points,
    max(total)::integer AS max_points,
    count(*)::integer AS managers
FROM kenya_standings
WHERE league_id = 131 AND total IS NOT NULL
GROUP BY bucket
ORDER BY bucket;

CREATE UNIQUE INDEX idx_mv_points_distribution_bucket ON mv_points_distribution (bucket);

CREATE MATERIALIZED VIEW mv_rank_band_summary AS
WITH base AS (
    SELECT
        ks.entry,
        ks.rank,
        ks.total,
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
    band,
    count(DISTINCT base.entry)::integer AS managers,
    round(avg(base.total), 2) AS avg_total,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY base.total)::numeric(10,2) AS median_total,
    round(avg(mgh.points), 2) AS avg_weekly_points,
    round(avg(mgh.points_on_bench), 2) AS avg_bench_points,
    round(avg(mgh.event_transfers_cost), 2) AS avg_transfer_cost,
    round(avg(mgh.value) / 10.0, 2) AS avg_team_value
FROM base
JOIN manager_gw_history mgh ON mgh.entry = base.entry
WHERE band IS NOT NULL
GROUP BY band;

CREATE UNIQUE INDEX idx_mv_rank_band_summary_band ON mv_rank_band_summary (band);

ANALYZE mv_gameweek_summary;
ANALYZE mv_points_distribution;
ANALYZE mv_rank_band_summary;

DROP TABLE IF EXISTS manager_gw_history_old;
