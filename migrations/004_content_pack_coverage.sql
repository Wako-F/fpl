BEGIN;

CREATE TABLE IF NOT EXISTS cohort_memberships (
    season_id TEXT NOT NULL REFERENCES seasons(id),
    event INTEGER NOT NULL,
    cohort_name TEXT NOT NULL DEFAULT 'top_national_rank',
    entry INTEGER NOT NULL,
    selected_rank INTEGER,
    source_snapshot_id BIGINT NOT NULL REFERENCES standings_snapshots(id),
    selected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (season_id, event, cohort_name, entry)
);

CREATE INDEX IF NOT EXISTS idx_cohort_memberships_event
    ON cohort_memberships (season_id, event, cohort_name, selected_rank);

COMMIT;
