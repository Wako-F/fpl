BEGIN;

ALTER TABLE standings_snapshots
    ADD COLUMN IF NOT EXISTS official_data_checked BOOLEAN NOT NULL DEFAULT false;

CREATE OR REPLACE VIEW vw_latest_standings_snapshot AS
SELECT DISTINCT ON (season_id)
    id, season_id, event, captured_at, is_complete, pages_collected, managers_collected,
    source_note, crawl_mode, crawl_status, started_at, finished_at, last_heartbeat_at,
    expected_pages, expected_rows, rows_fetched, duplicate_rows, official_data_checked
FROM standings_snapshots
WHERE crawl_status = 'finished' AND pages_collected > 0
ORDER BY season_id, event DESC NULLS LAST, is_complete DESC, captured_at DESC;

COMMIT;
