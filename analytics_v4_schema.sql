SET statement_timeout = 0;
SET lock_timeout = 0;
SET maintenance_work_mem = '1GB';
SET work_mem = '256MB';

DROP MATERIALIZED VIEW IF EXISTS mv_weekly_kenya_ranks;
DROP MATERIALIZED VIEW IF EXISTS mv_season_stories;
DROP MATERIALIZED VIEW IF EXISTS mv_weekly_rank_swings;
DROP MATERIALIZED VIEW IF EXISTS mv_manager_phase_splits;
DROP TABLE IF EXISTS mv_weekly_kenya_ranks;
DROP TABLE IF EXISTS mv_season_stories;
DROP TABLE IF EXISTS mv_weekly_rank_swings;
DROP TABLE IF EXISTS mv_manager_phase_splits;

CREATE MATERIALIZED VIEW mv_weekly_kenya_ranks AS
SELECT
    entry,
    event,
    total_points,
    points,
    rank() OVER (PARTITION BY event ORDER BY total_points DESC, points DESC, entry ASC)::integer AS kenya_rank,
    percent_rank() OVER (PARTITION BY event ORDER BY total_points ASC)::numeric AS kenya_percentile
FROM manager_gw_history;

CREATE UNIQUE INDEX idx_mv_weekly_kenya_ranks_entry_event ON mv_weekly_kenya_ranks (entry, event);
CREATE INDEX idx_mv_weekly_kenya_ranks_event_rank ON mv_weekly_kenya_ranks (event, kenya_rank);

CREATE MATERIALIZED VIEW mv_weekly_rank_swings AS
WITH ranked AS (
    SELECT
        wkr.*,
        lag(kenya_rank) OVER (PARTITION BY entry ORDER BY event) AS previous_kenya_rank
    FROM mv_weekly_kenya_ranks wkr
),
swings AS (
    SELECT
        ranked.entry,
        ks.entry_name,
        ks.player_name,
        ks.rank AS final_rank,
        ranked.event,
        ranked.previous_kenya_rank,
        ranked.kenya_rank,
        (ranked.previous_kenya_rank - ranked.kenya_rank)::integer AS rank_gain,
        ranked.points,
        ranked.total_points
    FROM ranked
    JOIN kenya_standings ks ON ks.entry = ranked.entry AND ks.league_id = 131
    WHERE ranked.previous_kenya_rank IS NOT NULL
)
SELECT *
FROM swings
WHERE abs(rank_gain) > 0
ORDER BY abs(rank_gain) DESC
LIMIT 1000;

CREATE INDEX idx_mv_weekly_rank_swings_gain ON mv_weekly_rank_swings (rank_gain DESC);
CREATE INDEX idx_mv_weekly_rank_swings_event ON mv_weekly_rank_swings (event);

CREATE MATERIALIZED VIEW mv_manager_phase_splits AS
SELECT
    mgh.entry,
    round(avg(mgh.points) FILTER (WHERE event BETWEEN 1 AND 10), 2) AS early_avg,
    round(avg(mgh.points) FILTER (WHERE event BETWEEN 11 AND 20), 2) AS mid_avg,
    round(avg(mgh.points) FILTER (WHERE event BETWEEN 21 AND 30), 2) AS late_avg,
    round(avg(mgh.points) FILTER (WHERE event BETWEEN 31 AND 38), 2) AS run_in_avg,
    sum(mgh.points) FILTER (WHERE event BETWEEN 1 AND 10)::integer AS early_points,
    sum(mgh.points) FILTER (WHERE event BETWEEN 31 AND 38)::integer AS run_in_points
FROM manager_gw_history mgh
GROUP BY mgh.entry;

CREATE UNIQUE INDEX idx_mv_manager_phase_splits_entry ON mv_manager_phase_splits (entry);

CREATE MATERIALIZED VIEW mv_season_stories AS
WITH pivots AS (
    SELECT
        ks.entry,
        ks.entry_name,
        ks.player_name,
        ks.rank AS final_rank,
        ks.total,
        max(wkr.kenya_rank) FILTER (WHERE wkr.event = 5) AS rank_gw5,
        max(wkr.kenya_rank) FILTER (WHERE wkr.event = 10) AS rank_gw10,
        max(wkr.kenya_rank) FILTER (WHERE wkr.event = 20) AS rank_gw20,
        max(wkr.kenya_rank) FILTER (WHERE wkr.event = 30) AS rank_gw30,
        max(wkr.kenya_rank) FILTER (WHERE wkr.event = 38) AS rank_gw38,
        min(wkr.kenya_rank) AS best_kenya_rank,
        max(wkr.kenya_rank) AS worst_kenya_rank
    FROM kenya_standings ks
    JOIN mv_weekly_kenya_ranks wkr ON wkr.entry = ks.entry
    WHERE ks.league_id = 131
    GROUP BY ks.entry, ks.entry_name, ks.player_name, ks.rank, ks.total
),
stories AS (
    SELECT
        pivots.*,
        phase.early_avg,
        phase.mid_avg,
        phase.late_avg,
        phase.run_in_avg,
        phase.early_points,
        phase.run_in_points,
        (rank_gw10 - final_rank)::integer AS comeback_after_gw10,
        (rank_gw20 - final_rank)::integer AS comeback_after_gw20,
        (rank_gw30 - final_rank)::integer AS run_in_gain,
        (final_rank - rank_gw10)::integer AS collapse_after_gw10,
        (worst_kenya_rank - best_kenya_rank)::integer AS journey_range,
        CASE
            WHEN rank_gw20 - final_rank >= 50000 THEN 'Comeback King'
            WHEN rank_gw30 - final_rank >= 25000 THEN 'Late Charger'
            WHEN final_rank - rank_gw10 >= 50000 THEN 'Early Collapse'
            WHEN worst_kenya_rank - best_kenya_rank <= 5000 AND final_rank <= 10000 THEN 'Elite Cruiser'
            WHEN run_in_avg >= early_avg + 10 THEN 'Run-in Heater'
            WHEN early_avg >= run_in_avg + 10 THEN 'Early Burner'
            ELSE 'Ordinary Arc'
        END AS story_type
    FROM pivots
    JOIN mv_manager_phase_splits phase ON phase.entry = pivots.entry
)
SELECT *
FROM stories;

CREATE UNIQUE INDEX idx_mv_season_stories_entry ON mv_season_stories (entry);
CREATE INDEX idx_mv_season_stories_type ON mv_season_stories (story_type);
CREATE INDEX idx_mv_season_stories_comeback20 ON mv_season_stories (comeback_after_gw20 DESC);
CREATE INDEX idx_mv_season_stories_runin ON mv_season_stories (run_in_gain DESC);
CREATE INDEX idx_mv_season_stories_collapse ON mv_season_stories (collapse_after_gw10 DESC);

ANALYZE mv_weekly_kenya_ranks;
ANALYZE mv_weekly_rank_swings;
ANALYZE mv_manager_phase_splits;
ANALYZE mv_season_stories;
