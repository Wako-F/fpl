BEGIN;

ALTER TABLE standings_snapshots
    ADD COLUMN IF NOT EXISTS crawl_mode TEXT,
    ADD COLUMN IF NOT EXISTS crawl_status TEXT,
    ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_heartbeat_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS expected_pages INTEGER,
    ADD COLUMN IF NOT EXISTS expected_rows INTEGER,
    ADD COLUMN IF NOT EXISTS rows_fetched INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS duplicate_rows INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS official_data_checked BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS error_summary TEXT;

UPDATE standings_snapshots
SET crawl_mode = CASE WHEN is_complete THEN 'full' ELSE 'bounded' END,
    crawl_status = CASE WHEN pages_collected > 0 THEN 'finished' ELSE 'failed' END,
    started_at = COALESCE(started_at, captured_at),
    finished_at = CASE WHEN pages_collected > 0 THEN COALESCE(finished_at, captured_at) ELSE finished_at END,
    last_heartbeat_at = COALESCE(last_heartbeat_at, captured_at),
    rows_fetched = GREATEST(rows_fetched, managers_collected)
WHERE crawl_mode IS NULL OR crawl_status IS NULL OR started_at IS NULL;

ALTER TABLE standings_snapshots
    ALTER COLUMN crawl_mode SET DEFAULT 'bounded',
    ALTER COLUMN crawl_mode SET NOT NULL,
    ALTER COLUMN crawl_status SET DEFAULT 'running',
    ALTER COLUMN crawl_status SET NOT NULL,
    ALTER COLUMN started_at SET DEFAULT now(),
    ALTER COLUMN started_at SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'standings_snapshots_crawl_mode_check'
    ) THEN
        ALTER TABLE standings_snapshots
            ADD CONSTRAINT standings_snapshots_crawl_mode_check
            CHECK (crawl_mode IN ('bounded', 'full'));
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'standings_snapshots_crawl_status_check'
    ) THEN
        ALTER TABLE standings_snapshots
            ADD CONSTRAINT standings_snapshots_crawl_status_check
            CHECK (crawl_status IN ('running', 'finished', 'failed'));
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS standings_crawl_pages (
    snapshot_id BIGINT NOT NULL REFERENCES standings_snapshots(id) ON DELETE CASCADE,
    page INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    row_count INTEGER,
    has_next BOOLEAN,
    started_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ,
    duration_ms INTEGER,
    error_summary TEXT,
    PRIMARY KEY (snapshot_id, page),
    CHECK (page > 0),
    CHECK (status IN ('pending', 'running', 'finished', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_standings_crawl_pages_progress
    ON standings_crawl_pages (snapshot_id, status, page);

CREATE INDEX IF NOT EXISTS idx_standings_snapshots_crawl_lookup
    ON standings_snapshots (season_id, event DESC, crawl_mode, crawl_status, captured_at DESC);

CREATE OR REPLACE VIEW vw_latest_standings_snapshot AS
SELECT DISTINCT ON (season_id)
    id, season_id, event, captured_at, is_complete, pages_collected, managers_collected,
    source_note, crawl_mode, crawl_status, started_at, finished_at, last_heartbeat_at,
    expected_pages, expected_rows, rows_fetched, duplicate_rows, official_data_checked
FROM standings_snapshots
WHERE crawl_status = 'finished' AND pages_collected > 0
ORDER BY season_id, event DESC NULLS LAST, is_complete DESC, captured_at DESC;

CREATE OR REPLACE VIEW vw_latest_standings AS
SELECT r.*
FROM standings_snapshot_rows r
JOIN vw_latest_standings_snapshot s ON s.id = r.snapshot_id;

COMMIT;
