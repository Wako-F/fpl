CREATE TABLE IF NOT EXISTS collection_runs (
    id BIGSERIAL PRIMARY KEY,
    job_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    error TEXT
);

CREATE TABLE IF NOT EXISTS raw_api_responses (
    source TEXT NOT NULL DEFAULT 'official_fpl',
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    event INTEGER,
    page INTEGER,
    url TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload JSONB NOT NULL,
    PRIMARY KEY (source, resource_type, resource_id)
);

CREATE TABLE IF NOT EXISTS fpl_bootstrap_snapshots (
    fetched_at TIMESTAMPTZ PRIMARY KEY DEFAULT now(),
    current_event INTEGER,
    player_count INTEGER NOT NULL,
    team_count INTEGER NOT NULL,
    event_count INTEGER NOT NULL,
    payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS fixtures_snapshots (
    fetched_at TIMESTAMPTZ PRIMARY KEY DEFAULT now(),
    fixture_count INTEGER NOT NULL,
    payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS kenya_standings (
    league_id INTEGER NOT NULL,
    page INTEGER NOT NULL,
    entry INTEGER NOT NULL,
    entry_name TEXT,
    player_name TEXT,
    rank INTEGER,
    last_rank INTEGER,
    rank_sort INTEGER,
    total INTEGER,
    event_total INTEGER,
    has_played BOOLEAN,
    club_badge_src TEXT,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw JSONB NOT NULL,
    PRIMARY KEY (league_id, entry)
);

CREATE INDEX IF NOT EXISTS idx_kenya_standings_rank ON kenya_standings (league_id, rank);
CREATE INDEX IF NOT EXISTS idx_kenya_standings_total ON kenya_standings (league_id, total DESC);

CREATE TABLE IF NOT EXISTS managers (
    entry INTEGER PRIMARY KEY,
    player_first_name TEXT,
    player_last_name TEXT,
    player_region_id INTEGER,
    player_region_name TEXT,
    player_region_iso_code TEXT,
    summary_overall_points INTEGER,
    summary_overall_rank INTEGER,
    summary_event_points INTEGER,
    current_event INTEGER,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS manager_history (
    entry INTEGER PRIMARY KEY,
    current_rows INTEGER,
    past_rows INTEGER,
    chips_rows INTEGER,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS manager_transfers (
    entry INTEGER PRIMARY KEY,
    transfer_rows INTEGER,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS manager_picks (
    entry INTEGER NOT NULL,
    event INTEGER NOT NULL,
    picks_rows INTEGER,
    automatic_subs_rows INTEGER,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw JSONB NOT NULL,
    PRIMARY KEY (entry, event)
);

CREATE TABLE IF NOT EXISTS event_live (
    event INTEGER PRIMARY KEY,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS element_summaries (
    element INTEGER PRIMARY KEY,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    fixtures_rows INTEGER,
    history_rows INTEGER,
    history_past_rows INTEGER,
    payload JSONB NOT NULL
);
