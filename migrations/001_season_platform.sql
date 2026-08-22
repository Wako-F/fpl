BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS seasons (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    starts_year INTEGER NOT NULL,
    ends_year INTEGER NOT NULL,
    country_league_id INTEGER NOT NULL,
    country_region_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (ends_year = starts_year + 1)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_seasons_one_active
    ON seasons (is_active) WHERE is_active;

INSERT INTO seasons (id, label, starts_year, ends_year, country_league_id, country_region_id, is_active)
VALUES
    ('2025-26', '2025/26', 2025, 2026, 131, 111, false),
    ('2026-27', '2026/27', 2026, 2027, 131, 111, true)
ON CONFLICT (id) DO UPDATE SET
    label = EXCLUDED.label,
    country_league_id = EXCLUDED.country_league_id,
    country_region_id = EXCLUDED.country_region_id,
    is_active = EXCLUDED.is_active;

UPDATE seasons SET is_active = (id = '2026-27');

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id BIGSERIAL PRIMARY KEY,
    season_id TEXT NOT NULL REFERENCES seasons(id),
    job_name TEXT NOT NULL,
    event INTEGER,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    error TEXT,
    CHECK (status IN ('running', 'finished', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_season_started
    ON pipeline_runs (season_id, started_at DESC);

CREATE TABLE IF NOT EXISTS raw_snapshots (
    id BIGSERIAL PRIMARY KEY,
    season_id TEXT NOT NULL REFERENCES seasons(id),
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    event INTEGER,
    page INTEGER,
    url TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload_sha256 TEXT NOT NULL,
    payload JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_snapshots_lookup
    ON raw_snapshots (season_id, resource_type, resource_id, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_snapshots_event
    ON raw_snapshots (season_id, event, resource_type, fetched_at DESC);

CREATE TABLE IF NOT EXISTS fpl_events (
    season_id TEXT NOT NULL REFERENCES seasons(id),
    event INTEGER NOT NULL,
    name TEXT NOT NULL,
    deadline_time TIMESTAMPTZ NOT NULL,
    is_previous BOOLEAN NOT NULL DEFAULT false,
    is_current BOOLEAN NOT NULL DEFAULT false,
    is_next BOOLEAN NOT NULL DEFAULT false,
    finished BOOLEAN NOT NULL DEFAULT false,
    data_checked BOOLEAN NOT NULL DEFAULT false,
    average_entry_score INTEGER,
    highest_score INTEGER,
    ranked_count BIGINT,
    chip_plays JSONB NOT NULL DEFAULT '[]'::jsonb,
    raw JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (season_id, event)
);

CREATE TABLE IF NOT EXISTS fpl_teams (
    season_id TEXT NOT NULL REFERENCES seasons(id),
    team_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    code INTEGER,
    strength INTEGER,
    raw JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (season_id, team_id)
);

CREATE TABLE IF NOT EXISTS fpl_players (
    season_id TEXT NOT NULL REFERENCES seasons(id),
    element INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    element_type INTEGER NOT NULL,
    web_name TEXT NOT NULL,
    first_name TEXT,
    second_name TEXT,
    now_cost INTEGER NOT NULL,
    status TEXT,
    selected_by_percent NUMERIC,
    total_points INTEGER NOT NULL DEFAULT 0,
    event_points INTEGER NOT NULL DEFAULT 0,
    form NUMERIC,
    points_per_game NUMERIC,
    expected_goals NUMERIC,
    expected_assists NUMERIC,
    expected_goal_involvements NUMERIC,
    expected_goals_conceded NUMERIC,
    defensive_contribution INTEGER,
    price_change_projection JSONB,
    raw JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (season_id, element),
    FOREIGN KEY (season_id, team_id) REFERENCES fpl_teams(season_id, team_id)
);

CREATE INDEX IF NOT EXISTS idx_fpl_players_season_points
    ON fpl_players (season_id, total_points DESC);
CREATE INDEX IF NOT EXISTS idx_fpl_players_season_team
    ON fpl_players (season_id, team_id);

CREATE TABLE IF NOT EXISTS fpl_fixtures (
    season_id TEXT NOT NULL REFERENCES seasons(id),
    fixture_id INTEGER NOT NULL,
    event INTEGER,
    kickoff_time TIMESTAMPTZ,
    team_h INTEGER NOT NULL,
    team_a INTEGER NOT NULL,
    team_h_score INTEGER,
    team_a_score INTEGER,
    finished BOOLEAN NOT NULL DEFAULT false,
    started BOOLEAN NOT NULL DEFAULT false,
    difficulty_h INTEGER,
    difficulty_a INTEGER,
    raw JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (season_id, fixture_id)
);

CREATE INDEX IF NOT EXISTS idx_fpl_fixtures_season_event
    ON fpl_fixtures (season_id, event, kickoff_time);

CREATE TABLE IF NOT EXISTS standings_snapshots (
    id BIGSERIAL PRIMARY KEY,
    season_id TEXT NOT NULL REFERENCES seasons(id),
    event INTEGER,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_complete BOOLEAN NOT NULL DEFAULT false,
    pages_collected INTEGER NOT NULL DEFAULT 0,
    managers_collected INTEGER NOT NULL DEFAULT 0,
    source_note TEXT
);

CREATE INDEX IF NOT EXISTS idx_standings_snapshots_latest
    ON standings_snapshots (season_id, captured_at DESC);

CREATE TABLE IF NOT EXISTS standings_snapshot_rows (
    snapshot_id BIGINT NOT NULL REFERENCES standings_snapshots(id) ON DELETE CASCADE,
    season_id TEXT NOT NULL REFERENCES seasons(id),
    event INTEGER,
    page INTEGER NOT NULL,
    entry INTEGER NOT NULL,
    entry_name TEXT,
    player_name TEXT,
    rank INTEGER,
    last_rank INTEGER,
    total INTEGER,
    event_total INTEGER,
    has_played BOOLEAN,
    raw JSONB NOT NULL,
    PRIMARY KEY (snapshot_id, entry)
);

CREATE INDEX IF NOT EXISTS idx_standings_rows_season_event_rank
    ON standings_snapshot_rows (season_id, event, rank);
CREATE INDEX IF NOT EXISTS idx_standings_rows_entry
    ON standings_snapshot_rows (season_id, entry, snapshot_id DESC);
CREATE INDEX IF NOT EXISTS idx_standings_rows_entry_name_trgm
    ON standings_snapshot_rows USING gin (entry_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_standings_rows_player_name_trgm
    ON standings_snapshot_rows USING gin (player_name gin_trgm_ops);

CREATE TABLE IF NOT EXISTS manager_profiles_v2 (
    season_id TEXT NOT NULL REFERENCES seasons(id),
    entry INTEGER NOT NULL,
    player_first_name TEXT,
    player_last_name TEXT,
    player_region_id INTEGER,
    player_region_name TEXT,
    favourite_team INTEGER,
    summary_overall_points INTEGER,
    summary_overall_rank INTEGER,
    summary_event_points INTEGER,
    current_event INTEGER,
    raw JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (season_id, entry)
);

CREATE TABLE IF NOT EXISTS manager_event_history_v2 (
    season_id TEXT NOT NULL REFERENCES seasons(id),
    entry INTEGER NOT NULL,
    event INTEGER NOT NULL,
    points INTEGER,
    total_points INTEGER,
    overall_rank INTEGER,
    percentile_rank INTEGER,
    bank INTEGER,
    team_value INTEGER,
    event_transfers INTEGER,
    event_transfers_cost INTEGER,
    points_on_bench INTEGER,
    raw JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (season_id, entry, event)
);

CREATE INDEX IF NOT EXISTS idx_manager_event_history_event_points
    ON manager_event_history_v2 (season_id, event, points DESC);

CREATE TABLE IF NOT EXISTS manager_chips_v2 (
    season_id TEXT NOT NULL REFERENCES seasons(id),
    entry INTEGER NOT NULL,
    chip_name TEXT NOT NULL,
    event INTEGER NOT NULL,
    raw JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (season_id, entry, chip_name, event)
);

CREATE TABLE IF NOT EXISTS manager_picks_v2 (
    season_id TEXT NOT NULL REFERENCES seasons(id),
    entry INTEGER NOT NULL,
    event INTEGER NOT NULL,
    element INTEGER NOT NULL,
    position INTEGER NOT NULL,
    multiplier INTEGER NOT NULL,
    is_captain BOOLEAN NOT NULL,
    is_vice_captain BOOLEAN NOT NULL,
    raw JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (season_id, entry, event, position)
);

CREATE INDEX IF NOT EXISTS idx_manager_picks_event_element
    ON manager_picks_v2 (season_id, event, element);

CREATE TABLE IF NOT EXISTS player_event_live_v2 (
    season_id TEXT NOT NULL REFERENCES seasons(id),
    event INTEGER NOT NULL,
    element INTEGER NOT NULL,
    total_points INTEGER NOT NULL DEFAULT 0,
    minutes INTEGER NOT NULL DEFAULT 0,
    goals_scored INTEGER NOT NULL DEFAULT 0,
    assists INTEGER NOT NULL DEFAULT 0,
    clean_sheets INTEGER NOT NULL DEFAULT 0,
    saves INTEGER NOT NULL DEFAULT 0,
    bonus INTEGER NOT NULL DEFAULT 0,
    bps INTEGER NOT NULL DEFAULT 0,
    defensive_contribution INTEGER NOT NULL DEFAULT 0,
    expected_goals NUMERIC,
    expected_assists NUMERIC,
    raw JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (season_id, event, element)
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    season_id TEXT NOT NULL REFERENCES seasons(id),
    element INTEGER NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    now_cost INTEGER NOT NULL,
    transfers_in_event INTEGER NOT NULL DEFAULT 0,
    transfers_out_event INTEGER NOT NULL DEFAULT 0,
    selected_by_percent NUMERIC,
    projection JSONB,
    PRIMARY KEY (season_id, element, captured_at)
);

CREATE TABLE IF NOT EXISTS content_facts (
    season_id TEXT NOT NULL REFERENCES seasons(id),
    event INTEGER NOT NULL,
    fact_key TEXT NOT NULL,
    status TEXT NOT NULL,
    value JSONB NOT NULL,
    cohort TEXT NOT NULL,
    sample_size INTEGER,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    methodology TEXT NOT NULL,
    source_snapshot_id BIGINT REFERENCES standings_snapshots(id),
    PRIMARY KEY (season_id, event, fact_key, status),
    CHECK (status IN ('live', 'provisional', 'final'))
);

CREATE TABLE IF NOT EXISTS data_quality_results (
    id BIGSERIAL PRIMARY KEY,
    pipeline_run_id BIGINT REFERENCES pipeline_runs(id),
    season_id TEXT NOT NULL REFERENCES seasons(id),
    event INTEGER,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    observed_value TEXT,
    expected_value TEXT,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (status IN ('pass', 'warn', 'fail'))
);

CREATE OR REPLACE VIEW vw_active_season AS
SELECT * FROM seasons WHERE is_active;

CREATE OR REPLACE VIEW vw_latest_standings_snapshot AS
SELECT DISTINCT ON (season_id)
    id, season_id, event, captured_at, is_complete, pages_collected, managers_collected, source_note
FROM standings_snapshots
ORDER BY season_id, captured_at DESC;

CREATE OR REPLACE VIEW vw_latest_standings AS
SELECT r.*
FROM standings_snapshot_rows r
JOIN vw_latest_standings_snapshot s ON s.id = r.snapshot_id;

CREATE OR REPLACE VIEW vw_manager_event_metrics AS
SELECT
    h.season_id,
    h.entry,
    count(*)::integer AS gameweeks,
    round(avg(h.points), 2) AS avg_points,
    round(stddev_pop(h.points), 2) AS volatility,
    max(h.points)::integer AS best_week,
    min(h.points)::integer AS worst_week,
    sum(h.points_on_bench)::integer AS bench_points,
    sum(h.event_transfers_cost)::integer AS transfer_cost,
    round(avg(h.team_value) / 10.0, 2) AS avg_team_value
FROM manager_event_history_v2 h
GROUP BY h.season_id, h.entry;

COMMIT;
